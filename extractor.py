import os
from utils import *
from constants import types

def extract_filesystem(image, mount_dir, final_dir):
    """
    Recursively extracts the file system from a firmware image.

    Args:
        image (Image): The Image object containing path and fs_type information.
        final_dir (str): The final directory where the extracted files will be placed.

    Returns:
        str: The directory where the file system is mounted, or the final directory if extraction fails.
    """        
    # Clean directories
    clean_dir(final_dir)
    clean_dir(mount_dir)

    # Counter to limit recursion
    counter = 0

    # Extract initial file path to working directory
    # Makes ./extracted/_img.bin.extracted/
    working_dir = image.extract_fs(image.path, final_dir, True)
    working_dir = os.path.join(final_dir, f"_{os.path.basename(image.path)}.extracted")
    print(f"Extracted to {working_dir}")
    if not working_dir or not os.path.isdir(working_dir):
        raise Exception(f"Failed to extract data from {image.path}")
    image.fs_type = identify_fs_type(working_dir)
    fs_type = image.fs_type

    # Recursively extract until file system is found or limit is reached
    while not (fs_exists_in_curdir(working_dir, fs_type) or fs_compressed_exists_in_curdir(working_dir, fs_type)) and counter < 5:
        counter += 1
        new_data = os.path.join(final_dir, "new") 
        working_dir = image.extract_fs(working_dir, new_data)
        if not working_dir:
            raise Exception(f"Failed to extract data from {new_data}")

    mounted_dir = None
    # Handle uncompressed file system
    if fs_exists_in_curdir(working_dir, fs_type):
        print(f"Filesystem {fs_type} found (uncompressed) in {working_dir}")
        mounted_dir = image.move_root(working_dir, mount_dir)
        if mounted_dir:
            return mounted_dir

    # Handle compressed file system if it is not already mounted
    if fs_compressed_exists_in_curdir(working_dir, fs_type) and mounted_dir is None:
        print(f"Filesystem {fs_type} found (compressed) in {working_dir}")
        if fs_type == types.SQUASH:
            mounted_dir = image.unsquashFS(working_dir, mount_dir)
        if fs_type == types.CPIO:
            mounted_dir = image.decompressCPIO(working_dir, mount_dir)
        if not mounted_dir:
            mounted_dir = image.mount_fs(working_dir, fs_type, mount_dir)
        if mounted_dir is not None:
            return mounted_dir

    print(f"Filesystem {fs_type} not found within recursion limit (tried {counter} times)")
    return final_dir