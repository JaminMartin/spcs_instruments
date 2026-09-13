# Configuration

Each experiment uses a TOML file for reproducible metadata and device settings.
The experiment function receives its path and passes it to every driver.

```toml
[experiment.info]
name = "Jane Doe"
email = "jane@example.edu"
experiment_name = "Temperature sweep"
experiment_description = "Measure a sample during a controlled temperature sweep."

[device.Test_DAQ]
gate_time = 0.1
averages = 64
trace = false
```

The device section name must match the driver name. For example,
`Test_daq(config_path)` reads `[device.Test_DAQ]`, while a custom instance name
is declared and used consistently:

```toml
[device.daq_reference]
gate_time = 0.1
averages = 64
trace = false

[device.daq_signal]
gate_time = 0.5
averages = 128
trace = false
```

```python
reference = spcs.Test_daq(config_path, name="daq_reference")
signal = spcs.Test_daq(config_path, name="daq_signal")
```

Drivers may use nested tables for device-specific settings. Consult the
individual driver page for the exact keys, valid values, units, and safety
constraints. Rex can supply a configuration path at runtime with `rex run -c
other-config.toml`, avoiding changes to the experiment script.
