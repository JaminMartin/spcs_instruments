# SPCS - Instruments

A simple hardware abstraction layer for interfacing with instruments. This project aims to provide a deterministic measurement setup.

# Philosophy
- All data acquisition devices provide a minimal set of public API's that have crossover such as a measure() function that returns counts, volts etc for all devices, this makes swapping between devices within the one GUI trivial. As each instrument may have multiple ways to implement various measurements these measurement routines can be specified internally and configured using a config file, This allows internal API's to function as the device requires them to, without having lots of what effectively becomes boilerplate code in your measurement scripts. 

- Instead of adding device-level control for the data acquisition device, these should be set in a `config.toml` file. This way, a GUI or measurement script remains simplified, and the acquisition parameters are abstracted away from them and can be set elsewhere specific to that device or if the device supports it, the device itself (which is often easier in my experience). It makes it easy to swap out these devices e.g. swapping a lock-in amplifier for a scope, or photon counter on the fly. Instead, the GUI can wait for the data from the specified device regardless of what it is.

User independence: measurements based around a config file & a measurement script / GUI allow for specific configurations to be more deterministic. There are no issues around accidentally setting the wrong settings or recording the wrong parameters of your experiment as these are all taken care of by the library. Results record the final parameters for all connected devices allowing for experimental troubleshooting down the road. 

# The workflow
The idea is to produce abstracted scripts where the experiment class handles all the data logging from the resulting measurement and the `config.toml` file can be adjusted as required. 
```py
import spcs_instruments as spcs 

config = 'path/to/config.toml'
def a_measurement(config) -> dict:
    daq = spcs.SiglentSDS2352XE(config)
    daq2 = spcs.Fake_daq(config)
    for i in range(5):
            daq.measure()
            daq2.measure()

    data = {
    daq.name: daq.data,
    daq2.name: daq2.data}
    return data


experiment = spcs.Experiment(a_measurement, config)
experiment.start()

```

# Linux install (Ubuntu 22.04 LTS)
```
sudo apt update
sudo apt upgrade
sudo apt install libusb-1.0-0-dev

sudo apt install ./ni-ubuntu2204-drivers-2024Q1.deb #or latest version for your version of Linux
 
sudo apt update
  

sudo apt install ni-visa
sudo apt install ni-hwcfg-utility
sudo dkms autoinstall
sudo su
echo 'SUBSYSTEM=="usb", MODE="0666", GROUP="usbusers"' >> /etc/udev/rules.d/99-com.rules
rmmod usbtmc
echo 'blacklist usbtmc' > /etc/modprobe.d/nousbtmc.conf
sudo reboot

# Prepare the python environment 
sudo apt install curl
sudo apt install git
sudo apt install pipx
pipx ensurepath
pipx install poetry
poetry config virtualenvs.create false
poetry config virtualenvs.prefer-active-python true



curl -L -O "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-$(uname)-$(uname -m).sh"
bash Miniforge3-$(uname)-$(uname -m).sh

git clone https://github.com/JaminMartin/spcs_instruments.git
```

# Build and install 
cd into spcs_instruments
```
conda env create --name spcs_infra --file=environments.yml 
poetry install
```

# Test with a real device
plug in a spcs test device e.g. SDS2352XE osciliscope 
cd into tests and run pytest 

```
pytest test.py
```

if this passes, your instruments are ready to go!
