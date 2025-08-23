#!/bin/bash

# =============================================================================
# YOVA Installation Script for Raspberry Pi
# =============================================================================
# 
# This script serves TWO purposes:
# 1. AUTOMATED INSTALLATION: Run this script to automatically install YOVA
# 2. MANUAL INSTALLATION GUIDE: Use the comments as step-by-step instructions
#
# To run automated installation:
#   curl -fsSL https://raw.githubusercontent.com/jamro/yova/main/scripts/install.sh -o install.sh && bash install.sh
#
# To use as manual guide:
#   Read the comments for each function to understand what commands to run manually
#   Each function contains detailed explanations and the exact commands to execute
#
# =============================================================================
# MANUAL INSTALLATION OVERVIEW
# =============================================================================
# 
# The manual installation process follows these main steps:
# 1. System preparation and dependency installation
# 2. ReSpeaker HAT driver installation and configuration
# 3. Audio system configuration (ALSA)
# 4. Python Poetry installation
# 5. YOVA software installation
# 6. OpenAI API configuration
# 7. Systemd service setup
# 8. Audio testing and validation
#
# Each section below contains detailed comments explaining what to do manually.
# =============================================================================

# Exit on any error for automated installation
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Global variables for ReSpeaker HAT device
RESPEAKER_CARD=""
RESPEAKER_DEVICE=""
# Global variable to track if reboot is needed
REBOOT_NEEDED=false

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# =============================================================================
# OPENAI API CONFIGURATION
# =============================================================================
# 
# MANUAL INSTALLATION STEPS:
# Configure your OpenAI API key for YOVA to function.
#
# =============================================================================

# Function to prompt for OpenAI API key and inject it into config
# MANUAL: Configure your OpenAI API key in the YOVA configuration
# COMMANDS:
#   nano ~/yova/yova.config.json
#
# Find the "open_ai" section and update the "api_key" field:
#   "open_ai": {
#     "api_key": "sk-your-actual-api-key-here",
#     ...
#   }
#
# EXPLANATION:
# - You need an OpenAI API key from https://platform.openai.com/api-keys
# - The key should start with 'sk-proj-' or 'sk-'
# - This enables YOVA to use OpenAI's speech-to-text and text-to-speech services
# - Without a valid API key, YOVA cannot process voice commands or generate responses
configure_openai_api() {
    print_status "Configuring OpenAI API key..."
    
    # Check if API key is already configured (different from default placeholder)
    local current_key=$(grep -o '"api_key": "[^"]*"' yova.config.json | cut -d'"' -f4)
    if [ "$current_key" != "sk-proj-..." ] && [ -n "$current_key" ]; then
        print_warning "OpenAI API key already configured, skipping configuration step"
        return 0
    fi
    
    echo ""
    echo "Please provide your OpenAI API key:"
    echo "- You can find it at: https://platform.openai.com/api-keys"
    echo "- The key should start with 'sk-proj-' or 'sk-'"
    echo ""
    
    # Ask user if they want to configure the API key now
    read -p "Do you want to configure the OpenAI API key now? (Y/n): " -n 1 -r
    echo ""
    
    if [[ $REPLY =~ ^[Nn]$ ]]; then
        print_warning "OpenAI API key configuration skipped. You can configure it later by editing yova.config.json"
        return 0
    fi
    
    # Prompt for API key (hidden input)
    read -s -p "Enter your OpenAI API key: " api_key
    echo ""
    
    # Validate API key format
    if [[ ! "$api_key" =~ ^sk-[a-zA-Z0-9_\-]{20,}$ ]]; then
        print_error "Invalid API key format. API key should start with 'sk-' and be at least 20 characters long."
        print_error "Provided key: $api_key"
        return 1
    fi
    
    # Update the API key in the config file
    if command -v jq &> /dev/null; then
        # Use jq if available for safer JSON manipulation
        print_status "Using jq for safe JSON manipulation"
        jq --arg key "$api_key" '.open_ai.api_key = $key' yova.config.json > yova.config.json.tmp
        mv yova.config.json.tmp yova.config.json
    else
        # Fallback to sed if jq is not available
        print_warning "jq not found, using sed fallback (less safe)"
        sed -i "s/\"api_key\": \"[^\"]*\"/\"api_key\": \"$api_key\"/" yova.config.json
    fi
    
    # Verify the update
    local updated_key=$(grep -o '"api_key": "[^"]*"' yova.config.json | cut -d'"' -f4)
    if [ "$updated_key" = "$api_key" ]; then
        # Validate JSON syntax if jq is available
        if command -v jq &> /dev/null; then
            if jq empty yova.config.json 2>/dev/null; then
                print_success "OpenAI API key configured successfully"
                return 0
            else
                print_error "Configuration file contains invalid JSON after update"
                return 1
            fi
        else
            print_success "OpenAI API key configured successfully"
            return 0
        fi
    else
        print_error "Failed to update API key in configuration"
        return 1
    fi
}

# =============================================================================
# SYSTEM PREPARATION AND DEPENDENCY INSTALLATION
# =============================================================================
# 
# MANUAL INSTALLATION STEPS:
# These commands prepare your Raspberry Pi system and install required dependencies.
# Run them in sequence if doing manual installation.
#
# =============================================================================

# Function to check if running on Raspberry Pi
# MANUAL: Verify you're on a Raspberry Pi by checking /proc/cpuinfo
check_raspberry_pi() {
    if ! grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then
        print_error "This script must be run on a Raspberry Pi"
        exit 1
    fi
    print_success "Raspberry Pi detected"
}

# Function to check if running as root
# MANUAL: Ensure you're NOT running as root - use 'pi' user instead
# COMMAND: whoami  (should show 'pi', not 'root')
check_root() {
    if [[ $EUID -eq 0 ]]; then
        print_error "This script should not be run as root. Please run as pi user."
        exit 1
    fi
}

# Function to check if pi user exists
# MANUAL: Verify the 'pi' user exists on your system
# COMMAND: id pi  (should show user information)
check_pi_user() {
    if ! id "pi" &>/dev/null; then
        print_error "User 'pi' does not exist. Please create it first."
        exit 1
    fi
    print_success "User 'pi' found"
}

# Function to update system
# MANUAL: Update your Raspberry Pi system packages
# COMMANDS:
#   sudo apt update
#   sudo apt upgrade -y
update_system() {
    print_status "Updating system packages..."
    sudo apt update
    DEBIAN_FRONTEND=noninteractive sudo apt upgrade -y -o Dpkg::Options::="--force-confnew"
    print_success "System updated"
}

# Function to install dependencies
# MANUAL: Install all required system dependencies for YOVA
# COMMAND:
#   sudo apt install -y build-essential python3-dev libasound2-dev libportaudio2 \
#       portaudio19-dev libportaudiocpp0 libjack-jackd2-dev python3-rpi-lgpio \
#       curl alsa-utils jq
#
# EXPLANATION:
# - build-essential: C/C++ compiler and build tools
# - python3-dev: Python development headers
# - libasound2-dev: ALSA audio library development files
# - libportaudio2: PortAudio audio I/O library
# - portaudio19-dev: PortAudio development files
# - libportaudiocpp0: PortAudio C++ bindings
# - libjack-jackd2-dev: JACK audio server development files
# - python3-rpi-lgpio: Raspberry Pi GPIO library for Python
# - curl: Download files from the web
# - alsa-utils: ALSA utilities (alsamixer, aplay, arecord)
# - jq: JSON processor for configuration file manipulation
install_dependencies() {
    print_status "Installing system dependencies..."
    sudo apt install -y build-essential python3-dev libasound2-dev libportaudio2 \
        portaudio19-dev libportaudiocpp0 libjack-jackd2-dev python3-rpi-lgpio \
        curl alsa-utils jq
    print_success "Dependencies installed"
}

# Function to configure GPIO access
# MANUAL: Add the 'pi' user to the 'gpio' group for GPIO access
# COMMAND: sudo usermod -aG gpio pi
# NOTE: You'll need to log out and back in for group changes to take effect
configure_gpio() {
    print_status "Configuring GPIO access..."
    sudo usermod -aG gpio pi
    print_success "GPIO access configured"
}

# =============================================================================
# RESPEAKER HAT DRIVER INSTALLATION AND CONFIGURATION
# =============================================================================
# 
# MANUAL INSTALLATION STEPS:
# These steps install and configure the ReSpeaker 2-Mic HAT drivers.
# This is a critical step for audio functionality.
#
# =============================================================================

# Function to install ReSpeaker HAT drivers
# MANUAL: Install the ReSpeaker HAT device tree overlay
# COMMANDS:
#   curl https://raw.githubusercontent.com/Seeed-Studio/seeed-linux-dtoverlays/refs/heads/master/overlays/rpi/respeaker-2mic-v2_0-overlay.dts -o respeaker-2mic-v2_0-overlay.dts
#   dtc -I dts respeaker-2mic-v2_0-overlay.dts -o respeaker-2mic-v2_0-overlay.dtbo
#   sudo cp respeaker-2mic-v2_0-overlay.dtbo /boot/firmware/overlays/
#
# EXPLANATION:
# - Downloads the device tree source file for ReSpeaker HAT
# - Compiles the DTS file to a binary DTB overlay
# - Installs the overlay to the boot firmware directory
# - This enables the kernel to recognize the ReSpeaker HAT hardware
install_respeaker_drivers() {
    print_status "Installing ReSpeaker HAT drivers..."
    
    # Download and compile device tree overlay
    curl -s https://raw.githubusercontent.com/Seeed-Studio/seeed-linux-dtoverlays/refs/heads/master/overlays/rpi/respeaker-2mic-v2_0-overlay.dts -o respeaker-2mic-v2_0-overlay.dts
    
    if [ ! -f respeaker-2mic-v2_0-overlay.dts ]; then
        print_error "Failed to download ReSpeaker overlay file"
        exit 1
    fi
    
    # Compile DTS to DTB
    dtc -I dts respeaker-2mic-v2_0-overlay.dts -o respeaker-2mic-v2_0-overlay.dtbo
    
    if [ ! -f respeaker-2mic-v2_0-overlay.dtbo ]; then
        print_error "Failed to compile ReSpeaker overlay"
        exit 1
    fi
    
    # Install overlay
    # TODO: check if this is really necessary
    # sudo dtoverlay respeaker-2mic-v2_0-overlay.dtbo
    sudo cp respeaker-2mic-v2_0-overlay.dtbo /boot/firmware/overlays/
    
    # Clean up temporary files
    rm -f respeaker-2mic-v2_0-overlay.dts respeaker-2mic-v2_0-overlay.dtbo
    
    print_success "ReSpeaker HAT drivers installed"
}

# Function to configure boot config
# MANUAL: Configure the Raspberry Pi boot configuration to enable ReSpeaker HAT
# COMMANDS:
#   sudo nano /boot/firmware/config.txt
#
# Add these lines under the [all] section:
#   # ReSpeaker HAT
#   dtoverlay=respeaker-2mic-v2_0-overlay
#   dtoverlay=i2s-mmap
#
# EXPLANATION:
# - dtoverlay=respeaker-2mic-v2_0-overlay: Enables the ReSpeaker HAT driver
# - dtoverlay=i2s-mmap: Enables I2S audio interface with memory mapping
# - These changes require a reboot to take effect
configure_boot_config() {
    print_status "Configuring boot configuration..."
    
    # Backup original config
    sudo cp /boot/firmware/config.txt /boot/firmware/config.txt.backup
    
    # Check if overlays are already configured
    if ! grep -q "respeaker-2mic-v2_0-overlay" /boot/firmware/config.txt; then
        # Check if [all] section exists
        if grep -q "^\[all\]" /boot/firmware/config.txt; then
            # [all] section exists, add dtoverlay entries under it
            # Find the line number of [all] section
            local all_section_line=$(grep -n "^\[all\]" /boot/firmware/config.txt | cut -d: -f1)
            # Insert dtoverlay entries after [all] section
            sudo sed -i "${all_section_line}a\\
# ReSpeaker HAT\\
dtoverlay=respeaker-2mic-v2_0-overlay\\
dtoverlay=i2s-mmap" /boot/firmware/config.txt
        else
            # [all] section doesn't exist, add it at the end with dtoverlay entries
            echo "" | sudo tee -a /boot/firmware/config.txt
            echo "[all]" | sudo tee -a /boot/firmware/config.txt
            echo "# ReSpeaker HAT" | sudo tee -a /boot/firmware/config.txt
            echo "dtoverlay=respeaker-2mic-v2_0-overlay" | sudo tee -a /boot/firmware/config.txt
            echo "dtoverlay=i2s-mmap" | sudo tee -a /boot/firmware/config.txt
        fi
        print_success "Boot configuration updated"
        REBOOT_NEEDED=true
    else
        print_warning "ReSpeaker overlays already configured in boot config"
    fi
}

# =============================================================================
# AUDIO SYSTEM CONFIGURATION (ALSA)
# =============================================================================
# 
# MANUAL INSTALLATION STEPS:
# These steps configure the ALSA audio system to work with the ReSpeaker HAT.
# After completing the previous steps and rebooting, you'll configure audio.
#
# =============================================================================

# Function to detect ReSpeaker HAT device
# MANUAL: After reboot, detect which audio device corresponds to your ReSpeaker HAT
# COMMANDS:
#   aplay -l  (list playback devices)
#   arecord -l  (list recording devices)
#
# EXPECTED OUTPUT:
# Look for a device named 'seeed2micvoicec' or similar:
#   card 2: seeed2micvoicec [seeed2micvoicec], device 0: ...
#   - Card number = 2 (in this example)
#   - Device number = 0 (in this example)
detect_respeaker_device() {
    print_status "Detecting ReSpeaker HAT device..."
    
    # Get list of audio devices
    local aplay_output=$(aplay -l 2>/dev/null)
    
    if [ $? -ne 0 ]; then
        print_error "Failed to get audio device list"
        return 1
    fi
    
    # Look for ReSpeaker HAT device
    local respeaker_line=$(echo "$aplay_output" | grep -i "seeed2micvoicec\|seeed-2mic-voicec\|respeaker")
    
    if [ -n "$respeaker_line" ]; then
        # Extract card and device numbers
        local card=$(echo "$respeaker_line" | sed -n 's/.*card \([0-9]*\):.*/\1/p')
        local device=$(echo "$respeaker_line" | sed -n 's/.*device \([0-9]*\):.*/\1/p')
        
        if [ -n "$card" ] && [ -n "$device" ]; then
            print_success "Detected ReSpeaker HAT: card $card, device $device"
            RESPEAKER_CARD=$card
            RESPEAKER_DEVICE=$device
            return 0
        fi
    fi
    
    print_warning "Could not automatically detect ReSpeaker HAT device"
    return 1
}

# Function for interactive device selection
# MANUAL: If automatic detection fails, manually select your ReSpeaker HAT device
# COMMANDS:
#   aplay -l  (to see all available devices)
#   arecord -l  (to see all available recording devices)
#   Look for 'seeed2micvoicec' or similar device name
interactive_device_selection() {
    print_status "Interactive device selection..."
    
    echo ""
    echo "Available audio devices:"
    aplay -l
    
    echo ""
    print_warning "Please identify which card and device correspond to your ReSpeaker HAT"
    print_warning "Look for a device named 'seeed2micvoicec' or similar. CTRL+C to cancel."
    
    # Get user input
    read -p "Enter card number: " card_input
    read -p "Enter device number: " device_input
    
    # Validate input
    if [[ "$card_input" =~ ^[0-9]+$ ]] && [[ "$device_input" =~ ^[0-9]+$ ]]; then
        RESPEAKER_CARD=$card_input
        RESPEAKER_DEVICE=$device_input
        print_success "Using card $RESPEAKER_CARD, device $RESPEAKER_DEVICE"
        return 0
    else
        print_error "Invalid input. Please enter numeric values."
        return 1
    fi
}

# Function to configure ALSA
# MANUAL: Create ALSA configuration file to use ReSpeaker HAT as default audio device
# COMMANDS:
#   sudo nano /etc/asound.conf
#
# Add this content (replace X,Y with your card,device numbers):
#   pcm.!default {
#       type plug
#       slave.pcm "hw:X,Y"
#       slave.rate 16000
#   }
#   ctl.!default {
#       type hw
#       card X
#   }
#
# EXPLANATION:
# - pcm.!default: Sets the default playback device
# - slave.pcm "hw:X,Y": Uses hardware device X,Y (your ReSpeaker HAT)
# - slave.rate 16000: Sets sample rate to 16kHz (optimal for speech)
# - ctl.!default: Sets the default control device for volume control
configure_alsa() {
    print_status "Configuring ALSA..."
    
    # Try automatic detection first
    if ! detect_respeaker_device; then
        # Fall back to interactive detection
        if ! interactive_device_selection; then
            # Final fallback to hardcoded values
            print_warning "Using fallback values: card 2, device 0"
            RESPEAKER_CARD=2
            RESPEAKER_DEVICE=0
        fi
    fi
    
    # Create ALSA configuration
    sudo tee /etc/asound.conf > /dev/null <<EOF
pcm.!default {
    type plug
    slave.pcm "hw:${RESPEAKER_CARD},${RESPEAKER_DEVICE}"
    slave.rate 16000
}
ctl.!default {
    type hw
    card ${RESPEAKER_CARD}
}
EOF
    
    print_success "ALSA configuration created with card ${RESPEAKER_CARD}, device ${RESPEAKER_DEVICE}"
}

# Function to enable SPI
# MANUAL: Enable SPI interface for ReSpeaker HAT LED control
# COMMANDS:
#   sudo raspi-config
#   - Select "Interfacing Options"
#   - Select "SPI"
#   - Select "Yes"
#   - Exit and reboot
#
# ALTERNATIVE: Edit config.txt manually
#   sudo nano /boot/firmware/config.txt
#   Add: dtparam=spi=on
enable_spi() {
    print_status "Enabling SPI interface..."
    
    # Check if SPI is already enabled (not commented out)
    if grep -q "^[[:space:]]*dtparam=spi=on" /boot/firmware/config.txt; then
        print_warning "SPI already enabled in boot config"
        return 0
    fi
    
    # Check if SPI line exists but is commented out
    if grep -q "^[[:space:]]*#[[:space:]]*dtparam=spi=on" /boot/firmware/config.txt; then
        print_status "SPI line found but commented out, enabling it..."
        # Uncomment the existing line
        sudo sed -i 's/^[[:space:]]*#[[:space:]]*dtparam=spi=on/dtparam=spi=on/' /boot/firmware/config.txt
        print_success "SPI enabled by uncommenting existing line"
        REBOOT_NEEDED=true
        return 0
    fi
    
    # If no SPI line exists, add it
    print_status "Adding SPI configuration to boot config..."
    echo "dtparam=spi=on" | sudo tee -a /boot/firmware/config.txt > /dev/null
    
    # Verify the change was made
    if grep -q "^[[:space:]]*dtparam=spi=on" /boot/firmware/config.txt; then
        print_success "SPI configuration added successfully"
        REBOOT_NEEDED=true
    else
        print_error "Failed to add SPI configuration"
        return 1
    fi
}

# =============================================================================
# PYTHON POETRY INSTALLATION
# =============================================================================
# 
# MANUAL INSTALLATION STEPS:
# Install Python Poetry for dependency management and then install YOVA.
#
# =============================================================================

# Function to install Python Poetry
# MANUAL: Install Python Poetry for dependency management
# COMMANDS:
#   curl -sSL https://install.python-poetry.org | python3 -
#   echo 'export PATH="/home/pi/.local/bin:$PATH"' >> ~/.bashrc
#   source ~/.bashrc
#
# EXPLANATION:
# - Downloads and installs Poetry using the official installer
# - Adds Poetry to your PATH via .bashrc
# - Reloads the shell configuration
install_poetry() {
    print_status "Installing Python Poetry..."
    
    if ! command -v poetry &> /dev/null; then
        curl -sSL https://install.python-poetry.org | python3 -
        echo 'export PATH="/home/pi/.local/bin:$PATH"' >> ~/.bashrc
        export PATH="/home/pi/.local/bin:$PATH"
        print_success "Poetry installed"
    else
        print_warning "Poetry already installed"
    fi
}

# =============================================================================
# YOVA SOFTWARE INSTALLATION
# =============================================================================
# 
# MANUAL INSTALLATION STEPS:
# Clone the YOVA repository and install it using Poetry.
#
# =============================================================================

# Function to clone and install YOVA
# MANUAL: Clone YOVA repository and install dependencies
# COMMANDS:
#   cd /home/pi
#   git clone https://github.com/jamro/yova.git
#   cd yova
#   poetry config keyring.enabled false
#   make install
#   cp yova.config.default.json yova.config.json
#
# EXPLANATION:
# - Clones the YOVA repository from GitHub
# - Configures Poetry to disable keyring (not needed on Raspberry Pi)
# - Installs all Python dependencies using Poetry
# - Creates a configuration file from the template
install_yova() {
    print_status "Installing YOVA..."
    
    # Ensure we're in the pi user's home directory
    cd /home/pi
    
    if [ ! -d "yova" ]; then
        git clone https://github.com/jamro/yova.git
        cd yova
    else
        print_warning "YOVA directory already exists, updating..."
        cd yova
        git pull
    fi
    
    # Configure Poetry
    poetry config keyring.enabled false
    
    # Install dependencies
    make install
    
    # Copy configuration
    if [ ! -f "yova.config.json" ]; then
        cp yova.config.default.json yova.config.json
        print_success "Configuration file created from template"
    fi
    
    print_success "YOVA installed at /home/pi/yova"
}

# =============================================================================
# SYSTEMD SERVICE CONFIGURATION
# =============================================================================
# 
# MANUAL INSTALLATION STEPS:
# Set up YOVA to run automatically as a system service.
#
# =============================================================================

# Function to configure systemd service
# MANUAL: Set up YOVA to run as a system service
# COMMANDS:
#   sudo cp ~/yova/scripts/supervisord.service /etc/systemd/system/
#   sudo systemctl daemon-reload
#   sudo systemctl enable supervisord.service
#   sudo systemctl start supervisord.service
#
# EXPLANATION:
# - Copies the supervisord service file to systemd directory
# - Reloads systemd to recognize the new service
# - Enables the service to start automatically on boot
# - Starts the service immediately
# - This ensures YOVA runs automatically and restarts if it crashes
configure_systemd() {
    print_status "Configuring systemd service..."
    
    # Check if systemd service is already configured
    if systemctl is-enabled supervisord.service &>/dev/null; then
        print_warning "Systemd service already configured and enabled, skipping configuration step"
        return 0
    fi
    
    if [ -f "scripts/supervisord.service" ]; then
        sudo cp scripts/supervisord.service /etc/systemd/system/
        sudo systemctl daemon-reload
        sudo systemctl enable supervisord.service
        sudo systemctl start supervisord.service
        print_success "Systemd service configured"
        REBOOT_NEEDED=true
    else
        print_warning "supervisord.service not found, skipping systemd configuration"
    fi
}

# =============================================================================
# AUDIO TESTING AND VALIDATION
# =============================================================================
# 
# MANUAL INSTALLATION STEPS:
# Test audio playback and recording to ensure ReSpeaker HAT is working correctly.
# These tests are critical - YOVA cannot function without working audio.
#
# =============================================================================

# Function to download test audio file
# MANUAL: Download a test audio file for testing audio playback
# COMMANDS:
#   wget https://github.com/jamro/yova/raw/refs/heads/main/yova_shared/assets/test_sound.wav
#   # OR
#   curl -L -o test_sound.wav https://github.com/jamro/yova/raw/refs/heads/main/yova_shared/assets/test_sound.wav
download_test_audio() {
    print_status "Downloading test audio file..."
    
    local test_file="test_sound.wav"
    local download_url="https://github.com/jamro/yova/raw/refs/heads/main/yova_shared/assets/test_sound.wav"
    
    echo "Downloading from: $download_url"
    
    if curl -L -o "$test_file" "$download_url" 2>/dev/null; then
        print_success "Test audio file downloaded successfully: $test_file"
    else
        print_error "Failed to download test audio file"
        return 1
    fi
}

# Function to test audio playback
# MANUAL: Test audio playback through your ReSpeaker HAT
# COMMANDS:
#   # First, adjust volume if needed:
#   alsamixer
#   # Press F6 to select output device, choose 'seeed2micvoicec'
#   # Set PCM and Line DAC to 80-100%
#   # Press ESC to exit
#
#   # Test playback:
#   aplay -D "plughw:X,Y" test_sound.wav
#   # Replace X,Y with your card,device numbers
#
#   # Store volume settings:
#   sudo alsactl store
#
# EXPLANATION:
# - Tests if audio output is working correctly
# - Allows you to adjust volume settings if needed
# - Stores volume settings so they persist across reboots
# - This test is required before proceeding with installation
test_playback() {
    print_status "Testing audio playback..."
    echo ""
    echo "This test will play a test sound through your ReSpeaker HAT."
    echo "Please ensure your speaker is connected and volume is set appropriately."
    echo ""
    
    read -p "Press Enter to continue with the audio test..."
    
    # Check if test file exists, download if it doesn't
    local test_file="test_sound.wav"
    if [ ! -f "$test_file" ]; then
        print_status "Test audio file not found, downloading..."
        if ! download_test_audio >/dev/null 2>&1; then
            print_error "Failed to download test audio file. Cannot proceed with audio testing."
            exit 1
        fi
    else
        print_status "Using existing test audio file: $test_file"
    fi
    
    local test_success=false
    local test_attempts=0
    local max_attempts=10
    
    while [ "$test_success" = false ] && [ $test_attempts -lt $max_attempts ]; do
        test_attempts=$((test_attempts + 1))
        echo ""
        print_status "Audio test attempt $test_attempts of $max_attempts"
        echo "Playing test sound..."
        
        # Check if test file exists
        if [ ! -f "$test_file" ]; then
            print_error "Test audio file not found: $test_file"
            echo "Please ensure YOVA is properly installed."
            exit 1
        fi
        
        # Play the test sound
        if aplay -D "plughw:${RESPEAKER_CARD},${RESPEAKER_DEVICE}" "$test_file" 2>/dev/null; then
            echo ""
            echo "Test sound played successfully."
            read -p "Did you hear the sound clearly? (y/n): " -n 1 -r
            echo ""
            
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                print_success "Audio playback test passed!"
                test_success=true
                
                # Store ALSA settings after successful test
                print_status "Storing ALSA settings..."
                if sudo alsactl store; then
                    print_success "ALSA settings stored successfully"
                else
                    print_warning "Failed to store ALSA settings, but audio is working"
                fi
                
                # Clean up test file
                if [ -f "$test_file" ]; then
                    rm -f "$test_file"
                    print_status "Test file cleaned up"
                fi
            else
                echo ""
                print_warning "Sound was not heard clearly or was too quiet."
                echo ""
                echo "Let's adjust the audio volume settings using alsamixer."
                echo "Focus on playback volume only (skip recording/capture settings for now)."
                echo ""
                echo "Recommended settings:"
                echo "1. Press F6 to select output device"
                echo "2. Select 'seeed2micvoicec' from the device list"
                echo "3. Set PCM to 100%"
                echo "4. Set Line DAC to 100%"
                echo ""
                echo "To exit alsamixer: Press ESC key"
                echo ""
                
                read -p "Press Enter to open alsamixer for volume adjustment..."
                
                # Run alsamixer for the user
                alsamixer
                
                echo ""
                print_status "alsamixer closed. Let's test the audio again..."
            fi
        else
            print_error "Failed to play test sound. Please check your audio configuration."
            echo ""
            echo "Let's adjust the audio settings using alsamixer."
            echo ""
            echo "Recommended settings:"
            echo "1. Press F6 to select output device"
            echo "2. Select 'seeed2micvoicec' from the device list"
            echo "3. Set PCM to 100%"
            echo "4. Set Line DAC to 100%"
            echo ""
            echo "To exit alsamixer: Press ESC key"
            echo ""
            
            read -p "Press Enter to open alsamixer for volume adjustment..."
            
            # Run alsamixer for the user
            alsamixer
            
            echo ""
            print_status "alsamixer closed. Let's try the audio test again..."
        fi
    done
    
    if [ "$test_success" = false ]; then
        # Clean up test file before exiting
        if [ -f "$test_file" ]; then
            rm -f "$test_file"
            print_status "Test file cleaned up"
        fi
        
        print_error "Audio testing failed after $max_attempts attempts."
        echo ""
        echo "Please resolve the audio configuration issue before continuing."
        echo "You can:"
        echo "1. Check hardware connections"
        echo "2. Verify ReSpeaker HAT detection"
        echo "3. Adjust volume settings with 'alsamixer'"
        echo "4. Check system logs for audio errors"
        echo ""
        echo "Installation cannot continue without working audio."
        exit 1
    fi
}

# Function to test audio recording
# MANUAL: Test audio recording from your ReSpeaker HAT microphone
# COMMANDS:
#   # First, adjust recording volume if needed:
#   alsamixer
#   # Press F6 to select input device, choose 'seeed2micvoicec'
#   # Press F4 to filter capture settings
#   # Set Capture (PGA) to 25-30% (recommended)
#   # Press ESC to exit
#
#   # Test recording:
#   arecord -D "plughw:X,Y" -f S16_LE -c1 -r 16000 -d 5 rec_test.wav
#   # Replace X,Y with your card,device numbers
#
#   # Test playback of recording:
#   aplay -D "plughw:X,Y" rec_test.wav
#
#   # Store volume settings:
#   sudo alsactl store
#
# EXPLANATION:
# - Tests if microphone input is working correctly
# - Allows you to adjust recording volume settings if needed
# - Records for 5 seconds and plays back to verify quality
# - This test is required before proceeding with installation
test_recording() {
    print_status "Testing audio recording..."
    echo ""
    echo "This test will record audio from your ReSpeaker HAT microphone for 5 seconds."
    echo "Please speak clearly into the microphone during the recording."
    echo ""
    
    read -p "Press Enter to continue with the recording test..."
    
    local test_success=false
    local test_attempts=0
    local max_attempts=10
    
    while [ "$test_success" = false ] && [ $test_attempts -lt $max_attempts ]; do
        test_attempts=$((test_attempts + 1))
        echo ""
        print_status "Recording test attempt $test_attempts of $max_attempts"
        echo "Recording audio for 5 seconds... Please speak clearly."
        
        # Record audio
        if arecord -D "plughw:${RESPEAKER_CARD},${RESPEAKER_DEVICE}" -f S16_LE -c1 -r 16000 -d 5 rec_test.wav 2>/dev/null; then
            echo ""
            echo "Recording completed successfully."
            echo "Now playing back the recorded audio..."
            
            # Play back the recorded audio
            if aplay -D "plughw:${RESPEAKER_CARD},${RESPEAKER_DEVICE}" rec_test.wav 2>/dev/null; then
                echo ""
                echo "Playback completed."
                read -p "Did you hear your voice clearly in the playback? It should be loud but without audio clipping. (y/n): " -n 1 -r
                echo ""
                
                if [[ $REPLY =~ ^[Yy]$ ]]; then
                    print_success "Audio recording test passed!"
                    test_success=true

                    # Store ALSA settings after successful test
                    print_status "Storing ALSA settings..."
                    if sudo alsactl store; then
                        print_success "ALSA settings stored successfully"
                    else
                        print_warning "Failed to store ALSA settings, but audio is working"
                    fi
                    
                    # Clean up test file
                    rm -f rec_test.wav
                else
                    echo ""
                    print_warning "Recording was not clear or too quiet."
                    echo ""
                    echo "Let's adjust the audio recording settings using alsamixer."
                    echo "Focus on capture/recording volume settings."
                    echo ""
                    echo "Recommended settings:"
                    echo "1. Press F6 to select input device"
                    echo "2. Select 'seeed2micvoicec' from the device list"
                    echo "3. Press F4 to filter capture settings"
                    echo "4. Set Capture (PGA) to 30% (recommended)"
                    echo ""
                    echo "To exit alsamixer: Press ESC key"
                    echo ""
                    
                    read -p "Press Enter to open alsamixer for recording volume adjustment..."
                    
                    # Run alsamixer for the user
                    alsamixer
                    
                    echo ""
                    print_status "alsamixer closed. Let's test the recording again..."
                fi
            else
                print_error "Failed to play back recorded audio."
                echo ""
                echo "Let's adjust the audio settings using alsamixer."
                echo ""
                echo "Recommended settings:"
                echo "1. Press F6 to select input device"
                echo "2. Select 'seeed2micvoicec' from the device list"
                echo "3. Press F4 to filter capture settings"
                echo "4. Set Capture (PGA) to 30% (recommended)"
                echo ""
                echo "To exit alsamixer: Press ESC key"
                echo ""
                
                read -p "Press Enter to open alsamixer for recording volume adjustment..."
                
                # Run alsamixer for the user
                alsamixer
                
                echo ""
                print_status "alsamixer closed. Let's try the recording test again..."
            fi
        else
            print_error "Failed to record audio. Please check your microphone configuration."
            echo ""
            echo "Let's adjust the audio settings using alsamixer."
            echo ""
            echo "Recommended settings:"
            echo "1. Press F6 to select input device"
            echo "2. Select 'seeed2micvoicec' from the device list"
            echo "3. Press F4 to filter capture settings"
            echo "4. Set Capture (PGA) to 30% (recommended)"
            echo ""
            echo "To exit alsamixer: Press ESC key"
            echo ""
            
            read -p "Press Enter to open alsamixer for recording volume adjustment..."
            
            # Run alsamixer for the user
            alsamixer
            
            echo ""
            print_status "alsamixer closed. Let's try the recording test again..."
        fi
    done
    
    if [ "$test_success" = false ]; then
        print_error "Audio recording test failed after $max_attempts attempts."
        echo ""
        echo "Please resolve the audio recording configuration issue before continuing."
        echo "You can:"
        echo "1. Check microphone connection"
        echo "2. Verify ReSpeaker HAT detection"
        echo "3. Adjust recording volume settings with 'alsamixer'"
        echo "4. Check system logs for audio errors"
        echo ""
        echo "Installation cannot continue without working audio recording."
        exit 1
    fi
}

# =============================================================================
# POST-INSTALLATION INSTRUCTIONS AND SERVICE MANAGEMENT
# =============================================================================
# 
# MANUAL INSTALLATION STEPS:
# After installation, learn how to manage YOVA and troubleshoot issues.
#
# =============================================================================

# Function to provide post-installation instructions
# MANUAL: After installation, here's what you need to know
# COMMANDS FOR TESTING YOVA:
#   # Test YOVA functionality:
#   # 1. Press the push-to-talk button on your ReSpeaker HAT
#   # 2. Wait for the beep sound to confirm it's listening
#   # 3. Ask a question (e.g., 'Tell me a joke' or 'What is artificial intelligence?')
#   # 4. Wait for YOVA to respond
#
# COMMANDS FOR SERVICE MANAGEMENT:
#   # Check service status:
#   sudo systemctl status supervisord.service
#
#   # View service logs:
#   sudo journalctl -u supervisord.service -f
#
#   # Restart service (after config changes):
#   sudo systemctl restart supervisord.service
#
# COMMANDS FOR CONFIGURATION:
#   # Edit configuration:
#   nano ~/yova/yova.config.json
#
#   # Common customizations:
#   # - Change language settings
#   # - Adjust audio settings
#   # - Modify OpenAI model preferences
post_install_instructions() {
    print_success "Installation completed!"
    echo ""
    
    if [ -n "$RESPEAKER_CARD" ] && [ -n "$RESPEAKER_DEVICE" ]; then
        echo "ReSpeaker HAT detected and configured:"
        echo "- Card: $RESPEAKER_CARD"
        echo "- Device: $RESPEAKER_DEVICE"
        echo ""
    fi
    
    # Restart service to ensure it's running fresh
    echo "Restarting YOVA service..."
    sudo systemctl restart supervisord.service
    
    # Check if service is configured and running
    echo "Checking YOVA service status..."
    if systemctl is-enabled supervisord.service &>/dev/null; then
        print_success "✓ YOVA service is configured and enabled"
    else
        print_warning "✗ YOVA service is not configured"
    fi
    
    if systemctl is-active supervisord.service &>/dev/null; then
        print_success "✓ YOVA service is running"
    else
        print_warning "✗ YOVA service is not running"
        echo "   To start: sudo systemctl start supervisord.service"
    fi
    
    echo ""
    echo "Next steps:"
    echo "1. Test YOVA functionality:"
    echo "   - Press the push-to-talk button on your ReSpeaker HAT"
    echo "   - Wait for the beep sound to confirm it's listening"
    echo "   - Ask a question (e.g., 'Tell me a joke' or 'What is artificial intelligence?')"
    echo "   - Wait for YOVA to respond"
    echo ""
    echo "2. Review and customize configuration:"
    echo "   - Edit: nano ~/yova/yova.config.json"
    echo "   - Common customizations:"
    echo "     * Change language"
    echo "     * Adjust audio settings"
    echo "   - After config changes, restart the service:"
    echo "     sudo systemctl restart supervisord.service"
    echo ""
    echo "3. If you need to check service status:"
    echo "   - Status: sudo systemctl status supervisord.service"
    echo "   - Logs: sudo journalctl -u supervisord.service -f"
}

# =============================================================================
# REBOOT HANDLING
# =============================================================================
# 
# MANUAL INSTALLATION STEPS:
# Some configuration changes require a reboot to take effect.
#
# =============================================================================

# Function to handle reboot confirmation and execution
# MANUAL: When prompted for reboot, you have two options:
# OPTION 1: Reboot now (recommended)
#   - Type 'y' when prompted
#   - Wait for system to reboot
#   - After reboot, re-run the install script to continue
#
# OPTION 2: Reboot later
#   - Type 'n' when prompted
#   - Reboot manually when ready: sudo reboot
#   - After reboot, re-run the install script to continue
#
# EXPLANATION:
# - Reboot is required after modifying /boot/firmware/config.txt
# - This ensures kernel loads the new ReSpeaker HAT drivers
# - Without reboot, audio devices won't be detected properly
handle_reboot() {
    if [ "$REBOOT_NEEDED" = true ]; then
        echo ""
        print_warning "A reboot is required to apply the boot configuration changes."
        echo "The reboot is necessary before continuing to the next installation steps."
        echo ""
        echo "After reboot, you must re-run the install script to complete the installation."
        echo ""
        
        read -p "Do you agree to reboot the machine now to apply changes? (y/N): " -n 1 -r
        echo ""
        
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            print_status "Rebooting in 5 seconds... Press Ctrl+C to cancel."
            print_status "REMEMBER: After reboot, re-run install command!"
            echo ""
            sleep 2
            print_status "Rebooting in 3 seconds... Press Ctrl+C to cancel."
            sleep 1
            print_status "Rebooting in 2 seconds... Press Ctrl+C to cancel."
            sleep 1
            print_status "Rebooting in 1 second... Press Ctrl+C to cancel."
            sleep 1
            print_status "Rebooting now..."
            sudo reboot
        else
            print_warning "Reboot cancelled. Please reboot manually when ready and re-run this script."
            print_warning "Installation cannot continue without a reboot."
            exit 0
        fi
    fi
}

# =============================================================================
# MAIN INSTALLATION FUNCTION
# =============================================================================
# 
# MANUAL INSTALLATION SEQUENCE:
# This is the complete sequence of steps for manual installation.
# Follow these steps in order, rebooting when prompted.
#
# =============================================================================

# Main installation function
# MANUAL: Complete installation sequence - follow these steps in order:
# 
# PHASE 1: System Preparation (no reboot needed)
#   1. Update system: sudo apt update && sudo apt upgrade -y
#   2. Install dependencies: sudo apt install -y build-essential python3-dev libasound2-dev libportaudio2 portaudio19-dev libportaudiocpp0 libjack-jackd2-dev python3-rpi-lgpio curl alsa-utils jq
#   3. Configure GPIO: sudo usermod -aG gpio pi
#
# PHASE 2: ReSpeaker HAT Setup (reboot required)
#   4. Install drivers: curl https://raw.githubusercontent.com/Seeed-Studio/seeed-linux-dtoverlays/refs/heads/master/overlays/rpi/respeaker-2mic-v2_0-overlay.dts -o respeaker-2mic-v2_0-overlay.dts
#   5. Compile overlay: dtc -I dts respeaker-2mic-v2_0-overlay.dts -o respeaker-2mic-v2_0-overlay.dtbo
#   6. Install overlay: sudo cp respeaker-2mic-v2_0-overlay.dtbo /boot/firmware/overlays/
#   7. Edit boot config: sudo nano /boot/firmware/config.txt
#      Add under [all] section:
#        # ReSpeaker HAT
#        dtoverlay=respeaker-2mic-v2_0-overlay
#        dtoverlay=i2s-mmap
#   8. Enable SPI: sudo nano /boot/firmware/config.txt
#      Add: dtparam=spi=on
#   9. REBOOT: sudo reboot
#
# PHASE 3: Audio Configuration (no reboot needed)
#   10. Detect devices: aplay -l && arecord -l
#   11. Configure ALSA: sudo nano /etc/asound.conf
#       Add content with your card,device numbers
#   12. Test audio: aplay -D "plughw:X,Y" test_sound.wav
#   13. Test recording: arecord -D "plughw:X,Y" -f S16_LE -c1 -r 16000 -d 5 rec_test.wav
#
# PHASE 4: Software Installation (no reboot needed)
#   14. Install Poetry: curl -sSL https://install.python-poetry.org | python3 -
#   15. Clone YOVA: git clone https://github.com/jamro/yova.git
#   16. Install YOVA: cd yova && poetry config keyring.enabled false && make install
#   17. Configure API: nano yova.config.json (add your OpenAI API key)
#   18. Setup service: sudo cp scripts/supervisord.service /etc/systemd/system/ && sudo systemctl daemon-reload && sudo systemctl enable supervisord.service && sudo systemctl start supervisord.service
#
# PHASE 5: Testing and Validation (no reboot needed)
#   19. Test YOVA: Press push-to-talk button and ask a question
#   20. Check service: sudo systemctl status supervisord.service
#   21. View logs: sudo journalctl -u supervisord.service -f
main() {
    echo "=========================================="
    echo "    YOVA Installation Script"
    echo "=========================================="
    echo ""
    echo "This script will automatically:"
    echo "- Install all system dependencies"
    echo "- Configure ReSpeaker HAT audio"
    echo "- Set up YOVA with Python Poetry"
    echo "- Prompt for and configure your OpenAI API key"
    echo "- Set up systemd services"
    echo "- Test audio playback to ensure proper configuration"
    echo "- Test audio recording to ensure microphone functionality"
    echo ""
    
    # Pre-flight checks
    check_raspberry_pi
    check_root
    check_pi_user
    
    # Installation steps
    update_system
    install_dependencies
    configure_gpio
    install_respeaker_drivers
    configure_boot_config
    enable_spi
    
    # Handle reboot if needed
    handle_reboot
    
    # Continue with remaining steps after potential reboot
    configure_alsa
    test_playback 
    test_recording
    
    install_poetry
    install_yova
    configure_openai_api
    configure_systemd

    # Handle reboot if needed
    handle_reboot
    
    # Post-installation
    post_install_instructions
}

# Run main function
main "$@"

# =============================================================================
# MANUAL INSTALLATION GUIDE USAGE
# =============================================================================
# 
# This script serves as both an automated installer AND a comprehensive manual guide.
#
# TO USE AS AUTOMATED INSTALLER:
#   bash install.sh
#
# TO USE AS MANUAL GUIDE:
#   1. Read the header comments for an overview
#   2. Read each function's comments for step-by-step instructions
#   3. Follow the manual commands provided in each section
#   4. Use the main() function comments as a complete installation checklist
#
# KEY MANUAL INSTALLATION POINTS:
# - System dependencies must be installed first
# - ReSpeaker HAT drivers require a reboot after configuration
# - Audio testing is critical and must pass before continuing
# - OpenAI API key is required for YOVA to function
# - Service configuration ensures YOVA runs automatically
#
# TROUBLESHOOTING:
# - Check service status: sudo systemctl status supervisord.service
# - View logs: sudo journalctl -u supervisord.service -f
# - Test audio manually: aplay -l && arecord -l
# - Verify hardware connections and power supply
#
# For more detailed information, see: docs/install.md
# =============================================================================
