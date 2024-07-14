import ctypes
import os
import time
from typing import TypeVar

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
dll.C8855Setup.argtypes = [
    ctypes.c_void_p,
    ctypes.c_ubyte,
    ctypes.c_ubyte,
    ctypes.c_ushort,
]
dll.C8855Setup.restype = ctypes.c_bool


def setup_device(
    handle: ctypes.c_void_p,
    gate_time: ctypes.c_ubyte,
    transfer_mode: ctypes.c_ubyte,
    number_of_gate: ctypes.c_ushort,
) -> bool:
    return dll.C8855Setup(handle, gate_time, transfer_mode, number_of_gate)


# Gate time settings
C8855_GATETIME_50US = 0x02
C8855_GATETIME_100US = 0x03
C8855_GATETIME_200US = 0x04
C8855_GATETIME_500US = 0x05
C8855_GATETIME_1MS = 0x06
C8855_GATETIME_1MS = 0x07
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
def start_counting(
    handle: ctypes.c_void_p, trigger_mode: ctypes.c_ubyte = C8855_SOFTWARE_TRIGGER
) -> bool:
    return dll.C8855CountStart(handle, trigger_mode)


# Define C8855ReadData
dll.C8855ReadData.argtypes = [
    ctypes.c_void_p,
    ctypes.POINTER(ctypes.c_ulong),
    ctypes.POINTER(ctypes.c_ubyte),
]
dll.C8855ReadData.restype = ctypes.c_bool

# Function to read data from the device


def read_data(handle: ctypes.c_void_p, data_buffer: Pointer_c_ulong):
    result_returned = ctypes.c_ubyte()
    success = dll.C8855ReadData(handle, data_buffer, ctypes.byref(result_returned))

    if success:
        print("Data read succeeded.")
        print(f"ResultReturned: {result_returned.value}")
    else:
        print("Data read failed.")


# Define the function prototype for C8855CountStop
dll.C8855CountStop.argtypes = [ctypes.c_void_p]
dll.C8855CountStop.restype = ctypes.c_bool


# Function to stop the counting process
def stop_counting(handle: ctypes.c_void_p) -> bool:
    return dll.C8855CountStop(handle)


# TODO!
# create a higher level measurement class to simplify the API for future integrations
# this could be as simple as an abstraction over the loop run below. For versatility it could also return a tuple of the array and sum of counts
if __name__ == "__main__":
    # Example usage
    # Call the function to connect to the device
    device_handle = open_device()

    # Check if the handle is valid
    print(f"Photon counter handle: {device_handle}")

    if device_handle:
        success = reset_device(device_handle)
        if success:
            print("C8855Reset succeeded.")
        else:
            print("C8855Reset failed.")
    else:
        print("Device handle not obtained. Initialization failed.")

    for i in range(5):
        if device_handle:
            success = setup_device(
                device_handle,
                gate_time=C8855_GATETIME_50US,
                transfer_mode=C8855_BLOCK_TRANSFER,
                number_of_gate=32,
            )
            if success:
                print("Device setup succeeded.")
            else:
                print("Device setup failed.")
        else:
            print("Device handle not obtained. Initialization failed.")

        success = start_counting(device_handle)
        if success:
            print("Counting started.")
        else:
            print("Counting start failed.")

        # Wait for the data to be ready

        data_buffer = (ctypes.c_ulong * 1024)()
        overall_start_time = time.time()
        read_data(device_handle, data_buffer)

        # Calculate and print the overall elapsed time

        success = stop_counting(device_handle)
        if success:
            print("Counting stopped.")
        else:
            print("Counting stop failed.")
        time.sleep(1)

        print(list(data_buffer))

        success = reset_device(device_handle)
        if success:
            print("C8855Reset succeeded.")
        else:
            print("C8855Reset failed.")

    # Call the function to disconnect the device
    result = close_device(device_handle)
    print("closing photon counter")
    print(f"counter closed: {result}")
