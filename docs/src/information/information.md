# Information

## Adding a local driver

An instrument does not need to be included in this package before it can be
used in an experiment. Add its module directory to Python's import path, import
the driver in the experiment script, and use the same Rex-compatible calling
pattern.

```python
import sys

sys.path.append("/path/to/local/instruments")
import my_instruments


device = my_instruments.MyDevice("config.toml")
```

A compatible driver should accept a configuration path and a unique name, and
expose an operation such as `measure()`, `set_*()`, or `go_to_*()`. A
measurement driver should return its values and record them as Rex
`Measurement` objects before creating the payload.

## Developing this package

Create a local environment with `uv sync`, then run tests with `uv run pytest`.
New public drivers belong under `src/spcs_instruments/instruments/`, must be
re-exported through the package `__init__.py` files, and should include a
configuration template, documentation page, and focused test.

Rex is installed as a standalone package, so Rust is not required for ordinary
driver development. Rust tooling is only needed when working on Rex itself.
