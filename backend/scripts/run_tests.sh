#!/bin/bash
# Script to run the complete test suite

set -e

echo "🧪 Running Financial Nomad API test suite..."

# Change to backend directory
cd "$(dirname "$0")/.."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3.11 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements-test.txt

# Set test environment variables
export DEBUG=false
export ENVIRONMENT=testing
export USE_FIRESTORE_EMULATOR=true
export FIRESTORE_EMULATOR_HOST=localhost:8081
export GOOGLE_CLIENT_ID=test-client-id
export SECRET_KEY=test-secret-key-for-testing
export FIRESTORE_PROJECT_ID=test-project

# Start Firestore emulator in background
echo "🔥 Starting Firestore emulator..."
gcloud emulators firestore start --host-port=localhost:8081 --project=test-project &
FIRESTORE_PID=$!

# Wait for emulator to start
sleep 5

# Trap to cleanup emulator on exit
cleanup() {
    echo "🧹 Cleaning up..."
    if [ ! -z "$FIRESTORE_PID" ]; then
        kill $FIRESTORE_PID 2>/dev/null || true
    fi
}
trap cleanup EXIT

# Run linting
echo "🔍 Running linting..."
ruff check src tests

# Run type checking  
echo "🏷️  Running type checking..."
mypy src

# Run security scan
echo "🔒 Running security scan..."
bandit -r src -ll

# Run unit tests
echo "🧪 Running unit tests..."
pytest tests/unit -v --cov=src --cov-report=term-missing --cov-report=html

# Run integration tests
echo "🔗 Running integration tests..."
pytest tests/integration -v --cov=src --cov-append

# Check coverage threshold
echo "📊 Checking coverage threshold..."
coverage report --fail-under=85

echo "✅ All tests passed!"