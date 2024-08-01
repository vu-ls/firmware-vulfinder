#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Function to print messages
function print_message() {
    echo "----------------------------------------"
    echo "$1"
    echo "----------------------------------------"
}

function enter_directory() {
    echo "----------------------------------------"
    echo "Please enter the extraction directory path - must be an absolute path."
    read -p "Enter the directory path: " DIRECTORY_PATH
    echo "----------------------------------------"
}

print_message "Starting build process..."

# Determine the operating system type
OS=$(uname -s)
case "$OS" in
    Linux*)     OS_TYPE=Linux;;
    Darwin*)    OS_TYPE=Mac;;
    CYGWIN*|MINGW32*|MSYS*|MINGW*) OS_TYPE=Windows;;
    *)          OS_TYPE="UNKNOWN";;
esac

print_message "Detected operating system: $OS_TYPE"

# Install dependencies based on the OS type
if [ "$OS_TYPE" == "Linux" ]; then
    # Update package lists and install binwalk and squashfs-tools
    sudo apt-get update
    sudo apt-get install -y binwalk squashfs-tools
elif [ "$OS_TYPE" == "Mac" ]; then
    # Check if Homebrew is installed, install if not
    if ! command -v brew &> /dev/null; then
        print_message "Homebrew not found, install homebrew or manually install binwalk and squashfs with your selected package manager."
    fi
    # Install binwalk and squashfs
    brew install binwalk squashfs
elif [ "$OS_TYPE" == "Windows" ]; then
    print_message "Please install binwalk and squashfs manually for Windows."
    print_message "Visit: https://github.com/ReFirmLabs/binwalk for instructions."
    print_message "And for SquashFS tools: https://github.com/plougher/squashfs-tools"
else
    echo "Unsupported OS: $OS"
    exit 1
fi

# Create the config.py file in the current directory
touch config.py

# Initialize choice variable and enter the directory
CHOICE=""
enter_directory

# Validate the directory path and confirm the choice
while [[ -z "$DIRECTORY_PATH" || "$CHOICE" != "y" ]]; do
    if [[ -n "$DIRECTORY_PATH" ]]; then
        print_message "Are you sure you want to extract the files to $DIRECTORY_PATH? (y/n)"
        read -p "Enter your choice: " CHOICE
    fi

    if [[ -z "$DIRECTORY_PATH" || "$CHOICE" != "y" ]]; then
        enter_directory
    fi
done

# Remove trailing slash from directory path if present
DIRECTORY_PATH=${DIRECTORY_PATH%/}

# Create the directory if it doesn't exist
mkdir -p $DIRECTORY_PATH
mkdir -p $DIRECTORY_PATH/mountpoint

# Write the directory path to the config.py file
echo "final_dir = '$DIRECTORY_PATH'" > config.py
echo "mount_dir = '$DIRECTORY_PATH/mountpoint'" >> config.py

print_message "Build process completed successfully!"
