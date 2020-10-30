# OCR-D Browser

An extensible viewer for [OCR-D](https://ocr-d.de/) mets.xml files 

## Screenshot

![OCRD Browser with two image and one xml view](docs/screenshot.png)

## Installation on Ubuntu 18.04

```
sudo apt install libcairo2-dev libgtk-3-dev libglib2.0-dev libgtksourceview-3.0-dev libgirepository1.0-dev pkg-config cmake
pip install browse-ocrd
```


## Usage
```
browse-ocrd ./path/to/mets.xml
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

