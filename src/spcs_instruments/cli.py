import argparse
import spcs_instruments._spcs_cli as spi


def runner():
    parser = argparse.ArgumentParser(
        description="A simple CLI script that echoes command line arguments."
    )
    parser.add_argument("args", nargs="*", help="Arguments to be echoed")
    parsed_args = parser.parse_args()

    print("Echoing command line arguments:")
    for arg in parsed_args.args:
        print(arg)
    res = spi.adder(int(parsed_args.args[0]), int(parsed_args.args[1]))
    print(res)
