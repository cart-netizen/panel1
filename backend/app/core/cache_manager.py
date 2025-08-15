"""
Менеджер кэширования для масштабирования
"""
import redis
import pickle
import json
from typing import Dict, Any, Optional
from datetime import timedelta, datetime
import logging
from threading import Lock
from backend.app.core.database import SessionLocal, LotteryDraw
from backend.app.core.data_manager import LOTTERY_CONFIGS
logger = logging.getLogger(__name__)


class CacheManager:
  """
  Менеджер кэширования с Redis для масштабирования
  """
  _instance = None
  _lock = Lock()

  def __new__(cls):
    if cls._instance is None:
      with cls._lock:
        if cls._instance is None:
          cls._instance = super().__new__(cls)
    return cls._instance

  def __init__(self, redis_url: str = "redis://localhost:6379"):
    self.redis_client = redis.from_url(redis_url, decode_responses=False)
    self.default_ttl = 3600  # 1 час
    if not hasattr(self, 'initialized'):
      self.cache: Dict[str, Any] = {}
      self.last_draws_cache: Dict[str, Dict] = {}  # Кэш последних тиражей
      self.stats_cache: Dict[str, Any] = {}  # Кэш статистики
      self.cache_ttl = {
        'last_draw': timedelta(minutes=5),
        'stats': timedelta(minutes=2),
        'trends': timedelta(seconds=30)
      }
      self.cache_timestamps: Dict[str, datetime] = {}
      self.initialized = True
      logger.info("CacheManager инициализирован")

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

  def get_last_draw(self, lottery_type: str) -> Optional[Dict]:
      """
      Получить последний тираж из кэша
      """
      cache_key = f"last_draw_{lottery_type}"

      # Проверяем актуальность кэша
      if cache_key in self.cache_timestamps:
        age = datetime.utcnow() - self.cache_timestamps[cache_key]
        if age < self.cache_ttl['last_draw']:
          return self.last_draws_cache.get(lottery_type)

      # Кэш устарел или отсутствует - обновляем
      return self.update_last_draw_cache(lottery_type)

  def update_last_draw_cache(self, lottery_type: str) -> Optional[Dict]:
    """
    Обновить кэш последнего тиража
    """
    db = SessionLocal()
    try:
      latest_draw = db.query(LotteryDraw).filter(
        LotteryDraw.lottery_type == lottery_type
      ).order_by(
        LotteryDraw.draw_number.desc()
      ).first()

      if latest_draw:
        draw_data = {
          'draw_number': latest_draw.draw_number,
          'draw_date': latest_draw.draw_date.isoformat() if hasattr(latest_draw.draw_date, 'isoformat') else str(
            latest_draw.draw_date),
          'field1_numbers': sorted(list(latest_draw.field1_numbers)) if latest_draw.field1_numbers else [],
          'field2_numbers': sorted(list(latest_draw.field2_numbers)) if latest_draw.field2_numbers else [],
          'lottery_type': lottery_type
        }

        # Сохраняем в кэш
        self.last_draws_cache[lottery_type] = draw_data
        self.cache_timestamps[f"last_draw_{lottery_type}"] = datetime.utcnow()

        logger.info(f"Кэш последнего тиража обновлен для {lottery_type}: #{draw_data['draw_number']}")
        return draw_data

      return None

    except Exception as e:
      logger.error(f"Ошибка обновления кэша последнего тиража: {e}")
      return None
    finally:
      db.close()

  def update_all_last_draws(self):
    """
    Обновить кэш последних тиражей для всех лотерей
    """
    for lottery_type in LOTTERY_CONFIGS.keys():
      self.update_last_draw_cache(lottery_type)
    logger.info("Кэш всех последних тиражей обновлен")

  def invalidate_cache(self, cache_type: str = None, lottery_type: str = None):
    """
    Инвалидировать кэш
    """
    if cache_type == 'last_draw' and lottery_type:
      if lottery_type in self.last_draws_cache:
        del self.last_draws_cache[lottery_type]
        cache_key = f"last_draw_{lottery_type}"
        if cache_key in self.cache_timestamps:
          del self.cache_timestamps[cache_key]
        logger.info(f"Кэш последнего тиража очищен для {lottery_type}")
    elif cache_type == 'all':
      self.last_draws_cache.clear()
      self.stats_cache.clear()
      self.cache_timestamps.clear()
      logger.info("Весь кэш очищен")

  def get_stats(self, key: str) -> Optional[Any]:
    """
    Получить статистику из кэша
    """
    cache_key = f"stats_{key}"
    if cache_key in self.cache_timestamps:
      age = datetime.utcnow() - self.cache_timestamps[cache_key]
      if age < self.cache_ttl['stats']:
        return self.stats_cache.get(key)
    return None

  def set_stats(self, key: str, value: Any):
    """
    Сохранить статистику в кэш
    """
    self.stats_cache[key] = value
    self.cache_timestamps[f"stats_{key}"] = datetime.utcnow()

# Глобальный менеджер кэша
GLOBAL_CACHE = CacheManager()
CACHE_MANAGER = CacheManager()