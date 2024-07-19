import os
import subprocess
from config import mount_dir, final_dir
from extractor import extract_filesystem
from utils import *

class Image():
    """Image class representing a firmware image."""
    
    def __init__(self, path, fs_type, mounted=False, kernel_version=None):
        self.path = path
        self.fs_type = fs_type
        self.mounted = mounted
        self.kernel_version = kernel_version

    def extractFS(self):
        """Extracts the filesystem using the specified extractor."""
        return extract_filesystem(self, mount_dir, final_dir)

    def printFS(self):
        """Prints the filesystem contents."""
        return print_filesystem(mount_dir)
    
    def extract_fs(self, path, edir, find_kernel=False):
        """Extracts the filesystem."""
        if binwalk_extraction_with_timeout(self, path, edir, 300, find_kernel) != path and os.listdir(edir):
            return edir
        else:
        # If binwalk extraction fails, try to extract the filesystem manually
            for _, _, files in os.walk(path):
                for f in files:
                    file_path = os.path.join(path, f)
                    # First check for a filesystem
                    offset, size = parse_binwalk_output_for_fs(file_path, self.fs_type)
                    if offset and size:
                        output_file = os.path.join(edir, "extracted")
                        # Extract the filesystem
                        dd_extract(file_path, offset, size, output_file)
                        new_edir = os.path.join(edir, "extracted")
                        return new_edir
                    # If no filesystem found, check for compressed data
                    offset, size = parse_binwalk_output(file_path, "compressed data")
                    if offset and size:
                        data_file = os.path.join(edir, "extracted")
                        # Extract the compressed data
                        dd_extract(file_path, offset, size, data_file)
                        new_edir = os.path.join(edir, "extracted")
                        return new_edir

            print(f"Extraction failed: could not find filesystem in {path}")
            return None
    
    def mount_fs(self, path, fs_type, mountdir):
        """Mounts the filesystem."""
        mount_fs(path, fs_type, mountdir)
        if os.listdir(mountdir):
            self.mounted = True

    def move_root(self, curdir, mountdir):
        """Moves the root."""
        return move_root(self, curdir, mountdir)

    def get_kernel_version(self):
        """Gets the kernel version from the filesystem."""
        if self.kernel_version is None:
            set_kernel_version_from_lib(self, mount_dir)
        return self.kernel_version
    
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
                        print(f"Failed to decompress CPIO -- {err}")
                        return None

        print("Could not find suitable CPIO file to mount.")
        return None
    
def create_image(path):
    """Creates an Image object based on the file name."""
    filename = os.path.basename(path).lower()
    if "squash" in filename:
        return Image(path, types.SQUASH)
    elif "cpio" in filename:
        return Image(path, types.CPIO)
    else:
        return Image(path, types.UNKNOWN)