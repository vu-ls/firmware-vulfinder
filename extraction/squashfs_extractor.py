import os
import shutil
import subprocess
from .utils import run_binwalk_with_timeout, parse_binwalk_output, dd_extract, mount_fs

def extract_squashfs(path, edir):
    # Try to extract using binwalk
    if run_binwalk_with_timeout(path, edir, 10):
        return edir

    # If binwalk times out, use dd to extract the .squashfs file
    offset, size = parse_binwalk_output(path, "Squashfs")
    if offset is not None and size is not None:
        squashfs_file = os.path.join(edir, "extracted.squashfs")
        dd_extract(path, offset, size, squashfs_file)
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

def move_squashfs_root(curdir, mount_dir):
    for root, subdirs, files in os.walk(curdir):
        if 'squashfs-root' in subdirs:
            src_dir = os.path.join(root, 'squashfs-root')
            shutil.move(src_dir, os.path.join(str(mount_dir), 'squashfs-root'))
            print("mount_dir:", mount_dir)
            if os.listdir(mount_dir):
                print("Successfully mounted the squashfs!")
                return mount_dir
    return None

def mount_SquashFS(path, fs_type, mount_dir):
    mount_fs(path, fs_type, mount_dir)