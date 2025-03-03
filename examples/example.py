import os
import sys


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


from spcs_instruments import Test_daq, Test_spectrometer, Test_cryostat
from spcs_instruments import Experiment
import time

def test_fake_experiment():
    def a_measurement(config) -> dict:
        daq = Test_daq(config, name = "Test_DAQ_1")
        spectrometer = Test_spectrometer(config, name = "Test_Spectrometer")
        cryostat = Test_cryostat(config)


        for j in range (5):
            cryostat.goto_setpoint(j * 5)
            spectrometer.goto_wavelength(500)
            for i in range(50):
                spectrometer.goto_wavelength(spectrometer.wavelength + spectrometer.step_size)
                val = daq.measure()
                val2 = spectrometer.measure()
                val3 = cryostat.measure()
                time.sleep(2)

        return 

    dir_path = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(dir_path, "..", "templates", "config2.toml")
    config_path = os.path.abspath(config_path)

    experiment = Experiment(a_measurement, config_path)
    experiment.start()


if __name__ == "__main__":
    test_fake_experiment()