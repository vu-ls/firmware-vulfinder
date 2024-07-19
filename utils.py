import subprocess
import re
import os
import shutil
from constants import *

def binwalk_extraction_with_timeout(image, path, edir, timeout, kernel_search=False):
    cmd = f"binwalk --signature --matryoshka --extract --directory {edir} {path}"
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        stdout, _ = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        process.kill()
    # Check for kernel version if needed
    if kernel_search:
        for line in stdout.splitlines():
            line = line.decode()
            if "kernel version" in line:
                print(f"Found kernel version line: {line}")
                kernel_version = re.search(r'(?i)linux\s*kernel\s*version\s*:?([\d.]+)', line)
                if kernel_version:
                    # Returns the group matched by the actual version number (.*)
                    print(f"Kernel version: {kernel_version.group(1)}")
                    image.kernel_version = kernel_version.group(1)
            
    # Return the directory where the extraction was done
    return edir

def parse_binwalk_output_for_fs(path, fs_type):
    cmd = f"binwalk {path}"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
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
            match = pattern.search(line)
            if match:
                offset = int(match.group(1))
                size = int(match.group(2))
                return offset, size

    return None, None

def parse_binwalk_output(path, search):
    cmd = f"binwalk {path}"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    output = result.stdout

    pattern = re.compile(fr'(\d+)\s+0x[0-9a-fA-F]+\s+{search}.*?size:\s+(\d+)\s+bytes')

    for line in output.splitlines():
        match = pattern.search(line)
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
    elif fs_type == types.CPIO:
        param = 'cpio-root'

    if not param:
        return False
    # Try walking current extracted directory
    for root, subdirs, _ in os.walk(path):
        if param in subdirs:
            subdir_path = os.path.join(root, param)
            if os.listdir(subdir_path):
                print(f"Found {fs_type} in {subdir_path}")
                return True
    return False

def fs_compressed_exists_in_curdir(path, fs_type):
    # Determine what to look for by file type
    suffix = None
    alt_suffix = None
    if fs_type == types.SQUASH:
        suffix = ".squashfs"
        alt_suffix = ".sqfs"
    elif fs_type == types.CPIO:
        suffix = ".cpio"

    if not suffix:
        return False
    # Try walking current extracted directory
    for _, _, files in os.walk(path):
        for f in files:
            if f.endswith(suffix) or (alt_suffix and f.endswith(alt_suffix)):
                return True
    return False

def move_root(image, curdir, mount_dir):
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

def mount_fs(path, fs_type, mount_dir):
    type = None
    # Extract initial level
    if fs_type == types.SQUASH:
        type = "squashfs"
    elif fs_type == types.CPIO:
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
    for _, subdirs, _ in os.walk(path):
        dir_arr.append(subdirs)
    return dir_arr

def set_kernel_version_from_lib(image, path):
    for root, subdirs, _ in os.walk(path):
        # Check if the current directory is /lib/modules
        if os.path.basename(root) == "modules" and os.path.dirname(root).split("/")[-1] == "lib":
            image.kernel_version = subdirs

def identify_fs_type(path):
    """Identify the filesystem type based on the extracted directory."""
    if fs_exists_in_curdir(path, types.SQUASH) or fs_compressed_exists_in_curdir(path, types.SQUASH):
        return types.SQUASH
    if fs_exists_in_curdir(path, types.CPIO) or fs_compressed_exists_in_curdir(path, types.CPIO):
        return types.CPIO
    # Add more filesystem type checks if necessary
    return types.UNKNOWN