import os
import sys
from spcs_instruments import C8855_counting_unit
dir_path = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(dir_path, "..", "templates", "config6.toml")
config_path = os.path.abspath(config_path)


counter = C8855_counting_unit(config_path)
print(counter.config)
# counter.test_print()
counter.setup_config()
#counter.setup_experiment()
bins,counts = counter.measure()

print(bins)
print(len(bins))
print(counts)
