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
# Build and install (For running experiments on a lab computer) 

## Initial setup
**Note** this is a WIP and will change to `rye install spcs_instruments` once this is made avaiable on PyPi. For now just the source code.
```
git clone https://github.com/JaminMartin/spcs_instruments.git
cd spcs_instruments
rye install .
```
This will install the `PyFeX` (Python experiment manager) cli tool that runs your experiment file as a global system package. 
To run an experiment you can then just invoke 
```
pfx -p your_experiment.py 
```
anywhere on the system. `PyFex` as a few addittional features. It can loop over an an experiment `n` number of times as well as accept a delay until an experiment starts. It can also (currently only at UC) send an email with the experimental log files and in future exeperiment status if there has been an error. To see the full list of features and commands run 
```
pfx --help
```
which lists the full command set
```
A commandline experiment manager for SPCS-Instruments

Usage: pfx [OPTIONS] --path <PATH>

Options:
  -e, --email <EMAIL>    Email address to recieve results
  -d, --delay <DELAY>    Time delay in minutes before starting the experiment [default: 0]
  -l, --loops <LOOPS>    [default: 1]
  -p, --path <PATH>      
  -o, --output <OUTPUT>  [default: /Users/"user_name"]
  -h, --help             Print help
  -V, --version          Print version
  
```

# Build and install for developing an experiment & instrument drivers  
**(WIP)**
## Importing a valid instrument not yet included in spcs-instruments
If you have not yet made a pull request to include your instrument that implements the appropriate traits but still want to use it. This is quite simple! So long as it is using the same dependencies e.g. Pyvisa, PyUSB etc. **Note** Support for `Yaq` and `PyMeasure` instruments will be added in future. However a thin API wrapper will need to be made to make it compliant with the expected data / control layout. These are not added as default dependencies as they have not yet been tested. 

Simply add a valid module path to your experiment file and then import the module like so;
```py
import sys
sys.path.append(os.path.expanduser("~/Path/To/Extra/Instruments/Folder/"))
import myinstruments

#and in your experiment function create your instrument
my_daq = myinstrument.a_new_instruemnt(config)

```
## Developing SPCS-Instruments

### Rust Tests
If you are making alterations to the rust code, there are some some additional flags you will need to pass cargo in order for the tests to complete.

Many of the `Rust` functions are annotated with a `#[pyfunction]` allowing them to be called via python. However for testing we would like to just test them using cargo, so we must use the `--no-default-features` flag. This will compile the library functions as if they are rust functions. Lastly we need to set the threads to `1` as many of the functions are not designed to interact simultaneously with the file system. 

```
cargo test --no-default-features -- --test-threads=1
```

## Contributing an instrument to spcs-instruments

### Python Tests

# Linux Setup (Ubuntu 22.04 LTS x86)

```
sudo apt update
sudo apt upgrade
sudo apt install libusb-1.0-0-dev
# You will need to create a National Instruments account to download the .deb file first!
sudo apt install ./ni-ubuntu2204-drivers-2024Q1.deb #or latest version for your version of Linux
 
sudo apt update
  

sudo apt install ni-visa
sudo apt install ni-hwcfg-utility
sudo dkms autoinstall
sudo su
echo 'SUBSYSTEM=="usb", MODE="0666", GROUP="usbusers"' >> /etc/udev/rules.d/99-com.rules
rmmod usbtmc
echo 'blacklist usbtmc' > /etc/modprobe.d/nousbtmc.conf

# Install any dependencies (for rust & rye accept the defaults)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
curl -sSf https://rye.astral.sh/get | bash
echo 'source "$HOME/.rye/env"' >> ~/.bashrc
sudo reboot
```

# MacOS Setup (ARM)
**(WIP)**
# Windows Setup (x86)
**(WIP)**
