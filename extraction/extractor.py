import os
from extraction.utils import fs_exists_in_curdir, fs_compressed_exists_in_curdir, clean_dir
from constants import mount_dir, types

# Algorithm to recursively extract the file system
def extract_filesystem(Image, final_dir):
    img_path = Image.path
    fs_type = Image.fs_type
    # Remove existing files and unmount the directory
    clean_dir(final_dir) and clean_dir(mount_dir)

    # Working dir is something like "/firmware-analysis/extracted/firmware-image.bin/"
    working_dir = os.path.join(final_dir, os.path.basename(img_path))
    os.makedirs(working_dir, exist_ok=True)
    
    # Working dir is assigned to dir where extraction happens
    # /fimware-analysis/extracted/firmware-image.bin/firmware-image.bin.extracted/
    working_dir = Image.extract_fs(img_path, working_dir)

    if not working_dir:
        raise Exception(f"Failed to extract data from {img_path}")

    # Extract until the file system (root folder or .fs compression) is found
    while not (fs_exists_in_curdir(working_dir, fs_type) or fs_compressed_exists_in_curdir(working_dir, fs_type)):
        # Variable to hold where the new data is coming in
        new_data = working_dir
        # /fimware-analysis/extracted/firmware-image.bin/firmware-image.bin.extracted/34023.xz.extracted/
        working_dir = Image.extract_fs(new_data, working_dir)
        if not working_dir:
            raise Exception(f"Failed to extract data from {new_data}")

    # File system (-root folder) has been found
    if fs_exists_in_curdir(working_dir, fs_type):
        print(f"Filesystem {fs_type} found (uncompressed) in {working_dir}")
        mounted_dir = Image.move_root(working_dir, mount_dir)
        if mounted_dir:
            return mounted_dir

    # File system (.fs file) has been found
    elif fs_compressed_exists_in_curdir(working_dir, fs_type):
        print(f"Filesystem {fs_type} found (compressed) in {working_dir}")
        # A .squashfs or .sqfs file exists in the working_dir directory
        # Try to unsquash it first, then try to mount if unsquash fails
        if fs_type == types.SQUASH:
            mounted_dir = Image.unsquashFS(working_dir, mount_dir)
        if fs_type == types.UNKNOWN or mounted_dir is None:
            mounted_dir = Image.mount_fs(working_dir, fs_type, mount_dir)
        if mounted_dir is not None:
            return mounted_dir
        
    else:
        print(f"Filesystem {fs_type} not found within recursion limit")

    # If extraction did not work, return the final directory
    return final_dir