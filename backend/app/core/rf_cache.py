"""
Кэширование RF оценок для максимальной скорости
"""
import threading
import hashlib
import pickle
from typing import Dict, Tuple, Optional
import time


class RFScoreCache:
  """Кэш оценок RF модели для ультра быстрого доступа"""

  def __init__(self, max_cache_size=1000):
    self._cache: Dict[str, float] = {}
    self._cache_timestamps: Dict[str, float] = {}
    self._lock = threading.Lock()
    self.max_cache_size = max_cache_size
    self.cache_ttl = 7200  # 1 час TTL для оценок

    # Статистика
    self.hits = 0
    self.misses = 0

  def _get_combination_key(self, f1: list, f2: list) -> str:
    """Создает уникальный ключ для комбинации"""
    # Сортируем для консистентности
    f1_sorted = tuple(sorted(f1))
    f2_sorted = tuple(sorted(f2))

    # Создаем хэш
    combination_str = f"{f1_sorted}|{f2_sorted}"
    return hashlib.md5(combination_str.encode()).hexdigest()[:16]  # Короткий хэш

  def get_score(self, f1: list, f2: list) -> Optional[float]:
    """Получает кэшированную оценку"""
    key = self._get_combination_key(f1, f2)

    with self._lock:
      if key in self._cache:
        # Проверяем актуальность - УВЕЛИЧИВАЕМ TTL
        timestamp = self._cache_timestamps.get(key, 0)
        if time.time() - timestamp < self.cache_ttl:
          self.hits += 1
          # НОВОЕ: Обновляем timestamp при использовании (LRU)
          self._cache_timestamps[key] = time.time()
          return self._cache[key]
        else:
          # Удаляем устаревшую запись
          del self._cache[key]
          del self._cache_timestamps[key]

      self.misses += 1
      return None

  def set_score(self, f1: list, f2: list, score: float):
    """Сохраняет оценку в кэш"""
    key = self._get_combination_key(f1, f2)

    with self._lock:
      # Проверяем размер кэша
      if len(self._cache) >= self.max_cache_size:
        self._cleanup_old_entries()

      self._cache[key] = score
      self._cache_timestamps[key] = time.time()

  def _cleanup_old_entries(self):
    """Очищает старые записи"""
    current_time = time.time()
    keys_to_remove = []

    for key, timestamp in self._cache_timestamps.items():
      if current_time - timestamp > self.cache_ttl:
        keys_to_remove.append(key)

    # Удаляем старые записи
    for key in keys_to_remove:
      self._cache.pop(key, None)
      self._cache_timestamps.pop(key, None)

    # Если все еще переполнен, удаляем самые старые
    if len(self._cache) >= self.max_cache_size:
      sorted_keys = sorted(
        self._cache_timestamps.items(),
        key=lambda x: x[1]
      )

      # Удаляем 20% самых старых
      remove_count = max(1, len(sorted_keys) // 5)
      for key, _ in sorted_keys[:remove_count]:
        self._cache.pop(key, None)
        self._cache_timestamps.pop(key, None)

  def get_stats(self) -> dict:
    """Статистика кэша"""
    with self._lock:
      total_requests = self.hits + self.misses
      hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0

      return {
        'cache_size': len(self._cache),
        'hits': self.hits,
        'misses': self.misses,
        'hit_rate_percent': hit_rate,
        'max_size': self.max_cache_size
      }

  def clear_cache(self):
    """Очищает весь кэш"""
    with self._lock:
      self._cache.clear()
      self._cache_timestamps.clear()
      self.hits = 0
      self.misses = 0


# Глобальный экземпляр кэша
GLOBAL_RF_CACHE = RFScoreCache(max_cache_size=2000)  # Кэш на 2000 комбинаций