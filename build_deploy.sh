#!/bin/zsh

rm -rf dist
rm -rf build

python3 setup.py clean --all install clean --all
python3 setup.py sdist bdist_wheel
python3 -m twine upload dist/*