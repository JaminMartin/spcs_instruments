# DPO7104_TekTronix_scope

Driver for the Tektronix DPO7104 oscilloscope over GPIB using PyVISA.

This class manages instrument connection, configuration, gated area integration, waveform
capture, and optional forwarding of measurement payloads to a Rex server.

The driver supports averaged acquisitions, cursor-based gated area measurements on CH1,
raw voltage waveform downloads for CH1 and CH2, and limited trigger setup on CH2. Time axis 
must be reconstructed from saved parameters. 

KNOWN FOOTGUNS:
- Waveform downloads can be slow, massive and may cause the scope's CPU to struggle, or even overfill the computer storage.
    Used the samples_saved config to reduce the amount saved.
- Area measurement pulled from the scope vs area calculated from the pulled waveform can differ if the first 
    cursor is <1.0e-7s or negative, relative to the trigger. This is only an issue if you are setting the cursor 
    tiny and then trying to compare the area measurement to a calculated area from the waveform, if you are just 
    using the area measurement as a relative metric, such as for emission scans, then this is not a problem.
- This driver assumes a negative-going output and inverts the area measurement accordingly, if you are have  
    a positive signal you will need to multiply the area by -1 to get the correct polarity. Beware of waveforms
    that have significant positive and negative components, as the area measurement may not reflect the full area of 
    the pulse in this case.
- The SCOPE_ADDRESS and RESOURCE_MANAGER may need to be adjusted depending on your specific GPIB connection. 
- If you do not know the strongest transition to maunally set the vertical scale for, you can run a quick emission scan and
    look at the CH1 waveform (on the scope) to find the max peak, then set the vertical scale so that this peak fills
    the screen, this will hopefully ensure all peaks are relative and do not go offscreen.


## Attributes

### state (int)

Measurement cycle counter.

### connect_to_rex (bool)

Whether to forward payloads to a Rex server link.

### sock (socket | None)

TCP socket used for Rex forwarding.

### scope

PyVISA resource for the connected oscilloscope.

### measurements (dict)

Stored Measurement objects for area, waveform, trigger, and timing.

### averages (int)

Number of waveform acquisitions to average.

### start_bound (float)

Left cursor position relative to the trigger.

### end_bound (float)

Right cursor position relative to the trigger.

### area_enabled (bool)

Whether gated area measurements are enabled.

### waveform_enabled (bool)

Whether CH1 waveform capture is enabled.

### trigger_enabled (bool)

Whether CH2 trigger waveform capture is enabled.


## Configuration

This class requires configuration in your `config.toml` file:


### Example Configuration

```toml

[device.DPO7104_TekTronix_scope]
# DPO7104_TekTronix_scope configuration
# Number of averages
averages = 10
# Starting bound, the position of the first cursor relative to the trigger
start_bound = 1e-07
# Ending bound, the position of the second cursor relative to the trigger
end_bound = 0.001
# Pulls area data
area = True
# Pulls voltage wavefrom data, channel 1
waveform = False
# Pulls trigger waveform data, channel 2
trigger = False
# Number of samples to be saved of the waveform
samples_saved = 50
```


## Methods

### open_connection

Opens the resource manager and connects to the scope, saving it to self.scope.



### set_config



### set_cursors



### measure_area

Waits till the scope has enough acquisitionS, from now, to make an average, then pulls the area and
multiplies by -1



### step_data_puller

**Signature:** `step_data_puller(new_size)`

Pulls one point of the waveform data, then steps further and pulls again, to try to avoid overwhelming the scope's 
CPU and saving massive data files. This is a bit of a hack, but you cannot change the scope's sampling rate (and thus 
record length) without also changing the horizontal scale. If new_size is too big it will be very slow, but won't
create massive data files.



### measure_waveform

**Signature:** `measure_waveform(channel)`

Slowly pulls the waveform data and the parameters to reconstruct the time axis. Channel 2 for trigger for debugging.
This will save a lot of data and the scope's cpu can struggle to keep up, so use with caution and only use if required



### measure



### full_autoset



### close


