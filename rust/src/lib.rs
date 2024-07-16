pub mod cli_tool;
pub mod mail_handler;
pub mod data_handler;
use pyo3::prelude::*;

use cli_tool::cli_parser;
use data_handler::start_experiment;

#[pymodule]
pub fn spcs_rust_utils(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(cli_parser, m)?)?;
    m.add_function(wrap_pyfunction!(start_experiment, m)?)?;
    Ok(())
}