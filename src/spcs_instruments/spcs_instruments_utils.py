import toml
import socket
import json

def load_config(path: str) -> dict:
    with open(path, "r") as f:
        config_toml = toml.load(f)
    return config_toml



def pyfex_support(cls):
    
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

    def create_payload(self) -> dict:
        device_config = {key: value for key, value in self.config.items()}
        
        payload = {
            "device_name": self.name,
            "device_config": device_config,
            "measurements": self.data
        }
        
        return payload
    cls.create_payload = create_payload
    cls.tcp_connect = tcp_connect
    cls.tcp_send = tcp_send
    return cls
    
@pyfex_support    
class Experiment:
    def __init__(self, measurement_func, config_path):
        self.measurement_func = measurement_func
        self.config_path = config_path

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
        
        sock = self.tcp_connect()
        self.tcp_send(payload,sock)
        
        
        
