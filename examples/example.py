import os
import sys


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


from spcs_instruments import Test_daq, Test_spectrometer
from spcs_instruments import Experiment
import time

def test_fake_experiment():
    def a_measurement(config) -> dict:
        daq = Test_daq(config, name = "Test_DAQ_1")
        print("DAQ1 initialised")
        spectrometer = Test_spectrometer(config, name = "Test_Spectrometer")
        print("Test_Spectrometer initialised")
        for i in range(50):
            val = daq.measure()
            val2 = spectrometer.evaluate()
            print(val)
            print(val2)
            print("Starting next measurement")
            time.sleep(1)

        data = {daq.name: daq.data,
                spectrometer.name: spectrometer.data}
        return data

    dir_path = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(dir_path, "..", "templates", "config2.toml")
    config_path = os.path.abspath(config_path)

    experiment = Experiment(a_measurement, config_path)
    experiment.start()


if __name__ == "__main__":
    test_fake_experiment()
    print("experiment complete!")
