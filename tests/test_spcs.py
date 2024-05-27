import os
import sys
import pytest
import numpy as np
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.spcs_instruments.instruments.siglent_sds_2352xe_driver import SiglentSDS2352XE
from src.spcs_instruments.spcs_instruments_utils import Experiment

def test_measure():
    dir_path = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(dir_path, '..', 'templates', 'config.toml')
    config_path = os.path.abspath(config_path)

    scope = SiglentSDS2352XE(config_path)
    # scope.setup_config("test")
    for i in range(5):
        with pytest.raises(Exception):
            volts = scope.measure()
            assert False, "An exception was raised during measurement"
       


def test_experiment():
    # Define the measurement function
    def a_measurement(config) -> dict:
        daq = SiglentSDS2352XE(config)
        for i in range(20):
                daq.measure()

        data = {
        daq.name: daq.data}
        return data
   
    # Get the path to the config file
    dir_path = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(dir_path, '..', 'templates', 'config.toml')
    config_path = os.path.abspath(config_path)

    # Create and start the experiment
    experiment = Experiment(a_measurement, config_path)
    experiment.start()

    # Check the log file
    with open(experiment.log_file.name, 'r') as f:
        log_contents = f.read()
    assert "Experiment started at" in log_contents
    assert "Config contents:" in log_contents
    assert "Measurement data for" in log_contents
    assert "Experiment ended at" in log_contents