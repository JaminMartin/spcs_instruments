"""Rex integration for a Stanford Research Systems SR830 lock-in amplifier."""

from __future__ import annotations

import time
from typing import Any

from qcodes.instrument_drivers.stanford_research import SR830
from rex_utils import Measurement, RexSupport


class SR830Lockin(RexSupport):
    """Configure and acquire coherent SR830 readings through QCoDeS.

    Configuration is applied once during construction. ``measure`` only reads
    the lock-in, so an experiment can control settling explicitly after a
    reference, frequency, sensitivity, or time-constant change.
    """

    __toml_config__ = {
        "device.SR830Lockin": {
            "_section_description": "Stanford Research Systems SR830 lock-in configuration",
            "visa_resource": {
                "_value": "GPIB0::8::INSTR",
                "_description": "PyVISA resource for the SR830",
            },
            "timeout_seconds": {
                "_value": 2.0,
                "_description": "PyVISA communication timeout in seconds",
            },
            "reference_source": {
                "_value": "external",
                "_description": "Reference source: external or internal",
            },
            "phase_deg": {"_value": 0.0, "_description": "Reference phase in degrees"},
            "harmonic": {"_value": 1, "_description": "Detection harmonic"},
            "input_config": {
                "_value": "a",
                "_description": "Input configuration: a, a-b, I 1M, or I 100M",
            },
            "input_shield": {
                "_value": "ground",
                "_description": "Input shield: float or ground",
            },
            "input_coupling": {
                "_value": "AC",
                "_description": "Input coupling: AC or DC",
            },
            "notch_filter": {
                "_value": "both",
                "_description": "Line-notch filtering: off, line in, 2x line in, or both",
            },
            "sensitivity_v": {
                "_value": 0.001,
                "_description": "Sensitivity in volts for voltage inputs",
            },
            "reserve": {
                "_value": "normal",
                "_description": "Dynamic reserve: high, normal, or low noise",
            },
            "time_constant_s": {
                "_value": 0.3,
                "_description": "Output-filter time constant in seconds",
            },
            "filter_slope_db_per_octave": {
                "_value": 24,
                "_description": "Output-filter slope: 6, 12, 18, or 24 dB/octave",
            },
            "sync_filter": {
                "_value": "on",
                "_description": "Synchronous filter: on or off",
            },
            "settle_time_constants": {
                "_value": 5,
                "_description": "Number of time constants waited by wait_for_settle",
            },
            "record_aux_inputs": {
                "_value": False,
                "_description": "Record auxiliary input voltages 1 through 4",
            },
        }
    }

    def __init__(
        self, config: str, name: str = "SR830Lockin", connect_to_rex: bool = True
    ) -> None:
        self.connect_to_rex = connect_to_rex
        super().__init__(name=name)
        self.bind_config(config)

        timeout_seconds = float(self.require_config("timeout_seconds"))
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than zero")
        self.instrument = SR830(
            name=f"{name}_instrument",
            address=self.require_config("visa_resource"),
            timeout=timeout_seconds,
        )
        self.record_aux_inputs = bool(self.require_config("record_aux_inputs"))
        self.settle_time_constants = float(
            self.require_config("settle_time_constants")
        )
        if self.settle_time_constants < 0:
            raise ValueError("settle_time_constants must not be negative")
        self.configure()

        self.measurements = {
            "X (V)": Measurement(data=[], unit="V"),
            "Y (V)": Measurement(data=[], unit="V"),
            "R (V)": Measurement(data=[], unit="V"),
            "phase (deg)": Measurement(data=[], unit="deg"),
        }
        if self.record_aux_inputs:
            self.measurements.update(
                {
                    f"auxiliary input {channel} (V)": Measurement(data=[], unit="V")
                    for channel in range(1, 5)
                }
            )
        if self.connect_to_rex:
            self.sock = self.tcp_connect()

    def configure(self) -> None:
        """Apply the configured reference, input, and filter settings once."""
        settings: dict[str, Any] = {
            "reference_source": self.require_config("reference_source"),
            "phase": float(self.require_config("phase_deg")),
            "harmonic": int(self.require_config("harmonic")),
            "input_config": self.require_config("input_config"),
            "input_shield": self.require_config("input_shield"),
            "input_coupling": self.require_config("input_coupling"),
            "notch_filter": self.require_config("notch_filter"),
            "sensitivity": float(self.require_config("sensitivity_v")),
            "reserve": self.require_config("reserve"),
            "time_constant": float(self.require_config("time_constant_s")),
            "filter_slope": int(self.require_config("filter_slope_db_per_octave")),
            "sync_filter": self.require_config("sync_filter"),
        }
        if settings["reference_source"] == "internal":
            settings["frequency"] = float(self.require_config("frequency_hz"))
            settings["amplitude"] = float(self.require_config("amplitude_v"))
        for parameter, value in settings.items():
            getattr(self.instrument, parameter)(value)

    def set_frequency(self, frequency_hz: float) -> None:
        """Set the internal reference frequency in hertz."""
        self.instrument.frequency(float(frequency_hz))

    def set_phase(self, phase_deg: float) -> None:
        """Set the demodulation phase in degrees."""
        self.instrument.phase(float(phase_deg))

    def set_sensitivity(self, sensitivity_v: float) -> None:
        """Set voltage-input sensitivity using an SR830-supported range."""
        self.instrument.sensitivity(float(sensitivity_v))

    def set_time_constant(self, time_constant_s: float) -> None:
        """Set the output-filter time constant using an SR830-supported value."""
        self.instrument.time_constant(float(time_constant_s))

    def auto_phase(self) -> None:
        """Run the SR830 automatic phase adjustment."""
        self.instrument.auto_phase()

    def auto_gain(self) -> None:
        """Run the SR830 automatic gain adjustment."""
        self.instrument.auto_gain()

    def auto_reserve(self) -> None:
        """Run the SR830 automatic reserve adjustment."""
        self.instrument.auto_reserve()

    def wait_for_settle(self, time_constants: float | None = None) -> None:
        """Wait a multiple of the current output-filter time constant."""
        multiplier = self.settle_time_constants if time_constants is None else float(time_constants)
        if multiplier < 0:
            raise ValueError("time_constants must not be negative")
        time.sleep(multiplier * float(self.instrument.time_constant()))

    def measure(self) -> dict[str, Measurement]:
        """Read a coherent X/Y/R/phase snapshot and optionally auxiliary inputs."""
        x, y, r, phase = self.instrument.snap("x", "y", "r", "phase")
        values = {"X (V)": x, "Y (V)": y, "R (V)": r, "phase (deg)": phase}
        if self.record_aux_inputs:
            auxiliary_inputs = self.instrument.snap("aux1", "aux2", "aux3", "aux4")
            values.update(
                {
                    f"auxiliary input {channel} (V)": value
                    for channel, value in enumerate(auxiliary_inputs, start=1)
                }
            )
        for key, value in values.items():
            self.measurements[key] = Measurement(data=[float(value)], unit=self.measurements[key].unit)
        if self.connect_to_rex:
            self.tcp_send(self.create_payload(), self.sock)
        return self.measurements

    def close(self) -> None:
        """Close QCoDeS' managed PyVISA connection."""
        instrument = getattr(self, "instrument", None)
        if instrument is not None:
            instrument.close()
