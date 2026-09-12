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
```

```python
from spcs_instruments import Lakeshore325

controller = Lakeshore325("config.toml")
controller.go_to_temperature(4.2)
# Enable a heater range only after checking the hardware configuration.
controller.set_heater_range(1)
readings = controller.measure()
controller.close()
```

The driver intentionally does not alter a setpoint or heater range during
connection. `measure()` returns temperature, setpoint, and heater-output
measurements; `is_at_setpoint(tolerance=0.1)` compares the selected input with
the current target.
