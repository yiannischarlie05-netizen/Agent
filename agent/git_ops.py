"""Git operations module for the local coding agent."""

import subprocess
import os


def _run_git(args, cwd):
    """Run a git command and return the output."""
    try:
        result = subprocess.run(
            ["git", "--no-pager"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
            "success": result.returncode == 0,
        }
    except FileNotFoundError:
        return {"error": "git is not installed", "success": False}
    except subprocess.TimeoutExpired:
        return {"error": "Git command timed out", "success": False}


def git_status(cwd):
    """Get git status of the working directory."""
    return _run_git(["status", "--short"], cwd)


def git_diff(cwd, staged=False):
    """Get git diff."""
    args = ["diff"]
    if staged:
        args.append("--staged")
    return _run_git(args, cwd)


def git_log(cwd, count=20):
    """Get recent git log."""
    return _run_git(["log", "--oneline", f"-{count}"], cwd)


def git_branch(cwd):
    """List git branches."""
    return _run_git(["branch", "-a"], cwd)


def git_add(cwd, files=None):
    """Stage files."""
    args = ["add"]
    if files:
        args.extend(files)
    else:
        args.append(".")
    return _run_git(args, cwd)


def git_commit(cwd, message):
    """Create a git commit."""
    return _run_git(["commit", "-m", message], cwd)


def git_checkout(cwd, branch, create=False):
    """Checkout a branch."""
    args = ["checkout"]
    if create:
        args.append("-b")
    args.append(branch)
    return _run_git(args, cwd)


def git_stash(cwd, action="push"):
    """Stash or unstash changes."""
    return _run_git(["stash", action], cwd)


def git_show(cwd, ref):
    """Show a git commit."""
    return _run_git(["show", ref], cwd)


def is_git_repo(path):
    """Check if a path is inside a git repository."""
    result = _run_git(["rev-parse", "--is-inside-work-tree"], path)
    return result.get("success", False)
