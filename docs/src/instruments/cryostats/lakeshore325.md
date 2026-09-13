# Lake Shore 325

`Lakeshore325` adds Rex-compatible acquisition and temperature-setpoint control
for a Lake Shore Model 325 cryogenic temperature controller. It is a thin
adapter around QCoDeS' dedicated `LakeshoreModel325` driver, which manages the
Model 325's two sensor inputs, two heaters, PID, heater ranges, ramps, and
calibration curves. QCoDeS uses PyVISA for the Model 325's RS-232 or IEEE-488
resource.

```toml
[device.Lakeshore325]
# Example RS-232 resource. A GPIB resource such as GPIB0::12::INSTR also works.
visa_resource = "ASRL/dev/tty.usbserial::INSTR"
input_channel = "A"
control_loop = 1
timeout_seconds = 2.0
setpoint_tolerance_k = 0.1
stability_tolerance_k = 0.1
stability_readings = 3
stability_sample_interval_s = 1.0
```

```python
from spcs_instruments import Lakeshore325

controller = Lakeshore325("config.toml")
controller.go_to_temperature(4.2)
controller.set_heater_range(1)
readings = controller.measure()
controller.close()
```

`go_to_temperature()` updates the selected control-loop setpoint.
`is_at_setpoint()` compares the selected input with the current setpoint and
checks the configured stability window. The window contains
`stability_readings` samples separated by `stability_sample_interval_s`; it is
stable when its maximum temperature span is within `stability_tolerance_k`.
`measure()` records temperature, setpoint, and heater output.

See [`examples/lakeshore_325_setpoint_example.py`](../../../../examples/lakeshore_325_setpoint_example.py)
for a configured temperature sweep that measures a `Test_daq` once at each
stable setpoint.
