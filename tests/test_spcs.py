import os
import sys
import pytest
import numpy as np
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.spcs_instruments.instruments.siglent_sds_2352xe_driver import SiglentSDS2352XE
from src.spcs_instruments.instruments.test_instrument import Fake_daq
from src.spcs_instruments.spcs_instruments_utils import Experiment

def test_measure():
    dir_path = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(dir_path, '..', 'templates', 'config.toml')
    config_path = os.path.abspath(config_path)

    scope = SiglentSDS2352XE(config_path)

    for i in range(5):
        with pytest.raises(Exception):
            volts = scope.measure()
            print(volts)
            assert False, "An exception was raised during measurement"
    scope.close()     


def test_experiment():

    def a_measurement(config) -> dict:
        daq = SiglentSDS2352XE(config)
        daq2 = Fake_daq(config)
        for i in range(5):
                daq.measure()
                daq2.measure()

        daq.close()
        data = {
        daq.name: daq.data,
        daq2.name: daq2.data}
        return data
   

def test_fake_experiment():

    def a_measurement(config) -> dict:

        daq = Fake_daq(config)
        for i in range(5):
                daq.measure()
      


        data = {
        daq.name: daq.data}
        return data
    
    dir_path = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(dir_path, '..', 'templates', 'config.toml')
    config_path = os.path.abspath(config_path)

 
    experiment = Experiment(a_measurement, config_path)
    experiment.start()


    with open(experiment.log_file.name, 'r') as f:
        log_contents = f.read()
    assert "Experiment started at" in log_contents
    assert "Experiment information" in log_contents
    assert "SDS2352X-E" in log_contents
    assert "Measurement data for simulated daq:" in log_contents
    assert "Experiment ended at" in log_contents



