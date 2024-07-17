use pyo3::prelude::*;
use std::path::{Path, PathBuf};
use std::process::Command;
use std::thread::sleep;
use std::time::Duration;
use clap::Parser;
use crate::mail_handler::mailer;
use crate::data_handler::{create_explog_file, create_time_stamp};
use std::env;


/// Get the current working directory.
fn get_current_dir() -> String{
    env::current_dir()
        .unwrap_or_else(|_| PathBuf::from("."))
        .to_str()
        .unwrap().to_string()
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
    /// Email address to recieve results
    #[arg(short, long)]
    email: Option<String>,
    /// Time delay in minutes before starting the experiment
    #[arg(short, long, default_value_t = 0)]
    delay: u64,
    // Number of times to loop the experiment
    #[arg(short, long, default_value_t = 1)]
    loops: u8,
    // Path to the python file containing the experimental setup
    #[arg(short, long)]
    path: PathBuf,
    // Target directory for output path 
    #[arg(short, long, default_value_t = get_current_dir())]
    output: String

}

#[pyfunction]
pub fn cli_parser() {
    // Initialises a temp file for writing experimental data to that can be accessed by other functions. 
    let temp_filename = ".exp_output.log";
    match create_explog_file(temp_filename) {
        Ok(_) => {},
        Err(e) => eprintln!("Error creating experimental logfile file: {}", e),
    }
    
    let original_args: Vec<String> = std::env::args().collect();

    let python_path: Option<&String> = original_args.iter().find(|arg| arg.contains("python"));

    let python_path_str = match python_path {
        Some(python_path) => python_path.clone(),
        None => "".to_string()};
    // println!("{}", python_path_str);
    // Filter out unwanted arguments
    let mut cleaned_args: Vec<String> = original_args
        .into_iter()
        .filter(|arg| !arg.contains("python")) // Filter out any argument containing "python"
        .collect();

    // Replace the first argument after cleaning with the actual cli tool name currently this is a place holder
    if let Some(first_arg_index) = cleaned_args.iter().position(|arg| !arg.starts_with('-')) {
        cleaned_args[first_arg_index] = "pfx".to_string();
    }

    // Parse the cleaned arguments using Clap
    let args = Args::parse_from(cleaned_args);

    // Call the python interp and and run the experiment as per additional args

    println!("Experiment starting in {} s", args.delay * 60);
    sleep(Duration::from_secs(&args.delay * 60));
    if !python_path_str.is_empty() {
        // Path to the Python script you want to execute
        let script_path = args.path;
        for _ in 0..args.loops {
            // Execute the Python script
            let output = Command::new(&python_path_str)
                .arg(&script_path)
                .output()
                .expect("Failed to execute Python script");

            // Handle the output
            if output.status.success() {
                let stdout = String::from_utf8_lossy(&output.stdout);
                println!("Script output:\n{}", stdout);
            } else {
                let stderr = String::from_utf8_lossy(&output.stderr);
                eprintln!("Script error:\n{}", stderr);
            }
            let output_path = resolve_path(Path::new(&args.output));
            println!("The output file directory is: {}", output_path.display());
            let filename = temp_filename.to_string(); //temp while working on file naming and creation and ensures email works but currently sends a blank file.
            let file_path = output_path.join(&filename);
            mailer(args.email.as_ref(), &file_path, &filename);
            
            
        }
    } else {
        eprintln!("No Python path found in the arguments");
    }
}


