# Instruments

Each driver accepts a configuration path and, optionally, a device name. A
driver's `measure()` method returns its latest `Measurement` values and sends
them to Rex when connected to a running session.

The current collection includes cryostat and temperature controllers,
oscilloscopes, spectrometers, a dye laser, source-measure equipment, a photon
counter, and an SPCS mixed-signal switch box. Use the entries in the sidebar
for each driver's connection requirements, configuration keys, and control
methods.

For instrument communication, install the driver-specific dependencies and
vendor software needed by the hardware. In particular, PyVISA-backed devices
need an accessible VISA resource; USB-only drivers may have their own backend.
