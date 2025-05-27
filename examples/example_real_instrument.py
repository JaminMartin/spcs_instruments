import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


from spcs_instruments import SiglentSDS2352XE
from spcs_instruments import Experiment


def test_fake_experiment():
    def a_measurement(config) -> dict:
        daq = SiglentSDS2352XE(config)

        for i in range(20):
            val = daq.measure()
            time.sleep(1)


        return 

    dir_path = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(dir_path, "..", "templates", "config3.toml")
    config_path = os.path.abspath(config_path)

    experiment = Experiment(a_measurement, config_path)
    experiment.start()


if __name__ == "__main__":
    test_fake_experiment()

