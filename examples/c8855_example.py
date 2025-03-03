import os
import sys
from spcs_instruments import C8855_counting_unit, Experiment

import time

def test_fake_experiment():
    def a_measurement(config) -> dict:
        counter = C8855_counting_unit(config_path)
        counter.setup_config()
        for i in range(100):
            data = counter.measure()
            time.sleep(0.1)



    dir_path = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(dir_path, "..", "templates", "config6.toml")
    config_path = os.path.abspath(config_path)

    experiment = Experiment(a_measurement, config_path)
    experiment.start()


if __name__ == "__main__":
    test_fake_experiment()
    print("experiment complete!")
