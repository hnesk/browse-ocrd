export

SHELL = /bin/bash
PYTHON = python3
PIP = pip3
LOG_LEVEL = INFO
PYTHONIOENCODING=utf8

deps-ubuntu:
	apt install -y libgtksourceview-3.0-dev

deps:
	$(PIP) install -r requirements.txt

install:
	$(PIP) install .

clean-build: pyclean
	rm -Rf build dist *.egg-info

pyclean:
	rm -f **/*.pyc
	rm -rf .pytest_cache

build: clean-build
	$(PYTHON) setup.py sdist bdist_wheel

testpypi: clean-build build
	twine upload --repository testpypi ./dist/browse[_-]ocrd*.{tar.gz,whl}

pypi: clean-build build
	twine upload ./dist/browse[_-]ocrd*.{tar.gz,whl}
