# Running Enterprise Setup Locally

## Quick Start (5 minutes)

### Prerequisites
- Docker Desktop installed and running
- At least 8GB RAM available
- OpenAI API key

### 1. Clone and Configure

```bash
cd /path/to/db-rag

# Copy environment template
cp .env.production.example .env

# Edit with your API key
nano .env
```

Minimal `.env` configuration:
```bash
OPENAI_API_KEY=sk-your-key-here
DB_PASSWORD=postgres
REDIS_PASSWORD=

# Enterprise setup
CELERY_RESULT_BACKEND=postgres
CELERY_RESULT_EXPIRES=0
```

### 2. Start Everything

```bash
# One command to start all services
./start_production.sh

# Or manually:
docker-compose -f docker-compose.production.yml up -d
```

### 3. Access Monitoring Dashboards

After 30 seconds, all services will be available:

| Service | URL | Credentials | Purpose |
|---------|-----|-------------|---------|
| **API** | http://localhost:8000 | - | FastAPI backend |
| **Frontend** | http://localhost:3000 | - | React UI |
| **Flower** 🌸 | http://localhost:5555 | admin/admin | Celery task monitoring |
| **Grafana** 📊 | http://localhost:3001 | admin/admin | Metrics dashboards |
| **Prometheus** | http://localhost:9090 | - | Metrics collection |
| **API Docs** | http://localhost:8000/docs | - | Swagger UI |

---

## Monitoring Tools Available

### 1. Flower (Celery Task Manager) 🌸

**URL**: http://localhost:5555  
**Login**: admin / admin

**What you can see**:
- ✅ Real-time worker status
- ✅ Active tasks (currently running)
- ✅ Task history (succeeded/failed)
- ✅ Task timeline & charts
- ✅ Worker pools & concurrency
- ✅ Broker (Redis) connection status
- ✅ Task retries & exceptions
- ✅ Task arguments & results

**Screenshots of what you'll see**:

#### Dashboard
```
Workers:     2 online
Active Tasks: 3
Completed:   127
Failed:      2
Success Rate: 98.5%
```

#### Active Tasks View
```
Task ID                           Name                    Worker    Started
abc123-def456                    ingest_document_task     worker1   2s ago
xyz789-uvw012                    update_metadata_task     worker2   5s ago
```

#### Task Details
- Click any task to see:
  - Arguments passed
  - Result/error
  - Runtime duration
  - Worker that executed it
  - Exception traceback (if failed)

**Key Features**:
- 🔄 Auto-refresh every 5 seconds
- 📈 Task rate charts
- ⏱️ Task runtime distribution
- 🔍 Search tasks by name/ID
- 🎯 Filter by status (pending/started/success/failure)

---

### 2. Grafana (Metrics Dashboards) 📊

**URL**: http://localhost:3001  
**Login**: admin / admin

**Pre-configured dashboards**:

#### System Overview Dashboard
- Request rate (queries/second)
- API latency (p50, p95, p99)
- Error rate
- Active connections

#### Celery Dashboard
- Task throughput
- Queue depth by priority
- Worker utilization
- Task success/failure rates
- Average task duration

#### Database Dashboard
- Query latency
- Connection pool usage
- Index hit rate
- Table sizes

#### Cache Dashboard
- Cache hit rate (embedding, metadata, query)
- Redis memory usage
- Cache operations/sec
- Eviction rate

#### Cost Dashboard
- OpenAI API calls
- Token usage
- Estimated cost (USD)
- Cost per query

**How to use**:
1. Open http://localhost:3001
2. Login (admin/admin)
3. Click "Dashboards" → "Browse"
4. Select dashboard to view

---

### 3. Prometheus (Metrics Store)

**URL**: http://localhost:9090

**What you can query**:

#### Example Queries

```promql
# Embedding cache hit rate
100 * cache_operations_total{operation="get", result="hit"} / 
      cache_operations_total{operation="get"}

# P95 query latency
histogram_quantile(0.95, 
  rate(http_request_duration_seconds_bucket[5m])
)

# Task queue depth
celery_queue_length{queue="default"}

# Worker active tasks
celery_task_total{status="started"} - 
celery_task_total{status="success"} - 
celery_task_total{status="failure"}

# OpenAI cost per hour
rate(llm_cost_usd_total[1h])
```

---

### 4. Redis CLI (Queue Inspection)

**Access Redis CLI**:
```bash
docker-compose -f docker-compose.production.yml exec redis redis-cli
```

**Check queue stats**:
```redis
# List all keys
KEYS *

# Check queue length
LLEN celery

# Check result backend keys
KEYS celery-task-meta-*

# Check cache keys
KEYS emb:*

# Get cache stats
INFO stats

# Check memory usage
INFO memory

# Monitor commands in real-time
MONITOR
```

**Redis queues**:
```bash
# Default queue length
LLEN celery

# Low priority queue
LLEN low

# Inspect a task
LINDEX celery 0
```

---

### 5. PostgreSQL (Job History)

**Access PostgreSQL**:
```bash
docker-compose -f docker-compose.production.yml exec postgres \
  psql -U dbrag_user dbrag
```

**Query job history**:
```sql
-- Recent tasks
SELECT 
    task_id,
    name,
    status,
    date_done,
    worker
FROM celery_taskmeta
ORDER BY date_done DESC
LIMIT 20;

-- Failed tasks with errors
SELECT 
    task_id,
    name,
    traceback,
    date_done
FROM celery_taskmeta
WHERE status = 'FAILURE'
ORDER BY date_done DESC
LIMIT 10;

-- Task statistics
SELECT 
    name,
    status,
    COUNT(*) as count,
    AVG(EXTRACT(EPOCH FROM (date_done - date_started))) as avg_duration
FROM celery_taskmeta
WHERE date_done > NOW() - INTERVAL '24 hours'
GROUP BY name, status
ORDER BY count DESC;

-- Success rate by task type
SELECT 
    name,
    COUNT(CASE WHEN status = 'SUCCESS' THEN 1 END) as success,
    COUNT(CASE WHEN status = 'FAILURE' THEN 1 END) as failure,
    ROUND(100.0 * COUNT(CASE WHEN status = 'SUCCESS' THEN 1 END) / COUNT(*), 2) as success_rate
FROM celery_taskmeta
GROUP BY name;
```

---

### 6. FastAPI Docs (API Testing)

**URL**: http://localhost:8000/docs

**What you can do**:
- 🔍 Browse all API endpoints
- 🧪 Test endpoints directly in browser
- 📋 See request/response schemas
- 🔐 Test authentication

**Key endpoints to try**:

#### Submit a document for processing
```bash
POST /api/documents/upload?async_processing=true
```
- Upload a PDF
- Returns job_id
- Track with `/api/jobs/{job_id}`

#### Check job status
```bash
GET /api/jobs/{job_id}
```
Returns:
```json
{
  "job_id": "abc123-def456-789",
  "status": "success",
  "result": {
    "chunks": 15,
    "document_ids": ["uuid1", "uuid2", ...],
    "embeddings_from_cache": 8,
    "embeddings_generated": 7
  }
}
```

#### List active jobs
```bash
GET /api/jobs/
```

#### Worker health check
```bash
POST /api/jobs/test
```

---

## Real-Time Monitoring Commands

### Watch logs in real-time

```bash
# All services
docker-compose -f docker-compose.production.yml logs -f

# Specific service
docker-compose -f docker-compose.production.yml logs -f worker-default
docker-compose -f docker-compose.production.yml logs -f api
docker-compose -f docker-compose.production.yml logs -f redis

# With timestamps
docker-compose -f docker-compose.production.yml logs -f --timestamps

# Last 100 lines
docker-compose -f docker-compose.production.yml logs --tail=100 worker-default
```

### Check service health

```bash
# All services status
docker-compose -f docker-compose.production.yml ps

# Restart a service
docker-compose -f docker-compose.production.yml restart worker-default

# Check resource usage
docker stats
```

### Monitor Redis queue

```bash
# Watch queue length (refreshes every 2 seconds)
watch -n 2 'docker-compose -f docker-compose.production.yml exec redis redis-cli LLEN celery'

# Or continuously monitor
docker-compose -f docker-compose.production.yml exec redis redis-cli --latency
```

### Monitor Celery workers

```bash
# Inspect active tasks
docker-compose -f docker-compose.production.yml exec worker-default \
  celery -A celeryconfig inspect active

# Check registered tasks
docker-compose -f docker-compose.production.yml exec worker-default \
  celery -A celeryconfig inspect registered

# Worker statistics
docker-compose -f docker-compose.production.yml exec worker-default \
  celery -A celeryconfig inspect stats
```

---

## Testing the Setup

### 1. Submit a test job

```bash
# Upload a document
curl -X POST http://localhost:8000/api/documents/upload?async_processing=true \
  -F "file=@test.pdf"

# Response:
{
  "success": true,
  "job_id": "abc123-def456",
  "message": "Document submitted for background processing",
  "status_url": "/api/jobs/abc123-def456"
}
```

### 2. Check Flower

Open http://localhost:5555 and watch:
- Task appears in "Active Tasks"
- Moves to "Succeeded" after completion
- Click task to see details

### 3. Check job status via API

```bash
curl http://localhost:8000/api/jobs/abc123-def456

# Response:
{
  "job_id": "abc123-def456",
  "status": "success",
  "result": {
    "chunks": 12,
    "document_ids": ["uuid1", "uuid2"],
    "embeddings_from_cache": 5,
    "embeddings_generated": 7
  }
}
```

### 4. Query PostgreSQL job history

```bash
docker-compose -f docker-compose.production.yml exec postgres \
  psql -U dbrag_user dbrag -c \
  "SELECT task_id, name, status, date_done FROM celery_taskmeta ORDER BY date_done DESC LIMIT 5;"
```

### 5. Check cache stats

```bash
curl http://localhost:8000/api/cache/stats

# Response:
{
  "cache_enabled": true,
  "cache_hits": 245,
  "cache_misses": 123,
  "cache_hit_rate": "66.58%",
  "api_calls": 123,
  "total_requests": 368
}
```

---

## Monitoring Workflow Example

### Scenario: Process 100 documents

1. **Submit jobs** (via API or UI)
   ```bash
   for file in documents/*.pdf; do
     curl -X POST http://localhost:8000/api/documents/upload?async_processing=true \
       -F "file=@$file"
   done
   ```

2. **Watch in Flower** (http://localhost:5555)
   - See tasks being processed
   - Monitor worker distribution
   - Check for any failures

3. **Monitor metrics in Grafana** (http://localhost:3001)
   - Queue depth decreasing
   - Task throughput (tasks/sec)
   - Cache hit rate improving
   - OpenAI cost tracking

4. **Check logs** if issues:
   ```bash
   docker-compose -f docker-compose.production.yml logs -f worker-default
   ```

5. **Query results in PostgreSQL**:
   ```sql
   SELECT 
     COUNT(*) as total,
     COUNT(CASE WHEN status = 'SUCCESS' THEN 1 END) as success,
     COUNT(CASE WHEN status = 'FAILURE' THEN 1 END) as failure
   FROM celery_taskmeta
   WHERE name = 'tasks.ingest_document_task'
   AND date_done > NOW() - INTERVAL '1 hour';
   ```

---

## Troubleshooting

### Workers not processing tasks

```bash
# Check worker status
docker-compose -f docker-compose.production.yml exec worker-default \
  celery -A celeryconfig inspect active

# Check Redis connection
docker-compose -f docker-compose.production.yml exec redis redis-cli ping

# Restart workers
docker-compose -f docker-compose.production.yml restart worker-default worker-low
```

### Tasks failing

1. **Check Flower** → Failed tasks → Click for traceback
2. **Check PostgreSQL**:
   ```sql
   SELECT task_id, name, traceback 
   FROM celery_taskmeta 
   WHERE status = 'FAILURE' 
   ORDER BY date_done DESC 
   LIMIT 1;
   ```
3. **Check worker logs**:
   ```bash
   docker-compose -f docker-compose.production.yml logs worker-default | grep ERROR
   ```

### Cache not working

```bash
# Test Redis connection
docker-compose -f docker-compose.production.yml exec redis redis-cli ping

# Check cache stats
curl http://localhost:8000/api/cache/stats

# Check Redis memory
docker-compose -f docker-compose.production.yml exec redis redis-cli INFO memory
```

---

## Stop Everything

```bash
# Stop all services
docker-compose -f docker-compose.production.yml down

# Stop and remove volumes (clean slate)
docker-compose -f docker-compose.production.yml down -v
```

---

## Summary: All Monitoring Tools

| Tool | URL | What You See |
|------|-----|--------------|
| **Flower** 🌸 | :5555 | Celery tasks, workers, queues |
| **Grafana** 📊 | :3001 | Dashboards, metrics, alerts |
| **Prometheus** 📈 | :9090 | Raw metrics, queries |
| **API Docs** 📚 | :8000/docs | Interactive API testing |
| **Frontend** 💻 | :3000 | User interface |
| **Redis CLI** | docker exec | Queue inspection |
| **PostgreSQL** | docker exec | Job history queries |

**Best workflow**: 
1. Use **Flower** for task-level monitoring
2. Use **Grafana** for system-level metrics
3. Use **PostgreSQL** for historical analysis
4. Use **logs** for debugging

The entire enterprise stack is available locally with full observability! 🚀
