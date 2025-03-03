# HoribaiHR550

A class to control and interface with the Horiba iHR550 Spectrometer via libusb.

This class provides a control interface for the iHR550 spectrometer including
wavelength control, grating selection, mirror positioning, and slit width adjustment.


## Attributes

### VENDOR_ID (int)

USB vendor ID for the device (0xC9B)

### PRODUCT_ID (int)

USB product ID for the device (0x101)

### LANG_ID_US_ENGLISH (int)

Language ID for US English (0x409)

### B_REQUEST_OUT (int)

USB output request type (0x40)

### B_REQUEST_IN (int)

USB input request type (0xC0)

### BM_REQUEST_TYPE (int)

USB request type (0xB3)

### CMD_WAVELENGTH_SET (int)

Command index for setting wavelength (4)

### CMD_WAVELENGTH_READ (int)

Command index for reading wavelength (2)

### CMD_TURRET_SET (int)

Command index for setting turret (17)

### CMD_TURRET_READ (int)

Command index for reading turret (16)

### CMD_BUSY (int)

Command index for checking busy status (5)

### CMD_INIT (int)

Command index for initialization (0)

### CMD_SET_MIRROR (int)

Command index for setting mirror (41)

### CMD_READ_MIRROR (int)

Command index for reading mirror (40)

### CMD_SET_SLITWIDTH (int)

Command index for setting slit width (33)

### CMD_READ_SLITWIDTH (int)

Command index for reading slit width (32)

### TURRET_MAPPING (dict)

Maps turret indices to grating names

### MIRROR_MAPPING (dict)

Maps mirror indices to names

### SLIT_MAPPING (dict)

Maps slit names to their indices

### __toml_config__ (dict)

Default configuration template for the device

### bypass_homing (bool)

Whether to skip the homing sequence

### slit_type (int)

Type of slit mechanism (hardcoded to 7)

### hardware_config (dict)

Contains gratings and mirrors configuration

### _state (dict)

Current state of device (position, turret, mirrors, slits)

### _dev (usb.core.Device)

USB device instance

### data (dict)

Measurement data storage

### config

Bound configuration as defined by the user

### connect_to_pyfex (bool)

Whether to connect to pyfex experiment manager

### sock

Socket connection when pyfex is enabled

### step_size (float)

Step size for measurements (default 0.1nm)

### start_wavelength (float)

Initial start wavelength (default 500nm)

### final_wavelength (float)

End wavelength for a measurement (default 600nm)


## Configuration

This class requires configuration in your `config.toml` file:


### Example Configuration

```toml

[device.iHR550]
# IHR550 measurement configuration
# Valid grating name to be used for the measurement, options: VIS, NIR, MIR
grating = "VIS"
# Step size in nm
step_size = 0.1
# Start wavelength (nm)
initial_wavelength = 500
# Stop wavelength in (nm)
final_wavelength = 500

[device.iHR550.slits]
# Slit configuration settings
# Entrance front slit width in mm
Entrance_Front = 0.5
# Entrance side slit width in mm
Entrance_Side = 0.0
# Exit front slit width in mm
Exit_Front = 0.5
# Exit side slit width in mm
Exit_Side = 0.0

[device.iHR550.mirrors]
# Mirror configuration settings
# Orientation of extrance mirror
Entrance = "front"
# Orientation of exit mirror
Exit = "side"
```


## Methods

### close

Release the USB device and free associated resources.

Should be called when finished using the device to ensure proper cleanup.



### is_busy

Check if the spectrometer is currently busy.

Returns:
    bool: True if the device is busy, False otherwise

Raises:
    Exception: If there's an error reading the busy state



### wait_until_not_busy

**Signature:** `wait_until_not_busy(poll_interval, timeout)`

Wait until the device reports it is not busy.

Args:
    poll_interval (float, optional): Time between checks in seconds. Defaults to 0.05
    timeout (float, optional): Maximum wait time in seconds. Defaults to 30.0

Raises:
    TimeoutError: If device remains busy longer than timeout period



### update_state

**Signature:** `update_state(timeout)`

Update the internal state of the device by reading current settings.

Updates turret position, wavelength, mirror positions, and slit widths.

Args:
    timeout (float, optional): Maximum time to wait for updates in seconds. Defaults to 30.0



### set_wavelength

**Signature:** `set_wavelength(wavelength, timeout)`

Set the spectrometer to a specific wavelength.

Args:
    wavelength (float): Target wavelength in nanometers
    timeout (float, optional): Maximum time to wait for movement in seconds. Defaults to 30.0

Raises:
    ValueError: If current turret configuration is invalid



### get_wavelength

Get the current wavelength setting.

Returns:
    float: Current wavelength in nanometers



### set_turret

**Signature:** `set_turret(turret, timeout)`

Set the grating turret to a specific position.

Args:
    turret (str): Desired turret position ("VIS", "NIR", or "MIR")
    timeout (float, optional): Maximum time to wait for movement in seconds. Defaults to 400.0

Raises:
    ValueError: If specified turret position is invalid



### set_slit

**Signature:** `set_slit(port, width, timeout)`

Set a specific slit to the desired width.

Args:
    port (str): Slit identifier (e.g., "Entrance_Front", "Exit_Side")
    width (float): Desired slit width in millimeters
    timeout (float, optional): Maximum time to wait for movement in seconds. Defaults to 30.0



### get_slit

**Signature:** `get_slit(index, timeout)`

Read the width of a specific slit.

Args:
    index (int): Index of the slit to read
    timeout (float, optional): Maximum time to wait for reading in seconds. Defaults to 30.0

Returns:
    float: Slit width in millimeters



### get_turret

**Signature:** `get_turret(timeout)`

Read the current turret position.

Args:
    timeout (float, optional): Maximum time to wait for reading in seconds. Defaults to 30.0

Returns:
    int: Current turret index



### initialize

**Signature:** `initialize(timeout)`

Initialize and home the spectrometer.

If bypass_homing is False, performs a full initialization sequence.

Args:
    timeout (float, optional): Maximum time to wait for homing in seconds. Defaults to 90.0



### setup_device

Configure the device according to the current configuration.

Sets up step size, turret position, initialization, slit widths, mirror positions,
and initial wavelength according to the configuration.



### spectrometer_step

Move the wavelength by one step size increment.

Advances the wavelength by the configured step_size value.



### measure

Take a measurement at the current wavelength.

Returns:
    Dict: Dictionary containing measurement data with wavelength information



### get_mirror

**Signature:** `get_mirror(index, timeout)`

Read the current position of a specific mirror.

Args:
    index (int): Mirror index to read
    timeout (float, optional): Maximum time to wait for reading in seconds. Defaults to 30.0

Returns:
    str: Mirror position ("side" or "front")



### set_mirror

**Signature:** `set_mirror(port, side, timeout)`

Set a specific mirror to the desired position.

Args:
    port (str): Mirror identifier ("Entrance" or "Exit")
    side (str): Desired position ("side" or "front")
    timeout (float, optional): Maximum time to wait for movement in seconds. Defaults to 30.0


