# Installation

Install SPCS-Instruments and Rex into isolated environments on the laboratory
computer. `uv` is the documented option, although another environment manager
can be used if it provides the same isolation.

```bash
uv tool install spcs-instruments
uv tool install rex-pycli
```

To update an existing installation, rerun the first command with `--force`.
For a branch or prerelease, install from its Git reference instead:

```bash
uv tool install --from git+https://github.com/JaminMartin/spcs_instruments.git@<tag-or-branch> spcs-instruments
```

Rex needs the Python interpreter that contains the device drivers. Run
`spcs_version` after installation and use its reported interpreter path in the
Rex configuration. You can then start an experiment from any directory:

```bash
rex run your_experiment.py
```

Use `rex run --help` for options such as output location, delay, repeats,
email notification, interactive mode, and an alternate configuration path.

## Platform notes

PyVISA instruments need a compatible VISA backend and any vendor drivers
required by the hardware. On Linux this commonly means National Instruments
VISA plus appropriate USB permissions. On Apple Silicon, NI-VISA support is
limited; pure serial/USB drivers can still work, but each VISA device should be
validated with its available backend. On Windows, install the matching
National Instruments VISA driver before connecting GPIB or USBTMC equipment.
