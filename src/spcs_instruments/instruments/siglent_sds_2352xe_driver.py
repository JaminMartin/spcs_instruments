import pyvisa
import numpy as np
import time
from ..spcs_instruments_utils import rex_support, DeviceError

@rex_support
class SiglentSDS2352XE:
    """
    Class to create user-fiendly interface with the SiglentSDS2352X-E scope.
    note! cursors must be on for this method to work!

    """
    __toml_config__ = {
    "device.SIGLENT_Scope": {
        "_section_description": "SIGLENT_Scope measurement configuration",
        "acquisition_mode": {
            "_value": "AVERAGE",
            "_description": "Valid grating name to be used for the measurement, options: VIS, NIR, MIR"
        },
        "averages": {
            "_value": 64,
            "_description": "Number of averages to collect: 4, 16, 32, 64, 128, 256, 512, 1024"
        },
        "reset_per": {
            "_value": True,
            "_description": "Enable/Disable rolling averaging"
        },
        "frquency":{
            "_value": 5, 
            "_description": "Frequency of the trigger source to aproximate waiting x number off averages. The scope doesnt have a query to see if the number of averages has been reached"
        },
        "channel":{
            "_value": "c1", 
            "_description": "Desired measurement channel"
        },
        "data_type":{
            "_value": "area", 
            "_description": "Return the area, or the full trace. Options: area, trace"
        }
    }}
    def __init__(self, config, name = "SIGLENT_Scope",connect_to_rex=True):
        '''
        Initializes the SDS2352X-E with a given configuration.

        Args:
            config (str): Path to the configuration file.
            name (str, optional): Name of the device. Defaults to 'SIGLENT_Scope'.
            connect_to_rex (bool, optional): Whether to connect to rex experiment manager. Defaults to True.
        '''
        self.connect_to_rex = connect_to_rex
        rm = pyvisa.ResourceManager()
        self.name = name
        self.resource_adress = "not found"
        resources = rm.list_resources()
        for i in range(len(resources)):
            try:
                my_instrument = rm.open_resource(resources[i])
                query = my_instrument.query("*IDN?").strip()
    
                if (
                    query
                    == "Siglent Technologies,SDS2352X-E,SDS2EDDQ6R0793,2.1.1.1.20 R3"
                ):
                    self.resource_adress = resources[i]
                    self.instrument = my_instrument

            except:
                pass
        if self.resource_adress == "not found":
            self.logger.error(
                "Siglent Technologies,SDS2352X-E not found, try reconecting. If issues persist, restart python"
            )

        self.config = self.bind_config(config)

        
        self.logger.debug(f"SIGLENT_Scope connected with this config {self.config}")
        if self.connect_to_rex:
            self.sock = self.tcp_connect()
        self.setup_config()
        self.data = {}
        return

    def setup_config(self) -> None:
        '''
        Setup function for the oscilliscope
        '''
        # Get the configuration parameters
        self.acquisition_mode = self.require_config("acquisition_mode")
        self.averages = self.require_config("averages")
        self.data_type = self.require_config("data_type")
        self.reset_per = self.require_config("reset_per")
        self.frequency = self.require_config("frequency")
        self.channel = self.require_config("channel")
        if self.acquisition_mode is not None and self.averages is not None:
            self.instrument.write(
                f"ACQUIRE_WAY {self.acquisition_mode},{self.averages}"
            )

    def measure(self):
        '''
        High level measurement API, calls into measure_sample or measure_trace depending on device configuration.
        '''
        match self.data_type:
            case "area":
                return self.measure_sample()

            case "trace":
                return self.measure_trace()
            case _ :
                raise DeviceError("Measurement mode not specified correctly")
        

    def close(self):
        '''
        Releases the device.
        '''
        self.instrument.close()

    def get_waveform(self, channel="c1"):
        '''
        Mostly vendor provided function to return the waveform from the oscilisope. 
        '''
        # Change the way the scope responds to queries. For example, 'chdir off'
        # Will result in a returned value like 200E-3, instead of 'C1:VOLT_DIV 200E-3 V'
        self.instrument.write("chdr off")

        # Query the volts/division for channel 1
        vdiv = self.instrument.query(f"{channel}:vdiv?")

        # Query the vertical offset for channel 1
        ofst = self.instrument.query(f"{channel}:ofst?")

        # Query the time/division
        tdiv = self.instrument.query("tdiv?")

        # Query the sample rate of the scope
        sara = self.instrument.query("sara?")

        sara_unit = {"G": 1e9, "M": 1e6, "k": 1e3}
        for unit in sara_unit.keys():
            if sara.find(unit) != -1:
                sara = sara.split(unit)
                sara = float(sara[0]) * sara_unit[unit]
                break
        sara = float(sara)

        horizontal_offset = self.instrument.query(f"{channel}:CRVA? HREL").strip()

        horizontal_offset = horizontal_offset.split(",")
        horizontal_offset = float(horizontal_offset[4].replace("s", ""))
        # print(horizontal_offset)
        # Query the waveform of channel 1 from the scope to the controller. This write command
        # and the next read command act like a single query command. We are telling the scope
        # to get the waveform data ready, then reading the raw data into 'recv'
        self.instrument.write(channel + ":wf? dat2")

        recv = list(self.instrument.read_raw())[16:]

        # Removes elements in 'recv', although can't remember why this is here
        recv.pop()
        recv.pop()

        # Creating and empty list of y-axis and x-axis data and appending it per iteration.
        # The reason for the if statements is on page 142 of the programming manual
        volt_value = []
        for data in recv:
            if data > 127:
                data = data - 256
            else:
                pass
            volt_value.append(data)

        time_value = []
        for idx in range(0, len(volt_value)):
            volt_value[idx] = volt_value[idx] / 25 * float(vdiv) - float(ofst)
            time_data = -(float(tdiv) * 14 / 2) + idx * (1 / sara) - horizontal_offset
            time_value.append(time_data)

        volt_value = np.asarray(volt_value)
        time_value = np.asarray(time_value)
        return time_value, volt_value

    def measure_sample(self) -> float:
        '''
        Returns a single value (voltage) based on the area under the transient. Makes assumption that data is either all negative voltages, or that the signal voltage is more positive than the baseline voltage.
        In the case the baseline voltage is positive and the signal voltage is more negative, your results may appear inverted. Standard practice is to ensure your baseline voltage and signal voltage is either all positive or all negative for this to work reliably.

        Args: Self
        Returns: float64
        '''
        self.instrument.write(f"ACQUIRE_WAY {self.acquisition_mode},{self.averages}")
        dwell_time = int(int(self.averages) / self.frequency)
        time.sleep(dwell_time)
        time.sleep(1)
        _, v = self.get_waveform(channel=self.channel)
        if self.reset_per:
            self.instrument.write("ACQUIRE_WAY SAMPLING,1")
        all_negative = np.all(v < 0)
        if all_negative:
            v_t = abs(v)
            volt_array = v_t - v_t.min()
        else:
            volt_array = v - v.min()
        volts = np.sum(volt_array)
        self.data["voltage (mV)"] = [volts]    
        if self.connect_to_rex:
            payload = self.create_payload()
            self.tcp_send(payload, self.sock)

        return volts


    def measure_trace(self) -> tuple:
        '''
        Returns the entire trace/waveform from the osciliscope, where t=0 is defined by the x1 cursor. 
        Args: Self
        Returns: tuple (time: NDarray f64, voltage: NDarray f64)
        '''
        self.instrument.write(f"ACQUIRE_WAY {self.acquisition_mode},{self.averages}")
        dwell_time = int(int(self.averages) / self.frequency)
        time.sleep(dwell_time)    
        time_s, voltage = self.get_waveform()
        
        self.data["voltage (mV)"] = [voltage.tolist()]  
        self.data["time (s)"] = [time_s.tolist()]   
        if self.connect_to_rex:
            payload = self.create_payload()
            self.tcp_send(payload, self.sock)
        if self.reset_per:    
            self.instrument.write("ACQUIRE_WAY SAMPLING,1")    
        return time_s, voltage   