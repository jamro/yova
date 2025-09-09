# YOVA Development Environment Setup

This guide will help you set up a complete development environment for YOVA (Your Own Voice Assistant) on your local machine. You'll be able to develop, test, and debug YOVA without needing a Raspberry Pi.

## Prerequisites

Before you begin, ensure you have the following installed on your system:

- **Python 3.8+** (3.9+ recommended)
- **Poetry** for dependency management
- **Git** for version control
- **Make** (usually pre-installed on macOS/Linux)
- **OpenAI API Key** (for testing the voice assistant functionality)

## Quick Start

### 1. Clone and Setup the Repository

```bash
# Clone the YOVA repository
git clone https://github.com/jamro/yova.git
cd yova

# Install development dependencies (excludes Raspberry Pi specific packages)
make install-dev

# Copy the default configuration
cp yova.config.default.json yova.config.json
```

### 2. Configure Your API Key

Edit the `yova.config.json` file and add your OpenAI API key:

```json
{
  "open_ai": {
    "api_key": "sk-proj-your-actual-api-key-here"
  },
  // ... rest of configuration
}
```

**Important**: Replace `sk-proj-your-actual-api-key-here` with your actual OpenAI API key. You can get one from [OpenAI's website](https://platform.openai.com/api-keys).

### 3. Start the Development Environment

Run the development supervisor to start all YOVA services:

```bash
make supervisor-dev
```

This will start:
- **yova_core**: Main voice processing engine
- **yova_broker**: Message broker for inter-service communication  
- **yova_api**: OpenAI API connector
- **yova_client**: Hardware interface (will show errors on non-Pi systems - this is expected)

### 4. Expected Output

You should see output similar to this:

```
2025-09-09 14:16:20,167 - INFO - Starting YOVA Development Supervisor
2025-09-09 14:16:20,167 - INFO - Starting supervisor...
2025-09-09 14:16:24,098 - INFO - Supervisor started successfully
2025-09-09 14:16:24,098 - INFO - Waiting for processes to start...

==================================================
SUPERVISOR STATUS
==================================================
yova_api                         RUNNING   pid 22537, uptime 0:00:07
yova_broker                      RUNNING   pid 22538, uptime 0:00:07
yova_client                      BACKOFF   Exited too quickly (process log may have details)
yova_core                        RUNNING   pid 22540, uptime 0:00:07
==================================================
[yova_client] Error: RPi.GPIO module not found.
[yova_core] 2025-09-09 14:17:29.967 - INFO:yova_shared.broker.subscriber:Starting to listen for messages..
```

**Note**: The `yova_client` error is expected when running on a non-Raspberry Pi system. The important services (`yova_core`, `yova_broker`, `yova_api`) should be running successfully.

### 5. Test with Development Tools

In a **separate terminal**, run the development client:

```bash
make dev-tools
```

This provides a keyboard-based interface to test YOVA:

- **Press SPACEBAR** to activate push-to-talk mode (you'll hear a beep)
- **Speak your command** while holding spacebar
- **Release SPACEBAR** when finished speaking
- **YOVA will process and respond** with the AI-generated answer

## Development Workflow

### Available Make Commands

The project includes several useful development commands:

```bash
# Development
make install-dev          # Install all dependencies (excludes RPi packages)
make supervisor-dev        # Start development supervisor
make dev-tools            # Run keyboard-based test client

# Testing
make test                 # Run all tests
make test-cov            # Run tests with coverage report
make test-watch          # Run tests in watch mode

# Code Quality
make lint                 # Run linting checks
make format              # Format code with black and isort
make check               # Run all checks (lint + test)

# Utilities
make clean               # Clean up generated files
make show-deps           # Show current dependencies
make shell               # Open Poetry shell
```

### Project Structure

```
yova/
├── yova_core/           # Core voice processing engine
├── yova_broker/         # Message broker service
├── yova_api_openai/     # OpenAI API integration
├── yova_client_dev_tools/ # Development testing tools
├── yova_shared/         # Shared utilities and models
├── tests/               # Test suite
├── docs/                # Documentation
└── configs/             # Configuration files
```