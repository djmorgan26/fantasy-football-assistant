#!/bin/bash

# Fantasy Football Assistant - Docker Setup Script

set -e

echo "🐳 Fantasy Football Assistant - Docker Setup"
echo "============================================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is required but not installed"
    echo "Please install Docker Desktop and try again"
    exit 1
fi

# Check if Docker Compose is available
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose is required but not installed"
    exit 1
fi

echo "✅ Docker found"

# Create .env file for docker-compose if it doesn't exist
if [[ ! -f ".env" ]]; then
    echo "Creating .env file for Docker Compose..."
    cat > .env << EOL
# Database
POSTGRES_PASSWORD=fantasy_password_change_this

# Backend
SECRET_KEY=your-super-secret-key-change-this-in-production
DEBUG=false
LOG_LEVEL=INFO

# You can add your ESPN credentials here or in the app later
# ESPN_S2=
# ESPN_SWID=
EOL
    echo "⚠️  Please edit .env file with secure passwords and keys"
fi

# Build and start services
echo ""
echo "🔨 Building Docker images..."
if command -v docker-compose &> /dev/null; then
    docker-compose build
else
    docker compose build
fi

echo ""
echo "🚀 Starting services..."
if command -v docker-compose &> /dev/null; then
    docker-compose up -d
else
    docker compose up -d
fi

echo ""
echo "⏳ Waiting for services to be healthy..."
sleep 10

# Check service health
echo ""
echo "🔍 Checking service status..."
if command -v docker-compose &> /dev/null; then
    docker-compose ps
else
    docker compose ps
fi

echo ""
echo "📋 Running database migrations..."
if command -v docker-compose &> /dev/null; then
    docker-compose exec backend alembic upgrade head
else
    docker compose exec backend alembic upgrade head
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "🌐 Services are running at:"
echo "  - Frontend: http://localhost:3000"
echo "  - Backend API: http://localhost:8000"
echo "  - API Documentation: http://localhost:8000/docs"
echo "  - Database: localhost:5432"
echo "  - Redis: localhost:6379"
echo ""
echo "📋 Useful commands:"
if command -v docker-compose &> /dev/null; then
    echo "  - View logs: docker-compose logs -f [service]"
    echo "  - Stop services: docker-compose down"
    echo "  - Restart: docker-compose restart"
    echo "  - Update: docker-compose pull && docker-compose up -d"
else
    echo "  - View logs: docker compose logs -f [service]"
    echo "  - Stop services: docker compose down"
    echo "  - Restart: docker compose restart"
    echo "  - Update: docker compose pull && docker compose up -d"
fi
echo ""
echo "⚠️  Remember to:"
echo "1. Edit the .env file with secure passwords"
echo "2. Add your ESPN credentials in the app settings"