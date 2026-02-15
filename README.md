# Real-Time Analytics Dashboard

A production-grade streaming analytics pipeline that ingests IoT sensor data and user activity events, processes them in real time with windowed aggregations and anomaly detection, and visualizes insights on a live dashboard.

**One command to run everything:** `docker compose up`

## Architecture

```
 IoT Producer ──┐                                      ┌── REST API (/api/v1/*)
                ├──► Apache Kafka ──► Stream Processor ─┤
Activity Prod ──┘     (3 partitions)      │             └── WebSocket (/ws/live)
                                          │                        │
                                    ┌─────┴─────┐                 │
                                    │  Anomaly   │                 ▼
                                    │  Detection │            Dashboard
                                    │  (Z-score) │          (Chart.js + CSS Grid)
                                    │            │
                                    │  Trend     │
                                    │  Analysis  │
                                    │  (OLS)     │
                                    │            │
                                    │  Windowed  │
                                    │  Aggregator│
                                    └─────┬──────┘
                                          │
                                        Redis
                                    (Time-series + Cache
                                     + Pub/Sub + Alerts)
```

## Key Features

- **Streaming Ingestion** — Kafka producers simulate 10 IoT devices and 50 user events/sec with realistic noise patterns (sinusoidal cycles, Gaussian noise, drift, anomaly spikes)
- **Real-Time Processing** — Tumbling (10s) and sliding (60s) window aggregations computing avg, min, max, count, p99
- **Anomaly Detection** — Rolling z-score detector with adaptive thresholds; severity levels (warning/critical)
- **Trend Analysis** — Online OLS linear regression classifying metrics as rising, falling, or stable
- **Live Dashboard** — Dark-themed responsive UI with streaming Chart.js visualizations, gauge panels, and alert feed
- **WebSocket Push** — Server pushes updates to all connected clients via Redis Pub/Sub bridge with per-client throttling
- **Dead Letter Queue** — Unprocessable messages routed to DLQ topic with full error context
- **Circuit Breaker** — Redis client with 3-state circuit breaker (closed/open/half-open) preventing cascading failures

## Performance Optimizations

| Layer | Optimization | Impact |
|-------|-------------|--------|
| Kafka Producer | 16KB batching + LZ4 compression | ~10x throughput vs single sends |
| Kafka Consumer | Batch polling (500/poll) + manual commits | Fewer broker round-trips |
| Redis | Connection pooling (20) + pipelining (50 ops/batch) | ~50x latency reduction |
| WebSocket | 100ms per-client throttle + backpressure | Prevents client overwhelm |
| Dashboard | Chart.js decimation + 60-point rolling window | Smooth 60fps rendering |

## Quick Start

### Prerequisites

- Docker and Docker Compose v2+

### Run the Pipeline

```bash
# Start all services (Kafka, Redis, producers, processor, API, dashboard)
docker compose up --build

# Or use the Makefile
make up
```

Once healthy, open:

| Service | URL |
|---------|-----|
| Dashboard | http://localhost:3000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| Health Check | http://localhost:8000/health |
| Prometheus Metrics | http://localhost:8000/metrics |

### With Monitoring (Prometheus + Grafana)

```bash
docker compose --profile monitoring up --build

# Or
make up-monitoring
```

| Service | URL |
|---------|-----|
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3001 (admin/admin) |

### Stop Everything

```bash
docker compose down        # Stop services
docker compose down -v     # Stop + remove volumes
make clean                 # Stop + remove + prune
```

## Project Structure

```
├── config/                     # Centralized settings (pydantic-settings)
│   ├── settings.py             # All env-configurable parameters
│   └── logging_config.py       # Structured JSON logging (structlog)
│
├── producers/                  # Kafka data producers
│   ├── schemas.py              # Pydantic event models (SensorReading, ActivityEvent)
│   ├── base_producer.py        # ABC with batching, compression, graceful shutdown
│   ├── iot_producer.py         # IoT device simulator (temp, humidity, pressure)
│   ├── activity_producer.py    # User activity simulator (views, clicks, purchases)
│   └── noise.py                # Realistic noise generation
│
├── processor/                  # Stream processing engine
│   ├── aggregator.py           # Tumbling + sliding window aggregations
│   ├── anomaly.py              # Z-score anomaly detection
│   ├── trend.py                # OLS linear regression trends
│   ├── consumer.py             # Kafka consumer with manual offsets
│   ├── dead_letter.py          # Dead letter queue handler
│   └── main.py                 # Pipeline orchestrator
│
├── storage/                    # Redis storage layer
│   ├── redis_client.py         # Connection pool + circuit breaker
│   ├── time_series.py          # Sorted-set time-series store
│   └── cache.py                # Latest metrics, alerts, leaderboards
│
├── api/                        # FastAPI backend
│   ├── main.py                 # App factory with lifespan events
│   ├── ws_manager.py           # WebSocket manager with throttling
│   └── routers/                # REST + WebSocket endpoints
│
├── dashboard/                  # Frontend (served by Nginx)
│   ├── index.html              # Dark-themed SPA
│   ├── css/styles.css          # Responsive CSS Grid layout
│   └── js/                     # Chart.js visualizations + WebSocket client
│
├── monitoring/                 # Prometheus + Grafana configs
├── tests/                      # Unit + integration tests
├── docker-compose.yml          # Full stack orchestration (8 services)
└── Makefile                    # Developer commands
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Liveness probe |
| `GET` | `/ready` | Readiness probe (checks Redis) |
| `GET` | `/api/v1/metrics/iot/latest` | Latest reading per device |
| `GET` | `/api/v1/metrics/iot/history?key=...` | Historical time-series data |
| `GET` | `/api/v1/metrics/activity/latest` | Activity event counts |
| `GET` | `/api/v1/metrics/activity/leaderboard` | Top pages by purchases |
| `GET` | `/api/v1/alerts` | Recent anomaly alerts |
| `WS` | `/ws/live` | Real-time streaming updates |
| `GET` | `/metrics` | Prometheus metrics |

## Configuration

All settings are configurable via environment variables with `PIPELINE_` prefix:

```bash
PIPELINE_IOT_NUM_DEVICES=20          # Number of simulated IoT devices
PIPELINE_ACTIVITY_EVENTS_PER_SEC=100 # User events per second
PIPELINE_TUMBLING_WINDOW_SEC=10      # Tumbling window duration
PIPELINE_ANOMALY_Z_THRESHOLD=3.0     # Z-score threshold for anomalies
PIPELINE_WS_THROTTLE_MS=100          # WebSocket throttle interval
```

See `.env.example` for all available options.

## Testing

```bash
# Unit tests (no infrastructure required)
make test-unit

# All tests
make test-all
```

## Reliability Patterns

- **Circuit Breaker** — Redis client trips after 5 consecutive failures, auto-recovers after 30s cooldown
- **Dead Letter Queue** — Failed messages preserved with error context for debugging
- **Graceful Shutdown** — SIGTERM/SIGINT handlers flush producers, commit offsets, close connections
- **Health Checks** — Docker Compose enforces startup ordering via `service_healthy` conditions
- **Retry with Backoff** — Exponential backoff on Redis operations and WebSocket reconnects
- **At-Least-Once Delivery** — Manual Kafka offset commits after successful batch processing

## Tech Stack

- **Streaming**: Apache Kafka (Confluent Platform 7.5)
- **Processing**: Python 3.12, kafka-python-ng, MessagePack
- **Storage**: Redis 7 (sorted sets, hashes, pub/sub, bounded lists)
- **API**: FastAPI, uvicorn, WebSockets
- **Dashboard**: Chart.js 4, vanilla JS, CSS Grid
- **Infrastructure**: Docker Compose, Nginx
- **Monitoring**: Prometheus, Grafana
- **Testing**: pytest
- **Logging**: structlog (structured JSON)
