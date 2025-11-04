#!/usr/bin/env python3
"""
AgenticFleet Performance Dashboard

Web-based dashboard for real-time monitoring and visualization of load test results.
"""

import asyncio
import contextlib
import json
from datetime import datetime
from typing import Any

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

app = FastAPI(title="AgenticFleet Performance Dashboard")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# WebSocket connections manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            with contextlib.suppress(Exception):
                await connection.send_text(message)


manager = ConnectionManager()

# Performance data storage
performance_data = {
    "current_test": None,
    "metrics": [],
    "alerts": [],
    "system_info": {},
    "test_history": [],
}


@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    """Serve the main dashboard HTML."""
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AgenticFleet Performance Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        .metric-card {
            @apply bg-white rounded-lg shadow p-6 border-l-4 border-blue-500;
        }
        .alert {
            @apply bg-yellow-50 border-l-4 border-yellow-400 p-4 mb-4;
        }
        .status-indicator {
            @apply inline-block w-3 h-3 rounded-full mr-2;
        }
        .status-running { @apply bg-green-500; }
        .status-stopped { @apply bg-red-500; }
        .status-warning { @apply bg-yellow-500; }
    </style>
</head>
<body class="bg-gray-100">
    <div class="container mx-auto px-4 py-8">
        <!-- Header -->
        <div class="mb-8">
            <h1 class="text-3xl font-bold text-gray-800 mb-2">AgenticFleet Performance Dashboard</h1>
            <p class="text-gray-600">Real-time monitoring and analysis of load testing results</p>
        </div>

        <!-- Status Bar -->
        <div class="bg-white rounded-lg shadow p-4 mb-6">
            <div class="flex items-center justify-between">
                <div class="flex items-center">
                    <span id="test-status" class="status-indicator status-stopped"></span>
                    <span id="test-name" class="font-semibold">No Active Test</span>
                </div>
                <div class="text-sm text-gray-600">
                    Last Updated: <span id="last-updated">Never</span>
                </div>
            </div>
        </div>

        <!-- Key Metrics -->
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            <div class="metric-card">
                <div class="flex items-center justify-between">
                    <div>
                        <p class="text-sm text-gray-600">Active Users</p>
                        <p class="text-2xl font-bold text-gray-800" id="active-users">0</p>
                    </div>
                    <div class="text-blue-500">
                        <svg class="w-8 h-8" fill="currentColor" viewBox="0 0 20 20">
                            <path d="M9 6a3 3 0 11-6 0 3 3 0 016 0zM17 6a3 3 0 11-6 0 3 3 0 016 0zM12.93 17c.046-.327.07-.66.07-1a6.97 6.97 0 00-1.5-4.33A5 5 0 0119 16v1h-6.07zM6 11a5 5 0 015 5v1H1v-1a5 5 0 015-5z"/>
                        </svg>
                    </div>
                </div>
            </div>

            <div class="metric-card border-l-green-500">
                <div class="flex items-center justify-between">
                    <div>
                        <p class="text-sm text-gray-600">Avg Response Time</p>
                        <p class="text-2xl font-bold text-gray-800" id="avg-response-time">0ms</p>
                    </div>
                    <div class="text-green-500">
                        <svg class="w-8 h-8" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clip-rule="evenodd"/>
                        </svg>
                    </div>
                </div>
            </div>

            <div class="metric-card border-l-yellow-500">
                <div class="flex items-center justify-between">
                    <div>
                        <p class="text-sm text-gray-600">Error Rate</p>
                        <p class="text-2xl font-bold text-gray-800" id="error-rate">0%</p>
                    </div>
                    <div class="text-yellow-500">
                        <svg class="w-8 h-8" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/>
                        </svg>
                    </div>
                </div>
            </div>

            <div class="metric-card border-l-red-500">
                <div class="flex items-center justify-between">
                    <div>
                        <p class="text-sm text-gray-600">CPU Usage</p>
                        <p class="text-2xl font-bold text-gray-800" id="cpu-usage">0%</p>
                    </div>
                    <div class="text-red-500">
                        <svg class="w-8 h-8" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M11.3 1.046A1 1 0 0112 2v5h4a1 1 0 01.82 1.573l-7 10A1 1 0 018 18v-5H4a1 1 0 01-.82-1.573l7-10a1 1 0 011.12-.38z" clip-rule="evenodd"/>
                        </svg>
                    </div>
                </div>
            </div>
        </div>

        <!-- Charts Section -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
            <!-- Response Time Chart -->
            <div class="bg-white rounded-lg shadow p-6">
                <h3 class="text-lg font-semibold mb-4">Response Time Trend</h3>
                <canvas id="response-time-chart" width="400" height="200"></canvas>
            </div>

            <!-- Request Rate Chart -->
            <div class="bg-white rounded-lg shadow p-6">
                <h3 class="text-lg font-semibold mb-4">Request Rate</h3>
                <canvas id="request-rate-chart" width="400" height="200"></canvas>
            </div>
        </div>

        <!-- Alerts Section -->
        <div class="bg-white rounded-lg shadow p-6 mb-8">
            <h3 class="text-lg font-semibold mb-4">Recent Alerts</h3>
            <div id="alerts-container">
                <p class="text-gray-500">No alerts</p>
            </div>
        </div>

        <!-- Test History -->
        <div class="bg-white rounded-lg shadow p-6">
            <h3 class="text-lg font-semibold mb-4">Recent Test Runs</h3>
            <div id="test-history">
                <p class="text-gray-500">No test history available</p>
            </div>
        </div>
    </div>

    <script>
        // WebSocket connection for real-time updates
        const ws = new WebSocket('ws://localhost:8001/ws');

        // Chart configurations
        const responseTimeChart = new Chart(document.getElementById('response-time-chart'), {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Response Time (ms)',
                    data: [],
                    borderColor: 'rgb(59, 130, 246)',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    tension: 0.1
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });

        const requestRateChart = new Chart(document.getElementById('request-rate-chart'), {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Requests/sec',
                    data: [],
                    borderColor: 'rgb(34, 197, 94)',
                    backgroundColor: 'rgba(34, 197, 94, 0.1)',
                    tension: 0.1
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });

        // WebSocket message handling
        ws.onmessage = function(event) {
            const data = JSON.parse(event.data);
            updateDashboard(data);
        };

        function updateDashboard(data) {
            // Update status
            if (data.current_test) {
                document.getElementById('test-status').className = 'status-indicator status-running';
                document.getElementById('test-name').textContent = data.current_test.name || 'Active Test';
            } else {
                document.getElementById('test-status').className = 'status-indicator status-stopped';
                document.getElementById('test-name').textContent = 'No Active Test';
            }

            // Update metrics
            if (data.metrics) {
                const latestMetric = data.metrics[data.metrics.length - 1];
                if (latestMetric) {
                    document.getElementById('active-users').textContent = latestMetric.active_users || 0;
                    document.getElementById('avg-response-time').textContent = Math.round(latestMetric.avg_response_time || 0) + 'ms';
                    document.getElementById('error-rate').textContent = (latestMetric.error_rate || 0).toFixed(1) + '%';
                    document.getElementById('cpu-usage').textContent = (latestMetric.cpu_usage || 0).toFixed(1) + '%';
                }

                // Update charts
                updateCharts(data.metrics);
            }

            // Update alerts
            if (data.alerts && data.alerts.length > 0) {
                updateAlerts(data.alerts);
            }

            // Update last updated time
            document.getElementById('last-updated').textContent = new Date().toLocaleTimeString();
        }

        function updateCharts(metrics) {
            const labels = metrics.map(m => new Date(m.timestamp).toLocaleTimeString());
            const responseTimes = metrics.map(m => m.avg_response_time || 0);
            const requestRates = metrics.map(m => m.request_rate || 0);

            // Keep only last 20 data points
            const maxPoints = 20;
            const startIdx = Math.max(0, labels.length - maxPoints);

            responseTimeChart.data.labels = labels.slice(startIdx);
            responseTimeChart.data.datasets[0].data = responseTimes.slice(startIdx);
            responseTimeChart.update('none');

            requestRateChart.data.labels = labels.slice(startIdx);
            requestRateChart.data.datasets[0].data = requestRates.slice(startIdx);
            requestRateChart.update('none');
        }

        function updateAlerts(alerts) {
            const container = document.getElementById('alerts-container');
            if (alerts.length === 0) {
                container.innerHTML = '<p class="text-gray-500">No alerts</p>';
                return;
            }

            const recentAlerts = alerts.slice(-5).reverse(); // Show last 5 alerts
            container.innerHTML = recentAlerts.map(alert => `
                <div class="alert mb-2">
                    <div class="flex">
                        <div class="flex-shrink-0">
                            <svg class="h-5 w-5 text-yellow-400" viewBox="0 0 20 20" fill="currentColor">
                                <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/>
                            </svg>
                        </div>
                        <div class="ml-3">
                            <p class="text-sm text-yellow-700">
                                <strong>${alert.rule_name}:</strong> ${alert.message}
                            </p>
                            <p class="text-xs text-yellow-600 mt-1">
                                ${new Date(alert.timestamp).toLocaleString()}
                            </p>
                        </div>
                    </div>
                </div>
            `).join('');
        }

        // Load initial data
        fetch('/api/metrics')
            .then(response => response.json())
            .then(data => updateDashboard(data))
            .catch(error => console.error('Error loading initial data:', error));
    </script>
</body>
</html>
    """


@app.get("/api/metrics")
async def get_metrics():
    """Get current performance metrics."""
    return performance_data


@app.get("/api/test-history")
async def get_test_history():
    """Get test history."""
    return {"tests": performance_data["test_history"]}


@app.post("/api/metrics")
async def update_metrics(metrics: dict[str, Any]):
    """Update performance metrics (called by monitoring system)."""
    performance_data["metrics"].append(metrics)

    # Keep only last 100 metrics
    if len(performance_data["metrics"]) > 100:
        performance_data["metrics"] = performance_data["metrics"][-100:]

    # Broadcast to WebSocket clients
    await manager.broadcast(json.dumps(performance_data))

    return {"status": "ok"}


@app.post("/api/alert")
async def add_alert(alert: dict[str, Any]):
    """Add a new alert."""
    alert["timestamp"] = datetime.now().isoformat()
    performance_data["alerts"].append(alert)

    # Keep only last 50 alerts
    if len(performance_data["alerts"]) > 50:
        performance_data["alerts"] = performance_data["alerts"][-50:]

    await manager.broadcast(json.dumps(performance_data))

    return {"status": "ok"}


@app.post("/api/test-start")
async def start_test(test_info: dict[str, Any]):
    """Start monitoring a new test."""
    performance_data["current_test"] = {
        "name": test_info.get("name"),
        "start_time": datetime.now().isoformat(),
        "users": test_info.get("users", 0),
        "type": test_info.get("type", "unknown"),
    }

    await manager.broadcast(json.dumps(performance_data))
    return {"status": "ok"}


@app.post("/api/test-end")
async def end_test(results: dict[str, Any]):
    """End the current test and save results."""
    if performance_data["current_test"]:
        test_result = {
            **performance_data["current_test"],
            "end_time": datetime.now().isoformat(),
            "results": results,
        }

        performance_data["test_history"].append(test_result)
        performance_data["current_test"] = None

        # Keep only last 20 tests
        if len(performance_data["test_history"]) > 20:
            performance_data["test_history"] = performance_data["test_history"][-20]

        await manager.broadcast(json.dumps(performance_data))

    return {"status": "ok"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    await manager.connect(websocket)
    try:
        # Send initial data
        await manager.send_personal_message(json.dumps(performance_data), websocket)

        # Keep connection alive
        while True:
            await asyncio.sleep(30)  # Send heartbeat every 30 seconds
            await manager.send_personal_message('{"type": "heartbeat"}', websocket)

    except WebSocketDisconnect:
        manager.disconnect(websocket)


def start_dashboard(port: int = 8001):
    """Start the dashboard server."""
    print("🚀 Starting AgenticFleet Performance Dashboard")
    print(f"📊 Dashboard available at: http://localhost:{port}")
    print(f"🔌 WebSocket endpoint: ws://localhost:{port}/ws")

    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="AgenticFleet Performance Dashboard")
    parser.add_argument("--port", type=int, default=8001, help="Port to run the dashboard on")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")

    args = parser.parse_args()

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
