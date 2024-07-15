from abc import ABC, abstractmethod
import os
import subprocess
from constants import mount_dir
from extractor import extract_filesystem
from utils import *

class Image(ABC):
    """Abstract Image class representing a firmware image."""
    
    def __init__(self, path, fs_type, mounted=False, kernel_version=None):
        self.path = path
        self.fs_type = fs_type
        self.mounted = mounted
        self.kernel_version = kernel_version

    def extractFS(self):
        """Extracts the filesystem using the specified extractor."""
        return extract_filesystem(self, "/Users/jacobdavey/Analygence/firmware-analysis/extracted")

    def is_mounted(self):
        return self.mounted

    def printFS(self):
        """Prints the filesystem contents."""
        return print_filesystem(mount_dir)

    def mount_fs(self, path, fs_type, mount_dir):
        """Mounts the filesystem."""
        mount_fs(path, fs_type, mount_dir)
        if os.listdir(mount_dir):
            self.mounted = True

    @abstractmethod
    def move_root(self, curdir, mount_dir):
        pass

    @abstractmethod
    def extract_fs(self, path, edir, find_kernel=False):
        pass

    def get_kernel_version(self):
        """Gets the kernel version from the filesystem."""
        if self.kernel_version is None:
            set_kernel_version_from_lib(self, mount_dir)
        return self.kernel_version

class SquashImage(Image):
    """Class representing a SquashFS firmware image."""
    
    def __init__(self, path):
        super().__init__(path, "Squash")

    def extract_fs(self, path, edir, find_kernel=False):
        """Extracts the SquashFS filesystem."""
        if binwalk_extraction_with_timeout(self, path, edir, 300, find_kernel):
            return edir

        offset, size = parse_binwalk_output(path, "Squashfs")
        if offset and size:
            output_file = os.path.join(edir, "extracted.squashfs")
            dd_extract(path, offset, size, output_file)
            return edir

        offset, size = parse_binwalk_output(path, "compressed data")
        if offset and size:
            data_file = os.path.join(edir, "extracted.lzma")
            dd_extract(path, offset, size, data_file)
            return edir

        print(f"Extraction failed: could not find Squash filesystem in {path}")
        return None

    @staticmethod
    def unsquashFS(curdir, mount_dir):
        """Unsquashes a SquashFS filesystem."""
        for root, _, files in os.walk(curdir):
            for f in files:
                if f.endswith('.squashfs') or f.endswith('.sqfs'):
                    squashfs_path = os.path.join(root, f)
                    try:
                        unsquash_command = f"unsquashfs -d {mount_dir} {squashfs_path}"
                        subprocess.run(unsquash_command, shell=True, check=True)
                        if os.listdir(mount_dir):
                            print("Successfully mounted the SquashFS!")
                            return mount_dir
                    except subprocess.CalledProcessError as err:
                        print(f"Failed to unsquash: {err}")
                        return None

        print("Could not find suitable SquashFS file to mount.")
        return None

    def move_root(self, curdir, mount_dir):
        """Moves the SquashFS root."""
        return move_root(self, curdir, mount_dir, "squashfs-root")

class UnknownImage(Image):
    """Class representing an unknown firmware image type."""
    
    def __init__(self, path):
        super().__init__(path, "Unknown")

    def extract_fs(self, path, edir, find_kernel=False):
        """Extracts an unknown filesystem type."""
        if binwalk_extraction_with_timeout(self, path, edir, 300, find_kernel):
            return edir

        offset, size = parse_binwalk_output(path, "file system")
        if offset and size:
            unknown_file = os.path.join(edir, "extracted")
            dd_extract(path, offset, size, unknown_file)
            return edir

        offset, size = parse_binwalk_output(path, "compressed data")
        if offset and size:
            data_file = os.path.join(edir, "extracted")
            dd_extract(path, offset, size, data_file)
            return edir

        print(f"Extraction failed: could not find (unknown type) filesystem in {path}")
        return None

    def move_root(self, curdir, mount_dir):
        """Moves the unknown root."""
        return move_root(self, curdir, mount_dir, "cpio-root")

def create_image(path):
    """Creates an Image object based on the file name."""
    filename = os.path.basename(path).lower()
    if "squash" in filename:
        return SquashImage(path)
    else:
        return UnknownImage(path)