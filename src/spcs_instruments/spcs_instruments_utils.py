from time import sleep
import time
import datetime
import os
import toml
import json
import numpy as np
from datetime import datetime




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
 
        self.log_file = open(f"log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.spcs", "w")

 
        start_time = datetime.now()
        self.log(f"Experiment started at {start_time}")

   
        config = load_config(self.config_path)
        self.log(f"Config contents:\n{config}")


        measurement_data = self.measurement_func(self.config_path)

        for device, data in measurement_data.items():
            self.log(f"Measurement data for {device}:\n{data}")


        end_time = datetime.now()
        self.log(f"Experiment ended at {end_time}")

     
        self.log_file.close()

    def log(self, message):
        # Write the message to the log file and print it
        print(message, file=self.log_file)
        print(message)

