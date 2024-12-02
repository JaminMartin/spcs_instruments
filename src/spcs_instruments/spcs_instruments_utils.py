import toml
import socket
import json

def load_config(path: str) -> dict:
    with open(path, "r") as f:
        config_toml = toml.load(f)
    return config_toml

def tcp_connect(host='127.0.0.1', port=8080):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    try:
        # Connect to the server
        sock.connect((host, port))
        print(f"Connected to {host}:{port}")
        return sock
    except KeyboardInterrupt:
        print("\nStopping client...")
    except ConnectionRefusedError:
        print(f"Could not connect to server at {host}:{port}")
    except Exception as e:
        print(f"An error occurred: {e}")    
    
def tcp_send(payload, sock):    
    data = json.dumps(payload) + '\n' 
    sock.sendall(data.encode())
    
    # Receive acknowledgment
    response = sock.recv(1024).decode()
    print(f"Server response: {response}")
    
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
        
        sock = tcp_connect()
        tcp_send(payload,sock)
        
        
        
