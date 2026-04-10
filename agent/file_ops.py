"""File operations module for the local coding agent."""

import os
import shutil
import fnmatch
import difflib


def list_directory(path, show_hidden=False):
    """List contents of a directory with file metadata."""
    entries = []
    try:
        for name in sorted(os.listdir(path)):
            if not show_hidden and name.startswith("."):
                continue
            full_path = os.path.join(path, name)
            entry = {
                "name": name,
                "path": full_path,
                "is_dir": os.path.isdir(full_path),
                "size": os.path.getsize(full_path) if os.path.isfile(full_path) else 0,
            }
            entries.append(entry)
    except PermissionError:
        return {"error": f"Permission denied: {path}"}
    except FileNotFoundError:
        return {"error": f"Directory not found: {path}"}
    return {"entries": entries, "path": os.path.abspath(path)}


def read_file(path):
    """Read file contents with line numbers."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        return {"content": content, "path": os.path.abspath(path), "lines": len(content.splitlines())}
    except FileNotFoundError:
        return {"error": f"File not found: {path}"}
    except PermissionError:
        return {"error": f"Permission denied: {path}"}


def write_file(path, content):
    """Write content to a file, creating parent directories if needed."""
    try:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return {"success": True, "path": os.path.abspath(path)}
    except PermissionError:
        return {"error": f"Permission denied: {path}"}


def edit_file(path, old_str, new_str):
    """Replace a string in a file."""
    result = read_file(path)
    if "error" in result:
        return result
    content = result["content"]
    count = content.count(old_str)
    if count == 0:
        return {"error": f"String not found in {path}"}
    if count > 1:
        return {"error": f"String found {count} times in {path}. Please provide more context to make it unique."}
    new_content = content.replace(old_str, new_str, 1)
    return write_file(path, new_content)


def create_file(path, content=""):
    """Create a new file."""
    if os.path.exists(path):
        return {"error": f"File already exists: {path}"}
    return write_file(path, content)


def delete_file(path):
    """Delete a file or directory."""
    try:
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)
        return {"success": True, "path": path}
    except FileNotFoundError:
        return {"error": f"Not found: {path}"}
    except PermissionError:
        return {"error": f"Permission denied: {path}"}


def search_files(directory, pattern, content_pattern=None):
    """Search for files matching a glob pattern, optionally filtering by content."""
    matches = []
    try:
        for root, dirs, files in os.walk(directory):
            # Skip hidden directories
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for filename in files:
                if fnmatch.fnmatch(filename, pattern):
                    filepath = os.path.join(root, filename)
                    match_entry = {"path": filepath, "name": filename}
                    if content_pattern:
                        try:
                            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                                lines = f.readlines()
                            matching_lines = []
                            for i, line in enumerate(lines, 1):
                                if content_pattern in line:
                                    matching_lines.append({"line": i, "content": line.rstrip()})
                            if matching_lines:
                                match_entry["matches"] = matching_lines
                                matches.append(match_entry)
                        except (PermissionError, OSError):
                            continue
                    else:
                        matches.append(match_entry)
    except PermissionError:
        return {"error": f"Permission denied: {directory}"}
    return {"matches": matches, "count": len(matches)}


def get_diff(original_content, modified_content, filename="file"):
    """Generate a unified diff between two strings."""
    original_lines = original_content.splitlines(keepends=True)
    modified_lines = modified_content.splitlines(keepends=True)
    diff = difflib.unified_diff(
        original_lines, modified_lines,
        fromfile=f"a/{filename}",
        tofile=f"b/{filename}"
    )
    return "".join(diff)
