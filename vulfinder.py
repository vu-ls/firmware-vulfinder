import os
import re
import subprocess

# Define folders typically containing web content and patterns to search for potential injections
webfolders = ["bin", "www", "cgi", "htdocs", "scripts", "includes", "config", "src", "lib", "public"]

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
        # Search each pattern in the file
        for pattern in injections:
            command = pattern['pattern']
            result = subprocess.run(['grep', '-E', '-n', command, file_path], stdout=subprocess.PIPE, text=True)
            run_command = f"grep -E -n '{command}' {file_path}"
            if result.stdout:
                print(result.stdout)
                # Process the results from grep
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    # Extract line number and matching line
                    match = re.match(r'(\d+):(.*)', line)
                    if match:
                        line_number = match.group(1)
                        line_content = match.group(2)
                        # Format the matches for better readability
                        if re.search(command, line_content):
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
        result = subprocess.run(['file', file_path], stdout=subprocess.PIPE, text=True)
        return 'python' in result.stdout.lower()
    except Exception as e:
        print(f"Error checking file type: {file_path} - {e}")
        return False

def is_executable_script(file_path):
    """Check if a file is an executable script."""
    try:
        result = subprocess.run(['file', file_path], stdout=subprocess.PIPE, text=True)
        return 'script' in result.stdout.lower() and 'executable' in result.stdout.lower()
    except Exception as e:
        print(f"Error checking file type: {file_path} - {e}")
        return False

def find_command_injection(path) -> list:
    """Find and report potential command injections in web scripts."""
    results = []
    # Traverse the directory tree
    for root, subdirs, files in os.walk(path):
        for subdir in subdirs:
            if subdir in webfolders:
                dir_path = os.path.join(root, subdir) 
                for file_name in files:
                    file_path = os.path.join(root, file_name)
                    if is_executable_script(file_path):
                        matches = search_for_command_injections(file_path, exec_injections)
                        if matches:
                            results.extend(matches)
                    if is_python_script(file_path):
                        matches = search_for_command_injections(file_path, python_injections)
                        if matches:
                            results.extend(matches)
    return results