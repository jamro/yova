#!/bin/bash

# YOVA Installation Script for Raspberry Pi
# This script automates the manual installation process

set -e  # Exit on any error

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

# Function to prompt for OpenAI API key and inject it into config
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

# Function to check if running on Raspberry Pi
check_raspberry_pi() {
    if ! grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then
        print_error "This script must be run on a Raspberry Pi"
        exit 1
    fi
    print_success "Raspberry Pi detected"
}

# Function to check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        print_error "This script should not be run as root. Please run as pi user."
        exit 1
    fi
}

# Function to check if pi user exists
check_pi_user() {
    if ! id "pi" &>/dev/null; then
        print_error "User 'pi' does not exist. Please create it first."
        exit 1
    fi
    print_success "User 'pi' found"
}

# Function to update system
update_system() {
    print_status "Updating system packages..."
    sudo apt update
    DEBIAN_FRONTEND=noninteractive sudo apt upgrade -y -o Dpkg::Options::="--force-confnew"
    print_success "System updated"
}

# Function to install dependencies
install_dependencies() {
    print_status "Installing system dependencies..."
    sudo apt install -y build-essential python3-dev libasound2-dev libportaudio2 \
        portaudio19-dev libportaudiocpp0 libjack-jackd2-dev python3-rpi-lgpio \
        curl alsa-utils jq
    print_success "Dependencies installed"
}

# Function to configure GPIO access
configure_gpio() {
    print_status "Configuring GPIO access..."
    sudo usermod -aG gpio pi
    print_success "GPIO access configured"
}

# Function to install ReSpeaker HAT drivers
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

# Function to detect ReSpeaker HAT device
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
enable_spi() {
    print_status "Enabling SPI interface..."
    
    # Check if SPI is already enabled
    if ! grep -q "dtparam=spi=on" /boot/firmware/config.txt; then
        echo "dtparam=spi=on" | sudo tee -a /boot/firmware/config.txt
        print_success "SPI enabled in boot config"
        REBOOT_NEEDED=true
    else
        print_warning "SPI already enabled in boot config"
    fi
}

# Function to install Python Poetry
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

# Function to clone and install YOVA
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
    poetry install
    
    # Copy configuration
    if [ ! -f "yova.config.json" ]; then
        cp yova.config.default.json yova.config.json
        print_success "Configuration file created from template"
    fi
    
    print_success "YOVA installed at /home/pi/yova"
}

# Function to configure systemd service
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
        print_success "Systemd service configured"
        REBOOT_NEEDED=true
    else
        print_warning "supervisord.service not found, skipping systemd configuration"
    fi
}

# Function to test audio playback
test_playback() {
    print_status "Testing audio playback..."
    echo ""
    echo "This test will play a test sound through your ReSpeaker HAT."
    echo "Please ensure your speaker is connected and volume is set appropriately."
    echo ""
    
    read -p "Press Enter to continue with the audio test..."
    
    local test_success=false
    local test_attempts=0
    local max_attempts=10
    
    while [ "$test_success" = false ] && [ $test_attempts -lt $max_attempts ]; do
        test_attempts=$((test_attempts + 1))
        echo ""
        print_status "Audio test attempt $test_attempts of $max_attempts"
        echo "Playing test sound..."
        
        # Check if test file exists
        local test_file="/home/pi/yova/yova_shared/assets/test_sound.wav"
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

# Function to provide post-installation instructions
post_install_instructions() {
    print_success "Installation completed!"
    echo ""
    
    if [ -n "$RESPEAKER_CARD" ] && [ -n "$RESPEAKER_DEVICE" ]; then
        echo "ReSpeaker HAT detected and configured:"
        echo "- Card: $RESPEAKER_CARD"
        echo "- Device: $RESPEAKER_DEVICE"
        echo ""
    fi
    
    echo "Next steps:"
    echo "1. Adjust audio volume: alsamixer"
    echo "2. Start YOVA: sudo systemctl start supervisord.service"
    echo "3. Check status: sudo systemctl status supervisord.service"
    echo "4. View logs: sudo journalctl -u supervisord.service -f"
    echo ""
    echo "For manual volume adjustment:"
    echo "- Press F6 to select output device 'seeed2micvoicec'"
    echo "- Set PCM to 100%"
    echo "- Set Line DAC to 100%"
    echo "- Save settings: sudo alsactl store"
}

# Function to handle reboot confirmation and execution
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
            print ""
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

# Main installation function
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
    install_poetry
    install_yova
    configure_openai_api
    configure_systemd

    # Handle reboot if needed
    handle_reboot
    
    # Post-installation
    test_playback 
    test_recording
    post_install_instructions
}

# Run main function
main "$@"
