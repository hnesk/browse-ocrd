export

SHELL = /bin/bash
PYTHON = python3
PIP = pip3
LOG_LEVEL = INFO
PYTHONIOENCODING=utf8
MIME_DIR=~/.local/share/mime

deps-ubuntu:
	apt install -y libcairo2-dev libgtk-3-dev libglib2.0-dev libgtksourceview-3.0-dev libgirepository1.0-dev pkg-config cmake

deps:
	$(PIP) install -r requirements.txt

install:
	$(PIP) install .

install-xdg-mime: share/mime/packages/ocrd_browser.xml
	mkdir -p $(MIME_DIR)/packages
	cp $< $(MIME_DIR)/packages
	update-mime-database $(MIME_DIR)

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

test: tests/assets
	$(PYTHON) -m unittest discover -s tests


# Clone OCR-D/assets to ./repo/assets
repo/assets:
	mkdir -p $(dir $@)
	git clone https://github.com/OCR-D/assets "$@"


# Setup test assets
tests/assets: repo/assets
	mkdir -p $@
	cp -r -t $@ repo/assets/data/*


.PHONY: assets-clean
# Remove symlinks in test/assets
assets-clean:
	rm -rf test/assets
