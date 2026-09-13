# Taiko PDL M1

`TaikoPDLM1` controls a PicoQuant Taiko PDL M1 through the vendor-installed
Windows DLL. It identifies the driver by serial number, not by its temporary
USB slot, and reads the connected laser head's capabilities and calibration
limits at runtime.

The driver requires Windows and the DLLs installed by PicoQuant's Taiko
software. Point `dll_path` at `PDLM_Lib.dll`; its companion DLLs must remain in
the same installed directory. The Python interpreter architecture must match
the DLL architecture.

```python
from spcs_instruments import TaikoPDLM1

laser = TaikoPDLM1("config.toml")
reading = laser.measure()

laser.set_laser_mode("pulse")
laser.set_frequency(20_000_000)
laser.set_power_permille(100)
laser.shutdown()  # software-lock, then release the API connection
```

## Configuration

```toml
[device.TaikoPDLM1]
# Path to the vendor-installed Windows API DLL.
dll_path = "C:/Program Files/PicoQuant/Taiko/API/Win64/PDLM_Lib.dll"
# Persistent device identity, read from the Taiko or its software.
serial_number = "1234567"
```

`measure()` records system status, locking state, mode, frequency, calibrated
power setpoint, diode and case temperatures, and Taiko's estimated wavelength
when the head supports wavelength tuning. For a configured wavelength scan it
also records `desired wavelength (nm)`: the application-side calibration target
that appears after the first target is requested.

Use `set_software_lock(True)` as the programmatic safe-off action. The physical
interlock, keylock, and front-panel safety controls remain active. Prefer
`set_power_permille()` over absolute watts so a configuration remains sensible
when the connected laser head changes. Its argument is a fraction of the
head's calibrated maximum on a 0–1000 scale: `100` means 10%, not 100 W.

Wavelength tuning uses diode temperature. Taiko reports an estimated,
temperature-shifted wavelength based on the head calibration. Use
`set_target_temperature()` with a calibration for the attached head and confirm
the resulting wavelength through `measure()`.

## Optional wavelength scan calibration

Scanning requires a wavelength-tunable head and at least two measured,
strictly monotonic temperature-to-wavelength points:

```toml
[[device.TaikoPDLM1.wavelength_temperature_map]]
wavelength_nm = 979.8
temperature_c = 20.0

[[device.TaikoPDLM1.wavelength_temperature_map]]
wavelength_nm = 980.2
temperature_c = 22.0

temperature_tolerance_c = 0.1
wavelength_tolerance_nm = 0.1
stability_readings = 3
stability_sample_interval_s = 1.0
stability_max_samples = 120

[device.TaikoPDLM1.wavelength_scan]
start_wavelength_nm = 979.8
stop_wavelength_nm = 980.2
step_nm = 0.1
```

`scan_configured_wavelength_range()` uses the TOML start/stop/step range and
linearly interpolates the supplied map into wavelength/diode-temperature
targets. For a standard scan, use `move_to_next_wavelength()` followed by
`measure()`; the move method waits for the configured number of stable reads.
`is_at_desired_wavelength()` reports whether the current scan target is within
both configured temperature and estimated-wavelength tolerances. Its defaults
are 0.1 °C and 0.1 nm; all settling values are optional and may be overridden
in the TOML. `stability_max_samples` bounds the wait and raises `TimeoutError`
when exceeded. A Taiko head-change status clears the active wavelength scan
calibration. See
[`examples/taiko_pdl_m1_example.py`](../../../../examples/taiko_pdl_m1_example.py)
for a bounded monitoring and power-profile example.
