"""Core agent engine that orchestrates coding tasks."""

import os
import json
import time
import uuid

from agent.file_ops import (
    list_directory, read_file, write_file, edit_file,
    create_file, delete_file, search_files, get_diff
)
from agent.git_ops import (
    git_status, git_diff, git_log, git_branch,
    git_add, git_commit, git_checkout, git_show, is_git_repo
)
from agent.code_analyzer import (
    detect_language, analyze_python_file, analyze_project_structure,
    find_issues, grep_codebase
)
from agent.task_runner import TaskRunner


class AgentCore:
    """The core agent that processes user tasks and executes actions."""

    def __init__(self, workspace=None):
        self.workspace = workspace or os.path.expanduser("~")
        self.task_runner = TaskRunner()
        self.task_history = []
        self.current_task_id = None

    def set_workspace(self, path):
        """Set the current workspace directory."""
        path = os.path.abspath(os.path.expanduser(path))
        if not os.path.isdir(path):
            return {"error": f"Directory not found: {path}"}
        self.workspace = path
        return {"success": True, "workspace": self.workspace}

    def get_workspace(self):
        """Get the current workspace."""
        return {"workspace": self.workspace}

    def execute_action(self, action, params=None):
        """Execute a single agent action."""
        params = params or {}
        action_map = {
            # File operations
            "list_dir": self._action_list_dir,
            "read_file": self._action_read_file,
            "write_file": self._action_write_file,
            "edit_file": self._action_edit_file,
            "create_file": self._action_create_file,
            "delete_file": self._action_delete_file,
            "search_files": self._action_search_files,
            # Git operations
            "git_status": self._action_git_status,
            "git_diff": self._action_git_diff,
            "git_log": self._action_git_log,
            "git_branch": self._action_git_branch,
            "git_add": self._action_git_add,
            "git_commit": self._action_git_commit,
            "git_checkout": self._action_git_checkout,
            "git_show": self._action_git_show,
            # Code analysis
            "analyze_project": self._action_analyze_project,
            "analyze_file": self._action_analyze_file,
            "find_issues": self._action_find_issues,
            "grep": self._action_grep,
            # Command execution
            "run_command": self._action_run_command,
            "run_interactive": self._action_run_interactive,
            "read_output": self._action_read_output,
            "stop_process": self._action_stop_process,
            "list_processes": self._action_list_processes,
        }

        handler = action_map.get(action)
        if not handler:
            return {"error": f"Unknown action: {action}", "available_actions": list(action_map.keys())}

        try:
            result = handler(params)
            self._log_action(action, params, result)
            return result
        except Exception as e:
            error_result = {"error": str(e)}
            self._log_action(action, params, error_result)
            return error_result

    def process_task(self, task_description):
        """Process a high-level task description and return a plan."""
        task_id = str(uuid.uuid4())[:8]
        self.current_task_id = task_id

        task_entry = {
            "id": task_id,
            "description": task_description,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "status": "planning",
            "actions": [],
            "results": [],
        }
        self.task_history.append(task_entry)

        # Analyze the workspace to understand context
        project_info = analyze_project_structure(self.workspace)
        git_info = None
        if is_git_repo(self.workspace):
            git_info = {
                "status": git_status(self.workspace),
                "branch": git_branch(self.workspace),
            }

        plan = {
            "task_id": task_id,
            "description": task_description,
            "workspace": self.workspace,
            "project_info": project_info,
            "git_info": git_info,
            "status": "ready",
        }

        return plan

    def get_task_history(self):
        """Get the history of all tasks."""
        return {"tasks": self.task_history}

    def _resolve_path(self, path):
        """Resolve a path relative to the workspace, ensuring it stays within the workspace."""
        if not path:
            return self.workspace
        if os.path.isabs(path):
            resolved = os.path.realpath(path)
        else:
            resolved = os.path.realpath(os.path.join(self.workspace, path))
        # Ensure the resolved path is within the workspace
        workspace_real = os.path.realpath(self.workspace)
        if not resolved.startswith(workspace_real + os.sep) and resolved != workspace_real:
            raise ValueError(f"Path '{path}' resolves outside the workspace")
        return resolved

    def _log_action(self, action, params, result):
        """Log an action to the current task."""
        if self.current_task_id:
            for task in self.task_history:
                if task["id"] == self.current_task_id:
                    task["actions"].append({
                        "action": action,
                        "params": params,
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    })
                    break

    # === File operation actions ===

    def _action_list_dir(self, params):
        path = self._resolve_path(params.get("path", ""))
        return list_directory(path, params.get("show_hidden", False))

    def _action_read_file(self, params):
        path = self._resolve_path(params.get("path", ""))
        return read_file(path)

    def _action_write_file(self, params):
        path = self._resolve_path(params.get("path", ""))
        return write_file(path, params.get("content", ""))

    def _action_edit_file(self, params):
        path = self._resolve_path(params.get("path", ""))
        return edit_file(path, params.get("old_str", ""), params.get("new_str", ""))

    def _action_create_file(self, params):
        path = self._resolve_path(params.get("path", ""))
        return create_file(path, params.get("content", ""))

    def _action_delete_file(self, params):
        path = self._resolve_path(params.get("path", ""))
        return delete_file(path)

    def _action_search_files(self, params):
        directory = self._resolve_path(params.get("directory", ""))
        return search_files(directory, params.get("pattern", "*"), params.get("content_pattern"))

    # === Git operation actions ===

    def _action_git_status(self, params):
        return git_status(self._resolve_path(params.get("path", "")))

    def _action_git_diff(self, params):
        return git_diff(self._resolve_path(params.get("path", "")), params.get("staged", False))

    def _action_git_log(self, params):
        return git_log(self._resolve_path(params.get("path", "")), params.get("count", 20))

    def _action_git_branch(self, params):
        return git_branch(self._resolve_path(params.get("path", "")))

    def _action_git_add(self, params):
        return git_add(self._resolve_path(params.get("path", "")), params.get("files"))

    def _action_git_commit(self, params):
        return git_commit(self._resolve_path(params.get("path", "")), params.get("message", ""))

    def _action_git_checkout(self, params):
        return git_checkout(
            self._resolve_path(params.get("path", "")),
            params.get("branch", ""),
            params.get("create", False)
        )

    def _action_git_show(self, params):
        return git_show(self._resolve_path(params.get("path", "")), params.get("ref", "HEAD"))

    # === Code analysis actions ===

    def _action_analyze_project(self, params):
        path = self._resolve_path(params.get("path", ""))
        return analyze_project_structure(path)

    def _action_analyze_file(self, params):
        path = self._resolve_path(params.get("path", ""))
        lang = detect_language(path)
        result = {"language": lang, "path": path}
        if lang == "python":
            result["analysis"] = analyze_python_file(path)
        return result

    def _action_find_issues(self, params):
        path = self._resolve_path(params.get("path", ""))
        return {"issues": find_issues(path), "path": path}

    def _action_grep(self, params):
        directory = self._resolve_path(params.get("directory", ""))
        return grep_codebase(
            directory,
            params.get("pattern", ""),
            params.get("file_pattern", "*"),
            params.get("ignore_case", False)
        )

    # === Command execution actions ===

    def _action_run_command(self, params):
        return self.task_runner.run_command(
            params.get("command", ""),
            cwd=self._resolve_path(params.get("cwd", "")),
            timeout=params.get("timeout", 300),
        )

    def _action_run_interactive(self, params):
        return self.task_runner.run_interactive(
            params.get("command", ""),
            cwd=self._resolve_path(params.get("cwd", "")),
        )

    def _action_read_output(self, params):
        return self.task_runner.read_output(params.get("pid", 0))

    def _action_stop_process(self, params):
        return self.task_runner.stop_process(params.get("pid", 0))

    def _action_list_processes(self, params):
        return {"processes": self.task_runner.list_processes()}
