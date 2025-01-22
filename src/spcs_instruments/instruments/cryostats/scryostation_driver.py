
from ...spcs_instruments_utils import pyfex_support
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
    def __init__(self, config: str, name: str = "scyostation", immediate_start: bool = False) -> None:
        """
        Initializes the Scryostation with the provided configuration and optional settings.

        Args:
            config (str): Configuration file for the cryostation.
            name (str, optional): Name of the cryostation instance. Defaults to "scyostation". Name must be reflected within the configuration file
            immediate_start (bool, optional): Whether to immediately start the cryostation cooldown process. Defaults to False.
        """
        self.name = name
         
        self.config = self.bind_config(config)
        
        self.ip = self.require_config("device_ip")
        self.primary_temp_probe = self.require_config("temperature_probe")
        self.cryostat = scryostation.SCryostation(self.ip)
        print(f"{self.name} connected with this config {self.config}")
        self.sock = self.tcp_connect()
        self.data = {
                "temperature (K)": [],
                "stability (K)": [],
                "Pressure (Pa)": [],
             }
            
        #self.setup_config(immediate_start)

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
                self.cryostat.set_platform_stabiltiy(self.stability)
            case "sample":
                #as the platform target wont be used, set it to 0K
                self.cryostat.set_platform_target_temperature(0)
                self.cryostat.set_user1_target_temperature(self.intial_cooldown_target)
                self.cryostat.set_user1_stability_target(self.stability)
        if immediate_start:
            self.prepare_cryostat()
            print("Initialising cryostat into desired state")

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
        print('Started cooldown')
    
    def warm_up(self) -> None:
        """        
        Initiates the warm-up process for the cryostation.
        """
        self.cryostat.warmup()



    def is_at_setpoint(self) -> bool:
        """
        Checks if the cryostation has reached its target temperature and stability.
        Validates if the cryostation is both within a setpoint tolerance as well as temperature stability.  
        Args:
            tolerance (float): Acceptable tolerance between actual and desired setpoint temperature.
        Returns:
            bool: True if the cryostation is at the target setpoint, False otherwise.
        """
        # TODO: Implement functionality
        pass
        
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

    def measure(self) -> dict:
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
        
        payload = self.create_payload()
        self.tcp_send(payload, self.sock)
        return self.data  
        
            
             
