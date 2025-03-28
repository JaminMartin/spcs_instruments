import pyvisa
import numpy as np
import time
from ..spcs_instruments_utils import load_config, pyfex_support

@pyfex_support
class SiglentSDS2352XE:
    """
    Class to create user-fiendly interface with the SiglentSDS2352X-E scope.
    Has the get waveform subroutine for use once a connection has been established these functions can
    be used inside of the measurement file / GUI.
    note! cursors must be on for this method to work!

    """

    def __init__(self, config, name = "SIGLENT_Scope",connect_to_pyfex=True):
        self.connect_to_pyfex = connect_to_pyfex
        rm = pyvisa.ResourceManager()
        self.name = name
        self.resource_adress = "not found"
        resources = rm.list_resources()
        for i in range(len(resources)):
            try:
                my_instrument = rm.open_resource(resources[i])
                query = my_instrument.query("*IDN?").strip()
                # print(query)
                if (
                    query
                    == "Siglent Technologies,SDS2352X-E,SDS2EDDQ6R0793,2.1.1.1.20 R3"
                ):
                    self.resource_adress = resources[i]
                    self.instrument = my_instrument

            except:
                pass
        if self.resource_adress == "not found":
            print(
                "Siglent Technologies,SDS2352X-E not found, try reconecting. If issues persist, restart python"
            )

        config = load_config(config)

        self.config = config.get('device', {}).get(self.name, {})
        print(f"SIGLENT_Scope connected with this config {self.config}")
        if self.connect_to_pyfex:
            self.sock = self.tcp_connect()
        self.setup_config()
        self.data = {"voltage": []}
        return

    def setup_config(self):
        # Get the configuration parameters
        self.acquisition_mode = self.config.get("acquisition_mode")
        self.averages = self.config.get("averages")
        self.reset_per = self.config.get("measure_mode", {}).get("reset_per")
        self.measurement_frequency = self.config.get("measure_mode", {}).get(
            "frequency"
        )
        # Only send the ACQUIRE_WAY command if both parameters are found
        if self.acquisition_mode is not None and self.averages is not None:
            self.instrument.write(
                f"ACQUIRE_WAY {self.acquisition_mode},{self.averages}"
            )

    def measure(self):
        if self.reset_per:
            return self.measure_reset()
        else:
            return self.measure_basic()

    def close(self):
        self.instrument.close()

    def get_waveform(self, channel="c1"):
        # Change the way the scope responds to queries. For example, 'chdir off'
        # Will result in a returned value like 200E-3, instead of 'C1:VOLT_DIV 200E-3 V'
        self.instrument.write("chdr off")

        # Query the volts/division for channel 1
        vdiv = self.instrument.query("c1:vdiv?")

        # Query the vertical offset for channel 1
        ofst = self.instrument.query("c1:ofst?")

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

        horizontal_offset = self.instrument.query("C1:CRVA? HREL").strip()

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

    def measure_reset(self):
        self.instrument.write(f"ACQUIRE_WAY {self.acquisition_mode},{self.averages}")
        time.sleep(0.5 + 1 / self.measurement_frequency)
        _, v = self.get_waveform()
        self.instrument.write("ACQUIRE_WAY SAMPLING,1")
        volts = np.sum(v)
        self.data["voltage"] = [volts]    
        if self.connect_to_pyfex:
            payload = self.create_payload()
            self.tcp_send(payload, self.sock)

        return np.sum(v)

    def measure_basic(self):
        _, v = self.get_waveform()
        time.sleep(0.5)
        volts = np.sum(v)
        self.data["voltage"] = [volts]    
        if self.connect_to_pyfex:
            payload = self.create_payload()
            self.tcp_send(payload, self.sock)

        return np.sum(v)

