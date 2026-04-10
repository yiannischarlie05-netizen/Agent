"""Flask web application for the Local Coding Agent."""

import os
import logging

from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit

from agent.agent_core import AgentCore

app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), "templates"),
    static_folder=os.path.join(os.path.dirname(__file__), "static"),
)
app.config["SECRET_KEY"] = os.urandom(24).hex()

socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

logger = logging.getLogger(__name__)

# Global agent instance
agent = AgentCore()


def _sanitize_result(result):
    """Remove sensitive information from results before sending to client."""
    if not isinstance(result, dict):
        return result
    sanitized = dict(result)
    # Remove any traceback information
    sanitized.pop("traceback", None)
    return sanitized


def _safe_jsonify(result):
    """Safely jsonify a result, sanitizing error information."""
    return jsonify(_sanitize_result(result))


# === Web Routes ===

@app.route("/")
def index():
    """Serve the main UI page."""
    return render_template("index.html")


# === REST API Routes ===

@app.route("/api/workspace", methods=["GET"])
def get_workspace():
    """Get current workspace."""
    return _safe_jsonify(agent.get_workspace())


@app.route("/api/workspace", methods=["POST"])
def set_workspace():
    """Set workspace directory."""
    data = request.get_json()
    path = data.get("path", "")
    result = agent.set_workspace(path)
    return _safe_jsonify(result)


@app.route("/api/action", methods=["POST"])
def execute_action():
    """Execute an agent action."""
    data = request.get_json()
    action = data.get("action", "")
    params = data.get("params", {})
    result = agent.execute_action(action, params)
    return _safe_jsonify(result)


@app.route("/api/task", methods=["POST"])
def process_task():
    """Process a high-level task."""
    data = request.get_json()
    description = data.get("description", "")
    result = agent.process_task(description)
    return _safe_jsonify(result)


@app.route("/api/history", methods=["GET"])
def get_history():
    """Get task history."""
    return _safe_jsonify(agent.get_task_history())


@app.route("/api/files", methods=["GET"])
def list_files():
    """List files in a directory."""
    path = request.args.get("path", agent.workspace)
    show_hidden = request.args.get("hidden", "false").lower() == "true"
    result = agent.execute_action("list_dir", {"path": path, "show_hidden": show_hidden})
    return _safe_jsonify(result)


@app.route("/api/file", methods=["GET"])
def read_file_route():
    """Read a file."""
    path = request.args.get("path", "")
    result = agent.execute_action("read_file", {"path": path})
    return _safe_jsonify(result)


@app.route("/api/file", methods=["PUT"])
def write_file_route():
    """Write to a file."""
    data = request.get_json()
    result = agent.execute_action("write_file", {
        "path": data.get("path", ""),
        "content": data.get("content", ""),
    })
    return _safe_jsonify(result)


@app.route("/api/file", methods=["POST"])
def create_file_route():
    """Create a new file."""
    data = request.get_json()
    result = agent.execute_action("create_file", {
        "path": data.get("path", ""),
        "content": data.get("content", ""),
    })
    return _safe_jsonify(result)


@app.route("/api/file", methods=["DELETE"])
def delete_file_route():
    """Delete a file."""
    path = request.args.get("path", "")
    result = agent.execute_action("delete_file", {"path": path})
    return _safe_jsonify(result)


@app.route("/api/search", methods=["POST"])
def search_route():
    """Search files."""
    data = request.get_json()
    result = agent.execute_action("search_files", data)
    return _safe_jsonify(result)


@app.route("/api/grep", methods=["POST"])
def grep_route():
    """Grep codebase."""
    data = request.get_json()
    result = agent.execute_action("grep", data)
    return _safe_jsonify(result)


@app.route("/api/analyze", methods=["GET"])
def analyze_route():
    """Analyze project structure."""
    path = request.args.get("path", "")
    result = agent.execute_action("analyze_project", {"path": path})
    return _safe_jsonify(result)


@app.route("/api/analyze/file", methods=["GET"])
def analyze_file_route():
    """Analyze a single file."""
    path = request.args.get("path", "")
    result = agent.execute_action("analyze_file", {"path": path})
    return _safe_jsonify(result)


@app.route("/api/issues", methods=["GET"])
def find_issues_route():
    """Find issues in a file."""
    path = request.args.get("path", "")
    result = agent.execute_action("find_issues", {"path": path})
    return _safe_jsonify(result)


@app.route("/api/git/<action>", methods=["GET", "POST"])
def git_route(action):
    """Handle git operations."""
    git_actions = {
        "status": "git_status",
        "diff": "git_diff",
        "log": "git_log",
        "branch": "git_branch",
        "add": "git_add",
        "commit": "git_commit",
        "checkout": "git_checkout",
        "show": "git_show",
    }

    agent_action = git_actions.get(action)
    if not agent_action:
        return jsonify({"error": f"Unknown git action: {action}"}), 400

    params = {}
    if request.method == "POST":
        params = request.get_json() or {}
    else:
        params = dict(request.args)

    result = agent.execute_action(agent_action, params)
    return _safe_jsonify(result)


# === WebSocket Events ===

@socketio.on("connect")
def handle_connect():
    """Handle WebSocket connection."""
    emit("connected", {"workspace": agent.workspace})


@socketio.on("run_command")
def handle_run_command(data):
    """Handle command execution via WebSocket."""
    command = data.get("command", "")
    cwd = data.get("cwd", "")

    emit("command_start", {"command": command})

    result = agent.execute_action("run_command", {
        "command": command,
        "cwd": cwd,
        "timeout": data.get("timeout", 300),
    })

    emit("command_result", _sanitize_result(result))


@socketio.on("execute_task")
def handle_task(data):
    """Handle task execution via WebSocket."""
    description = data.get("description", "")

    emit("task_start", {"description": description})

    # First, analyze the project
    plan = agent.process_task(description)
    emit("task_plan", _sanitize_result(plan))

    emit("task_complete", {"task_id": plan.get("task_id")})


def create_app(workspace=None, host="127.0.0.1", port=8888, debug=False):
    """Create and configure the Flask application."""
    if workspace:
        agent.set_workspace(workspace)

    return app, socketio, host, port, debug


def run_app(workspace=None, host="127.0.0.1", port=8888, debug=False):
    """Run the Flask application."""
    if workspace:
        agent.set_workspace(workspace)

    print(f"\n{'='*60}")
    print(f"  Local Coding Agent v1.0.0")
    print(f"  Workspace: {agent.workspace}")
    print(f"  UI: http://{host}:{port}")
    print(f"{'='*60}\n")

    socketio.run(app, host=host, port=port, debug=debug)
