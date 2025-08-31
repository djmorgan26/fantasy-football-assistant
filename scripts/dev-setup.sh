#!/bin/bash

# Fantasy Football Assistant - Development Setup Script

set -e

echo "🏈 Fantasy Football Assistant - Development Setup"
echo "================================================"

# Check prerequisites
echo "Checking prerequisites..."

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1-2)
if [[ $(echo "$PYTHON_VERSION < 3.11" | bc -l) ]]; then
    echo "❌ Python 3.11+ is required (found $PYTHON_VERSION)"
    exit 1
fi
echo "✅ Python $PYTHON_VERSION found"

# Check Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is required but not installed"
    exit 1
fi

NODE_VERSION=$(node --version | cut -d'v' -f2 | cut -d'.' -f1)
if [[ $NODE_VERSION -lt 18 ]]; then
    echo "❌ Node.js 18+ is required (found v$NODE_VERSION)"
    exit 1
fi
echo "✅ Node.js $(node --version) found"

# Check PostgreSQL
if ! command -v psql &> /dev/null; then
    echo "❌ PostgreSQL is required but not installed"
    echo "Please install PostgreSQL 14+ and try again"
    exit 1
fi
echo "✅ PostgreSQL found"

# Backend setup
echo ""
echo "🔧 Setting up backend..."
cd backend

# Create virtual environment
if [[ ! -d "venv" ]]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Copy environment file
if [[ ! -f ".env" ]]; then
    echo "Creating backend .env file..."
    cp .env.example .env
    echo "⚠️  Please edit backend/.env with your configuration"
fi

# Frontend setup
echo ""
echo "🎨 Setting up frontend..."
cd ../frontend

# Install dependencies
echo "Installing Node.js dependencies..."
npm install

# Copy environment file
if [[ ! -f ".env.local" ]]; then
    echo "Creating frontend .env.local file..."
    cp .env.example .env.local
fi

# Database setup
echo ""
echo "🗄️  Setting up database..."
echo "Please ensure PostgreSQL is running and create the database:"
echo "  createdb fantasy_football_db"
echo ""
echo "Then run migrations from the backend directory:"
echo "  cd backend"
echo "  source venv/bin/activate"
echo "  alembic upgrade head"

echo ""
echo "✅ Setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Edit backend/.env with your database connection and ESPN credentials"
echo "2. Create the database: createdb fantasy_football_db"
echo "3. Run migrations: cd backend && source venv/bin/activate && alembic upgrade head"
echo "4. Start the backend: cd backend && source venv/bin/activate && uvicorn app.main:app --reload"
echo "5. Start the frontend: cd frontend && npm run dev"
echo ""
echo "🌐 Access the app at http://localhost:3000"
echo "📚 API docs at http://localhost:8000/docs"