import random as rd

import numpy as np
from rex_utils import Measurement, RexSupport


class Test_daq(RexSupport):
    __toml_config__ = {
        "device.Test_DAQ": {
            "_section_description": "Test_DAQ measurement configuration",
            "gate_time": {"_value": 0.1, "_description": "Step size in nm"},
            "averages": {"_value": 500, "_description": "Start wavelength (nm)"},
            "trace": {
                "_value": False,
                "_description": "Sends mock time series data if set to True",
            },
        }
    }

    def __init__(self, config, name="Test_DAQ", emulate=True, connect_to_rex=True):
        """
        A simulated device
        """

        self.emulation = emulate
        self.state = 0
        self.connect_to_rex = connect_to_rex
        super().__init__(name=name)
        self.bind_config(config)
        self.logger.debug(f"{self.name} connected with this config {self.config}")
        if self.connect_to_rex:
            self.sock = self.tcp_connect()
        self.setup_config()
        self.measurements = {
            "counts": Measurement(data=[], unit="dimensionless"),
            "current (mA)": Measurement(data=[], unit="mA"),
            "trace (signal)": Measurement(data=[], unit="V"),
            "trace (time (s))": Measurement(data=[], unit="s"),
        }

    def setup_config(self):
        self.gate_time = self.config.get("gate_time")
        self.averages = self.config.get("averages")
        self.trace_enabled = self.config.get("trace", False)

    def measure(self) -> float:
        data = rd.uniform(0.0, 10) * self.gate_time + self.state
        self.measurements["counts"] = Measurement(
            data=[data],
            unit="dimensionless",
        )

        self.measurements["current (mA)"] = Measurement(
            data=[data * rd.uniform(0.0, 10.0)],
            unit="mA",
        )

        if self.trace_enabled:
            time = np.linspace(0.0, 10.0, 20)
            noise = np.random.normal(0.0, 0.1, 20)
            trace_data = np.exp(-time) + noise

            self.measurements["trace (signal)"] = Measurement(
                data=trace_data.tolist(),
                unit="V",
            )

            self.measurements["trace (time (s))"] = Measurement(
                data=time.tolist(),
                unit="s",
            )

        self.state += 1
        if self.connect_to_rex:
            payload = self.create_payload()
            self.tcp_send(payload, self.sock)
        return data
