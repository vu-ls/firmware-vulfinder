from abc import ABC
import os
from extraction.extractor import extract_filesystem, is_mounted, print_filesystem, find_kernel_version
from constants import mount_dir

class Image(ABC):
    def __init__(self, path, fs_type):
        self.path = path
        self.fs_type = fs_type
        self.mounted = False

    # Extract file system of any type using extractor
    def extractFS(self):
        return extract_filesystem(self.fs_type, self.path, "/home/jacob/firmware_analysis/extracted")
    def is_mounted(self):
        # /home/jacob/firmware_analysis/extracted/firmware.bin/mountpoint
        self.mounted = is_mounted(mount_dir)
        return self.mounted
    def printFS(self):
        return print_filesystem(mount_dir)
    def get_kernel_version(self):
        return find_kernel_version(mount_dir)

class SquashImage(Image):
    def __init__(self, path):
        super().__init__(path, "Squash")

class JFFS2Image(Image):
    def __init__(self, path):
        super().__init__(path, "JFFS2")

class InitramImage(Image):
    def __init__(self, path):
        super().__init__(path, "Initram")

class UnknownImage(Image):
    def __init__(self, path):
        super().__init__(path, "Unknown")
    
# Return concrete image based on file name
def create_image(path):
    filename = os.path.basename(path).lower()

    if "squash" in filename:
        return SquashImage(path)
    elif "jffs2" in filename:
        return JFFS2Image(path)
    elif "initram" in filename:
        return InitramImage(path)
    else:
        return UnknownImage(path)