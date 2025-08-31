#!/bin/bash

echo "Installing ECAPA-TDNN speaker recognition dependencies using Poetry..."

# Check if Poetry is available
if ! command -v poetry &> /dev/null; then
    echo "Error: Poetry is required but not installed."
    echo "Please install Poetry first: https://python-poetry.org/docs/#installation"
    exit 1
fi

# Check if we're in a Poetry project
if [ ! -f "pyproject.toml" ]; then
    echo "Error: Not in a Poetry project directory (pyproject.toml not found)"
    exit 1
fi

echo "Installing dependencies using Poetry..."
poetry install

echo "Installing additional ECAPA dependencies..."
poetry add torch torchaudio speechbrain librosa scipy

echo "Testing ECAPA model download..."
poetry run python3 test_ecapa.py

echo ""
echo "Installation completed!"
echo ""
echo "To test the system, run:"
echo "poetry run python3 dev-sandbox.py"
echo ""
echo "Note: The first run will download the ECAPA-TDNN model (~100MB)"
echo "This may take a few minutes depending on your internet connection."
