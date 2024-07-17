use std::fs::File;
use std::io::prelude::*;
use std::fs::OpenOptions;
use pyo3::prelude::*;
use time::OffsetDateTime;
use time::macros::format_description;
use std::collections::HashMap;
use serde::{Deserialize, Serialize};
use std::fs;
use std::io::Write;

#[derive(Debug, Deserialize, Serialize)]
struct Experiment {
    start_time: Option<String>,
    info: ExperimentInfo,
}

#[derive(Debug, Deserialize, Serialize)]
struct ExperimentInfo {
    name: String,
    email: String,
    experiment_name: String,
    experiment_description: String,
}

#[derive(Debug, Deserialize, Serialize)]
struct Config {
    experiment: Experiment,
    #[serde(flatten)]
    unstructured: HashMap<String, toml::Value>,
}


fn toml_parse_read(toml_content: String) -> Result<Config, Box<dyn std::error::Error>> {
    // Read the TOML file

    // Parse the TOML content
    let config: Config = toml::from_str(&toml_content)?;
    Ok(config)
}

// Place holder
// fn toml_parse_write() {
//     let toml_string = toml::to_string(&config)?;
//     let mut file = fs::File::create("output.toml")?;
//     file.write_all(toml_string.as_bytes())?;   
// }
pub fn create_time_stamp(header: bool) -> String {
    let now = OffsetDateTime::now_utc();
    let format_file = match header {
    false  => format_description!("[day]-[month]-[year] [hour repr:24]:[minute]:[second].[subsecond digits:3]"),
    true => format_description!("[day][month][year][hour repr:24][minute][second][subsecond digits:3]")};


    let formatted = now.format(&format_file).unwrap();

    formatted
}

pub fn create_explog_file(filename: &str) -> Result<(), Box<dyn std::error::Error>> {
    // Define the TOML content
    let _file = File::create(filename)?;
    Ok(())
}

#[pyfunction]
pub fn start_experiment(config_path: String) -> PyResult<()> {
    // Open or create the log file
    let toml_content = fs::read_to_string(config_path)?;
    let config = toml_parse_read(toml_content);

    let mut log_file = OpenOptions::new()
        .create(false)
        .write(true)
        .append(true)
        .open(".exp_output.temp")?;

    // Log the experiment start time
    let time_stamp = create_time_stamp(false);

    let toml_time = format!(
        "[Experiment]\nstarted_at = \"{}\"\n",
        time_stamp
    );
    writeln!(log_file, "{toml_time}")?;

    Ok(())
}




