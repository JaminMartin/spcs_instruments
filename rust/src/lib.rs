use pyo3::prelude::*;

#[pyfunction]
pub fn adder(a: i32, b: i32) -> PyResult<i32> {
    let mut result = a + b;
    Ok(result)
}

#[pymodule]
fn _spcs_cli(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(adder, m)?)?;
    Ok(())
}
