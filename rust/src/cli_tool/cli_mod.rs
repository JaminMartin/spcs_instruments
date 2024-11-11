use crate::data_handler::{create_explog_file, create_time_stamp, process_output};
use crate::mail_handler::mailer;
use clap::Parser;
use env_logger::{Builder, Target};
use log::LevelFilter;
use pyo3::prelude::*;
use std::env;
use std::fs;
use std::io::{self, BufRead};
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::thread::sleep;
use std::time::Duration;

fn get_current_dir() -> String {
    env::current_dir()
        .unwrap_or_else(|_| PathBuf::from("."))
        .to_str()
        .unwrap()
        .to_string()
}

fn resolve_path(path: &Path) -> PathBuf {
    if path.is_absolute() {
        path.to_path_buf()
    } else {
        env::current_dir().unwrap().join(path)
    }
}

/// A commandline experiment manager for SPCS-Instruments
#[derive(Parser, Debug)]
#[command(version, about, long_about = None)]
struct Args {
    /// desired log level, info displays summary of connected instruments & recent data. debug will include all data, including standard output from Python.
    #[arg(short, long, default_value_t = 2)]
    verbosity: u8,
    /// Email address to receive results
    #[arg(short, long)]
    email: Option<String>,
    /// Time delay in minutes before starting the experiment
    #[arg(short, long, default_value_t = 0)]
    delay: u64,
    /// Number of times to loop the experiment
    #[arg(short, long, default_value_t = 1)]
    loops: u8,
    /// Path to the python file containing the experimental setup
    #[arg(short, long)]
    path: PathBuf,
    /// Target directory for output path
    #[arg(short, long, default_value_t = get_current_dir())]
    output: String,
}

#[pyfunction]
pub fn cli_parser() {
    // Initialises a temp file for writing experimental data to that can be accessed by other functions. Ensures that if cleanup has failed then logs arent appended into the same file in the next run

    let temp_filename = ".exp_output.log";
    match create_explog_file(temp_filename) {
        Ok(_) => {}
        Err(e) => eprintln!("Error creating experimental logfile file: {}", e),
    }

    // Placeholder fix to allow spcs-instruments to work on windows. Rye does not seem to path correctly on non-unix based
    // systems. This is a work around based on rye's internal structure. It is a hotfix and is by no means "correct" however, it does work.
    let original_args: Vec<String> = std::env::args().collect();
    let split_point = ".rye";
    let corrected_win_path = "\\tools\\spcs-instruments\\Scripts\\python.exe";
    let mut corrected_paths = Vec::new();

    let python_path: Option<&String> = match env::consts::OS {
        "windows" => {
            let original_path = original_args.iter().find(|arg| arg.contains("python"));

            match original_path {
                Some(original_path) => {
                    let split_path: Vec<&str> = original_path.split(split_point).collect();
                    match split_path.first() {
                        Some(first_part) => {
                            let corrected_path =
                                format!("{}{}{}", first_part, split_point, corrected_win_path);

                            corrected_paths.push(corrected_path);
                            corrected_paths.last().map(|s| s as &String)
                        }
                        None => None,
                    }
                }
                None => original_args.iter().find(|arg| arg.contains("python")),
            }
        }
        _ => original_args.iter().find(|arg| arg.contains("python")),
    };

    let python_path_str = match python_path {
        Some(python_path) => python_path.clone(),
        None => "".to_string(),
    };

    let mut cleaned_args: Vec<String> = original_args
        .into_iter()
        .filter(|arg| !arg.contains("python"))
        .collect();

    if let Some(first_arg_index) = cleaned_args.iter().position(|arg| !arg.starts_with('-')) {
        cleaned_args[first_arg_index] = "pfx".to_string();
    }

    let args = Args::parse_from(cleaned_args);

    let log_level = match args.verbosity {
        0 => LevelFilter::Error,
        1 => LevelFilter::Warn,
        2 => LevelFilter::Info,
        3 => LevelFilter::Debug,
        _ => LevelFilter::Trace,
    };
    let mut builder = Builder::new();
    builder
        .filter_level(log_level)
        .target(Target::Stdout)
        .format_timestamp_secs();
    builder.init();
    log::info!(target: "pfx", "Experiment starting in {} s", args.delay * 60);
    sleep(Duration::from_secs(&args.delay * 60));

    if !python_path_str.is_empty() {
        let script_path = args.path;
        for _ in 0..args.loops {
            let file_name_suffix = create_time_stamp(true);
            // Execute the Python script
            let mut output = Command::new(&python_path_str)
                .arg("-u")
                .arg(&script_path)
                .stdout(Stdio::piped())
                .spawn()
                .expect("Failed to execute Python script");

            // Handle the output
            if let Some(stdout) = output.stdout.take() {
                let reader = io::BufReader::new(stdout);
                for line in reader.lines() {
                    match line {
                        Ok(line) => log::debug!(target: "python", "{}", line),
                        Err(e) => log::error!(target: "python" , "Error reading line: {}", e),
                    }
                }
            }
            let output_path: PathBuf = resolve_path(Path::new(&args.output));
            let output_file = match process_output(&output_path, &file_name_suffix) {
                Ok(v) => Ok(v),
                Err(e) => {
                    log::error!(target: "pfx", "{:?}", e);

                    Err(e)
                }
            };
            log::info!(target: "pfex", "The output file directory is: {}", output_path.display());

            mailer(args.email.as_ref(), &output_path, &output_file);
        }
    } else {
        log::error!(target: "pfx","No Python path found in the arguments");
    }

    match fs::remove_file(temp_filename) {
        Ok(_) => {
            log::info!(target: "pfx", "Experiment exited, Cleaned up temp files")
        }
        Err(_e) => log::info!(target: "pfx", "Nothing to clean up! Experiment complete",),
    }
}
