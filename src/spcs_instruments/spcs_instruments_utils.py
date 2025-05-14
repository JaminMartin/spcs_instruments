import toml
import socket
import json
import time
from functools import wraps
from typing import Any, Dict
def load_config(path: str) -> dict:
    with open(path, "r") as f:
        config_toml = toml.load(f)
    return config_toml
import os
import time
import logging
import polars as pl
import pandas as pd
import rex 

RUST_TO_PYTHON_LEVELS = {
    "ERROR": logging.ERROR,
    "WARN": logging.WARNING,
    "INFO": logging.INFO,
    "DEBUG": logging.DEBUG,
    "TRACE": logging.DEBUG  
}



def pyfex_support(cls):
    instrument_init = cls.__init__

    @wraps(instrument_init)
    def extension_init(self, *args, **kwargs):
        self.init_time_s = time.time()

        rust_level = os.environ.get("RUST_LOG_LEVEL")
        python_level = RUST_TO_PYTHON_LEVELS.get(rust_level)
        logging.basicConfig(
        level=python_level,
        format='%(message)s'
            )
        self.logger = logging.getLogger(f"pyfex.{cls.__name__}")
        instrument_init(self, *args, **kwargs)    


             
    def tcp_connect(self, host='127.0.0.1', port=7676):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        try:
      
            sock.connect((host, port))
            self.logger.debug(f"{self.name} connected to {host}:{port}")
            return sock
        except KeyboardInterrupt:
            self.logger.debug("Stopping client...")
        except ConnectionRefusedError:
            self.logger.error(f"Could not connect to server at {host}:{port}")
        except Exception as e:
            self.logger.error(f"An error occurred: {e}")    
    
    def tcp_send(self, payload, sock):    
        data = json.dumps(payload) + '\n' 
        sock.sendall(data.encode())
        
       
        response = sock.recv(1024).decode()
        self.logger.debug(f"Server response: {response}")
        return response

    def find_key(self, target_key: str, current_dict: Dict[str, Any] = None) -> Any:
          """
          Recursively search for a key in the configuration dictionary,
          regardless of nesting level.
          """
          if current_dict is None:
                current_dict = self.config
        
         
          if target_key in current_dict:
                return current_dict[target_key]
        
      
          for value in current_dict.values():
                if isinstance(value, dict):
                    try:
                        result = self.find_key(target_key, value)
                        if result is not None:  # Found in nested dict
                            return result
                    except ValueError:
                        continue
                
          raise ValueError(f"Missing required configuration key: {target_key}")
        
        
    def require_config(self, key: str) -> Any:
          """Get a required configuration value by searching for the key."""
          return self.find_key(key)
      
    def create_payload(self) -> dict:
        device_config = {key: value for key, value in self.config.items()}
        elapsed_time = time.time() - self.init_time_s
        self.data["time since initialisation (s)"] = [elapsed_time]
        
        payload = {
            "device_name": self.name,
            "device_config": device_config,
            "measurements": self.data
        }
        
        return self.adjust_payload(payload)
    
    def adjust_payload(self, payload: dict) -> dict:
        """
        For each measurement in the payload, if the measurement value is a list with
        more than one element and is not already double-wrapped, wrap it in an extra list.
        """
        measurements = payload.get("measurements", {})
        for key, value in measurements.items():
 
            if isinstance(value, list):
                
                if value and isinstance(value[0], list):
                    continue  # Already wrapped, do nothing

                
                if len(value) > 1:
                    measurements[key] = [value]
        payload["measurements"] = measurements
        return payload

    def bind_config(self, path: str) -> dict:
        overall_config = load_config(path)
        device_config = overall_config.get('device', {}).get(self.name, {})
        return device_config
    
    cls.adjust_payload = adjust_payload
    cls.bind_config = bind_config    
    cls.create_payload = create_payload
    cls.tcp_connect = tcp_connect
    cls.tcp_send = tcp_send
    cls.require_config = require_config
    cls.find_key = find_key

    cls.__init__ = extension_init
    return cls
    
@pyfex_support    
class Experiment:
    def __init__(self, measurement_func, config_path):
        self.name = "Experiment"
        self.measurement_func = measurement_func
        self.config_path = config_path
        self.sock = self.tcp_connect()

    def start(self):
        self.send_exp()
        try:
            self.measurement_func(self.config_path)
        except KeyboardInterrupt:
            self.logger.error("Experiment interrupted by user (Ctrl+C). Exiting safely.")
   

    def send_exp(self):
        self.conf = load_config(self.config_path)
        info_data = self.conf.get("experiment", {}).get("info", {})
        payload = {
            "info": {
                "name": info_data.get("name"),
                "email": info_data.get("email"),
                "experiment_name": info_data.get("experiment_name"),
                "experiment_description": info_data.get("experiment_description")
            }
        }
        
        
        self.tcp_send(payload,self.sock)


@pyfex_support    
class Listener:
    def __init__(self):
        self.name = "Experiment Listener"

        self.sock = self.tcp_connect()
        self.start()
    def start(self):
        self.send_exp()

    def send_exp(self):
        self.payload = {
                "name": "Experiment Listener",
                "id": "eaoifhja3por13",
        }
        
    def check_state(self) -> bool:

        response = self.tcp_send(self.payload,self.sock).strip()
        match response:
        
            case "Paused":
                while self.tcp_send(self.payload,self.sock).strip() == "Paused":
                    time.sleep(1)
   
            case "Running":
                  return                     

class DeviceError(Exception):
    pass        
        
def load_experimental_data(data_file: str, method: str) ->  pl.DataFrame | pd.DataFrame | dict:
    data_dict = rex.load_experimental_data(data_file) 
    match method:
        case "dict":
            return data_dict
        case "polars":
            return nested_dict_to_polars(data_dict)
        case "pandas":
            return nested_dict_to_pandas(data_dict)
        case _ :
            raise ValueError("Invalid Input, options are: 'polars', 'pandas', 'dict'")

def nested_dict_to_polars(data: dict) -> pl.DataFrame:
    df_list = [
        pl.DataFrame(measurements).select([
             pl.col(column_name).alias(f"{device_name}_{column_name}")
             for column_name in pl.DataFrame(measurements).columns]) 

         for device_name, measurements in data.items()
    ]
    return pl.concat(df_list, how="horizontal")

def nested_dict_to_pandas(data: dict) -> pd.DataFrame:
    dfs = []
    for device_name, measurements in data.items():
        df = pd.DataFrame(measurements)

        df = df.add_prefix(f"{device_name}_")
        dfs.append(df)

    combined_df = pd.concat(dfs, axis=1)
    return combined_df