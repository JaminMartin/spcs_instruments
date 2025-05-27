# SiglentSDS2352XE

Class to create user-fiendly interface with the SiglentSDS2352X-E scope.
note! cursors must be on for this method to work!


## Configuration

This class requires configuration in your `config.toml` file:


### Example Configuration

```toml

[device.SIGLENT_Scope]
# SIGLENT_Scope measurement configuration
# Valid grating name to be used for the measurement, options: VIS, NIR, MIR
acquisition_mode = "AVERAGE"
# Number of averages to collect: 4, 16, 32, 64, 128, 256, 512, 1024
averages = 64
# Enable/Disable rolling averaging
reset_per = True
# Frequency of the trigger source to aproximate waiting x number off averages. The scope doesnt have a query to see if the number of averages has been reached
frquency = 5
# Desired measurement channel
channel = "c1"
# Return the area, or the full trace. Options: area, trace
data_type = "area"
```


## Methods

### setup_config



### measure



### close



### get_waveform

**Signature:** `get_waveform(channel)`



### measure_reset



### measure_basic


