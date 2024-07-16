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

    def mount_fs(self, path, fs_type, mountdir):
        """Mounts the filesystem."""
        mount_fs(path, fs_type, mountdir)
        if os.listdir(mountdir):
            self.mounted = True

    @abstractmethod
    def move_root(self, curdir, mountdir):
        pass

    @abstractmethod
    def extract_fs(self, path, edir, find_kernel=False):
        pass

    def get_kernel_version(self):
        """Gets the kernel version from the filesystem."""
        if self.kernel_version is None:
            set_kernel_version_from_lib(self, mount_dir)
        return self.kernel_version
    
    # For dynamic recasting of Image objects based on filesystem type
    def create_image_with_type(path, fs_type):
        """Creates an Image object based on the identified filesystem type."""
        if fs_type == types.SQUASH:
            return SquashImage(path)
        else:
            return UnknownImage(path)

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
    def unsquashFS(curdir, mountdir):
        """Unsquashes a SquashFS filesystem."""
        for root, _, files in os.walk(curdir):
            for f in files:
                if f.endswith('.squashfs') or f.endswith('.sqfs'):
                    squashfs_path = os.path.join(root, f)
                    try:
                        unsquash_command = f"unsquashfs -d {mountdir} {squashfs_path}"
                        subprocess.run(unsquash_command, shell=True, check=True)
                        if os.listdir(mountdir):
                            print("Successfully mounted the SquashFS!")
                            return mountdir
                    except subprocess.CalledProcessError as err:
                        print(f"Failed to unsquash: {err}")
                        return None

        print("Could not find suitable SquashFS file to mount.")
        return None

    def move_root(self, curdir, mountdir):
        """Moves the SquashFS root."""
        return move_root(self, curdir, mountdir, "squashfs-root")

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
    
    @staticmethod
    def decompressCPIO(curdir, mountdir):
        """Decompresses a CPIO filesystem."""
        for root, _, files in os.walk(curdir):
            for f in files:
                if f.endswith('.cpio'):
                    cpio_path = os.path.join(root, f)
                    try:
                        cpio_command = f"tar -xvf {cpio_path} -C {mountdir}"
                        subprocess.run(cpio_command, shell=True, check=True)
                        if os.listdir(mountdir):
                            print("Successfully mounted the SquashFS!")
                            return mountdir
                    except subprocess.CalledProcessError as err:
                        print(f"Failed to unsquash: {err}")
                        return None

        print("Could not find suitable SquashFS file to mount.")
        return None
    
    def move_root(self, curdir, mountdir):
        """Moves the unknown root."""
        return move_root(self, curdir, mountdir, "cpio-root")

def create_image(path):
    """Creates an Image object based on the file name."""
    filename = os.path.basename(path).lower()
    if "squash" in filename:
        return SquashImage(path)
    else:
        return UnknownImage(path)