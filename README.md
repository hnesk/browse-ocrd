# OCR-D Browser

An extensible viewer for [OCR-D](https://ocr-d.de/) [mets.xml](https://ocr-d.de/en/spec/mets) files

[![Unit tests](https://github.com/hnesk/browse-ocrd/workflows/Unit%20tests/badge.svg?branch=master)](https://github.com/hnesk/browse-ocrd/actions/workflows/unittest.yml)

## Screenshot

![OCRD Browser with Page and Xml view](docs/screenshot.png)


## Features

- Browse fileGrps and pages, arranging views next to each other for comparison
- PageView: Show original or derived page images with [PAGE-XML](https://ocr-d.de/en/spec/page) annotations overlay, similar to [PageViewer](https://github.com/PRImA-Research-Lab/prima-page-viewer)
- ImageView: Show original or derived images (`AlternativeImage` on any level of the structural hierarchy)
- ImageView: Show multiple images at once for different pages (horizontally) or different segments (vertically), zooming freely
- XmlView: Show raw [PAGE-XML](https://ocr-d.de/en/spec/page) with syntax highlighting, open with [PageViewer](https://github.com/PRImA-Research-Lab/prima-page-viewer)
- TextView: Show concatenated [PAGE-XML](https://ocr-d.de/en/spec/page) text annotation
- DiffView: Show a simple diff comparison between text annotations from different fileGrps  
- HtmlView: Show rendered HTML comparison from [dinglehopper](https://github.com/qurator-spk/dinglehopper) evaluations


## Installation 

In any case you need a venv with a current pip version (>=20), preferably your existing ocrd-venv:

<details>
  <summary>Create a current pip venv:</summary>

```bash
sudo apt install python3-pip python3-venv 
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip setuptools wheel
```
</details>


### From source
```bash
git clone https://github.com/hnesk/browse-ocrd.git 
cd browse-ocrd
sudo make deps-ubuntu
make install
```

### Via pip 

```bash
sudo apt install libcairo2-dev libgirepository1.0-dev
pip install browse-ocrd
```
 
## Usage
```
browse-ocrd ./path/to/mets.xml # or open interactively
```

## Configuration

### Configuration file locations

At startup the following directories a searched for a config file named `ocrd-browser.conf` 

```python
# directories and their default values under Ubuntu 20.04
GLib.get_system_config_dirs()  # '/etc/xdg/xdg-ubuntu/ocrd-browser.conf', '/etc/xdg/ocrd-browser.conf'
GLib.get_user_config_dir()     # '/home/jk/.config/ocrd-browser.conf'  
os.getcwd()                    # './ocrd-browser.conf'
```

### Configuration file syntax

The `ocrd-browser.conf` file is an ini-file with the following keys:
```ini
[FileGroups]
# Preferred fileGrp names for thumbnail display in the Page Browser 
# Comma seperated list of regular expressions
preferredImages = OCR-D-IMG, OCR-D-IMG.*, ORIGINAL

# Each Tool has a section header [Tool XYZ]
# At the moment the only defined tool is "PageViewer"  
[Tool PageViewer]
# (ba)sh commandline to execute with placeholders  
commandline = /usr/bin/java -jar /home/jk/bin/JPageViewer/JPageViewer.jar --resolve-dir {workspace.directory} {file.path.absolute}
```

The `commandline` string will be used as a python format string with the keyword arguments:

* `workspace` : The current `ocrd.Workspace`, all properties get shell escaped (by `shlex.quote`) automatically.
* `file` : The current `ocrd_models.OcrdFile`, all properties get shell escaped (by `shlex.quote`) automatically, also there is an additional property `path` with the properties `absolute` and `relative`, so `{file.path.absolute}` will be replaced by the shell quoted absolute path of the file. 

> Note: You can get PRImA's PageViewer at [Github](https://github.com/PRImA-Research-Lab/prima-page-viewer/releases).
