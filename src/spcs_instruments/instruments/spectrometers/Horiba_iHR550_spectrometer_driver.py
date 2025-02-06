from ...spcs_instruments_utils import pyfex_support, DeviceError 
import time
import struct
import time
from typing import Dict
import usb.core
import math

@pyfex_support
class HoribaiHR550:
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
        0: "Front_Entrance",
        1: "Front_Side",
        2: "Exit_Front",
        3: "Exit_Side"
    }
    def __init__(self):
        """
        Initialize spectrometer with configuration.
        """
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
        
  
        self.update_state()
    def close(self):
        """
        Releases the USB device and frees resources.
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
     
        self._dev.ctrl_transfer(
            self.B_REQUEST_OUT,
            self.BM_REQUEST_TYPE,
            wValue=value,
            wIndex=cmd_index,
            data_or_wLength=data
        )
        
    def _usb_read(self, cmd_index: int, length: int = 4, value: int = 0) -> bytes:

        return self._dev.ctrl_transfer(
            self.B_REQUEST_IN,
            self.BM_REQUEST_TYPE,
            wValue=value,
            wIndex=cmd_index,
            data_or_wLength=length
        )
        
    def is_busy(self) -> bool:
        """Check if the spectrometer is busy."""
        try:
            busy_bytes = self._usb_read(self.CMD_BUSY)
            # The device returns an integer where 0 is not busy and nonzero means busy.
            busy_flag = struct.unpack("<i", busy_bytes)[0]
            return bool(busy_flag)
        except Exception as e:
            print(f"Error reading busy state: {e}")
            return True
        
    def wait_until_not_busy(self, poll_interval: float = 0.05, timeout: float = 30.0) -> None:
        """
        Wait until the device reports it is not busy.
        
        poll_interval: How often (in seconds) to check the busy flag.
        timeout: Maximum time (in seconds) to wait before raising an error.
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
        """Update the device state.
           (This method could be called periodically if needed.)
        """
        try:
            #self.wait_until_not_busy(timeout=timeout)
            turret_idx = self.get_turret()
            turret_name = self.TURRET_MAPPING.get(turret_idx) 
            print(turret_name)
            self._state["turret"] = turret_name


            wavelength_bytes = self._usb_read(self.CMD_WAVELENGTH_READ)
            wavelength = struct.unpack("<f", wavelength_bytes)[0]
            print(f"raw:{wavelength}")
            grating = self.hardware_config["gratings"][self._state["turret"]]
            adjusted_wavelength = wavelength / (grating["lines_per_mm"] / 1200.0)
            self._state["position"] = adjusted_wavelength
            
            #mirrors
            for index, name in self.MIRROR_MAPPING.items():
                self._state["mirrors"][name] = self.get_mirror(index)
            #slits
            for index, name in self.SLIT_MAPPING.items():
    
                match index:
                    case 0:
                        self._state["slits"]["Entrance"]["Front"] = self.get_slit(index)
                    case 1:
                        self._state["slits"]["Entrance"]["Side"] = self.get_slit(index)
                    case 2:
                        self._state["slits"]["Exit"]["Front"] = self.get_slit(index)
                    case 3:
                        self._state["slits"]["Exit"]["Side"] = self.get_slit(index)

        except Exception as e:
            print(f"Error updating state: {e}")
        
    def set_wavelength(self, wavelength: float, timeout: float = 30.0) -> None:
        """Set the wavelength and wait for movement to complete."""
        if self._state["turret"] not in self.hardware_config["gratings"]:
            raise ValueError("Invalid turret configuration")
            
        grating = self.hardware_config[self._state["turret"]]

        adjusted_wavelength = wavelength * (grating["lines_per_mm"] / 1200.0)

        self.wait_until_not_busy(timeout=timeout)

        self._usb_write(
            self.CMD_WAVELENGTH_SET,
            struct.pack("<f", adjusted_wavelength)
        )
        
    
        self.wait_until_not_busy(timeout=timeout)
        self.update_state()

            
    def get_wavelength(self) -> float:
        """Return the current wavelength (state)."""
        return self._state["position"]
        
    def set_turret(self, turret: str, timeout: float = 400.0) -> None:
        """Set the grating turret position and wait for it to settle."""
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
        

    def set_slit(self, index: int, width: float, timeout: float =30.00):
        """Set slit with index to width (in mm)"""
        if math.isnan(width):
            return
        self.wait_until_not_busy(timeout=timeout)
        
        const = self.slit_type / 1000
        self._usb_write(
            self.CMD_SET_SLITWIDTH,
            struct.pack("<i", round(width / const)),
            index
        )    
        self.wait_until_not_busy(timeout=timeout)
        time.sleep(6)
        self.update_state()
   
    
    def get_slit(self, index: int, timeout: float = 30.00) -> float:
        self.wait_until_not_busy(timeout=timeout)
        const = self.slit_type / 1000
        data = self._usb_read(self.CMD_READ_SLITWIDTH, value=index)
        return const * struct.unpack("<i", data)[0]
    
    def get_turret(self, timeout: float = 30.00) -> float:
        self.wait_until_not_busy(timeout=timeout)
 
        data = self._usb_read(self.CMD_TURRET_READ)
           
        return struct.unpack("<i", data)[0]
    
    def initialize(self, timeout: float = 90.0) -> None:
        """Initialize/home the spectrometer and wait until homing is complete."""
        self._usb_write(self.CMD_INIT, b'')
        
       
        time.sleep(3)
        self.wait_until_not_busy(timeout=timeout)  

        time.sleep(10)
        self.update_state()

    def setup_device(self) -> None:
        pass

    def get_mirror(self, index: int, timeout: float = 30.0):
        self.wait_until_not_busy(timeout=timeout)
        data = self._usb_read(cmd_index = self.CMD_READ_MIRROR, value= index)
        return "side" if bool(struct.unpack("<i", data)[0]) else "front"
    
    def set_mirror(self, port: str, side: str, timeout: float = 30.00):
        """Set mirror with index to front or side"""
        self.wait_until_not_busy(timeout=timeout)
        index = self.hardware_config["mirrors"][port]
        self._usb_write(self.CMD_SET_MIRROR, data=struct.pack("<i", side == "side"), value=index)
        self.wait_until_not_busy(timeout=timeout)
        time.sleep(10)
        self.update_state()

  
