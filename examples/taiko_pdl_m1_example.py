"""Run a calibrated wavelength/power profile with a PicoQuant Taiko.

Run this on Windows with PicoQuant's Taiko software/API installed.
"""

from pathlib import Path

from spcs_instruments import TaikoPDLM1


CONFIG_PATH = Path(__file__).resolve().parents[1] / "templates" / "config11.toml"

# Power is expressed relative to the attached head's calibrated maximum.
POWER_PROFILE_PERMILLE = [50, 100, 200, 100, 50]


laser = TaikoPDLM1(CONFIG_PATH)

try:
    laser.set_laser_mode("pulse")
    if not (laser.supports_wavelength_scan and laser.wavelength_scan_config):
        raise RuntimeError(
            "This example needs a wavelength_temperature_map and wavelength_scan "
            "table for the connected laser head."
        )

    for _ in range(laser.total_wavelength_steps):
        desired_wavelength = laser.move_to_next_wavelength()
        readings = laser.measure()
        estimated_wavelength = readings["estimated wavelength (nm)"].data[0]
        print(
            f"target={desired_wavelength:.3f} nm, "
            f"estimated={estimated_wavelength:.3f} nm"
        )
        for power_permille in POWER_PROFILE_PERMILLE:
            laser.set_power_permille(power_permille)
            readings = laser.measure()
            power_watts = readings["power setpoint (W)"].data[0]
            print(
                f"target={desired_wavelength:.3f} nm, power={power_permille}/1000, "
                f"setpoint={power_watts:.6f} W"
            )
finally:
    laser.shutdown()
