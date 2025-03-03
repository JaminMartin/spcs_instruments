import serial
import serial.tools.list_ports
import time
from ...spcs_instruments_utils import pyfex_support, DeviceError


@pyfex_support
class Gl100:
    """
    A class to control and interface with the Horiba iHR550 Spectrometer via libusb.
    
    This class provides a control interface for the iHR550 spectrometer including
    wavelength control, grating selection, mirror positioning, and slit width adjustment.
    
    Attributes:
        LOWER_LIMIT (float): Lowest limit laser can be set to in nm (380.00)
        UPPER_LIMIT (float): Highest limit laser can be set to in nm (750.00)
        ZERO (string): Command used to zero the stepper motor (X0= 15T)
        GET_MANUFACTURER (string): Command used to get the manufacturer information (X-12?)
        GET_POSTION (string): Used to get the current stepper motor position (X-1?)
        __toml_config__ (dict): Default configuration template for the device
        data (dict): Measurement data storage
        config: Bound configuration as defined by the user
        connect_to_pyfex (bool): Whether to connect to pyfex experiment manager
        sock: Socket connection when pyfex is enabled
        step_size (float): Step size for wavelength measurements.
        start_wavelength (float): Initial start wavelength for a scan 
        final_wavelength (float): End wavelength for a measurement scan 
        grating_factor (float): Factor related to the diffraction grating used in the system.
        name (string): Name or identifier for the device.
        scan_data (dict): Stores data related to the scan, namely positions and motor steps required, as well as error from desired wavelenght goals.
        start_measurement_position (float): Position of the start wavelength in stepper motor units.
        end_measurement_position (float): Position of the end wavelength in stepper motor units.
        min_step_size (float): Minimum allowable step size for the measurement system. (min 1/grating factor nm)
        current_index (int): The current index position within a scan or measurement sequence.
        total_steps_from_zero (int): Total number of steps the stepper motor has moved from the zero position.
        total_steps (int): Total number of steps required to complete the scan from start to end.
    """
    LOWER_LIMIT=380.00
    UPPER_LIMIT=750.00
    ZERO = "X0= 15T"
    GET_MANUFACTURER = "X-12?"
    GET_POSITION = "X-1?"
    __toml_config__ = {
    "device.GL100_Dye_Laser": {
        "_section_description": "GL100_Dye_Laser measurement configuration",
        "step_size": {
            "_value": 0.1,
            "_description": "Step size in nm"
        },
        "initial_position": {
            "_value": 490,
            "_description": "Calibrated wavelength from mechanical dial (nm)"
        },
        "start_position":{
            "_value": 500, 
            "_description": "Start wavelength in (nm)"
        },   
        "end_position":{
            "_value": 600, 
            "_description": "End wavelength in (nm)"
        },
        "dye":{
            "_value": "C540", 
            "_description": "Dye used for the experiment"
        }
    }}
    def __init__(self, config: str, name: str='GL100_Dye_Laser', connect_to_pyfex=True):
        """
        Initializes the Gl100 with a given configuration.

        Args:
            config (str): Path to the configuration file.
            name (str, optional): Name of the device. Defaults to 'GL100_Dye_Laser'.
            connect_to_pyfex (bool, optional): Whether to connect to PyFex experiment manager. Defaults to True.
        """
        self.name = name
        self.config = self.bind_config(config)
        self.connect_to_pyfex = connect_to_pyfex
        
        if self.connect_to_pyfex:
            self.sock = self.tcp_connect()
            
        self.data = {
            'wavelength (nm)': []
        }
        self.current_index = 0
        self.grating_factor = 32 # Hardcoded from 1200groves/mm dye laser grating
        self.min_step_size = 1/self.grating_factor 
        self.setup_config()
        self.start_measurement_position = self.move_to_start()
        self.scan_data = self._generatescan_data(self.start_measurement_position, self.end_measurement_position)

    def setup_config(self):
        """
        Sets up the device configuration by loading necessary parameters from the config file and checks any hardware limits.
        Connects to the correct port if the device is found.
        """
        self.initial_position = self.require_config('initial_position')
        self.start_measurement_position = self.require_config("start_position")
        self.end_measurement_position = self.require_config("end_position")
        self.check_limits()
        self.step_size = self.check_step(self.require_config("step_size"))
        self.total_steps_from_zero = 0
        self.dye = self.require_config("dye")
        connect = self.find_correct_port("GenStepper 5.51 January 31, 2014")
        if connect == None:
            raise DeviceError("Cant find device!")
        else:
            self.connect()

    def check_limits(self):
        """
        Checks if the configured positions are within the device's wavelength limits.
        Raises:
            DeviceError: If any position is outside the defined LOWER_LIMIT or UPPER_LIMIT.
        """
        if (
            self.initial_position <= self.LOWER_LIMIT
            or self.start_measurement_position <= self.LOWER_LIMIT
            or self.end_measurement_position <= self.LOWER_LIMIT
        ):
            raise DeviceError("Outside lower wavelength limit!")
        if (
            self.initial_position >= self.UPPER_LIMIT
            or self.start_measurement_position >= self.UPPER_LIMIT
            or self.end_measurement_position >= self.UPPER_LIMIT
        ):
            raise DeviceError("Outside lower wavelength limit!")
         
    def check_step(self, step_size):
        """
        Ensures the step size is not smaller than the minimum allowed step size.
        Logs a warning if the step size is adjusted.
        
        Args:
            step_size (float): Desired step size.
        """
        self.actual_step_size = max(step_size, self.min_step_size)
        if self.actual_step_size != step_size:
            self.logger.warning(f"Warning: Desired step size {step_size}nm is smaller than minimum step size {self.min_step_size}nm")
            self.logger.warning(f"Using minimum step size of {self.min_step_size}nm instead")

    def _generatescan_data(self, start, stop):
        """
        Generates scan positions and step data for measurement.
        
        Args:
            start (float): Start position.
            stop (float): Stop position.
        
        Returns:
            list: List of scan position dictionaries containing desired wavelength, actual movement, steps and errors.
        """
        num_desired_points = int((stop - start) / self.actual_step_size) + 1
        scan_positions = []
        current_pos = start
        self.total_steps = 0

        for point_idx in range(num_desired_points):
            desired_wavelength = start + (point_idx * self.actual_step_size)
            steps_needed = round((desired_wavelength - current_pos) * self.grating_factor)

            if steps_needed != 0:
                actual_movement = steps_needed / self.grating_factor
                current_pos += actual_movement
                self.total_steps += steps_needed

            scan_positions.append({
                'index': point_idx,
                'desired_wavelength': desired_wavelength,
                'actual_wavelength': current_pos,
                'wavelength_error': current_pos - desired_wavelength,
                'steps_required': steps_needed, 
                'total_steps_from_start': self.total_steps
            })

        return scan_positions
    
    def move_to_next_position(self):
        """
        Moves to the next scan position and returns the corresponding scan data.
        
        Returns:
            dict or None: Next position data or None if scan is complete.
        """
        if self.current_index >= len(self.scan_data):
            return None

        next_position = self.scan_data[self.current_index]
        steps = next_position['steps_required']

        if steps != 0:
            self.move(steps)
        else:
            self.logger.debug(f"No movement needed for position {self.current_index}")

        self.current_index += 1

        return next_position

    def move(self, steps):
        """
        Moves the stepper motor by the specified number of steps.
        
        Args:
            steps (int): Number of steps to move.
        """
        self.logger.debug(f"Moving laser {steps} steps")
        self.send_command(f"X{steps}G")
        self.total_steps_from_zero += steps


    def measure(self):
        """
        Performs a measurement at the current scan position.
        
        Returns:
            dict or None: Measurement data at the current position, or None if the scan is complete.
        """
        if self.current_index >= len(self.scan_data):
            return None
        
        current_position = self.scan_data[self.current_index]
        self.data = {
            'wavelength (nm)': [current_position['actual_wavelength']],
            'desired wavelength (nm)': [current_position['desired_wavelength']],
            'wavelength_error': [current_position['wavelength_error']],
        }
        if self.connect_to_pyfex:
            payload = self.create_payload()
            self.tcp_send(payload, self.sock)
        return self.data
    
    def find_correct_port(self, expected_response, baudrate=9600, timeout=2):
        ports = serial.tools.list_ports.comports()
        
        for port in ports:
            try:
                with serial.Serial(port.device, baudrate, timeout=timeout) as ser:
                    ser.write(b'X-12?') 
                    responses = ser.readlines()  
                    
                 
                    cleaned_responses = [line.decode().strip() for line in responses if line.strip()]

                    if any(expected_response in line for line in cleaned_responses):
                        
                        self.port = port.device
                        return cleaned_responses
                    
            except (serial.SerialException, OSError) as e:
                self.logger.error(f"Could not open {port.device}: {e}")
        
        self.logger.error("No matching device found.")
        return None
    
    def connect(self):
        self.ser = serial.Serial(self.port, 9600, timeout=1)

    def send_command(self,command):
        self.ser.write(f"{command}".encode()) 
        time.sleep(0.06)  
        response = self.ser.readlines()  
        return [line.decode().strip() for line in response] 
    


    def return_to_zero(self):
        """
        Return to the zero position by moving exact negative of total steps.
        Includes backlash compensation.
        """
        if self.total_steps_from_zero == 0:

            return

       
        backlash_offset = 5.0  # nm
        steps_to_zero = -self.total_steps_from_zero
        
        if steps_to_zero > 0: 
            self.move(steps_to_zero)
        else:  
      
            extra_steps = round(backlash_offset * self.grating_factor)
            self.move(steps_to_zero - extra_steps)
 
            self.move(extra_steps)
        

        if self.total_steps_from_zero == 0:
            self.total_steps_from_zero = 0
       
        else:
            raise DeviceError("Failed to return to zero position")
            
    def move_to_start(self):
        """
        Move to start position with backlash compensation.
        Always approaches from lower wavelength to avoid mechanical backlash.
        Handles integer step rounding to ensure accurate final position.
        Returns the actual position reached.
        """

        current_pos = self.initial_position
        target_pos = self.start_measurement_position
        backlash_offset = 5.0  # nm 
        
        if current_pos <= target_pos:
            steps = round((target_pos - current_pos) * self.grating_factor)
            actual_movement = steps / self.grating_factor
            final_pos = current_pos + actual_movement
            self.move(steps)
        else:

            intermediate_pos = target_pos - backlash_offset
            steps_back = round((intermediate_pos - current_pos) * self.grating_factor)
            actual_back_movement = steps_back / self.grating_factor
            pos_after_back = current_pos + actual_back_movement
            self.move(steps_back)
            
            steps_forward = round((target_pos - pos_after_back) * self.grating_factor)
            actual_forward_movement = steps_forward / self.grating_factor
            final_pos = pos_after_back + actual_forward_movement
            self.move(steps_forward)
        
        
        
        position_error = final_pos - target_pos
       
        
        return final_pos