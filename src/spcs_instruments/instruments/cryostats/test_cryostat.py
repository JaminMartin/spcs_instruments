import random as rd

from rex_utils import Measurement, RexSupport


class Test_cryostat(RexSupport):
    def __init__(self, config, name="Test_cryostat", emulate=True, connect_to_rex=True):
        """
        A simulated device
        """

        self.emulation = emulate
        self.connect_to_rex = connect_to_rex

        super().__init__(name=name)
        self.bind_config(config)
        self.logger.debug(f"{self.name} connected with this config {self.config}")
        if self.connect_to_rex:
            self.sock = self.tcp_connect()

        self.setup_config()
        self.measurements = {
            "temperature (K)": Measurement(
                data=[],
                unit="K",
            ),
            "stability (K)": Measurement(
                data=[],
                unit="K",
            ),
            "pressure (kPa)": Measurement(
                data=[],
                unit="kPa",
            ),
            "magnetic field (mT)": Measurement(
                data=[],
                unit="mT",
            ),
        }

    def setup_config(self):
        self.logger.debug("Initialising cryostat into desired state")
        self.goto_setpoint(self.config.get(""))
        self.desired_stability = self.config.get("desired_stability")
        self.desired_field_strength = 0.0

    def measure(self) -> float:
        temperature, stability, pressure = self.get_cryostate()
        field_strength = self.get_magnetstate()
        self.measurements["temperature (K)"] = Measurement(data=[temperature], unit="K")
        self.measurements["stability (K)"] = Measurement(data=[stability], unit="K")
        self.measurements["pressure (kPa)"] = Measurement(data=[pressure], unit="kPa")
        self.measurements["magnetic field (mT)"] = Measurement(
            data=[field_strength], unit="mT"
        )

        if self.connect_to_rex:
            payload = self.create_payload()
            self.tcp_send(payload, self.sock)
        return self.measurements

    def goto_setpoint(self, setpoint):
        self.set_point = setpoint

    def set_magneticfield(self, strength):
        self.desired_field_strength = strength

    def get_cryostate(self):
        temperature = self.set_point + rd.uniform(-0.005, 0.05)
        stability = self.desired_stability + rd.uniform(-0.005, 0.005)
        pressure = 2e-6 + rd.uniform(-0.1, 0.1)
        return temperature, stability, pressure

    def get_magnetstate(self):
        field_strength = self.desired_field_strength
        return field_strength
