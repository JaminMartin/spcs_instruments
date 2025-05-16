from ...spcs_instruments_utils import rex_support
import seabreeze
from seabreeze.spectrometers import Spectrometer
@rex_support
class Ocean_optics_spectrometer:
    """A class to control and interact with an OceanOptics Spectrometer.

    Attributes:
        name (str): Name identifier for the device.
        config (dict): Configuration settings for the device.
        connect_to_rex (bool): Indicates whether to connect to the rex experiment manager.
        sock (socket, optional): Socket connection for rex, if enabled.
        data (dict): Stores measurement data.
        __toml_config__ (dict): Default configuration template for the device
    """

    __toml_config__ = {
    "device.OceanOpitics_Spectrometer": {
        "_section_description": "OceanOpitics_Spectrometer measurement configuration",
        "integration_time": {
            "_value": 50000,
            "_description": "Integration time in microseconds"
        },
        "averages": {
            "_value": 1,
            "_description": "Number of averages"
        },
        "upper_limit":{
            "_value": 600, 
            "_description": "Upper wavelength range"
        },   
        "lower_limit":{
            "_value": 500, 
            "_description": "Lower wavelength range"
        },
        "backend":{
            "_value": "pyseabreeze",
            "_description": "which backend to use to connect, options: 'pyseabreeze', 'cseabreeze'"
        },

    }}
    def __init__(self, config, name="OceanOpitics_Spectrometer", connect_to_rex=True):
        """
        A simulated device
        """
        self.name = name
        self.connect_to_rex = connect_to_rex
        self.config = self.bind_config(config)
        
        self.logger.debug(f"{self.name} connected with this config {self.config}")
        
        if self.connect_to_rex:
            self.sock = self.tcp_connect()
        self.setup_config()
        self.spec = Spectrometer.from_first_available()
        self.data = {
            "wavelength (nm)": [[]],
            "intensity (cps)": [[]],
        }

    def setup_config(self):
        self.integration_time  = self.require_config("integration_time")
        self.spec.integration_time_micros(self.integration_time)
        self.lower_limit = self.require_config("lower_limit")
        self.upper_limit = self.require_config("upper_limit")
        self.averages = self.require_config("averages")
        self.backend = self.require_config("backend")
        seabreeze.use(self.backend)
        
        


    def measure(self) -> dict:
        self.wavelength = None
        self.intensity = None
        try:
            if self.averages > 1:
               for i in range(self.averages):
 
                   if self.wavelength is None:
             
                        self.wavelength = self.spec.wavelengths()
                        self.intensity = self.spec.intensities()
                        self.logger.debug(f"{self.intensity}")
                   else:
              
                        self.intensity += self.spec.intensities()
                        self.logger.debug(f"{self.intensity}")
               self.intensity = self.intensity / self.averages         
               self.intensity = self.intensity.tolist()
               self.wavelength = self.wavelength.tolist()
            else:
                self.wavelength = self.spec.wavelengths().tolist()
                self.intensity = self.spec.intensities().tolist()

            lower_bound, upper_bound = self.bounds(self.wavelength, self.lower_limit, self.upper_limit)
            self.data["wavelength (nm)"] = [self.wavelength[lower_bound:upper_bound]]
            self.data["intensity (cps)"] = [self.intensity[lower_bound:upper_bound]]
            if self.connect_to_rex:
                payload = self.create_payload()
                self.tcp_send(payload, self.sock)
            return self.data
        except Exception as e: self.logger.error(f"Error: {e}")

    def bounds(self, data: list, lower_limit: float, upper_limit: float) -> tuple:
        
        lower_bound = min(range(len(data)), key=lambda i: abs(data[i] - lower_limit))
        upper_bound = min(range(len(data)), key=lambda i: abs(data[i] - upper_limit))
        upper_bound = min(upper_bound + 1, len(data))

        return lower_bound, upper_bound
