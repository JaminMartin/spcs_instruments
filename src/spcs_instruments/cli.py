import rex
import logging
import sys
logging.basicConfig(level=logging.ERROR, format="%(asctime)s - %(levelname)s - %(message)s")

def runner():
    try:
  
        rex.cli_parser_py()
    except KeyboardInterrupt:
        logging.debug("rex has exited after being exited by the user.")
        sys.exit(0)  

def runner_standalone():
    rex.cli_standalone()
def spcs_version():
    from spcs_instruments.spcs_instruments_utils import get_package_version
    version = get_package_version("spcs_instruments")
    print(f'SPCS-Instruments version: {version}')
if __name__ == "__main__":
    runner()
