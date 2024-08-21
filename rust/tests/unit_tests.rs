// tests/basic_test.rs
use spcs_rust_utils::data_handler::Config;
use spcs_rust_utils::data_handler::{
    create_time_stamp, sanitize_filename, start_experiment, update_experiment_log, load_experimental_data,
};

use regex::Regex;
use std::collections::HashMap;
use std::fs;
use std::fs::File;
use std::io::Write;
use tempfile::NamedTempFile;

use toml::Value as TomlValue;
#[test]
fn test_create_time_stamp() {
    let timestamp = create_time_stamp(false);
    let re = Regex::new(r"^\d{2}-\d{2}-\d{4} \d{2}:\d{2}:\d{2}\.\d{3}$").unwrap();
    assert!(
        re.is_match(&timestamp),
        "Timestamp does not match expected format: {}",
        timestamp
    );

    let header_timestamp = create_time_stamp(true);
    let header_re = Regex::new(r"^\d{2}_\d{2}_\d{4}_\d{2}_\d{2}_\d{2}_\d{3}$").unwrap();
    assert!(
        header_re.is_match(&header_timestamp),
        "Header timestamp does not match expected format: {}",
        header_timestamp
    );
}

#[test]
fn test_sanitize_filename() {
    assert_eq!(sanitize_filename("file name"), "file_name");

    assert_eq!(sanitize_filename("file/name"), "file_name");

    assert_eq!(sanitize_filename("file / name"), "file___name");

    assert_eq!(sanitize_filename("filename"), "filename");

    assert_eq!(
        sanitize_filename("file / name / test"),
        "file___name___test"
    );
}

#[test]
fn test_start_experiment() {
    let mut temp_file = NamedTempFile::new().expect("Failed to create temp file");
    let toml_content = r#"
        [experiment.info]
        name = "Test User"
        email = "test@example.com"
        experiment_name = "Test Experiment"
        experiment_description = "This is a test."
    "#;
    temp_file
        .write_all(toml_content.as_bytes())
        .expect("Failed to write to temp file");

    let config_path = temp_file.path().to_str().unwrap().to_string();

    let result = start_experiment(config_path.clone());
    assert!(
        result.is_ok(),
        "start_experiment function failed: {:?}",
        result
    );

    let log_file_path = std::env::current_dir().unwrap().join(".exp_output.log");
    let log_content = fs::read_to_string(&log_file_path).expect("Failed to read log file");

    let updated_config: Config =
        toml::from_str(&log_content).expect("Failed to parse log file content");
    assert!(
        updated_config.experiment.start_time.is_some(),
        "start_time is not set in the log file"
    );

    fs::remove_file(log_file_path).expect("Failed to remove log file");
}

#[test]
fn test_update_experiment_log() {
    let log_file_path = std::env::current_dir().unwrap().join(".exp_output.log");

    let mut log_file = File::create(&log_file_path).expect("Failed to create log file");
    let toml_content = r#"
        [experiment]
        start_time = ""
        end_time = ""

        [experiment.info]
        name = "Test User"
        email = "test@example.com"
        experiment_name = "Test Experiment"
        experiment_description = "This is a test."

        [device.Fake_DAQ]
        gate_time = 1000
        averages = 40
    "#;
    log_file
        .write_all(toml_content.as_bytes())
        .expect("Failed to write to log file");

    // Create fake DAQ data with device table
    let mut inner_data = HashMap::new();
    inner_data.insert("sensor1".to_string(), vec![1.1, 2.2, 3.3]);
    inner_data.insert("sensor2".to_string(), vec![4.4, 5.5, 6.6]);

    let mut device_data = HashMap::new();
    device_data.insert("Fake_DAQ".to_string(), inner_data);

    let result = update_experiment_log(device_data.clone());
    assert!(
        result.is_ok(),
        "update_experiment_log function failed: {:?}",
        result
    );

    let log_content = fs::read_to_string(&log_file_path).expect("Failed to read log file");

    let updated_config: Config =
        toml::from_str(&log_content).expect("Failed to parse log file content");

    if let Some(TomlValue::Table(device_table)) = updated_config.unstructured.get("device") {
        if let Some(TomlValue::Table(fake_daq_table)) = device_table.get("Fake_DAQ") {
            if let Some(TomlValue::Table(data_table)) = fake_daq_table.get("data") {
                assert_eq!(
                    data_table.get("sensor1").unwrap(),
                    &TomlValue::Array(vec![
                        TomlValue::Float(1.1),
                        TomlValue::Float(2.2),
                        TomlValue::Float(3.3)
                    ])
                );
                assert_eq!(
                    data_table.get("sensor2").unwrap(),
                    &TomlValue::Array(vec![
                        TomlValue::Float(4.4),
                        TomlValue::Float(5.5),
                        TomlValue::Float(6.6)
                    ])
                );
            } else {
                panic!("Data table not found in Fake_DAQ.");
            }
        } else {
            panic!("Fake_DAQ not found in device table.");
        }
    } else {
        panic!("Device table not found in config.");
    }

    fs::remove_file(log_file_path).expect("Failed to remove log file");
}

#[test]
fn test_load_data() {
    // Write a sample TOML string for testing
    let toml_content = r#"
        [device.Test_DAQ.data]
        counts = [778.2368218901281, 6377.393470601288, 2316.8743649537096]
        voltage = [778.2368218901281, 6377.393470601288, 2316.8743649537096]
        "#;

    // Create a temporary file to store the TOML content
    let temp_file = "test_data.toml";
    std::fs::write(temp_file, toml_content).expect("Failed to write temporary TOML file");

    let data = load_experimental_data(temp_file);
    println!("data after func{:?}", data);
    std::fs::remove_file(temp_file).expect("Failed to delete temporary TOML file");

    println!("Loaded data: {:?}", data); // Debug print

    assert!(data.contains_key("Test_DAQ"), "Test_DAQ section not found in the data");
    let test_daq_data = data.get("Test_DAQ").expect("Missing Test_DAQ section");

    let counts = test_daq_data.get("counts").expect("Missing counts data");
    assert_eq!(
        counts,
        &vec![778.2368218901281, 6377.393470601288, 2316.8743649537096]
    );

    let voltage = test_daq_data.get("voltage").expect("Missing voltage data");
    assert_eq!(
        voltage,
        &vec![778.2368218901281, 6377.393470601288, 2316.8743649537096]
    );
}