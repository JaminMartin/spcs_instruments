# SRS SR830 Lock-in

`SR830Lockin` is a Rex adapter around QCoDeS' SR830 driver. It applies the
reference, input, sensitivity, and filtering configuration once during
connection. `measure()` then performs a read-only coherent snapshot of X, Y,
R, and phase.

```toml
[device.SR830Lockin]
visa_resource = "GPIB0::8::INSTR"
timeout_seconds = 2.0

reference_source = "external"
phase_deg = 0.0
harmonic = 1
input_config = "a"
input_shield = "ground"
input_coupling = "AC"
notch_filter = "both"
sensitivity_v = 0.001
reserve = "normal"
time_constant_s = 0.3
filter_slope_db_per_octave = 24
sync_filter = "on"
settle_time_constants = 5
record_aux_inputs = false
```

For an internal reference, also set `frequency_hz` and `amplitude_v`.

```python
from spcs_instruments import SR830Lockin

lockin = SR830Lockin("config.toml")
lockin.wait_for_settle()
readings = lockin.measure()
lockin.close()
```

Call `wait_for_settle()` after changing phase, frequency, sensitivity, or time
constant. It waits the configured number of current time constants. The
explicit `auto_phase()`, `auto_gain()`, and `auto_reserve()` methods expose the
corresponding instrument routines without invoking them automatically.
