# Scryostation

A class to manage and control a cryostation system, including its configuration,
initialization, and operational states such as bake-out, purging, and cooldown.


## Attributes

### name (str)

Name of the cryostation.

### config (dict)

Parsed configuration data for the cryostation.

### ip (str)

IP address of the cryostation device.

### cryostat (object)

Instance of the cryostation control object.

### sock (socket)

TCP socket for communication with the cryostation.

### data (dict)

Stores measured data such as temperature, stability, and pressure.


## Configuration

This class requires configuration in your `config.toml` file:


### Example Configuration

```toml

[instruments.scryostation]
# Scryostation configuration
# Valid IP address of the cryostation or device name (DHCP)
ip_address = "0.0.0.0"
# Initial target temperature for the cryostation in Kelvin
inital_cooldown_target = 5
# Desired temperature stability in Kelvin
desired_stability = 0.1
# Toggle if there will be a bakeout process before cooling the cryostat
enable_bakeout = True
# Bakeout temperature in Kelvin (max 350)
bakeout_temperature = 325
# Time in minutes for the bakeout process
bakeout_time = 30
# Toggle if there will be a nitrogen purge process before cooling the cryostat
enable_purge = True
# Number of nitrogen purges
purges = 5
# Determines what is the primary temperature probe options: 'sample' 'platform'
temperature_probe = "sample"
```


## Methods

### setup_config

**Signature:** `setup_config(immediate_start)`

Sets up the cryostation configuration and optionally starts the cooldown process.

Args:
    immediate_start (bool): Whether to immediately start the cryostation cooldown process.



### prepare_cryostat

Prepares the cryostation by performing a bake-out, purge, and cooldown in sequence.



### bake_out

Configures and initiates the bake-out process for the cryostation.

Retrieves the necessary settings from the configuration and applies them.



### purge

Configures and initiates the nitrogen purge process for the cryostation.

Retrieves the necessary settings from the configuration and applies them.



### cooldown

Starts the cooldown process for the cryostation.

Raises:
    RuntimeError: If the system fails to enter the 'Cooldown' state.



### warm_up

Initiates the warm-up process for the cryostation.



### is_at_setpoint

**Signature:** `is_at_setpoint(tolerance)`

Checks if the cryostation has reached its target temperature and stability.
Validates if the cryostation is both within a setpoint tolerance as well as temperature stability.  
Args:
    tolerance (optional float): Acceptable tolerance between actual and desired setpoint temperature. If unset, it checks if the temperatrue has reached stability and setpoint per the manufacturer.
Returns:
    bool: True if the cryostation is at the target setpoint, False otherwise.



### go_to_temperature

**Signature:** `go_to_temperature(temperature, stability)`

Sets the cryostation to a specific target temperature and stability.

Args:
    temperature (float): Target temperature in Kelvin.
    stability (float, optional): Target stability. Defaults to the configured stability.



### toggle_magnetic_field

**Signature:** `toggle_magnetic_field(state)`

Toggles the magnet on and off.

Args:
    state (str): "on" or "off" to toggle the magnetic field on and off.



### set_magnetic_field

**Signature:** `set_magnetic_field(strength)`

Set the magnetic field to a desired field strength

Args:
    strength (float): Desired field strength in mT



### get_magnetic_field

**Signature:** `get_magnetic_field(tolerance)`

Checks the magnetic field by first checking its still operational, it then checks that the measured and calculated field strength are within a given tolerance in Tesla
Args:
    tolerance (float (mT)): Acceptable difference between desired and actual field strengths. Automatically converts to T from mT.

Returns:
    float: Magnetic field strength in mT



### measure

**Signature:** `measure(tolerance)`

Measures and retrieves the current temperature, stability, and pressure of the scryostation.

Updates the internal data dictionary with the latest measurements and sends the data payload to the PyFeX TCP server.

Returns:
    dict: A dictionary containing the latest measurements for use within a Python script.


