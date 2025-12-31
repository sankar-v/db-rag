"""
Prometheus metrics instrumentation for DB-RAG
Exposes metrics for monitoring embedding generation, cache performance, and query latency
"""
import time
import logging
from functools import wraps
from typing import Callable, Any
from prometheus_client import Counter, Histogram, Gauge, Info, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response
from fastapi.responses import Response as FastAPIResponse

logger = logging.getLogger(__name__)

# Application info
app_info = Info('dbrag_app', 'DB-RAG application information')
app_info.info({
    'version': '1.0.0',
    'python_version': '3.11',
    'environment': 'production'
})

# Request metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'endpoint']
)

# Embedding metrics
embedding_requests_total = Counter(
    'embedding_requests_total',
    'Total embedding generation requests',
    ['cache_hit', 'model']
)

embedding_generation_duration_seconds = Histogram(
    'embedding_generation_duration_seconds',
    'Embedding generation latency',
    ['model', 'batch_size_range']  # e.g., '1', '2-10', '11-50', '51-100', '100+'
)

embedding_cache_size_bytes = Gauge(
    'embedding_cache_size_bytes',
    'Current size of embedding cache in bytes'
)

embedding_tokens_total = Counter(
    'embedding_tokens_total',
    'Total tokens processed for embeddings',
    ['model']
)

# Cache metrics
cache_operations_total = Counter(
    'cache_operations_total',
    'Total cache operations',
    ['operation', 'cache_type', 'result']  # operation: get/set, result: hit/miss/error
)

cache_hit_rate = Gauge(
    'cache_hit_rate',
    'Cache hit rate percentage',
    ['cache_type']  # embedding, metadata, query
)

# Vector search metrics
vector_search_duration_seconds = Histogram(
    'vector_search_duration_seconds',
    'Vector similarity search latency',
    ['table']  # documents or metadata_catalog
)

vector_search_results_total = Counter(
    'vector_search_results_total',
    'Total vector search results returned',
    ['table']
)

# SQL query metrics
sql_query_duration_seconds = Histogram(
    'sql_query_duration_seconds',
    'SQL query execution latency',
    ['query_type']  # select, insert, update, delete
)

sql_query_errors_total = Counter(
    'sql_query_errors_total',
    'Total SQL query errors',
    ['error_type']
)

# LLM metrics
llm_requests_total = Counter(
    'llm_requests_total',
    'Total LLM API requests',
    ['model', 'operation']  # operation: chat, embedding
)

llm_request_duration_seconds = Histogram(
    'llm_request_duration_seconds',
    'LLM API request latency',
    ['model', 'operation']
)

llm_tokens_total = Counter(
    'llm_tokens_total',
    'Total tokens consumed',
    ['model', 'token_type']  # token_type: prompt, completion
)

llm_cost_usd_total = Counter(
    'llm_cost_usd_total',
    'Total estimated cost in USD',
    ['model']
)

# Celery task metrics
celery_task_duration_seconds = Histogram(
    'celery_task_duration_seconds',
    'Celery task execution latency',
    ['task_name', 'status']  # status: success, failure, retry
)

celery_task_total = Counter(
    'celery_task_total',
    'Total Celery tasks executed',
    ['task_name', 'status']
)

celery_queue_length = Gauge(
    'celery_queue_length',
    'Current queue depth',
    ['queue']  # critical, default, low
)

# Database connection metrics
db_connections_active = Gauge(
    'db_connections_active',
    'Number of active database connections',
    ['database']
)

db_connections_idle = Gauge(
    'db_connections_idle',
    'Number of idle database connections',
    ['database']
)

# Document metrics
documents_total = Gauge(
    'documents_total',
    'Total number of documents in vector store'
)

document_chunks_total = Gauge(
    'document_chunks_total',
    'Total number of document chunks'
)

# Table metadata metrics
metadata_catalog_tables_total = Gauge(
    'metadata_catalog_tables_total',
    'Total number of tables in metadata catalog'
)


# Decorator for timing functions
def track_time(metric: Histogram, labels: dict = None):
    """Decorator to track function execution time"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                if labels:
                    metric.labels(**labels).observe(duration)
                else:
                    metric.observe(duration)
                return result
            except Exception as e:
                duration = time.time() - start_time
                if labels:
                    labels['status'] = 'error'
                    metric.labels(**labels).observe(duration)
                else:
                    metric.observe(duration)
                raise
        return wrapper
    return decorator


# Decorator for counting operations
def track_count(metric: Counter, labels: dict):
    """Decorator to count function calls"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                result = func(*args, **kwargs)
                metric.labels(**labels).inc()
                return result
            except Exception as e:
                error_labels = labels.copy()
                error_labels['status'] = 'error'
                metric.labels(**error_labels).inc()
                raise
        return wrapper
    return decorator


# Metrics endpoint for Prometheus scraping
def metrics_endpoint() -> FastAPIResponse:
    """Generate Prometheus metrics"""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


# Helper functions for updating metrics
def update_cache_hit_rate(cache_type: str, hits: int, total: int):
    """Update cache hit rate gauge"""
    if total > 0:
        hit_rate = (hits / total) * 100
        cache_hit_rate.labels(cache_type=cache_type).set(hit_rate)


def get_batch_size_range(batch_size: int) -> str:
    """Convert batch size to range label"""
    if batch_size == 1:
        return '1'
    elif batch_size <= 10:
        return '2-10'
    elif batch_size <= 50:
        return '11-50'
    elif batch_size <= 100:
        return '51-100'
    else:
        return '100+'


def estimate_llm_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """
    Estimate LLM cost in USD
    Pricing as of 2024 (update as needed)
    """
    pricing = {
        'gpt-4o': {
            'prompt': 0.005 / 1000,  # $5 per 1M tokens
            'completion': 0.015 / 1000  # $15 per 1M tokens
        },
        'gpt-4o-mini': {
            'prompt': 0.00015 / 1000,  # $0.15 per 1M tokens
            'completion': 0.0006 / 1000  # $0.60 per 1M tokens
        },
        'text-embedding-3-small': {
            'prompt': 0.00002 / 1000,  # $0.02 per 1M tokens
            'completion': 0
        },
        'text-embedding-3-large': {
            'prompt': 0.00013 / 1000,  # $0.13 per 1M tokens
            'completion': 0
        }
    }
    
    if model not in pricing:
        return 0.0
    
    cost = (
        prompt_tokens * pricing[model]['prompt'] +
        completion_tokens * pricing[model]['completion']
    )
    return cost


# Example usage in code:
# @track_time(embedding_generation_duration_seconds, {'model': 'text-embedding-3-small', 'batch_size_range': '2-10'})
# def generate_embeddings(texts):
#     ...
#
# embedding_requests_total.labels(cache_hit='true', model='text-embedding-3-small').inc()
