import os
import sys
import pytest
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


from spcs_instruments.instruments.test_instrument import Fake_daq
from spcs_instruments.spcs_instruments_utils import Experiment


def test_fake_experiment():
    def a_measurement(config) -> dict:
        daq = Fake_daq(config)
        for i in range(5):
           val = daq.measure()
           print(val)
        
        data = {daq.name: daq.data}
        return data

    dir_path = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(dir_path, "..", "templates", "config.toml")
    config_path = os.path.abspath(config_path)

    experiment = Experiment(a_measurement, config_path)
    experiment.start()


if __name__ == "__main__":
    test_fake_experiment()
    print("experiment complete!")
    
