use crate::data_handler::{create_time_stamp, ServerState};
use crate::tcp_handler::{save_state, server_status, start_tcp_server};
use clap::Parser;
use crossbeam::channel;
use env_logger::{Builder, Target};
use log::LevelFilter;
use pyo3::prelude::*;
use std::env;
use std::fmt::Debug;
use std::io::{self, BufRead};
use std::path::PathBuf;
use std::process::{Command, Stdio};
use std::sync::Arc;
use std::thread;
use std::thread::sleep;
use std::time::Duration;
use tokio::sync::broadcast;
use tokio::sync::Mutex;

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
    let python_path = Arc::new(python_path_str);
    let script_path = Arc::new(args.path);
    let python_path_loop = Arc::clone(&python_path);
    let output_path = Arc::new(args.output);
    if !python_path_loop.is_empty() {
        for _ in 0..args.loops {
            let python_path_clone = Arc::clone(&python_path);
            let script_path_clone = Arc::clone(&script_path);
            log::info!("Server is starting...");
            let (tx, rx) = channel::unbounded();
            let state = Arc::new(Mutex::new(ServerState::new()));
            let (shutdown_tx, _) = broadcast::channel(1);
            let shutdown_rx_tcp = shutdown_tx.subscribe();
            let shutdown_rx_server_satus = shutdown_tx.subscribe();
            let shutdown_rx_logger = shutdown_tx.subscribe();

            let tcp_state = Arc::clone(&state);
            let server_state = Arc::clone(&state);
            let tcp_tx = tx.clone();

            let tcp_server_thread = thread::spawn(move || {
                let addr = "127.0.0.1:8080";
                let rt = tokio::runtime::Runtime::new().unwrap();
                rt.block_on(start_tcp_server(tcp_tx, addr, tcp_state, shutdown_rx_tcp))
                    .unwrap();
            });
            let python_thread = thread::spawn(move || {
                start_python_process(python_path_clone, script_path_clone).unwrap();
                shutdown_tx.send(()).unwrap();
            });

            let printer_thread = thread::spawn(move || {
                let rt = tokio::runtime::Runtime::new().unwrap();
                rt.block_on(server_status(server_state, shutdown_rx_server_satus))
                    .unwrap();
            });
            let save_statie_arc = Arc::clone(&state);
            let file_name_suffix = create_time_stamp(true);

            let output_path_clone = Arc::clone(&output_path);
            let dumper = thread::spawn(move || {
                let rt = tokio::runtime::Runtime::new().unwrap();
                rt.block_on(save_state(
                    save_statie_arc,
                    shutdown_rx_logger,
                    &file_name_suffix,
                    output_path_clone.as_ref(),
                ))
                .unwrap();
            });

            for received in rx.try_iter() {
                log::debug!("Received data: {}", received);
            }
            tcp_server_thread.join().unwrap();
            python_thread.join().unwrap();
            printer_thread.join().unwrap();
            dumper.join().unwrap();
            log::info!(target: "pfx", "The output file directory is: {}", output_path);
            // TODO! fix mailer for new structure.
            //mailer(args.email.as_ref(), &output_path, &output_file);
        }
    } else {
        log::error!(target: "pfx","No Python path found in the arguments");
    }
}

fn get_current_dir() -> String {
    env::current_dir()
        .unwrap_or_else(|_| PathBuf::from("."))
        .to_str()
        .unwrap()
        .to_string()
}

fn start_python_process(python_path: Arc<String>, script_path: Arc<PathBuf>) -> io::Result<()> {
    let mut python_process = Command::new(python_path.as_ref())
        .arg("-u")
        .arg(script_path.as_ref())
        .stdout(Stdio::piped())
        .spawn()
        .expect("Failed to execute Python script");

    // Handle the output
    if let Some(stdout) = python_process.stdout.take() {
        let reader = io::BufReader::new(stdout);
        for line in reader.lines() {
            match line {
                Ok(line) => log::debug!(target: "python", "{}", line),
                Err(e) => log::error!("Error reading line: {}", e),
            }
        }
    }
    Ok(())
}
