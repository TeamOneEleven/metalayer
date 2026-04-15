#!/usr/bin/env bash
# Plugin setup script — runs on SessionStart.
# Installs Python package and QMD into CLAUDE_PLUGIN_DATA if not already done.
set -e

ROOT="${CLAUDE_PLUGIN_ROOT}"
DATA="${CLAUDE_PLUGIN_DATA}"

if [ -z "$ROOT" ] || [ -z "$DATA" ]; then
    # Not running as a plugin — skip
    exit 0
fi

mkdir -p "$DATA"

# Check if setup is needed (compare a stamp file)
STAMP="$DATA/.setup-stamp"
CURRENT_VERSION=$(grep '"version"' "$ROOT/.claude-plugin/plugin.json" | head -1 | sed 's/.*: *"\(.*\)".*/\1/')

if [ -f "$STAMP" ] && [ "$(cat "$STAMP")" = "$CURRENT_VERSION" ]; then
    # Already set up for this version
    exit 0
fi

echo "Setting up Metalayer v${CURRENT_VERSION}..."

# === Prereq checks ===
MISSING=""

if ! command -v uv &> /dev/null; then
    MISSING="${MISSING}\n  - uv (Python package manager): curl -LsSf https://astral.sh/uv/install.sh | sh"
fi

if ! command -v python3 &> /dev/null; then
    MISSING="${MISSING}\n  - Python 3.11+: https://www.python.org/downloads/"
fi

if ! command -v npm &> /dev/null; then
    MISSING="${MISSING}\n  - Node.js + npm (for QMD search): https://nodejs.org/"
fi

if [ -n "$MISSING" ]; then
    echo ""
    echo "============================================================"
    echo "  Metalayer setup: missing prerequisites"
    echo "============================================================"
    echo ""
    echo "  Install these first, then restart your session:"
    echo -e "$MISSING"
    echo ""
    echo "  After installing, Metalayer will set up automatically"
    echo "  on your next session start."
    echo "============================================================"
    echo ""
    exit 0
fi

# === Python venv + package install ===
echo "  Installing Python package..."
cd "$DATA"
uv venv --python 3.11
source .venv/bin/activate
uv pip install -e "$ROOT"

# === QMD (project-local npm install) ===
echo "  Installing QMD search..."
if [ -f "$ROOT/package.json" ]; then
    cp "$ROOT/package.json" "$DATA/package.json"
    cd "$DATA"
    npm install --silent
fi

# Write stamp
echo "$CURRENT_VERSION" > "$STAMP"

echo ""
echo "============================================================"
echo "  Metalayer v${CURRENT_VERSION} ready"
echo "============================================================"
echo ""
echo "  Get started:"
echo "    /metalayer:setup     — configure sources and first import"
echo "    metalayer validate   — check vault integrity"
echo "    metalayer search     — search the vault"
echo ""
echo "  Ask a data question and the agent will follow the"
echo "  ask-data workflow automatically."
echo "============================================================"
