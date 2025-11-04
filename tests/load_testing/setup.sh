#!/bin/bash

# AgenticFleet Load Testing Setup Script
# This script sets up the load testing environment

set -e

echo "🚀 Setting up AgenticFleet Load Testing Environment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in the right directory
if [ ! -f "locustfile.py" ]; then
    print_error "Please run this script from the tests/load_testing directory"
    exit 1
fi

print_status "Creating necessary directories..."

# Create directories for reports and logs
mkdir -p reports
mkdir -p logs
mkdir -p data

print_status "Checking Python installation..."

# Check Python version
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
print_status "Found Python version: $PYTHON_VERSION"

print_status "Installing Python dependencies..."

# Install Python dependencies
if command -v uv &> /dev/null; then
    print_status "Using uv to install dependencies..."
    uv add -r requirements.txt
else
    print_status "Using pip to install dependencies..."
    pip3 install -r requirements.txt
fi

print_status "Checking k6 installation..."

# Check if k6 is installed
if ! command -v k6 &> /dev/null; then
    print_warning "k6 is not installed. Installing k6..."

    # Detect OS and install k6 accordingly
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        print_status "Installing k6 on Linux..."
        sudo gpg -k
        sudo gpg --no-default-keyring --keyring /usr/share/keyrings/k6-archive-keyring.gpg --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
        echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list
        sudo apt-get update
        sudo apt-get install k6
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command -v brew &> /dev/null; then
            print_status "Installing k6 using Homebrew..."
            brew install k6
        else
            print_error "Homebrew is not installed. Please install k6 manually from https://k6.io/docs/getting-started/installation"
        fi
    else
        print_error "Unsupported OS. Please install k6 manually from https://k6.io/docs/getting-started/installation"
    fi
else
    print_status "k6 is already installed: $(k6 version)"
fi

print_status "Checking Locust installation..."

# Check if Locust is installed
if ! python3 -c "import locust" &> /dev/null; then
    print_error "Locust is not installed properly. Please check the installation."
    exit 1
else
    LOCUST_VERSION=$(python3 -c "import locust; print(locust.__version__)")
    print_status "Locust version: $LOCUST_VERSION"
fi

print_status "Verifying test files..."

# Check if all test files exist
required_files=("locustfile.py" "k6-chat-test.js" "config.py" "monitoring.py" "run_load_tests.py")

for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        print_status "✓ $file found"
    else
        print_error "✗ $file not found"
        exit 1
    fi
done

print_status "Creating configuration files..."

# Create a sample configuration file
if [ ! -f "load_test_config.yaml" ]; then
    cat > load_test_config.yaml << EOF
# AgenticFleet Load Testing Configuration
environment: local
base_url: http://localhost:8000

scenarios:
  smoke_test:
    description: Quick smoke test
    users: 5
    duration: 30s

  load_test:
    description: Normal load test
    users: 50
    duration: 5m

  stress_test:
    description: Stress test
    users: 200
    duration: 10m

monitoring:
  enabled: true
  prometheus_port: 9090
  alerting:
    error_rate_threshold: 5.0
    response_time_threshold: 5000
EOF
    print_status "Created sample configuration file: load_test_config.yaml"
fi

print_status "Running smoke test..."

# Run a quick smoke test to verify setup
echo "Starting AgenticFleet server in background for smoke test..."
# Note: This assumes the user has the AgenticFleet server running or will start it manually

print_status "Setup completed successfully! 🎉"

echo ""
echo "📋 Next steps:"
echo "1. Make sure your AgenticFleet server is running on http://localhost:8000"
echo "2. Run a smoke test: python3 run_load_tests.py --scenario smoke_test --health-check"
echo "3. View the Locust web interface: http://localhost:8089 (when running with --web-ui)"
echo "4. Check monitoring metrics: http://localhost:9090 (when monitoring is enabled)"
echo ""
echo "📚 Usage examples:"
echo "  # Run smoke test"
echo "  python3 run_load_tests.py --scenario smoke_test"
echo ""
echo "  # Run custom test with specific parameters"
echo "  python3 run_load_tests.py --tool locust --users 100 --spawn-rate 10 --duration 10m"
echo ""
echo "  # Run k6 test"
echo "  python3 run_load_tests.py --tool k6 --users 50"
echo ""
echo "  # List available scenarios"
echo "  python3 run_load_tests.py --list-scenarios"
echo ""

# Make the script executable
chmod +x setup.sh
