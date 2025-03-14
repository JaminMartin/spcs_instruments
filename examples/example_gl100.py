from spcs_instruments import Gl100, Experiment
import os
import time
def test_fake_experiment():

    def a_measurement(config):
        las = Gl100(config, connect_to_pyfex=True)
        total_positions = len(las.scan_data)
        measurement = las.measure()
        for i in range(total_positions):
            position = las.move_to_next_position()
            measurement = las.measure()
            time.sleep(0.25)
        time.sleep(10)
        las.return_to_zero()
        


    dir_path = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(dir_path, "..", "templates", "config8.toml")
    config_path = os.path.abspath(config_path)
    experiment = Experiment(a_measurement, config_path)
   
    experiment.start()
if __name__ == "__main__":
    test_fake_experiment()