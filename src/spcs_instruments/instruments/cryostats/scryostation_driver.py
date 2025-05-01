
from ...spcs_instruments_utils import pyfex_support, DeviceError 
from .montana_support import scryostation
from .montana_support.instrument import TunnelError
import time

@pyfex_support
class Scryostation:
    """
    A class to manage and control a cryostation system, including its configuration,
    initialization, and operational states such as bake-out, purging, and cooldown.

    Attributes:
        name (str): Name of the cryostation.
        config (dict): Parsed configuration data for the cryostation.
        ip (str): IP address of the cryostation device.
        cryostat (object): Instance of the cryostation control object.
        sock (socket): TCP socket for communication with the cryostation.
        data (dict): Stores measured data such as temperature, stability, and pressure.
    """

    __toml_config__ = {
        "instruments.scryostation": {
            "_section_description": "Scryostation configuration",
            "ip_address": {
                "_value": "0.0.0.0",
                "_description": "Valid IP address of the cryostation or device name (DHCP)"
            },
            "inital_cooldown_target": {
                "_value": 5,
                "_description": "Initial target temperature for the cryostation in Kelvin"
            },
            "desired_stability": {
                "_value": 0.1,
                "_description": "Desired temperature stability in Kelvin"
            },
            "enable_bakeout": {
                "_value": True,
                "_description": "Toggle if there will be a bakeout process before cooling the cryostat"
            },
            "bakeout_temperature": {
                "_value": 325,
                "_description": "Bakeout temperature in Kelvin (max 350)"
            }
            ,
            "bakeout_time": {
                "_value": 30,
                "_description": "Time in minutes for the bakeout process"
            }
            ,
            "enable_purge": {
                "_value": True,
                "_description": "Toggle if there will be a nitrogen purge process before cooling the cryostat"
            }
            ,
            "purges": {
                "_value": 5,
                "_description": "Number of nitrogen purges"
            }
            ,
            "temperature_probe": {
                "_value": "sample",
                "_description": "Determines what is the primary temperature probe options: 'sample' 'platform'"
            }
        }
    }    
    def __init__(self, config: str, name: str = "scyostation", immediate_start: bool = False, connect_to_pyfex=True) -> None:
        """
        Initializes the Scryostation with the provided configuration and optional settings.

        Args:
            config (str): Configuration file for the cryostation.
            name (str, optional): Name of the cryostation instance. Defaults to "scyostation". Name must be reflected within the configuration file
            immediate_start (bool, optional): Whether to immediately start the cryostation cooldown process. Defaults to False.
        """
        self.name = name
         
        self.config = self.bind_config(config)
        self.connect_to_pyfex = connect_to_pyfex
        self.ip = self.require_config("device_ip")
        self.primary_temp_probe = self.require_config("temperature_probe")
        self.cryostat = scryostation.SCryostation(self.ip)
        self.logger.debug(f"{self.name} connected with this config {self.config}")
        if self.connect_to_pyfex:
            self.sock = self.tcp_connect()
        self.magstate = False
        self.data = {
                "temperature (K)": [],
                "stability (K)": [],
                "Pressure (Pa)": [],
                "Magnetic Field (mT)": []
             }
            
        self.setup_config(immediate_start)

    def setup_config(self, immediate_start: bool):
        """
        Sets up the cryostation configuration and optionally starts the cooldown process.

        Args:
            immediate_start (bool): Whether to immediately start the cryostation cooldown process.
        """
        self.stability = self.require_config("desired_stability")
        self.intial_cooldown_target = self.require_config("inital_cooldown_target")
        match self.primary_temp_probe:
            case "platform": 
                self.cryostat.set_platform_target_temperature(self.intial_cooldown_target)
                self.cryostat.set_platform_stabiltiy_target(self.stability)
                self.temperature_target = self.intial_cooldown_target
            case "sample":
                #as the platform target wont be used, set it to 0K
                self.cryostat.set_platform_target_temperature(0)
                self.cryostat.set_user1_target_temperature(self.intial_cooldown_target)
                self.cryostat.set_user1_stability_target(self.stability)
                self.temperature_target = self.intial_cooldown_target
        if immediate_start:
            self.prepare_cryostat()
            self.logger.debug("Initialising cryostat into desired state")

    def prepare_cryostat(self) -> None:
        """
        Prepares the cryostation by performing a bake-out, purge, and cooldown in sequence.
        """
        self.bake_out()
        self.purge()
        self.cooldown()

    def bake_out(self) -> None:
        """
        Configures and initiates the bake-out process for the cryostation.
        
        Retrieves the necessary settings from the configuration and applies them.
        """
            
        self.cryostat.set_platform_bakeout_enabled(self.require_config("enable_bakeout")) # Bool
        self.cryostat.set_platform_bakeout_temperature(self.require_config("bakeout_temperature")) # Temp in Kelvin
        self.cryostat.set_platform_bakeout_time(self.require_config("bakeout_time") * 60) # Time in mins 

    def purge(self) -> None:
        """
        Configures and initiates the nitrogen purge process for the cryostation.
        
        Retrieves the necessary settings from the configuration and applies them.
        """
        self.cryostat.set_dry_nitrogen_purge_enabled(self.require_config("enable_purge")) # bool
        self.cryostat.set_dry_nitrogen_purge_num_times(self.require_config("purges"))

    def cooldown(self) -> None:
        """
        Starts the cooldown process for the cryostation.

        Raises:
            RuntimeError: If the system fails to enter the 'Cooldown' state.
        """
        self.cryostat.cooldown()
        time.sleep(2)
        if self.cryostat.get_system_goal() != 'Cooldown':
            raise RuntimeError('Failed to initiate Cooldown!')
        self.logger.info('Started cooldown')
    
    def warm_up(self) -> None:
        """        
        Initiates the warm-up process for the cryostation.
        """
        self.cryostat.warmup()



    def is_at_setpoint(self, tolerance=None) -> bool:
        """
        Checks if the cryostation has reached its target temperature and stability.
        Validates if the cryostation is both within a setpoint tolerance as well as temperature stability.  
        Args:
            tolerance (optional float): Acceptable tolerance between actual and desired setpoint temperature. If unset, it checks if the temperatrue has reached stability and setpoint per the manufacturer.
        Returns:
            bool: True if the cryostation is at the target setpoint, False otherwise.
        """
        if tolerance is not None:
            match self.primary_temp_probe:
                case "sample":
                    temperature_values = self.cryostat.get_user1_temperature_sample()
                    
                case "platform":
                    temperature_values = self.cryostat.get_platform_temperature_sample()
                            
            actual_temperature  = temperature_values["temperature"]
            stability_measured = temperature_values["temperatureStability"]
            if abs(self.temperature_target - actual_temperature) <= tolerance  and stability_measured <= self.stability:
                temp_valid = True
            else:
                temp_valid = False    
            return temp_valid
        else:
            match self.primary_temp_probe:
                case "sample":
                    temperature_values = self.cryostat.get_user1_temperature_sample()

                case "platform":
                    temperature_values = self.cryostat.get_platform_temperature_sample()
            stability_measured = temperature_values["temperatureStability"]
            if abs(self.temperature_target - actual_temperature) <= 0.1  and stability_measured <= self.stability:
                return True
            else:
                return False            
        
        
    def go_to_temperature(self, temperature: float, stability: float = None) -> None:
        """
        Sets the cryostation to a specific target temperature and stability.

        Args:
            temperature (float): Target temperature in Kelvin.
            stability (float, optional): Target stability. Defaults to the configured stability.
        """
                
        if stability is None:
            stability = self.require_config("desired_stability")
            
        match self.primary_temp_probe:
            case "platform": 
                self.cryostat.set_platform_target_temperature(temperature)
                self.cryostat.set_platform_stabiltiy(stability)
            case "sample":

                self.cryostat.set_user1_target_temperature(temperature)
                self.cryostat.set_user1_stability_target(stability)
        self.temperature_target = temperature 

                
    def toggle_magnetic_field(self, state: str):
        """
        Toggles the magnet on and off.

        Args:
            state (str): "on" or "off" to toggle the magnetic field on and off.
        """
        match state:
            case "on":
                match self.magstate:
                    case True:
                        pass
                    case False: 
                        self.cryostat.set_mo_enabled(True)
                        self.magstate = True
            case "off":
                match self.magstate:
                    case False:
                        pass
                    case True:
                        self.cryostat.set_mo_enabled(False)
                        self.magstate = False
                
    def set_magnetic_field(self, strength: float):
        """
        Set the magnetic field to a desired field strength

        Args:
            strength (float): Desired field strength in mT
        """
        if strength >= -700 and strength <= 700:
            self.cryostat.set_mo_target_field(strength / 1000) # convert to Tesla
        else:
            raise ValueError("Magnetic field set out of bounds! (-700-700mT limit!)")
        

    def get_magnetic_field(self, tolerance: float) -> float:
        """
        Checks the magnetic field by first checking its still operational, it then checks that the measured and calculated field strength are within a given tolerance in Tesla
        Args:
            tolerance (float (mT)): Acceptable difference between desired and actual field strengths. Automatically converts to T from mT.

        Returns:
            float: Magnetic field strength in mT
        """
        if self.magstate:
            tolerance_T = tolerance / 1000 
            if self.cryostat.get_mo_safe_mode():
                raise DeviceError("Magnet is in safe mode!")
            
            desired = self.cryostat.get_mo_target_field()
            actual = self.cryostat.get_mo_calculated_field()
            if abs( desired - actual) <= tolerance_T:
                return actual * 1000 # convert to mT
            else:
                raise DeviceError("Desired field is not met, is the device working?")
        else:
            # if the field is off return 0mT
            return 0     
    def measure(self, tolerance: float  = 5.0) -> dict:
        """
        Measures and retrieves the current temperature, stability, and pressure of the scryostation.

        Updates the internal data dictionary with the latest measurements and sends the data payload to the PyFeX TCP server.

        Returns:
            dict: A dictionary containing the latest measurements for use within a Python script.
        """
        
        match self.primary_temp_probe:
            case "sample":
                temperature_values = self.cryostat.get_user1_temperature_sample()
            case "platform":
                temperature_values = self.cryostat.get_platform_temperature_sample()
 
      
        values_pressure = self.cryostat.get_sample_chamber_pressure()
        self.data["temperature (K)"] = [temperature_values["temperature"]]
        self.data["stability (K)"] = [temperature_values["temperatureStability"]]
        self.data["Pressure (Pa)"] = [values_pressure]
        field = self.get_magnetic_field(tolerance)
        self.data["Magnetic Field (mT)"] = [field]
        if self.connect_to_pyfex:
            payload = self.create_payload()
            self.tcp_send(payload, self.sock)
        return self.data  
        
