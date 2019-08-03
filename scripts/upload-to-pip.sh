#!/bin/sh

set -eu

cd "`dirname $0`"
cd ..

python setup.py sdist

twine upload dist/*
