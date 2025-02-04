import os
import sys




from spcs_instruments import Experiment
import time


def test_fake_experiment():
    def a_measurement(config) -> dict:
        for i in range(1000):
            time.sleep(2)
        return 

    dir_path = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(dir_path, "..", "templates", "config2.toml")
    config_path = os.path.abspath(config_path)

    experiment = Experiment(a_measurement, config_path)
    experiment.start()


if __name__ == "__main__":
    test_fake_experiment()