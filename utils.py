import subprocess
import re
import os
import shutil
from constants import *

def binwalk_extraction_with_timeout(image, path, edir, timeout, kernel_search=False):
    cmd = f"binwalk --signature --matryoshka --extract --directory {edir} {path}"
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        process.kill()
        return False
    # Check for kernel version if needed
    if kernel_search:
        for line in stdout.splitlines():
            line = line.decode()
            if "Kernel version" in line:
                print(f"Found kernel version line: {line}")
                kernel_version = re.search(r'Kernel version\s*:\s*(.*)', line)
                if kernel_version:
                    # Returns the group matched by the actual version number (.*)
                    print(f"Kernel version: {kernel_version.group(1)}")
                    image.kernel_version = kernel_version.group(1)
    return True

def parse_binwalk_output(path, fs_type):
    cmd = f"binwalk --run-as=root {path}"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    output = result.stdout

    fs_pattern = re.compile(fr'(\d+)\s+0x[0-9a-fA-F]+\s+{fs_type} filesystem.*?size:\s+(\d+)\s+bytes')

    for line in output.splitlines():
        match = fs_pattern.search(line)
        if match:
            offset = int(match.group(1))
            size = int(match.group(2))
            return offset, size

    return None, None

def dd_extract(path, offset, size, output_file):
    dd_cmd = f"dd if={path} skip={offset} count={size} bs=1 of={output_file}"
    subprocess.run(dd_cmd, shell=True, check=True)

def fs_exists_in_curdir(path, fs_type):
    # Determine what to look for by directory name
    param = None
    if fs_type == types.SQUASH:
        param = "squashfs-root"
    elif fs_type == types.UNKNOWN:
        # Just using cpio for now, could be anything
        param = 'root'

    for root, subdirs, files in os.walk(path):
        if param in subdirs:
            subdir_path = os.path.join(root, param)
            if os.listdir(subdir_path):
                return True
    return False

def fs_compressed_exists_in_curdir(path, fs_type):
    # Determine what to look for by file type
    suffix = None
    alt_suffix = ''
    alt_suffix2 = None
    if fs_type == types.SQUASH:
        suffix = ".squashfs"
        alt_suffix = ".sqfs"
    elif fs_type == types.UNKNOWN:
        # Just using cpio for now, could be anything
        suffix = ".cpio"
        alt_suffix = ".squashfs"
        alt_suffix2 = ".sqfs"

    # Try walking current extracted directory
    for root, subdirs, files in os.walk(path):
        for f in files:
            if f.endswith(suffix) or f.endswith(alt_suffix) or (alt_suffix2 and f.endswith(alt_suffix2)):
                return True
            
    return False

def move_root(image, curdir, mount_dir, name):
    for root, subdirs, _ in os.walk(curdir):
        if name in subdirs:
            src_dir = os.path.join(root, name)
            shutil.move(src_dir, os.path.join(str(mount_dir), name))
            print("mount_dir:", mount_dir)
            if os.listdir(mount_dir):
                print(f"Successfully mounted the {name}!")
                image.mounted = True
                return mount_dir
    return None

def mount_fs(path, fs_type, mount_dir):
    type = None
    # Extract initial level
    if fs_type == types.SQUASH:
        type = "squashfs"
    elif fs_type == types.UNKNOWN:
        # Just using cpio for now, could be anything
        type = "cpio"

    cmd = f"sudo mount --type={type} --options='loop' --source={path} --target={mount_dir}"
    subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return mount_dir

def clean_dir(directory):
    # Remove existing contents in the mount directory and remake it
    unmount_cmd = f"sudo umount -fv {directory}"
    subprocess.run(unmount_cmd, shell=True, capture_output=True, text=True)
    
    if os.path.exists(directory):
        shutil.rmtree(directory)
    
    os.makedirs(directory)

def print_filesystem(path):
    dir_arr = []
    for root, subdirs, files in os.walk(path):
        dir_arr.append(subdirs)
    return dir_arr

def set_kernel_version_from_lib(image, path):
    for root, subdirs, files in os.walk(path):
        # Check if the current directory is /lib/modules
        if os.path.basename(root) == "modules" and os.path.dirname(root).split("/")[-1] == "lib":
            image.kernel_version = subdirs

def identify_fs_type(path):
    """Identify the filesystem type based on the extracted directory."""
    if fs_exists_in_curdir(path, types.SQUASH) or fs_compressed_exists_in_curdir(path, types.SQUASH):
        return types.SQUASH
    # Add more filesystem type checks if necessary
    return types.UNKNOWN