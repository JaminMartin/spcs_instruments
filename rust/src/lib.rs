use clap::Parser;
use pyo3::prelude::*;

/// Simple program to greet a person
#[derive(Parser, Debug)]
#[command(version, about, long_about = None)]
struct Args {
    /// Name of the person to greet
    #[arg(short, long)]
    name: String,

    /// Number of times to greet
    #[arg(short, long, default_value_t = 1)]
    count: u8,
}

#[pyfunction]
pub fn cli_parser() {
    // Get original arguments
    let original_args: Vec<String> = std::env::args().collect();
    println!("Original arguments: {:?}", original_args);

    // Filter out unwanted arguments
    let mut cleaned_args: Vec<String> = original_args.into_iter()
        .filter(|arg| !arg.contains("python"))  // Filter out any argument containing "python"
        .collect();
    println!("Cleaned arguments: {:?}", cleaned_args);

    // Replace the first argument after cleaning
    if let Some(first_arg_index) = cleaned_args.iter().position(|arg| !arg.starts_with('-')) {
        cleaned_args[first_arg_index] = "cake".to_string();
    }

    // Parse the cleaned arguments using Clap
    let args = Args::parse_from(cleaned_args);
    println!("Parsed arguments: {:?}", args);

    // Print greetings based on parsed arguments
    for _ in 0..args.count {
        println!("Hello {}!", args.name);
    }
}

#[pymodule]
fn spcs_cli(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(cli_parser, m)?)?;
    Ok(())
}
