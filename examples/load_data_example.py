from spcs_instruments import load_experimental_data

import polars as pl
import pandas as pd
from pathlib import Path
# Get the directory where the current script is located
script_dir = Path(__file__).parent

# Construct the path to the TOML file relative to the script
results = str(script_dir / "example_data.toml")

#retrieve the data as a pure dict
data_dict = load_experimental_data(data_file = results, method = "dict")
print(data_dict)


# load data as polars dataframe
df_polars = load_experimental_data(data_file = results, method = "polars")
print(df_polars)

# filter the data polars
temp_1 = df_polars.filter(pl.col("Test_cryostat_temperature (K)") < 4.0)
temp_2 = df_polars.filter(
    pl.col("Test_cryostat_temperature (K)").is_between(4.0, 8.0, closed="left")
)
temp_3 = df_polars.filter(
    pl.col("Test_cryostat_temperature (K)").is_between(8.0, 11.0, closed="left")
)
temp_4 = df_polars.filter(
    pl.col("Test_cryostat_temperature (K)").is_between(14.0, 18.0, closed="left")
)
temp_5 = df_polars.filter(
    pl.col("Test_cryostat_temperature (K)").is_between(18.0, 25.0, closed="left")
)
print(temp_1)

# load data as pandas dataframe
df_pandas = load_experimental_data(data_file = results, method = "pandas")
print(df_pandas)
# filter the data pandas
col = "Test_cryostat_temperature (K)"
temp_1 = df_pandas[df_pandas[col] < 4.0]
temp_2 = df_pandas[df_pandas[col].between(4.0, 8.0, inclusive="left")]
temp_3 = df_pandas[df_pandas[col].between(8.0, 11.0, inclusive="left")]
temp_4 = df_pandas[df_pandas[col].between(14.0, 18.0, inclusive="left")]
temp_5 = df_pandas[df_pandas[col].between(18.0, 25.0, inclusive="left")]

print(temp_1)