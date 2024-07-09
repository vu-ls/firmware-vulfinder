import os
import shutil
from .utils import run_binwalk_with_timeout, parse_binwalk_output, dd_extract, mount_fs
from image import Image

class UnknownImage(Image):
    def __init__(self, path):
        super().__init__(path, "Unknown", False, None)
        
    def extract_unknown(path, edir):
        # Try to extract using binwalk
        if run_binwalk_with_timeout(path, edir, 40):
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
    
    # Using cpio assumption, can change or add more options later\
    def move_root(curdir, mount_dir):
        for root, subdirs, files in os.walk(curdir):
            if 'cpio-root' in subdirs:
                src_dir = os.path.join(root, 'cpio-root')
                shutil.move(src_dir, os.path.join(str(mount_dir), 'cpio-root'))
                print("mount_dir:", mount_dir)
                if os.listdir(mount_dir):
                    print("Successfully mounted the cpio-root!")
                    return mount_dir
        return None

    def mount_unknownFS(self, path, fs_type, mount_dir):
        mount_fs(path, fs_type, mount_dir)
        if os.listdir(path) is not None:
            self.mounted = True