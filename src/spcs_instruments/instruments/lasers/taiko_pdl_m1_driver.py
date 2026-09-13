"""Rex driver for a PicoQuant Taiko PDL M1 laser driver.

The Taiko API is a Windows ``stdcall`` DLL API. The driver obtains calibration
limits and supported features from the connected laser head.
"""

from __future__ import annotations

import ctypes
import os
import sys
import time
from pathlib import Path
from threading import RLock
from typing import Iterator

from rex_utils import DeviceError, Measurement, RexSupport


class TaikoError(DeviceError):
    """An error returned by the PicoQuant Taiko API."""


class TaikoPDLM1(RexSupport):
    """Control a Taiko PDL M1 through PicoQuant's DLL."""

    USB_INDEX_MIN = 0
    USB_INDEX_MAX = 7

    LASER_MODE_CW = 0
    LASER_MODE_PULSE = 1
    LASER_MODE_BURST = 2

    FEATURE_CW_CAPABILITY = 0x00000001
    FEATURE_BURST_CAPABILITY = 0x00000010
    FEATURE_WAVELENGTH_TUNABLE = 0x00000100

    STATUS_LASER_HEAD_CHANGED = 0x00000800

    TEMPERATURE_CELSIUS = 0

    __toml_config__ = {
        "device.TaikoPDLM1": {
            "_section_description": "PicoQuant Taiko PDL M1 laser configuration",
            "dll_path": {
                "_value": "C:/Program Files/PicoQuant/Taiko/API/Win64/PDLM_Lib.dll",
                "_description": "Path to the vendor-installed PDLM_Lib.dll. Python and the DLL must have the same 32/64-bit architecture.",
            },
            "serial_number": {
                "_value": "1234567",
                "_description": "Taiko driver serial number. It is used instead of an unstable USB slot index.",
            },
            "wavelength_temperature_map": {
                "_value": [],
                "_description": "Optional list of measured {wavelength_nm, temperature_c} calibration points. At least two points enable wavelength scanning for this laser head.",
            },
            "temperature_tolerance_c": {
                "_value": 0.1,
                "_description": "Maximum diode-temperature error in degrees C before a wavelength step is considered settled.",
            },
            "wavelength_tolerance_nm": {
                "_value": 0.1,
                "_description": "Maximum difference in nm between the requested calibrated wavelength and Taiko's estimated wavelength before a scan step is considered settled.",
            },
            "stability_readings": {
                "_value": 3,
                "_description": "Consecutive in-tolerance temperature readings required for a scan step.",
            },
            "stability_sample_interval_s": {
                "_value": 1.0,
                "_description": "Seconds between diode-temperature checks while a scan step settles.",
            },
            "stability_max_samples": {
                "_value": 120,
                "_description": "Maximum bounded temperature checks before a scan step raises TimeoutError.",
            },
        }
    }

    def __init__(
        self, config: str, name: str = "TaikoPDLM1", connect_to_rex: bool = True
    ) -> None:
        super().__init__(name=name)
        self.bind_config(config)
        self.connect_to_rex = connect_to_rex
        self._api_lock = RLock()
        self._usb_index: int | None = None
        self._is_open = False

        self._load_library(Path(self.require_config("dll_path")))
        self.library_version = self._get_library_version()
        self.serial_number = str(self.require_config("serial_number"))
        self._usb_index = self._find_device(self.serial_number)
        self._open_device(self._usb_index, self.serial_number)
        self._is_open = True
        self.refresh_head_capabilities()
        self.wavelength_temperature_map = self._parse_wavelength_temperature_map(
            self.config.get("wavelength_temperature_map", [])
        )
        self.temperature_tolerance_c = float(
            self.config.get("temperature_tolerance_c", 0.1)
        )
        self.wavelength_tolerance_nm = float(
            self.config.get("wavelength_tolerance_nm", 0.1)
        )
        self.stability_readings = int(self.config.get("stability_readings", 3))
        self.stability_sample_interval_s = float(
            self.config.get("stability_sample_interval_s", 1.0)
        )
        self.stability_max_samples = int(
            self.config.get("stability_max_samples", 120)
        )
        self._validate_stability_settings()
        self.wavelength_scan_config = self._parse_wavelength_scan_config(
            self.config.get("wavelength_scan")
        )
        self.wavelength_scan_targets = (
            list(self.scan_configured_wavelength_range())
            if self.wavelength_scan_config is not None
            else []
        )
        self.current_wavelength_index = 0
        self.desired_wavelength_nm: float | None = None

        self.measurements = {
            "system status": Measurement(data=[], unit="dimensionless"),
            "laser locked": Measurement(data=[], unit="dimensionless"),
            "laser mode": Measurement(data=[], unit="dimensionless"),
            "frequency (Hz)": Measurement(data=[], unit="Hz"),
            "power setpoint (W)": Measurement(data=[], unit="W"),
            "power setpoint (permille)": Measurement(data=[], unit="dimensionless"),
            "diode temperature (degC)": Measurement(data=[], unit="degC"),
            "case temperature (degC)": Measurement(data=[], unit="degC"),
        }
        if self.supports_wavelength_tuning:
            self.measurements["estimated wavelength (nm)"] = Measurement(
                data=[], unit="nm"
            )
        if self.connect_to_rex:
            self.sock = self.tcp_connect()

    def _load_library(self, dll_path: Path) -> None:
        """Load the vendor DLL and declare the scalar APIs used by this driver."""
        if sys.platform != "win32":
            raise TaikoError(
                "TaikoPDLM1 requires Windows and PicoQuant's PDLM_Lib.dll; "
                "the vendor documents non-Windows operation only through Wine."
            )
        if not dll_path.is_file():
            raise TaikoError(f"Taiko DLL was not found: {dll_path}")

        # PDLM_Lib.dll has companion DLLs in the installed API directory.
        self._dll_directory = os.add_dll_directory(str(dll_path.parent))
        self.dll = ctypes.WinDLL(str(dll_path))

        self._declare("PDLM_GetLibraryVersion", [ctypes.c_char_p, ctypes.c_uint32])
        self._declare(
            "PDLM_DecodeError",
            [ctypes.c_int, ctypes.c_char_p, ctypes.POINTER(ctypes.c_uint32)],
        )
        self._declare("PDLM_OpenDevice", [ctypes.c_int, ctypes.c_char_p])
        self._declare("PDLM_CloseDevice", [ctypes.c_int])
        self._declare("PDLM_OpenGetSerNumAndClose", [ctypes.c_int, ctypes.c_char_p])
        self._declare(
            "PDLM_GetLHFeatures", [ctypes.c_int, ctypes.POINTER(ctypes.c_uint32)]
        )
        self._declare("PDLM_GetSystemStatus", [ctypes.c_int, ctypes.POINTER(ctypes.c_uint32)])
        self._declare("PDLM_GetLocked", [ctypes.c_int, ctypes.POINTER(ctypes.c_uint32)])
        self._declare("PDLM_SetSoftLock", [ctypes.c_int, ctypes.c_uint32])
        self._declare("PDLM_GetLaserMode", [ctypes.c_int, ctypes.POINTER(ctypes.c_uint32)])
        self._declare("PDLM_SetLaserMode", [ctypes.c_int, ctypes.c_uint32])
        self._declare(
            "PDLM_GetFrequencyLimits",
            [ctypes.c_int, ctypes.POINTER(ctypes.c_uint32), ctypes.POINTER(ctypes.c_uint32)],
        )
        self._declare("PDLM_GetFrequency", [ctypes.c_int, ctypes.POINTER(ctypes.c_uint32)])
        self._declare("PDLM_SetFrequency", [ctypes.c_int, ctypes.c_uint32])
        self._declare(
            "PDLM_GetLHCurrentTemp",
            [ctypes.c_int, ctypes.c_uint32, ctypes.POINTER(ctypes.c_float)],
        )
        self._declare(
            "PDLM_GetLHTargetTempLimits",
            [
                ctypes.c_int,
                ctypes.c_uint32,
                ctypes.POINTER(ctypes.c_float),
                ctypes.POINTER(ctypes.c_float),
            ],
        )
        self._declare(
            "PDLM_GetLHTargetTemp",
            [ctypes.c_int, ctypes.c_uint32, ctypes.POINTER(ctypes.c_float)],
        )
        self._declare(
            "PDLM_SetLHTargetTemp",
            [ctypes.c_int, ctypes.c_uint32, ctypes.c_float],
        )
        self._declare(
            "PDLM_GetLHCaseTemp",
            [ctypes.c_int, ctypes.c_uint32, ctypes.POINTER(ctypes.c_float)],
        )
        self._declare("PDLM_GetLHWavelength", [ctypes.c_int, ctypes.POINTER(ctypes.c_float)])
        for prefix in ("Pulse", "Cw"):
            self._declare(
                f"PDLM_Get{prefix}PowerLimits",
                [ctypes.c_int, ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_float)],
            )
            self._declare(
                f"PDLM_Get{prefix}Power",
                [ctypes.c_int, ctypes.POINTER(ctypes.c_float)],
            )
            self._declare(
                f"PDLM_Set{prefix}Power",
                [ctypes.c_int, ctypes.c_float],
            )
            self._declare(
                f"PDLM_Get{prefix}PowerPermille",
                [ctypes.c_int, ctypes.POINTER(ctypes.c_uint32)],
            )
            self._declare(
                f"PDLM_Set{prefix}PowerPermille", [ctypes.c_int, ctypes.c_uint32]
            )

    def _declare(self, name: str, argtypes: list[object]) -> None:
        function = getattr(self.dll, name)
        function.argtypes = argtypes
        function.restype = ctypes.c_int

    def _get_library_version(self) -> str:
        buffer = ctypes.create_string_buffer(32)
        self._check(self.dll.PDLM_GetLibraryVersion(buffer, len(buffer)))
        return buffer.value.decode("latin-1")

    def _find_device(self, serial_number: str) -> int:
        """Return the USB slot currently assigned to ``serial_number``."""
        for usb_index in range(self.USB_INDEX_MIN, self.USB_INDEX_MAX + 1):
            buffer = ctypes.create_string_buffer(32)
            result = self.dll.PDLM_OpenGetSerNumAndClose(usb_index, buffer)
            if result == 0 and buffer.value.decode("latin-1") == serial_number:
                return usb_index
        raise TaikoError(f"No Taiko with serial number {serial_number!r} was found.")

    def _open_device(self, usb_index: int, serial_number: str) -> None:
        buffer = ctypes.create_string_buffer(serial_number.encode("latin-1"), 32)
        self._check(self.dll.PDLM_OpenDevice(usb_index, buffer))

    def _check(self, result: int) -> None:
        if result:
            raise TaikoError(self._decode_error(int(result)))

    def _decode_error(self, error_code: int) -> str:
        buffer = ctypes.create_string_buffer(256)
        length = ctypes.c_uint32(len(buffer))
        result = self.dll.PDLM_DecodeError(error_code, buffer, ctypes.byref(length))
        if result == 0 and buffer.value:
            return f"Taiko API error {error_code}: {buffer.value.decode('latin-1')}"
        return f"Taiko API error {error_code}"

    @property
    def usb_index(self) -> int:
        """Current USB slot; use ``serial_number`` for persistent configuration."""
        if self._usb_index is None:
            raise TaikoError("Taiko device is not open.")
        return self._usb_index

    def _get_uint(self, function_name: str) -> int:
        value = ctypes.c_uint32()
        with self._api_lock:
            self._check(
                getattr(self.dll, function_name)(self.usb_index, ctypes.byref(value))
            )
        return int(value.value)

    def _get_float(self, function_name: str, *inputs: int) -> float:
        value = ctypes.c_float()
        with self._api_lock:
            self._check(
                getattr(self.dll, function_name)(
                    self.usb_index, *inputs, ctypes.byref(value)
                )
            )
        return float(value.value)

    def refresh_head_capabilities(self) -> int:
        """Refresh feature flags after connecting or changing a laser head."""
        self.head_features = self._get_uint("PDLM_GetLHFeatures")
        return self.head_features

    @staticmethod
    def _parse_wavelength_temperature_map(
        raw_points: object,
    ) -> tuple[tuple[float, float], ...]:
        """Validate and sort an optional wavelength-to-temperature calibration."""
        if raw_points in (None, []):
            return ()
        if not isinstance(raw_points, list) or len(raw_points) < 2:
            raise ValueError(
                "wavelength_temperature_map must contain at least two calibration points"
            )
        try:
            points = sorted(
                (float(point["wavelength_nm"]), float(point["temperature_c"]))
                for point in raw_points
            )
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(
                "Each wavelength_temperature_map point needs wavelength_nm and temperature_c"
            ) from error
        temperature_directions = {
            (next_temperature > temperature) - (next_temperature < temperature)
            for (_, temperature), (_, next_temperature) in zip(points, points[1:])
        }
        if (
            any(next_wavelength <= wavelength for (wavelength, _), (next_wavelength, _) in zip(points, points[1:]))
            or len(temperature_directions) != 1
            or 0 in temperature_directions
        ):
            raise ValueError(
                "wavelength_temperature_map wavelengths and temperatures must each be strictly monotonic"
            )
        return tuple(points)

    def _validate_stability_settings(self) -> None:
        if self.temperature_tolerance_c < 0:
            raise ValueError("temperature_tolerance_c must not be negative")
        if self.wavelength_tolerance_nm < 0:
            raise ValueError("wavelength_tolerance_nm must not be negative")
        if self.stability_readings < 1:
            raise ValueError("stability_readings must be at least one")
        if self.stability_sample_interval_s < 0:
            raise ValueError("stability_sample_interval_s must not be negative")
        if self.stability_max_samples < self.stability_readings:
            raise ValueError("stability_max_samples must cover stability_readings")

    @staticmethod
    def _parse_wavelength_scan_config(
        raw_config: object,
    ) -> tuple[float, float, float] | None:
        """Validate optional TOML start, stop, and step values for a scan."""
        if raw_config is None:
            return None
        if not isinstance(raw_config, dict):
            raise ValueError("wavelength_scan must be a TOML table")
        try:
            start = float(raw_config["start_wavelength_nm"])
            stop = float(raw_config["stop_wavelength_nm"])
            step = float(raw_config["step_nm"])
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(
                "wavelength_scan needs start_wavelength_nm, stop_wavelength_nm, and step_nm"
            ) from error
        if step == 0:
            raise ValueError("wavelength_scan.step_nm must not be zero")
        return start, stop, step

    @property
    def supports_cw(self) -> bool:
        return bool(self.head_features & self.FEATURE_CW_CAPABILITY)

    @property
    def supports_burst(self) -> bool:
        return bool(self.head_features & self.FEATURE_BURST_CAPABILITY)

    @property
    def supports_wavelength_tuning(self) -> bool:
        return bool(self.head_features & self.FEATURE_WAVELENGTH_TUNABLE)

    def get_frequency_limits(self) -> tuple[int, int]:
        """Return calibrated pulse-frequency limits for the connected head."""
        minimum = ctypes.c_uint32()
        maximum = ctypes.c_uint32()
        with self._api_lock:
            self._check(
                self.dll.PDLM_GetFrequencyLimits(
                    self.usb_index, ctypes.byref(minimum), ctypes.byref(maximum)
                )
            )
        return int(minimum.value), int(maximum.value)

    def get_target_temperature_limits(self) -> tuple[float, float]:
        """Return the connected head's valid diode-target range in degrees C."""
        minimum = ctypes.c_float()
        maximum = ctypes.c_float()
        with self._api_lock:
            self._check(
                self.dll.PDLM_GetLHTargetTempLimits(
                    self.usb_index,
                    self.TEMPERATURE_CELSIUS,
                    ctypes.byref(minimum),
                    ctypes.byref(maximum),
                )
            )
        return float(minimum.value), float(maximum.value)

    def get_target_temperature(self) -> float:
        """Return the diode-temperature setpoint in degrees C."""
        return self._get_float("PDLM_GetLHTargetTemp", self.TEMPERATURE_CELSIUS)

    def set_target_temperature(self, temperature_c: float) -> None:
        """Set diode temperature in degrees C within the head's calibrated range.

        The Taiko has no direct wavelength setter. For wavelength tuning, use
        this method with a head-specific temperature/wavelength calibration and
        verify the result with :meth:`measure`.
        """
        minimum, maximum = self.get_target_temperature_limits()
        if not minimum <= temperature_c <= maximum:
            raise ValueError(
                f"temperature_c must be within {minimum}..{maximum} degrees C"
            )
        with self._api_lock:
            self._check(
                self.dll.PDLM_SetLHTargetTemp(
                    self.usb_index, self.TEMPERATURE_CELSIUS, temperature_c
                )
            )
        self.desired_wavelength_nm = None

    @property
    def supports_wavelength_scan(self) -> bool:
        """Whether this head supports tuning and has a supplied calibration map."""
        return self.supports_wavelength_tuning and bool(self.wavelength_temperature_map)

    def temperature_for_wavelength(self, wavelength_nm: float) -> float:
        """Interpolate the supplied calibration map to a diode temperature.

        The calibration range bounds the supported wavelength range.
        """
        if not self.supports_wavelength_scan:
            raise TaikoError(
                "Wavelength scanning requires a wavelength-tunable head and an optional "
                "wavelength_temperature_map with at least two measured points."
            )
        wavelength_nm = float(wavelength_nm)
        first_wavelength, _ = self.wavelength_temperature_map[0]
        last_wavelength, _ = self.wavelength_temperature_map[-1]
        if not first_wavelength <= wavelength_nm <= last_wavelength:
            raise ValueError(
                f"wavelength_nm must be within the calibrated range "
                f"{first_wavelength}..{last_wavelength} nm"
            )
        for (lower_wavelength, lower_temperature), (
            upper_wavelength,
            upper_temperature,
        ) in zip(self.wavelength_temperature_map, self.wavelength_temperature_map[1:]):
            if lower_wavelength <= wavelength_nm <= upper_wavelength:
                fraction = (wavelength_nm - lower_wavelength) / (
                    upper_wavelength - lower_wavelength
                )
                return lower_temperature + fraction * (
                    upper_temperature - lower_temperature
                )
        raise RuntimeError("The wavelength calibration map could not be interpolated")

    def get_current_temperature(self) -> float:
        """Read diode temperature."""
        return self._get_float("PDLM_GetLHCurrentTemp", self.TEMPERATURE_CELSIUS)

    def is_temperature_stable(self) -> bool:
        """Check target-temperature tolerance."""
        return (
            abs(self.get_current_temperature() - self.get_target_temperature())
            <= self.temperature_tolerance_c
        )

    def is_at_desired_wavelength(self) -> bool:
        """Whether the last calibrated wavelength request is temperature-settled.

        A settled target has diode temperature and estimated wavelength within
        their configured tolerances.
        """
        return (
            self.desired_wavelength_nm is not None
            and self.supports_wavelength_scan
            and self.is_temperature_stable()
            and abs(
                self._get_float("PDLM_GetLHWavelength")
                - self.desired_wavelength_nm
            )
            <= self.wavelength_tolerance_nm
        )

    def _wait_for_temperature_stability(self) -> None:
        """Wait until the current wavelength target is settled."""
        consecutive_readings = 0
        for sample_index in range(self.stability_max_samples):
            if self.is_at_desired_wavelength():
                consecutive_readings += 1
                if consecutive_readings >= self.stability_readings:
                    return
            else:
                consecutive_readings = 0
            if sample_index < self.stability_max_samples - 1:
                time.sleep(self.stability_sample_interval_s)
        raise TimeoutError(
            "Taiko did not reach the configured temperature and estimated-wavelength "
            f"tolerances within {self.stability_max_samples} samples"
        )

    def scan_wavelength_range(
        self, start_wavelength_nm: float, stop_wavelength_nm: float, step_nm: float
    ) -> Iterator[tuple[float, float]]:
        """Yield calibrated wavelength and diode-temperature targets."""
        if step_nm == 0:
            raise ValueError("step_nm must not be zero")
        start_wavelength_nm = float(start_wavelength_nm)
        stop_wavelength_nm = float(stop_wavelength_nm)
        step_nm = abs(float(step_nm))
        direction = 1 if stop_wavelength_nm >= start_wavelength_nm else -1
        point_count = int(abs(stop_wavelength_nm - start_wavelength_nm) / step_nm) + 1
        last_wavelength_nm = start_wavelength_nm
        for point_index in range(point_count):
            wavelength_nm = start_wavelength_nm + direction * point_index * step_nm
            if direction * (wavelength_nm - stop_wavelength_nm) > 0:
                break
            last_wavelength_nm = wavelength_nm
            yield wavelength_nm, self.temperature_for_wavelength(wavelength_nm)
        if abs(last_wavelength_nm - stop_wavelength_nm) > 1e-12:
            yield stop_wavelength_nm, self.temperature_for_wavelength(stop_wavelength_nm)

    def scan_configured_wavelength_range(
        self,
    ) -> Iterator[tuple[float, float]]:
        """Yield optional TOML-configured wavelength/temperature targets."""
        if self.wavelength_scan_config is None:
            raise TaikoError(
                "wavelength_scan is not configured; add start_wavelength_nm, "
                "stop_wavelength_nm, and step_nm to the config."
            )
        return self.scan_wavelength_range(*self.wavelength_scan_config)

    @property
    def total_wavelength_steps(self) -> int:
        """Number of configured wavelength targets available to scan."""
        return len(self.wavelength_scan_targets)

    def reset_wavelength_scan(self) -> None:
        """Return the configured scan cursor to its first wavelength target."""
        self.current_wavelength_index = 0

    def move_to_next_wavelength(self) -> float | None:
        """Move to and stabilize at the next configured wavelength target."""
        if not self.supports_wavelength_scan:
            raise TaikoError(
                "Wavelength scanning requires a wavelength-tunable head and an optional "
                "wavelength_temperature_map with at least two measured points."
            )
        if self.current_wavelength_index >= self.total_wavelength_steps:
            return None
        wavelength_nm, temperature_c = self.wavelength_scan_targets[
            self.current_wavelength_index
        ]
        self.set_target_temperature(temperature_c)
        self.desired_wavelength_nm = wavelength_nm
        self._wait_for_temperature_stability()
        self.current_wavelength_index += 1
        return wavelength_nm

    def set_software_lock(self, locked: bool) -> None:
        """Set the Taiko software lock; locking is the explicit safe-off action."""
        with self._api_lock:
            self._check(self.dll.PDLM_SetSoftLock(self.usb_index, int(locked)))

    def set_laser_mode(self, mode: str) -> None:
        """Set ``pulse``, ``cw``, or ``burst`` after checking head support."""
        modes = {"cw": self.LASER_MODE_CW, "pulse": self.LASER_MODE_PULSE, "burst": self.LASER_MODE_BURST}
        try:
            mode_code = modes[mode.lower()]
        except KeyError as error:
            raise ValueError("mode must be 'pulse', 'cw', or 'burst'") from error
        if mode_code == self.LASER_MODE_CW and not self.supports_cw:
            raise TaikoError("The connected laser head does not support CW mode.")
        if mode_code == self.LASER_MODE_BURST and not self.supports_burst:
            raise TaikoError("The connected laser head does not support burst mode.")
        with self._api_lock:
            self._check(self.dll.PDLM_SetLaserMode(self.usb_index, mode_code))

    def set_frequency(self, frequency_hz: int) -> None:
        """Set pulse frequency within the connected head's reported limits."""
        minimum, maximum = self.get_frequency_limits()
        if not minimum <= frequency_hz <= maximum:
            raise ValueError(f"frequency_hz must be within {minimum}..{maximum} Hz")
        with self._api_lock:
            self._check(self.dll.PDLM_SetFrequency(self.usb_index, frequency_hz))

    def get_power_limits(self) -> tuple[float, float]:
        """Return calibrated power limits in watts for the current emission mode."""
        prefix = (
            "Cw"
            if self._get_uint("PDLM_GetLaserMode") == self.LASER_MODE_CW
            else "Pulse"
        )
        minimum = ctypes.c_float()
        maximum = ctypes.c_float()
        with self._api_lock:
            self._check(
                getattr(self.dll, f"PDLM_Get{prefix}PowerLimits")(
                    self.usb_index, ctypes.byref(minimum), ctypes.byref(maximum)
                )
            )
        return float(minimum.value), float(maximum.value)

    def set_power_permille(self, permille: int) -> None:
        """Set power as 0–1000 permille of the active head's calibrated maximum."""
        if not 0 <= permille <= 1000:
            raise ValueError("permille must be between 0 and 1000")
        prefix = (
            "Cw"
            if self._get_uint("PDLM_GetLaserMode") == self.LASER_MODE_CW
            else "Pulse"
        )
        with self._api_lock:
            self._check(
                getattr(self.dll, f"PDLM_Set{prefix}PowerPermille")(
                    self.usb_index, permille
                )
            )

    def set_power_watts(self, watts: float) -> None:
        """Set an absolute power setpoint; prefer ``set_power_permille`` for portability."""
        minimum, maximum = self.get_power_limits()
        if not minimum <= watts <= maximum:
            raise ValueError(f"watts must be within {minimum}..{maximum} W")
        prefix = (
            "Cw"
            if self._get_uint("PDLM_GetLaserMode") == self.LASER_MODE_CW
            else "Pulse"
        )
        with self._api_lock:
            self._check(
                getattr(self.dll, f"PDLM_Set{prefix}Power")(self.usb_index, watts)
            )

    def measure(self) -> dict[str, Measurement]:
        """Read and publish a Taiko status snapshot."""
        with self._api_lock:
            status = self._get_uint("PDLM_GetSystemStatus")
            if status & self.STATUS_LASER_HEAD_CHANGED:
                self.refresh_head_capabilities()
                # A head change clears the active wavelength scan calibration.
                self.wavelength_temperature_map = ()
                self.wavelength_scan_targets = []
                self.current_wavelength_index = 0
                self.desired_wavelength_nm = None
                if (
                    self.supports_wavelength_tuning
                    and "estimated wavelength (nm)" not in self.measurements
                ):
                    self.measurements["estimated wavelength (nm)"] = Measurement(
                        data=[], unit="nm"
                    )
                elif (
                    not self.supports_wavelength_tuning
                    and "estimated wavelength (nm)" in self.measurements
                ):
                    del self.measurements["estimated wavelength (nm)"]
                if "desired wavelength (nm)" in self.measurements:
                    del self.measurements["desired wavelength (nm)"]
            locked = self._get_uint("PDLM_GetLocked")
            mode = self._get_uint("PDLM_GetLaserMode")
            prefix = "Cw" if mode == self.LASER_MODE_CW else "Pulse"
            values = {
                "system status": status,
                "laser locked": locked,
                "laser mode": mode,
                "frequency (Hz)": self._get_uint("PDLM_GetFrequency"),
                "power setpoint (W)": self._get_float(f"PDLM_Get{prefix}Power"),
                "power setpoint (permille)": self._get_uint(
                    f"PDLM_Get{prefix}PowerPermille"
                ),
                "diode temperature (degC)": self._get_float(
                    "PDLM_GetLHCurrentTemp", self.TEMPERATURE_CELSIUS
                ),
                "case temperature (degC)": self._get_float(
                    "PDLM_GetLHCaseTemp", self.TEMPERATURE_CELSIUS
                ),
            }
            if self.supports_wavelength_tuning:
                values["estimated wavelength (nm)"] = self._get_float(
                    "PDLM_GetLHWavelength"
                )
            if (
                self.supports_wavelength_scan
                and self.desired_wavelength_nm is not None
            ):
                if "desired wavelength (nm)" not in self.measurements:
                    self.measurements["desired wavelength (nm)"] = Measurement(
                        data=[], unit="nm"
                    )
                values["desired wavelength (nm)"] = (
                    self.desired_wavelength_nm
                )
        for key, value in values.items():
            self.measurements[key] = Measurement(
                data=[value], unit=self.measurements[key].unit
            )
        if self.connect_to_rex:
            self.tcp_send(self.create_payload(), self.sock)
        return self.measurements

    def shutdown(self) -> None:
        """Lock the laser through software, then release the API connection."""
        self.set_software_lock(True)
        self.close()

    def close(self) -> None:
        """Release the exclusive API connection."""
        if self._is_open:
            with self._api_lock:
                self._check(self.dll.PDLM_CloseDevice(self.usb_index))
            self._is_open = False
            self._usb_index = None
        dll_directory = getattr(self, "_dll_directory", None)
        if dll_directory is not None:
            dll_directory.close()
