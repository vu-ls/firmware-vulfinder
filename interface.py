import tkinter as tk
from tkinter import filedialog, messagebox
from image import create_image

class FileUploadGUI:
    def __init__(self, root):

        # Root setup
        self.root = root
        self.root.title("Firmware Extractor Interface")
        self.root.geometry("1600x800")

        # Label for the uploaded file
        self.file_label = tk.Label(root, text="No file selected", wraplength=550)
        self.file_label.pack(pady=10)

        # Button to upload firmware image
        self.upload_button = tk.Button(root, text="Upload Firmware Image", command=self.upload_file)
        self.upload_button.pack(pady=10)

        # Button to identify filesystem type
        self.find_type_button = tk.Button(root, text="Identify Filesystem Type", command=self.filesystem_type, 
                                          state=tk.DISABLED)
        self.find_type_button.pack(pady=10)

        # Button to extract filesystem
        self.extract_fs_button = tk.Button(root, text="Extract Filesystem", command=self.extract_filesystem, 
                                           state=tk.DISABLED)
        self.extract_fs_button.pack(pady=10)

        # Button to print filesystem
        self.print_fs_button = tk.Button(root, text="Print Filesystem", command=self.print_filesystem, 
                                         state=tk.DISABLED)
        self.print_fs_button.pack(pady=20)

        # Button to print kernel version
        # self.print_kernel_version_button = tk.Button(root, text="Print Kernel Version", 
        #                                              command=self.print_kernel_version, state=tk.DISABLED)
        # self.print_kernel_version_button.pack(pady=20)

        # Text box to display information
        self.text_box = tk.Text(root, wrap=tk.WORD, width=70, height=20)
        self.text_box.pack(pady=10)

        self.file_path = None
        self.image = None

    def upload_file(self):
        # Ask for .bin or .img files
        new_file = filedialog.askopenfilename()
        self.file_path = new_file if new_file else self.file_path

        if self.file_path:
            # Set file label to selected file and enable extraction buttons
            self.file_label.config(text=f"Selected File: {self.file_path}")
            self.find_type_button.config(state=tk.NORMAL)
            self.extract_fs_button.config(state=tk.DISABLED)
            self.print_fs_button.config(state=tk.DISABLED)
            self.print_kernel_version_button.config(state=tk.DISABLED)

    def filesystem_type(self):
        if not self.file_path:
            messagebox.showerror("Error", "No file selected!")
            return

        # Clear text box
        self.text_box.delete(1.0, tk.END)

        try:
            # Create the correct Image object based on the file path
            self.image = create_image(self.file_path)
            self.text_box.insert(tk.END, f"Detected File System Type: {self.image.fs_type}\n\n")
            self.extract_fs_button.config(state=tk.NORMAL)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to identify filesystem type:\n{e}")

    def extract_filesystem(self):
        if not self.image:
            messagebox.showerror("Error", "No filesystem type identified!")
            return
        try:
            extracted_dir = self.image.extractFS()
            self.text_box.insert(tk.END, f"Extracted Directory: {extracted_dir}\n")
            if self.image.mounted:
                self.text_box.insert(tk.END, f"Succesfully mounted {self.image.fs_type} file system!")
                self.print_fs_button.config(state=tk.NORMAL)
                self.print_kernel_version_button.config(state=tk.NORMAL)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to extract filesystem:\n{e}")

    def print_filesystem(self):
        if not self.image.mounted:
            messagebox.showerror("Error, file system has not been mounted!")
            return
        try:
            directories = self.image.printFS()
            self.text_box.delete(1.0, tk.END)
            self.text_box.insert(tk.END, f'Here are the contents of the filesystem: {directories}')
        except Exception as e:
            messagebox.showerror("Error", f"Failed to print filesystem\n{e}")

    # def print_kernel_version(self):
    #     if not self.image.mounted:
    #         messagebox.showerror("Error, file system has not been mounted!")
    #         return
    #     try:
    #         kernel_versions = self.image.get_kernel_version()
    #         printable = ','.join(map(str, kernel_versions))
    #         self.text_box.delete(1.0, tk.END)
    #         self.text_box.insert(tk.END, f'Here is the kernel version of the filesystem: {printable}')
    #     except Exception as e:
    #         messagebox.showerror("Error", f"Failed to find a kernel version\n{e}")


if __name__ == "__main__":
    root = tk.Tk()
    app = FileUploadGUI(root)
    root.mainloop()
