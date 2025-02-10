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



def pyfex_support(cls):
    instrument_init = cls.__init__

    @wraps(instrument_init)
    def extension_init(self, *args, **kwargs):
        self.init_time_s = time.time()
        instrument_init(self, *args, **kwargs)    


             
    def tcp_connect(self, host='127.0.0.1', port=8080):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        try:
      
            sock.connect((host, port))
            print(f"Connected to {host}:{port}")
            return sock
        except KeyboardInterrupt:
            print("\nStopping client...")
        except ConnectionRefusedError:
            print(f"Could not connect to server at {host}:{port}")
        except Exception as e:
            print(f"An error occurred: {e}")    
    
    def tcp_send(self, payload, sock):    
        data = json.dumps(payload) + '\n' 
        sock.sendall(data.encode())
        
       
        response = sock.recv(1024).decode()
        print(f"Server response: {response}")

    def find_key(self, target_key: str, current_dict: Dict[str, Any] = None) -> Any:
          """
          Recursively search for a key in the configuration dictionary,
          regardless of nesting level.
          """
          if current_dict is None:
                current_dict = self.config
        
            # Check current level
          if target_key in current_dict:
                return current_dict[target_key]
        
            # Search nested dictionaries
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
        
        return payload
    
    def bind_config(self, path: str) -> dict:
        overall_config = load_config(path)
        device_config = overall_config.get('device', {}).get(self.name, {})
        return device_config
    

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
        self.measurement_func = measurement_func
        self.config_path = config_path
        self.sock = self.tcp_connect()
    def start(self):
        self.send_exp()
        self.measurement_func(self.config_path)

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
        
class DeviceError(Exception):
    pass        
        
