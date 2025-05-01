import random as rd

from ...spcs_instruments_utils import pyfex_support

@pyfex_support
class Test_spectrometer:
    def __init__(self, config, name="Test_Spectrometer", emulate=True, connect_to_pyfex=True):
        """
        A simulated device
        """
        self.name = name

        self.connect_to_pyfex = connect_to_pyfex
        self.config = self.bind_config(config)
        
        self.logger.debug(f"{self.name} connected with this config {self.config}")
        self.wavelength = 500.0
        if self.connect_to_pyfex:
            self.sock = self.tcp_connect()
        self.setup_config()
        self.data = {
            "wavelength (nm)": [],
        }

    def setup_config(self):
        self.inital_position = self.require_config("initial_position")
        self.goto_wavelength(self.inital_position)
        self.slit_width = self.require_config("slit_width")
        self.step_size = self.require_config("step_size")

    def measure(self) -> dict:
        self.wavelength = round(self.wavelength, 2)
        self.data["wavelength (nm)"] = [self.wavelength]
        if self.connect_to_pyfex:
            payload = self.create_payload()
            self.tcp_send(payload, self.sock)
        return self.data
    
    def goto_wavelength(self, wavelength):
        self.wavelength = wavelength
