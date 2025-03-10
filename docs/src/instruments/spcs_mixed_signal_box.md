# SPCS_mixed_signal_box

A class to control and interact with an SPCS Mixed Signal Switch Box.


## Attributes

### MATRIX_CHANNEL_MAPPING (dict)

Maps logical channel names to matrix channel letters. e.g., "CH1" maps to "A", "CH2" maps to "B", etc.

### POLARITY_CHANNEL_MAPPING (dict)

Maps logical channel names to polarity channel letters. e.g., "CH1" maps to "E", "CH2" maps to "F", etc.

### MATRIX_MAPPING (dict)

Converts hexadecimal and string representations to integer values. Supports values from '0' to 'f', mapping to integers 0-15.

### REVERSE_MATRIX_MAPPING (dict)

Inverted MATRIX_CHANNEL_MAPPING for reverse lookups.

### REVERSE_POLARITY_MAPPING (dict)

Inverted POLARITY_CHANNEL_MAPPING for reverse lookups.

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

[device.SPCS_mixed_signal_switch_box]
# SPCS_mixed_signal_switch_box measurement configuration
# Reset the device on initilisation either true or false (bool)
reset = True

[device.SPCS_mixed_signal_switch_box.matrix]
# Matrix configuration settings
# Activiation state for the given channel (str) range: 1-f (hexidecimal)
CH1 = "1"
# Activiation state for the given channel (str) range: 1-f (hexidecimal)
CH2 = "2"
# Activiation state for the given channel (str) range: 1-f (hexidecimal)
CH3 = "4"
# Activiation state for the given channel (str) range: 1-f (hexidecimal)
CH4 = "8"

[device.SPCS_mixed_signal_switch_box.polarity]
# polarity configuration settings
# Polarity switch (str) '0' non-inverted '1' inverted
CH1 = "1"
# Polarity switch (str) '0' non-inverted '1' inverted
CH2 = "0"
# Polarity switch (str) '0' non-inverted '1' inverted
CH3 = "1"
# Polarity switch (str) '0' non-inverted '1' inverted
CH4 = "0"
```


## Methods

### find_correct_port

**Signature:** `find_correct_port(expected_response, baudrate, timeout)`

Automatically find the correct serial port for the matrix switch box.

Args:
    expected_response (str): The expected response from the device to identify it.
    baudrate (int, optional): Serial communication baudrate. Defaults to 115200.
    timeout (int, optional): Connection timeout in seconds. Defaults to 2.

Returns:
    str or None: The response from the device if found, None otherwise.

Raises:
    Logs an error if no matching device is found.



### connect

Establish a serial connection to the device using the previously identified port.

Sets up a serial connection with 115200 baudrate and 1-second timeout.



### set_channel_matrix

**Signature:** `set_channel_matrix(channel, command)`

Set the matrix routing for a specific channel.

Args:
    channel (str): The matrix channel to configure (A, B, C, or D).
    command (str): The routing configuration (0-15 or hex 0-f).



### set_channel_polarity

**Signature:** `set_channel_polarity(channel, command)`

Set the polarity for a specific channel.

Args:
    channel (str): The polarity channel to configure (E, F, G, or H).
    command (str): Polarity setting (0 = non-inverted, 1 = inverted).



### get_state

Retrieve the current state of all channels.

Returns:
    dict: A dictionary representing the current state of matrix and polarity settings.



### update_state

**Signature:** `update_state(response)`

Update the internal state based on the device's response.

Args:
    response (str): A comma-separated string of channel states.



### switch_layout

Print a diagram explaining the switch box channel and polarity mapping.

Provides a visual reference for channel routing and polarity configurations.



### setup_config

Set up the initial configuration of the device.

Performs a reset if specified in the configuration and sets initial channel states.



### reset

Reset all matrix and polarity channels to their default (0) state.

Iterates through all channels, setting matrix routing to 0 and polarity to non-inverted.



### set_initial_state

Configure initial matrix and polarity settings based on the configuration.

Sets matrix routing and polarity for channels as specified in the configuration.



### measure

Capture the current state of the device and optionally send data to PyFex.

Returns:
    dict: A dictionary of current channel states, with each state in a list.


