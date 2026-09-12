import os
import sys
import time

from rex_utils import Session

from spcs_instruments import HoribaiHR550

from DPO7104_TekTronix_scope_driver import DPO7104_TekTronix_scope

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def emission_experiment_test():
    def scope_spec_measurement(config) -> dict:
        spec = HoribaiHR550(config)
        tektronix = DPO7104_TekTronix_scope(config)

        spec.set_wavelength(spec.initial_wavelength)
        steps = int((spec.final_wavelength - spec.initial_wavelength) / spec.step_size)
        for i in range(steps+1):
            val = tektronix.measure()
            spec.measure()
            spec.spectrometer_step()
            
        tektronix.close()

        return

    dir_path = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(dir_path, "emission_config.toml") #adjust the path to the config file as needed
    config_path = os.path.abspath(config_path)

    experiment = Session(scope_spec_measurement, config_path)
    experiment.start()


if __name__ == "__main__":
    emission_experiment_test()

#run: rex run .\emission_measurement_test.py -o .\Outputs\  