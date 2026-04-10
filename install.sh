#!/bin/bash
# Install script for Local Coding Agent

set -e

echo "============================================"
echo "  Local Coding Agent - Installer"
echo "============================================"
echo ""

# Check Python version
PYTHON=""
for cmd in python3 python; do
    if command -v "$cmd" &> /dev/null; then
        version=$($cmd --version 2>&1 | grep -oP '\d+\.\d+')
        major=$(echo "$version" | cut -d. -f1)
        minor=$(echo "$version" | cut -d. -f2)
        if [ "$major" -ge 3 ] && [ "$minor" -ge 8 ]; then
            PYTHON="$cmd"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    echo "Error: Python 3.8 or higher is required."
    echo "Install Python 3: sudo apt install python3 python3-pip python3-venv"
    exit 1
fi

echo "Using Python: $PYTHON ($($PYTHON --version))"

# Create virtual environment
if [ ! -d "venv" ]; then
    echo ""
    echo "Creating virtual environment..."
    $PYTHON -m venv venv
fi

echo "Activating virtual environment..."
source venv/bin/activate

echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "Installing Local Coding Agent..."
pip install -e .

echo ""
echo "============================================"
echo "  Installation Complete!"
echo "============================================"
echo ""
echo "Usage:"
echo "  source venv/bin/activate"
echo "  local-agent [workspace_path]"
echo ""
echo "Or run directly:"
echo "  source venv/bin/activate && python -m bin.local_agent_cli [workspace_path]"
echo ""
echo "Open http://127.0.0.1:8888 in your browser"
echo ""
