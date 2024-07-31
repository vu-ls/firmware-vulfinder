# Description
Beta version of firmware analysis tool. Uses binwalk and file decompression tools to extract squash-fs, CPIO-fs, and other filesystems. Preliminary capabilities:
* Extracts filesystem from firmware image
* Identifies type of filesystem
* Mounts filesystem
* Identifies kernel version
* Identifies command injection vulnerabilities present in file system

# Installation
```
git clone https://github.com/jdavey-analygence/firmware-analysis.git
cd firmware-analysis
./build.sh
```
# Setup
1) Create config.py file in the repo directory
2) Set constants (found in config-template.py) to chosen directories
   - final_dir must be one directory above mount_dir
3) Run interface.py (with IDE or run `python interface.py` in terminal)
