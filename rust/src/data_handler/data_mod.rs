use dirs::config_dir;
use pyo3::prelude::*;
use serde::{Deserialize, Serialize};
use std::collections::hash_map::Entry;
use std::collections::HashMap;
use std::env;
use std::fs;
use std::io::{self};
use time::macros::format_description;
use time::OffsetDateTime;
use toml::{Table, Value};
#[derive(Debug, Serialize, Deserialize)]
pub struct Configuration {
    pub email_server: Option<EmailServer>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct EmailServer {
    pub server: String,
    pub security: bool,
    pub username: Option<String>,
    pub password: Option<String>,
    pub port: Option<String>,
    pub from_address: String,
}
#[derive(Debug, Serialize, Deserialize)]
pub enum Entity {
    Device(Device),
    ExperimentSetup(Experiment),
}

#[derive(Debug, Serialize, Deserialize)]
pub struct Listner {
    pub name: String,
    pub id: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct Experiment {
    pub start_time: Option<String>,
    pub end_time: Option<String>,
    pub info: ExperimentInfo,
}

impl Experiment {
    pub fn new(info: ExperimentInfo) -> Self {
        Experiment {
            start_time: Some(create_time_stamp(false)),
            end_time: None,
            info,
        }
    }
    fn append_end_time(&mut self) {
        self.end_time = Some(create_time_stamp(false));
    }
}
impl Default for Experiment {
    fn default() -> Self {
        Experiment {
            start_time: Some(create_time_stamp(false)),
            end_time: None,
            info: ExperimentInfo::default(),
        }
    }
}

#[derive(Debug, Serialize, Deserialize, Default)]
pub struct ExperimentInfo {
    pub name: String,
    pub email: String,
    pub experiment_name: String,
    pub experiment_description: String,
}
#[derive(Debug, Serialize, Deserialize)]
#[serde(untagged)]
pub enum MeasurementData {
    Single(Vec<f64>),
    Multi(Vec<Vec<f64>>),
}
impl IntoPy<PyObject> for MeasurementData {
    fn into_py(self, py: Python<'_>) -> PyObject {
        match self {
            MeasurementData::Single(values) => values.into_py(py),
            MeasurementData::Multi(arrays) => arrays.into_py(py),
        }
    }
}
#[derive(Debug, Serialize, Deserialize)]
pub struct Device {
    pub device_name: String,
    pub device_config: HashMap<String, Value>,
    pub measurements: HashMap<String, MeasurementData>,
}
#[derive(Debug, Serialize, Deserialize)]
pub struct DeviceData {
    pub device_name: String,
    pub measurements: HashMap<String, Vec<f64>>,
}
impl Device {
    fn update(&mut self, other: Self) {
        for (measure_type, values) in other.measurements {
            match self.measurements.entry(measure_type) {
                Entry::Occupied(mut entry) => match (entry.get_mut(), &values) {
                    (MeasurementData::Single(existing), MeasurementData::Single(new_values)) => {
                        existing.extend(new_values.clone());
                    }
                    (MeasurementData::Multi(existing), MeasurementData::Multi(new_values)) => {
                        existing.extend(new_values.clone());
                    }
                    _ => {
                        log::error!("Measurement type mismatch during update for '{}' - cannot change between Single and Multi variants", entry.key());
                    }
                },
                Entry::Vacant(entry) => {
                    entry.insert(values);
                }
            }
        }
    }
    fn latest_data_truncated(&self, max_measurements: usize) -> DeviceData {
        let truncated_measurements = self
            .measurements
            .iter()
            .map(|(key, values)| {
                let truncated = match values {
                    MeasurementData::Single(single_values) => single_values
                        .iter()
                        .rev()
                        .take(max_measurements)
                        .cloned()
                        .collect::<Vec<f64>>()
                        .into_iter()
                        .rev()
                        .collect(),
                    MeasurementData::Multi(multi_values) => {
                        if let Some(latest_array) = multi_values.last() {
                            match latest_array.len() {
                                0..=100 => latest_array.clone(),
                                _ => {
                                    let chunk_size = div_ceil(latest_array.len(), 100);
                                    latest_array
                                        .chunks(chunk_size)
                                        .map(|chunk| chunk.iter().sum::<f64>() / chunk.len() as f64)
                                        .collect()
                                }
                            }
                        } else {
                            Vec::new()
                        }
                    }
                };
                (key.clone(), truncated)
            })
            .collect();

        DeviceData {
            device_name: self.device_name.clone(),
            measurements: truncated_measurements,
        }
    }

    pub fn truncate(&mut self) {
        self.measurements
            .iter_mut()
            .for_each(|(_, values)| match values {
                MeasurementData::Single(single_values) => {
                    let len = single_values.len();
                    if len > 100 {
                        single_values.drain(0..len - 100);
                    }
                }
                MeasurementData::Multi(multi_values) => {
                    let len_before = multi_values.len();
                    if len_before > 1 {
                        let last = multi_values.pop();
                        multi_values.clear();
                        if let Some(last) = last {
                            multi_values.push(last);
                        }
                    }
                }
            });
    }
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ServerState {
    pub entities: HashMap<String, Entity>,
    pub internal_state: bool,
    pub retention: bool,
}

impl ServerState {
    pub fn new() -> Self {
        ServerState {
            entities: HashMap::new(),
            internal_state: true,
            retention: true,
        }
    }

    pub fn update_entity(&mut self, key: String, incoming: Entity) {
        match incoming {
            Entity::Device(incoming_device) => match self.entities.entry(key) {
                Entry::Occupied(mut entry) => {
                    if let Entity::Device(existing_device) = entry.get_mut() {
                        existing_device.update(incoming_device);
                    }
                }
                Entry::Vacant(entry) => {
                    entry.insert(Entity::Device(incoming_device));
                }
            },
            Entity::ExperimentSetup(experiment_setup) => match self.entities.entry(key) {
                Entry::Vacant(entry) => {
                    let experiment = Experiment::new(experiment_setup.info);
                    entry.insert(Entity::ExperimentSetup(experiment));
                }
                Entry::Occupied(_) => {
                    log::warn!("Can't create multiple experiments: ignoring");
                }
            },
        }
        if self.retention == false {
            self.truncate_data();
        };
    }
    pub fn truncate_data(&mut self) {
        for (_, value) in &mut self.entities {
            match value {
                Entity::Device(device_data) => {
                    device_data.truncate();
                }
                Entity::ExperimentSetup(_) => {}
            }
        }
    }
    pub fn finalise_time(&mut self) {
        for entity in self.entities.values_mut() {
            if let Entity::ExperimentSetup(experiment) = entity {
                experiment.append_end_time()
            }
        }
    }

    pub fn print_state(&self) {
        log::info!("=== Current Server State ===");
        if self.entities.is_empty() {
            log::info!("No devices connected.");
            return;
        }

        for entity in self.entities.values() {
            match entity {
                Entity::Device(device) => {
                    let total_measurements: usize = device
                        .measurements
                        .values()
                        .map(|v| match v {
                            MeasurementData::Single(data) => data.len(),
                            MeasurementData::Multi(data) => data.len(),
                        })
                        .sum();

                    let last_measurement = device
                        .measurements
                        .values()
                        .flat_map(|v| match v {
                            MeasurementData::Single(data) => vec![data.last().cloned()],
                            MeasurementData::Multi(data) => {
                                vec![data.last().and_then(|inner| inner.last().cloned())]
                            }
                        })
                        .flatten()
                        .last();

                    log::info!(
                        "Device: {} - Total measurements: {}, Last measurement: {:?}",
                        device.device_name,
                        total_measurements,
                        last_measurement
                    );
                }
                Entity::ExperimentSetup(_experiment) => {}
            }
        }
        log::info!("========================\n");
    }

    pub fn dump_to_toml(&self, file_path: &String) -> io::Result<()> {
        let mut root = Table::new();

        for (key, entity) in &self.entities {
            match entity {
                Entity::ExperimentSetup(exeperimentsetup) => {
                    if !root.contains_key("experiment") {
                        root.insert("experiment".to_string(), Value::Table(Table::new()));
                    }

                    let experiment_table = root
                        .get_mut("experiment")
                        .and_then(|v| v.as_table_mut())
                        .unwrap();
                    experiment_table.insert(
                        "start_time".to_string(),
                        Value::String(exeperimentsetup.start_time.clone().unwrap_or_default()),
                    );
                    experiment_table.insert(
                        "end_time".to_string(),
                        Value::String(exeperimentsetup.end_time.clone().unwrap_or_default()),
                    );
                    let mut experiment_config = Table::new();

                    experiment_config.insert(
                        "name".to_string(),
                        Value::String(exeperimentsetup.info.name.clone()),
                    );
                    experiment_config.insert(
                        "email".to_string(),
                        Value::String(exeperimentsetup.info.email.clone()),
                    );

                    experiment_config.insert(
                        "experiment_name".to_string(),
                        Value::String(exeperimentsetup.info.experiment_name.clone()),
                    );
                    experiment_config.insert(
                        "experiment_description".to_string(),
                        Value::String(exeperimentsetup.info.experiment_description.clone()),
                    );

                    experiment_table.insert("info".to_string(), Value::Table(experiment_config));
                }

                Entity::Device(device) => {
                    if !root.contains_key("device") {
                        root.insert("device".to_string(), Value::Table(Table::new()));
                    }

                    let device_table = root
                        .get_mut("device")
                        .and_then(|v| v.as_table_mut())
                        .unwrap();

                    let mut device_config = Table::new();
                    device_config.insert(
                        "device_name".to_string(),
                        Value::String(device.device_name.clone()),
                    );

                    for (config_key, config_value) in &device.device_config {
                        device_config.insert(config_key.clone(), config_value.clone());
                    }

                    let mut data_table = Table::new();
                    for (measurement_type, values) in &device.measurements {
                        match values {
                            MeasurementData::Single(single_values) => {
                                data_table.insert(
                                    measurement_type.clone(),
                                    Value::Array(
                                        single_values.iter().map(|&v| Value::Float(v)).collect(),
                                    ),
                                );
                            }
                            MeasurementData::Multi(multi_values) => {
                                let nested_arrays: Vec<Value> = multi_values
                                    .iter()
                                    .map(|inner_vec| {
                                        Value::Array(
                                            inner_vec.iter().map(|&v| Value::Float(v)).collect(),
                                        )
                                    })
                                    .collect();

                                data_table
                                    .insert(measurement_type.clone(), Value::Array(nested_arrays));
                            }
                        }
                    }

                    device_config.insert("data".to_string(), Value::Table(data_table));

                    device_table.insert(key.clone(), Value::Table(device_config));
                }
            }
        }
        let toml_string = toml::to_string_pretty(&root)
            .map_err(|e| io::Error::new(io::ErrorKind::Other, e.to_string()))?;
        fs::write(file_path, toml_string.clone())?;
        let tmp_dir = env::temp_dir();
        let temp_path = tmp_dir.join("pyfex.toml");
        fs::write(&temp_path, toml_string)?;
        Ok(())
    }
    pub fn get_experiment_name(&self) -> Option<String> {
        self.entities.values().find_map(|entity| {
            if let Entity::ExperimentSetup(experiment) = entity {
                Some(experiment.info.experiment_name.clone())
            } else {
                None
            }
        })
    }
    pub fn validate(&self) -> io::Result<()> {
        log::trace!("Validating state, entities: {:?}", self.entities);

        let has_experiment_setup = self
            .entities
            .values()
            .any(|entity| matches!(entity, Entity::ExperimentSetup(_)));
        if !has_experiment_setup {
            return Err(io::Error::new(
                io::ErrorKind::InvalidData,
                "No entity of type ExperimentSetup found",
            ));
        }
        Ok(())
    }

    pub fn send_stream(&self) -> HashMap<String, DeviceData> {
        let mut stream_contents = HashMap::new();
        for entity in self.entities.values() {
            match entity {
                Entity::Device(device) => {
                    stream_contents.insert(
                        device.device_name.clone(),
                        device.latest_data_truncated(100),
                    );
                }
                Entity::ExperimentSetup(_experiment) => {}
            }
        }
        stream_contents
    }
}

impl Default for ServerState {
    fn default() -> Self {
        Self::new()
    }
}
pub fn sanitize_filename(name: String) -> String {
    name.replace([' ', '/'], "_")
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

#[pyfunction]
pub fn load_experimental_data(filename: &str) -> HashMap<String, HashMap<String, MeasurementData>> {
    let content = fs::read_to_string(filename).expect("Failed to read the TOML file");
    let toml_data: Value = content.parse().expect("Failed to parse the TOML file");
    let mut data_dict = HashMap::new();

    if let Value::Table(table) = toml_data {
        if let Some(Value::Table(devices)) = table.get("device") {
            for (device_name, device_content) in devices {
                if let Value::Table(inner_table) = device_content {
                    if let Some(Value::Table(data_table)) = inner_table.get("data") {
                        let mut data_map = HashMap::new();
                        for (key, value) in data_table {
                            if let Value::Array(outer_array) = value {
                                // Check if we have a nested array structure
                                if !outer_array.is_empty() && outer_array[0].is_array() {
                                    // Handle nested arrays (Multi case)
                                    let nested_data: Vec<Vec<f64>> = outer_array
                                        .iter()
                                        .filter_map(|inner_val| {
                                            if let Value::Array(inner_array) = inner_val {
                                                let inner_vec: Vec<f64> = inner_array
                                                    .iter()
                                                    .filter_map(|v| v.as_float())
                                                    .collect();
                                                if !inner_vec.is_empty() {
                                                    Some(inner_vec)
                                                } else {
                                                    None
                                                }
                                            } else {
                                                None
                                            }
                                        })
                                        .collect();
                                    data_map
                                        .insert(key.clone(), MeasurementData::Multi(nested_data));
                                } else {
                                    // Handle flat arrays (Single case)
                                    let data_array: Vec<f64> =
                                        outer_array.iter().filter_map(|v| v.as_float()).collect();
                                    data_map
                                        .insert(key.clone(), MeasurementData::Single(data_array));
                                }
                            }
                        }
                        data_dict.insert(device_name.clone(), data_map);
                    }
                }
            }
        }
    }

    data_dict
}
fn div_ceil(a: usize, b: usize) -> usize {
    (a + b - 1) / b
}

pub fn get_configuration() -> Result<Configuration, String> {
    let config_path = config_dir()
        .map(|mut path| {
            path.push("pyfex");
            path.push("config.toml");
            path
        })
        .ok_or("Failed to get config directory, setup your config directory then run pyfex");

    let conf = match config_path {
        Ok(path) => path,
        Err(res) => {
            log::error!("{}", res);
            return Err(res.to_string());
        }
    };
    let config_contents = fs::read_to_string(conf);

    let contents: Configuration = match config_contents {
        Ok(contents) => toml::from_str(&contents).expect("Unable to parse config.toml"),
        Err(e) => {
            log::error!(
                "Could not read config.toml file, raised the following error: {}",
                e
            );
            return Err(e.to_string());
        }
    };
    log::debug!("{:?}", contents);
    Ok(contents)
}
