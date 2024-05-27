from time import sleep
import time
import datetime
import os
import toml
import json
import numpy as np
from datetime import datetime
import pandas as pd



def load_config(path: str) -> dict:
    with open(path, 'r') as f:
        config_toml = toml.load(f)
    return config_toml    




class Experiment:
    def __init__(self, measurement_func, config_path):
        self.measurement_func = measurement_func
        self.config_path = config_path
        self.log_file = None

    def start(self):
 
        self.log_file = open(f"spcs_experiment_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log", "w")

 
        start_time = datetime.now()
        self.log(f"Experiment started at {start_time}\n")

        self.log(f"Experiment information:\n")
        config = load_config(self.config_path)
        for header, contents in config.items():
            self.log(f"{header}:")
            for key, value in contents.items():
                self.log(f"  {key} = {value}")
            self.log("")


        measurement_data = self.measurement_func(self.config_path)



        for device, data in measurement_data.items():
            df = pd.DataFrame(data)
            self.log(f"Measurement data for {device}:\n{df.to_string()}\n")


        end_time = datetime.now()
        self.log(f"\nExperiment ended at {end_time}")

     
        self.log_file.close()

    def log(self, message):
      
        print(message, file=self.log_file)
        print(message)

    