# SPCS - Instruments

A simple hardware abstraction layer for interfacing with instruments using the [rex experiment manager](https://github.com/JaminMartin/rex). 

The general overview of SPCS-Instruments and how it works with `Rex`
```
    +-------------------------+                                                                                                       
    |                         |                                                                                                       
    |                         |                       +----------------------------------------------------+                          
    |Interactive TUI/Graphing |                       |              Python Virtual Environment(Venv)      |                          
    |                         |                       |                                                    |                          
    |                         |                       |                 +----------------+                 |                          
    |                         |                       |             +-- |SPCS-Instruments|-----+           |                          
    |                         |                       |             |   +----------------+     +-----------+-----------+              
    +---+---------------------+                       |             v                          |           |           |              
     ^  |                                             |  +-------------------------+           |           |           |              
     |  |                                             |  |        Rex (Rust)       |           |           |           |              
     |  | +-------------------------------------------+->| CLI interface           |           v           |           |              
     |  | |                                           |  |                         | Experiment Initialiser|           |              
     |  | |                     +--User Interaction---+--+ Interpreter manager     |           |           |           |              
     |  | |                     |                     |  |                         |           |           |           |              
     |  | |                     |                     |  | Thread pool management  |           |           |           |              
     |  | |                     |                     |  |                         |           v           |           |              
     |  | |                     v                     |  | TCP server              | Python Device Drivers |           |              
     |  v |               +------------+              |  |                         |           |           |           |              
+----+----+-------+       |            |<------+      |  | Mailer                  |           |           |           |              
|                 |<------| TCP Server |       |      |  |                         |           |           |           |              
|Triaged logging          |            +---+   |      |  | Loops/Delays            |           v           | Library imports from Venv
|                 |------>|            |   |   |      |  +------------------------++  VISA/USB Libraries   |           |              
+--------+--------+       +------------+   |   |      |                           |                        |           |              
    ^    |   ^                             |   |      +---------------------------+------------------------+           |              
    |    |   |                             |   |                                  |                                    |              
    |    |   |                             |   |                                  |                                    |              
    |    |   |                             |   |                                  |                                    |              
    |    v   |                             |   |                                  v                                    |              
    |  +-----+------------+                |   |                                +--------------------------+           |              
    |  | Data Validation  |                |   +--------------------------------+  Python experiment file  |           |              
    |  |                  |                |    Real Time data exchange         |                          |           |              
    |  +-----------+------+                +----------------------------------->|  - Control flow          |           |              
    |              |                  +----------------------------+            |                          |           |              
    |              |                  |                            |            |  - Device initialisation |<----------+              
    |              v                  |     User Config File       +----------->|                          |                          
    |  +------------------+           | - Device configuration     |            |  - Relays experiment info|                          
    |  |      Storage     |           |                            |            |                          |                          
    +--+                  |           | - Experiment information   |            |                          |                          
       +------------------+           |                            |            |                          |                          
                                      +----------------------------+            +--------------------------+                         
```


# Build and install (For running experiments on a lab computer) 

## Initial setup

It is highly recomended to install `spcs-instruments` & `rex` with a dedicated python environment manager such as, `uv`, `pixi` or `pipx` this ensures a complete set of isolated depedencies for reliable usage in a multi-user lab environment. In these examples we will use `uv` as it is a tool I use personally. 


```
uv tool install spcs_instruments 
```

If you are wanting to update to a newer version of `spcs-instruments` add a `-f` to the above to force install the latest version. 
```
uv tool install spcs_instruments -f 
```
If you prefer to run a bleeding edge release e.g. alpha or beta releases, you can do this with the following command:
```
uv tool install --from git+https://github.com/JaminMartin/spcs_instruments.git@v0.7.3-alpha.1 spcs_instruments
```
Where after the @ you can provide either a tag or branch. . 
You can find the specific latest tagged release [here](https://github.com/JaminMartin/spcs_instruments/tags). 

This will install the `spcs-instruments` python device drivers

Next we need to install `Rex`, again with a simple `uv tool install rex-pycli`, this give you the tool that runs your experiment file as a global system package. See the [rex documentation](https://github.com/JaminMartin/rex) for how to configure rex explicitly. But for a simple usecase we just need to setup the path to the python interpreter for spcs-instruments.
`Rex` in a nutshell an utilises the isolated python environment provided by the spcs-instruments in this case to call the python drivers and log data, all without *you* having to setup python virtial environments on what is likely a shared system. To simplify the setup, `spcs-instruments` can export the interpreter path `rex` needs by running `spcs_version` in your terminal after installation. Copy this path into your `rex` config.

To run an experiment you can then just invoke 
```
rex run -p your_experiment.py 
```
Anywhere on the system. `Rex` has a few additional features. It can loop over an experiment `n` number of times as well as accept a delay until an experiment starts. It can also) send an email with the experimental log files and in future experiment status if there has been an error. To see the full list of features and commands run 
```
rex --help
```
which lists the full command set
```
A commandline experiment manager

Usage: rex [OPTIONS] --path <PATH>

Options:
  -v, --verbosity <VERBOSITY>  desired log level, info displays summary of connected instruments & recent data. debug will include all data, including standard output from Python [default: 2]
  -e, --email <EMAIL>          Email address to receive results
  -d, --delay <DELAY>          Time delay in minutes before starting the experiment [default: 0]
  -l, --loops <LOOPS>          Number of times to loop the experiment [default: 1]
  -p, --path <PATH>            Path to the python file containing the experimental setup
  -o, --output <OUTPUT>        Target directory for output path [default: "/home/jamin/Documents/spcs instruments"]
  -i, --interactive            Enable interactive TUI mode
  -h, --help                   Print help
  -V, --version                Print version
```
As long as your experiment file has spcs_instruments included, you should be good to go for running an experiment. 


#### Interactive mode:
If you pass the flag `-i` or `--interactive` you will get a live stream of all your data sources, allowing you to render your real time data however you like. To access the menu to get a list of the controls, simply press the `m` key.


#### Remote interactive mode:

The installation of `rex` also includes the `rex view` command, this is an identical TUI for remote monitoring / interaction with a currently running `rex` instance. You can also remotely terminate, pause or resume an experiment. 
`rex view` can be used by simply using the following command, where the address is the internal IP address of the device currently running the experiment.

```
rex view -a 127.0.0.1:7676 -backened tcp #http is in the works!
```

For a full (and likely more up to date) list of `rex`'s features do check out its [dedicated documentation](https://github.com/JaminMartin/rex)
# The workflow - Lets get experimenting
The idea is to produce abstracted scripts where `rex` handles all the data logging from the resulting measurement and the `config.toml` file can be adjusted as required. This keeps storage, control flow and configuration compartmentalised. 

```py
import spcs_instruments as spcs 

config = 'path/to/config.toml'
def a_measurement(config: str) -> dict:
    scope = spcs.SiglentSDS2352XE(config)
    daq = spcs.Fake_daq(config)
    for i in range(5):
            scope.measure()
            daq.measure()


    return 


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

    return


experiment = spcs.Experiment(a_measurement, config)
experiment.start()

```
## Setting up an experimental config file. 
**Note!!!** the configuration parameters for a given instrument can be found [here](https://jaminmartin.github.io/spcs_instruments/) or in the source code of this project. These docs are a work in progress.
The experimental config file allows your experiment to be deterministic. It keeps magic numbers out of your experimental `Python` file (which effectively defines experimental flow control) and allows easy logging of setup parameters. This is invaluable when you wish to know what settings a certain experiment used. 

There are a few parameters that **must** be set, or the experiment won't run. These are name, email, experiment name and an experimental description.
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

In some cases, you might want to set explicit measurement types which have its own configuration. This is the case with an oscilloscope currently implemented in spcs_instruments. 
```toml 
[device.SIGLENT_Scope]
acquisition_mode = "AVERAGE"
averages = "64"


[device.SIGLENT_Scope.measure_mode]
reset_per = false
frequency = 0.5
```

The `measure_mode` is a sub-dictionary. It contains information only pertaining to some aspects of a measurement. In this case, if the scope should reset per cycle or not (basically turning off or on a rolling average) as its acquisition mode is set to average. This allows the config file to be expressive and compartmentalised. 

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



This is all we need for our config file, we can change values here and maybe the description and run it with our experiment file, `Rex` will handle the logging of the data and the configuration. 
**Note** `rex` can pass in a config directly to the experiemnt file through a commandline flag `-c` this avoids having to change the config path within your python file allowing you to define a single "control flow" and provide it different pre-configured config files. 

## Importing a valid instrument not yet included in spcs-instruments
If you have not yet made a pull request to include your instrument that implements the appropriate traits but still want to use it. This is quite simple! So long as it is using the same dependencies e.g. Pyvisa, PyUSB etc. **Note** Support for `Yaq` and `PyMeasure` instruments will be added in future. However, a thin API wrapper will need to be made to make it compliant with the expected data/control layout. These are not added as default dependencies as they have not yet been tested. 

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
SPCS-instruments is a hybrid Rust-Python project and as such development requires both tool chains to be installed for development. The combination of `Rustup` (for `Rust`), `UV` for `Python` installation and `Maturin` for exposing `Rust` bindings to `Python` have been found to be ideal for such development. However, a system `Python` or `conda Python` is needed for some of the standalone `Rust` tests. 

*NOTE* as of v0.9.0, rust is not strictly required to be installed. Rex is a standalone rust package with python bindings. If you need to contribue to `rex` you will need the rust tool chian installed.


## The Tools
`uv` if you don't already have it installed from [here](https://docs.astral.sh/uv/getting-started/installation/). 

With `uv`, I also recommend installing `ruff`, `pytest` and `pyright` for linting, formatting and running tests.


For example:
```bash
uv tool install ruff 
```
This will make it globally available for development. 
## Using The Tools

Clone the repository locally and `cd` into it. Run `uv sync` to build a local virtual environment. This downloads and installs all the remaining project dependencies. You can also use `uv` to install the project (e.g. `spcs-instruments`) as a standalone tool, much like the installation for running on lab pc's. This can be used to emulate how it will be run by an end user. Just run `uv tool install .` or if on Windows, `uv install spcs-instruments --path .`. If it is already installed you may also need to pass an additional `-f` flag **Note this will overwrite any existing standalone spcs-instruments install**.

To use the virtual environment for development, activate it by running the appropriate shell script in the `.venv/bin/` directory.
From here we can use `pytest` to test any `Python` tests, and importantly it provides `spcs-instruements` as editable within the local environment, not affecting a global installation. 

From here, you can create new instruments in the `src/spcs_instruments/instruments/` folder and utilise the template instruments as a guide. It is also important to note, you will need to modify the `__init__.py` files in both `src/spcs_instruments` and `src/spcs_instruments/instruments` folders to re-export your instrument classes to where they are expected. 

e.g.
```py
from .instruments import Fake_daq
from .instruments import SiglentSDS2352XE
from .instruments import Keithley2400
from .spcs_instruments_utils import Experiment

__all__ = ["Fake_daq","SiglentSDS2352XE", "Experiment", "Keithley2400"]
```

If you are wanting to add an instrument to `spcs-instruments` currently there are only three core requirements that need to be met. 
- Your instrument class accepts a:
    - unique name (for multiple identical instruments)
    - config file (there are tools written to support this)
- It exposes a `measure()`, `set()` or `goto()` API call.
- *IF* using `measure()` data is both returned from that call and appended to an internal data dictionary. See the example instruments for further details. 

It is highly recommended you write a test for this instrument in the test directory and run it alongside the standard test suite. Your instrument-specific tests will not be tested in CI/CD pipelines, so it is important you mention you have run these tests before opening a pull request. These tests are used for long-term retention of how a piece of equipment is expected to work & to troubleshoot experiment workflows. 
 
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

# Install any dependencies

curl -LsSf https://astral.sh/uv/install.sh | sh

sudo reboot
```

# MacOS Setup (ARM)
As national instruments VISA is not supported yet on Apple Silicon, none of the instruments that rely on national instruments will be usable. This does not prevent its use, however, with any pure serial/USB devices being completely functional. If demand is there, instruments can try to run with a pure Python VISA implementation as an Apple Silicon fallback. This will involve building this into all instruments and does not assure compatibility, as I have experienced devices not working at all with the pure Python implementation.

In such case, spcs-instruments can be installed as shown in the [build and install](#build-and-install-for-running-experiments-on-a-lab-computer). 

For Intel Macs, you can install National instruments drivers (for MacOS 12) [here](https://www.ni.com/en/support/downloads/drivers/download.ni-visa.html)
# Windows Setup (x86)
For Windows systems, simply install the appropriate Windows National Instruments driver from the following [link.](https://www.ni.com/en/support/downloads/drivers/download.ni-visa.html)
Once this is complete, install spcs-instruments as described in [build and install](#build-and-install-for-running-experiments-on-a-lab-computer).
