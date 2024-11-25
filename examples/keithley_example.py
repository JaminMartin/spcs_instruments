import os
import sys


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


from spcs_instruments import Keithley2400
from spcs_instruments import Experiment


def test_fake_experiment():
    def a_measurement(config) -> dict:
        keithley = Keithley2400(config_path)
        
        for i in range(10):
            val = keithley.measure()
        
            

        data = {keithley.name: keithley.data,
                }
        keithley.close()        
        return data
        
    dir_path = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(dir_path, "..", "templates", "config4.toml")
    config_path = os.path.abspath(config_path)

    experiment = Experiment(a_measurement, config_path)
    experiment.start()


if __name__ == "__main__":
    test_fake_experiment()
    print("experiment complete!")        
