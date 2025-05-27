import random as rd

from ...spcs_instruments_utils import rex_support

@rex_support
class Test_spectrometer:
    '''
    A basic mock spectrometer class.
    '''
    
    __toml_config__ = {
    "device.Test_spectrometer": {
        "_section_description": "Test_spectrometer measurement configuration",
        "step_size": {
            "_value": 0.1,
            "_description": "Step size in nm"
        },
        "initial_wavelength": {
            "_value": 500,
            "_description": "Start wavelength (nm)"
        },
        "final_wavelength":{
            "_value": 600, 
            "_description": "Stop wavelength in (nm)"
        }}}
    
    def __init__(self, config, name="Test_Spectrometer", emulate=True, connect_to_rex=True):
        """
        A simulated device
        """
        self.name = name

        self.connect_to_rex = connect_to_rex
        self.config = self.bind_config(config)
        
        self.logger.debug(f"{self.name} connected with this config {self.config}")
        self.wavelength = 500.0
        if self.connect_to_rex:
            self.sock = self.tcp_connect()
        self.setup_config()
        self.data = {
            "wavelength (nm)": [],
        }

    def setup_config(self):
        self.initial_wavelength = self.require_config("initial_wavelength")
        self.final_wavelength = self.require_config("final_wavelength")
        self.set_wavelength(self.initial_wavelength)
        self.step_size = self.require_config("step_size")

    def measure(self) -> dict:
        self.wavelength = round(self.wavelength, 2)
        self.data["wavelength (nm)"] = [self.wavelength]
        if self.connect_to_rex:
            payload = self.create_payload()
            self.tcp_send(payload, self.sock)
        return self.data
    
    def set_wavelength(self, wavelength):
        self.wavelength = wavelength

    def spectrometer_step(self) -> None:
        """
        Move the wavelength by one step size increment.
        
        Advances the wavelength by the configured step_size value.
        """        
        self.set_wavelength(self.wavelength + self.step_size)

    def total_steps(self) -> int:
        """
        Return the total number of steps for the current configuration 
        """             
        return abs(int((self.final_wavelength - self.initial_wavelength) / self.step_size))             
            