import random as rd
from ..spcs_instruments_utils import load_config
from ..spcs_instruments_utils import pyfex_support
import numpy as np
@pyfex_support
class Test_daq:
    def __init__(self, config, name="Test_DAQ", emulate=True, connect_to_pyfex=True):
        """
        A simulated device
        """
        self.name = name
        self.emulation = emulate
        self.state = 0

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
        self.trace_enabled = self.config.get("trace", False)
    def measure(self) -> float:
        data = rd.uniform(0.0, 10) * self.gate_time + self.state   
        self.data["counts"] = [data]
        self.data["current (mA)"] = [data]
        if self.trace_enabled:
            time = np.linspace(0, 10, 1000)
            noise = np.random.normal(0, 0.1, 1000)
            trace_data = np.exp(-time) + noise
            self.data["trace (signal)"] = trace_data.tolist()
            self.data["trace (time (s))"] = time.tolist()
        self.state +=1
        payload = self.create_payload()
        self.tcp_send(payload, self.sock)
        return data

    
