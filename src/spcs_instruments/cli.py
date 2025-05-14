import rex
import logging
import sys
logging.basicConfig(level=logging.ERROR, format="%(asctime)s - %(levelname)s - %(message)s")

def runner():
    try:
  
        rex.cli_parser_py()
    except KeyboardInterrupt:
        logging.debug("PyFex has exited after being exited by the user.")
        sys.exit(0)  

def runner_standalone():
    rex.cli_standalone()

if __name__ == "__main__":
    runner()
