pub mod cli_tool;
pub mod data_handler;
pub mod mail_handler;
pub mod tcp_handler;
pub mod tui_tool;
use pyo3::prelude::*;

use cli_tool::{cli_parser, cli_standalone};
use data_handler::load_experimental_data;

#[pymodule]
pub fn pyfex(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(cli_parser, m)?)?;
    m.add_function(wrap_pyfunction!(cli_standalone, m)?)?;
    m.add_function(wrap_pyfunction!(load_experimental_data, m)?)?;
    Ok(())
}
