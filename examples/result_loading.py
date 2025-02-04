from spcs_instruments.pyfex import load_experimental_data
from pathlib import Path

# Get the directory where the current script is located
script_dir = Path(__file__).parent

# Construct the path to the TOML file relative to the script
results = str(script_dir / "example_results.toml")

#loads the data from the results file. Automaticlly parses out the experimental data and ignores all the equipment config & experimental config
data = load_experimental_data(results)
print(data)