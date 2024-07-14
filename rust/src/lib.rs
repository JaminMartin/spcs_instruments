use clap::Parser;
use pyo3::prelude::*;
use std::path::PathBuf;
use std::process::Command;

/// A commandline experiment manager for SPCS-Instruments
#[derive(Parser, Debug)]
#[command(version, about, long_about = None)]
struct Args {
    /// Email address to recieve results
    #[arg(short, long)]
    email: Option<String>,
    /// Time delay in minutes before starting the experiment
    #[arg(short, long, default_value_t = 0)]
    delay: u8,
    // Number of times to loop the experiment
    #[arg(short, long, default_value_t = 1)]
    loops: u8,
    // Path to the python file containing the experimental setup
    #[arg(short, long)]
    path: PathBuf,
}

#[pyfunction]
pub fn cli_parser() {
    let original_args: Vec<String> = std::env::args().collect();
    // For debuging purposes to see what arguments python injects
    // Get original arguments
    // println!("Original arguments: {:?}", original_args);
    let python_path: Option<&String> = original_args.iter().find(|arg| arg.contains("python"));
    let python_path_str = python_path
        .map(|s| s.clone())
        .unwrap_or_else(|| "".to_string());
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

    // Print greetings based on parsed arguments
    if !python_path_str.is_empty() {
        // Path to the Python script you want to execute
        let script_path = args.path;

        // Execute the Python script
        let output = Command::new(&python_path_str)
            .arg(script_path)
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
    } else {
        eprintln!("No Python path found in the arguments");
    }
}

#[pymodule]
fn spcs_cli(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(cli_parser, m)?)?;
    Ok(())
}
