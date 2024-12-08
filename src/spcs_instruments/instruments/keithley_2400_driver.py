import pyvisa
import toml
from ..spcs_instruments_utils import load_config
import time
class Keithley2400:
    def __init__(self, config,  name = "Keithley2400"):
        self.name = name

        rm = pyvisa.ResourceManager()
        self.resource_adress = "not found"
        resources = rm.list_resources()
        self.data = {
                "Voltage": [],
                "Current": [],
                "Unknown1": [],
                "Unknown2": [],
                "Unknown3": [],
            }
        for i in range(len(resources)):
            try:
                my_instrument = rm.open_resource(resources[i])
                my_instrument.read_termination = '\r'
                query = my_instrument.query("*IDN?").strip()

                if "KEITHLEY INSTRUMENTS INC.,MODEL 2400" in query:
                 self.resource_adress = resources[i]
                 self.instrument = my_instrument
                 print("Keithley Found!")
        
            except:
                pass


        if self.resource_adress == "not found":
             print(
                 "KEITHLEY INSTRUMENTS INC.,MODEL 2400not found, try reconecting. If issues persist, restart python"
             )

        config = load_config(config)
        self.config = config.get('device', {}).get(self.name, {})
        print(f"KEITHLEY connected with this config {self.config}")
        # Configure the Keithley 2400
        self.configure_device()
        return


    
    def configure_device(self):
        # Access the measurement settings
        self.measurement_settings = self.config["measurement"]
        # NEED TO ADD RESET
        # Example configuration commands
        self.instrument.write(f":SOUR:FUNC {self.measurement_settings['source_mode']}")  # Current or voltage is sourced to sample
        self.instrument.write(f":SOUR:{self.measurement_settings['source_mode']}:MODE FIX")  # Fixed sourcing mode
        
        if self.measurement_settings["source_mode"] == "CURR":
            self.instrument.write(f":SOUR:{self.measurement_settings['source_mode']}:RANG {self.measurement_settings['current_range']}")  # Current source range
            self.instrument.write(f":SOUR:{self.measurement_settings['source_mode']}:LEV {self.measurement_settings['current_level']}")  # Current source amplitude
        elif self.measurement_settings["source_mode"] == "VOLT":
            self.instrument.write(f":SOUR:{self.measurement_settings['source_mode']}:RANG {self.measurement_settings['voltage_range']}")  # Voltage source range
            self.instrument.write(f":SOUR:{self.measurement_settings['source_mode']}:LEV {self.measurement_settings['voltage_level']}")  # Voltage source amplitude

        self.instrument.write(f":SENS:FUNC '{self.measurement_settings['sense_mode']}'")  # Measure voltage or current

        if self.measurement_settings["sense_mode"] == "VOLT":
            self.instrument.write(f":SENS:{self.measurement_settings['sense_mode']}:PROT {self.measurement_settings['compliance_voltage']}")  # Compliance voltage
            self.instrument.write(f":SENS:{self.measurement_settings['sense_mode']}:RANG {self.measurement_settings['measurevolt_range']}")  # Measure current range
        elif self.measurement_settings["sense_mode"] == "CURR":
            self.instrument.write(f":SENS:{self.measurement_settings['sense_mode']}:PROT {self.measurement_settings['compliance_current']}")  # Compliance current
            self.instrument.write(f":SENS:{self.measurement_settings['sense_mode']}:RANG {self.measurement_settings['measurecurrent_range']}")  # Measure voltage range
        
    
    def measure(self):
        # Turn on the output
        self.instrument.write(":OUTP ON")

        # Trigger a measurement
        measurement = self.instrument.query(":READ?").strip()
     
  
        # Turn off the output
        self.instrument.write(":OUTP OFF")

        # Store the measurement
        
        measurement_values = measurement.split(',')
        V = float(measurement_values[0])  # Convert the first value to a float
     
        I=float(measurement_values[1])
    
        U1=float(measurement_values[2])

        U2=float(measurement_values[3])
   
        U3=float(measurement_values[4])
    
        self.data["Voltage"].append(V)
        self.data["Current"].append(I)
        self.data["Unknown1"].append(U1)
        self.data["Unknown2"].append(U2)
        self.data["Unknown3"].append(U3)
        return self.data

    def close(self):
        # Close the instrument connection
        self.instrument.close()

