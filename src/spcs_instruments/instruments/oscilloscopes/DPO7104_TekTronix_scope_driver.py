import time
import numpy as np
import pyvisa

from rex_utils import Measurement, RexSupport


class DPO7104_TekTronix_scope(RexSupport):
    """Driver for the Tektronix DPO7104 oscilloscope over GPIB using PyVISA.

    This class manages instrument connection, configuration, gated area integration, waveform
    capture, and optional forwarding of measurement payloads to a Rex server.

    The driver supports averaged acquisitions, cursor-based gated area measurements on CH1,
    raw voltage waveform downloads for CH1 and CH2, and limited trigger setup on CH2. Time axis 
    must be reconstructed from saved parameters. 

    KNOWN FOOTGUNS:
    - Waveform downloads can be slow, massive and may cause the scope's CPU to struggle, or even overfill the computer storage.
        Used the samples_saved config to reduce the amount saved.
    - Area measurement pulled from the scope vs area calculated from the pulled waveform can differ if the first 
        cursor is <1.0e-7s or negative, relative to the trigger. This is only an issue if you are setting the cursor 
        tiny and then trying to compare the area measurement to a calculated area from the waveform, if you are just 
        using the area measurement as a relative metric, such as for emission scans, then this is not a problem.
    - This driver assumes a negative-going output and inverts the area measurement accordingly, if you are have  
        a positive signal you will need to multiply the area by -1 to get the correct polarity. Beware of waveforms
        that have significant positive and negative components, as the area measurement may not reflect the full area of 
        the pulse in this case.
    - The SCOPE_ADDRESS and RESOURCE_MANAGER may need to be adjusted depending on your specific GPIB connection. 
    - If you do not know the strongest transition to maunally set the vertical scale for, you can run a quick emission scan and
        look at the CH1 waveform (on the scope) to find the max peak, then set the vertical scale so that this peak fills
        the screen, this will hopefully ensure all peaks are relative and do not go offscreen.

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
        step_data_puller(new_size=50): Steps about to get sparse waveform voltage data, saves storage space.
        measure_waveform(channel=1): Download and scale the waveform voltage data and time axis parameters from the given channel.
        measure(): Run enabled measurements and optionally send the payload to Rex.
        full_autoset(): Execute the instrument autoset sequence.
        close(): Close the PyVISA resource safely.
    """

    #pyvisa settings
    RESOURCE_MANAGER = '' #default to pyvisa's default backend, but can be set to "@ivi" or other backends if needed for compatibility with specific GPIB-USB adapters or drivers. 
    SCOPE_ADDRESS = "GPIB0::1::INSTR" #may need to change for PCI-GPIB

    __toml_config__ = {
        "device.DPO7104_TekTronix_scope": {
            "_section_description": "DPO7104_TekTronix_scope configuration",
            "averages": {"_value": 10, "_description": "Number of averages"}, #set to 1 for non-averaged data, set to >1 for averaged data, but be aware this will slow down your acquisition loop
            "start_bound": {"_value": 1.0e-7, "_description": "Starting bound, the position of the first cursor relative to the trigger"},
            "end_bound": {"_value": 1.0e-3, "_description": "Ending bound, the position of the second cursor relative to the trigger"},
            "area": {"_value": True, "_description": "Pulls area data"},
            "waveform": {"_value": False, "_description": "Pulls voltage wavefrom data, channel 1"},
            "trigger": {"_value": False, "_description": "Pulls trigger waveform data, channel 2"},
            "samples_saved": {"_value": 50, "_description": "Number of samples to be saved of the waveform"}, #100000 for all, ie for lifetimes. Don't do this for multiple scans.
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
            "area": Measurement(data=[], unit="Vs"),  #may not be these units on display
            "waveform": Measurement(data=[], unit="V"), #may not be these units on display
            "trigger": Measurement(data=[], unit="V"), #may not be these units on display
            "time_from_trigger_parameters": Measurement(data=[], unit="s") #unit after reconstruction, use: np.arange(0, {int(self.record_length)}, step={int(self.record_length)//voltages.size}) * {x_incr} + {x_zero} - {trigger_pos}
        }

        self.validate_measurements()

    def open_connection(self):
            """Opens the resource manager and connects to the scope, saving it to self.scope."""
            try:
                rm = pyvisa.ResourceManager(self.RESOURCE_MANAGER)
                if self.SCOPE_ADDRESS not in rm.list_resources():
                    self.logger.error(f"Scope address {self.SCOPE_ADDRESS} not found in available resources: {rm.list_resources()}")
                    raise Exception(f'{self.SCOPE_ADDRESS} not in {rm.list_resources()}. Try changing the RESOURCE_MANAGER')
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
                self.logger.error(f"pyvisa.ResourceManager() did not work: {e}")

    def set_config(self):
        self.averages = self.require_config("averages")
        self.start_bound = self.require_config("start_bound")
        self.end_bound = self.require_config("end_bound")
        self.area_enabled = self.require_config("area")
        self.waveform_enabled = self.require_config("waveform")
        self.trigger_enabled = self.require_config("trigger")
        self.samples_saved = self.require_config("samples_saved")

        if not self.scope:
            raise RuntimeError("Oscilloscope connection is not open. Check the cable connections.")

        #self.full_autoset()

        #remember to manually set the vertical scale for the max peak to fill the screen
        #then all peaks will not go offscreen and be relative which is essential

        self.scope.write("TRIGger:A:TYPe EDGE")
        self.scope.write("TRIGger:A:EDGE:SOUrce CH2") 
        self.scope.write("TRIGger:A:EDGE:SLOPe FALL") 
        #self.scope.write("TRIGger:A SETLevel") #setting to 50% often gets lost in the noise, set manually instead

        if self.averages == 1:
            self.scope.write(f"ACQuire:MODe SAMple")
        else:
            self.scope.write(f"ACQuire:MODe AVErage")
            self.scope.write(f"ACQuire:NUMAVg {self.averages}") 

        #v_position = 3.8 
        #self.scope.write(f'CH1:POSition {v_position}') #turn off to allow manual adjustment

        self.scope.write("*CLS") #clears the event status registers, not the acquisitions

    def set_cursors(self): 
        self.scope.write('CURSor:STATE ON') #this sometimes doesn't set cursors to be from channel 1, check the scope
        self.scope.write('CURSor:FUNCtion VBARS')
        self.scope.write(f'CURSor:VBARS:POS1 {self.start_bound}')
        self.scope.write(f'CURSor:VBARS:POS2 {self.end_bound}')
 
        self.scope.write('MEASUrement:GATing ON')
        self.scope.write('MEASUrement:IMMed:TYPE AREA')
        self.scope.write(f'MEASUrement:IMMed:SOUrce CH1')
        time.sleep(0.5)

    def measure_area(self):
        """Waits till the scope has enough acquisitionS, from now, to make an average, then pulls the area and
        multiplies by -1"""
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
        a_unit = str(self.scope.query('MEASUrement:IMMEd:UNits?').strip()).strip('"')

        data = -1.0 * area #PMT is negative voltage

        self.measurements["area"] = Measurement(
                data=[data],
                unit=a_unit,
            )
        
    def step_data_puller(self, new_size=50):
        """Pulls one point of the waveform data, then steps further and pulls again, to try to avoid overwhelming the scope's 
        CPU and saving massive data files. This is a bit of a hack, but you cannot change the scope's sampling rate (and thus 
        record length) without also changing the horizontal scale. If new_size is too big it will be very slow, but won't
        create massive data files."""
        total_points = self.record_length  #likely to be 100000 for real data
        step_size = total_points // new_size
        adc_samples = np.zeros(new_size)
        pull_log = 0

        for start in range(1, total_points+1, step_size):
            stop = min(start, total_points) #pulls 1 point every step
            self.scope.write(f"DATa:STARt {start}")
            self.scope.write(f"DATa:STOP {stop}")
            adc_samples[start//step_size] = (self.scope.query_binary_values("CURVe?", datatype='h', is_big_endian=True, container=np.ndarray))[0]
            pull_log += 1

        self.logger.debug(f'Made: {pull_log} CURve? pulls')
        return np.array(adc_samples)
    
    def measure_waveform(self, channel=1):
        """Slowly pulls the waveform data and the parameters to reconstruct the time axis. Channel 2 for trigger for debugging.
        This will save a lot of data and the scope's cpu can struggle to keep up, so use with caution and only use if required"""
        if self.averages > 1 and not self.area_enabled: #wait till fully averaged
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

        self.scope.write(f"DATa:SOUrce CH{channel}")
        self.scope.write("DATa:ENCdg RIBINARY")
        self.scope.write("DATa:WIDth 2") 

        self.record_length = int(self.scope.query("HORizontal:RECOrdlength?").strip())

        if self.samples_saved > 90000:
            self.scope.write("DATa:STARt 1")
            self.scope.write(f"DATa:STOP {self.record_length}") #save all 100000 data points, will take ~4s, there is probably a better method
            self.scope.write("ACQuire:STOPAfter SEQuence") #stops the scope to pull, may need to put inside step_data_puller
            adc_samples = np.array(self.scope.query_binary_values("CURVe?", datatype='h', is_big_endian=True))
            self.scope.write("ACQuire:STOPAfter RUNSTOP")
            self.scope.write("ACQuire:STATE RUN")

        else:
            self.scope.write("ACQuire:STOPAfter SEQuence")
            adc_samples = self.step_data_puller(new_size=self.samples_saved)
            self.scope.write("ACQuire:STOPAfter RUNSTOP")
            self.scope.write("ACQuire:STATE RUN")

        # Query scaling parameters from the preamble
        y_mult = float(self.scope.query("WFMOutpre:YMUlt?"))
        y_off  = float(self.scope.query("WFMOutpre:YOFf?"))
        y_zero = float(self.scope.query("WFMOutpre:YZEro?"))

        x_incr = float(self.scope.query("WFMOutpre:XINcr?"))
        x_zero = float(self.scope.query("WFMOutpre:XZEro?"))
        trigger_pos = float(self.scope.query("HORizontal:MAIn:SCAle?"))

        self.logger.debug(f"Waveform scaling parameters: y_mult={y_mult}, y_off={y_off}, y_zero={y_zero}, x_incr={x_incr}, x_zero={x_zero}, trigger_pos={trigger_pos}")

        voltages = (adc_samples - y_off) * y_mult + y_zero
        #time_axis = np.arange(adc_samples.size) * x_incr + x_zero - trigger_pos #relative to trigger

        data = voltages.tolist()
        #times = time_axis.tolist()
        y_unit = str(self.scope.query("WFMOutpre:YUnit?").strip()).strip('"') #to check mV or V
        x_unit = str(self.scope.query("WFMOutpre:XUnit?").strip()).strip('"')

        time_params = [int(self.record_length), int(self.record_length)//voltages.size, x_incr, x_zero, trigger_pos]
        #times = np.arange(0, {int(self.record_length)}, step={int(self.record_length)//voltages.size}) * {x_incr} + {x_zero} - {trigger_pos}
        
        self.measurements["time_from_trigger_parameters"] = Measurement(
                data=[time_params],
                unit=x_unit, #need to reconstruct, but will then be in s
            )

        if channel == 1:
            self.measurements["waveform"] = Measurement(
                data=[data],
                unit=y_unit,
            )
        elif channel == 2:
            self.measurements["trigger"] = Measurement(
                data=[data],
                unit=y_unit,
            )
        else:
            raise Exception('Only channel 1 and 2 supported for data saving, but this could easily be modified')
        
    def measure(self):
        self.scope.write("*CLS") #clears the event status registers, not the acquisitions

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
        self.scope.write("AUToset EXECute")
        
    def close(self):
        if self.scope:
            self.scope.close()

    