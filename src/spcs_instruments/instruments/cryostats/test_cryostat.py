import random as rd
from ...spcs_instruments_utils import load_config
from ...spcs_instruments_utils import pyfex_support

@pyfex_support
class Test_cryostat:
    def __init__(self, config, name="Test_cryostat", emulate=True, connect_to_pyfex=True):
        """
        A simulated device
        """
        self.name = name
        self.emulation = emulate
        self.connect_to_pyfex = connect_to_pyfex

        config = load_config(config)
        self.config = config.get('device', {}).get(self.name, {})
        self.logger.debug(f"{self.name} connected with this config {self.config}")
        if self.connect_to_pyfex:
            self.sock = self.tcp_connect()
        
        
        self.setup_config()
        self.data = {
            "temperature (K)": [],
            "stability (K)": [],
            "pressure (kPa)": [],
            "magnetic field (mT)": [],

        }

    def setup_config(self):

        self.logger.debug("Initialising cryostat into desired state")
        self.goto_setpoint(self.config.get(""))
        self.desired_stability = self.config.get("desired_stability")
        self.desired_field_strength = 0.0
        


    def measure(self) -> float:
        temperature, stability, pressure = self.get_cryostate()
        field_strength = self.get_magnetstate()
        self.data["temperature (K)"] = [temperature]
        self.data["stability (K)"] = [stability]
        self.data["pressure (kPa)"] = [pressure]
        self.data["magnetic field (mT)"] = [field_strength]
        if self.connect_to_pyfex:
            payload = self.create_payload()
            self.tcp_send(payload, self.sock)
        return self.data
    
    def goto_setpoint(self, setpoint):
        self.set_point = setpoint

    def set_magneticfield(self, strength):
        self.desired_field_strength = strength
        
    def get_cryostate(self):
        temperature = self.set_point + rd.uniform(-0.005, 0.05)
        stability = self.desired_stability + rd.uniform(-0.005, 0.005)
        pressure = 2e-6 + rd.uniform(-0.1,0.1)
        return temperature, stability, pressure
    
    def get_magnetstate(self):
        field_strength = self.desired_field_strength
        return field_strength    
