import sys
import glob
import serial
import time
import random as rd
from ..spcs_instruments_utils import load_config


class Fake_daq:
    def __init__(self, config, emulate=True):
        """
        a simulated device
        """
        self.emulation = True
        self.name = "simulated daq"
        if self.emulation == False:
            print(
                "This device is not real, it cannot be used in a non emulated environment"
            )
            print("Would you like to emulate the device instead?")
        else:
            self.instrument = print("Simulated Daq Sucsessfully emulated")
            self.name = "simulated daq"
            config = load_config(config)
            self.config = config.get("Test_DAQ", {})
            print(f"Test DAQ connected with this config {self.config}")
            self.setup_config()
            self.data = {
                "counts": [],
                "current": [],
            }
        return

    def setup_config(self):
        # Get the configuration parameters
        self.gate_time = self.config.get("gate_time")
        self.averages = self.config.get("averages")

    def measure(self) -> float:
        data = rd.uniform(0.0, 10) * self.gate_time
        self.data["counts"].append(data)
        self.data["current"].append(data)
        return data
