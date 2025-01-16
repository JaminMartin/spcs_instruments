
from ...spcs_instruments_utils import load_config, pyfex_support
from .montana_support import instrument, scryostation
from .montana_support.instrument import TunnelError


@pyfex_support
class Scryostation:
    def __init__(self, config, name="scyostation", connect_to_pyfex=True):
        """
        A simulated device
        """
        self.name = name
   
        config = load_config(config)
        self.config = config.get('device', {}).get(self.name, {})
        self.ip = self.config.get("device_ip")
        self.cryostat = scryostation.SCryostation(self.ip)
        print(f"{self.name} connected with this config {self.config}")
        self.sock = self.tcp_connect()
            
            
        self.setup_config()
        self.data = {
                "temperature (K)": [],
                "stability (K)": [],
                "Pressure (Pa)": [],
             }
    def setup_config(self):

        print("Initialising cryostat into desired state")

    def measure(self):
        values = self.cryostat.get_platform_temperature_sample()
        values_pressure = self.cryostat.get_sample_chamber_pressure()
        self.cryostat.get_sample_chamber_pressure()
        self.data["temperature (K)"] = [values["temperature"]]
        self.data["stability (K)"] = [values["temperatureStability"]]
        self.data["Pressure (Pa)"] = [values_pressure]
        
        payload = self.create_payload()
        print(payload)
        self.tcp_send(payload, self.sock)
        return self.data  
        
            
             
