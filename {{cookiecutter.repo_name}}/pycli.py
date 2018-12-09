#!/usr/bin/env python

import argparse
import os
import pathlib
import shutil
import subprocess
import sys
import types


class _Registry:
    def __init__(self):
        self.registered = {}

    def __call__(self, function):
        self.registered[function.__name__] = function
        return function


_register = _Registry()


@_register
def clean(cfg):
    """Remove extraneous files."""
    paths = [cfg.venv_path, ".coverage"] + list(pathlib.Path().glob(".coverage.*"))

    for path in paths:
        try:
            shutil.rmtree(path)
        except FileNotFoundError:
            pass


@_register
def init(cfg):
    """Set up a virtualenv, install requirements.txt, dev-requirements.txt, and current dir."""

    subprocess.run(
        ["virtualenv", "--python", sys.executable, cfg.venv_path], check=True
    )
    lock(cfg)
    if pathlib.Path("dev-requirements.txt").exists():
        subprocess.run(
            [
                cfg.venv_path / "bin/pip",
                "install",
                "--requirement",
                "dev-requirements.txt",
            ],
            check=True,
        )
    subprocess.run(
        [cfg.venv_path / "bin/pip", "install", "--requirement", "requirements.txt"],
        check=True,
    )
    subprocess.run(
        [cfg.venv_path / "bin/pip", "install", "--editable", "."], check=True
    )


@_register
def lock(cfg):
    """Use pip-compile to generate package hashes from setup.py and write them into requirements.txt."""
    subprocess.run([cfg.venv_path / "bin/pip", "install", "pip-tools"], check=True)
    subprocess.run(
        [
            cfg.venv_path / "bin/pip-compile",
            "--generate-hashes",
            "--output-file",
            "requirements.txt",
            "setup.py",
        ],
        check=True,
    )
    subprocess.run(
        [
            cfg.venv_path / "bin/pip-compile",
            "--generate-hashes",
            "--output-file",
            "dev-requirements.txt",
            "setup.py",
            "dev-requirements.in",
        ],
        check=True,
    )


@_register
def build(cfg):
    """Build source and binary distributions."""
    subprocess.run(
        [cfg.venv_path / "bin/python", "setup.py", "sdist", "bdist_wheel"], check=True
    )


@_register
def upload(cfg):
    """Upload the distributions to PyPI."""
    subprocess.run([cfg.venv_path / "bin/python", "-m", "pip", "install", "twine"])
    dists = [str(path) for path in pathlib.Path("dist").iterdir()]
    subprocess.run([cfg.venv_path / "bin/twine", "upload", *dists], check=True)


def _get_default_venv_path():
    """Get the default path of the venv."""
    venv_path = os.environ.get("VENV_PATH")
    if venv_path:
        return pathlib.Path(venv_path)

    workon_home = os.environ.get("WORKON_HOME")
    if workon_home is not None:
        project_name = pathlib.Path(os.getcwd()).name
        return pathlib.Path(workon_home) / project_name

    return pathlib.Path().resolve() / "venv"


def cli():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--venv",
        default=_get_default_venv_path(),
        type=pathlib.Path,
        help="Path of the venv directory. Defaults, in order: $VENV_PATH, $WORKON_HOME/[current directory name], venv",
    )

    subparsers = parser.add_subparsers(dest="command_name")
    for name, function in _register.registered.items():
        subparsers.add_parser(name, help=function.__doc__)

    args = parser.parse_args()
    function = _register.registered[args.command_name]
    cfg = types.SimpleNamespace()
    cfg.venv_path = args.venv
    function(cfg)


if __name__ == "__main__":
    cli()
