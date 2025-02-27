# C8855_counting_unit

Class for controlling the C8855 photon counting unit.


## Attributes

### gate_time_mapping (dict)

Maps human-readable gate times to corresponding hexadecimal values.

### transfer_type_mapping (dict)

Maps transfer types to their respective integer values.

### trigger_type_mapping (dict)

Maps trigger modes to their respective integer values.

### name (str)

Name identifier for the device.

### config (dict)

Configuration settings for the device.

### connect_to_pyfex (bool)

Indicates whether to connect to the PyFex experiment manager.

### sock (socket, optional)

Socket connection for PyFex, if enabled.

### data (dict)

Stores measurement data.

### __toml_config__ (dict)

Default configuration template for the device


## Configuration

This class requires configuration in your `config.toml` file:


### Example Configuration

```toml

[device.C8855_photon_counter]
# C8855_photon_counter measurement configuration
# Transfer type, working and validated transfer type is 'block_transfer' however 'single_transfer' is available.
transfer_type = "block_transfer"
# Number of gates: 2,4,8,16,32,64,128,256,512
number_of_gates = 512
# Gate time to use, e.g. '500us' or '1ms', or '2ms' etc. available gate times: '50us': 0x02,'100us','200us','500us','1ms','2ms','5ms','10ms','20ms','50ms','100ms','200ms','500ms','1s','2s','5s','10s'
gate_time = "500us"
# Type of device triggering to use (external, software)
trigger_type = "external"
# Number of averages to take
averages = 16
# Measurement mode to use, counts only (counts_only), trace only (trace), or both as a tupple (all)
measure_mode = "counts_only"
# DLL path to use for C8855 photon counter
dll_path = "/path/to/dll"
```


## Methods

### setup_config

Loads device configuration and initializes the DLL functions.



### general_measurement

Performs a single measurement cycle, including resetting, setting up, starting, reading, and stopping.



### stop_counting

**Signature:** `stop_counting(handle)`

Stops the photon counting process.

Args:
    handle (ctypes.c_void_p): A handle to the C8855 device.

Returns:
    bool: True if the counting was successfully stopped, False otherwise.



### measure

Conducts multiple measurements based on the configured number of averages.

Returns:
    float | tuple: Depending on measure_mode, returns either total count, trace data, or both.



### open_device

Opens a connection to the device.

Returns:
    ctypes.c_void_p: Handle to the device.



### reset_device

**Signature:** `reset_device(handle)`

Resets the device to its default state.

Args:
    handle (ctypes.c_void_p): Device handle.

Returns:
    bool: True if successful, False otherwise.



### close_device

**Signature:** `close_device(handle)`

Closes the connection to the device.

Args:
    handle (ctypes.c_void_p): Device handle.

Returns:
    int: Status of the close operation.



### setup_device

**Signature:** `setup_device(handle, gate_time, transfer_mode, number_of_gates)`

Configures the device with the specified parameters.

Args:
    handle (ctypes.c_void_p): Device handle.
    gate_time (ctypes.c_ubyte): Gate time setting.
    transfer_mode (ctypes.c_ubyte): Transfer mode setting.
    number_of_gates (ctypes.c_ushort): Number of gates for measurement.

Returns:
    bool: True if setup was successful, False otherwise.



### start_counting

**Signature:** `start_counting(handle, trigger_mode)`

Starts the counting process.

Args:
    handle (ctypes.c_void_p): Device handle.
    trigger_mode (ctypes.c_ubyte, optional): Trigger mode. Defaults to C8855_EXTERNAL_TRIGGER.

Returns:
    bool: True if counting started successfully, False otherwise.



### read_data

**Signature:** `read_data(handle, data_buffer)`

Reads data from the device into the provided buffer.

Args:
    handle (ctypes.c_void_p): Device handle.
    data_buffer (Pointer_c_ulong): Buffer to store retrieved data.


