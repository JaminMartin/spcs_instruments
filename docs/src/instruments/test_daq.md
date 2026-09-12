# Test_daq

`Test_daq` is a simulated measurement device for testing experiment control and
Rex payloads without hardware. `measure()` returns synthetic counts and
current; set `trace = true` to include synthetic time-series data.

```python
from spcs_instruments import Test_daq

daq = Test_daq("config.toml")
reading = daq.measure()
```


## Configuration

This class requires configuration in your `config.toml` file:


### Example Configuration

```toml

[device.Test_DAQ]
# Test_DAQ measurement configuration
# Step size in nm
gate_time = 0.1
# Start wavelength (nm)
averages = 500
# Sends mock time series data if set to True
trace = False
```


## Methods

### setup_config



### measure

