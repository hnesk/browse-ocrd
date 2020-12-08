export

SHELL = /bin/bash
PYTHON = python3
PIP = pip3
LOG_LEVEL = INFO
PYTHONIOENCODING=utf8
SHARE_DIR=~/.local/share

deps-ubuntu:
	apt install -y libcairo2-dev libgtk-3-dev libglib2.0-dev libgtksourceview-3.0-dev libgirepository1.0-dev gir1.2-webkit2-4.0 pkg-config cmake

deps-dev:
	$(PIP) install -r requirements-dev.txt

deps:
	$(PIP) install -r requirements.txt

install:
	$(PIP) install .

install-xdg-mime: share/mime/packages/org.readmachine.ocrd-browser.xml
	mkdir -p $(SHARE_DIR)/mime/packages
	cp $< $(SHARE_DIR)/mime/packages
	update-mime-database $(SHARE_DIR)/mime
	# Maybe better: xdg-mime install --mode user share/mime/packages/org.readmachine.ocrd-browser.xml


install-xdg-applications: share/applications/org.readmachine.ocrd-browser.desktop
	@mkdir -p $(SHARE_DIR)/applications
	@cp $< $(SHARE_DIR)/applications/org.readmachine.ocrd-browser.desktop
	@chmod +x $(SHARE_DIR)/applications/org.readmachine.ocrd-browser.desktop
	@update-desktop-database $(SHARE_DIR)/applications
	# Maybe better: xdg-desktop-menu install --mode user share/applications/org.readmachine.ocrd-browser.desktop
	$(info ### Done! You have to restart nautilus with)
	$(info ###     nautilus -q && nautilus &)
	$(info ### for the changes to have effect)

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

flake8:
	$(PYTHON) -m flake8 ocrd_browser tests

mypy:
	$(PYTHON) -m mypy --show-error-codes  -p ocrd_browser

ci: flake8 mypy test


test: tests/assets
	$(PYTHON) -m xmlrunner discover -v -s tests --output-file $(CURDIR)/unittest.xml

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
