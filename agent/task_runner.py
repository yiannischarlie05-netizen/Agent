"""Task runner module for executing shell commands safely."""

import subprocess
import os
import signal
import threading
import time
import shlex


class TaskRunner:
    """Manages execution of shell commands with timeout and output capture."""

    def __init__(self):
        self._processes = {}
        self._lock = threading.Lock()

    def run_command(self, command, cwd=None, timeout=300, env=None):
        """Run a shell command and return the result."""
        if cwd and not os.path.isdir(cwd):
            return {
                "error": f"Working directory does not exist: {cwd}",
                "success": False,
            }

        merged_env = os.environ.copy()
        if env:
            merged_env.update(env)

        try:
            process = subprocess.Popen(
                command,
                shell=True,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=merged_env,
                preexec_fn=os.setsid,
            )

            pid = process.pid
            with self._lock:
                self._processes[pid] = process

            try:
                stdout, stderr = process.communicate(timeout=timeout)
                return {
                    "stdout": stdout.decode("utf-8", errors="replace"),
                    "stderr": stderr.decode("utf-8", errors="replace"),
                    "returncode": process.returncode,
                    "success": process.returncode == 0,
                    "pid": pid,
                }
            except subprocess.TimeoutExpired:
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                time.sleep(2)
                if process.poll() is None:
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                stdout, stderr = process.communicate()
                return {
                    "stdout": stdout.decode("utf-8", errors="replace"),
                    "stderr": stderr.decode("utf-8", errors="replace"),
                    "returncode": -1,
                    "success": False,
                    "error": f"Command timed out after {timeout} seconds",
                    "pid": pid,
                }
            finally:
                with self._lock:
                    self._processes.pop(pid, None)

        except OSError as e:
            return {"error": str(e), "success": False}

    def run_interactive(self, command, cwd=None, env=None):
        """Start an interactive process and return its PID for streaming."""
        merged_env = os.environ.copy()
        if env:
            merged_env.update(env)

        try:
            process = subprocess.Popen(
                command,
                shell=True,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=merged_env,
                preexec_fn=os.setsid,
            )

            pid = process.pid
            with self._lock:
                self._processes[pid] = process

            return {"pid": pid, "success": True}

        except OSError as e:
            return {"error": str(e), "success": False}

    def read_output(self, pid, timeout=5):
        """Read available output from an interactive process."""
        with self._lock:
            process = self._processes.get(pid)

        if not process:
            return {"error": f"No process with PID {pid}", "success": False}

        output_lines = []
        deadline = time.time() + timeout

        while time.time() < deadline:
            if process.poll() is not None:
                # Process has ended, read remaining output
                remaining = process.stdout.read()
                if remaining:
                    output_lines.append(remaining.decode("utf-8", errors="replace"))
                break

            # Non-blocking read
            try:
                line = process.stdout.readline()
                if line:
                    output_lines.append(line.decode("utf-8", errors="replace"))
                else:
                    time.sleep(0.1)
            except (IOError, OSError):
                break

        return {
            "output": "".join(output_lines),
            "running": process.poll() is None,
            "returncode": process.returncode,
            "success": True,
        }

    def stop_process(self, pid):
        """Stop a running process."""
        with self._lock:
            process = self._processes.get(pid)

        if not process:
            return {"error": f"No process with PID {pid}", "success": False}

        try:
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            time.sleep(2)
            if process.poll() is None:
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)

            with self._lock:
                self._processes.pop(pid, None)

            return {"success": True, "pid": pid}
        except (ProcessLookupError, OSError):
            with self._lock:
                self._processes.pop(pid, None)
            return {"success": True, "pid": pid}

    def list_processes(self):
        """List all tracked processes."""
        with self._lock:
            result = []
            for pid, process in list(self._processes.items()):
                result.append({
                    "pid": pid,
                    "running": process.poll() is None,
                    "returncode": process.returncode,
                })
            return result
