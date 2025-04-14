import logging
import os
import subprocess
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Access variables
VENV_PATH = os.getenv("PYTHON_VENV_PATH")


def run_command(command, timeout=300):
    """Execute shell command with timeout"""
    process = subprocess.run(
        command,
        shell=True,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout,
    )

    if process.stderr:
        logger.error(f"Command error: {process.stderr}")
    elif process.stdout != "":
        logger.info(f"Command output: {process.stdout}")

    return process


def set_path():
    cwd_name = Path.cwd().name

    if VENV_PATH:
        venv_path = Path(f"{VENV_PATH}/{cwd_name}")
    else:
        raise RuntimeError("No virtual env path available")

    return venv_path


def init_venv(venv_path: Path):
    # Create the virtual environment
    run_command(f"python3 -m venv --clear {venv_path}")

    # Install dependencies
    run_command(f'{venv_path}/bin/pip install -e ".[dev]"')

    # Print activation instructions instead of trying to activate
    logger.info(f"\nVirtual environment created at: {venv_path}")
    logger.info("To activate the virtual environment, run:")
    logger.info(f"  source {venv_path}/bin/activate")


def main():
    venv_path = set_path()
    init_venv(venv_path)

    return


if __name__ == "__main__":
    sys.exit(main())
