import os

from src.spcs_instruments import pyfex
        
def test_reading_dat():        
    file_name = 'test.toml'
    dir_path = os.path.dirname(os.path.abspath(__file__))
    test_file_path = os.path.join(dir_path, file_name)
    test_file_path = os.path.abspath(test_file_path)

    data = pyfex.load_experimental_data(test_file_path)
    assert 'Test_DAQ' in data, "'Test_DAQ' key is missing from the loaded data"
    assert 'Test_DAQ2' in data, "'Test_DAQ2' key is missing from the loaded data"

    assert 'Test_DAQ3' in data, "'Test_DAQ3' key is missing from the loaded data"
    # Optional: Print keys for debugging purposes
    print(f"Loaded keys: {list(data.keys())}")
            
