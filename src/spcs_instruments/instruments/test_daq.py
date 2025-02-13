import random as rd
from ..spcs_instruments_utils import load_config
from ..spcs_instruments_utils import pyfex_support

@pyfex_support
class Test_daq:
    def __init__(self, config, name="Test_DAQ", emulate=True, connect_to_pyfex=True):
        """
        A simulated device
        """
        self.name = name
        self.emulation = emulate


        config = load_config(config)
        self.config = config.get('device', {}).get(self.name, {})
        self.logger.debug(f"{self.name} connected with this config {self.config}")
        self.sock = self.tcp_connect()
        self.setup_config()
        self.data = {
            "counts": [],
            "current (mA)": [],
        }

    def setup_config(self):
        self.gate_time = self.config.get("gate_time")
        self.averages = self.config.get("averages")

    def measure(self) -> float:
        data = rd.uniform(0.0, 10) * self.gate_time    
        self.data["counts"] = [data]
        self.data["current (mA)"] = [data]
    
        payload = self.create_payload()
        self.tcp_send(payload, self.sock)
        return data

    
