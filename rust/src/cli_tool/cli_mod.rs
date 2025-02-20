use crate::data_handler::{create_time_stamp, ServerState};
use crate::mail_handler::mailer;
use crate::tcp_handler::{save_state, server_status, start_tcp_server};
use crate::tui_tool::run_tui;
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
use tui_logger;

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
    /// Enable interactive TUI mode
    #[arg(short, long)]
    interactive: bool,
}
#[derive(Parser, Debug)]
#[command(version, about, long_about = None)]
struct StandaloneArgs {
    // Port the current experiment is running on. If you are running this on the same device it will be 127.0.0.1:7676
    // otherwise, please use the devices IP , device_ip:7676
    #[arg(short, long)]
    address: String,
    /// desired log level, info displays summary of connected instruments & recent data. debug will include all data, including standard output from Python.
    #[arg(short, long, default_value_t = 2)]
    verbosity: u8,
}

#[pyfunction]
pub fn cli_parser() {
    // Placeholder fix to allow spcs-instruments to work on windows. Rye does not seem to path correctly on non-unix based
    // systems. This is a work around based on rye's internal structure. It is a hotfix and is by no means "correct" however, it does work.
    // This fails to work in development builds due to the hard coded paths which are obviously different.
    // Testing on windows requires complete building with rye rather than maturin.

    let original_args: Vec<String> = std::env::args().collect();

    let (mut cleaned_args, python_path_str) = process_args(original_args);

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
    if args.interactive {
        let _ = tui_logger::init_logger(log_level);
    } else {
        let mut builder = Builder::new();
        builder
            .filter_level(log_level)
            .target(Target::Stdout)
            .format_timestamp_secs();
        builder.init();
    };

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

            let tui_thread = if args.interactive {
                Some(thread::spawn(move || {
                    let rt = match tokio::runtime::Runtime::new() {
                        Ok(rt) => rt,
                        Err(e) => {
                            log::error!("Error creating Tokio runtime for TUI: {:?}", e);
                            return;
                        }
                    };

                    match rt.block_on(run_tui("127.0.0.1:7676")) {
                        Ok(_) => log::info!("TUI closed successfully"),
                        Err(e) => log::error!("TUI encountered an error: {}", e),
                    }
                }))
            } else {
                None
            };
            let tcp_server_thread = thread::spawn(move || {
                let addr = "127.0.0.1:7676";
                let rt = match tokio::runtime::Runtime::new() {
                    Ok(rt) => rt,
                    Err(e) => {
                        log::error!("Error in thread: {:?}", e);
                        return;
                    }
                };
                rt.block_on(start_tcp_server(tcp_tx, addr, tcp_state, shutdown_rx_tcp))
                    .unwrap();
            });
            let python_thread = thread::spawn(move || {
                start_python_process(python_path_clone, script_path_clone, log_level).unwrap();
                shutdown_tx.send(()).unwrap();
            });

            let printer_thread = thread::spawn(move || {
                let rt = match tokio::runtime::Runtime::new() {
                    Ok(rt) => rt,
                    Err(e) => {
                        log::error!("Error in thread: {:?}", e);
                        return;
                    }
                };

                rt.block_on(server_status(server_state, shutdown_rx_server_satus))
                    .unwrap();
            });
            let save_statie_arc = Arc::clone(&state);
            let file_name_suffix = create_time_stamp(true);

            let output_path_clone = Arc::clone(&output_path);
            let dumper = thread::spawn(move || {
                let rt = match tokio::runtime::Runtime::new() {
                    Ok(rt) => rt,
                    Err(e) => {
                        log::error!("Failed to create Tokio runtime in Dumper Thread: {:?}", e);
                        return None;
                    }
                };

                match rt.block_on(save_state(
                    save_statie_arc,
                    shutdown_rx_logger,
                    &file_name_suffix,
                    output_path_clone.as_ref(),
                )) {
                    Ok(filename) => {
                        log::info!("Dumper Thread completed successfully.");
                        Some(filename)
                    }
                    Err(e) => {
                        log::error!("Dumper Thread encountered an error: {:?}", e);
                        None
                    }
                }
            });
            for received in rx.try_iter() {
                log::debug!("Received data: {}", received);
            }
            let tcp_server_result = tcp_server_thread.join();
            let python_result = python_thread.join();
            let printer_result = printer_thread.join();
            let dumper_result = dumper.join();
            match tui_thread {
                Some(tui_result) => {
                    let result = tui_result.join();
                    match result {
                        Ok(_) => log::info!("Tui hread shutdown successfully."),
                        Err(e) => {
                            if let Some(err) = e.downcast_ref::<String>() {
                                log::error!("Tui thread encountered an error: {}", err);
                            } else if let Some(err) = e.downcast_ref::<&str>() {
                                log::error!("Tui thread encountered an error: {}", err);
                            } else {
                                log::error!("Tui thread encountered an unknown error.");
                            }
                        }
                    }
                }
                None => {}
            };

            let results = [
                ("TCP Server Thread", tcp_server_result),
                ("Python Thread", python_result),
                ("Printer Thread", printer_result),
            ];

            for (name, result) in &results {
                match result {
                    Ok(_) => log::info!("{} shutdown successfully.", name),
                    Err(e) => {
                        if let Some(err) = e.downcast_ref::<String>() {
                            log::error!("{} encountered an error: {}", name, err);
                        } else if let Some(err) = e.downcast_ref::<&str>() {
                            log::error!("{} encountered an error: {}", name, err);
                        } else {
                            log::error!("{} encountered an unknown error.", name);
                        }
                    }
                }
            }
            let output_file = match dumper_result {
                Ok(Some(filename)) => {
                    log::info!("Data Storage Thread shutdown successfully.");
                    filename
                }
                Ok(None) => {
                    log::error!(
                        "Dumper Thread shutdown successfully but failed to produce a filename"
                    );
                    return;
                }
                Err(e) => {
                    if let Some(err) = e.downcast_ref::<String>() {
                        log::error!("Dumper Thread encountered an error: {}", err);
                    } else if let Some(err) = e.downcast_ref::<&str>() {
                        log::error!("Dumper Thread encountered an error: {}", err);
                    } else {
                        log::error!("Dumper Thread encountered an unknown error.");
                    }
                    return;
                }
            };
            log::info!(target: "pfx", "The output file directory is: {}", output_path);
            mailer(args.email.as_ref(), &output_file);
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

fn start_python_process(
    python_path: Arc<String>,
    script_path: Arc<PathBuf>,
    log_level: LevelFilter,
) -> io::Result<()> {
    let level_str = match log_level {
        LevelFilter::Error => "ERROR",
        LevelFilter::Warn => "WARNING",
        LevelFilter::Info => "INFO",
        LevelFilter::Debug => "DEBUG",
        LevelFilter::Trace => "DEBUG",
        LevelFilter::Off => "ERROR",
    };
    let mut python_process = Command::new(python_path.as_ref())
        .env("RUST_LOG_LEVEL", level_str)
        .arg("-u")
        .arg(script_path.as_ref())
        .stdout(Stdio::piped()) // Capture stdout
        .stderr(Stdio::piped()) // Capture stderr
        .spawn()
        .expect("Failed to execute Python script");


    let stdout = python_process
        .stdout
        .take()
        .expect("Failed to capture stdout");
    let stderr = python_process
        .stderr
        .take()
        .expect("Failed to capture stderr");

    let stdout_reader = io::BufReader::new(stdout);
    let stderr_reader = io::BufReader::new(stderr);


    let stdout_thread = std::thread::spawn(move || {
        for line in stdout_reader.lines() {
            match line {
                Ok(line) => log::debug!(target: "Python", "{}", line),
                Err(e) => log::error!("Error reading stdout: {}", e),
            }
        }
    });

    let stderr_thread = std::thread::spawn(move || {
        let mut in_traceback = false; 
    
        for line in stderr_reader.lines() {
            match line {
                Ok(line) if line.starts_with("Traceback (most recent call last):") => {
                    in_traceback = true;
                    log::error!("{}", line);
                }
                Ok(line) if in_traceback => {
                    log::error!("{}", line);
                    if line.trim().is_empty() {
                        in_traceback = false;
                    }
                }
                Ok(line) if line.contains("(Ctrl+C)") => log::warn!("{}", line),
                Ok(line) => log::debug!("{}", line),
                Err(e) => log::error!("Error reading stderr: {}", e),
            }
        }
    });


    let _ = stdout_thread.join();
    let _ = stderr_thread.join();


    let status = python_process.wait()?;
    log::info!("Python process exited with status: {}", status);

    Ok(())
}

#[pyfunction]
pub fn cli_standalone() {
    let original_args: Vec<String> = std::env::args().collect();
    //let args = Args::parse_from(original_args);
    let (mut cleaned_args, _) = process_args(original_args);
    if let Some(first_arg_index) = cleaned_args.iter().position(|arg| !arg.starts_with('-')) {
        cleaned_args[first_arg_index] = "pfxs".to_string();
    }
    let args = StandaloneArgs::parse_from(cleaned_args);

    let log_level = match args.verbosity {
        0 => LevelFilter::Error,
        1 => LevelFilter::Warn,
        2 => LevelFilter::Info,
        3 => LevelFilter::Debug,
        _ => LevelFilter::Trace,
    };

    let _ = tui_logger::init_logger(log_level);

    let tui_thread = Some(thread::spawn(move || {
        let rt = match tokio::runtime::Runtime::new() {
            Ok(rt) => rt,
            Err(e) => {
                log::error!("Error creating Tokio runtime for TUI: {:?}", e);
                return;
            }
        };

        match rt.block_on(run_tui(&args.address)) {
            Ok(_) => log::info!("TUI closed successfully"),
            Err(e) => log::error!("TUI encountered an error: {}", e),
        }
    }));

    match tui_thread {
        Some(tui_result) => {
            let result = tui_result.join();
            match result {
                Ok(_) => log::info!("Tui hread shutdown successfully."),
                Err(e) => {
                    if let Some(err) = e.downcast_ref::<String>() {
                        log::error!("Tui thread encountered an error: {}", err);
                    } else if let Some(err) = e.downcast_ref::<&str>() {
                        log::error!("Tui thread encountered an error: {}", err);
                    } else {
                        log::error!("Tui thread encountered an unknown error.");
                    }
                }
            }
        }
        None => {}
    };
}

fn process_args(original_args: Vec<String>) -> (Vec<String>, String) {
    let split_point = ".rye";
    let corrected_win_path = "\\tools\\spcs-instruments\\Scripts\\python.exe";
    let mut corrected_paths = Vec::new();

    let python_path: Option<String> = match env::consts::OS {
        "windows" => {
            let original_path = original_args.iter().find(|arg| arg.contains("python"));

            match original_path {
                Some(original_path) => {
                    let split_path: Vec<&str> = original_path.split(split_point).collect();
                    match split_path.first() {
                        Some(first_part) => {
                            let corrected_path =
                                format!("{}{}{}", first_part, split_point, corrected_win_path);

                            corrected_paths.push(corrected_path.clone());
                            Some(corrected_path)
                        }
                        None => None,
                    }
                }
                None => None,
            }
        }
        _ => original_args
            .iter()
            .find(|arg| arg.contains("python"))
            .cloned(),
    };

    let python_path_str = python_path.unwrap_or_else(|| "".to_string());

    let cleaned_args = original_args
        .into_iter()
        .filter(|arg| !arg.contains("python"))
        .collect();
    (cleaned_args, python_path_str)
}
