# Local Coding Agent

A Linux-based local coding agent tool with a web UI that performs advanced coding tasks on your local codebase. Describe what you want to build, fix, or change — and the agent analyzes your project, manages files, runs commands, and integrates with Git.

## Features

- **Web-based UI** — Modern dark-themed interface with file explorer, code editor, terminal, and diff viewer
- **Task Execution** — Describe coding tasks in natural language and get project analysis and execution plans
- **File Explorer** — Browse, create, edit, and delete files in your project
- **Code Editor** — Built-in editor with line numbers, syntax awareness, and keyboard shortcuts (Ctrl+S to save, Tab for indent)
- **Integrated Terminal** — Run shell commands directly from the UI with command history
- **Git Integration** — View status, diffs, logs, branches, stage files, and commit changes
- **Code Analysis** — Analyze project structure, detect languages, find issues, and search codebases
- **Diff Viewer** — See changes before and after edits with color-coded diff output
- **Real-time Updates** — WebSocket-based communication for live command output

## Quick Start

### Prerequisites

- Linux (Ubuntu/Debian, Fedora, Arch, etc.)
- Python 3.8 or higher
- pip (Python package manager)
- Git (for version control features)

### Installation

```bash
# Clone the repository
git clone https://github.com/yiannischarlie05-netizen/Agent.git
cd Agent

# Run the install script
chmod +x install.sh
./install.sh

# Activate the virtual environment
source venv/bin/activate
```

### Running

```bash
# Start with current directory as workspace
local-agent

# Start with a specific project directory
local-agent /path/to/your/project

# Use a custom port
local-agent --port 9000

# Listen on all interfaces (for remote access)
local-agent --host 0.0.0.0

# Enable debug mode
local-agent --debug
```

Then open **http://127.0.0.1:8888** in your browser.

### Manual Installation (without install.sh)

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -e .
local-agent
```

## Usage

### Setting a Workspace
1. Enter your project path in the workspace input field at the top
2. Click **Open** to load the project
3. The file explorer will populate with your project files

### Executing Tasks
1. Type a task description in the **Agent Task** area (e.g., "Analyze this project and find potential bugs")
2. Press **Ctrl+Enter** or click **Execute Task**
3. View results in the Output panel

### Editing Files
1. Click any file in the file explorer to open it in the editor
2. Make changes and press **Ctrl+S** to save
3. View diffs in the **Diff View** tab

### Running Commands
1. Switch to the **Terminal** tab
2. Type commands and press **Enter**
3. Use **Up/Down** arrows for command history
4. Use **Quick Commands** in the right sidebar for common operations

### Git Operations
1. Click **Git** in the header to view status, diff, and recent commits
2. Use quick commands or the terminal for git operations

## Architecture

```
Agent/
├── agent/                    # Python backend package
│   ├── __init__.py
│   ├── app.py               # Flask web application & API routes
│   ├── agent_core.py        # Core agent engine & task orchestration
│   ├── file_ops.py          # File system operations
│   ├── git_ops.py           # Git integration
│   ├── code_analyzer.py     # Code analysis & project structure
│   ├── task_runner.py       # Shell command execution
│   ├── templates/
│   │   └── index.html       # Main UI template
│   └── static/
│       ├── css/style.css     # UI styles (Catppuccin theme)
│       └── js/app.js         # Frontend application logic
├── bin/
│   ├── local-agent           # CLI entry point
│   └── local_agent_cli.py    # CLI module
├── tests/
│   └── test_agent.py         # Unit tests
├── requirements.txt          # Python dependencies
├── setup.py                  # Package setup
├── install.sh                # Installation script
└── README.md                 # This file
```

## API Reference

### REST Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/workspace` | Get current workspace |
| POST | `/api/workspace` | Set workspace directory |
| POST | `/api/action` | Execute an agent action |
| POST | `/api/task` | Process a high-level task |
| GET | `/api/history` | Get task history |
| GET | `/api/files?path=` | List directory contents |
| GET | `/api/file?path=` | Read a file |
| PUT | `/api/file` | Write to a file |
| POST | `/api/file` | Create a new file |
| DELETE | `/api/file?path=` | Delete a file |
| POST | `/api/search` | Search files by name/content |
| POST | `/api/grep` | Grep codebase |
| GET | `/api/analyze` | Analyze project structure |
| GET | `/api/issues?path=` | Find code issues |
| GET/POST | `/api/git/<action>` | Git operations |

### Agent Actions

| Action | Description |
|--------|-------------|
| `list_dir` | List directory contents |
| `read_file` | Read file contents |
| `write_file` | Write to a file |
| `edit_file` | Replace string in a file |
| `create_file` | Create a new file |
| `delete_file` | Delete a file |
| `search_files` | Search for files by pattern |
| `git_status` | Get git status |
| `git_diff` | Get git diff |
| `git_log` | Get git log |
| `git_branch` | List branches |
| `git_add` | Stage files |
| `git_commit` | Create a commit |
| `analyze_project` | Analyze project structure |
| `analyze_file` | Analyze a single file |
| `find_issues` | Find code issues |
| `grep` | Search codebase by pattern |
| `run_command` | Run a shell command |

## Running Tests

```bash
source venv/bin/activate
python -m pytest tests/ -v
```

## License

MIT License
