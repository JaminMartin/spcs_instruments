#!/usr/bin/env python3


"""Base class forREST API on MI cryostations
"""

import sys
import os
from . import instrument 

class PidScheduleItem:
    def __init__(self, temperature, kc=None, ti=None, td=None):
        self.temperature = temperature
        self.kc          = kc
        self.ti          = ti
        self.td          = td
        return
    def __lt__(self, other): 
        if self.temperature != other.temperature: return self.temperature < other.temperature
        elif self.kc != other.kc:                 return self.kc < other.kc
        elif self.ti != other.ti:                 return self.ti < other.ti
        else:                                     return self.td < other.td
    def __repr__(self):
        return repr((self.temperature, self.kc, self.ti, self.td))

    
class GenericCryostat(instrument.Instrument):
    """Functionality common to all cryostat instruments. 

    All derived classes should register themselves using the
    @genericcryostat.register decorator. 
    """
    def __init__(self, ip, port, version='v1', verbose=False, tunnel=False):
        super().__init__(ip=ip,
                         port=port,
                         version=version,
                         verbose=verbose,
                         tunnel=tunnel)
        return
    
    def cryo_thermometer_channels(self) -> [tuple]:
        """Return names of the thermometers for s and xp series Cryostations

        Return 
           tuple(location, channel) 
           example ('sampleChamber', 'platform')
        """

        def is_tc(x):
            """Determine if endpoint is a TC (temperature controller)

            We use this to filter out all the non-TC endpoints when we
            iterate through the list of all endpoints.
            """
            return (len(x)==10
                    and x[3]=='v1'
                    # and x[4] in ('cooler', 'sampleChamber', 'magnet')
                    and x[5]=='temperatureControllers'
                    and x[7:10]==['thermometer', 'properties', 'sample'])
            
        # First we'll search for endpoints match the following pattern
        #   0    1       2             3           4                              5            6      7          8        9
        #  http://192.168.45.184:47103/v1/{cooler|sampleChamber|magnet}/temperatureControllers/*/thermometer/properties/sample
        return list(set([(x[4], x[6]) for x in [x.split('/') for x in self.get('/')] if is_tc(x)]))

    def cryo_thermometer_channels_by_name(self) -> dict:
        """Return a Lookup table from name of the channel to return a
           fully unique description (i.e. the channel name and
           location) for example
              {'platform',   ('sampleChamber', 'platform'), 
               'stage1',     ('cooler',        'stage1')}
        """
        return { x[1]: x for x in self.cryo_thermometer_channels() }
    
    def cryo_tc_channel_endpoint_root(self, channel):
        """Return endpoint root for TCs for s and xp series Cryostations

        This is designed to use in conjunction with instrument.get_prop()

        Keywords arguments:
           channel     A pair of strings.  First item is the name of the 
                       chamber (e.g. cooler).  Second item is the channel
                       (e.g. stage2)
        """

        return f'/{channel[0]}/temperatureControllers/{channel[1]}'
    
    def _tc_root(self, channel): return self.cryo_tc_channel_endpoint_root(channel)

    def cryo_tc_pid_schedule_endpoint(self, channel):
        """Return endpoint name of the PID schedule for a cryostation

        This is designed to use in conjunction with instrument.get_prop()

        Keywords arguments:
           channel     A pair of strings.  First item is the name of the 
                       chamber (e.g. cooler).  Second item is the channel
                       (e.g. stage2)
        """

        return f'{self.cryo_tc_channel_endpoint_root(channel)}/properties/pidSchedule'


    def cryo_thermometer_channel_sample_endpoint(self, channel):
        """Return endpoint names of the thermometers for s and xp series Cryostations

        This is designed to use in conjunction with instrument.get_prop()

        Keywords arguments:
           channel     A pair of strings.  First item is the name of the 
                       chamber (e.g. cooler).  Second item is the channel
                       (e.g. stage2)
        """

        return f'{self.cryo_tc_channel_endpoint_root(channel)}/thermometer/properties/sample'

    def cryo_heater_channel_sample_endpoint(self, channel):
        """Return endpoint names of the heaters for s and xp series Cryostations

        This is designed to use in conjunction with instrument.get_prop()

        Keywords arguments:
           channel     A pair of strings.  First item is the name of the 
                       chamber (e.g. cooler).  Second item is the channel
                       (e.g. stage2)
        """

        return f'{self.cryo_tc_channel_endpoint_root(channel)}/heater/properties/sample'

    def cryo_onoff_channel_sample_endpoint(self, channel):
        """Return endpoint names of the thermometers for s and xp series Cryostations

        This is designed to use in conjunction with instrument.get_prop()

        Keywords arguments:
           channel     A pair of strings.  First item is the name of the 
                       chamber (e.g. cooler).  Second item is the channel
                       (e.g. stage2)
        """

        return f'{self.cryo_tc_channel_endpoint_root(channel)}/properties/onOffSample'

    def set_on_off_power(self, channel: tuple, value: float) -> None:
        path = self._tc_root(channel) + "/properties/onOffPower"
        return self.set_prop(path, {'onOffPower': value})
    

    def set_on_off_hysteresis(self, channel: int, value: float) -> None:
        path = self._tc_root(channel) + "/properties/onOffHysteresis"
        return self.set_prop(path, {'onOffHysteresis': value})
        
    def enable_controller(self, channel, mode, temperature):
        assert mode in ('OnOff', 'PID')
        root = self.cryo_tc_channel_endpoint_root(channel)
        return self.call_method(root + "/methods/enableController(ControlMode:mode,double:temperature)",
                         {'mode':         mode,
                          'temperature':  temperature})

    def disable_controller(self, channel):
        return self.call_method(self.cryo_tc_channel_endpoint_root(channel)
                         + "/methods/disableController()")

    def get_tc_pid_schedule(self, channel: (str,str)) -> [PidScheduleItem]:
        """Return the PID schedule for the temperature controller. 

        Keywords arguments:
           channel     A pair of strings.  First item is the name of the 
                       chamber (e.g. sampleChamber).  Second item is the channel
                       (e.g. platform)
        """
        ep = self.cryo_tc_pid_schedule_endpoint(channel)
        print(f"ep is {ep}")
        try:
            sched = self.get_prop(ep)
        except instrument.ApiError:
            print("Failed to get pid schedule")
            sched = {'pidSchedule': {'rows': []}}
        return sorted([PidScheduleItem(temperature = row['temperature'],
                                       kc          = row['kc'],
                                       ti          = row['ti'],
                                       td          = row['td']) 
                       for row in sched['pidSchedule']['rows']])
    
    def set_tc_pid_schedule(self,
                            channel: (str,str),
                            sched:   [PidScheduleItem]) -> None:
        """Store the PID schedule on the system. 
        """
        data = {'rows': [{'temperature': r.temperature, 'kc': r.kc, 'ti': r.ti, 'td': r.td}
                                         for r in sched]}
        print(f"data is {data}")
        print(f"Trying to set |{self.cryo_tc_pid_schedule_endpoint(channel)}|")
        self.set_prop(self.cryo_tc_pid_schedule_endpoint(channel), data)
        return 
        

    
_cryo_classes = {}
def register_cryo_class(cls, create=None):
    """

    Keyword arguments: 
       cls     A cryostation class.  (Should be derived from GenericCryostat)
       create  A function to create an object.  
    """
    if create is None: _cryo_classes[cls] = lambda ip, tunnel: cls(ip, 'v1', False, tunnel)
    else:              _cryo_classes[cls] = create
    return

def register(cls):
    """Class decorator to register a class derived from GenericCryostat

    Classes that are registered can take part in automatic device
    discovery through the connect_cryostat() function.

    Example
       @genericcryostat.register
       class SCryostation(genericcryostat.GenericCryostat): 
          ...

    Keyword arguments
      cls    The class being decorated.

    """
    assert issubclass(cls, GenericCryostat), "only cryostat objects should be registered as cryostats"
    register_cryo_class(cls)
    return cls

def connect_cryostat(host: str, tunnel: bool) -> GenericCryostat:
    """
    Try to connect to a cryostation HLM on the given IP address. 

    This function will try to connect to a cryostation using one 
    of the classes derived from GenericCryostat and registered 
    with the @genericcryostat.register class decorator.

    Keyword Paramameters
       host   -- Host name or IP address of a cryostation 
       tunnel -- Communicate through a secure SSH tunnel?

    Return 
       A GenericCryostat derived object, None if no connection could
       be established.         
    """
    #
    # First try to connect using one of the registered cryostat
    # classes.  Remember, this can only find a cryostat class if it's
    # been registered with the @genericcryostat.register decorator or
    # the register_cryo_class() function.
    # 
    cryo = None
    try:
        for c in _cryo_classes.keys():
            func = _cryo_classes[c]    # lookup the function to make a cryostation object
            cryo = func(host, tunnel)
            if cryo.is_up(): break;
            cryo.close()
            cryo = None
    except instrument.BadUrl:
        cryo = None

    #
    # If we couldn't find a specific one, try a generic.  Currently
    # this only looks on two different port numbers.
    #
    try:
        if cryo is None:
            for p in [instrument.Rest_Ports.scryostation_hlm,
                      instrument.Rest_Ports.xpcryostation_hlm]:
                cryo = GenericCryostat(host,
                                       port    = p,
                                       version = 'v1',
                                       tunnel  = tunnel);
                if cryo.is_up(): break
                cryo.close()
                cryo = None
    except instrument.BadUrl:
        cryo = None

    if cryo is None:
        print("raising instrument.CouldNotConnect()")
        raise instrument.CouldNotConnect()
    
    return cryo


