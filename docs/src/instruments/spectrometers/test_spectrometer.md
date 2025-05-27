# Test_spectrometer

A basic mock spectrometer class.


## Configuration

This class requires configuration in your `config.toml` file:


### Example Configuration

```toml

[device.Test_spectrometer]
# Test_spectrometer measurement configuration
# Step size in nm
step_size = 0.1
# Start wavelength (nm)
initial_wavelength = 500
# Stop wavelength in (nm)
final_wavelength = 600
```


## Methods

### setup_config



### measure



### set_wavelength

**Signature:** `set_wavelength(wavelength)`



### spectrometer_step

Move the wavelength by one step size increment.

Advances the wavelength by the configured step_size value.



### total_steps

Return the total number of steps for the current configuration 


