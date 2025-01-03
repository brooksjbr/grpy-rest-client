#!/usr/bin/env python3
import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

HOME = Path.home()
VENV_PATH = os.getenv("VENV_PATH", "projects/.venvs")
PROJECT_NAME = Path.cwd().name


def get_venv_path():
    """Get virtualenv path using user's home directory"""
    return HOME / VENV_PATH / PROJECT_NAME


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


def setup_virtualenv():
    """Create and configure virtualenv"""
    venv_path = get_venv_path()
    logger.info(f"Virtualenv path: {venv_path}")

    try:
        if not venv_path.exists():
            logger.info(f"Creating virtualenv at {venv_path}")
            run_command(f"python3 -m venv {venv_path}")

        commands = [
            f'{venv_path}/bin/python3 -m pip install -e ".[dev]"',
            f". {venv_path}/bin/activate",
        ]

        for cmd in commands:
            logger.info(f"Running: {cmd}")
            run_command(cmd)
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to setup virtualenv: {e}")
        # Add cleanup of partially created venv
        if venv_path.exists():
            shutil.rmtree(venv_path)


def check_prerequisites():
    """Verify python version and venv module availability"""
    if sys.version_info < (3, 8):
        raise RuntimeError("Python 3.8+ required")


if __name__ == "__main__":
    check_prerequisites()
    setup_virtualenv()
    logger.info(
        f"Virtualenv setup complete, {PROJECT_NAME} is ready run in development!"
    )
