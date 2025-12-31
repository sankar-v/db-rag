"""
Embedding Service with caching and batch processing
Handles all embedding generation with Redis caching
"""
import hashlib
import json
import logging
from typing import List, Optional, Dict, Any
from openai import OpenAI
import redis

from config import LLMConfig, CacheConfig


logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating embeddings with caching and batching"""
    
    def __init__(self, llm_config: LLMConfig, cache_config: CacheConfig):
        self.llm_config = llm_config
        self.cache_config = cache_config
        self.client = OpenAI(api_key=llm_config.api_key)
        
        # Initialize Redis cache
        self.cache_enabled = cache_config.enabled
        if self.cache_enabled:
            try:
                self.redis_client = redis.Redis(
                    host=cache_config.redis_host,
                    port=cache_config.redis_port,
                    db=cache_config.redis_db,
                    password=cache_config.redis_password,
                    decode_responses=False  # We'll handle encoding
                )
                # Test connection
                self.redis_client.ping()
                logger.info(f"Connected to Redis at {cache_config.redis_host}:{cache_config.redis_port}")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                self.cache_enabled = False
                self.redis_client = None
        else:
            self.redis_client = None
            logger.info("Cache disabled")
        
        # Batch size for OpenAI API (max 2048)
        self.max_batch_size = 2048
        
        # Metrics
        self.cache_hits = 0
        self.cache_misses = 0
        self.api_calls = 0
    
    def _get_cache_key(self, text: str) -> str:
        """Generate cache key from text"""
        text_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()
        return f"emb:v1:{text_hash}"
    
    def _get_from_cache(self, text: str) -> Optional[List[float]]:
        """Get embedding from cache"""
        if not self.cache_enabled or not self.redis_client:
            return None
        
        try:
            cache_key = self._get_cache_key(text)
            cached_value = self.redis_client.get(cache_key)
            
            if cached_value:
                self.cache_hits += 1
                logger.debug(f"Cache hit for text (length={len(text)})")
                return json.loads(cached_value)
            else:
                self.cache_misses += 1
                return None
        except Exception as e:
            logger.error(f"Cache read error: {e}")
            return None
    
    def _set_in_cache(self, text: str, embedding: List[float], ttl: Optional[int] = None):
        """Store embedding in cache"""
        if not self.cache_enabled or not self.redis_client:
            return
        
        try:
            cache_key = self._get_cache_key(text)
            cache_value = json.dumps(embedding)
            
            if ttl is None:
                ttl = self.cache_config.embedding_cache_ttl
            
            self.redis_client.setex(cache_key, ttl, cache_value)
            logger.debug(f"Cached embedding for text (length={len(text)})")
        except Exception as e:
            logger.error(f"Cache write error: {e}")
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text with caching
        
        Args:
            text: Input text
            
        Returns:
            Embedding vector
        """
        # Check cache first
        cached_embedding = self._get_from_cache(text)
        if cached_embedding is not None:
            return cached_embedding
        
        # Generate embedding via API
        try:
            self.api_calls += 1
            response = self.client.embeddings.create(
                input=text,
                model=self.llm_config.embedding_model
            )
            embedding = response.data[0].embedding
            
            # Cache the result
            self._set_in_cache(text, embedding)
            
            logger.info(f"Generated embedding via API (length={len(text)})")
            return embedding
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise
    
    def generate_embeddings_batch(
        self, 
        texts: List[str],
        show_progress: bool = False
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts with caching and batching
        
        Args:
            texts: List of input texts
            show_progress: Log progress for large batches
            
        Returns:
            List of embedding vectors (same order as input)
        """
        if not texts:
            return []
        
        # Initialize result array with None placeholders
        embeddings: List[Optional[List[float]]] = [None] * len(texts)
        
        # Track which texts need API calls
        uncached_texts = []
        uncached_indices = []
        
        # Check cache for each text
        for i, text in enumerate(texts):
            cached_embedding = self._get_from_cache(text)
            if cached_embedding is not None:
                embeddings[i] = cached_embedding
            else:
                uncached_texts.append(text)
                uncached_indices.append(i)
        
        # Log cache performance
        if texts:
            cache_hit_rate = (len(texts) - len(uncached_texts)) / len(texts) * 100
            logger.info(
                f"Batch embedding request: {len(texts)} texts, "
                f"{len(texts) - len(uncached_texts)} from cache ({cache_hit_rate:.1f}%), "
                f"{len(uncached_texts)} need API calls"
            )
        
        # Generate embeddings for uncached texts in batches
        if uncached_texts:
            for batch_start in range(0, len(uncached_texts), self.max_batch_size):
                batch_end = min(batch_start + self.max_batch_size, len(uncached_texts))
                batch_texts = uncached_texts[batch_start:batch_end]
                
                if show_progress:
                    logger.info(
                        f"Processing batch {batch_start//self.max_batch_size + 1}: "
                        f"texts {batch_start+1}-{batch_end} of {len(uncached_texts)}"
                    )
                
                try:
                    self.api_calls += 1
                    response = self.client.embeddings.create(
                        input=batch_texts,
                        model=self.llm_config.embedding_model
                    )
                    
                    # Process results
                    for idx, embedding_data in enumerate(response.data):
                        original_idx = uncached_indices[batch_start + idx]
                        embedding = embedding_data.embedding
                        
                        # Store in result array
                        embeddings[original_idx] = embedding
                        
                        # Cache the embedding
                        self._set_in_cache(batch_texts[idx], embedding)
                    
                    logger.info(f"Generated {len(batch_texts)} embeddings via API")
                    
                except Exception as e:
                    logger.error(f"Failed to generate batch embeddings: {e}")
                    raise
        
        # Verify all embeddings were generated
        if None in embeddings:
            raise RuntimeError("Some embeddings failed to generate")
        
        return embeddings  # type: ignore
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self.cache_hits + self.cache_misses
        hit_rate = (self.cache_hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "cache_enabled": self.cache_enabled,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_rate": f"{hit_rate:.2f}%",
            "api_calls": self.api_calls,
            "total_requests": total_requests
        }
    
    def clear_cache(self, pattern: str = "emb:*"):
        """Clear embeddings from cache"""
        if not self.cache_enabled or not self.redis_client:
            logger.warning("Cache not enabled, nothing to clear")
            return 0
        
        try:
            keys = list(self.redis_client.scan_iter(match=pattern))
            if keys:
                deleted = self.redis_client.delete(*keys)
                logger.info(f"Cleared {deleted} embeddings from cache")
                return deleted
            return 0
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            return 0
    
    def close(self):
        """Close Redis connection"""
        if self.redis_client:
            try:
                self.redis_client.close()
                logger.info("Closed Redis connection")
            except Exception as e:
                logger.error(f"Error closing Redis connection: {e}")
