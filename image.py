from abc import ABC
import os
from extraction.extractor import extract_filesystem
from constants import mount_dir
from extraction.squashfs import SquashImage
from extraction.unknown import UnknownImage
from extraction.utils import print_filesystem

# Abstract Image class
class Image(ABC):
    def __init__(self, path, fs_type, mounted, kernel_version):
        self.path = path
        self.fs_type = fs_type
        self.mounted = mounted
        self.kernel_version = kernel_version

    # Extract file system of any type using extractor
    def extractFS(self):
        return extract_filesystem(self, "/home/jacob/firmware-analysis/extracted")
    def is_mounted(self):
        return self.mounted
    def printFS():
        return print_filesystem(mount_dir)
    def extract_fs(self, path, edir):
        pass
    def move_root(curdir, mount_dir):
        pass
    def mount_fs(path, fs_type, mount_dir):
        pass

    # def get_kernel_version(self):
    #     return find_kernel_version(mount_dir)
    
# Return concrete image based on file name
# Implement additional logic to find type of image
def create_image(path):
    filename = os.path.basename(path).lower()
    if "squash" in filename:
        return SquashImage(path)
    else:
        return UnknownImage(path)