from spcs_instruments import SPCS_mixed_signal_box
import os

def test_fake_experiment():
    dir_path = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(dir_path, "..", "templates", "config8.toml")
    config_path = os.path.abspath(config_path)
    def a_measurement(config):
        switch = SPCS_mixed_signal_box(config, connect_to_pyfex=False)
        switch.set_channel_matrix("C","5")
        switch.set_channel_matrix("A","1")
        switch.set_channel_matrix("B","4")
        switch.set_channel_matrix("D","f")
        switch.get_state()
        switch.switch_layout()
        print(switch._state)
    a_measurement(config_path)




if __name__ == "__main__":
    test_fake_experiment()