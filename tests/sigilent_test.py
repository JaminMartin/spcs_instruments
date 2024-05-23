import os
import sys
import pytest
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.spcs_instruments.instruments.siglent_sds_2352xe_driver import SiglentSDS2352XE


def test_measure():
    dir_path = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(dir_path, '..', 'templates', 'config.toml')
    config_path = os.path.abspath(config_path)

    scope = SiglentSDS2352XE(config_path)
    # scope.setup_config("test")
    for i in range(20):
        with pytest.raises(Exception):
            volts = scope.measure()
            assert False, "An exception was raised during measurement"