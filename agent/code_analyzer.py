"""Code analysis module for the local coding agent."""

import os
import ast
import re
import json


def detect_language(filename):
    """Detect programming language from file extension."""
    ext_map = {
        ".py": "python", ".js": "javascript", ".ts": "typescript",
        ".jsx": "jsx", ".tsx": "tsx", ".java": "java",
        ".c": "c", ".cpp": "cpp", ".h": "c-header", ".hpp": "cpp-header",
        ".go": "go", ".rs": "rust", ".rb": "ruby",
        ".php": "php", ".swift": "swift", ".kt": "kotlin",
        ".cs": "csharp", ".sh": "bash", ".bash": "bash",
        ".html": "html", ".css": "css", ".scss": "scss",
        ".json": "json", ".yaml": "yaml", ".yml": "yaml",
        ".xml": "xml", ".md": "markdown", ".sql": "sql",
        ".dockerfile": "dockerfile", ".toml": "toml",
    }
    _, ext = os.path.splitext(filename.lower())
    if os.path.basename(filename).lower() == "dockerfile":
        return "dockerfile"
    if os.path.basename(filename).lower() == "makefile":
        return "makefile"
    return ext_map.get(ext, "text")


def analyze_python_file(filepath):
    """Analyze a Python file using AST."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source, filename=filepath)
    except (SyntaxError, FileNotFoundError) as e:
        return {"error": str(e)}

    analysis = {
        "classes": [],
        "functions": [],
        "imports": [],
        "global_variables": [],
        "issues": [],
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            methods = [n.name for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
            analysis["classes"].append({
                "name": node.name,
                "line": node.lineno,
                "methods": methods,
                "decorators": [_get_decorator_name(d) for d in node.decorator_list],
            })
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not any(node.lineno >= c["line"] for c in analysis["classes"] if "line" in c):
                analysis["functions"].append({
                    "name": node.name,
                    "line": node.lineno,
                    "args": [arg.arg for arg in node.args.args],
                    "is_async": isinstance(node, ast.AsyncFunctionDef),
                    "decorators": [_get_decorator_name(d) for d in node.decorator_list],
                })
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    analysis["imports"].append({"module": alias.name, "alias": alias.asname})
            else:
                for alias in node.names:
                    analysis["imports"].append({
                        "module": f"{node.module}.{alias.name}" if node.module else alias.name,
                        "alias": alias.asname,
                    })

    return analysis


def _get_decorator_name(decorator):
    """Get the name of a decorator node."""
    if isinstance(decorator, ast.Name):
        return decorator.id
    elif isinstance(decorator, ast.Attribute):
        return f"{_get_decorator_name(decorator.value)}.{decorator.attr}"
    elif isinstance(decorator, ast.Call):
        return _get_decorator_name(decorator.func)
    return "unknown"


def analyze_project_structure(directory):
    """Analyze the structure of a project directory."""
    structure = {
        "languages": {},
        "total_files": 0,
        "total_lines": 0,
        "config_files": [],
        "has_git": os.path.exists(os.path.join(directory, ".git")),
        "has_readme": False,
        "build_systems": [],
    }

    config_patterns = {
        "package.json": "npm/node",
        "requirements.txt": "pip/python",
        "setup.py": "setuptools/python",
        "pyproject.toml": "python",
        "Cargo.toml": "cargo/rust",
        "go.mod": "go-modules",
        "pom.xml": "maven/java",
        "build.gradle": "gradle/java",
        "Makefile": "make",
        "CMakeLists.txt": "cmake",
        "Dockerfile": "docker",
        "docker-compose.yml": "docker-compose",
        ".github": "github-actions",
    }

    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d != "node_modules" and d != "__pycache__"]
        for filename in files:
            if filename.startswith("."):
                continue
            filepath = os.path.join(root, filename)
            lang = detect_language(filename)
            structure["languages"][lang] = structure["languages"].get(lang, 0) + 1
            structure["total_files"] += 1

            try:
                with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                    structure["total_lines"] += sum(1 for _ in f)
            except (PermissionError, OSError):
                pass

            if filename.lower() in ("readme.md", "readme.txt", "readme", "readme.rst"):
                structure["has_readme"] = True

            if filename in config_patterns:
                structure["config_files"].append(filename)
                structure["build_systems"].append(config_patterns[filename])

    structure["build_systems"] = list(set(structure["build_systems"]))
    return structure


def find_issues(filepath):
    """Find common code issues in a file."""
    issues = []
    lang = detect_language(filepath)

    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except (FileNotFoundError, PermissionError):
        return issues

    for i, line in enumerate(lines, 1):
        # Check for common issues
        if len(line.rstrip()) > 120:
            issues.append({"line": i, "type": "style", "message": "Line exceeds 120 characters"})
        if line.rstrip() != line.rstrip("\n") and line.rstrip().endswith(" "):
            issues.append({"line": i, "type": "style", "message": "Trailing whitespace"})
        if "TODO" in line or "FIXME" in line or "HACK" in line:
            tag = "TODO" if "TODO" in line else ("FIXME" if "FIXME" in line else "HACK")
            issues.append({"line": i, "type": "note", "message": f"{tag} found: {line.strip()}"})

    if lang == "python":
        try:
            source = "".join(lines)
            compile(source, filepath, "exec")
        except SyntaxError as e:
            issues.append({"line": e.lineno, "type": "error", "message": f"Syntax error: {e.msg}"})

    return issues


def grep_codebase(directory, pattern, file_pattern="*", ignore_case=False):
    """Search codebase for a pattern."""
    import subprocess
    args = ["grep", "-rn"]
    if ignore_case:
        args.append("-i")
    args.extend(["--include", file_pattern, pattern, directory])

    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=30)
        matches = []
        for line in result.stdout.splitlines()[:100]:  # Limit to 100 results
            parts = line.split(":", 2)
            if len(parts) >= 3:
                matches.append({
                    "file": parts[0],
                    "line": int(parts[1]),
                    "content": parts[2].strip(),
                })
        return {"matches": matches, "count": len(matches)}
    except subprocess.TimeoutExpired:
        return {"error": "Search timed out"}
    except FileNotFoundError:
        return {"error": "grep is not installed"}
