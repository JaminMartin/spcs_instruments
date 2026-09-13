# Keithley2400

`Keithley2400` discovers a connected Keithley 2400 SourceMeter through PyVISA,
configures a fixed current or voltage source, then reads voltage, current,
resistance, timestamp, and status on each call to `measure()`.

```toml
[device.Keithley2400.measurement]
# Source either current (CURR) or voltage (VOLT).
source_mode = "CURR"
current_range = 0.001
current_level = 0.0001

# Measure voltage (VOLT) or current (CURR).
sense_mode = "VOLT"
compliance_voltage = 10.0
measurevolt_range = 10.0
```

For voltage sourcing, replace the current-specific settings with:

```toml
[device.Keithley2400.measurement]
source_mode = "VOLT"
voltage_range = 10.0
voltage_level = 1.0
sense_mode = "CURR"
compliance_current = 0.001
measurecurrent_range = 0.001
```

The source level and range values are sent directly to the instrument, so use
the units and safe operating limits from the Keithley 2400 manual. The driver
enables the output only during `measure()` and turns it off immediately after
the reading.

> **Current behavior:** the instrument returns voltage and current in its native
> V and A units. The driver's measurement keys are presently labelled `mV` and
> `mA`, but it does not apply a scale conversion.

## Methods

### `configure_device()`

Applies the measurement configuration read from the TOML file.

### `measure()`

Returns the current voltage, current, resistance, timestamp, and status as Rex
measurements.

### `close()`

Closes the PyVISA instrument connection.
