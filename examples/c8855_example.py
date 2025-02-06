from spcs_instruments import C8855_counting_unit


config = 'C:/Users/micha/Documents/spcs_instruments/examples/C8855.toml'

counter = C8855_counting_unit(config)
print(counter.config)
# counter.test_print()
counter.setup_config()
#counter.setup_experiment()
bins,counts = counter.measure()

print(bins)
print(len(bins))
print(counts)
