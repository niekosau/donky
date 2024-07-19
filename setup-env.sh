#!/bin/bash

set -e

VPATH=".venv"
if [ -e /etc/redhat-release ]
then
  sudo dnf -y install python3.9 python3.9-pip binutils make podman
fi
if [ -e /etc/debian_version ]
then
	sudo apt update
  sudo apt install -y git make binutils python3-venv python3-stdeb fakeroot python3-all dh-python
fi
pip3 install virtualenv
python3 -m venv ${VPATH}
${VPATH}/bin/pip install -U pip setuptools
${VPATH}/bin/pip install poetry
make dev
# sudo curl -sSL https://install.python-poetry.org | python3 -
# poetry env use python3.9
# poetry install
# make dev
