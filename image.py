from abc import ABC, abstractmethod
import os
import subprocess
from constants import mount_dir, final_dir, types
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
        return extract_filesystem(self, final_dir)

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
    @staticmethod
    def create_image_with_type(image, fs_type):
        """Creates an Image object based on the identified filesystem type."""
        if fs_type == types.SQUASH:
            return SquashImage(image.path, image.mounted, image.kernel_version)
        if fs_type == types.CPIO:
            return CPIOImage(image.path, image.mounted, image.kernel_version)
        else:
            return UnknownImage(image.path)

class SquashImage(Image):
    """Class representing a SquashFS firmware image."""
    
    def __init__(self, path, mounted=False, kernel_version=None):
        super().__init__(path, types.SQUASH, mounted, kernel_version)

    def extract_fs(self, path, edir, find_kernel=False):
        """Extracts the SquashFS filesystem."""
        if binwalk_extraction_with_timeout(self, path, edir, 300, find_kernel):
            return edir

        offset, size = parse_binwalk_output_for_fs(path, types.SQUASH)
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

    def unsquashFS(self, curdir, mountdir):
        """Unsquashes a SquashFS filesystem."""
        for root, _, files in os.walk(curdir):
            for f in files:
                if f.endswith('.squashfs') or f.endswith('.sqfs'):
                    squashfs_path = os.path.join(root, f)
                    try:
                        unsquash_command = f"unsquashfs -d {mountdir} {squashfs_path}"
                        subprocess.run(unsquash_command, shell=True, check=True)
                        if os.listdir(mountdir):
                            self.mounted = True
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

class CPIOImage(Image):
    """Class representing a CPIO firmware image."""
    
    def __init__(self, path, mounted=False, kernel_version=None):
        super().__init__(path, types.CPIO, mounted, kernel_version)

    def extract_fs(self, path, edir, find_kernel=False):
        """Extracts the CPIO filesystem."""
        if binwalk_extraction_with_timeout(self, path, edir, 300, find_kernel):
            return edir

        offset, size = parse_binwalk_output_for_fs(path, types.CPIO)
        if offset and size:
            output_file = os.path.join(edir, "extracted.cpio")
            dd_extract(path, offset, size, output_file)
            return edir

        offset, size = parse_binwalk_output(path, "compressed data")
        if offset and size:
            data_file = os.path.join(edir, "extracted")
            dd_extract(path, offset, size, data_file)
            return edir

        print(f"Extraction failed: could not find Squash filesystem in {path}")
        return None

    def decompressCPIO(self, curdir, mountdir):
        """Decompresses a CPIO filesystem."""
        for root, _, files in os.walk(curdir):
            for f in files:
                if f.endswith('.cpio'):
                    cpio_path = os.path.join(root, f)
                    try:
                        cpio_command = f"tar -xvf {cpio_path} -C {mountdir}"
                        subprocess.run(cpio_command, shell=True, check=True)
                        if os.listdir(mountdir):
                            self.mounted = True
                            print("Successfully mounted the CPIO FS!")
                            return mountdir
                    except subprocess.CalledProcessError as err:
                        print(f"Failed to unsquash: {err}")
                        return None

        print("Could not find suitable CPIO file to mount.")
        return None

    def move_root(self, curdir, mountdir):
        """Moves the cpio root."""
        return move_root(self, curdir, mountdir, "cpio-root")

class UnknownImage(Image):
    """Class representing an unknown firmware image type."""
    
    def __init__(self, path):
        super().__init__(path, types.UNKNOWN)

    def extract_fs(self, path, edir, find_kernel=False):
        """Extracts an unknown filesystem type."""
        if binwalk_extraction_with_timeout(self, path, edir, 300, find_kernel):
            return edir

        offset, size = parse_binwalk_output_for_fs(path, types.UNKNOWN)
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

def create_image(path):
    """Creates an Image object based on the file name."""
    filename = os.path.basename(path).lower()
    if "squash" in filename:
        return SquashImage(path)
    elif "cpio" in filename:
        return CPIOImage(path)
    else:
        return UnknownImage(path)