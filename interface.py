import os
import tkinter as tk
from tkinter import filedialog, messagebox
from image import create_image
from utils import clean_dir, identify_fs_type
from constants import final_dir, mount_dir, types

class FileUploadGUI:
    def __init__(self, root):
        # Root setup
        self.root = root
        self.root.title("Firmware Extractor Interface")
        self.root.geometry("1600x800")

        # Initialize instance variables
        self.file_path = None
        self.image = None

        # Set up the UI components
        self.setup_ui()

    def setup_ui(self):
        # Label for the uploaded file
        self.file_label = tk.Label(self.root, text="No file selected", wraplength=550)
        self.file_label.pack(pady=10)

        # Button to upload firmware image
        self.upload_button = tk.Button(self.root, text="Upload Firmware Image", command=self.upload_file)
        self.upload_button.pack(pady=10)

        # Button to identify filesystem type
        self.find_type_button = tk.Button(self.root, text="Identify Filesystem Type", command=self.filesystem_type, state=tk.DISABLED)
        self.find_type_button.pack(pady=10)

        # Button to extract filesystem
        self.extract_fs_button = tk.Button(self.root, text="Extract Filesystem", command=self.extract_filesystem, state=tk.DISABLED)
        self.extract_fs_button.pack(pady=10)

        # Button to print filesystem
        self.print_fs_button = tk.Button(self.root, text="Print Filesystem", command=self.print_filesystem, state=tk.DISABLED)
        self.print_fs_button.pack(pady=20)

        # Button to print kernel version
        self.print_kernel_version_button = tk.Button(self.root, text="Print Kernel Version", command=self.print_kernel_version, state=tk.DISABLED)
        self.print_kernel_version_button.pack(pady=20)

        # Text box to display information
        self.text_box = tk.Text(self.root, wrap=tk.WORD, width=70, height=20)
        self.text_box.pack(pady=10)

    def upload_file(self):
        new_file = filedialog.askopenfilename()
        if new_file:
            self.file_path = new_file
            self.file_label.config(text=f"Selected File: {self.file_path}")
            self.find_type_button.config(state=tk.NORMAL)
            self.extract_fs_button.config(state=tk.DISABLED)
            self.print_fs_button.config(state=tk.DISABLED)
            self.print_kernel_version_button.config(state=tk.DISABLED)
            print('Uploaded file:', self.file_path)

    def filesystem_type(self):
        if not self.file_path:
            return
        try:
            if not self.image or self.image.path != self.file_path:
                self.image = create_image(self.file_path)
                if self.image.fs_type == "Unknown":
                    self.find_image_type()
            self.clear_text_box()
            self.text_box.insert(tk.END, f"File System Type looks like: {self.image.fs_type}\n\n")
            if not self.image.mounted:
                self.extract_fs_button.config(state=tk.NORMAL)
            else:
                self.extract_fs_button.config(state=tk.DISABLED)
                self.print_fs_button.config(state=tk.NORMAL)
                self.print_kernel_version_button.config(state=tk.NORMAL)
        except Exception as e:
            self.show_error("Failed to identify filesystem type", e)

    def find_image_type(self):
        clean_dir(final_dir)
        clean_dir(mount_dir)
        working_dir = os.path.join(final_dir, os.path.basename(self.image.path))
        os.makedirs(working_dir, exist_ok=True)
        working_dir = self.image.extract_fs(self.image.path, final_dir)
        # Identify file system type if not already known
        fs_type = identify_fs_type(working_dir)
        if fs_type != types.UNKNOWN:
            self.image = self.image.create_image_with_type(self.image, fs_type)
        else:
            raise Exception(f"Failed to identify file system type in {working_dir}")

    def extract_filesystem(self):
        if not self.image:
            return
        try:
            extracted_dir = self.image.extractFS()
            self.clear_text_box()
            self.text_box.insert(tk.END, f"Extracted Directory: {extracted_dir}\n")
            if self.image.mounted:
                self.text_box.insert(tk.END, f"Successfully mounted {self.image.fs_type} file system!\n")
                self.print_fs_button.config(state=tk.NORMAL)
                self.print_kernel_version_button.config(state=tk.NORMAL)
                self.extract_fs_button.config(state=tk.DISABLED)
        except Exception as e:
            self.show_error("Failed to extract filesystem", e)

    def print_filesystem(self):
        if not self.image or not self.image.mounted:
            return
        try:
            directories = self.image.printFS()
            self.clear_text_box()
            self.text_box.insert(tk.END, f'Here are the contents of the filesystem:\n{directories}\n')
        except Exception as e:
            self.show_error("Failed to print filesystem", e)

    def print_kernel_version(self):
        if not self.image or not self.image.mounted:
            self.show_error("Filesystem not mounted", "Error: File system has not been mounted!")
            return
        try:
            kernel = self.image.get_kernel_version()
            self.clear_text_box()
            self.text_box.insert(tk.END, f'Here is the kernel version of the filesystem: {kernel}\n')
        except Exception as e:
            self.show_error("Failed to find a kernel version", e)

    def clear_text_box(self):
        self.text_box.delete(1.0, tk.END)

    def show_error(self, title, error):
        messagebox.showerror(title, str(error))


if __name__ == "__main__":
    root = tk.Tk()
    app = FileUploadGUI(root)
    root.mainloop()