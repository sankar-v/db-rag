# Production Architecture for DB-RAG

## Overview
This document outlines the enterprise-grade architecture for deploying DB-RAG at scale, addressing performance, reliability, and maintainability concerns.

## Current Bottlenecks

### 1. Synchronous Embedding Generation
- **Issue**: OpenAI API calls block request processing
- **Impact**: High latency, poor throughput, timeout risks
- **Scale**: ~100-500ms per embedding × documents/tables

### 2. No Batch Processing
- **Issue**: Individual API calls for each embedding
- **Impact**: Inefficient API usage, rate limiting, high costs
- **Scale**: OpenAI allows batch of 2048 inputs per request

### 3. No Job Queue
- **Issue**: Long-running tasks block HTTP requests
- **Impact**: Request timeouts, poor UX, resource exhaustion
- **Scale**: Document ingestion can take minutes for large PDFs

### 4. No Caching
- **Issue**: Duplicate embeddings for same text
- **Impact**: Unnecessary API calls, latency, costs
- **Scale**: ~10-30% cache hit rate typical

### 5. Suboptimal Index Configuration
- **Issue**: IVFFlat with fixed parameters
- **Impact**: Poor query performance at scale
- **Scale**: HNSW 10-100x faster for large datasets

---

## Enterprise Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Load Balancer                             │
│                     (NGINX / ALB / GCP LB)                       │
└────────────────────────┬────────────────────────────────────────┘
                         │
        ┌────────────────┴────────────────┐
        │                                  │
┌───────▼────────┐              ┌─────────▼────────┐
│  API Servers   │              │  API Servers     │
│  (FastAPI)     │              │  (FastAPI)       │
│  Replicas 1-N  │              │  Replicas 1-N    │
└───────┬────────┘              └─────────┬────────┘
        │                                  │
        └────────────┬─────────────────────┘
                     │
        ┌────────────┴────────────────┐
        │                              │
┌───────▼────────┐          ┌─────────▼────────┐
│  Message Queue │          │  Cache Layer     │
│  (Redis/RabbitMQ)│        │  (Redis)         │
│  - Jobs         │          │  - Embeddings   │
│  - Tasks        │          │  - Metadata     │
│  - Results      │          │  - Query Cache  │
└───────┬────────┘          └──────────────────┘
        │
        │
┌───────▼────────────────────────────────────────┐
│         Background Workers (Celery)            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │ Embedding│  │ Document │  │ Metadata │    │
│  │ Generator│  │ Processor│  │ Indexer  │    │
│  └──────────┘  └──────────┘  └──────────┘    │
│                                                 │
│  - Async embedding generation (batch)          │
│  - Document chunking & preprocessing           │
│  - Metadata catalog updates                    │
│  - Index maintenance                           │
└────────────────┬───────────────────────────────┘
                 │
        ┌────────┴────────┐
        │                  │
┌───────▼────────┐  ┌─────▼──────────┐
│  PostgreSQL    │  │  Vector Store  │
│  (Metadata)    │  │  (pgvector)    │
│  - Connections │  │  - Embeddings  │
│  - Users       │  │  - Documents   │
│  - Jobs        │  │  - HNSW Index  │
└────────────────┘  └────────────────┘
```

---

## Component Details

### 1. Async Embedding Service

**Technology**: Celery + Redis + Batch Processing

**Features**:
- Batch embeddings (up to 2048 texts per API call)
- Rate limiting and retry logic
- Embedding cache (Redis)
- Cost tracking
- Model fallback (embedding-3-small → embedding-ada-002)

**Implementation**:
```python
# New file: backend/embedding_service.py
from celery import Celery, group
import hashlib
import redis
from typing import List, Dict

class EmbeddingService:
    def __init__(self, cache_client, openai_client):
        self.cache = cache_client  # Redis
        self.openai = openai_client
        self.batch_size = 2048
        
    async def generate_embeddings_batch(
        self, 
        texts: List[str], 
        cache_ttl: int = 86400
    ) -> List[List[float]]:
        """Generate embeddings with caching and batching"""
        
        # Check cache first
        embeddings = []
        uncached_texts = []
        uncached_indices = []
        
        for i, text in enumerate(texts):
            cache_key = f"emb:{hashlib.sha256(text.encode()).hexdigest()}"
            cached = self.cache.get(cache_key)
            
            if cached:
                embeddings.append(json.loads(cached))
            else:
                embeddings.append(None)
                uncached_texts.append(text)
                uncached_indices.append(i)
        
        # Generate missing embeddings in batches
        if uncached_texts:
            for batch_start in range(0, len(uncached_texts), self.batch_size):
                batch = uncached_texts[batch_start:batch_start + self.batch_size]
                
                response = await self.openai.embeddings.create(
                    input=batch,
                    model="text-embedding-3-small"
                )
                
                # Cache and store results
                for idx, embedding_data in enumerate(response.data):
                    original_idx = uncached_indices[batch_start + idx]
                    embedding = embedding_data.embedding
                    
                    embeddings[original_idx] = embedding
                    
                    # Cache the embedding
                    cache_key = f"emb:{hashlib.sha256(uncached_texts[batch_start + idx].encode()).hexdigest()}"
                    self.cache.setex(
                        cache_key, 
                        cache_ttl, 
                        json.dumps(embedding)
                    )
        
        return embeddings
```

### 2. Job Queue System

**Technology**: Celery + Redis/RabbitMQ

**Job Types**:
- `ingest_document`: Process uploaded documents
- `update_metadata_catalog`: Refresh table metadata
- `rebuild_index`: Optimize vector indexes
- `batch_embed`: Generate embeddings in bulk

**Priority Queues**:
- `critical`: User-facing queries (high priority)
- `default`: Document processing
- `low`: Background maintenance

**Implementation**:
```python
# New file: backend/tasks.py
from celery import Celery
from celery.utils.log import get_task_logger

celery_app = Celery('dbrag')
celery_app.config_from_object('celeryconfig')

logger = get_task_logger(__name__)

@celery_app.task(bind=True, max_retries=3)
def ingest_document_task(self, document_content: str, metadata: dict):
    """Background task for document ingestion"""
    try:
        # Chunk document
        chunks = chunk_document(document_content)
        
        # Generate embeddings in batch
        embeddings = embedding_service.generate_embeddings_batch(chunks)
        
        # Store in database
        vector_agent.add_documents_batch(chunks, embeddings, metadata)
        
        return {"status": "success", "chunks": len(chunks)}
    except Exception as e:
        logger.error(f"Document ingestion failed: {e}")
        self.retry(countdown=60)

@celery_app.task
def update_table_metadata_task(table_name: str):
    """Background task for metadata catalog updates"""
    try:
        # Fetch schema and samples (fast)
        schema = db.get_table_context_string(table_name)
        samples = db.get_sample_data(table_name, limit=5)
        
        # Generate description (LLM call)
        description = metadata_catalog.generate_table_description(
            table_name, schema, samples
        )
        
        # Generate embedding
        embedding = embedding_service.generate_embeddings_batch(
            [f"{table_name} {description}"]
        )[0]
        
        # Update catalog
        metadata_catalog.update_catalog_entry(
            table_name, description, embedding
        )
        
        return {"status": "success", "table": table_name}
    except Exception as e:
        logger.error(f"Metadata update failed: {e}")
        raise
```

### 3. Caching Strategy

**Cache Layers**:

1. **Embedding Cache** (Redis)
   - Key: `emb:{sha256(text)}`
   - TTL: 24 hours
   - Size: ~1KB per embedding
   - Hit rate: 20-40% typical

2. **Metadata Cache** (Redis)
   - Key: `meta:{connection_id}:{table_name}`
   - TTL: 1 hour
   - Invalidation: On schema changes

3. **Query Result Cache** (Redis)
   - Key: `query:{sha256(query + context)}`
   - TTL: 5 minutes
   - Size: Variable (limit to 100KB)

4. **Connection Cache** (Application Memory)
   - Connection pool reuse
   - Prepared statements

**Implementation**:
```python
# Update: backend/config.py
@dataclass
class CacheConfig:
    enabled: bool = True
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None
    
    embedding_cache_ttl: int = 86400  # 24 hours
    metadata_cache_ttl: int = 3600    # 1 hour
    query_cache_ttl: int = 300        # 5 minutes
    
    max_cache_size_mb: int = 1024     # 1GB
    
    @classmethod
    def from_env(cls):
        return cls(
            enabled=os.getenv("CACHE_ENABLED", "true").lower() == "true",
            redis_host=os.getenv("REDIS_HOST", "localhost"),
            redis_port=int(os.getenv("REDIS_PORT", "6379")),
            redis_db=int(os.getenv("REDIS_DB", "0")),
            redis_password=os.getenv("REDIS_PASSWORD"),
            embedding_cache_ttl=int(os.getenv("EMBEDDING_CACHE_TTL", "86400")),
            metadata_cache_ttl=int(os.getenv("METADATA_CACHE_TTL", "3600")),
            query_cache_ttl=int(os.getenv("QUERY_CACHE_TTL", "300")),
        )
```

### 4. Vector Index Optimization

**Upgrade from IVFFlat to HNSW**:

```sql
-- Better index for production (10-100x faster queries)
CREATE INDEX documents_embedding_hnsw_idx 
ON dbrag_documents 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- For metadata catalog
CREATE INDEX metadata_embedding_hnsw_idx 
ON dbrag_metadata_catalog 
USING hnsw (description_embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

**Index Selection Guidelines**:
- **< 10K vectors**: IVFFlat is fine
- **10K - 1M vectors**: HNSW (m=16, ef=64)
- **> 1M vectors**: HNSW (m=32, ef=128) or consider specialized vector DBs

**Index Maintenance**:
```python
@celery_app.task
def rebuild_vector_indexes_task():
    """Periodic index optimization"""
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Reindex documents (if using IVFFlat)
    cursor.execute("REINDEX INDEX documents_embedding_idx")
    
    # Analyze for query planner
    cursor.execute("ANALYZE dbrag_documents")
    cursor.execute("ANALYZE dbrag_metadata_catalog")
    
    conn.commit()
```

### 5. Monitoring & Observability

**Metrics to Track**:
- Embedding generation latency (p50, p95, p99)
- Cache hit rates (by cache type)
- Vector search latency
- Queue depth (per priority)
- Worker utilization
- API error rates
- Cost per query (OpenAI tokens)

**Tools**:
- **Prometheus + Grafana**: Metrics and dashboards
- **Jaeger/Tempo**: Distributed tracing
- **Sentry**: Error tracking
- **Structlog**: Structured logging

**Implementation**:
```python
# New file: backend/monitoring.py
from prometheus_client import Counter, Histogram, Gauge
import time

# Metrics
embedding_requests = Counter(
    'embedding_requests_total', 
    'Total embedding requests',
    ['cache_hit']
)

embedding_latency = Histogram(
    'embedding_generation_seconds',
    'Embedding generation latency',
    ['batch_size']
)

vector_search_latency = Histogram(
    'vector_search_seconds',
    'Vector search latency'
)

cache_hit_rate = Gauge(
    'cache_hit_rate',
    'Cache hit rate percentage',
    ['cache_type']
)

# Usage in code
def generate_embedding_with_metrics(text):
    cache_key = compute_cache_key(text)
    cached = cache.get(cache_key)
    
    if cached:
        embedding_requests.labels(cache_hit='true').inc()
        return cached
    
    embedding_requests.labels(cache_hit='false').inc()
    
    start = time.time()
    embedding = openai_client.embeddings.create(...)
    duration = time.time() - start
    
    embedding_latency.labels(batch_size='1').observe(duration)
    
    cache.set(cache_key, embedding)
    return embedding
```

---

## Deployment Architecture

### Infrastructure Components

#### 1. API Tier (Horizontal Scaling)
```yaml
# kubernetes/api-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: dbrag-api
spec:
  replicas: 3  # Auto-scale based on CPU/memory
  selector:
    matchLabels:
      app: dbrag-api
  template:
    spec:
      containers:
      - name: api
        image: dbrag-api:latest
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
        env:
        - name: WORKERS
          value: "4"  # Gunicorn workers
        - name: REDIS_HOST
          value: "redis-service"
        - name: DB_HOST
          value: "postgres-service"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
```

#### 2. Worker Tier (Task Processing)
```yaml
# kubernetes/worker-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: dbrag-workers
spec:
  replicas: 5  # Scale based on queue depth
  template:
    spec:
      containers:
      - name: worker
        image: dbrag-worker:latest
        command: ["celery", "-A", "tasks", "worker"]
        args:
        - "--loglevel=info"
        - "--concurrency=4"
        - "--queues=critical,default,low"
        - "--max-tasks-per-child=100"
        resources:
          requests:
            memory: "1Gi"
            cpu: "1000m"
```

#### 3. Cache Layer (Redis)
```yaml
# kubernetes/redis-statefulset.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: redis
spec:
  serviceName: redis
  replicas: 3  # Redis Sentinel for HA
  template:
    spec:
      containers:
      - name: redis
        image: redis:7-alpine
        command:
        - redis-server
        - --maxmemory 2gb
        - --maxmemory-policy allkeys-lru
        - --save ""  # Disable RDB for cache
        ports:
        - containerPort: 6379
        volumeMounts:
        - name: redis-data
          mountPath: /data
```

#### 4. Database (PostgreSQL + pgvector)
```yaml
# Use managed service (AWS RDS, GCP Cloud SQL, Azure Database)
# Or self-hosted with:
- Replication: 1 primary + 2 read replicas
- Connection pooling: PgBouncer (1000+ connections)
- Backup: Daily snapshots + WAL archiving
- Monitoring: pg_stat_statements enabled
```

### Docker Compose (For Testing Production Setup)

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  api:
    build:
      context: .
      dockerfile: Dockerfile.api
    ports:
      - "8000:8000"
    environment:
      - WORKERS=4
      - REDIS_HOST=redis
      - DB_HOST=postgres
      - CELERY_BROKER_URL=redis://redis:6379/0
    depends_on:
      - redis
      - postgres
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '2'
          memory: 2G

  worker:
    build:
      context: .
      dockerfile: Dockerfile.worker
    command: celery -A tasks worker --loglevel=info --concurrency=4
    environment:
      - REDIS_HOST=redis
      - DB_HOST=postgres
      - CELERY_BROKER_URL=redis://redis:6379/0
    depends_on:
      - redis
      - postgres
    deploy:
      replicas: 5
      resources:
        limits:
          cpus: '1'
          memory: 1G

  redis:
    image: redis:7-alpine
    command: redis-server --maxmemory 2gb --maxmemory-policy allkeys-lru
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  postgres:
    image: pgvector/pgvector:pg16
    environment:
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=dbrag
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    command: postgres -c max_connections=200 -c shared_buffers=256MB

  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml

  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana

volumes:
  redis_data:
  postgres_data:
  grafana_data:
```

---

## Migration Path (Dev → Production)

### Phase 1: Add Caching (Week 1)
✅ **Low Risk, High Impact**
- Deploy Redis
- Add embedding cache
- Add metadata cache
- **Expected**: 50% latency reduction

### Phase 2: Async Workers (Week 2-3)
✅ **Medium Risk, Very High Impact**
- Set up Celery + Redis queue
- Move document ingestion to background
- Move metadata updates to background
- Add job status tracking API
- **Expected**: 10x throughput increase

### Phase 3: Batch Processing (Week 3-4)
✅ **Low Risk, High Impact**
- Implement batch embedding service
- Update document processor
- Update metadata catalog
- **Expected**: 5x faster, 50% cost reduction

### Phase 4: Index Optimization (Week 4-5)
✅ **Medium Risk, High Impact**
- Migrate from IVFFlat to HNSW
- Rebuild indexes
- Test query performance
- **Expected**: 10-100x faster queries

### Phase 5: Monitoring & Scaling (Week 5-6)
✅ **Low Risk, Essential**
- Deploy Prometheus + Grafana
- Add application metrics
- Set up alerts
- Configure auto-scaling
- **Expected**: Full observability

---

## Cost Optimization

### Current Costs (Dev Mode)
- OpenAI Embeddings: ~$0.00013 per 1K tokens
- For 1000 documents (avg 500 tokens each): **$0.065**
- For 100 tables (metadata): **$0.013**
- **Total**: ~$0.08 one-time + query costs

### Production Costs (With Optimization)
**Savings from Caching**:
- 30% cache hit rate → 30% cost reduction
- Deduplication → Additional 10-20% savings

**Savings from Batching**:
- Batch API calls → 5-10% efficiency gain
- Reduced overhead

**Expected Monthly Costs** (10K documents, 1K tables, 10K queries/day):
- Embedding generation: $20-30
- Query embeddings: $10-15
- Infrastructure (Redis, workers): $50-100
- **Total**: $80-145/month

---

## Alternative: Specialized Vector Databases

For very large scale (> 10M vectors), consider:

### Pinecone
- **Pros**: Managed, fast, easy
- **Cons**: $70-700/month, vendor lock-in
- **Use case**: > 10M vectors, need managed service

### Weaviate
- **Pros**: Open source, hybrid search, multi-tenancy
- **Cons**: More complex setup
- **Use case**: > 10M vectors, self-hosted

### Qdrant
- **Pros**: Rust performance, good API, easy self-host
- **Cons**: Newer ecosystem
- **Use case**: > 10M vectors, performance critical

### Recommendation
**Stick with pgvector + HNSW until > 10M vectors**, then evaluate:
1. Query latency requirements (< 50ms → specialized DB)
2. Cost constraints (high → self-hosted Qdrant/Weaviate)
3. Ops complexity (low → Pinecone)

---

## Security Considerations

### API Layer
- Rate limiting (per user/API key)
- Request size limits (prevent abuse)
- API authentication (JWT tokens)
- CORS configuration

### Database
- Connection encryption (SSL/TLS)
- Row-level security (multi-tenancy)
- Secrets management (Vault, AWS Secrets Manager)
- Regular backups (3-2-1 strategy)

### Embedding Cache
- Redis AUTH password
- Network isolation (private subnet)
- No PII in cache keys

---

## Performance Targets

### Latency (p95)
- Query routing: < 100ms
- SQL generation: < 500ms
- Vector search: < 50ms
- Document ingestion: < 30s (async)

### Throughput
- Concurrent queries: 100+ RPS
- Document ingestion: 1000+ docs/hour
- Metadata updates: 100+ tables/hour

### Availability
- API uptime: 99.9% (43 minutes downtime/month)
- Query success rate: 99.5%
- Worker availability: 99%

---

## Conclusion

The proposed architecture addresses all current bottlenecks:

✅ **Async embedding** → 10x throughput
✅ **Batch processing** → 50% cost reduction
✅ **Caching** → 50% latency reduction
✅ **HNSW indexes** → 100x faster queries
✅ **Job queues** → No request timeouts
✅ **Horizontal scaling** → Handle 100+ RPS
✅ **Monitoring** → Full observability

**Next Steps**: Start with Phase 1 (caching) for immediate wins, then progressively implement async workers and batching.
