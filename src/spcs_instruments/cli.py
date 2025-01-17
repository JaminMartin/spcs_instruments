import spcs_instruments.pyfex as spi


def runner():
    spi.cli_parser()

def runner_standalone():
    spi.cli_standalone()

if __name__ == "__main__":
    runner()
