import time
import numpy as np
import pyvisa

from rex_utils import Measurement, RexSupport


class DPO7104_TekTronix_scope(RexSupport):
    """Driver for the Tektronix DPO7104 oscilloscope over GPIB using PyVISA.

    This class manages instrument connection, configuration, gated area integration, waveform
    capture, and optional forwarding of measurement payloads to a Rex server.

    The driver supports averaged acquisitions, cursor-based gated area measurements on CH1,
    raw waveform downloads for CH1 and CH2, and basic trigger setup on CH2.

    Attributes:
        state (int): Measurement cycle counter.
        connect_to_rex (bool): Whether to forward payloads to a Rex server link.
        sock (socket | None): TCP socket used for Rex forwarding.
        scope: PyVISA resource for the connected oscilloscope.
        measurements (dict): Stored Measurement objects for area, waveform, trigger, and timing.
        averages (int): Number of waveform acquisitions to average.
        start_bound (float): Left cursor position relative to the trigger.
        end_bound (float): Right cursor position relative to the trigger.
        area_enabled (bool): Whether gated area measurements are enabled.
        waveform_enabled (bool): Whether CH1 waveform capture is enabled.
        trigger_enabled (bool): Whether CH2 trigger waveform capture is enabled.

    Methods:
        open_connection(): Open the instrument connection and verify identity.
        set_config(): Apply configuration and prepare acquisition settings.
        set_cursors(): Configure vertical cursor positions and gated area measurement.
        measure_area(): Acquire gated area and convert polarity for PMT output.
        measure_waveform(channel=1): Download and scale waveform data from the given channel.
        measure(): Run enabled measurements and optionally send the payload to Rex.
        full_autoset(): Execute the instrument autoset sequence.
        close(): Close the PyVISA resource safely.
    """

    #pyvisa settings
    RESOURCE_MANAGER = '' #default to pyvisa's default backend, but can be set to "@ivi" or other backends if needed for compatibility with specific GPIB-USB adapters or drivers. 
    SCOPE_ADDRESS = "GPIB0::1::INSTR"

    __toml_config__ = {
        "device.DPO7104_TekTronix_scope": {
            "_section_description": "DPO7104_TekTronix_scope configuration",
            "averages": {"_value": 10, "_description": "Number of averages"}, #set to 1 for non-averaged data, set to >1 for averaged data, but be aware this will slow down your acquisition loop as the scope needs to acquire and process multiple waveforms for each measurement cycle
            "start_bound": {"_value": 1.0e-7, "_description": "Starting bound, the position of the first cursor relative to the trigger"},
            "end_bound": {"_value": 1.0e-4, "_description": "Ending bound, the position of the second cursor relative to the trigger"},
            "area": {"_value": True, "_description": "Pulls area data"},
            "waveform": {"_value": False, "_description": "Pulls wavefrom data, channel 1"},
            "trigger": {"_value": False, "_description": "Pulls trigger waveform data, channel 2"},
        }
    }

    def __init__(self, config, name="DPO7104_TekTronix_scope", connect_to_rex=True):
        self.state = 0
        self.connect_to_rex = connect_to_rex
        super().__init__(name=name)
        self.bind_config(config)
        self.logger.debug(f"{self.name} connected with this config {self.config}")

        if self.connect_to_rex:
            self.sock = self.tcp_connect()

        self.scope = None

        self.open_connection()
        self.set_config()
        self.set_cursors()

        self.measurements = {
            "area": Measurement(data=[], unit="mV*s"), 
            "waveform": Measurement(data=[], unit="mV"),
            "trigger": Measurement(data=[], unit="mV"),
            "time_from_trigger": Measurement(data=[], unit="s")
        }

        self.validate_measurements()

    def open_connection(self):
            """Opens the resource manager and connects to the scope, saving it to self.scope."""
            try:
                rm = pyvisa.ResourceManager(self.RESOURCE_MANAGER)
                if self.SCOPE_ADDRESS not in rm.list_resources():
                    self.logger.error(f"Scope address {self.SCOPE_ADDRESS} not found in available resources: {rm.list_resources()}")
                    raise Exception(f'{self.SCOPE_ADDRESS} not in {rm.list_resources()}')
                else:
                    self.scope = rm.open_resource(self.SCOPE_ADDRESS)
                    self.scope.timeout = 25000 
                    
                    try:
                        TRUE_NAME = 'TEKTRONIX,DPO7104,B069280,CF:91.1CT FV:5.3.5 Build 22'  
                        idn = self.scope.query("*IDN?").strip()
                        if TRUE_NAME not in idn: 
                            self.logger.error(f"Unexpected Scope ID: {idn} does not contain expected identifier {TRUE_NAME}")
                            raise Exception(f"Unexpected Scope ID: {idn} is not {TRUE_NAME}")
                    except Exception as e:
                        self.logger.error(f"Scope did not accept ID query: {e}")

            except Exception as e:
                self.logger.error(f"pyvisa.ResourceManager did not work: {e}")

    def set_config(self):
        self.averages = self.require_config("averages")
        self.start_bound = self.require_config("start_bound")
        self.end_bound = self.require_config("end_bound")
        self.area_enabled = self.require_config("area")
        self.waveform_enabled = self.require_config("waveform")
        self.trigger_enabled = self.require_config("trigger")

        if not self.scope:
            raise RuntimeError("Oscilloscope connection is not open. Check the cable connections.")

        #self.full_autoset()

        #remember to manually set the vertical scale for the max peak to fill the screen
        #then all peaks will not go offscreen and be relative which is essential

        self.scope.write("TRIGger:A:TYPe EDGE")
        self.scope.write("TRIGger:A:EDGE:SOUrce CH2") 
        self.scope.write("TRIGger:A:EDGE:SLOPe FALL") 
        #self.scope.write("TRIGger:A SETLevel") #setting to 50% gets lost in the noise

        if self.averages == 1:
            self.scope.write(f"ACQuire:MODe SAMple")
        else:
            self.scope.write(f"ACQuire:MODe AVErage")
            self.scope.write(f"ACQuire:NUMAVg {self.averages}") 

        #v_position = 3.8 
        #self.scope.write(f'CH1:POSition {v_position}') #turn off to allow manual adjustment

        self.scope.write("*CLS")

    def set_cursors(self): 
        self.scope.write('CURSor:STATE ON') #this doesn't always set cursors to be from channel 1, check the scope
        self.scope.write('CURSor:FUNCtion VBARS')
        self.scope.write(f'CURSor:VBARS:POS1 {self.start_bound}')
        self.scope.write(f'CURSor:VBARS:POS2 {self.end_bound}')
 
        self.scope.write('MEASUrement:GATing ON')
        self.scope.write('MEASUrement:IMMed:TYPE AREA')
        self.scope.write(f'MEASUrement:IMMed:SOUrce CH1')
        time.sleep(0.5)

    def measure_area(self):
        if self.averages > 1:
            self.scope.write('ACQuire:STOPAfter SEQUENCE')
            self.scope.write('ACQuire:STATE RUN')
            
            # Base buffer (e.g. 5s) + expected time per average (e.g. 0.5s)
            timeout_at = time.time() + 5.0 + (self.averages * 0.5)
            
            while True:
                is_busy = int(self.scope.query("BUSY?"))
                if not is_busy:
                    break # Success, acquisition is completed
                    
                if time.time() > timeout_at:
                    self.scope.write('ACQuire:STATE STOP')
                    raise TimeoutError(f"Scope timed out waiting for {self.averages} averages. Check trigger!")
        
        self.scope.write('MEASUrement:IMMEd:STATE ON')
        area = float(self.scope.query('MEASUrement:IMMEd:VALue?'))

        data = -1.0 * area #PMT is negative voltage

        self.measurements["area"] = Measurement(
                data=[data],
                unit="mV*s",
            )
    
    def measure_waveform(self, channel=1):
        """Slowly pulls the waveform data, and data to make the time axis. Channel 2 for trigger for debugging.
        This will also create a massive amount of data and the scope's cpu can struggle to keep up, 
        so use with caution and consider using only area measurements for faster acquisition loops."""
        
        self.scope.write(f"DATa:SOUrce CH{channel}")
        self.scope.write("DATa:ENCdg RIBINARY")
        self.scope.write("DATa:WIDth 2") 
        self.scope.write("DATa:STARt 1")
        self.scope.write("DATa:STOP 100000") #will take ~4s, there is probably a faster method

        # Query scaling parameters from the preamble
        y_mult = float(self.scope.query("WFMOutpre:YMUlt?"))
        y_off  = float(self.scope.query("WFMOutpre:YOFf?"))
        y_zero = float(self.scope.query("WFMOutpre:YZEro?"))
        x_incr = float(self.scope.query("WFMOutpre:XINcr?"))
        x_zero = float(self.scope.query("WFMOutpre:XZEro?"))
        trigger_pos = float(self.scope.query("HORizontal:MAIn:SCAle?"))

        self.logger.debug(f"Waveform scaling parameters: y_mult={y_mult}, y_off={y_off}, y_zero={y_zero}, x_incr={x_incr}, x_zero={x_zero}, trigger_pos={trigger_pos}")

        self.scope.write("ACQuire:STOPAfter SEQuence")

        adc_samples = np.array(self.scope.query_binary_values("CURVe?", datatype='h', is_big_endian=True))

        self.scope.write("ACQuire:STOPAfter RUNSTOP")
        self.scope.write("ACQuire:STATE RUN")

        voltages = (adc_samples - y_off) * y_mult + y_zero
        time_axis = np.arange(adc_samples.size) * x_incr + x_zero - trigger_pos #relative to trigger

        data = voltages.tolist()
        times = time_axis.tolist()

        self.measurements["time_from_trigger"] = Measurement(
                data=[times],
                unit="s",
            )

        if channel == 1:
            self.measurements["waveform"] = Measurement(
                data=[data],
                unit="mV",
            )
        elif channel == 2:
            self.measurements["trigger"] = Measurement(
                data=[data],
                unit="mV",
            )
        
    def measure(self):
        self.scope.write("*CLS")

        if self.area_enabled:
            self.measure_area()
        if self.waveform_enabled:
            self.measure_waveform()
        if self.trigger_enabled:
            self.measure_waveform(2)

        self.state += 1

        if self.connect_to_rex:
            payload = self.create_payload()
            self.tcp_send(payload, self.sock)

        return self.measurements
    
    def full_autoset(self):
        self.scope.query("*OPC?")
        self.scope.write("AUToset EXECute")
        
    def close(self):
        if self.scope:
            self.scope.close()

    