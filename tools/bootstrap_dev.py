#!/usr/bin/env python3
import subprocess
from pathlib import Path

HOME = Path.home()
VENV_PATH = 'projects/.venvs'
PROJECT_NAME = Path.cwd().name


def get_venv_path():
    """Get virtualenv path using user's home directory"""
    return HOME / VENV_PATH / PROJECT_NAME


def run_command(command):
    """Execute shell command and wait for completion"""
    process = subprocess.run(
        command,
        shell=True,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    print(f"Command output: {process.stdout}")
    return process


def setup_virtualenv():
    """Create and configure virtualenv"""
    venv_path = get_venv_path()

    if not venv_path.exists():
        print(f"Creating virtualenv at {venv_path}")
        run_command(f"python3 -m venv {venv_path}")

    commands = [
        f"{venv_path}/bin/python3 -m pip install -e .",
        f"{venv_path}/bin/python3 -m pip install -r dev_requirements.txt",
        f"{venv_path}/bin/python3 -m pip install -r test_requirements.txt",
    ]

    for cmd in commands:
        print(f"Running: {cmd}")
        run_command(cmd)


if __name__ == "__main__":
    setup_virtualenv()
    print("Virtualenv setup complete!")
