# Self-Managed Production Setup Guide

This guide covers deploying DB-RAG in a self-managed, cloud-agnostic environment using Docker Compose with Celery workers, Redis caching, and full monitoring.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    Load Balancer (Optional)                      │
└──────────────────────────┬──────────────────────────────────────┘
                           │
         ┌─────────────────┴─────────────────┐
         │                                    │
    ┌────▼─────┐                       ┌─────▼────┐
    │   API    │                       │   API    │
    │ (FastAPI)│                       │ (FastAPI)│
    └────┬─────┘                       └─────┬────┘
         │                                    │
         └──────────────┬─────────────────────┘
                        │
         ┌──────────────┼──────────────┐
         │              │               │
    ┌────▼────┐    ┌────▼────┐    ┌────▼────┐
    │  Redis  │    │Workers  │    │ Postgres│
    │ (Cache  │    │(Celery) │    │(pgvector)│
    │  + MQ)  │    │         │    │         │
    └─────────┘    └─────────┘    └─────────┘
         │              │               │
         └──────────────┼───────────────┘
                        │
              ┌─────────┴─────────┐
              │                    │
         ┌────▼────┐         ┌────▼────┐
         │Prometheus│        │ Grafana │
         │         │        │         │
         └─────────┘        └─────────┘
```

## Components

1. **FastAPI Application** (4 workers)
   - Handles HTTP requests
   - WebSocket connections
   - Job submission

2. **Celery Workers** (2 default + 1 low priority)
   - Document ingestion with chunking
   - Metadata catalog updates
   - Index maintenance

3. **Redis** (2GB memory)
   - Embedding cache (30-40% hit rate)
   - Metadata cache
   - Celery message broker

4. **PostgreSQL 16 + pgvector**
   - Primary data storage
   - Vector similarity search (HNSW indexes)
   - Connection pooling

5. **Monitoring Stack**
   - Prometheus: Metrics collection
   - Grafana: Dashboards
   - Flower: Celery monitoring
   - Redis/Postgres exporters

## Prerequisites

- Docker 24.0+ and Docker Compose 2.0+
- 8GB RAM minimum (16GB recommended)
- 50GB disk space
- OpenAI API key

## Quick Start

### 1. Clone and Configure

```bash
cd /path/to/db-rag

# Copy environment template
cp .env.production.example .env

# Edit .env with your values
nano .env
```

Required environment variables:
```bash
OPENAI_API_KEY=sk-...
DB_PASSWORD=your_secure_password
REDIS_PASSWORD=your_redis_password  # Optional
```

### 2. Build and Start

```bash
# Build images
docker-compose -f docker-compose.production.yml build

# Start all services
docker-compose -f docker-compose.production.yml up -d

# Check status
docker-compose -f docker-compose.production.yml ps
```

### 3. Initialize Database

```bash
# Wait for postgres to be ready
docker-compose -f docker-compose.production.yml exec postgres pg_isready

# Run migrations (if needed)
docker-compose -f docker-compose.production.yml exec api python setup_metadata_db.py

# Upgrade to HNSW indexes
docker-compose -f docker-compose.production.yml exec api python upgrade_to_hnsw.py
```

### 4. Verify Services

```bash
# API health check
curl http://localhost:8000/health

# Worker health check
curl http://localhost:8000/api/jobs/test

# Check Redis
docker-compose -f docker-compose.production.yml exec redis redis-cli ping

# Check cache stats
curl http://localhost:8000/api/cache/stats
```

### 5. Access UIs

- **API**: http://localhost:8000
- **Frontend**: http://localhost:3000
- **Flower** (Celery monitoring): http://localhost:5555
  - Username: admin (from .env)
  - Password: admin (from .env)
- **Grafana**: http://localhost:3001
  - Username: admin (from .env)
  - Password: admin (from .env)
- **Prometheus**: http://localhost:9090

## Configuration

### Scaling Workers

Edit `docker-compose.production.yml`:

```yaml
worker-default:
  deploy:
    replicas: 5  # Increase to 5 workers
```

Or scale dynamically:
```bash
docker-compose -f docker-compose.production.yml up -d --scale worker-default=5
```

### Cache Configuration

In `.env`:
```bash
CACHE_ENABLED=true
EMBEDDING_CACHE_TTL=86400      # 24 hours
METADATA_CACHE_TTL=3600        # 1 hour
QUERY_CACHE_TTL=300            # 5 minutes
MAX_CACHE_SIZE_MB=2048         # 2GB
```

### Worker Concurrency

In `.env`:
```bash
CELERY_WORKER_CONCURRENCY=4    # Threads per worker
```

Or per service in `docker-compose.production.yml`:
```yaml
worker-default:
  command: celery -A celeryconfig worker --concurrency=8 --queues=default
```

### Database Performance Tuning

Edit `docker-compose.production.yml` postgres environment:
```yaml
postgres:
  environment:
    POSTGRES_SHARED_BUFFERS: 512MB    # 25% of RAM
    POSTGRES_EFFECTIVE_CACHE_SIZE: 2GB # 50% of RAM
    POSTGRES_MAX_CONNECTIONS: 500
    POSTGRES_WORK_MEM: 10MB
```

## Operations

### Monitoring

#### View Metrics

```bash
# Embedding service stats
curl http://localhost:8000/api/cache/stats

# Worker stats
curl http://localhost:8000/api/jobs/stats/workers

# Active jobs
curl http://localhost:8000/api/jobs/
```

#### Grafana Dashboards

1. Open http://localhost:3001
2. Login with credentials
3. Import dashboards from `monitoring/grafana/dashboards/`

Key metrics to watch:
- Cache hit rate (target: > 30%)
- P95 query latency (target: < 500ms)
- Worker queue depth (target: < 100)
- Embedding generation rate
- OpenAI API costs

### Backup and Restore

#### Backup

```bash
# Backup database
docker-compose -f docker-compose.production.yml exec postgres \
  pg_dump -U dbrag_user dbrag | gzip > backup_$(date +%Y%m%d).sql.gz

# Backup Redis (if persistence enabled)
docker-compose -f docker-compose.production.yml exec redis \
  redis-cli BGSAVE
```

#### Restore

```bash
# Restore database
gunzip -c backup_20241231.sql.gz | \
docker-compose -f docker-compose.production.yml exec -T postgres \
  psql -U dbrag_user dbrag
```

### Log Management

```bash
# View API logs
docker-compose -f docker-compose.production.yml logs -f api

# View worker logs
docker-compose -f docker-compose.production.yml logs -f worker-default

# View all logs with timestamps
docker-compose -f docker-compose.production.yml logs -f --timestamps

# Export logs
docker-compose -f docker-compose.production.yml logs --no-color > logs_$(date +%Y%m%d).txt
```

### Maintenance

#### Clear Cache

```bash
# Via API
curl -X DELETE http://localhost:8000/api/cache/clear

# Via Redis CLI
docker-compose -f docker-compose.production.yml exec redis \
  redis-cli FLUSHDB
```

#### Rebuild Indexes

```bash
# Manual trigger
docker-compose -f docker-compose.production.yml exec api \
  python -c "from tasks import rebuild_vector_indexes_task; rebuild_vector_indexes_task.delay()"

# Or schedule via Celery Beat (runs daily)
```

#### Update Metadata Catalog

```bash
# Sync all tables
curl -X POST http://localhost:8000/api/metadata/sync

# Or via task
docker-compose -f docker-compose.production.yml exec api \
  python -c "from tasks import batch_update_metadata_task; batch_update_metadata_task.delay(['table1', 'table2'])"
```

### Troubleshooting

#### Workers not processing tasks

```bash
# Check worker status
docker-compose -f docker-compose.production.yml exec worker-default \
  celery -A celeryconfig inspect active

# Check Redis connection
docker-compose -f docker-compose.production.yml exec redis redis-cli ping

# Restart workers
docker-compose -f docker-compose.production.yml restart worker-default worker-low
```

#### High cache miss rate

```bash
# Check cache stats
curl http://localhost:8000/api/cache/stats

# Increase cache TTL in .env
EMBEDDING_CACHE_TTL=172800  # 48 hours

# Increase Redis memory
# Edit docker-compose.production.yml:
redis:
  command: redis-server --maxmemory 4gb ...
```

#### Slow queries

```bash
# Check Prometheus metrics
# Query: histogram_quantile(0.95, rate(vector_search_duration_seconds_bucket[5m]))

# Check database slow queries
docker-compose -f docker-compose.production.yml exec postgres psql -U dbrag_user dbrag \
  -c "SELECT * FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;"

# Rebuild HNSW indexes
docker-compose -f docker-compose.production.yml exec api python upgrade_to_hnsw.py
```

## Production Checklist

- [ ] Set strong passwords in `.env`
- [ ] Configure Redis AUTH password
- [ ] Enable SSL/TLS for database connections
- [ ] Set up firewall rules (only expose 80/443)
- [ ] Configure log rotation
- [ ] Set up automated backups
- [ ] Configure Grafana alerts
- [ ] Enable Prometheus authentication
- [ ] Set resource limits in docker-compose
- [ ] Configure health checks
- [ ] Set up reverse proxy (NGINX)
- [ ] Enable CORS for production domains
- [ ] Configure rate limiting
- [ ] Set up SSL certificates

## Performance Tuning

### Expected Performance

With this setup on a 16GB RAM / 8 CPU server:

- **Throughput**: 100-200 queries/second
- **Latency**: < 500ms p95
- **Document ingestion**: 1000+ docs/hour
- **Cache hit rate**: 30-40%
- **Cost**: ~$80-150/month (10K docs, 10K queries/day)

### Optimization Tips

1. **Increase cache size** - More RAM = better hit rate
2. **Scale workers horizontally** - More workers = more throughput
3. **Use batch processing** - Group operations for efficiency
4. **Tune HNSW parameters** - Increase `ef_search` for accuracy
5. **Connection pooling** - Use PgBouncer for 1000+ connections

## Migration from Development

```bash
# Export development data
docker-compose exec postgres pg_dump -U postgres corp_db > dev_backup.sql

# Import to production
cat dev_backup.sql | docker-compose -f docker-compose.production.yml exec -T postgres \
  psql -U dbrag_user dbrag

# Upgrade indexes
docker-compose -f docker-compose.production.yml exec api python upgrade_to_hnsw.py
```

## Next Steps

1. **Cloud Deployment**: Deploy to AWS/GCP/Azure using Kubernetes
2. **Serverless Version**: Migrate to AWS Lambda + SQS + DynamoDB
3. **Multi-tenancy**: Enable full tenant isolation
4. **Horizontal Scaling**: Add load balancer and multiple API replicas
5. **Advanced Monitoring**: Integrate Jaeger for distributed tracing

## Support

For issues or questions:
- Check logs: `docker-compose -f docker-compose.production.yml logs`
- Review metrics: http://localhost:9090
- Monitor workers: http://localhost:5555
- GitHub Issues: [Your repo URL]
