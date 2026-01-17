import importlib.metadata
import logging
import sys

logging.basicConfig(
    level=logging.ERROR, format="%(asctime)s - %(levelname)s - %(message)s"
)


def get_package_version(package_name):
    try:
        return importlib.metadata.version(package_name)
    except importlib.metadata.PackageNotFoundError:
        return None


def spcs_version():
    version = get_package_version("spcs_instruments")
    python_path = sys.executable
    print(f"SPCS-Instruments version: {version}")
    print(f"Python executable path: {python_path}")


if __name__ == "__main__":
    spcs_version()
