"""Measure a fake DAQ once at each stable Lake Shore temperature target."""

from pathlib import Path
import time
import tomllib

from spcs_instruments import Lakeshore325, Test_daq


CONFIG_PATH = (
    Path(__file__).resolve().parents[1] / "templates" / "lakeshore_325_example.toml"
)

with CONFIG_PATH.open("rb") as config_file:
    sweep_config = tomllib.load(config_file)["temperature_sweep"]

targets_k = [
    float(sweep_config["initial_temperature_k"]),
    *(float(target) for target in sweep_config["target_temperatures_k"]),
]
poll_interval_s = float(sweep_config.get("poll_interval_s", 1.0))
max_wait_seconds = float(sweep_config.get("max_wait_seconds", 1800.0))

cryostat = Lakeshore325(CONFIG_PATH)
daq = Test_daq(CONFIG_PATH)

try:
    target_index = 0
    cryostat.go_to_temperature(targets_k[target_index])
    target_started_at = time.monotonic()

    while target_index < len(targets_k):
        if cryostat.is_at_setpoint():
            daq.measure()
            target_index += 1
            if target_index == len(targets_k):
                break
            cryostat.go_to_temperature(targets_k[target_index])
            target_started_at = time.monotonic()
        elif time.monotonic() - target_started_at >= max_wait_seconds:
            raise TimeoutError(
                f"Lake Shore did not stabilize at {targets_k[target_index]:.3f} K "
                f"within {max_wait_seconds:.0f} seconds"
            )
        time.sleep(poll_interval_s)
finally:
    cryostat.close()
