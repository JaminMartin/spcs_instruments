# Code to execute when the script is run directly
from spcs_instruments import Keithley2400
import os
import sys

if __name__ == "__main__":
    # Example usage
    dir_path = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(dir_path, "..", "templates", "config4.toml")
    keithley = Keithley2400(config_path)

    for i in range(1,11):
        keithley.measure()



    print(keithley.data)
    
    keithley.close()
