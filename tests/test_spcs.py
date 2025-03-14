import os

from spcs_instruments import spcs_instruments_utils


@spcs_instruments_utils.pyfex_support
class YourClass:
    def __init__(self, config):
        self.config = config
        self.init_time_s = time.time()
        self.data = {}    
            
import pytest
import time

config = {
        "level1": {
            "level2": {
                "target_key": "expected_value"
            }
        },
        "other_key": "other_value"
    }
@pytest.fixture
def obj():
    instance = YourClass(config)
    instance.config = {
        "level1": {
            "level2": {
                "target_key": "expected_value"
            }
        },
        "other_key": "other_value"
    }
    instance.init_time_s = time.time() - 100  # Simulate 100 seconds since init
    instance.name = "test_device"
    instance.data = {
        "temperature": [22.5, 23.0],
        "pressure": [101.2]
    }
    return instance

def test_find_key_existing(obj):
    assert obj.find_key("target_key") == "expected_value"

def test_find_key_missing(obj):
    with pytest.raises(ValueError):
        obj.find_key("non_existent_key")

def test_require_config_success(obj):
    assert obj.require_config("target_key") == "expected_value"

def test_require_config_failure(obj):
    with pytest.raises(ValueError):
        obj.require_config("missing_key")

def test_create_payload_structure(obj):
    payload = obj.create_payload()
    assert "device_name" in payload
    assert "device_config" in payload
    assert "measurements" in payload
    assert payload["device_name"] == "test_device"
    
    assert payload["measurements"]["time since initialisation (s)"][0] == pytest.approx(100, abs=1)


def test_adjust_payload_single_entry(obj):
    payload = {"measurements": {"temperature": [22.5]}}
    assert obj.adjust_payload(payload)["measurements"]["temperature"] == [22.5]

def test_adjust_payload_multiple_entries(obj):
    payload = {"measurements": {"temperature": [22.5, 23.0]}}
    assert obj.adjust_payload(payload)["measurements"]["temperature"] == [[22.5, 23.0]]

def test_adjust_payload_already_wrapped(obj):
    payload = {"measurements": {"temperature": [[22.5, 23.0]]}}
    assert obj.adjust_payload(payload)["measurements"]["temperature"] == [[22.5, 23.0]]
