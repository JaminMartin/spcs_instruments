from spcs_instruments import HoribaiHR550
import time

spec = HoribaiHR550()
print(spec._state)
spec.set_turret("VIS")
spec.initialize()
spec.set_mirror("Exit","side")
spec.set_slit(0,3)
spec.set_slit(3,3)
print(spec._state)