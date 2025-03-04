from spcs_instruments import SPCS_mixed_signal_box, Experiment
import os
import time

def test_fake_experiment():

    def a_measurement(config):
        switch = SPCS_mixed_signal_box(config, connect_to_pyfex=True)
        switch.measure()
        switch.set_channel_matrix("C","5")
        switch.set_channel_matrix("A","1")
        switch.set_channel_matrix("B","4")
        switch.set_channel_matrix("D","f")
        switch.measure()
        switch.switch_layout()
        switch.get_state()
        switch.measure()
        for i in range(100):
            switch.measure()
            time.sleep(1)

    dir_path = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(dir_path, "..", "templates", "config9.toml")
    config_path = os.path.abspath(config_path)

    experiment = Experiment(a_measurement, config_path)
    experiment.start()


if __name__ == "__main__":
    test_fake_experiment()