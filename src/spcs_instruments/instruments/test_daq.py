import random as rd
from ..spcs_instruments_utils import load_config
from ..spcs_instruments_utils import rex_support
import numpy as np
@rex_support
class Test_daq:
    __toml_config__ = {
    "device.Test_DAQ": {
        "_section_description": "Test_DAQ measurement configuration",
        "gate_time": {
            "_value": 0.1,
            "_description": "Step size in nm"
        },
        "averages": {
            "_value": 500,
            "_description": "Start wavelength (nm)"
        },
        "trace":{
            "_value": False, 
            "_description": "Sends mock time series data if set to True"
        }}}
    def __init__(self, config, name="Test_DAQ", emulate=True, connect_to_rex=True):
        """
        A simulated device
        """
        self.name = name
        self.emulation = emulate
        self.state = 0
        self.connect_to_rex = connect_to_rex
        config = load_config(config)
        self.config = config.get('device', {}).get(self.name, {})
        self.logger.debug(f"{self.name} connected with this config {self.config}")
        if self.connect_to_rex:
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
        self.data["current (mA)"] = [data * rd.uniform(0.0, 10) ]
        if self.trace_enabled:
            time = np.linspace(0, 10, 1000)
            noise = np.random.normal(0, 0.1, 1000)
            trace_data = np.exp(-time) + noise
            self.data["trace (signal)"] = trace_data.tolist()
            self.data["trace (time (s))"] = time.tolist()
        self.state +=1
        if self.connect_to_rex:
            payload = self.create_payload()
            self.tcp_send(payload, self.sock)
        return data

    
