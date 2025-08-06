#!/bin/bash

# Docker Installation Script for Ubuntu Server
# This script automates the Docker installation process

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_message() {
    echo -e "${2}${1}${NC}"
}

# Function to check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        print_message "This script should not be run as root. Please run as a regular user with sudo privileges." $RED
        exit 1
    fi
}

# Function to check Ubuntu version
check_ubuntu_version() {
    print_message "Checking Ubuntu version..." $YELLOW
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        if [[ "$ID" != "ubuntu" ]]; then
            print_message "This script is designed for Ubuntu. Detected: $ID" $RED
            exit 1
        fi
        print_message "Ubuntu $VERSION detected" $GREEN
    else
        print_message "Cannot detect OS version" $RED
        exit 1
    fi
}

# Function to update system
update_system() {
    print_message "Updating system packages..." $YELLOW
    sudo apt update
    sudo apt upgrade -y
    print_message "System updated successfully" $GREEN
}

# Function to install prerequisites
install_prerequisites() {
    print_message "Installing prerequisites..." $YELLOW
    sudo apt install -y \
        ca-certificates \
        curl \
        gnupg \
        lsb-release \
        software-properties-common \
        apt-transport-https
    print_message "Prerequisites installed successfully" $GREEN
}

# Function to remove old Docker versions
remove_old_docker() {
    print_message "Removing old Docker versions if any..." $YELLOW
    sudo apt remove -y docker docker-engine docker.io containerd runc || true
    print_message "Old Docker versions removed" $GREEN
}

# Function to install Docker
install_docker() {
    print_message "Installing Docker..." $YELLOW
    
    # Add Docker's official GPG key
    sudo mkdir -m 0755 -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    
    # Add Docker repository
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
      $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    # Update package index
    sudo apt update
    
    # Install Docker
    sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    
    print_message "Docker installed successfully" $GREEN
}

# Function to configure Docker
configure_docker() {
    print_message "Configuring Docker..." $YELLOW
    
    # Add current user to docker group
    sudo usermod -aG docker $USER
    
    # Create Docker daemon configuration
    sudo mkdir -p /etc/docker
    sudo tee /etc/docker/daemon.json > /dev/null <<EOF
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "storage-driver": "overlay2",
  "live-restore": true,
  "userland-proxy": false
}
EOF
    
    # Restart Docker
    sudo systemctl restart docker
    sudo systemctl enable docker
    
    print_message "Docker configured successfully" $GREEN
}

# Function to verify installation
verify_installation() {
    print_message "Verifying Docker installation..." $YELLOW
    
    # Check Docker version
    docker --version
    
    # Check Docker Compose version
    docker compose version
    
    print_message "Docker installation verified" $GREEN
}

# Function to show post-installation steps
post_installation() {
    print_message "\n=== Post-Installation Steps ===" $YELLOW
    print_message "1. Log out and log back in for group changes to take effect" $GREEN
    print_message "2. Run 'docker run hello-world' to test Docker" $GREEN
    print_message "3. Configure firewall rules if needed" $GREEN
    print_message "4. Set up Docker Swarm or Kubernetes if required" $GREEN
    print_message "\n=== Security Recommendations ===" $YELLOW
    print_message "1. Enable Docker Content Trust: export DOCKER_CONTENT_TRUST=1" $GREEN
    print_message "2. Use Docker Bench for Security: docker run -it --net host --pid host --cap-add audit_control -v /var/lib:/var/lib -v /var/run/docker.sock:/var/run/docker.sock -v /etc:/etc --label docker_bench_security docker/docker-bench-security" $GREEN
    print_message "3. Regularly update Docker and base images" $GREEN
}

# Main execution
main() {
    print_message "=== Docker Installation Script for Ubuntu ===" $YELLOW
    
    check_root
    check_ubuntu_version
    update_system
    install_prerequisites
    remove_old_docker
    install_docker
    configure_docker
    verify_installation
    post_installation
    
    print_message "\n=== Installation Complete! ===" $GREEN
    print_message "Please log out and log back in to use Docker without sudo" $YELLOW
}

# Run main function
main