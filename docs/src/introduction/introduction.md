# Introduction

SPCS-Instruments is a collection of Python device drivers designed to run with
the Rex experiment manager. Your experiment script owns the control flow; each
driver owns the connection and device-specific commands; Rex records the
measurements and experiment metadata.

The normal workflow is:

1. Define experiment metadata and device settings in a TOML file.
2. Instantiate drivers with that configuration path.
3. Call their `measure()` methods from the experiment function.
4. Start the session with `Experiment`; Rex receives and stores the resulting
   measurement payloads.

```python
import spcs_instruments as spcs


def acquire(config_path: str) -> None:
    daq = spcs.Test_daq(config_path)
    for _ in range(5):
        daq.measure()


experiment = spcs.Experiment(acquire, "config.toml")
experiment.start()
```

Use a unique device name when an experiment has more than one instance of the
same driver. The name passed to the constructor must match its section under
`[device]` in the configuration file. See the [configuration guide](../configuration.md).
