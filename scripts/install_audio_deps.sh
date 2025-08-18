#!/bin/bash

# Audio Dependencies Installation Script for YOVA
echo "Installing audio dependencies for YOVA..."

# Check if we're on macOS and install portaudio if needed
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "Detected macOS, checking for portaudio..."
    if ! brew list portaudio &> /dev/null; then
        echo "Installing portaudio via Homebrew..."
        brew install portaudio
    else
        echo "portaudio already installed via Homebrew"
    fi
# Check if we're on Linux (including Raspberry Pi) and install audio dependencies
elif [[ "$OSTYPE" == "linux-gnu"* ]] || [[ "$OSTYPE" == "linux"* ]]; then
    echo "Detected Linux/Raspberry Pi, installing audio dependencies..."
    
    # Update package list
    sudo apt-get update
    
    # Install system audio dependencies
    sudo apt-get install -y \
        portaudio19-dev \
        python3-dev \
        python3-pip \
        python3-venv \
        libasound2-dev \
        libportaudio2 \
        libportaudiocpp0 \
        ffmpeg
    
    # Check if we're on Raspberry Pi and install additional dependencies
    if [[ -f /proc/cpuinfo ]] && grep -q "Raspberry Pi" /proc/cpuinfo; then
        echo "Detected Raspberry Pi, installing additional dependencies..."
        sudo apt-get install -y \
            python3-pyaudio \
            libatlas-base-dev \
            libhdf5-dev \
            libhdf5-serial-dev \
            libatlas-base-dev \
            libjasper-dev \
            libqtcore4 \
            libqtgui4 \
            libqt4-test \
            libgstreamer1.0-0 \
            libgstreamer-plugins-base1.0-0 \
            libgtk-3-0
    fi
fi

# Install Python dependencies
if command -v poetry &> /dev/null; then
    echo "Using Poetry to install dependencies..."
    poetry install
elif command -v pip &> /dev/null; then
    echo "Using pip to install dependencies..."
    pip install pyaudio sounddevice numpy websockets openai
else
    echo "Error: Install poetry or pip first."
    exit 1
fi

echo "✅ Audio dependencies installed!"
echo "Test with: poetry run yova"
