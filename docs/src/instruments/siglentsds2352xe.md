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

Setup function for the oscilliscope



### measure

High level measurement API, calls into measure_sample or measure_trace depending on device configuration.



### close

Releases the device.



### get_waveform

**Signature:** `get_waveform(channel)`

Mostly vendor provided function to return the waveform from the oscilisope. 



### measure_sample

Returns a single value (voltage) based on the area under the transient. Makes assumption that data is either all negative voltages, or that the signal voltage is more positive than the baseline voltage.
In the case the baseline voltage is positive and the signal voltage is more negative, your results may appear inverted. Standard practice is to ensure your baseline voltage and signal voltage is either all positive or all negative for this to work reliably.

Args: Self
Returns: float64



### measure_trace

Returns the entire trace/waveform from the osciliscope, where t=0 is defined by the x1 cursor. 
Args: Self
Returns: tuple (time: NDarray f64, voltage: NDarray f64)


