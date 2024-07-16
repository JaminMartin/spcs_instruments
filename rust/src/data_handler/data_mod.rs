use std::fs::File;
use std::io::prelude::*;
use std::io::Result;
use std::fs::OpenOptions;
use std::time::Instant;
use pyo3::prelude::*;

pub fn create_explog_file(filename: &str) -> Result<()> {
    // Define the TOML content
    let _file = File::create(filename)?;



    Ok(())
}

#[pyfunction]
pub fn start_experiment(config_path: String) -> PyResult<()> {
    // Open or create the log file
    println!("{}", config_path);
    let mut log_file = OpenOptions::new()
        .create(true)
        .write(true)
        .append(true)
        .open(".exp_output.temp")?;

    // Log the experiment start time
    let start_time = Instant::now();
    let start_time_formatted = start_time.elapsed().as_secs();
    writeln!(log_file, "Experiment started at {} seconds.", start_time_formatted)?;

    // Log experiment information from the configuration file
    writeln!(log_file, "Experiment information:")?;
    // let config = load_config(config_path)?;
    // for (header, contents) in config.iter() {
    //     writeln!(log_file, "{}:", header)?;
    //     for (key, value) in contents.iter() {
    //         writeln!(log_file, "  {} = {}", key, value)?;
    //     }
    //     writeln!(log_file)?;
    // }

    println!("Experiment started. Log file: {:?}", ".exp_output.temp");

    Ok(())
}




