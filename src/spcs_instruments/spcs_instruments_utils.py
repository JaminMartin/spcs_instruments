from time import sleep
import time
import datetime
import os
import toml





def load_config(path: str) -> dict:
    with open(path, 'r') as f:
        config_toml = toml.load(f)
    return config_toml    




