import subprocess
import re
import os
import shutil
from constants import *

def binwalk_extraction_with_timeout(image, path, edir, timeout, kernel_search=False) -> str:
    """
    Runs binwalk on the specified firmware image with a timeout. Optionally searches for the kernel version.

    Args:
    image (object): The image object to store kernel version if found.
    path (str): The path to the firmware image.
    edir (str): The directory where extracted files will be stored.
    timeout (int): Timeout for the binwalk process.
    kernel_search (bool): Flag to enable kernel version search.

    Returns:
    str: The directory where the extraction was done.
    """
    cmd = f"binwalk --signature --matryoshka --extract --directory {edir} {path}"
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        stdout, stderr = process.communicate(timeout=timeout)
        print(stderr.decode())
    except subprocess.TimeoutExpired:
        process.kill()
    if kernel_search:
        for line in stdout.splitlines():
            line = line.decode()
            if "kernel version" in line:
                print(f"Found kernel version line: {line}")
                kernel_version = re.search(r'(?i)linux\s*kernel\s*version\s*:?([\d.]+)', line)
                if kernel_version:
                    print(f"Kernel version: {kernel_version.group(1)}")
                    image.kernel_version = kernel_version.group(1)
    return edir

def parse_binwalk_output_for_fs(path, fs_type) -> tuple:
    """
    Parses binwalk output to find filesystem information based on the specified filesystem type.

    Args:
    path (str): The path to the firmware image.
    fs_type (str): The type of filesystem to search for (e.g., SQUASH, CPIO, UNKNOWN).

    Returns:
    tuple: Offset and size of the filesystem if found, otherwise (None, None).
    """
    cmd = f"binwalk {path}"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.stderr:
        print(result.stderr, end='')
    if result.stdout:
        output = result.stdout

    fs_pattern = None
    fs_pattern1 = None
    fs_pattern2 = None

    if fs_type == types.SQUASH:
        fs_pattern = re.compile(fr'(\d+)\s+0x[0-9a-fA-F]+\s+Squashfs filesystem.*?size:\s+(\d+)\s+bytes')
    elif fs_type == types.CPIO:
        fs_pattern = re.compile(fr'(\d+)\s+0x[0-9a-fA-F]+\s+CPIO archive.*?size:\s+(\d+)\s+bytes')
    elif fs_type == types.UNKNOWN:
        fs_pattern = re.compile(fr'(\d+)\s+0x[0-9a-fA-F]+\s+Squashfs filesystem.*?size:\s+(\d+)\s+bytes')
        fs_pattern1 = re.compile(fr'(\d+)\s+0x[0-9a-fA-F]+\s+CPIO archive.*?size:\s+(\d+)\s+bytes')
        fs_pattern2 = re.compile(r'(\d+)\s+0x[0-9a-fA-F]+\s+TROC filesystem,\s+(\d+)\s+file entries')

    patterns = [fs_pattern, fs_pattern1, fs_pattern2]
    for line in output.splitlines():
        for pattern in patterns:
            if pattern:
                match = pattern.search(line)
                if match:
                    offset = int(match.group(1))
                    size = int(match.group(2))
                    return offset, size

    return None, None

def parse_binwalk_output(path, search) -> tuple:
    """
    Parses binwalk output to find specified search term and its size.

    Args:
    path (str): The path to the firmware image.
    search (str): The term to search for in the binwalk output.

    Returns:
    tuple: Offset and size of the found term if found, otherwise (None, None).
    """
    cmd = f"binwalk {path}"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.stderr:
        print(result.stderr, end='')
    if result.stdout:
        output = result.stdout

    pattern = re.compile(fr'(\d+)\s+0x[0-9a-fA-F]+\s+{search}.*?size:\s+(\d+)\s+bytes')

    for line in output.splitlines():
        match = pattern.search(line)
        if match:
            offset = int(match.group(1))
            size = int(match.group(2))
            return offset, size

    return None, None

def dd_extract(path, offset, size, output_file) -> None:
    """
    Extracts a portion of a file using dd command.

    Args:
    path (str): The path to the input file.
    offset (int): The offset to start extraction.
    size (int): The number of bytes to extract.
    output_file (str): The path to the output file.
    """
    dd_cmd = f"dd if={path} skip={offset} count={size} bs=1 of={output_file}"
    result = subprocess.run(dd_cmd, shell=True, check=True)
    if result.stderr:
        print(result.stderr, end='')
    if result.stdout:
        print(result.stdout, end='')

def fs_exists_in_curdir(path, fs_type) -> bool:
    """
    Checks if the specified filesystem type exists in the current directory.

    Args:
    path (str): The directory to search in.
    fs_type (str): The type of filesystem to search for (e.g., SQUASH, CPIO).

    Returns:
    bool: True if the filesystem type is found, False otherwise.
    """
    param = None
    if fs_type == types.SQUASH:
        param = "squashfs-root"
    elif fs_type == types.CPIO:
        param = 'cpio-root'

    if not param:
        return False

    for root, subdirs, _ in os.walk(path):
        if param in subdirs:
            subdir_path = os.path.join(root, param)
            if os.listdir(subdir_path):
                print(f"Found {fs_type} in {subdir_path}")
                return True
    return False

def fs_compressed_exists_in_curdir(path, fs_type) -> bool:
    """
    Checks if the specified compressed filesystem type exists in the current directory.

    Args:
    path (str): The directory to search in.
    fs_type (str): The type of filesystem to search for (e.g., SQUASH, CPIO).

    Returns:
    bool: True if the compressed filesystem type is found, False otherwise.
    """
    suffix = None
    alt_suffix = None
    if fs_type == types.SQUASH:
        suffix = ".squashfs"
        alt_suffix = ".sqfs"
    elif fs_type == types.CPIO:
        suffix = ".cpio"

    if not suffix:
        return False

    for _, _, files in os.walk(path):
        for f in files:
            if f.endswith(suffix) or (alt_suffix and f.endswith(alt_suffix)):
                return True
    return False

def move_root(image, curdir, mount_dir) -> str:
    """
    Moves the root directory of the extracted filesystem to the mount directory.

    Args:
    image (object): The image object to update the mount status.
    curdir (str): The current directory of the extracted filesystem.
    mount_dir (str): The directory where the root filesystem will be moved to.

    Returns:
    str: The mount directory if successful, None otherwise.
    """
    if image.fs_type == types.SQUASH:
        name = "squashfs-root"
    elif image.fs_type == types.CPIO:
        name = "cpio-root"
    for root, subdirs, _ in os.walk(curdir):
        if name in subdirs:
            src_dir = os.path.join(root, name)
            shutil.move(src_dir, os.path.join(str(mount_dir), name))
            if os.listdir(mount_dir):
                print(f"Successfully mounted the {name}!")
                image.mounted = True
                return mount_dir
    return None

def mount_fs(path, fs_type, mount_dir) -> str:
    """
    Mounts the specified filesystem type at the given mount directory.

    Parameters:
    path (str): The path to the filesystem image.
    fs_type (str): The type of filesystem to mount (e.g., SQUASH, CPIO).
    mount_dir (str): The directory where the filesystem will be mounted.

    Returns:
    str: The mount directory.
    """
    type = None
    if fs_type == types.SQUASH:
        type = "squashfs"
    elif fs_type == types.CPIO:
        type = "cpio"

    cmd = f"sudo mount --type={type} --options='loop' --source={path} --target={mount_dir}"
    subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return mount_dir

def clean_dir(directory) -> None:
    """
    Cleans the specified directory by removing its contents and recreating it.

    Args:
    directory (str): The directory to clean.
    """
    unmount_cmd = f"sudo umount -fv {directory}"
    subprocess.run(unmount_cmd, shell=True, capture_output=True, text=True)
    if os.path.exists(directory):
        shutil.rmtree(directory)
    
    os.makedirs(directory)

def print_filesystem(path) -> list:
    """
    Prints the structure of the filesystem.

    Args:
    path (str): The path to the root of the filesystem.

    Returns:
    list: A list of subdirectories in the filesystem.
    """
    dir_arr = []
    for _, subdirs, _ in os.walk(path):
        dir_arr.append(subdirs)
    return dir_arr

def set_kernel_version_from_lib(image, path) -> None:
    """
    Sets the kernel version of the image object based on the /lib/modules directory.

    Args:
    image (object): The image object to update the kernel version.
    path (str): The path to search for the kernel version.
    """
    for root, subdirs, _ in os.walk(path):
        if os.path.basename(root) == "modules" and os.path.dirname(root).split("/")[-1] == "lib":
            for subdir in subdirs:
                if image.kernel_version is None or subdir > image.kernel_version:
                    image.kernel_version = subdir

def identify_fs_type(path) -> str:
    """
    Identifies the filesystem type based on the extracted directory contents.

    Args:
    path (str): The path to the extracted directory.

    Returns:
    str: The identified filesystem type (e.g., SQUASH, CPIO, UNKNOWN).
    """
    if fs_exists_in_curdir(path, types.SQUASH) or fs_compressed_exists_in_curdir(path, types.SQUASH):
        return types.SQUASH
    if fs_exists_in_curdir(path, types.CPIO) or fs_compressed_exists_in_curdir(path, types.CPIO):
        return types.CPIO
    # Add more filesystem type checks if necessary
    return types.UNKNOWN