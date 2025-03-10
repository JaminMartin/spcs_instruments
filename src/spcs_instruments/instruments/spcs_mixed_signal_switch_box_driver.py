import serial
import serial.tools.list_ports
import time
from ..spcs_instruments_utils import pyfex_support, DeviceError


@pyfex_support
class SPCS_mixed_signal_box:
    """A class to control and interact with an SPCS Mixed Signal Switch Box.

    Attributes:
        MATRIX_CHANNEL_MAPPING (dict): Maps logical channel names to matrix channel letters. e.g., "CH1" maps to "A", "CH2" maps to "B", etc.
        POLARITY_CHANNEL_MAPPING (dict): Maps logical channel names to polarity channel letters. e.g., "CH1" maps to "E", "CH2" maps to "F", etc.
        MATRIX_MAPPING (dict): Converts hexadecimal and string representations to integer values. Supports values from '0' to 'f', mapping to integers 0-15.
        REVERSE_MATRIX_MAPPING (dict): Inverted MATRIX_CHANNEL_MAPPING for reverse lookups.
        REVERSE_POLARITY_MAPPING (dict): Inverted POLARITY_CHANNEL_MAPPING for reverse lookups.
        name (str): Name identifier for the device.
        config (dict): Configuration settings for the device.
        connect_to_pyfex (bool): Indicates whether to connect to the PyFex experiment manager.
        sock (socket, optional): Socket connection for PyFex, if enabled.
        data (dict): Stores measurement data.
        __toml_config__ (dict): Default configuration template for the device
    """

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
    __toml_config__ = {
    "device.SPCS_mixed_signal_switch_box": {
        "_section_description": "SPCS_mixed_signal_switch_box measurement configuration",
        "reset": {
            "_value": True,
            "_description": "Reset the device on initilisation either true or false (bool)"
        },

    },
    "device.SPCS_mixed_signal_switch_box.matrix": {
        "_section_description": "Matrix configuration settings",
        "CH1": {
            "_value": "1",
            "_description": "Activiation state for the given channel (str) range: 1-f (hexidecimal)"
        },
        "CH2": {
            "_value": "2",
            "_description": "Activiation state for the given channel (str) range: 1-f (hexidecimal)"
        },
        "CH3": {
            "_value": "4",
            "_description": "Activiation state for the given channel (str) range: 1-f (hexidecimal)"
        },
        "CH4": {
            "_value": "8",
            "_description": "Activiation state for the given channel (str) range: 1-f (hexidecimal)"
        } 
    },
        "device.SPCS_mixed_signal_switch_box.polarity": {
        "_section_description": "polarity configuration settings",
        "CH1": {
            "_value": "1",
            "_description": "Polarity switch (str) '0' non-inverted '1' inverted"
        },
        "CH2": {
            "_value": "0",
            "_description": "Polarity switch (str) '0' non-inverted '1' inverted"
        },
        "CH3": {
            "_value": "1",
            "_description": "Polarity switch (str) '0' non-inverted '1' inverted"
        },
        "CH4": {
            "_value": "0",
            "_description": "Polarity switch (str) '0' non-inverted '1' inverted"
        } 
    }
    }
    def __init__(self, config: str, name: str='SPCS_mixed_signal_switch_box', connect_to_pyfex=True):
        """
        Initializes the SPCS mixed signal box with a given configuration.

        Args:
            config (str): Path to the configuration file.
            name (str, optional): Name of the device. Defaults to 'SPCS_mixed_signal_box'.
            connect_to_pyfex (bool, optional): Whether to connect to PyFex experiment manager. Defaults to True.
        
        Initializes:
            - Device name and configuration
            - Optional PyFex connection
            - Serial port connection
            - Initial device configuration
            - Data storage dictionary
        """    
        self.name = name
        self.config = self.bind_config(config)
        self.connect_to_pyfex = connect_to_pyfex
        
        if self.connect_to_pyfex:
            self.sock = self.tcp_connect()
            
        self.find_correct_port("MATRIX")
        self.connect()
        self.setup_config()
        self.data = {'CH1_matrix': [], 'CH2_matrix': [], 'CH3_matrix': [], 'CH4_matrix': [], 'CH1_polarity': [], 'CH2_polarity': [], 'CH3_polarity': [], 'CH4_polarity': []}


    def find_correct_port(self, expected_response: str, baudrate: int = 115200, timeout: int=2) -> str:
        """
        Automatically find the correct serial port for the matrix switch box.

        Args:
            expected_response (str): The expected response from the device to identify it.
            baudrate (int, optional): Serial communication baudrate. Defaults to 115200.
            timeout (int, optional): Connection timeout in seconds. Defaults to 2.

        Returns:
            str or None: The response from the device if found, None otherwise.

        Raises:
            Logs an error if no matching device is found.
        """
        
        
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
    
    def connect(self) -> None:
        """
        Establish a serial connection to the device using the previously identified port.

        Sets up a serial connection with 115200 baudrate and 1-second timeout.
        """
        self.ser = serial.Serial(self.port, 115200, timeout=1)

    def set_channel_matrix(self, channel: str, command: str) -> None:
        """
        Set the matrix routing for a specific channel.

        Args:
            channel (str): The matrix channel to configure (A, B, C, or D).
            command (str): The routing configuration (0-15 or hex 0-f).
        """
        self.ser.write(f"{channel}={command}\r".encode()) 
        time.sleep(0.06)  

    def set_channel_polarity(self, channel: str, command: str) -> None:
        """
        Set the polarity for a specific channel.

        Args:
            channel (str): The polarity channel to configure (E, F, G, or H).
            command (str): Polarity setting (0 = non-inverted, 1 = inverted).
        """
        self.ser.write(f"{channel}={command}\r".encode()) 
        time.sleep(0.06)  

    def get_state(self) -> dict:
        """
        Retrieve the current state of all channels.

        Returns:
            dict: A dictionary representing the current state of matrix and polarity settings.
        """
        self.ser.write("?\r".encode())
        response = self.ser.readline().decode() 

        self.update_state(response)
        return self._state
    

    def update_state(self, response: str) -> None:
        """
        Update the internal state based on the device's response.

        Args:
            response (str): A comma-separated string of channel states.
        """
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
 
    def switch_layout(self) -> None:
        """
        Print a diagram explaining the switch box channel and polarity mapping.

        Provides a visual reference for channel routing and polarity configurations.
        """

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



    def setup_config(self) -> None:
        """
        Set up the initial configuration of the device.

        Performs a reset if specified in the configuration and sets initial channel states.
        """
        self.require_config("reset")

        if self.config["reset"]:
            self.reset()
        self.set_initial_state()

    def reset(self) -> None:
        """
        Reset all matrix and polarity channels to their default (0) state.

        Iterates through all channels, setting matrix routing to 0 and polarity to non-inverted.
        """
        for k in self.MATRIX_CHANNEL_MAPPING:
            self.set_channel_matrix(self.MATRIX_CHANNEL_MAPPING[k], 0)
            self.set_channel_polarity(self.POLARITY_CHANNEL_MAPPING[k], 0)
            time.sleep(0.3)

    def set_initial_state(self) -> None:
        """
        Configure initial matrix and polarity settings based on the configuration.

        Sets matrix routing and polarity for channels as specified in the configuration.
        """
        for k in self.config["matrix"]:

            self.set_channel_matrix(self.MATRIX_CHANNEL_MAPPING[k], self.config["matrix"][k])
            time.sleep(0.3)

        for k in self.config["polarity"]: 
       
            self.set_channel_polarity(self.POLARITY_CHANNEL_MAPPING[k], self.config["polarity"][k])

    def measure(self) -> dict:
        """
        Capture the current state of the device and optionally send data to PyFex.

        Returns:
            dict: A dictionary of current channel states, with each state in a list.
        """
        self.get_state()  
        self.data = {key: [value] for key, value in self._state.items()} 
        
        if self.connect_to_pyfex:
            payload = self.create_payload()
            self.tcp_send(payload, self.sock)
        return self.data    