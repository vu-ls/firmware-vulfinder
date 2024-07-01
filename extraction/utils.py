import subprocess
import re
import os
import shutil

def run_binwalk_with_timeout(path, edir, timeout):
    cmd = f"binwalk --signature --matryoshka --extract --directory {edir} {path}"
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        process.kill()
        return False
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
    if fs_type == "Squash":
        param = "squashfs-root"
    elif fs_type == "Initram":
        param = "initram"
    elif fs_type == "JFFS2":
        param = "jffs2"
    elif fs_type == "Unknown":
        # Just using cpio for now, could be anything
        param = 'cpio-root'

    # Try walking curent extracted directory
    for root, subdirs, files in os.walk(path):
        if param in subdirs:
            return True
        
    return False


def fs_compressed_exists_in_curdir(path, fs_type):
    # Determine what to look for by file type
    suffix = None
    alt_suffix = None
    if fs_type == "Squash":
        suffix = ".squashfs"
        alt_suffix = ".sqfs"
    elif fs_type == "Initram":
        suffix = ".initram"
    elif fs_type == "JFFS2":
        suffix = ".jffs2"
    elif fs_type == "Unknown":
        # Just using cpio for now, could be anything
        suffix=".cpio"

    # Try walking curent extracted directory
    for root, subdirs, files in os.walk(path):
        for f in files:
            if f.endswith(suffix) or f.endswith(alt_suffix):
                return True

    return False

# Mount a filesystem based on type
def mount_fs(path, fs_type, mount_dir):
    type = None
    # Extract intial level
    if fs_type == "Squash":
        type = "squashfs"
    elif fs_type == "JFFS2":
        pass
    elif fs_type == "Initram":
        pass
    elif fs_type == "Unknown":
        # Just using cpio for now, could be anything
        type = "cpio"

    cmd = f"sudo mount --type={type} --options='loop' --source={path} --target={mount_dir}"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    output = result.stdout
    return mount_dir

def clean_dir(directory):
    # Remove existing contents in the mount directory and remake it
    unmount_cmd = f"sudo umount -fv {directory}"
    result = subprocess.run(unmount_cmd, shell=True, capture_output=True, text=True)
    output = result.stdout
    
    if os.path.exists(directory):
        shutil.rmtree(directory)
    
    os.makedirs(directory)
