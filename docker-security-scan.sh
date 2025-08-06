#!/bin/bash

# Docker Security Scanning Script
# This script performs security checks on Docker images and running containers

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_message() {
    echo -e "${2}${1}${NC}"
}

# Function to check if Docker is installed
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_message "Docker is not installed. Please install Docker first." $RED
        exit 1
    fi
}

# Function to run Docker Bench Security
run_docker_bench() {
    print_message "\n=== Running Docker Bench Security ===" $BLUE
    docker run --rm --net host --pid host --userns host --cap-add audit_control \
        -e DOCKER_CONTENT_TRUST=$DOCKER_CONTENT_TRUST \
        -v /var/lib:/var/lib:ro \
        -v /var/run/docker.sock:/var/run/docker.sock:ro \
        -v /usr/lib/systemd:/usr/lib/systemd:ro \
        -v /etc:/etc:ro \
        --label docker_bench_security \
        docker/docker-bench-security
}

# Function to scan images with Trivy
scan_images_trivy() {
    print_message "\n=== Scanning Docker Images with Trivy ===" $BLUE
    
    # Install Trivy if not present
    if ! command -v trivy &> /dev/null; then
        print_message "Installing Trivy..." $YELLOW
        docker pull aquasec/trivy:latest
    fi
    
    # Get all images
    images=$(docker images --format "{{.Repository}}:{{.Tag}}" | grep -v "<none>")
    
    for image in $images; do
        print_message "\nScanning image: $image" $YELLOW
        docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
            aquasec/trivy:latest image --severity HIGH,CRITICAL $image
    done
}

# Function to check for exposed secrets
check_secrets() {
    print_message "\n=== Checking for Exposed Secrets ===" $BLUE
    
    # Check running containers for environment variables
    containers=$(docker ps -q)
    
    for container in $containers; do
        container_name=$(docker inspect --format '{{.Name}}' $container | sed 's/^///')
        print_message "\nChecking container: $container_name" $YELLOW
        
        # Check for common secret patterns in env vars
        docker exec $container env | grep -E "(PASSWORD|SECRET|KEY|TOKEN|PRIVATE|CREDENTIAL)" | grep -v "PUBLIC" || true
    done
}

# Function to audit Docker daemon configuration
audit_daemon_config() {
    print_message "\n=== Auditing Docker Daemon Configuration ===" $BLUE
    
    # Check if daemon.json exists
    if [ -f /etc/docker/daemon.json ]; then
        print_message "Docker daemon configuration found:" $GREEN
        cat /etc/docker/daemon.json
    else
        print_message "No daemon.json found. Using default configuration." $YELLOW
    fi
    
    # Check Docker root directory permissions
    docker_root=$(docker info 2>/dev/null | grep "Docker Root Dir" | awk '{print $NF}')
    if [ -n "$docker_root" ]; then
        print_message "\nDocker root directory: $docker_root" $YELLOW
        ls -la $docker_root | head -5
    fi
}

# Function to check container capabilities
check_container_capabilities() {
    print_message "\n=== Checking Container Capabilities ===" $BLUE
    
    containers=$(docker ps -q)
    
    for container in $containers; do
        container_name=$(docker inspect --format '{{.Name}}' $container | sed 's/^///')
        print_message "\nContainer: $container_name" $YELLOW
        
        # Check if running as privileged
        privileged=$(docker inspect --format '{{.HostConfig.Privileged}}' $container)
        if [ "$privileged" = "true" ]; then
            print_message "WARNING: Container is running in privileged mode!" $RED
        else
            print_message "Container is not running in privileged mode" $GREEN
        fi
        
        # Check capabilities
        cap_add=$(docker inspect --format '{{.HostConfig.CapAdd}}' $container)
        cap_drop=$(docker inspect --format '{{.HostConfig.CapDrop}}' $container)
        print_message "Added capabilities: $cap_add" $YELLOW
        print_message "Dropped capabilities: $cap_drop" $YELLOW
    done
}

# Function to check network exposure
check_network_exposure() {
    print_message "\n=== Checking Network Exposure ===" $BLUE
    
    # List all published ports
    print_message "\nPublished ports:" $YELLOW
    docker ps --format "table {{.Names}}\t{{.Ports}}"
    
    # Check for containers using host network
    print_message "\nContainers using host network:" $YELLOW
    docker ps --filter "network=host" --format "table {{.Names}}\t{{.ID}}"
}

# Function to generate security report
generate_report() {
    print_message "\n=== Security Scan Summary ===" $BLUE
    
    report_file="docker-security-report-$(date +%Y%m%d-%H%M%S).txt"
    
    {
        echo "Docker Security Scan Report"
        echo "Generated: $(date)"
        echo "=========================="
        echo ""
        echo "System Information:"
        echo "Docker Version: $(docker --version)"
        echo "Docker Compose Version: $(docker compose version 2>/dev/null || echo 'Not installed')"
        echo ""
        echo "Running Containers: $(docker ps -q | wc -l)"
        echo "Total Images: $(docker images -q | wc -l)"
        echo "Total Volumes: $(docker volume ls -q | wc -l)"
        echo "Total Networks: $(docker network ls -q | wc -l)"
        echo ""
        echo "Security Recommendations:"
        echo "1. Regularly update Docker and base images"
        echo "2. Use Docker Content Trust (DOCKER_CONTENT_TRUST=1)"
        echo "3. Implement least privilege principle"
        echo "4. Scan images before deployment"
        echo "5. Use secrets management for sensitive data"
        echo "6. Enable Docker daemon logging"
        echo "7. Implement network segmentation"
        echo "8. Regular security audits"
    } > $report_file
    
    print_message "Report saved to: $report_file" $GREEN
}

# Function to show menu
show_menu() {
    echo ""
    print_message "Docker Security Scanner" $BLUE
    print_message "======================" $BLUE
    echo "1. Run full security scan"
    echo "2. Run Docker Bench Security"
    echo "3. Scan images with Trivy"
    echo "4. Check for exposed secrets"
    echo "5. Audit daemon configuration"
    echo "6. Check container capabilities"
    echo "7. Check network exposure"
    echo "8. Generate security report"
    echo "9. Exit"
    echo ""
}

# Main function
main() {
    check_docker
    
    while true; do
        show_menu
        read -p "Select an option: " choice
        
        case $choice in
            1)
                run_docker_bench
                scan_images_trivy
                check_secrets
                audit_daemon_config
                check_container_capabilities
                check_network_exposure
                generate_report
                ;;
            2)
                run_docker_bench
                ;;
            3)
                scan_images_trivy
                ;;
            4)
                check_secrets
                ;;
            5)
                audit_daemon_config
                ;;
            6)
                check_container_capabilities
                ;;
            7)
                check_network_exposure
                ;;
            8)
                generate_report
                ;;
            9)
                print_message "Exiting..." $GREEN
                exit 0
                ;;
            *)
                print_message "Invalid option. Please try again." $RED
                ;;
        esac
    done
}

# Run main function
main