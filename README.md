# Filesystem Vulfinder
## Description
Beta version of firmware analysis tool. Uses binwalk and file decompression tools to extract squash-fs, CPIO-fs, and other filesystems. Preliminary capabilities:
* Extracts filesystem from firmware image
* Identifies type of filesystem
* Mounts filesystem
* Identifies kernel version
* Identifies command injection vulnerabilities present in file system

## Installation
```
git clone https://github.com/jdavey-analygence/firmware-analysis.git
cd firmware-analysis
chmod +x build.sh
./build.sh
```
You will be prompted to enter a file path for extracted files.

Enter an absolute file path, like "/Users/jacob/firmware-extraction"
## Setup
Run interface.py (with IDE or enter `python interface.py` in terminal)
