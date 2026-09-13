"""Rex integration for a Lake Shore Model 325 temperature controller."""

from __future__ import annotations

from collections import deque
import time

from qcodes.instrument_drivers.Lakeshore import LakeshoreModel325
from rex_utils import Measurement, RexSupport


class Lakeshore325(RexSupport):
    """Control and acquire measurements from a Lake Shore Model 325."""

    __toml_config__ = {
        "device.Lakeshore325": {
            "_section_description": "Lake Shore Model 325 configuration",
            "visa_resource": {
                "_value": "ASRL/dev/tty.usbserial::INSTR",
                "_description": "PyVISA resource for the Model 325 RS-232 or GPIB connection",
            },
            "input_channel": {
                "_value": "A",
                "_description": "Temperature input to record: A or B",
            },
            "control_loop": {
                "_value": 1,
                "_description": "Control loop used for setpoint and heater-output operations: 1 or 2",
            },
            "timeout_seconds": {
                "_value": 2.0,
                "_description": "PyVISA communication timeout in seconds",
            },
            "setpoint_tolerance_k": {
                "_value": 0.1,
                "_description": "Maximum selected-input error from the control-loop setpoint in kelvin",
            },
            "stability_tolerance_k": {
                "_value": 0.1,
                "_description": "Maximum temperature span across the stability sample window in kelvin",
            },
            "stability_readings": {
                "_value": 3,
                "_description": "Number of time-spaced temperature readings in the stability window",
            },
            "stability_sample_interval_s": {
                "_value": 1.0,
                "_description": "Minimum seconds between stability-window temperature readings",
            },
        }
    }

    def __init__(
        self,
        config: str,
        name: str = "Lakeshore325",
        connect_to_rex: bool = True,
    ) -> None:
        self.connect_to_rex = connect_to_rex
        super().__init__(name=name)
        self.bind_config(config)

        self.input_channel = self._validate_input_channel(
            self.require_config("input_channel")
        )
        self.control_loop = self._validate_control_loop(
            self.require_config("control_loop")
        )
        timeout_seconds = float(self.require_config("timeout_seconds"))
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than zero")
        self.setpoint_tolerance_k = float(
            self.config.get("setpoint_tolerance_k", 0.1)
        )
        self.stability_tolerance_k = float(
            self.config.get("stability_tolerance_k", 0.1)
        )
        self.stability_readings = int(self.config.get("stability_readings", 3))
        self.stability_sample_interval_s = float(
            self.config.get("stability_sample_interval_s", 1.0)
        )
        self._validate_stability_settings()
        self._stability_samples: deque[tuple[float, float]] = deque(
            maxlen=self.stability_readings
        )

        self.instrument = LakeshoreModel325(
            name=f"{name}_instrument",
            address=self.require_config("visa_resource"),
            timeout=timeout_seconds,
        )

        self.temperature_target = self.get_setpoint()
        self.measurements = {
            "temperature (K)": Measurement(data=[], unit="K"),
            "setpoint (K)": Measurement(data=[], unit="K"),
            "heater output (%)": Measurement(data=[], unit="%"),
        }
        if self.connect_to_rex:
            self.sock = self.tcp_connect()

        self.logger.debug("%s connected with config %s", self.name, self.config)

    @staticmethod
    def _validate_input_channel(channel: str) -> str:
        channel = str(channel).upper()
        if channel not in {"A", "B"}:
            raise ValueError("input_channel must be 'A' or 'B'")
        return channel

    @staticmethod
    def _validate_control_loop(control_loop: int) -> int:
        control_loop = int(control_loop)
        if control_loop not in {1, 2}:
            raise ValueError("control_loop must be 1 or 2")
        return control_loop

    def _validate_stability_settings(self) -> None:
        if self.setpoint_tolerance_k < 0:
            raise ValueError("setpoint_tolerance_k must not be negative")
        if self.stability_tolerance_k < 0:
            raise ValueError("stability_tolerance_k must not be negative")
        if self.stability_readings < 2:
            raise ValueError("stability_readings must be at least two")
        if self.stability_sample_interval_s < 0:
            raise ValueError("stability_sample_interval_s must not be negative")

    def _record_stability_sample(self, temperature: float) -> None:
        timestamp = time.monotonic()
        if (
            not self._stability_samples
            or timestamp - self._stability_samples[-1][0]
            >= self.stability_sample_interval_s
        ):
            self._stability_samples.append((timestamp, temperature))

    def get_temperature(self, input_channel: str | None = None) -> float:
        """Return the temperature in kelvin from input ``A`` or ``B``."""
        channel = self._validate_input_channel(input_channel if input_channel is not None else self.input_channel)
        return float(getattr(self.instrument, f"sensor_{channel}").temperature())

    def get_setpoint(self, control_loop: int | None = None) -> float:
        """Return the configured control-loop setpoint in kelvin."""
        loop = self._validate_control_loop(control_loop or self.control_loop)
        return float(getattr(self.instrument, f"heater_{loop}").setpoint())

    def go_to_temperature(
        self, temperature: float, control_loop: int | None = None
    ) -> None:
        """Set a control-loop temperature setpoint in kelvin."""
        loop = self._validate_control_loop(control_loop or self.control_loop)
        temperature = float(temperature)
        getattr(self.instrument, f"heater_{loop}").setpoint(temperature)
        if loop == self.control_loop:
            self.temperature_target = temperature
            self._stability_samples.clear()

    def set_heater_range(self, heater_range: int) -> None:
        """Set the selected loop's heater range (zero turns that heater off)."""
        getattr(self.instrument, f"heater_{self.control_loop}").output_range(
            int(heater_range)
        )

    def get_heater_output(self) -> float:
        """Return the selected loop's current heater output as a percentage."""
        return float(
            getattr(self.instrument, f"heater_{self.control_loop}").heater_output()
        )

    def is_temperature_stable(self, tolerance: float | None = None) -> bool:
        """Return whether the temperature stability window is within tolerance."""
        tolerance = (
            self.stability_tolerance_k if tolerance is None else float(tolerance)
        )
        if tolerance < 0:
            raise ValueError("tolerance must not be negative")
        if len(self._stability_samples) < self.stability_readings:
            return False
        temperatures = [temperature for _, temperature in self._stability_samples]
        return max(temperatures) - min(temperatures) <= tolerance

    def is_at_setpoint(
        self,
        tolerance: float | None = None,
        stability_tolerance: float | None = None,
    ) -> bool:
        """Return whether the selected input is at a stable control-loop setpoint."""
        tolerance = self.setpoint_tolerance_k if tolerance is None else float(tolerance)
        if tolerance < 0:
            raise ValueError("tolerance must not be negative")
        temperature = self.get_temperature()
        self._record_stability_sample(temperature)
        self.temperature_target = self.get_setpoint()
        return (
            abs(temperature - self.temperature_target) <= tolerance
            and self.is_temperature_stable(stability_tolerance)
        )

    def measure(self) -> dict[str, Measurement]:
        """Record temperature, setpoint, and heater output."""
        temperature = self.get_temperature()
        setpoint = self.get_setpoint()
        heater_output = self.get_heater_output()
        self.temperature_target = setpoint
        self._record_stability_sample(temperature)
        self.measurements["temperature (K)"] = Measurement(data=[temperature], unit="K")
        self.measurements["setpoint (K)"] = Measurement(data=[setpoint], unit="K")
        self.measurements["heater output (%)"] = Measurement(
            data=[heater_output], unit="%"
        )
        if self.connect_to_rex:
            self.tcp_send(self.create_payload(), self.sock)
        return self.measurements

    def close(self) -> None:
        """Close QCoDeS' managed PyVISA connection."""
        instrument = getattr(self, "instrument", None)
        if instrument is not None:
            instrument.close()
