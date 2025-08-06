# Voice Command Station

A simple Python application built with Poetry for voice command processing.

## Features

- Simple hello world functionality
- Command-line interface
- Comprehensive test suite
- Poetry-based dependency management

## Installation

This project uses Poetry for dependency management. Make sure you have Poetry installed:

```bash
# Install Poetry (if not already installed)
curl -sSL https://install.python-poetry.org | python3 -
```

Then install the project dependencies:

```bash
poetry install
```

## Usage

### Basic Usage

Run the application with default settings:

```bash
poetry run voice-command-station
```

This will output:
```
Hello, World! Welcome to Voice Command Station!
Version: 0.1.0
Ready to process voice commands!
```

### With Custom Name

You can provide a custom name as a command-line argument:

```bash
poetry run voice-command-station Alice
```

This will output:
```
Hello, Alice! Welcome to Voice Command Station!
Version: 0.1.0
Ready to process voice commands!
```

## Development

### Running Tests

Run the test suite:

```bash
poetry run pytest
```

Run tests with coverage:

```bash
poetry run pytest --cov=voice_command_station
```

### Project Structure

```
voice-command-station/
├── voice_command_station/
│   ├── __init__.py
│   └── main.py
├── tests/
│   ├── __init__.py
│   └── test_main.py
├── pyproject.toml
└── README.md
```

## Requirements

- Python 3.8 or higher
- Poetry for dependency management

## License

This project is open source and available under the MIT License.