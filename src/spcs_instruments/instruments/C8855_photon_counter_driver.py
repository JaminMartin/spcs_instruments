import ctypes
import os
import time
from typing import TypeVar
from ..spcs_instruments_utils import load_config, tcp_connect, tcp_send, pyfex_support, DeviceError 


Pointer_c_ulong = TypeVar("Pointer_c_ulong")
# Get the absolute path to the DLL
dll_path = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "c8855-01api-x64.dll"
)
# Load the DLL
dll = ctypes.WinDLL(dll_path)



# Define the function connection
dll.C8855Open.argtypes = []
dll.C8855Open.restype = ctypes.c_void_p  # Assuming the handle is a void pointer
def open_device() -> ctypes.c_void_p:
    return dll.C8855Open()

# Function to reset the device
dll.C8855Reset.argtypes = [ctypes.c_void_p]
dll.C8855Reset.restype = ctypes.c_bool
def reset_device(handle: ctypes.c_void_p) -> bool:
    return dll.C8855Reset(handle)

# Define connection
dll.C8855Close.argtypes = [ctypes.c_void_p]
dll.C8855Close.restype = ctypes.c_bool 
def close_device(handle: ctypes.c_void_p) -> int:
    result = dll.C8855Close(handle)
    return result


# Define  C8855Setup
dll.C8855Setup.argtypes = [ctypes.c_void_p, ctypes.c_ubyte, ctypes.c_ubyte, ctypes.c_ushort]
dll.C8855Setup.restype = ctypes.c_bool

def setup_device(handle: ctypes.c_void_p, gate_time: ctypes.c_ubyte, transfer_mode: ctypes.c_ubyte, number_of_gate: ctypes.c_ushort) -> bool:
    return dll.C8855Setup(handle, gate_time, transfer_mode, number_of_gate)

# Gate time settings
C8855_GATETIME_50US = 0x02
C8855_GATETIME_100US = 0x03
C8855_GATETIME_200US = 0x04
C8855_GATETIME_500US = 0x05
C8855_GATETIME_1MS = 0x06
C8855_GATETIME_2MS = 0x07
C8855_GATETIME_5MS = 0x08
C8855_GATETIME_10MS = 0x09
C8855_GATETIME_20MS = 0x0A
C8855_GATETIME_50MS = 0x0B
C8855_GATETIME_100MS = 0x0C
C8855_GATETIME_200MS = 0x0D
C8855_GATETIME_500MS = 0x0E
C8855_GATETIME_1S = 0x0F
C8855_GATETIME_2S = 0x10
C8855_GATETIME_5S = 0x11
C8855_GATETIME_10S = 0x12

# Transfer mode settings
C8855_SINGLE_TRANSFER = 1
C8855_BLOCK_TRANSFER = 2

# Trigger mode settings
C8855_SOFTWARE_TRIGGER = 0
C8855_EXTERNAL_TRIGGER = 1

# Define C8855CountStart
dll.C8855CountStart.argtypes = [ctypes.c_void_p, ctypes.c_ubyte]
dll.C8855CountStart.restype = ctypes.c_bool

# Function to start the counting process
def start_counting(handle: ctypes.c_void_p, trigger_mode:ctypes.c_ubyte =C8855_EXTERNAL_TRIGGER) -> bool:
    return dll.C8855CountStart(handle, trigger_mode)


def find_gate_packet(time):
    'takes a string from config file and returns packet numer'
    
    






@pyfex_support
class counting_unit:
    """Create class for the photon counting unit. (M.Moull 05/02/25)"""


    def __init__(self, config: str, name: str='counting_unit'):

        self.name = name

        self.config = self.bind_config(config)
        self.sock = self.tcp_connect()
        self.data = {
            'counts': []
        }

    def setup_config(self):
        self.number_of_bins = require_config('number_of_bins')
        self.trigger_type = require_config('trigger_type')




    
    



