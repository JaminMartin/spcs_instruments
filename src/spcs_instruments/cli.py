import argparse
import spcs_instruments.spcs_rust_utils as spi
import sys


def runner():
    spi.cli_parser()


if __name__ == "__main__":
    runner()
