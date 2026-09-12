"""Rex integration for a Lake Shore Model 325 temperature controller."""

from __future__ import annotations

from qcodes.instrument_drivers.Lakeshore import LakeshoreModel325
from rex_utils import Measurement, RexSupport


class Lakeshore325(RexSupport):
    """Control and acquire measurements from a Lake Shore Model 325.

    This is a thin Rex adapter around QCoDeS' dedicated ``LakeshoreModel325``
    driver. The controller may be connected through any PyVISA-supported
    resource, including its RS-232 or IEEE-488 interfaces. The driver does not
    change a setpoint or heater range when it connects.
    """

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
        """Set a control-loop temperature setpoint in kelvin.

        This does not enable the heater.  Use :meth:`set_heater_range` only
        after confirming the heater and control-loop configuration are safe.
        """
        loop = self._validate_control_loop(control_loop or self.control_loop)
        temperature = float(temperature)
        getattr(self.instrument, f"heater_{loop}").setpoint(temperature)
        if loop == self.control_loop:
            self.temperature_target = temperature

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

    def is_at_setpoint(self, tolerance: float = 0.1) -> bool:
        """Return whether the selected input is within ``tolerance`` kelvin of target."""
        tolerance = float(tolerance)
        if tolerance < 0:
            raise ValueError("tolerance must not be negative")
        return abs(self.get_temperature() - self.temperature_target) <= tolerance

    def measure(self) -> dict[str, Measurement]:
        """Record temperature, setpoint, and heater output and send them to Rex."""
        temperature = self.get_temperature()
        setpoint = self.get_setpoint()
        heater_output = self.get_heater_output()
        self.temperature_target = setpoint
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
