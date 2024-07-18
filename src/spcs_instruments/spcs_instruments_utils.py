import toml
import spcs_instruments.pyfex as spi


def load_config(path: str) -> dict:
    with open(path, "r") as f:
        config_toml = toml.load(f)
    return config_toml


class Experiment:
    def __init__(self, measurement_func, config_path):
        self.measurement_func = measurement_func
        self.config_path = config_path

    def start(self):
        spi.start_experiment(self.config_path)
        measurement_data = self.measurement_func(self.config_path)
        spi.update_experiment_log(measurement_data)
