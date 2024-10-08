pub mod cli_tool;
pub mod data_handler;
pub mod mail_handler;
use pyo3::prelude::*;

use cli_tool::cli_parser;
use data_handler::{load_experimental_data, start_experiment, update_experiment_log};

#[pymodule]
pub fn pyfex(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(cli_parser, m)?)?;
    m.add_function(wrap_pyfunction!(start_experiment, m)?)?;
    m.add_function(wrap_pyfunction!(update_experiment_log, m)?)?;
    m.add_function(wrap_pyfunction!(load_experimental_data, m)?)?;
    Ok(())
}
