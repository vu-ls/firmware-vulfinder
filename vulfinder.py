import os
import re

### This tool is designed to find potential command injections in web scripts, and can be expanded on immensely ###

# Define folders typically containing web content and patterns to search for potential injections
webfolders = ["www", "cgi", "htdocs", "scripts", "includes", "config", "src", "public", "bin"]

exec_injections = [
    {
        'pattern': r"'.*\$.*'",
        'description': "Single quotes followed by a dollar sign"
    },
    {
        'pattern': r"\$\(.*\$.*\)",
        'description': "Dollar sign followed by parentheses"
    },
    {
        'pattern': r"shell_exec\('.*\$.*'\);",
        'description': "shell_exec function with a dollar sign"
    },
    {
        'pattern': r"exec\('.*\$.*'\);",
        'description': "exec function with a dollar sign"
    }
]

python_injections = [
    {
        'pattern': r"os.system\('.*\$.*'\);",
        'description': "os.system function with a dollar sign"
    },
    {
        'pattern': r"subprocess.run\('.*\$.*'\);",
        'description': "subprocess.run function with a dollar sign"
    },
    {
        'pattern': r"subprocess.Popen\('.*\$.*'\);",
        'description': "subprocess.Popen function with a dollar sign"
    },
    {
        'pattern': r"os\.exec\('.*\$.*'\)",
        'description': "os.exec function with a dollar sign"
    },
    {
        'pattern': r"os\.popen\('.*\$.*'\)",
        'description': "os.popen function with a dollar sign"
    }
]

def search_for_command_injections(file_path, injections):
    """Search for potential command injections in the file."""
    matches = []
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
            content = file.read()
            for pattern in injections:
                command = pattern['pattern']
                # Find all matches in the file content
                for match in re.finditer(command, content):
                    line_number = content.count('\n', 0, match.start()) + 1
                    matches.append({
                        'file': file_path,
                        'line': line_number,
                        'pattern': pattern['description'],
                    })
    except Exception as e:
        print(f"Error searching file: {file_path} - {e}")
    return matches

def is_python_script(file_path):
    """Check if a file is a Python script."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
            first_line = file.readline()
            return first_line.startswith("#!") and "python" in first_line
    except Exception as e:
        print(f"Error checking file type: {file_path} - {e}")
        return False

def is_executable_script(file_path):
    """Check if a file is an executable script."""
    try:
        return os.access(file_path, os.X_OK)
    except Exception as e:
        print(f"Error checking file type: {file_path} - {e}")
        return False


def find_command_injection(path) -> list:
    """Find and report potential command injections in web scripts."""
    results = []
    # Traverse the directory tree
    for root, _, files in os.walk(path):
        # Determine the current level relative to the starting path
        relative_root = os.path.relpath(root, path)
        root_dirs = relative_root.split(os.sep)

        # Check if we are at the top-level directory and if it is in webfolders
        if len(root_dirs) == 1 and root_dirs[0] in webfolders:
            for file in files:
                file_path = os.path.join(root, file)
                if is_executable_script(file_path):
                    matches = search_for_command_injections(file_path, exec_injections)
                    if matches:
                        results.extend(matches)
                elif is_python_script(file_path):
                    matches = search_for_command_injections(file_path, python_injections)
                    if matches:
                        results.extend(matches)

    return results