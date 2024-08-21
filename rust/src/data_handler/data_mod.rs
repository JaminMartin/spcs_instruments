use pyo3::prelude::*;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs::{self, File, OpenOptions};
use std::io::Write;
use std::path::Path;
use time::macros::format_description;
use time::OffsetDateTime;
use toml::value::Table as TomlTable;
use toml::Value as TomlValue;

#[derive(Debug, Deserialize, Serialize)]
pub struct Experiment {
    pub start_time: Option<String>,
    pub end_time: Option<String>,
    pub info: ExperimentInfo,
}

#[derive(Debug, Deserialize, Serialize)]
pub struct ExperimentInfo {
    pub name: String,
    pub email: String,
    pub experiment_name: String,
    pub experiment_description: String,
}

#[derive(Debug, Deserialize, Serialize)]
pub struct Config {
    pub experiment: Experiment,
    #[serde(flatten)]
    pub unstructured: HashMap<String, toml::Value>,
}

pub fn sanitize_filename(name: &str) -> String {
    name.replace([' ', '/'], "_")
}

fn toml_parse_read(toml_content: String) -> Result<Config, Box<dyn std::error::Error>> {
    let config: Config = toml::from_str(&toml_content)?;
    Ok(config)
}

pub fn process_output(
    output_path: &Path,
    file_name_suffix: &String,
) -> Result<String, Box<dyn std::error::Error>> {
    let current_dir = std::env::current_dir()?;
    let log_file_path = current_dir.join(".exp_output.log");

    let toml_content = fs::read_to_string(log_file_path)?;
    let mut config: Config = toml::from_str(&toml_content)?;
    let endtime_stamp = create_time_stamp(false);
    config.experiment.end_time = Some(endtime_stamp);
    let sanitized_file_name = sanitize_filename(&config.experiment.info.experiment_name);
    let output_file_name = format!(
        "{}/{}_{}.toml",
        output_path.to_string_lossy(),
        sanitized_file_name,
        &file_name_suffix
    );
    let mut output_file = OpenOptions::new()
        .create(true)
        .append(true)
        .open(output_file_name)?;

    toml_parse_write(&config, &mut output_file)?;

    let output_file_name = format!("{}_{}.toml", sanitized_file_name, &file_name_suffix);

    let file_name = ".exp_output.log";

    match fs::remove_file(file_name) {
        Ok(_) => {}
        Err(e) => println!("Failed to delete file '{}': {}", file_name, e),
    }

    drop(output_file);
    Ok(output_file_name)
}

fn toml_parse_write(config: &Config, file: &mut File) -> Result<(), Box<dyn std::error::Error>> {
    let toml_string = toml::to_string(&config)?;
    file.write_all(toml_string.as_bytes())?;
    Ok(())
}
pub fn create_time_stamp(header: bool) -> String {
    let now = OffsetDateTime::now_local().unwrap_or_else(|_| OffsetDateTime::now_utc());
    let format_file = match header {
        false => format_description!(
            "[day]-[month]-[year] [hour repr:24]:[minute]:[second].[subsecond digits:3]"
        ),
        true => format_description!(
            "[day]_[month]_[year]_[hour repr:24]_[minute]_[second]_[subsecond digits:3]"
        ),
    };

    now.format(&format_file).unwrap()
}

pub fn create_explog_file(filename: &str) -> Result<(), Box<dyn std::error::Error>> {
    let _file = File::create(filename)?;
    Ok(())
}

#[pyfunction]
pub fn start_experiment(config_path: String) -> PyResult<()> {
    let toml_content = fs::read_to_string(config_path)?;

    let mut config = match toml_parse_read(toml_content) {
        Ok(v) => v,
        Err(v) => {
            println!("failed to parse toml data due to {}", v);
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                "failed to parse toml data due to {}",
                v
            )));
        }
    };

    let current_dir = std::env::current_dir()?;
    let log_file_path = current_dir.join(".exp_output.log");
    let mut log_file = OpenOptions::new()
        .create(true)
        .append(true)
        .open(log_file_path)?;
    let time_stamp = create_time_stamp(false);

    config.experiment.start_time = Some(time_stamp);

    match toml_parse_write(&config, &mut log_file) {
        Ok(_) => {}
        Err(v) => {
            println!("failed to write toml file due to {}", v);
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                "failed to write toml log file due to {}",
                v
            )));
        }
    }

    drop(log_file);
    Ok(())
}

fn update_toml_with_data(
    instrument_name: String,
    daq_data: HashMap<String, Vec<f64>>,
) -> Result<(), Box<dyn std::error::Error>> {
    let current_dir = std::env::current_dir()?;
    let log_file_path = current_dir.join(".exp_output.log");

    let toml_content = fs::read_to_string(&log_file_path)?;
    let mut config: Config = toml::from_str(&toml_content)?;

    // Navigate to the `device` table
    let device_table = config
        .unstructured
        .entry("device".to_string())
        .or_insert_with(|| TomlValue::Table(TomlTable::new()));

    if let TomlValue::Table(device_table) = device_table {
        // Navigate to the specific device entry
        let devices = device_table
            .entry(instrument_name.to_string())
            .or_insert_with(|| TomlValue::Table(TomlTable::new()));

        if let TomlValue::Table(table) = devices {
            // Update or create the `data` table
            let data_table = table
                .entry("data".to_string())
                .or_insert_with(|| TomlValue::Table(TomlTable::new()));

            if let TomlValue::Table(data_table) = data_table {
                for (key, value) in &daq_data {
                    let value_array: Vec<TomlValue> =
                        value.iter().map(|&x| TomlValue::Float(x)).collect();
                    data_table.insert(key.clone(), TomlValue::Array(value_array));
                }
            }
        }
    }

    let mut log_file = OpenOptions::new()
        .read(true)
        .write(true)
        .append(false)
        .open(&log_file_path)?;

    toml_parse_write(&config, &mut log_file)?;

    drop(log_file);

    Ok(())
}

#[pyfunction]
pub fn update_experiment_log(daq_data: HashMap<String, HashMap<String, Vec<f64>>>) -> PyResult<()> {
    for (key, value) in daq_data {
        match update_toml_with_data(key, value) {
            Ok(_) => {}
            Err(v) => {
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                    "Failed to write toml log file due to {}",
                    v
                )));
            }
        }
    }

    Ok(())
}
