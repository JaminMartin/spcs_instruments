from spcs_instruments import HoribaiHR550, Experiment, C8855_counting_unit
import time
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def test_fake_experiment():
    def a_measurement(config) -> dict:
        spec = HoribaiHR550(config, bypass_homing=False)
        daq = C8855_counting_unit(config)
        spec.set_wavelength(550.00)
        for i in range(100):
            daq.measure()
            spec.spectrometer_step()
            spec.measure()
            time.sleep(2)

            

        data = {daq.name: daq.data,
                spec.name: spec.data}
        return data

    dir_path = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(dir_path, "..", "templates", "config7.toml")
    config_path = os.path.abspath(config_path)

    experiment = Experiment(a_measurement, config_path)
    experiment.start()


if __name__ == "__main__":
    test_fake_experiment()
    print("experiment complete!")