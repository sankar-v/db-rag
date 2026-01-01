# Enterprise Task Queue Architecture Comparison

## Overview

This document compares different enterprise architectures for Celery task queue with persistence, reliability, and scalability requirements.

---

## Architecture Options

### 1. Redis Only (Development/Small Scale)

```
┌─────────┐    tasks     ┌─────────┐    results    ┌─────────┐
│ FastAPI │─────────────>│  Redis  │<──────────────│ Workers │
└─────────┘    broker    │ (In-Mem)│   (volatile)  └─────────┘
                         └─────────┘
```

**Pros**:
- ✅ Simple setup (single service)
- ✅ Fast (in-memory)
- ✅ Cache + Broker in one
- ✅ Good for < 10K tasks/day

**Cons**:
- ❌ Volatile results (TTL expires)
- ❌ Data loss on Redis restart
- ❌ No historical job tracking
- ❌ Limited message durability

**Use Case**: Development, non-critical workloads

**Cost**: $10-30/month (managed Redis)

---

### 2. Redis + PostgreSQL Result Backend (Recommended Enterprise)

```
┌─────────┐    tasks     ┌─────────┐    
│ FastAPI │─────────────>│  Redis  │    
└─────────┘    broker    │ (Broker)│    
                         └─────────┘    
                               
┌─────────┐   results    ┌──────────┐
│ Workers │─────────────>│PostgreSQL│  (Persistent)
└─────────┘   persist    │ (Results)│  (Queryable)
                         └──────────┘
```

**Pros**:
- ✅ **Persistent job history** (never expires)
- ✅ Fast broker (Redis)
- ✅ Queryable results (SQL)
- ✅ Audit trail & compliance
- ✅ Job analytics & reporting
- ✅ Retry & debugging easier

**Cons**:
- ⚠️ Extra database writes
- ⚠️ Slightly slower result storage (~50ms)
- ⚠️ Database growth (need archival)

**Use Case**: Production workloads requiring audit trail

**Cost**: $30-80/month (managed Redis + PostgreSQL)

**Configuration**:
```bash
# .env
CELERY_BROKER=redis
CELERY_RESULT_BACKEND=postgres
CELERY_RESULT_EXPIRES=0  # Never expire
```

---

### 3. RabbitMQ + PostgreSQL (High Reliability Enterprise)

```
┌─────────┐    tasks     ┌──────────┐    
│ FastAPI │─────────────>│ RabbitMQ │   (Durable queues)
└─────────┘    broker    │ (Broker) │   (Guaranteed delivery)
                         └──────────┘    
                               
┌─────────┐   results    ┌──────────┐
│ Workers │─────────────>│PostgreSQL│  (Persistent)
└─────────┘   persist    │ (Results)│  (Queryable)
                         └──────────┘
```

**Pros**:
- ✅ **Best message durability**
- ✅ Guaranteed delivery (persistent queues)
- ✅ Dead letter queues (DLQ)
- ✅ Priority queues built-in
- ✅ Complex routing patterns
- ✅ Better for > 100K tasks/day

**Cons**:
- ❌ More complex setup
- ❌ Extra service to manage
- ❌ Higher resource usage

**Use Case**: Financial transactions, critical workflows

**Cost**: $50-150/month (managed RabbitMQ + PostgreSQL)

**Configuration**:
```bash
# .env
CELERY_BROKER=rabbitmq
RABBITMQ_HOST=rabbitmq
RABBITMQ_USER=admin
RABBITMQ_PASSWORD=secure_password
CELERY_RESULT_BACKEND=postgres
```

---

### 4. Hybrid (Redis + PostgreSQL Results + Archival)

```
┌─────────┐    tasks     ┌─────────┐    
│ FastAPI │─────────────>│  Redis  │    
└─────────┘    broker    │ (Broker)│    
                         └─────────┘    
                               
┌─────────┐   results    ┌─────────┐     archive    ┌──────────┐
│ Workers │─────────────>│  Redis  │────────────────>│PostgreSQL│
└─────────┘   (fast)     │ (Cache) │   (periodic)   │ (Archive)│
                         └─────────┘                 └──────────┘
                         TTL: 1 hour                  Permanent
```

**Pros**:
- ✅ Fast result retrieval (Redis)
- ✅ Long-term storage (PostgreSQL)
- ✅ Best of both worlds
- ✅ Reduced PostgreSQL writes

**Cons**:
- ⚠️ Complex implementation
- ⚠️ Eventual consistency
- ⚠️ Custom archival logic

**Use Case**: High-throughput with audit requirements

**Cost**: $40-100/month

**Implementation**: Custom background task to archive Redis → PostgreSQL

---

## Comparison Matrix

| Feature | Redis Only | Redis + PG | RabbitMQ + PG | Hybrid |
|---------|-----------|-----------|---------------|--------|
| **Setup Complexity** | ⭐ Simple | ⭐⭐ Easy | ⭐⭐⭐ Moderate | ⭐⭐⭐⭐ Complex |
| **Broker Speed** | 🚀 Very Fast | 🚀 Very Fast | ⚡ Fast | 🚀 Very Fast |
| **Result Persistence** | ❌ Volatile | ✅ Permanent | ✅ Permanent | ✅ Permanent |
| **Message Durability** | ⚠️ AOF Only | ⚠️ AOF Only | ✅ Native | ⚠️ AOF Only |
| **Historical Queries** | ❌ No | ✅ SQL | ✅ SQL | ✅ SQL |
| **Audit Compliance** | ❌ No | ✅ Yes | ✅ Yes | ✅ Yes |
| **Scalability** | 10K tasks/day | 50K tasks/day | 1M+ tasks/day | 100K tasks/day |
| **Operational Cost** | $ | $$ | $$$ | $$ |
| **Recovery from Failure** | ⚠️ Data Loss | ✅ Full Recovery | ✅ Full Recovery | ✅ Full Recovery |
| **Debugging Ease** | ⚠️ Limited | ✅ Easy | ✅ Easy | ✅ Easy |

---

## Enterprise Recommendation (Preferred)

### **Option 2: Redis Broker + PostgreSQL Result Backend**

This is the **sweet spot** for most enterprise deployments:

#### Why This Architecture?

1. **Fast Broker** (Redis)
   - Sub-millisecond task queuing
   - High throughput (10K+ tasks/sec)
   - Simple configuration

2. **Persistent Results** (PostgreSQL)
   - Never expires (configurable)
   - Full SQL query capabilities
   - Audit trail for compliance
   - Easy debugging & monitoring

3. **Cost Effective**
   - Reuses existing PostgreSQL database
   - No extra message broker service
   - Simple to operate

4. **Production Ready**
   - Proven at scale (Instagram, Pinterest use similar)
   - Battle-tested Celery backends
   - Good community support

#### Configuration

```python
# config.py
@dataclass
class CeleryConfig:
    broker_url: str = "redis://redis:6379/0"
    result_backend: str = "db+postgresql://user:pass@postgres:5432/dbrag"
    result_expires: int = 0  # Never expire (keep forever)
    result_extended: bool = True  # Store extra metadata
```

```bash
# .env
CELERY_BROKER=redis
CELERY_RESULT_BACKEND=postgres
CELERY_RESULT_EXPIRES=0  # 0 = never expire
```

#### Database Tables Created

Celery automatically creates tables in PostgreSQL:

```sql
-- Task results table
CREATE TABLE celery_taskmeta (
    id SERIAL PRIMARY KEY,
    task_id VARCHAR(155) UNIQUE NOT NULL,
    status VARCHAR(50),
    result BYTEA,
    date_done TIMESTAMP,
    traceback TEXT,
    name VARCHAR(155),
    args BYTEA,
    kwargs BYTEA,
    worker VARCHAR(155),
    retries INTEGER,
    queue VARCHAR(155)
);

-- Group results table  
CREATE TABLE celery_groupmeta (
    id SERIAL PRIMARY KEY,
    taskset_id VARCHAR(155) UNIQUE NOT NULL,
    result BYTEA,
    date_done TIMESTAMP
);

-- Indexes for performance
CREATE INDEX celery_taskmeta_task_id_idx ON celery_taskmeta(task_id);
CREATE INDEX celery_taskmeta_date_done_idx ON celery_taskmeta(date_done);
CREATE INDEX celery_taskmeta_status_idx ON celery_taskmeta(status);
```

#### Querying Job History

```python
# Query all successful jobs
SELECT task_id, name, status, date_done, result
FROM celery_taskmeta
WHERE status = 'SUCCESS'
ORDER BY date_done DESC
LIMIT 100;

# Query failed jobs for debugging
SELECT task_id, name, traceback, date_done
FROM celery_taskmeta
WHERE status = 'FAILURE'
AND date_done > NOW() - INTERVAL '24 hours';

# Job completion rate
SELECT 
    status,
    COUNT(*) as count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) as percentage
FROM celery_taskmeta
GROUP BY status;
```

#### Monitoring Queries

```sql
-- Recent task activity
SELECT 
    DATE_TRUNC('hour', date_done) as hour,
    name as task_name,
    status,
    COUNT(*) as count
FROM celery_taskmeta
WHERE date_done > NOW() - INTERVAL '24 hours'
GROUP BY 1, 2, 3
ORDER BY 1 DESC;

-- Average task duration (if storing start/end times)
SELECT 
    name,
    AVG(EXTRACT(EPOCH FROM (date_done - date_started))) as avg_duration_seconds
FROM celery_taskmeta
WHERE status = 'SUCCESS'
GROUP BY name;
```

---

## Migration Guide

### From Redis Only → Redis + PostgreSQL

1. **Update Configuration**:
   ```bash
   # .env
   CELERY_RESULT_BACKEND=postgres  # Change from redis
   CELERY_RESULT_EXPIRES=0  # Never expire
   ```

2. **Install Database Backend**:
   ```bash
   pip install sqlalchemy psycopg2-binary
   ```

3. **Initialize Tables** (automatic on first use):
   ```bash
   celery -A celeryconfig upgrade
   ```

4. **No code changes needed** - Celery handles it automatically

5. **Restart Workers**:
   ```bash
   docker-compose restart worker-default worker-low
   ```

---

## Operational Considerations

### Database Growth

**PostgreSQL result backend will grow over time**. Implement archival:

```python
# Archive old completed tasks (keep last 30 days)
DELETE FROM celery_taskmeta
WHERE date_done < NOW() - INTERVAL '30 days'
  AND status IN ('SUCCESS', 'FAILURE');

# Or archive to separate table
INSERT INTO celery_taskmeta_archive
SELECT * FROM celery_taskmeta
WHERE date_done < NOW() - INTERVAL '30 days';

DELETE FROM celery_taskmeta
WHERE date_done < NOW() - INTERVAL '30 days';
```

**Recommended**: Run nightly via Celery Beat:

```python
@celery_app.task
def archive_old_tasks():
    """Archive tasks older than 30 days"""
    conn = db.get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        DELETE FROM celery_taskmeta
        WHERE date_done < NOW() - INTERVAL '30 days'
    """)
    
    deleted = cursor.rowcount
    conn.commit()
    cursor.close()
    
    return {"archived": deleted}

# Schedule in celeryconfig.py
celery_app.conf.beat_schedule = {
    'archive-old-tasks': {
        'task': 'tasks.archive_old_tasks',
        'schedule': crontab(hour=3, minute=0),  # 3 AM daily
    },
}
```

### Monitoring

Use Prometheus to track:
- `celery_taskmeta` table size
- Task completion rates
- Average task duration

### Backup

Include Celery tables in your PostgreSQL backup strategy:
```bash
pg_dump -t celery_taskmeta -t celery_groupmeta dbrag > celery_backup.sql
```

---

## RabbitMQ When Needed

**Upgrade to RabbitMQ if**:
- Processing > 100K tasks/day
- Need guaranteed message delivery (financial transactions)
- Complex routing patterns required
- Message loss is unacceptable

**Migration**: Change broker only, keep PostgreSQL results:
```bash
CELERY_BROKER=rabbitmq
RABBITMQ_HOST=rabbitmq
CELERY_RESULT_BACKEND=postgres  # Keep same
```

---

## Summary

### For DB-RAG Production (Recommended):

```bash
# .env Configuration
CELERY_BROKER=redis
REDIS_HOST=redis
REDIS_PORT=6379

CELERY_RESULT_BACKEND=postgres
DB_HOST=postgres
DB_NAME=dbrag
DB_USER=dbrag_user
DB_PASSWORD=your_password

CELERY_RESULT_EXPIRES=0  # Never expire
```

**Benefits**:
- ✅ Job history preserved forever (or until archived)
- ✅ SQL queries for analytics
- ✅ Audit compliance
- ✅ Fast broker (Redis)
- ✅ Cost effective
- ✅ Production ready

**This is what companies like Instagram, Pinterest, and Lyft use at scale.**
