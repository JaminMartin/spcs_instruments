import pyvisa

class Keithley2400:
    def __init__(self, config):
        self.config = config
        self.name = "Keithley2400"
        self.data = []

        # Initialise the VISA resource manager and open the instrument
        self.rm = pyvisa.ResourceManager()
        self.device = self.rm.open_resource(self.config['port'])
        self.device.baud_rate = self.config['baudrate']
        self.device.timeout = self.config['timeout']

        # Configure the Keithley 2400
        self.configure_device()

    def configure_device(self):
        # Example configuration commands based on table in lab manual
        self.device.write(f":SOUR:FUNC[:MODE] <CURR>") #Current is sourced to sample
        self.device.write(f":SOURce:CURRent:MODE FIXed") # Select fixed sourcing mode for I-source
        self.device.write(f":SOUR:CURR:RANG {self.config['voltage_range']}") #current source range
        self.device.write(f":SOUR:CURR:LEV {self.config['current_level']}") #current source amplitude
        self.device.write(f":SENS:FUNC <VOLT>") #measure the voltage
        self.device.write(f":SENS:VOLT:PROT <{self.config['compliance_voltage']}>") #maximum voltage to clamp at to avoid damaging machine
        self.device.write(f":SENS:VOLT:RANG <n>") #voltage range to measure (put in toml config file when known)
        

    def measure(self):
        # Turn on the output
        self.device.write(":OUTPut ON")

        # Trigger a measurement
        self.device.write(":READ?")
        measurement = self.device.read()

        # Turn off the output
        self.device.write(":OUTPut OFF")

        # Store the measurement
        self.data.append(measurement)

    def close(self):
        # Close the instrument connection
        self.device.close()