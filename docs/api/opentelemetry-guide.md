# OpenTelemetry Integration Guide

This guide explains how to enable and configure OpenTelemetry (OTel) for the AgenticFleet backend to export traces and metrics for observability.

## Enabling OpenTelemetry

By default, OpenTelemetry is disabled. To enable it, you must set the following environment variable:

```bash
ENABLE_OTEL=true
```

You can set this in your `.env` file or export it in your shell session before running the application.

## Configuring the OTLP Exporter

When OpenTelemetry is enabled, it needs an endpoint to send the telemetry data. The application is configured to use an OTLP (OpenTelemetry Protocol) exporter. You must specify the endpoint where an OTel collector is listening.

Set the following environment variable to configure the exporter endpoint:

```bash
OTLP_ENDPOINT="http://localhost:4317"
```

- The default value `http://localhost:4317` is a common endpoint for a local OTel collector listening for gRPC connections.
- Adjust the host and port to match your specific collector setup.

## Example `.env` Configuration

To enable OpenTelemetry and configure a local collector, add the following lines to your `.env` file:

````env
# .env

# Enable OpenTelemetry
ENABLE_OTEL=true

# Set the OTLP exporter endpoint
OTLP_ENDPOINT="http://localhost:4317"```

## Running a Local Collector

If you don't have an OpenTelemetry collector running, you can use a simple Docker setup for local development. Create a `docker-compose.yml` file with the following content:

```yaml
version: '3'
services:
  otel-collector:
    image: otel/opentelemetry-collector:latest
    command: ["--config=/etc/otel-collector-config.yaml"]
    volumes:
      - ./otel-collector-config.yaml:/etc/otel-collector-config.yaml
    ports:
      - "4317:4317" # OTLP gRPC
      - "4318:4318" # OTLP HTTP
      - "8889:8889" # Prometheus exporter
````

And create a corresponding `otel-collector-config.yaml`:

```yaml
receivers:
  otlp:
    protocols:
      grpc:
      http:

exporters:
  logging:
    loglevel: debug

service:
  pipelines:
    traces:
      receivers: [otlp]
      exporters: [logging]
    metrics:
      receivers: [otlp]
      exporters: [logging]
```

Run `docker-compose up` to start the collector. The backend will then be able to send telemetry data to it. You can then extend the collector configuration to forward data to observability platforms like Jaeger, Prometheus, or Grafana Tempo.
