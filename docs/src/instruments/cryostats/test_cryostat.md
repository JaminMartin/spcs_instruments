# Test_cryostat

`Test_cryostat` is a simulated cryostat for testing Rex workflows without
hardware. It returns temperature, stability, pressure, and magnetic-field
measurements with small random variation.

```toml
[device.Test_cryostat]
set_point = 3.0
desired_stability = 0.05
```

```python
from spcs_instruments import Test_cryostat

cryostat = Test_cryostat("config.toml")
cryostat.goto_setpoint(4.0)
cryostat.set_magneticfield(100.0)
readings = cryostat.measure()
```


## Methods

### setup_config



### measure



### goto_setpoint

**Signature:** `goto_setpoint(setpoint)`



### set_magneticfield

**Signature:** `set_magneticfield(strength)`



### get_cryostate



### get_magnetstate

