#!/usr/bin/env python3
import os
import fnmatch

# Configuration: Folders and files to always ignore
IGNORE_DIRS = {
    '.git', '__pycache__', 'node_modules', 'venv', '.env', 
    '.idea', '.vscode', 'dist', 'build', 'coverage'
}

IGNORE_FILES = {
    'package-lock.json', 'yarn.lock', '*.lock', '*.pyc', 
    '*.png', '*.jpg', '*.jpeg', '*.gif', '*.ico', '*.svg', 
    '*.exe', '*.dll', '*.so', '*.dylib', '.DS_Store'
}

def should_ignore(name, is_dir=False):
    """Checks if a file or directory should be ignored."""
    if is_dir:
        return name in IGNORE_DIRS
    
    # Check exact matches
    if name in IGNORE_FILES:
        return True
    
    # Check glob patterns (e.g., *.png)
    for pattern in IGNORE_FILES:
        if fnmatch.fnmatch(name, pattern):
            return True
    return False

def is_binary(file_path):
    """Simple heuristic to detect binary files."""
    try:
        with open(file_path, 'tr') as check_file:
            check_file.read()
            return False
    except:
        return True

def generate_tree(start_path):
    """Generates a string representation of the file tree."""
    tree_str = "PROJECT STRUCTURE:\n"
    for root, dirs, files in os.walk(start_path):
        dirs[:] = [d for d in dirs if not should_ignore(d, is_dir=True)]
        level = root.replace(start_path, '').count(os.sep)
        indent = ' ' * 4 * (level)
        tree_str += f"{indent}{os.path.basename(root)}/\n"
        subindent = ' ' * 4 * (level + 1)
        for f in files:
            if not should_ignore(f):
                tree_str += f"{subindent}{f}\n"
    return tree_str

def roll_codebase(start_path):
    """Reads all files and formats them into a prompt."""
    output = []
    
    # 1. Add the file tree
    output.append(generate_tree(start_path))
    output.append("\n" + "="*50 + "\n")
    output.append("FILE CONTENTS:\n")

    # 2. Walk through files
    for root, dirs, files in os.walk(start_path):
        # Modify dirs in-place to skip ignored directories
        dirs[:] = [d for d in dirs if not should_ignore(d, is_dir=True)]

        for file in files:
            if should_ignore(file):
                continue

            file_path = os.path.join(root, file)
            
            # Skip binaries
            if is_binary(file_path):
                print(f"Skipping binary file: {file_path}")
                continue

            # Format the output using XML tags for clarity
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
                output.append(f'<file path="{file_path}">\n{content}\n</file>\n')
            except Exception as e:
                print(f"Error reading {file_path}: {e}")

    return "\n".join(output)

if __name__ == "__main__":
    # Get current directory
    cwd = os.getcwd()
    print(f"Rolling codebase from: {cwd} ...")
    
    full_prompt = roll_codebase(cwd)
    
    # Write to file
    output_filename = "codebase_prompt.txt"
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(full_prompt)
        
    print(f"Done! Prompt saved to: {output_filename}")