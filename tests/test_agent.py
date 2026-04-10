"""Tests for the Local Coding Agent."""

import os
import sys
import tempfile
import shutil
import unittest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.file_ops import (
    list_directory, read_file, write_file, edit_file,
    create_file, delete_file, search_files
)
from agent.code_analyzer import (
    detect_language, analyze_project_structure, find_issues
)
from agent.git_ops import is_git_repo
from agent.agent_core import AgentCore


class TestFileOps(unittest.TestCase):
    """Tests for file operations."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.test_dir, "test.txt")
        with open(self.test_file, "w") as f:
            f.write("Hello, World!\nLine 2\nLine 3\n")

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_list_directory(self):
        result = list_directory(self.test_dir)
        self.assertIn("entries", result)
        self.assertEqual(len(result["entries"]), 1)
        self.assertEqual(result["entries"][0]["name"], "test.txt")

    def test_read_file(self):
        result = read_file(self.test_file)
        self.assertIn("content", result)
        self.assertEqual(result["content"], "Hello, World!\nLine 2\nLine 3\n")
        self.assertEqual(result["lines"], 3)

    def test_read_file_not_found(self):
        result = read_file("/nonexistent/file.txt")
        self.assertIn("error", result)

    def test_write_file(self):
        new_file = os.path.join(self.test_dir, "new.txt")
        result = write_file(new_file, "New content")
        self.assertTrue(result.get("success"))
        with open(new_file) as f:
            self.assertEqual(f.read(), "New content")

    def test_edit_file(self):
        result = edit_file(self.test_file, "Hello, World!", "Hi there!")
        self.assertTrue(result.get("success"))
        with open(self.test_file) as f:
            content = f.read()
        self.assertIn("Hi there!", content)
        self.assertNotIn("Hello, World!", content)

    def test_edit_file_not_found(self):
        result = edit_file(self.test_file, "nonexistent string", "replacement")
        self.assertIn("error", result)

    def test_create_file(self):
        new_file = os.path.join(self.test_dir, "created.txt")
        result = create_file(new_file, "Created content")
        self.assertTrue(result.get("success"))
        self.assertTrue(os.path.exists(new_file))

    def test_create_file_exists(self):
        result = create_file(self.test_file, "content")
        self.assertIn("error", result)

    def test_delete_file(self):
        result = delete_file(self.test_file)
        self.assertTrue(result.get("success"))
        self.assertFalse(os.path.exists(self.test_file))

    def test_search_files(self):
        result = search_files(self.test_dir, "*.txt")
        self.assertEqual(result["count"], 1)

    def test_search_files_with_content(self):
        result = search_files(self.test_dir, "*.txt", "Hello")
        self.assertEqual(result["count"], 1)
        self.assertTrue(len(result["matches"][0]["matches"]) > 0)


class TestCodeAnalyzer(unittest.TestCase):
    """Tests for code analyzer."""

    def test_detect_language(self):
        self.assertEqual(detect_language("test.py"), "python")
        self.assertEqual(detect_language("test.js"), "javascript")
        self.assertEqual(detect_language("test.go"), "go")
        self.assertEqual(detect_language("test.rs"), "rust")
        self.assertEqual(detect_language("test.unknown"), "text")
        self.assertEqual(detect_language("Dockerfile"), "dockerfile")
        self.assertEqual(detect_language("Makefile"), "makefile")

    def test_analyze_project_structure(self):
        test_dir = tempfile.mkdtemp()
        try:
            # Create some test files
            with open(os.path.join(test_dir, "main.py"), "w") as f:
                f.write("print('hello')\n")
            with open(os.path.join(test_dir, "README.md"), "w") as f:
                f.write("# Test\n")

            result = analyze_project_structure(test_dir)
            self.assertGreater(result["total_files"], 0)
            self.assertIn("python", result["languages"])
            self.assertTrue(result["has_readme"])
        finally:
            shutil.rmtree(test_dir)

    def test_find_issues(self):
        test_dir = tempfile.mkdtemp()
        test_file = os.path.join(test_dir, "test.py")
        try:
            with open(test_file, "w") as f:
                f.write("# TODO: fix this\n")
                f.write("x = 1\n")

            issues = find_issues(test_file)
            self.assertTrue(any(i["type"] == "note" for i in issues))
        finally:
            shutil.rmtree(test_dir)


class TestAgentCore(unittest.TestCase):
    """Tests for the agent core."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.agent = AgentCore(workspace=self.test_dir)
        # Create a test file
        with open(os.path.join(self.test_dir, "test.py"), "w") as f:
            f.write("def hello():\n    print('hello')\n")

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_set_workspace(self):
        result = self.agent.set_workspace(self.test_dir)
        self.assertTrue(result.get("success"))

    def test_set_workspace_invalid(self):
        result = self.agent.set_workspace("/nonexistent/path")
        self.assertIn("error", result)

    def test_get_workspace(self):
        result = self.agent.get_workspace()
        self.assertEqual(result["workspace"], self.test_dir)

    def test_execute_list_dir(self):
        result = self.agent.execute_action("list_dir", {})
        self.assertIn("entries", result)

    def test_execute_read_file(self):
        result = self.agent.execute_action("read_file", {"path": "test.py"})
        self.assertIn("content", result)

    def test_execute_unknown_action(self):
        result = self.agent.execute_action("unknown_action", {})
        self.assertIn("error", result)

    def test_execute_run_command(self):
        result = self.agent.execute_action("run_command", {"command": "echo hello"})
        self.assertTrue(result.get("success"))
        self.assertIn("hello", result.get("stdout", ""))

    def test_process_task(self):
        result = self.agent.process_task("Test task")
        self.assertIn("task_id", result)
        self.assertEqual(result["status"], "ready")

    def test_task_history(self):
        self.agent.process_task("Task 1")
        self.agent.process_task("Task 2")
        history = self.agent.get_task_history()
        self.assertEqual(len(history["tasks"]), 2)


class TestGitOps(unittest.TestCase):
    """Tests for git operations."""

    def test_is_git_repo(self):
        # The project root should be a git repo
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.assertTrue(is_git_repo(project_root))

    def test_is_not_git_repo(self):
        test_dir = tempfile.mkdtemp()
        try:
            self.assertFalse(is_git_repo(test_dir))
        finally:
            shutil.rmtree(test_dir)


if __name__ == "__main__":
    unittest.main()
