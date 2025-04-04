
import os
import sys


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


from spcs_instruments import Ocean_optics_spectrometer
from spcs_instruments import Experiment, Listener
import time

def test_fake_experiment():
    def a_measurement(config) -> dict:
        spectrometer = Ocean_optics_spectrometer(config, name = "OceanOpitics_Spectrometer")
        listener = Listener()

           
        while True:
            
            listener.check_state()
            spectrometer.measure()

            time.sleep(0.1)

        return 

    dir_path = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(dir_path, "..", "templates", "config10.toml")
    config_path = os.path.abspath(config_path)

    experiment = Experiment(a_measurement, config_path)
    experiment.start()


if __name__ == "__main__":
    test_fake_experiment()
