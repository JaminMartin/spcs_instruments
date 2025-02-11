from ...spcs_instruments_utils import pyfex_support, DeviceError 
import time
import struct
import time
from typing import Dict
import usb.core
import math

@pyfex_support
class HoribaiHR550:
    """
    A class to control and interface with the Horiba iHR550 Spectrometer via libusb.
    
    This class provides a control interface for the iHR550 spectrometer including
    wavelength control, grating selection, mirror positioning, and slit width adjustment.
    
    Attributes:
        VENDOR_ID (int): USB vendor ID for the device (0xC9B)
        PRODUCT_ID (int): USB product ID for the device (0x101)
        LANG_ID_US_ENGLISH (int): Language ID for US English (0x409)
        B_REQUEST_OUT (int): USB output request type (0x40)
        B_REQUEST_IN (int): USB input request type (0xC0)
        BM_REQUEST_TYPE (int): USB request type (0xB3)
        CMD_WAVELENGTH_SET (int): Command index for setting wavelength (4)
        CMD_WAVELENGTH_READ (int): Command index for reading wavelength (2)
        CMD_TURRET_SET (int): Command index for setting turret (17)
        CMD_TURRET_READ (int): Command index for reading turret (16)
        CMD_BUSY (int): Command index for checking busy status (5)
        CMD_INIT (int): Command index for initialization (0)
        CMD_SET_MIRROR (int): Command index for setting mirror (41)
        CMD_READ_MIRROR (int): Command index for reading mirror (40)
        CMD_SET_SLITWIDTH (int): Command index for setting slit width (33)
        CMD_READ_SLITWIDTH (int): Command index for reading slit width (32)
        TURRET_MAPPING (dict): Maps turret indices to grating names
        MIRROR_MAPPING (dict): Maps mirror indices to names
        SLIT_MAPPING (dict): Maps slit names to their indices
        __toml_config__ (dict): Default configuration template for the device
        bypass_homing (bool): Whether to skip the homing sequence
        slit_type (int): Type of slit mechanism (hardcoded to 7)
        hardware_config (dict): Contains gratings and mirrors configuration
        _state (dict): Current state of device (position, turret, mirrors, slits)
        _dev (usb.core.Device): USB device instance
        data (dict): Measurement data storage
        config: Bound configuration as defined by the user
        connect_to_pyfex (bool): Whether to connect to pyfex experiment manager
        sock: Socket connection when pyfex is enabled
        step_size (float): Step size for measurements (default 0.1nm)
        start_wavelength (float): Initial start wavelength (default 500nm)
        final_wavelength (float): End wavelength for a measurement (default 600nm)
    """
    # USB constants
    VENDOR_ID = 0xC9B
    PRODUCT_ID = 0x101  
    LANG_ID_US_ENGLISH = 0x409
    
    # USB command constants
    B_REQUEST_OUT = 0x40
    B_REQUEST_IN = 0xC0
    BM_REQUEST_TYPE = 0xB3
    
    # Command indices
    CMD_WAVELENGTH_SET = 4
    CMD_WAVELENGTH_READ = 2
    CMD_TURRET_SET = 17
    CMD_TURRET_READ = 16
    CMD_BUSY = 5
    CMD_INIT = 0
    CMD_SET_MIRROR = 41
    CMD_READ_MIRROR = 40
    CMD_SET_SLITWIDTH = 33
    CMD_READ_SLITWIDTH = 32
    
    TURRET_MAPPING = {
    0: "VIS",
    1: "NIR",
    2: "MIR",
    }
    MIRROR_MAPPING = {
        0: "Entrance",
        1: "Exit"
    }
    SLIT_MAPPING = {
        "Entrance_Front": 0,
        "Entrance_Side": 1,
        "Exit_Front": 2,
        "Exit_Side": 3,
    }


    __toml_config__ = {
    "device.iHR550": {
        "_section_description": "IHR550 measurement configuration",
        "grating": {
            "_value": "VIS",
            "_description": "Valid grating name to be used for the measurement, options: VIS, NIR, MIR"
        },
        "step_size": {
            "_value": 0.1,
            "_description": "Step size in nm"
        },
        "initial_wavelength": {
            "_value": 500,
            "_description": "Start wavelength (nm)"
        },
        "final_wavelength":{
            "_value": 500, 
            "_description": "Stop wavelength in (nm)"
        }
    },
    "device.iHR550.slits": {
        "_section_description": "Slit configuration settings",
        "Entrance_Front": {
            "_value": 0.5,
            "_description": "Entrance front slit width in mm"
        },
        "Entrance_Side": {
            "_value": 0.0,
            "_description": "Entrance side slit width in mm"
        },
        "Exit_Front": {
            "_value": 0.5,
            "_description": "Exit front slit width in mm"
        },
        "Exit_Side": {
            "_value": 0.0,
            "_description": "Exit side slit width in mm"
        } 
    },
    "device.iHR550.mirrors": {
        "_section_description": "Mirror configuration settings",
        "Entrance": {
            "_value": "front",
            "_description": "Orientation of extrance mirror"
        },
       "Exit": {
           "_value": "side",
           "_description": "Orientation of exit mirror"
       } 
    }

}
    def __init__(self, config:str, name="iHR550", bypass_homing: bool = False, connect_to_pyfex=True):
        """
        Initialize the spectrometer with the given configuration.

        Args:
            config (str): Configuration string or path for the device
            name (str, optional): Device name. Defaults to "iHR550"
            bypass_homing (bool, optional): Skip homing sequence if True. Defaults to False
            connect_to_pyfex (bool, optional): Enable connection to pyfex. Defaults to True

        Raises:
            RuntimeError: If the spectrometer device cannot be found
        """
        self.name = name
        self.bypass_homing = bypass_homing
        self.slit_type = 7 # hardcoded for now
        self.hardware_config  = {
            "gratings": {
                "VIS": {"index": 0, "lines_per_mm": 1200},
                "NIR": {"index": 1, "lines_per_mm": 600},
                "MIR": {"index": 2, "lines_per_mm": 300},
                },
            "mirrors":{
                "Entrance": 0,
                "Exit": 1,
            }
                 }
        
        self._state = {
            "position":"",
            "turret": "",
            "mirrors": {
                "Entrance": "",
                "Exit": ""
            },
            "slits":{
                "Entrance": {"Front": '', "Side": ''},
                "Exit": {"Front": '', "Side": ''},
            }
        }
        
    
        self._dev = usb.core.find(idVendor=self.VENDOR_ID, idProduct=self.PRODUCT_ID)
        if self._dev is None:
            raise RuntimeError("Spectrometer not found")
            

        self._dev._langids = (self.LANG_ID_US_ENGLISH,)
        
        self.data = {
                "wavelength (nm)": [],
            }

  
        self.update_state()
        
        self.config = self.bind_config(config)
        
        self.connect_to_pyfex = connect_to_pyfex
        
        if self.connect_to_pyfex:
            self.sock = self.tcp_connect()
        self.initial_wavelength = 500.00
        self.final_wavelength = None   
        self.setup_device()
        
    def close(self):
        """
        Release the USB device and free associated resources.
        
        Should be called when finished using the device to ensure proper cleanup.
        """
        if self._dev:
            usb.util.dispose_resources(self._dev)
            self._dev = None  

    def __del__(self):
        """
        Ensure the device is released when the object is garbage collected.
        """
        self.close() 


    def _usb_write(self, cmd_index: int, data: bytes, value: int = 0) -> None:
        """
        Send a command to the spectrometer via USB.

        Args:
            cmd_index (int): Command index for the operation
            data (bytes): Data to send
            value (int, optional): Value parameter for USB transfer. Defaults to 0
        """
        self._dev.ctrl_transfer(
            self.B_REQUEST_OUT,
            self.BM_REQUEST_TYPE,
            wValue=value,
            wIndex=cmd_index,
            data_or_wLength=data
        )
        
    def _usb_read(self, cmd_index: int, length: int = 4, value: int = 0) -> bytes:
        """
        Read data from the spectrometer via USB.

        Args:
            cmd_index (int): Command index for the operation
            length (int, optional): Number of bytes to read. Defaults to 4
            value (int, optional): Value parameter for USB transfer. Defaults to 0

        Returns:
            bytes: Data read from the device
        """
        return self._dev.ctrl_transfer(
            self.B_REQUEST_IN,
            self.BM_REQUEST_TYPE,
            wValue=value,
            wIndex=cmd_index,
            data_or_wLength=length
        )
        
    def is_busy(self) -> bool:
        """
        Check if the spectrometer is currently busy.

        Returns:
            bool: True if the device is busy, False otherwise

        Raises:
            Exception: If there's an error reading the busy state
        """           
        try:
            busy_bytes = self._usb_read(self.CMD_BUSY)
            # The device returns an integer where 0 is not busy and nonzero means busy.
            busy_flag = struct.unpack("<i", busy_bytes)[0]
            return bool(busy_flag)
        except Exception as e:
            self.logger.error(f"Error reading busy state: {e}")
            return True
        
    def wait_until_not_busy(self, poll_interval: float = 0.05, timeout: float = 30.0) -> None:
        """
        Wait until the device reports it is not busy.

        Args:
            poll_interval (float, optional): Time between checks in seconds. Defaults to 0.05
            timeout (float, optional): Maximum wait time in seconds. Defaults to 30.0

        Raises:
            TimeoutError: If device remains busy longer than timeout period
        """
        
        start_time = time.time()
        
        while True:
            busy = self.is_busy()  
        
            
            if not busy:
    
                return  
            
            if time.time() - start_time > timeout:
                raise TimeoutError("Device remained busy for too long")
            
         
            time.sleep(poll_interval)

        
    def update_state(self, timeout: float = 30.0) -> None:
        """
        Update the internal state of the device by reading current settings.

        Updates turret position, wavelength, mirror positions, and slit widths.

        Args:
            timeout (float, optional): Maximum time to wait for updates in seconds. Defaults to 30.0
        """        

        turret_idx = self.get_turret()
        turret_name = self.TURRET_MAPPING.get(turret_idx) 
        self._state["turret"] = turret_name


        wavelength_bytes = self._usb_read(self.CMD_WAVELENGTH_READ)
        wavelength = struct.unpack("<f", wavelength_bytes)[0]
        grating = self.hardware_config["gratings"][self._state["turret"]]
        adjusted_wavelength = wavelength / (grating["lines_per_mm"] / 1200.0)
        self._state["position"] = adjusted_wavelength
        
        #mirrors
        for index, name in self.MIRROR_MAPPING.items():
            self._state["mirrors"][name] = self.get_mirror(index)
        #slits
        for name, index in self.SLIT_MAPPING.items():

            match index:
                case 0:
                    self._state["slits"]["Entrance"]["Front"] = self.get_slit(index)
                case 1:
                    self._state["slits"]["Entrance"]["Side"] = self.get_slit(index)
                case 2:
                    self._state["slits"]["Exit"]["Front"] = self.get_slit(index)
                case 3:
                    self._state["slits"]["Exit"]["Side"] = self.get_slit(index)
        self.logger.debug(self._state)

        
    def set_wavelength(self, wavelength: float, timeout: float = 30.0) -> None:
        """
        Set the spectrometer to a specific wavelength.

        Args:
            wavelength (float): Target wavelength in nanometers
            timeout (float, optional): Maximum time to wait for movement in seconds. Defaults to 30.0

        Raises:
            ValueError: If current turret configuration is invalid
        """        
        if self._state["turret"] not in self.hardware_config["gratings"]:
            raise ValueError("Invalid turret configuration")
            
        grating = self.hardware_config["gratings"][self._state["turret"]]


        adjusted_wavelength = wavelength * (grating["lines_per_mm"] / 1200.0)

        self.wait_until_not_busy(timeout=timeout)

        self._usb_write(
            self.CMD_WAVELENGTH_SET,
            struct.pack("<f", adjusted_wavelength)
        )
        
    
        self.wait_until_not_busy(timeout=timeout)
        self.update_state()

            
    def get_wavelength(self) -> float:
        """
        Get the current wavelength setting.

        Returns:
            float: Current wavelength in nanometers
        """        
        return self._state["position"]
        
    def set_turret(self, turret: str, timeout: float = 400.0) -> None:
        """
        Set the grating turret to a specific position.

        Args:
            turret (str): Desired turret position ("VIS", "NIR", or "MIR")
            timeout (float, optional): Maximum time to wait for movement in seconds. Defaults to 400.0

        Raises:
            ValueError: If specified turret position is invalid
        """        
        if turret not in self.hardware_config["gratings"]:
            raise ValueError(f"Invalid turret position: {turret}")
            
        grating = self.hardware_config["gratings"][turret]
        self._usb_write(
            self.CMD_TURRET_SET,
            struct.pack("<i", grating["index"])
        )
        self.wait_until_not_busy(timeout=timeout)
        time.sleep(10)
        self.update_state()
        

    def set_slit(self, port: str, width: float, timeout: float =30.00):
        """
        Set a specific slit to the desired width.

        Args:
            port (str): Slit identifier (e.g., "Entrance_Front", "Exit_Side")
            width (float): Desired slit width in millimeters
            timeout (float, optional): Maximum time to wait for movement in seconds. Defaults to 30.0
        """        
        if math.isnan(width):
            return
        self.wait_until_not_busy(timeout=timeout)
        
        const = self.slit_type / 1000
        index = self.SLIT_MAPPING[port]
        self._usb_write(
            self.CMD_SET_SLITWIDTH,
            struct.pack("<i", round(width / const)),
            index
        )    
        self.wait_until_not_busy(timeout=timeout)
        time.sleep(6)
        self.update_state()
   
    
    def get_slit(self, index: int, timeout: float = 30.00) -> float:
        """
        Read the width of a specific slit.

        Args:
            index (int): Index of the slit to read
            timeout (float, optional): Maximum time to wait for reading in seconds. Defaults to 30.0

        Returns:
            float: Slit width in millimeters
        """        
        self.wait_until_not_busy(timeout=timeout)
        const = self.slit_type / 1000
        data = self._usb_read(self.CMD_READ_SLITWIDTH, value=index)
        return const * struct.unpack("<i", data)[0]
    
    def get_turret(self, timeout: float = 30.00) -> int:
        """
        Read the current turret position.

        Args:
            timeout (float, optional): Maximum time to wait for reading in seconds. Defaults to 30.0

        Returns:
            int: Current turret index
        """        
        self.wait_until_not_busy(timeout=timeout)
 
        data = self._usb_read(self.CMD_TURRET_READ)
           
        return struct.unpack("<i", data)[0]
    
    def initialize(self, timeout: float = 90.0) -> None:
        """
        Initialize and home the spectrometer.

        If bypass_homing is False, performs a full initialization sequence.

        Args:
            timeout (float, optional): Maximum time to wait for homing in seconds. Defaults to 90.0
        """
        self._usb_write(self.CMD_INIT, b'')
        time.sleep(3)
        self.wait_until_not_busy(timeout=timeout)  
        time.sleep(10)
        self.update_state()

    def setup_device(self) -> None:
        """
        Configure the device according to the current configuration.

        Sets up step size, turret position, initialization, slit widths, mirror positions,
        and initial wavelength according to the configuration.
        """
        self.step_size = self.require_config("step_size")
        self.initial_wavelength = self.require_config("initial_wavelength")
        # Check turret!
        desired_turret = self.require_config("grating")
        
        if desired_turret == self._state["turret"]:
           pass 
        else:
           self.set_turret(desired_turret)
        if self.bypass_homing:
            pass
        else:
            self.initialize()
        desired_slits = self.require_config("slits")
        for key, value in desired_slits.items():
            self.set_slit(key, value)  

        desired_mirror = self.require_config("mirrors")
        for key, value in desired_mirror.items():
            self.set_mirror(key, value)

        self.initial_wavelength = self.require_config("initial_wavelength")
        self.set_wavelength(self.initial_wavelength)        
        

                 
        
    def spectrometer_step(self) -> None:
        """
        Move the wavelength by one step size increment.
        
        Advances the wavelength by the configured step_size value.
        """        
        self.set_wavelength((self._state["position"] + self.step_size))
        
    def measure(self) -> Dict:
        """
        Take a measurement at the current wavelength.

        Returns:
            Dict: Dictionary containing measurement data with wavelength information
        """        
        current_wavelength = round(self._state["position"],2)
        self.data["wavelength (nm)"] = [current_wavelength]
        if self.connect_to_pyfex:
            payload = self.create_payload()
            self.tcp_send(payload, self.sock)
        return self.data
        
    def get_mirror(self, index: int, timeout: float = 30.0):
        """
        Read the current position of a specific mirror.

        Args:
            index (int): Mirror index to read
            timeout (float, optional): Maximum time to wait for reading in seconds. Defaults to 30.0

        Returns:
            str: Mirror position ("side" or "front")
        """        
        self.wait_until_not_busy(timeout=timeout)
        data = self._usb_read(cmd_index = self.CMD_READ_MIRROR, value= index)
        return "side" if bool(struct.unpack("<i", data)[0]) else "front"
    
    def set_mirror(self, port: str, side: str, timeout: float = 30.00):
        """
        Set a specific mirror to the desired position.

        Args:
            port (str): Mirror identifier ("Entrance" or "Exit")
            side (str): Desired position ("side" or "front")
            timeout (float, optional): Maximum time to wait for movement in seconds. Defaults to 30.0
        """        
        self.wait_until_not_busy(timeout=timeout)
        index = self.hardware_config["mirrors"][port]
        self._usb_write(self.CMD_SET_MIRROR, data=struct.pack("<i", side == "side"), value=index)
        self.wait_until_not_busy(timeout=timeout)
        time.sleep(10)
        self.update_state()

  
