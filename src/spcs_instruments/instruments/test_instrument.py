import random as rd
from ..spcs_instruments_utils import load_config


class Fake_daq:
    def __init__(self, config, name="Test_DAQ", emulate=True):
        """
        A simulated device
        """
        self.name = name
        self.emulation = emulate

        if not self.emulation:
            print(
                "This device is not real, it cannot be used in a non-emulated environment"
            )
            print("Would you like to emulate the device instead?")
        else:
            print(f"Simulated DAQ '{self.name}' successfully emulated")
            config = load_config(config)
            self.config = config.get('device', {}).get(self.name, {})
            print(f"{self.name} connected with this config {self.config}")
            self.setup_config()
            self.data = {
                "counts": [],
                "current": [],
            }

    def setup_config(self):
        # Get the configuration parameters
        self.gate_time = self.config.get("gate_time")
        self.averages = self.config.get("averages")

    def measure(self) -> float:
        data = rd.uniform(0.0, 10) * self.gate_time
        self.data["counts"].append(data)
        self.data["current"].append(data)
        return data
