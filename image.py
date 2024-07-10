from abc import ABC
import os
import subprocess
from constants import mount_dir
from extraction.extractor import extract_filesystem
from extraction.utils import print_filesystem, run_binwalk_with_timeout, parse_binwalk_output, dd_extract, mount_fs, move_root

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
    def printFS(self):
        return print_filesystem(mount_dir)
    def mount_fs(self, path, fs_type, mount_dir):
        mount_fs(path, fs_type, mount_dir)
        if os.listdir(mount_dir) is not None:
            self.mounted = True
    def move_root(self, curdir, mount_dir):
        pass
    def extract_fs(self, path, edir):
        pass

    # def get_kernel_version(self):
    #     return find_kernel_version(mount_dir)

class SquashImage(Image):
    def __init__(self, path):
        super().__init__(path, "Squash", False, None)

    def extract_fs(self, path, edir):
        # Try to extract using binwalk
        if run_binwalk_with_timeout(path, edir, 300):
            return edir

        # If binwalk times out, use dd to extract the .squashfs file
        offset, size = parse_binwalk_output(path, "Squashfs")
        if offset is not None and size is not None:
            output_file = os.path.join(edir, "extracted.squashfs")
            dd_extract(path, offset, size, output_file)
            return edir
        
        # Last place to look is for more compressed data, usually the file system is
        # compressed into a lzma or xz file
        else:
            offset, size = parse_binwalk_output(path, "compressed data")
            if offset is not None and size is not None:
                data_file = os.path.join(edir, "extracted.lzma")
                dd_extract(path, offset, size, data_file)
                # Return the same directory we started in, since that is where the file will be
                return edir
            
        print(f"Extraction failed: could not find Squash filesystem in {path}")
        return None

    def unsquashFS(curdir, mount_dir):
        for root, subdirs, files in os.walk(curdir):
            for f in files:
                if f.endswith('.squashfs') or f.endswith('.sqfs'):
                    squashfs_path = os.path.join(root, f)
                    try:
                        print('trying to unsquash')
                        unsquash_command = f"unsquashfs -d {mount_dir} {squashfs_path}"
                        subprocess.run(unsquash_command, shell=True, check=True)
                        print('ran unsquash command')
                        if os.listdir(mount_dir):
                            print("Successfully mounted the squashfs!")
                            return mount_dir
                    except subprocess.CalledProcessError as err:
                        print(f"Failed to unsquash: {err}")
                        return None

        print("Could not find squashfs-root or suitable squashfs file to mount.")
        return None
    
    def move_root(self, curdir, mount_dir):
        move_root(self, curdir, mount_dir, "squashfs-root")

class UnknownImage(Image):
    def __init__(self, path):
        super().__init__(path, "Unknown", False, None)
        
    def extract_fs(self, path, edir):
        # Try to extract using binwalk
        if run_binwalk_with_timeout(path, edir, 300):
            return edir
        print("binwalk failed")
        # If binwalk times out, use dd to extract the file
        offset, size = parse_binwalk_output(path, "file system")
        if offset is not None and size is not None:
            unknown_file = os.path.join(edir, "extracted")
            dd_extract(path, offset, size, unknown_file)
            return edir
        
        # Last place to look is for more compressed data
        else:
            offset, size = parse_binwalk_output(path, "compressed data")
            if offset is not None and size is not None:
                data_file = os.path.join(edir, "extracted")
                dd_extract(path, offset, size, data_file)
                # Return the same directory we started in, since that is where the file will be
                return edir
            
        print(f"Extraction failed: could not find (unknown type) filesystem in {path}")
        return None
    
    def move_root(self, curdir, mount_dir):
        move_root(self, curdir, mount_dir, "cpio-root")

# Return concrete image based on file name
# Implement additional logic to find type of image
def create_image(path):
    filename = os.path.basename(path).lower()
    if "squash" in filename:
        return SquashImage(path)
    else:
        return UnknownImage(path)