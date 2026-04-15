#!/bin/bash
set -e

echo "Setting up Metalayer..."
echo ""

# === Prereq checks ===
MISSING=""

if ! command -v uv &> /dev/null; then
    MISSING="${MISSING}\n  - uv (Python package manager): curl -LsSf https://astral.sh/uv/install.sh | sh"
fi

if ! command -v npm &> /dev/null; then
    MISSING="${MISSING}\n  - Node.js + npm (for QMD search): https://nodejs.org/"
fi

if [ -n "$MISSING" ]; then
    echo "Missing prerequisites. Install these first:"
    echo -e "$MISSING"
    echo ""
    echo "Then re-run: ./setup.sh"
    exit 1
fi

# Python environment
uv venv --python 3.11
source .venv/bin/activate
uv pip install -e .

# Initialize vault, install QMD, configure search
metalayer init

echo ""
echo "Metalayer installed. Open Claude Code in this directory and ask"
echo "it to connect your data source — it will walk you through setup."
echo ""
echo "  source .venv/bin/activate"
echo "  claude"
echo ""
