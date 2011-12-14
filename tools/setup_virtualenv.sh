#!/bin/bash

topdir=$(dirname $0)/../
cd $topdir

rm -rf .venv
virtualenv --no-site-packages .venv
.venv/bin/pip install -r tools/pip-requirements.txt
