import serial
import serial.tools.list_ports
import time
from ..spcs_instruments_utils import pyfex_support, DeviceError


@pyfex_support
class SPCS_mixed_signal_box:

    MATRIX_CHANNEL_MAPPING = {
    "CH1": "A",
    "CH2": "B",
    "CH3": "C",
    "CH4": "D",
}
    POLARITY_CHANNEL_MAPPING = {
        "CH1": "E",
        "CH2": "F",
        "CH3": "G",
        "CH4": "H",
    }
    MATRIX_MAPPING = {
        "0": 0,
        "1": 1,
        "2": 2,
        "3": 3,
        "4": 4,
        "5": 5,
        "6": 6,
        "7": 7,
        "8": 8,
        "9": 9,
        "a": 10,
        "b": 11,
        "c": 12,
        "d": 13,
        "e": 14,
        "f": 15,
    }
    REVERSE_MATRIX_MAPPING = {v: k for k, v in MATRIX_CHANNEL_MAPPING.items()}
    REVERSE_POLARITY_MAPPING = {v: k for k, v in POLARITY_CHANNEL_MAPPING.items()}

    def __init__(self, config: str, name: str='SPCS_mixed_signal_switch_box', connect_to_pyfex=True):
        """
        Initializes the SPCS mixed signal box with a given configuration.

        Args:
            config (str): Path to the configuration file.
            name (str, optional): Name of the device. Defaults to 'SPCS_mixed_signal_box'.
            connect_to_pyfex (bool, optional): Whether to connect to PyFex experiment manager. Defaults to True.
        """
        self.name = name
        self.config = self.bind_config(config)
        self.connect_to_pyfex = connect_to_pyfex
        
        if self.connect_to_pyfex:
            self.sock = self.tcp_connect()
            
        self.find_correct_port("MATRIX")
        self.connect()

    def find_correct_port(self, expected_response, baudrate=115200, timeout=2):
        ports = serial.tools.list_ports.comports()
        
        for port in ports:
            try:
                with serial.Serial(port.device, baudrate,timeout=timeout) as ser:
                    ser.write(b'*\r') 
                    responses = ser.readline()  
                    cleaned_response = responses.decode().strip()
                    if expected_response == cleaned_response:
                        
                        self.port = port.device
                        self.logger.debug("matrix switch box found")
                        
                        return cleaned_response
                    
            except (serial.SerialException, OSError) as e:
                pass
        
        self.logger.error("No matching device found.")
        return None
    
    def connect(self):
        self.ser = serial.Serial(self.port, 115200, timeout=1)

    def set_channel_matrix(self, channel, command):
        self.ser.write(f"{channel}={command}\r".encode()) 
        time.sleep(0.06)  

    def get_state(self):
        self.ser.write("?\r".encode())
        response = self.ser.readline().decode() 

        self.update_state(response)
        return self._state
    

    def update_state(self, response: str):
        self._state = {
            "CH1_matrix": None,
            "CH2_matrix": None,
            "CH3_matrix": None,
            "CH4_matrix": None,
            "CH1_polarity": None,
            "CH2_polarity": None,
            "CH3_polarity": None,
            "CH4_polarity": None,
        }
        

        for pair in response.strip().split(","):
            key, value = pair.split("=")
            if key in self.REVERSE_MATRIX_MAPPING:
                ch_key = self.REVERSE_MATRIX_MAPPING[key]
                self._state[f"{ch_key}_matrix"] = self.MATRIX_MAPPING[value]
            elif key in self.REVERSE_POLARITY_MAPPING:
                ch_key = self.REVERSE_POLARITY_MAPPING[key]
                self._state[f"{ch_key}_polarity"] = int(value)
 
    def switch_layout(self):
   
        diagram = """
    +---------+      
    | Switch  |      
    |         |      
    | CH1 = A |      
    | CH2 = B |      
    | CH3 = C |      
    | CH4 = D |
    | ---- = 0|     
    | |--- = 1|      
    | -|-- = 2|      
    | --|- = 4|      
    | ---| = 8|      
    | ||-- = 3|      
    | |-|- = 5|      
    | |--| = 9|      
    | -||- = 6|      
    | -|-| = a|      
    | --|| = c|      
    | |||- = 7|      
    | ||-| = b|      
    | |-|| = d|      
    | -||| = e|      
    | |||| = f|
    |         |
    | hex->int|
    | a = 10  |
    | b = 11  |
    | c = 12  |
    | d = 13  |
    | e = 14  |
    | f = 15  |
    |         |
    | Polarity|      
    | CH1 = E |      
    | CH2 = F |      
    | CH3 = G |      
    | CH4 = H |      
    |         |      
    | 0= !inv |      
    | 1= inv  |      
    +---------+      
    """   
        print(diagram)    