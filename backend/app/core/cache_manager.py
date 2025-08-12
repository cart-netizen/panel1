"""
Менеджер кэширования для масштабирования
"""
import redis
import pickle
import json
from typing import Any, Optional
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


class CacheManager:
  """
  Менеджер кэширования с Redis для масштабирования
  """

  def __init__(self, redis_url: str = "redis://localhost:6379"):
    self.redis_client = redis.from_url(redis_url, decode_responses=False)
    self.default_ttl = 3600  # 1 час

  async def get(self, key: str) -> Optional[Any]:
    """Получить значение из кэша"""
    try:
      data = self.redis_client.get(key)
      if data:
        return pickle.loads(data)
      return None
    except Exception as e:
      logger.error(f"Cache get error: {e}")
      return None

  async def set(self, key: str, value: Any, ttl: int = None) -> bool:
    """Сохранить значение в кэш"""
    try:
      ttl = ttl or self.default_ttl
      data = pickle.dumps(value)
      return self.redis_client.setex(key, ttl, data)
    except Exception as e:
      logger.error(f"Cache set error: {e}")
      return False

  async def delete(self, key: str) -> bool:
    """Удалить значение из кэша"""
    try:
      return bool(self.redis_client.delete(key))
    except Exception as e:
      logger.error(f"Cache delete error: {e}")
      return False

  def generate_key(self, prefix: str, **kwargs) -> str:
    """Генерирует ключ кэша"""
    params = "_".join(f"{k}_{v}" for k, v in sorted(kwargs.items()))
    return f"{prefix}:{params}"


# Глобальный менеджер кэша
GLOBAL_CACHE = CacheManager()