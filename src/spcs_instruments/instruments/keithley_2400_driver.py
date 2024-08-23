import pyvisa
import toml
from ..spcs_instruments_utils import load_config

class Keithley2400:
    def __init__(self, config,  name = "Keithley2400"):
        self.name = name
        config = load_config(config)
        self.config = config.get('device', {}).get(self.name, {})
        self.data = []
        
        # Initialise the VISA resource manager
        self.rm = pyvisa.ResourceManager()
        
        # Find the correct port automatically if not specified
        self.port = self.find_device() if "port" not in self.config["Keithley2400"] else self.config["Keithley2400"]["port"]

        if not self.port:
            raise ValueError("Could not find the Keithley 2400 device.")

        self.device = self.rm.open_resource(self.port)
        self.device.read_termination = '\r'
        self.device.baud_rate = self.config["Keithley2400"]["baudrate"]
        self.device.timeout = self.config["Keithley2400"]["timeout"]

        # Configure the Keithley 2400
        self.configure_device()

    def find_device(self):
        resources = self.rm.list_resources()
        ("Available VISA resources:", resources)
        print(f'Available resources: {resources}')
    
        for resource in resources:
            try:
                device = self.rm.open_resource(resource)
                device.read_termination = '\r'
                idn = device.query("*IDN?")
                print(f"Attempting resource {resource}, IDN: {idn.strip()}")
            
                if "KEITHLEY" in idn.upper():
                    return resource
            except Exception as e:
                print(f"Failed to communicate with {resource}: {e}")
                continue
    
        return None

    
    def configure_device(self):
        # Access the measurement settings
        self.measurement_settings = self.config["Measurement"]

        # Example configuration commands
        self.device.write(f":SOUR:FUNC {self.measurement_settings['source_mode']}")  # Current or voltage is sourced to sample
        self.device.write(f":SOUR:{self.measurement_settings['source_mode']}:MODE FIX")  # Fixed sourcing mode
        
        if self.measurement_settings["source_mode"] == "CURR":
            self.device.write(f":SOUR:{self.measurement_settings['source_mode']}:RANG {self.measurement_settings['current_range']}")  # Current source range
            self.device.write(f":SOUR:{self.measurement_settings['source_mode']}:LEV {self.measurement_settings['current_level']}")  # Current source amplitude
        elif self.measurement_settings["source_mode"] == "VOLT":
            self.device.write(f":SOUR:{self.measurement_settings['source_mode']}:RANG {self.measurement_settings['voltage_range']}")  # Voltage source range
            self.device.write(f":SOUR:{self.measurement_settings['source_mode']}:LEV {self.measurement_settings['voltage_level']}")  # Voltage source amplitude

        self.device.write(f":SENS:FUNC {self.measurement_settings['sense_mode']}")  # Measure voltage or current

        if self.measurement_settings["sense_mode"] == "VOLT":
            self.device.write(f":SENS:{self.measurement_settings['sense_mode']}:PROT {self.measurement_settings['compliance_voltage']}")  # Compliance voltage
            self.device.write(f":SENS:{self.measurement_settings['sense_mode']}:RANG {self.measurement_settings['measurevolt_range']}")  # Measure current range
        elif self.measurement_settings["sense_mode"] == "CURR":
            self.device.write(f":SENS:{self.measurement_settings['sense_mode']}:PROT {self.measurement_settings['compliance_current']}")  # Compliance current
            self.device.write(f":SENS:{self.measurement_settings['sense_mode']}:RANG {self.measurement_settings['measurecurrent_range']}")  # Measure voltage range
        
    def get_instrument_name(self):
        # Query the instrument for its ID
        self.device.write("*IDN?")
        instrument_name = self.device.read().strip()
        return instrument_name
    
    def measure(self):
        # Turn on the output
        self.device.write(":OUTP ON")

        # Trigger a measurement
        self.device.write(":READ?")
        measurement = self.device.read()

        # Turn off the output
        self.device.write(":OUTP OFF")

        # Store the measurement
        self.data.append(measurement)

    def close(self):
        # Close the instrument connection
        self.device.close()

# Code to execute when the script is run directly
if __name__ == "__main__":
    # Example usage
    config = r"C:\Users\david\Documents\spcs_instruments\src\spcs_instruments\instruments\config.toml"
    keithley = Keithley2400(config)

    # Get and print the instrument name
    instrument_name = keithley.get_instrument_name()
    print(f"SUCCESS!! My name is: {instrument_name}")

    # keithley.measure() # The comment means do not measure anything when running this script
    keithley.close()
