/**
 * AgenticFleet k6 Load Testing Script
 *
 * This script provides comprehensive load testing for AgenticFleet chat API
 * using k6, covering both regular and streaming chat functionality.
 */

import http from "k6/http";
import { check, sleep } from "k6";
import { Rate, Trend, Counter } from "k6/metrics";
import {
  randomIntBetween,
  randomItem,
} from "https://jslib.k6.io/k6-utils/1.2.0/index.js";

// Custom metrics
const chatResponseTime = new Trend("chat_response_time");
const chatErrorRate = new Rate("chat_error_rate");
const streamingTimeToFirstToken = new Trend("streaming_time_to_first_token");
const streamingTotalTime = new Trend("streaming_total_time");
const conversationCreationTime = new Trend("conversation_creation_time");
const workflowResponseTime = new Trend("workflow_response_time");

// Counters
const totalRequests = new Counter("total_requests");
const totalErrors = new Counter("total_errors");
const streamingEvents = new Counter("streaming_events");

// Test configuration
export const options = {
  stages: [
    // Warm-up phase
    { duration: "2m", target: 10 },
    // Normal load
    { duration: "5m", target: 50 },
    // Stress phase
    { duration: "3m", target: 100 },
    // Spike
    { duration: "1m", target: 200 },
    // Cool down
    { duration: "2m", target: 0 },
  ],
  thresholds: {
    http_req_duration: ["p(95)<5000"], // 95% of requests under 5s
    http_req_failed: ["rate<0.1"], // Error rate under 10%
    chat_error_rate: ["rate<0.05"], // Chat-specific error rate under 5%
    chat_response_time: ["p(95)<10000"], // Chat responses under 10s
  },
  ext: {
    loadimpact: {
      projectID: 3633313,
      name: "AgenticFleet Load Test",
    },
  },
};

// Configuration
const BASE_URL = __ENV.BASE_URL || "http://localhost:8000";
const API_PREFIX = "/v1";
const DEFAULT_TIMEOUT = 30000; // 30 seconds

// Test data
const CHAT_MESSAGES = [
  "What are the key principles of microservices architecture?",
  "Explain the benefits of using FastAPI for web development",
  "How do I optimize database queries for better performance?",
  "What are the best practices for API authentication?",
  "Can you help me design a scalable system architecture?",
  "What are the differences between SQL and NoSQL databases?",
  "How do I implement proper error handling in distributed systems?",
  "What are the key considerations for system monitoring and observability?",
];

// State management
const VUS = new Map();

// Helper functions
function generateUUID() {
  // cryptographically secure UUID v4 generator
  const bytes = new Uint8Array(16);
  crypto.getRandomValues(bytes);
  // Per RFC4122 variant and version bits
  bytes[6] = (bytes[6] & 0x0f) | 0x40; // Version 4
  bytes[8] = (bytes[8] & 0x3f) | 0x80; // Variant 10
  const hex = Array.from(bytes).map(b => b.toString(16).padStart(2, "0"));
  return [
    hex.slice(0, 4).join(""),
    hex.slice(4, 6).join(""),
    hex.slice(6, 8).join(""),
    hex.slice(8, 10).join(""),
    hex.slice(10, 16).join("")
  ].join("-");
}

function getUserContext(vuId) {
  if (!VUS.has(vuId)) {
    VUS.set(vuId, {
      conversationId: null,
      userId: `k6_user_${vuId}_${generateUUID().slice(0, 8)}`,
      sessionId: generateUUID(),
      userRole: randomItem(["developer", "architect", "student", "team_lead"]),
    });
  }
  return VUS.get(vuId);
}

function createConversation(userContext) {
  const payload = {
    title: `k6 Load Test ${new Date().toISOString()}`,
    user_context: {
      user_id: userContext.userId,
      role: userContext.userRole,
      session_id: userContext.sessionId,
    },
  };

  const params = {
    headers: {
      "Content-Type": "application/json",
      "User-Agent": `k6/${userContext.userId}`,
    },
    timeout: DEFAULT_TIMEOUT,
  };

  const response = http.post(
    `${BASE_URL}${API_PREFIX}/conversations`,
    JSON.stringify(payload),
    params,
  );
  conversationCreationTime.add(response.timings.duration);

  if (response.status === 201 && response.json) {
    const data = response.json();
    return data.id || generateUUID(); // Fallback if no ID returned
  } else {
    console.error(
      `Failed to create conversation: ${response.status} ${response.body}`,
    );
    return generateUUID(); // Fallback
  }
}

function sendChatMessage(userContext, streaming = false) {
  const message = randomItem(CHAT_MESSAGES);
  const payload = {
    message: message,
    conversation_id: userContext.conversationId,
    stream: streaming,
    user_context: {
      user_id: userContext.userId,
      role: userContext.userRole,
      session_id: userContext.sessionId,
    },
  };

  const params = {
    headers: {
      "Content-Type": "application/json",
      Accept: streaming ? "text/event-stream" : "application/json",
      "User-Agent": `k6/${userContext.userId}`,
    },
    timeout: streaming ? 60000 : DEFAULT_TIMEOUT, // Longer timeout for streaming
  };

  totalRequests.add(1);
  const startTime = Date.now();

  if (streaming) {
    return handleStreamingChat(payload, params, startTime);
  } else {
    return handleRegularChat(payload, params, startTime);
  }
}

function handleRegularChat(payload, params, startTime) {
  const response = http.post(
    `${BASE_URL}${API_PREFIX}/chat`,
    JSON.stringify(payload),
    params,
  );
  const endTime = Date.now();
  const totalTime = endTime - startTime;

  chatResponseTime.add(totalTime);

  const success = check(response, {
    "chat status is 200": (r) => r.status === 200,
    "chat response has content": (r) => r.json && r.json("message"),
    "chat response time is reasonable": (r) => totalTime < 10000,
  });

  if (!success) {
    totalErrors.add(1);
    console.error(
      `Chat failed: ${response.status} ${response.body.slice(0, 200)}`,
    );
  }

  chatErrorRate.add(!success);

  sleep(randomIntBetween(1, 3)); // Simulate user thinking time
  return success;
}

function handleStreamingChat(payload, params, startTime) {
  const response = http.post(
    `${BASE_URL}${API_PREFIX}/chat`,
    JSON.stringify(payload),
    params,
  );
  const endTime = Date.now();
  const totalTime = endTime - startTime;

  streamingTotalTime.add(totalTime);

  const success = check(response, {
    "streaming status is 200": (r) => r.status === 200,
    "streaming response is text/event-stream": (r) =>
      r.headers["Content-Type"] &&
      r.headers["Content-Type"].includes("text/event-stream"),
    "streaming completed in reasonable time": (r) => totalTime < 30000,
  });

  if (success && response.body) {
    // Parse SSE events
    const events = response.body.split("\n");
    let eventCount = 0;
    let firstTokenTime = null;

    for (const line of events) {
      if (line.startsWith("data: ") && !line.includes("[DONE]")) {
        eventCount++;
        streamingEvents.add(1);

        // Track time to first token (simplified)
        if (!firstTokenTime && eventCount === 1) {
          firstTokenTime = Date.now();
          streamingTimeToFirstToken.add(firstTokenTime - startTime);
        }
      }
    }

    console.log(
      `Streaming: ${eventCount} events processed for user ${payload.user_context.user_id}`,
    );
  } else {
    totalErrors.add(1);
    console.error(
      `Streaming chat failed: ${response.status} ${response.body.slice(0, 200)}`,
    );
  }

  chatErrorRate.add(!success);

  sleep(randomIntBetween(2, 4)); // Longer wait for streaming
  return success;
}

function getWorkflows() {
  const params = {
    headers: {
      "Content-Type": "application/json",
      "User-Agent": "k6/workflow_test",
    },
    timeout: DEFAULT_TIMEOUT,
  };

  const response = http.get(`${BASE_URL}${API_PREFIX}/workflows`, params);
  workflowResponseTime.add(response.timings.duration);

  const success = check(response, {
    "workflows status is 200": (r) => r.status === 200,
    "workflows response is JSON": (r) => r.json && r.json("workflows"),
    "workflows response time is reasonable": (r) => r.timings.duration < 5000,
  });

  if (!success) {
    console.error(`Workflows request failed: ${response.status}`);
  }

  return success;
}

function healthCheck() {
  const params = {
    timeout: 5000, // Short timeout for health checks
  };

  const response = http.get(`${BASE_URL}${API_PREFIX}/system/health`, params);

  check(response, {
    "health status is 200": (r) => r.status === 200,
  });

  // Don't fail the test for health check failures
  return response.status === 200;
}

// Test scenarios
export function setup() {
  console.log(`Starting AgenticFleet load test against: ${BASE_URL}`);
  console.log(`Test will run with ${__ENV.VUS || 100} virtual users`);

  // Initial health check
  if (!healthCheck()) {
    console.warn("Initial health check failed - target may not be ready");
  }

  return { startTime: Date.now() };
}

export default function (data) {
  const vuId = __VU; // Virtual user ID
  const userContext = getUserContext(vuId);

  // Create conversation if needed
  if (!userContext.conversationId) {
    userContext.conversationId = createConversation(userContext);
  }

  // Main test loop with different scenarios
  const scenario = Math.random();

  if (scenario < 0.6) {
    // 60%: Regular chat
    sendChatMessage(userContext, false);
  } else if (scenario < 0.85) {
    // 25%: Streaming chat
    sendChatMessage(userContext, true);
  } else if (scenario < 0.95) {
    // 10%: Workflow operations
    getWorkflows();
  } else {
    // 5%: Health check
    healthCheck();
  }
}

export function teardown(data) {
  const duration = Date.now() - data.startTime;
  console.log(`Load test completed. Duration: ${duration / 1000}s`);
  console.log(`Total requests: ${totalRequests.count}`);
  console.log(`Total errors: ${totalErrors.count}`);
  console.log(
    `Error rate: ${((totalErrors.count / totalRequests.count) * 100).toFixed(2)}%`,
  );
  console.log(
    `Average chat response time: ${chatResponseTime.mean.toFixed(2)}ms`,
  );
  console.log(
    `Average streaming time: ${streamingTotalTime.mean.toFixed(2)}ms`,
  );
}

// Optional: Handle interruptions gracefully
export function handleInterrupt(data) {
  console.log("Test interrupted, cleaning up...");
  // Any cleanup needed
}
