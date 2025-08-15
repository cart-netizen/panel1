"""
Глобальное кэширование данных для максимальной скорости
"""
import threading
import time
from typing import Dict, Any, Optional
import pandas as pd


class GlobalDataCache:
  """Глобальный кэш данных с автоматическим обновлением"""

  def __init__(self):
    self._cache: Dict[str, Any] = {}
    self._cache_timestamps: Dict[str, float] = {}
    self._lock = threading.Lock()
    self._cache_ttl = 300  # 5 минут TTL

  def get_cached_history(self, lottery_type: str, force_refresh: bool = False):
    """Получает кэшированную историю тиражей"""
    cache_key = f"history_{lottery_type}"

    with self._lock:
      # Проверяем актуальность кэша
      if not force_refresh and cache_key in self._cache:
        timestamp = self._cache_timestamps.get(cache_key, 0)
        if time.time() - timestamp < self._cache_ttl:
          print(f"📋 Используем кэшированную историю для {lottery_type}")
          return self._cache[cache_key]

      # Обновляем кэш
      print(f"🔄 Обновление кэша истории для {lottery_type}")
      try:
        from backend.app.core import data_manager
        df = data_manager.fetch_draws_from_db()

        self._cache[cache_key] = df
        self._cache_timestamps[cache_key] = time.time()

        print(f"✅ Кэш обновлен: {len(df)} тиражей для {lottery_type}")
        return df
      except Exception as e:
        print(f"❌ Ошибка обновления кэша: {e}")
        return pd.DataFrame()

  def invalidate_cache(self, lottery_type: str = None):
    """Принудительно очищает кэш"""
    with self._lock:
      if lottery_type:
        cache_key = f"history_{lottery_type}"
        self._cache.pop(cache_key, None)
        self._cache_timestamps.pop(cache_key, None)
        print(f"🗑️ Кэш очищен для {lottery_type}")
      else:
        self._cache.clear()
        self._cache_timestamps.clear()
        print(f"🗑️ Весь кэш очищен")

  def get_cache_stats(self):
    """Статистика кэша"""
    with self._lock:
      stats = {}
      for key, timestamp in self._cache_timestamps.items():
        age_seconds = time.time() - timestamp
        stats[key] = {
          'age_seconds': age_seconds,
          'age_minutes': age_seconds / 60,
          'size_mb': len(str(self._cache.get(key, ''))) / 1024 / 1024
        }
      return stats


# Глобальный экземпляр кэша
GLOBAL_DATA_CACHE = GlobalDataCache()