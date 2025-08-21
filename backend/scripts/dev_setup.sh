#!/bin/bash
# Development setup script

set -e

echo "🚀 Setting up Financial Nomad API development environment..."

# Change to backend directory
cd "$(dirname "$0")/.."

# Check Python version
python3.11 --version || {
    echo "❌ Python 3.11 is required but not found"
    echo "Please install Python 3.11 first"
    exit 1
}

# Create virtual environment
echo "📦 Creating virtual environment..."
python3.11 -m venv venv

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install development dependencies
echo "📥 Installing development dependencies..."
pip install -r requirements-dev.txt

# Copy example environment file
if [ ! -f ".env" ]; then
    echo "📋 Creating .env file from example..."
    cp .env.example .env
    echo "⚠️  Please edit .env file with your configuration"
fi

# Install pre-commit hooks
echo "🪝 Installing pre-commit hooks..."
pre-commit install

# Check if Docker is available
if command -v docker &> /dev/null; then
    echo "🐳 Docker found - you can use docker compose for development"
    echo "   Run: docker compose up -d"
else
    echo "⚠️  Docker not found - install Docker for easier development"
fi

# Check if gcloud is available
if command -v gcloud &> /dev/null; then
    echo "☁️  Google Cloud SDK found - Firestore emulator available"
else
    echo "⚠️  Google Cloud SDK not found"
    echo "   Install it for Firestore emulator: https://cloud.google.com/sdk/docs/install"
fi

echo ""
echo "✅ Development environment setup complete!"
echo ""
echo "🏃 Quick start:"
echo "   1. Activate virtual environment: source venv/bin/activate"
echo "   2. Edit .env file with your configuration"
echo "   3. Start development server: uvicorn src.main:app --reload"
echo "   4. Or use Docker: docker compose up"
echo ""
echo "🧪 Run tests: ./scripts/run_tests.sh"
echo "📖 API docs: http://localhost:8080/docs"