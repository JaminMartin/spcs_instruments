import ctypes
import time
import numpy as np
from typing import TypeVar
from ..spcs_instruments_utils import load_config, pyfex_support, DeviceError 


Pointer_c_ulong = TypeVar("Pointer_c_ulong")


@pyfex_support
class C8855_counting_unit:
    """Class for controlling the C8855 photon counting unit.
    
    Attributes:
        gate_time_mapping (dict): Maps human-readable gate times to corresponding hexadecimal values.
        transfer_type_mapping (dict): Maps transfer types to their respective integer values.
        trigger_type_mapping (dict): Maps trigger modes to their respective integer values.
        name (str): Name identifier for the device.
        config (dict): Configuration settings for the device.
        connect_to_pyfex (bool): Indicates whether to connect to the PyFex experiment manager.
        sock (socket, optional): Socket connection for PyFex, if enabled.
        data (dict): Stores measurement data.
        __toml_config__ (dict): Default configuration template for the device
    """
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

    gate_time_mapping = {
        '50us': 0x02,
        '100us': 0x03,
        '200us': 0x04,
        '500us': 0x05,
        '1ms': 0x06,
        '2ms': 0x07,
        '5ms': 0x08,
        '10ms': 0x09,
        '20ms': 0x0A,
        '50ms': 0x0B,
        '100ms': 0x0C,
        '200ms': 0x0D,
        '500ms': 0x0E,
        '1s': 0x0F,
        '2s': 0x10,
        '5s': 0x11,
        '10s': 0x12,
    }

    # Transfer mode settings
    transfer_type_mapping = {
        'single_transfer' : 1,
        'block_transfer' : 2
    }


    C8855_SINGLE_TRANSFER = 1
    C8855_BLOCK_TRANSFER = 2

    trigger_type_mapping = {
        'software' : 0,
        'external' : 1
    }

    # Trigger mode settings
    C8855_SOFTWARE_TRIGGER = 0
    C8855_EXTERNAL_TRIGGER = 1
    __toml_config__ = {
    "device.C8855_photon_counter": {
        "_section_description": "C8855_photon_counter measurement configuration",
        "transfer_type": {
            "_value": "block_transfer",
            "_description": "Transfer type, working and validated transfer type is 'block_transfer' however 'single_transfer' is available."
        },
        "number_of_gates": {
            "_value": 512,
            "_description": "Number of gates: 2,4,8,16,32,64,128,256,512"
        },
        "gate_time":{
            "_value": "500us", 
            "_description": "Gate time to use, e.g. '500us' or '1ms', or '2ms' etc. available gate times: '50us': 0x02,'100us','200us','500us','1ms','2ms','5ms','10ms','20ms','50ms','100ms','200ms','500ms','1s','2s','5s','10s'"
        },   
        "trigger_type":{
            "_value": "external", 
            "_description": "Type of device triggering to use (external, software)"
        },
        "averages":{
            "_value": 16, 
            "_description": "Number of averages to take"
        },
        "measure_mode":{
            "_value": "counts_only", 
            "_description": "Measurement mode to use, counts only (counts_only), trace only (trace), or both as a tupple (all)"
        },
        "dll_path":{
            "_value": "/path/to/dll", 
            "_description": "DLL path to use for C8855 photon counter"
        }
    }}
    def __init__(self, config: str, name: str='C8855_photon_counter', connect_to_pyfex=True):
        """
        Initializes the C8855 photon counting unit.
        
        Args:
            config (str): Path to the configuration file.
            name (str, optional): Name identifier for the device. Defaults to 'C8855_photon_counter'.
            connect_to_pyfex (bool, optional): Whether to connect to the PyFex experiment manager. Defaults to True.
        """
        self.name = name
        self.config = self.bind_config(config)
        self.connect_to_pyfex = connect_to_pyfex
        
        if self.connect_to_pyfex:
            self.sock = self.tcp_connect()
        self.data = {
            'counts': []
        }
        self.setup_config()

    def setup_config(self):
        """Loads device configuration and initializes the DLL functions."""
        self.number_of_gates = self.require_config('number_of_gates')
        self.transfer_type = self.transfer_type_mapping[self.require_config('transfer_type')]
        self.gate_time = self.gate_time_mapping[self.require_config('gate_time')]
        self.trigger_type = self.trigger_type_mapping[self.require_config('trigger_type')]
        self.averages = self.require_config('averages')
        self.measure_mode = self.require_config("measure_mode")
        dll_path = self.require_config("dll_path")
        self.dll= ctypes.WinDLL(dll_path)
        self.dll.C8855CountStop.argtypes = [ctypes.c_void_p]
        self.dll.C8855CountStop.restype = ctypes.c_bool
        self.dll.C8855ReadData.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong), ctypes.POINTER(ctypes.c_ubyte)]
        self.dll.C8855ReadData.restype = ctypes.c_bool
        self.dll.C8855CountStart.argtypes = [ctypes.c_void_p, ctypes.c_ubyte]
        self.dll.C8855CountStart.restype = ctypes.c_bool
        self.dll.C8855Setup.argtypes = [ctypes.c_void_p, ctypes.c_ubyte, ctypes.c_ubyte, ctypes.c_ushort]
        self.dll.C8855Setup.restype = ctypes.c_bool
        self.dll.C8855Close.argtypes = [ctypes.c_void_p]
        self.dll.C8855Close.restype = ctypes.c_bool 
        self.dll.C8855Reset.argtypes = [ctypes.c_void_p]
        self.dll.C8855Reset.restype = ctypes.c_bool
        self.dll.C8855Open.argtypes = []
        self.dll.C8855Open.restype = ctypes.c_void_p  # Assuming the handle is a void pointer



    def general_measurement(self):
        """
        Performs a single measurement cycle, including resetting, setting up, starting, reading, and stopping.
        """

        self.device_handle = self.open_device()

        if self.device_handle:
            success = self.reset_device(self.device_handle)
            if success:
                self.logger.debug('C8855Reset succeeded.')
            else:
                self.logger.error('C8855 Reset failed.')
        else:
            self.logger.error('Device handle not obtained. Initialization failed.')

        if self.device_handle:
            success = self.setup_device(self.device_handle, gate_time=self.gate_time, transfer_mode=self.transfer_type, number_of_gates=self.number_of_gates)
            if success:
                self.logger.debug('Device setup succeeded.')
            else:
                self.logger.error('Device setup failed.')
        else:
            self.logger.error('Device handle not obtained. Initialization failed.')
        success = self.start_counting(self.device_handle, self.trigger_type)
        if success:
            self.logger.debug('Counting started.')
        else:
            self.logger.error('C8855 Start failed.')



        data_buffer = (ctypes.c_ulong * 1024)()
        overall_start_time = time.time()
        

        self.read_data(self.device_handle, data_buffer)



        success = self.stop_counting(self.device_handle)
        if success:
            self.logger.debug('Counting stopped.')
        else:
            self.logger.error('Counting stop failed.')
        time.sleep(0.1)    



        self.bin_counts = np.asarray(list(data_buffer))
        self.bin_counts = self.bin_counts[:512-(512-self.number_of_gates)]
        self.counts = np.sum(self.bin_counts)
        self.bin_averages += self.bin_counts
        self.total_counts += self.counts
    
        success = self.reset_device(self.device_handle)
        if success:
            self.logger.debug('C8855Reset succeeded.')
        else:
            self.logger.error('C8855 Reset failed.')
    def stop_counting(self, handle: ctypes.c_void_p) -> bool:
        """
        Stops the photon counting process.

        Args:
            handle (ctypes.c_void_p): A handle to the C8855 device.

        Returns:
            bool: True if the counting was successfully stopped, False otherwise.
        """
        return self.dll.C8855CountStop(handle)
    
    def measure(self):
        """
        Conducts multiple measurements based on the configured number of averages.
        
        Returns:
            float | tuple: Depending on measure_mode, returns either total count, trace data, or both.
        """
        self.bin_averages = 0
        self.total_counts = 0
        if self.averages == 0:
            self.averages = 1
            
        for i in range(self.averages):
            self.general_measurement()

        bin_average_array = self.bin_averages/self.averages   
        count_average = self.total_counts/self.averages 
        #only return counts until trace data is implemented in PyFex
        self.data["counts"] = [count_average]
        if self.connect_to_pyfex:
            payload = self.create_payload()
            self.tcp_send(payload, self.sock)

        match self.measure_mode:
            case "all":
                return (bin_average_array),(count_average)    
            case "counts_only":
                return count_average
            case "trace":
                return bin_average_array 
            case _:
                raise DeviceError("Measurement mode not specified correctly")


    def open_device(self) -> ctypes.c_void_p:
        """
        Opens a connection to the device.
        
        Returns:
            ctypes.c_void_p: Handle to the device.
        """
        return self.dll.C8855Open()


    def reset_device(self, handle: ctypes.c_void_p) -> bool:
        """
        Resets the device to its default state.
        
        Args:
            handle (ctypes.c_void_p): Device handle.
        
        Returns:
            bool: True if successful, False otherwise.
        """
        return self.dll.C8855Reset(handle)


    def close_device(self, handle: ctypes.c_void_p) -> int:
        """
        Closes the connection to the device.
        
        Args:
            handle (ctypes.c_void_p): Device handle.
        
        Returns:
            int: Status of the close operation.
        """
        result = self.dll.C8855Close(handle)
        return result


    def setup_device(self, handle: ctypes.c_void_p, gate_time: ctypes.c_ubyte, transfer_mode: ctypes.c_ubyte, number_of_gates: ctypes.c_ushort) -> bool:
        """
        Configures the device with the specified parameters.
        
        Args:
            handle (ctypes.c_void_p): Device handle.
            gate_time (ctypes.c_ubyte): Gate time setting.
            transfer_mode (ctypes.c_ubyte): Transfer mode setting.
            number_of_gates (ctypes.c_ushort): Number of gates for measurement.
        
        Returns:
            bool: True if setup was successful, False otherwise.
        """
        return self.dll.C8855Setup(handle, gate_time, transfer_mode, number_of_gates)



    def start_counting(self, handle: ctypes.c_void_p, trigger_mode:ctypes.c_ubyte =C8855_EXTERNAL_TRIGGER) -> bool:
        """
        Starts the counting process.
        
        Args:
            handle (ctypes.c_void_p): Device handle.
            trigger_mode (ctypes.c_ubyte, optional): Trigger mode. Defaults to C8855_EXTERNAL_TRIGGER.
        
        Returns:
            bool: True if counting started successfully, False otherwise.
        """
        return self.dll.C8855CountStart(handle, trigger_mode)




    def read_data(self, handle:ctypes.c_void_p, data_buffer:Pointer_c_ulong):
        """
        Reads data from the device into the provided buffer.
        
        Args:
            handle (ctypes.c_void_p): Device handle.
            data_buffer (Pointer_c_ulong): Buffer to store retrieved data.
        """
        result_returned = ctypes.c_ubyte()
        _ = self.dll.C8855ReadData(handle, data_buffer, ctypes.byref(result_returned))