# Ocean_optics_spectrometer

A class to control and interact with an OceanOptics Spectrometer.


## Attributes

### name (str)

Name identifier for the device.

### config (dict)

Configuration settings for the device.

### connect_to_rex (bool)

Indicates whether to connect to the rex experiment manager.

### sock (socket, optional)

Socket connection for rex, if enabled.

### data (dict)

Stores measurement data.

### __toml_config__ (dict)

Default configuration template for the device


## Configuration

This class requires configuration in your `config.toml` file:


### Example Configuration

```toml

[device.OceanOpitics_Spectrometer]
# OceanOpitics_Spectrometer measurement configuration
# Integration time in microseconds
integration_time = 50000
# Number of averages
averages = 1
# Upper wavelength range
upper_limit = 600
# Lower wavelength range
lower_limit = 500
# which backend to use to connect, options: 'pyseabreeze', 'cseabreeze'
backend = "pyseabreeze"
```


## Methods

### setup_config



### measure



### bounds

**Signature:** `bounds(data, lower_limit, upper_limit)`


