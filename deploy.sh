#!/bin/bash

# Docker deployment script for Ubuntu 18.04

echo "=== NoctisView Docker Deployment Script ==="
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Docker is not installed. Installing Docker..."
    
    # Update package index
    sudo apt-get update
    
    # Install dependencies
    sudo apt-get install -y \
        apt-transport-https \
        ca-certificates \
        curl \
        gnupg \
        lsb-release
    
    # Add Docker's official GPG key
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    
    # Set up stable repository
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
      $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    # Install Docker Engine
    sudo apt-get update
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io
    
    # Add current user to docker group
    sudo usermod -aG docker $USER
    echo "Docker installed successfully! Please log out and back in for group changes to take effect."
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "Docker Compose is not installed. Installing Docker Compose..."
    
    # Download Docker Compose
    sudo curl -L "https://github.com/docker/compose/releases/download/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    
    # Apply executable permissions
    sudo chmod +x /usr/local/bin/docker-compose
    
    echo "Docker Compose installed successfully!"
fi

# Display Docker versions
echo ""
echo "Docker version:"
docker --version
echo "Docker Compose version:"
docker-compose --version

echo ""
echo "=== Deployment Options ==="
echo "1. Build and run with Docker only"
echo "2. Build and run with Docker Compose (recommended)"
echo ""
read -p "Choose option (1 or 2): " option

case $option in
    1)
        echo ""
        echo "Building Docker image..."
        docker build -t noctisview:latest .
        
        echo ""
        echo "Running Docker container..."
        docker run -d \
            --name noctisview-app \
            -p 8000:8000 \
            -v $(pwd)/media:/app/media \
            -v $(pwd)/logs:/app/logs \
            -e DJANGO_SETTINGS_MODULE=noctisview.settings \
            noctisview:latest
        
        echo ""
        echo "Application is running at http://localhost:8000"
        echo "To stop: docker stop noctisview-app"
        echo "To remove: docker rm noctisview-app"
        ;;
        
    2)
        echo ""
        echo "Building and starting services with Docker Compose..."
        docker-compose up -d --build
        
        echo ""
        echo "Waiting for services to start..."
        sleep 5
        
        echo ""
        echo "Running database migrations..."
        docker-compose exec web python3.8 manage.py migrate
        
        echo ""
        echo "Creating superuser (optional)..."
        read -p "Do you want to create a superuser? (y/n): " create_super
        if [ "$create_super" = "y" ]; then
            docker-compose exec web python3.8 manage.py createsuperuser
        fi
        
        echo ""
        echo "Services are running:"
        echo "- Application: http://localhost (via nginx)"
        echo "- Direct access: http://localhost:8000"
        echo ""
        echo "To view logs: docker-compose logs -f"
        echo "To stop: docker-compose down"
        echo "To remove volumes: docker-compose down -v"
        ;;
        
    *)
        echo "Invalid option. Exiting."
        exit 1
        ;;
esac

echo ""
echo "=== Deployment Complete ==="