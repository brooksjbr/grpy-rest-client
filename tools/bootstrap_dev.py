#!/usr/bin/env python3
import argparse
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


def setup_virtualenv(force=False):
    """Create and configure virtualenv"""
    venv_path = get_venv_path()
    logger.info(f"Virtualenv path: {venv_path}")

    try:
        if force and venv_path.exists():
            logger.info(f"Removing existing virtualenv at {venv_path}")
            shutil.rmtree(venv_path)

        if not venv_path.exists():
            logger.info(f"Creating virtualenv at {venv_path}")
            run_command(f"python3 -m venv {venv_path}")

        # Use the venv's pip directly without activation
        logger.info("Installing package with dev dependencies")
        run_command(f'{venv_path}/bin/pip install -e ".[dev]"')

        # Install and initialize pre-commit hooks
        logger.info("Setting up pre-commit hooks")
        run_command(f"{venv_path}/bin/pre-commit install")

    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to setup virtualenv: {e}")
        # Add cleanup of partially created venv
        if venv_path.exists():
            shutil.rmtree(venv_path)


def check_prerequisites():
    """Verify python version and venv module availability"""
    if sys.version_info < (3, 9):
        raise RuntimeError("Python 3.8+ required")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Setup development environment for grpy-service"
    )
    parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Force recreation of virtualenv",
    )
    args = parser.parse_args()

    check_prerequisites()
    setup_virtualenv(force=args.force)
    logger.info(
        f"Virtualenv setup complete!\n"
        f"Run 'source {get_venv_path()}/bin/activate' to activate the virtualenv."
    )
