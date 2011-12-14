#!/bin/bash
topdir=$(dirname $0)/..
cd $topdir
source .venv/bin/activate
exec "$@"
