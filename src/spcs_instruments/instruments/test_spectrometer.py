import random as rd
from ..spcs_instruments_utils import load_config
from ..spcs_instruments_utils import tcp_connect, tcp_send


class Test_spectrometer:
    def __init__(self, config, name="Test_Spectrometer", emulate=True, connect_to_pyfex=True):
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
            print(f"Simulated Spectrometer '{self.name}' successfully emulated")
            config = load_config(config)
            self.config = config.get('device', {}).get(self.name, {})
            print(f"{self.name} connected with this config {self.config}")
            self.sock = tcp_connect()
            self.wavelength = 500.0
            
            self.setup_config()
            self.data = {
                "wavelength (nm)": [],
            }

    def setup_config(self):
        self.inital_position = self.config.get("initial_position")
        self.goto_wavelength(self.inital_position)
        self.slit_width = self.config.get("slit_width")
        self.iter = self.config.get("step_size")

    def evaluate(self) -> float:
        self.wavelength = round(self.wavelength + self.iter, 2)
        self.data["wavelength (nm)"] = [self.wavelength]
        payload = self.create_payload()
        print(payload)
        tcp_send(payload, self.sock)
        return self.data
    
    def goto_wavelength(self, wavelength):
        self.wavelength = wavelength

    
    def create_payload(self) -> dict:
        device_config = {key: value for key, value in self.config.items()}
        
        payload = {
            "device_name": self.name,
            "device_config": device_config,
            "measurements": self.data
        }
        
        return payload
