# AgenticFleet Load Testing Suite

Comprehensive load testing framework for AgenticFleet API, designed to validate performance under various load conditions.

## 🎯 Overview

This load testing suite provides complete performance testing capabilities for AgenticFleet, including:

- **Chat API Load Testing**: Test both regular and streaming chat functionality
- **Workflow Performance**: Validate workflow orchestration performance
- **System Health Monitoring**: Real-time metrics and alerting
- **Multiple Testing Tools**: Support for Locust (Python) and k6 (JavaScript)
- **Comprehensive Reporting**: Detailed performance analysis and recommendations

## 🏗️ Architecture

```
tests/load_testing/
├── locustfile.py              # Main Locust test script
├── k6-chat-test.js           # k6 JavaScript test script
├── config.py                 # Configuration management
├── monitoring.py             # Real-time performance monitoring
├── run_load_tests.py         # Main test runner
├── setup.sh                  # Environment setup script
├── requirements.txt          # Python dependencies
├── reports/                  # Test reports directory
├── logs/                     # Log files directory
└── README.md                 # This file
```

## 🚀 Quick Start

### 1. Environment Setup

```bash
# Navigate to the load testing directory
cd tests/load_testing

# Run the setup script
./setup.sh
```

### 2. Start AgenticFleet Server

Make sure your AgenticFleet server is running:

```bash
# From the project root
make backend

# Or using uv directly
uv run agentic-fleet
```

### 3. Run Your First Test

```bash
# Run a smoke test to verify everything works
python3 run_load_tests.py --scenario smoke_test --health-check
```

## 📊 Test Scenarios

### Predefined Scenarios

1. **Smoke Test** (`smoke_test`)
   - Users: 5
   - Duration: 30 seconds
   - Purpose: Quick validation of basic functionality

2. **Normal Load** (`normal_load`)
   - Users: 50
   - Duration: 5 minutes
   - Purpose: Simulate normal user traffic

3. **Stress Test** (`stress_test`)
   - Users: 200
   - Duration: 10 minutes
   - Purpose: Test system limits and failure modes

4. **Spike Test** (`spike_test`)
   - Base users: 5, Spike to: 150
   - Duration: 2 minutes
   - Purpose: Test response to sudden load spikes

5. **Endurance Test** (`endurance_test`)
   - Users: 30
   - Duration: 30 minutes
   - Purpose: Test stability under sustained load

### Available Scenarios

```bash
# List all available scenarios
python3 run_load_tests.py --list-scenarios
```

## 🛠️ Testing Tools

### Locust (Python-based)

**Pros:**

- Python scripting (matches your tech stack)
- Excellent for FastAPI applications
- Great for streaming endpoints
- Web-based UI for real-time monitoring
- Distributed testing support

**Usage:**

```bash
# Run predefined scenario
python3 run_load_tests.py --tool locust --scenario normal_load

# Run with custom parameters
python3 run_load_tests.py --tool locust --users 100 --spawn-rate 10 --duration 10m

# Run with web UI (for interactive testing)
locust -f locustfile.py --host http://localhost:8000
```

### k6 (JavaScript-based)

**Pros:**

- Modern JavaScript/TypeScript support
- Excellent performance and resource efficiency
- Great for CI/CD integration
- Detailed metrics collection
- HTTP/2 support

**Usage:**

```bash
# Run k6 test
python3 run_load_tests.py --tool k6 --users 50

# Run k6 directly
k6 run k6-chat-test.js

# Run with environment variables
BASE_URL=http://localhost:8000 VUS=100 k6 run k6-chat-test.js
```

## 📈 Monitoring and Metrics

### Real-time Monitoring

The suite includes comprehensive monitoring with:

- **Prometheus Metrics**: Available at `http://localhost:9090/metrics`
- **System Metrics**: CPU, memory, disk usage
- **Application Metrics**: Response times, error rates, active users
- **Alerting**: Configurable thresholds for automated alerts

### Key Metrics Tracked

1. **HTTP Metrics**
   - Request count by endpoint and status
   - Response time distribution (50th, 95th, 99th percentiles)
   - Error rates

2. **Chat-Specific Metrics**
   - Chat request count (streaming vs non-streaming)
   - Time to first token (TTFT)
   - Total chat response time

3. **System Metrics**
   - CPU usage percentage
   - Memory usage percentage
   - Disk usage

4. **Workflow Metrics**
   - Workflow request count
   - Workflow response time

### Metrics Collection

Metrics are automatically collected during test runs and saved to:

- JSON format: `reports/{test_name}_metrics.json`
- HTML reports: `reports/{test_name}_report.html` (Locust)
- CSV data: `reports/{test_name}_stats.csv` (Locust)

## 🔧 Configuration

### Environment Configuration

Configure different environments using environment variables:

```bash
export AGENTICFLEET_API_KEY="your-api-key"
export DEV_API_URL="https://dev-api.agenticfleet.com"
export STAGING_API_URL="https://staging-api.agenticfleet.com"
export PROD_API_URL="https://api.agenticfleet.com"
```

### Custom Configuration

Create a custom configuration file:

```yaml
# load_test_config.yaml
environment: staging
base_url: https://staging-api.agenticfleet.com

scenarios:
  custom_scenario:
    description: Custom test scenario
    users: 75
    duration: 8m

monitoring:
  enabled: true
  prometheus_port: 9090
  alerting:
    error_rate_threshold: 3.0
    response_time_threshold: 3000
```

## 📊 Test Results and Reporting

### Report Types

1. **HTML Reports** (Locust)
   - Interactive web-based reports
   - Charts and graphs
   - Response time distributions

2. **JSON Metrics**
   - Raw metrics data
   - System performance data
   - Alert information

3. **CSV Data** (Locust)
   - Request statistics
   - Error breakdown
   - Response time data

### Interpreting Results

Key metrics to monitor:

- **Average Response Time**: Should be under 5 seconds for chat
- **95th Percentile Response Time**: Should be under 10 seconds
- **Error Rate**: Should be under 5%
- **CPU Usage**: Should stay under 80%
- **Memory Usage**: Should stay under 85%

### Performance Recommendations

The system automatically generates recommendations based on test results:

```json
{
  "recommendations": [
    "High average response time detected: 6500ms. Consider optimizing API performance.",
    "High CPU usage during test: 85%. Consider scaling up or optimizing operations.",
    "All performance metrics are within acceptable ranges."
  ]
}
```

## 🔄 CI/CD Integration

### GitHub Actions Example

```yaml
name: Load Testing

on:
  schedule:
    - cron: "0 2 * * *" # Daily at 2 AM
  workflow_dispatch:

jobs:
  load-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          cd tests/load_testing
          pip install -r requirements.txt

      - name: Run smoke test
        run: |
          cd tests/load_testing
          python3 run_load_tests.py --scenario smoke_test

      - name: Upload results
        uses: actions/upload-artifact@v3
        with:
          name: load-test-results
          path: tests/load_testing/reports/
```

## 🚨 Troubleshooting

### Common Issues

1. **Connection Refused**
   - Ensure AgenticFleet server is running on the correct port
   - Check firewall settings

2. **High Error Rates**
   - Verify API endpoints are accessible
   - Check authentication configuration
   - Review server logs

3. **Memory Issues**
   - Reduce the number of concurrent users
   - Increase system memory
   - Check for memory leaks

4. **k6 Installation Issues**
   - Ensure k6 is properly installed
   - Check PATH environment variable
   - Use the setup script for automated installation

### Debug Mode

Run tests with verbose logging:

```bash
# Locust with debug logging
LOCUST_LOGLEVEL=DEBUG locust -f locustfile.py --host http://localhost:8000

# Python test runner with debug
python3 run_load_tests.py --scenario smoke_test --debug
```

## 📝 Best Practices

1. **Start Small**: Begin with smoke tests before running large-scale tests
2. **Monitor System Resources**: Keep an eye on CPU and memory during tests
3. **Test Realistic Scenarios**: Use realistic user behavior patterns
4. **Validate Results**: Cross-check metrics between different tools
5. **Document Findings**: Keep records of performance baselines and improvements

## 🤝 Contributing

When adding new test scenarios:

1. Update the configuration in `config.py`
2. Add appropriate test data
3. Include monitoring for new endpoints
4. Update documentation

## 📚 Additional Resources

- [Locust Documentation](https://docs.locust.io/)
- [k6 Documentation](https://k6.io/docs/)
- [Prometheus Metrics](https://prometheus.io/)
- [FastAPI Performance](https://fastapi.tiangolo.com/advanced/performance/)

## 🆘 Support

For issues or questions:

1. Check the troubleshooting section
2. Review the AgenticFleet main documentation
3. Create an issue in the repository with:
   - Test scenario used
   - Error messages
   - System specifications
   - Logs from the test run

---

**Happy Load Testing! 🚀**
