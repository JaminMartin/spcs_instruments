import ctypes
import time
import numpy as np
from typing import TypeVar
from ..spcs_instruments_utils import load_config, pyfex_support, DeviceError 


Pointer_c_ulong = TypeVar("Pointer_c_ulong")


@pyfex_support
class C8855_counting_unit:
    """Create class for the photon counting unit. (M.Moull 05/02/25)"""
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

    def __init__(self, config: str, name: str='C8855_photon_counter'):

        self.name = name
        self.config = self.bind_config(config)
        #self.sock = self.tcp_connect()
        self.data = {
            'counts': []
        }

    def test_print(self):
        print("I am working")

    def setup_config(self):
        print('Setting up config')
        self.number_of_gates = self.require_config('number_of_gates')
        self.transfer_type = self.transfer_type_mapping[self.require_config('transfer_type')]
        self.gate_time = self.gate_time_mapping[self.require_config('gate_time')]
        self.trigger_type = self.trigger_type_mapping[self.require_config('trigger_type')]
        self.averages = self.require_config('averages')
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

        print('Setting up config complete')


    def setup_experiment(self):
        """Reset device and then setup device for current measurement"""

        print('Begin experiment setup')
        self.device_handle = self.open_device()

        # Check if the handle is valid
        print(f'Photon counter handle: {self.device_handle}')

        if self.device_handle:
            success = self.reset_device(self.device_handle)
            if success:
                print('C8855Reset succeeded.')
            else:
                print('C8855Reset failed.')
        else:
            print('Device handle not obtained. Initialization failed.')

        if self.device_handle:
            success = self.setup_device(self.device_handle, gate_time=self.gate_time, transfer_mode=self.transfer_type, number_of_gates=self.number_of_gates)
            if success:
                print('Device setup succeeded.')
            else:
                print('Device setup failed.')
        else:
            print('Device handle not obtained. Initialization failed.')
    
    def stop_counting(self, handle: ctypes.c_void_p) -> bool:
        return self.dll.C8855CountStop(handle)
    
    def measure(self):
        self.bin_averages = 0
        self.total_counts = 0
        print(self.averages)
        for i in range(self.averages):
            
            print('Begin experiment setup')
            self.device_handle = self.open_device()


            print(f'Photon counter handle: {self.device_handle}')

            if self.device_handle:
                success = self.reset_device(self.device_handle)
                if success:
                    print('C8855Reset succeeded.')
                else:
                    print('C8855Reset failed.')
            else:
                print('Device handle not obtained. Initialization failed.')

            if self.device_handle:
                success = self.setup_device(self.device_handle, gate_time=self.gate_time, transfer_mode=self.transfer_type, number_of_gates=self.number_of_gates)
                if success:
                    print('Device setup succeeded.')
                else:
                    print('Device setup failed.')
            else:
                print('Device handle not obtained. Initialization failed.')

            success = self.start_counting(self.device_handle, self.trigger_type)
            if success:
                print('Counting started.')
            else:
                print('Counting start failed.')



            data_buffer = (ctypes.c_ulong * 1024)()
            overall_start_time = time.time()
            

            self.read_data(self.device_handle, data_buffer)



            success = self.stop_counting(self.device_handle)
            if success:
                print('Counting stopped.')
            else:
                print('Counting stop failed.')
            time.sleep(1)    


            print(list(data_buffer))
            print(self.number_of_gates)
            self.bin_counts = np.asarray(list(data_buffer))
            #cutoff = 512-int(self.number_of_gates)
            self.bin_counts = self.bin_counts[:512-(512-self.number_of_gates)]

            self.counts = np.sum(self.bin_counts)
            self.bin_averages += self.bin_counts
            self.total_counts += self.counts
        
            success = self.reset_device(self.device_handle)
            if success:
                print('C8855Reset succeeded.')
            else:
                print('C8855Reset failed.')
        
        
        return (self.bin_averages/self.averages),(self.total_counts/self.averages)

    def open_device(self) -> ctypes.c_void_p:
        return self.dll.C8855Open()


    def reset_device(self, handle: ctypes.c_void_p) -> bool:
        return self.dll.C8855Reset(handle)


    def close_device(self, handle: ctypes.c_void_p) -> int:
        result = self.dll.C8855Close(handle)
        return result


    def setup_device(self, handle: ctypes.c_void_p, gate_time: ctypes.c_ubyte, transfer_mode: ctypes.c_ubyte, number_of_gates: ctypes.c_ushort) -> bool:
        return self.dll.C8855Setup(handle, gate_time, transfer_mode, number_of_gates)



    def start_counting(self, handle: ctypes.c_void_p, trigger_mode:ctypes.c_ubyte =C8855_EXTERNAL_TRIGGER) -> bool:
        return self.dll.C8855CountStart(handle, trigger_mode)




    def read_data(self, handle:ctypes.c_void_p, data_buffer:Pointer_c_ulong):
        result_returned = ctypes.c_ubyte()
        success = self.dll.C8855ReadData(handle, data_buffer, ctypes.byref(result_returned))

        if success:
            print('Data read succeeded.')
            print(f'ResultReturned: {result_returned.value}')
        else:
            print('Data read failed.')
