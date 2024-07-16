use std::fs::File;
use std::io::prelude::*;
use std::io::Result;
use std::fs::OpenOptions;
use pyo3::prelude::*;
use time::OffsetDateTime;
use time::macros::format_description;
use serde::Deserialize;
use std::collections::HashMap;





pub fn create_time_stamp() -> String {
    let now = OffsetDateTime::now_utc();
    let format_file = format_description!("[day]-[month]-[year] [hour repr:24]:[minute]:[second].[subsecond digits:3]");
    let formatted = now.format(&format_file).unwrap();
    // let format_name_default = format_description!("[day][month][year][hour repr:24][minute][second][subsecond digits:3]");
    // let formated_file_name = now.format(&format_name_default).unwrap();
    formatted
}

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
    let time_stamp = create_time_stamp();

    let toml_time = format!(
        "[Experiment]\nstarted_at = \"{}\"\n",
        time_stamp
    );
    writeln!(log_file, "{toml_time}")?;

    // Log experiment information from the configuration file
    // let config = load_config(config_path)?;
    // for (header, contents) in config.iter() {
    //     writeln!(log_file, "{}:", header)?;
    //     for (key, value) in contents.iter() {
    //         writeln!(log_file, "  {} = {}", key, value)?;
    //     }
    //     writeln!(log_file)?;
    // }


    Ok(())
}




