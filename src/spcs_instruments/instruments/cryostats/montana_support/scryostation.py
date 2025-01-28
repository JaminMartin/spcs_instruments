#!/usr/bin/env python3
#
"""
Class to simplify RESTful API communication with the s-series Cryostation instrument.

Example usage:
 import scryostation
 cryo = scryostation.SCryostation('192.168.1.123')

 # Shows how to use high-level methods for accessing common functions
 cryo.cooldown()
 cryo.set_platform_target_temperature(3.1)
 cryo.get_platform_temperature()
 cryo.get_platform_temperature_stability()
 cryo.warmup()

 # Shows how to use generic post/get/put methods for accessing any REST url/end-point
 cryo.call_method('/controller/methods/cooldown()')
 cryo.get_prop('/sampleChamber/temperatureControllers/platform/thermometer/sample')['sample']['temperature']
 cryo.set_prop('/controller/properties/platformTargetTemperature', 1.7)
"""
import sys
import os
from . import instrument
from . import genericcryostat

Ports = instrument.Rest_Ports


@genericcryostat.register
class SCryostation(genericcryostat.GenericCryostat):
    def __init__(self, ip, version='v1', verbose=False, tunnel=False, port=Ports.scryostation_hlm):
        super().__init__(ip=ip,
                         port=port,
                         version=version,
                         verbose=verbose,
                         tunnel=tunnel)

    def cooldown(self):
        self.call_method('/controller/methods/cooldown()')

    def warmup(self):
        self.call_method('/controller/methods/warmup()')

    def vent(self):
        self.call_method('/controller/methods/vent()')

    def pull_vacuum(self):
        self.call_method('/controller/methods/pullVacuum()')

    def abort_goal(self):
        self.call_method('/controller/methods/abortGoal()')

    def get_system_goal(self):
        return self.get_prop('/controller/properties/systemGoal')['systemGoal']

    def get_system_state(self):
        return self.get_prop('/controller/properties/systemState')['systemState']

    def get_sample_chamber_pressure(self):
        return self.get_prop('/vacuumSystem/vacuumGauges/sampleChamberPressure/properties/pressureSample')['pressureSample']['pressure']

    def set_platform_bakeout_enabled(self, enabled):
        return self.set_prop('/controller/properties/platformBakeoutEnabled', enabled)

    def set_platform_bakeout_temperature(self, temperature):
        return self.set_prop('/controller/properties/platformBakeoutTemperature', temperature)

    def set_platform_bakeout_time(self, duration):
        return self.set_prop('/controller/properties/platformBakeoutTime', duration)

    def set_dry_nitrogen_purge_enabled(self, enabled):
        return self.set_prop('/controller/properties/dryNitrogenPurgeEnabled', enabled)

    def set_dry_nitrogen_purge_num_times(self, times):
        return self.set_prop('/controller/properties/dryNitrogenPurgeNumTimes', times)

    #
    # Vent methods
    #
    def set_vent_continuously_enabled(self, enabled):
        return self.set_prop('/controller/properties/ventContinuouslyEnabled', enabled)

    #
    # Pull Vacuum methods
    #
    def set_pull_vacuum_target_pressure(self, target):
        return self.set_prop('/controller/properties/pullVacuumTargetPressure', target)

    #
    # Stage1 methods
    #
    def get_stage1_temperature_sample(self):
        r = self.get_prop('/cooler/temperatureControllers/stage1/thermometer/properties/sample')
        return r['sample']

    def get_stage1_temperature(self):
        r = self.get_prop('/cooler/temperatureControllers/stage1/thermometer/properties/sample')
        return r['sample']['temperatureOK'], r['sample']['temperature']


    #
    # Stage2 methods
    #
    def get_stage2_temperature_sample(self):
        r = self.get_prop('/cooler/temperatureControllers/stage2/thermometer/properties/sample')
        return r['sample']

    def get_stage2_temperature(self):
        r = self.get_prop('/cooler/temperatureControllers/stage2/thermometer/properties/sample')
        return r['sample']['temperatureOK'], r['sample']['temperature']

    #
    # Platform methods
    #
    def get_platform_target_temperature(self):
        r = self.get_prop('/controller/properties/platformTargetTemperature')
        return r['platformTargetTemperature']

    def set_platform_target_temperature(self, target):
        return self.set_prop('/controller/properties/platformTargetTemperature', target)

    def get_platform_temperature(self):
        r = self.get_prop('/sampleChamber/temperatureControllers/platform/thermometer/properties/sample')
        return r['sample']['temperatureOK'], r['sample']['temperature']

    def get_platform_temperature_stability(self):
        r = self.get_prop('/sampleChamber/temperatureControllers/platform/thermometer/properties/sample')
        return r['sample']['temperatureStabilityOK'], r['sample']['temperatureStability']

    def set_platform_stability_target(self, target):
        return self.set_prop('/sampleChamber/temperatureControllers/platform/thermometer/properties/stabilityTarget', target)

    def get_platform_temperature_stable(self):
        r = self.get_prop('/sampleChamber/temperatureControllers/platform/thermometer/properties/sample')
        return r['sample']['temperatureStabilityOK'], r['sample']['temperatureStable']

    def get_platform_temperature_sample(self):
        r = self.get_prop('/sampleChamber/temperatureControllers/platform/thermometer/properties/sample')
        return r['sample']

    def get_platform_heater_sample(self):
        r = self.get_prop('/sampleChamber/temperatureControllers/platform/heater/properties/sample')
        return r['sample']

    #
    # User1 methods
    #
    def get_user1_temperature_sample(self):
        r = self.get_prop('/sampleChamber/temperatureControllers/user1/thermometer/properties/sample')
        return r['sample']

    def get_user1_temperature(self):
        r = self.get_prop('/sampleChamber/temperatureControllers/user1/thermometer/properties/sample')
        return r['sample']['temperatureOK'], r['sample']['temperature']

    def get_user1_temperature_stability(self):
        r = self.get_prop('/sampleChamber/temperatureControllers/user1/thermometer/properties/sample')
        return r['sample']['temperatureStabilityOK'], r['sample']['temperatureStability']

    def set_user1_stability_target(self, target):
        return self.set_prop('/sampleChamber/temperatureControllers/user1/thermometer/properties/stabilityTarget', target)

    def get_user1_temperature_stable(self):
        r = self.get_prop('/sampleChamber/temperatureControllers/user1/thermometer/properties/sample')
        return r['sample']['temperatureStabilityOK'], r['sample']['temperatureStable']    

    def set_user1_temperature_controller_enabled(self, enabled):
        return self.set_prop('/sampleChamber/temperatureControllers/user1/properties/controllerEnabled', enabled)

    def set_user1_target_temperature(self, target):
        return self.set_prop('/sampleChamber/temperatureControllers/user1/properties/targetTemperature', target)

    def get_user1_heater_sample(self):
        r = self.get_prop('/sampleChamber/temperatureControllers/user1/heater/properties/sample')
        return r['sample']

    #
    # User2 methods
    #
    def get_user2_temperature_sample(self):
        r = self.get_prop('/sampleChamber/temperatureControllers/user2/thermometer/properties/sample')
        return r['sample']

    def get_user2_temperature(self):
        r = self.get_prop('/sampleChamber/temperatureControllers/user2/thermometer/properties/sample')
        return r['sample']['temperatureOK'], r['sample']['temperature']

    def get_user2_temperature_stability(self):
        r = self.get_prop('/sampleChamber/temperatureControllers/user2/thermometer/properties/sample')
        return r['sample']['temperatureStabilityOK'], r['sample']['temperatureStability']

    def set_user2_stability_target(self, target):
        return self.set_prop('/sampleChamber/temperatureControllers/user2/thermometer/properties/stabilityTarget', target)

    def get_user2_temperature_stable(self):
        r = self.get_prop('/sampleChamber/temperatureControllers/user2/thermometer/properties/sample')
        return r['sample']['temperatureStabilityOK'], r['sample']['temperatureStable']

    def set_user2_temperature_controller_enabled(self, enabled):
        return self.set_prop('/sampleChamber/temperatureControllers/user2/properties/controllerEnabled', enabled)

    def set_user2_target_temperature(self, target):
        return self.set_prop('/sampleChamber/temperatureControllers/user2/properties/targetTemperature', target)

    def get_user2_heater_sample(self):
        r = self.get_prop('/sampleChamber/temperatureControllers/user2/heater/properties/sample')
        return r['sample']

    #
    # Cryo-Optic methods
    #
    def get_cryooptic_temperature_sample(self):
        r = self.get_prop('/sampleChamber/temperatureControllers/cryoOptic/thermometer/properties/sample')
        return r['sample']

    def get_cryooptic_temperature(self):
        r = self.get_prop('/sampleChamber/temperatureControllers/cryoOptic/thermometer/properties/sample')
        return r['sample']['temperatureOK'], r['sample']['temperature']

    def get_cryooptic_temperature_stability(self):
        r = self.get_prop('/sampleChamber/temperatureControllers/cryoOptic/thermometer/properties/sample')
        return r['sample']['temperatureStabilityOK'], r['sample']['temperatureStability']

    def set_cryooptic_stability_target(self, target):
        return self.set_prop('/sampleChamber/temperatureControllers/cryoOptic/thermometer/properties/stabilityTarget', target)

    def get_cryooptic_temperature_stable(self):
        r = self.get_prop('/sampleChamber/temperatureControllers/cryoOptic/thermometer/properties/sample')
        return r['sample']['temperatureStabilityOK'], r['sample']['temperatureStable']

    def set_cryooptic_temperature_controller_enabled(self, enabled):
        return self.set_prop('/sampleChamber/temperatureControllers/cryoOptic/properties/controllerEnabled', enabled)

    def set_cryooptic_target_temperature(self, target):
        return self.set_prop('/sampleChamber/temperatureControllers/cryoOptic/properties/targetTemperature', target)

    def get_cryooptic_heater_sample(self):
        r = self.get_prop('/sampleChamber/temperatureControllers/cryoOptic/heater/properties/sample')
        return r['sample']
    
    #
    # Magneto-Optic
    #
    def get_mo_enabled(self):
        r = self.get_prop('/magnetoOptic/magnet/properties/enabled')
        return r['enabled']
    
    def set_mo_enabled(self, enabled):
        return self.set_prop('/magnetoOptic/magnet/properties/enabled', enabled)
    
    def get_mo_state(self):
        r = self.get_prop('/magnetoOptic/magnet/properties/state')
        return r['state']
    
    def get_mo_safe_mode(self):
        r = self.get_prop('/magnetoOptic/magnet/properties/safeMode')
        return r['safeMode']

    def get_mo_calculated_field(self):
        r = self.get_prop('/magnetoOptic/magnet/properties/calculatedField')
        return r['calculatedField']

    def get_mo_measured_current(self):
        r = self.get_prop('/magnetoOptic/magnet/properties/measuredCurrent')
        return r['measuredCurrent']

    def get_mo_target_field(self):
        r = self.get_prop('/magnetoOptic/magnet/properties/targetField')
        return r['targetField']

    def set_mo_target_field(self, target):
        return self.set_prop('/magnetoOptic/magnet/properties/targetField', target)
