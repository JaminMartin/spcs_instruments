# SPCS - Instruments

A simple hardware abstraction layer for interfacing with instruments. This project aims to provide a deterministic measurement setup and robust tooling to ensure long term data integrity. 

# Philosophy
- All data acquisition devices provide a minimal set of public API's that have crossover such as a measure() function that returns counts, volts etc for all devices, this makes swapping between devices within the one GUI trivial. As each instrument may have multiple ways to implement various measurements these measurement routines can be specified internally and configured using a config file, This allows internal API's to function as the device requires them to, without having lots of what effectively becomes boilerplate code in your measurement scripts. 

- Instead of adding device-level control for the data acquisition device, these should be set in a `config.toml` file. This way, a GUI or measurement script remains simplified, and the acquisition parameters are abstracted away from them and can be set elsewhere specific to that device or if the device supports it, the device itself (which is often easier in my experience). It makes it easy to swap out these devices e.g. swapping a lock-in amplifier for a scope, or photon counter on the fly. Instead, the GUI can wait for the data from the specified device regardless of what it is.

- User independence: measurements based around a config file & a measurement script / GUI allow for specific configurations to be more deterministic. There are no issues around accidentally setting the wrong settings or recording the wrong parameters of your experiment as these are all taken care of by the library. Results record the final parameters for all connected devices allowing for experimental troubleshooting down the road. 

- Data integrity: Experimental setup/configuration data, user data, purpose and finally the experimental data are logged in a structured plain text format that is very human readable. Tools are also provided to easily read from these files for rapid data analysis. 
# The workflow
The idea is to produce abstracted scripts where the experiment class handles all the data logging from the resulting measurement and the `config.toml` file can be adjusted as required. 

```py
import spcs_instruments as spcs 

config = 'path/to/config.toml'
def a_measurement(config: str) -> dict:
    scope = spcs.SiglentSDS2352XE(config)
    daq = spcs.Fake_daq(config)
    for i in range(5):
            scope.measure()
            daq.measure()

    data = {
    scope.name: scope.data,
    daq.name: daq.data}
    return data


experiment = spcs.Experiment(a_measurement, config)
experiment.start()

```

Multiple instruments are also supported. To support multiple devices you just have to give them unique device names in the [config.toml](#setting-up-an-experimental-config-file) file, e.g. `[device.daq_1]` and `[device.daq_2]`. A name does not need to be provided given that the name in the config file matches the default name for the instrument. 

We just pass this name into the instrument initialisation.
```py
import spcs_instruments as spcs 

config = 'path/to/config.toml'
def a_measurement(config: str) -> dict:
    scope = spcs.SiglentSDS2352XE(config)
    daq1 = spcs.Fake_daq(config, name = "daq_1")
    daq2 = spcs.Fake_daq(config, name = "daq_2")

    for i in range(5):
            scope.measure()
            daq1.measure()
            daq2.measure()

    data = {
    scope.name: scope.data,
    daq1.name: daq1.data,
    daq2.name: daq2.data}
    return data


experiment = spcs.Experiment(a_measurement, config)
experiment.start()

```

# Build and install (For running experiments on a lab computer) 

## Initial setup
**Note** this is a WIP and will change to `rye install spcs_instruments` once this is made available on PyPI. For now, you can get rye to install directly from GitHub until the first stable release.
```
rye install spcs_instruments --git https://github.com/JaminMartin/spcs_instruments.git
```
This will install the `PyFeX` (Python experiment manager) CLI tool that runs your experiment file as a global system package. 
`PyFeX` in a nutshell an isolated python environment masquerading as a system tool. This allows you to write simple python scripts for your experiments. 

To run an experiment you can then just invoke 
```
pfx -p your_experiment.py 
```
Anywhere on the system. `PyFeX` has a few additional features. It can loop over an experiment `n` number of times as well as accept a delay until an experiment starts. It can also (currently only at UC) send an email with the experimental log files and in future experiment status if there has been an error. To see the full list of features and commands run 
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
As long as your experiment file has included spcs_instruments included, you should be good to go for running an experiment. 

## Setting up an experimental config file. 
The experimental config file allows your experiment to be deterministic. It keeps magic numbers out of your experimental python file (which effectively defines experimental flow control) and allows easy logging of setup parameters. This is invaluable when you wish to know what settings a certain experiment used. 

There are a few parameters that **must** be set, or the experiment won't run. These are name, email, experiment name and an experimental description
We define them like so in our `config.toml` file (though you can call it whatever you want)

```toml
[experiment.info]
name = "John Doe"
email = "test@canterbury.ac.nz"
experiment_name = "Test Experiment"
experiment_description = "This is a test experiment"
```
The key `experiment.info` is a bit like a nested dictionary. This will become more obvious as we add more things to the file. 

Next we add an instrument. 
```toml
[device.Test_DAQ]
gate_time = 1000
averages = 40
```
The name `Test_DAQ` is the name that our instrument also expects to be called, so when it reads from this file, it can find the setup parameters it needs.

In some cases, you might want to set explicit measurement types which has its own configuration. This is the case with an oscilloscope currently implemented in spcs_instruments. 
```toml 
[device.SIGLENT_Scope]
acquisition_mode = "AVERAGE"
averages = "64"


[device.SIGLENT_Scope.measure_mode]
reset_per = false
frequency = 0.5
```

The `measure_mode` is a sub dictionary. It contains information only pertaining to some aspects of a measurement. In this case, if the scope should reset per cycle or not (basically turning off or on a rolling average) as its acquisition mode is set to average. This allows the config file to be expressive and compartmentalised. 

The actual keys and values for a given instrument are given in the instruments' documentation (WIP)

For identical instruments you can give them different unique names, this just has to be reflected in how you call them in your `experiment.py` file. 

```toml
[device.Test_DAQ_1]
gate_time = 1000
averages = 40

[device.Test_DAQ_2]
gate_time = 500
averages = 78

```



This is all we need for our config file, we can change values here and maybe the description and run it with our experiment file, `PyFeX` will handle the logging of the data and the configuration. 


## Importing a valid instrument not yet included in spcs-instruments
If you have not yet made a pull request to include your instrument that implements the appropriate traits but still want to use it. This is quite simple! So long as it is using the same dependencies e.g. Pyvisa, PyUSB etc. **Note** Support for `Yaq` and `PyMeasure` instruments will be added in future. However, a thin API wrapper will need to be made to make it compliant with the expected data / control layout. These are not added as default dependencies as they have not yet been tested. 

Simply add a valid module path to your experiment file and then import the module like so;
```py
import sys
sys.path.append(os.path.expanduser("~/Path/To/Extra/Instruments/Folder/"))
import myinstruments

#and in your experiment function create your instrument
my_daq = myinstrument.a_new_instruemnt(config)

```
## Developing SPCS-Instruments

# Build and install for developing an experiment & instrument drivers  
SPCS-instruments is a hybrid Rust-Python project and as such development requires both tool chains to be installed for development. The combination of `Rustup` (for `Rust`), `Rye` for `Python` installation and `Maturin` for exposing `Rust` bindings to `Python` have been found to be ideal for such development. However, a system `Python` or `conda Python` is needed for some of the standalone `Rust` tests. 


## The Tools
Install the rust tool chain from (here) and `rye` if you dont already have it installed from (here). I also recommend installing `miniforge` (conda) from (here). 

With `rye`, we can install `maturin`, I also recommend installing `ruff`, `pytest` and `pyright` for linting, formatting and running tests.


For example:
```bash
rye install maturin 
```
This will make it globally available for development. 
## Using The Tools

Clone the repository locally and `cd` into it. Run `rye sync` to build a local virtual environment. This downloads and installs all the remaining project dependencies. You can also use `rye` to install the project (e.g. `PyFeX`) as a standalone tool, much like the installation for running on lab pc's. This can be used to emulate how it will be run by an end user. Just run `rye install .` or if on Windows, `rye install spcs-instruments --path .`. If it is already installed you may also need to pass an additional `-f` flag **Note this will overwrite any existing standalone spcs-instruments install**.

To use the virtual environment for development, activate it by running the appropriate shell script in the `.venv/bin/` directory.
From here we can use `pytest` to test any `Python` tests, and importantly `Maturin` to develop and build `PyFeX` within the local environment, not affecting a global installation. It also provides output from the `Rust` compiler for any compilation errors. 
To develop the complete package, run 
```shell
maturin develop
```
In the root of the project. This will then allow a local call to `PyFeX` 
```
(spcs-instruments) which pfx
/spcs_instruments/.venv/bin/pfx
```
From here, it is important to note which `PyFeX` you are running if you have also installed it globally, as changes in your code and subsequent builds with `Maturin` will not alter the globally installed version. 

From here, you can create new instruments in the `src/spcs_instruments/instruments/` folder and utilise the template instruments as a guide. It is also important to note, you will need to modify the `__init__.py` files in both `src/spcs_instruments` and `src/spcs_instruments/instruments` folders to re-export your instrument classes to where they are expected. 

e.g.
```py
from .instruments import Fake_daq
from .instruments import SiglentSDS2352XE
from .instruments import Keithley2400
from .spcs_instruments_utils import Experiment

__all__ = ["Fake_daq","SiglentSDS2352XE", "Experiment", "Keithley2400"]
```

### Rust Tests
If you are making alterations to the `Rust` code, there are some additional flags you will need to pass `cargo` in order for the tests to complete.

Many of the `Rust` functions are annotated with a `#[pyfunction]` allowing them to be called via python. However, for testing we would like to just test them using cargo, so we must use the `--no-default-features` flag. This will compile the library functions as if they are rust functions. Lastly we need to set the threads to `1` as many of the functions are not designed to interact simultaneously with the file system. 

```
cargo test --no-default-features -- --test-threads=1
```
You will also need a non-`rye` version of `Python` installed, e.g. from `conda`. This is because `pyo3` expects there to be a valid system `Python` (`rye` is not compliant with this), however `conda` seems to work. 

## Contributing an instrument to spcs-instruments

### Python Tests

If you are wanting to add an instrument to `spcs-instruments` currently there are only three core requirements that need to be met. 
- Your instrument class accepts a:
    - unique name (for multiple identical instruments)
    - config file (there are tools written to support this)
- It exposes a `measure()`, `set()` or `goto()` API call.
- *IF* using `measure()` data is both returned from that call, and appended to an internal data dictionary. See the example instruments for further details. 

It is highly recommended you write a test for this instrument in the test directory and run it along-side the standard test suite. Your instrument specific tests will not be tested in CI/CD pipelines, so it is important you mention you have run these tests before oppening a pull request. These tests are used for long term retention of how a piece of equipment is expected to work & to troubleshoot experiment workflows. 
 
# Linux Setup (Ubuntu 22.04 LTS x86)
Note, if you don't have root access this script will need to be modified and run as root. The USB permissions may need to be adjusted, this is what was found to work. 
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
sudo usermod -aG dialout $USER

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
As national instruments is not supported yet on Apple Silicon, none of the instruments that rely on national instruments will be usable. This does not prevent its use however, with any pure serial/USB devices being completely functional. If demand is there, instruments can try to run with a pure Python VISA implementation as an Apple Silicon fallback. This will involve building this into all instruments and does not assure compatibility, as I have experience devices not working at all with the pure Python implementation.

In such case, spcs-instruments can be installed as shown in the [build and install](#build-and-install-for-running-experiments-on-a-lab-computer). 

For Intel Macs, you can install National instruments drivers (for MacOS 12) [here](https://www.ni.com/en/support/downloads/drivers/download.ni-visa.html)
# Windows Setup (x86)
For Windows systems, simply install the appropriate Windows National Instruments driver from the following [link.](https://www.ni.com/en/support/downloads/drivers/download.ni-visa.html)
Once this is complete, install spcs-instruments as described in [build and install](#build-and-install-for-running-experiments-on-a-lab-computer).
