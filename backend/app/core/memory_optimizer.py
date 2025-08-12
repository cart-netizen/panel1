"""
Оптимизация памяти и кэширования для ускорения ML операций
"""
import gc
import numpy as np
from functools import lru_cache
import psutil
import os


class MemoryOptimizer:
  """Менеджер оптимизации памяти"""

  def __init__(self):
    self.process = psutil.Process(os.getpid())
    self.initial_memory = self.get_memory_usage()

  def get_memory_usage(self):
    """Возвращает использование памяти в МБ"""
    return self.process.memory_info().rss / 1024 / 1024

  def cleanup_memory(self):
    """Принудительная очистка памяти"""
    gc.collect()  # Сборка мусора Python

    # Очистка numpy кэшей
    try:
      np.core._internal._clear_cache()
    except:
      pass

  def get_memory_stats(self):
    """Статистика памяти"""
    current = self.get_memory_usage()
    return {
      'current_mb': current,
      'initial_mb': self.initial_memory,
      'delta_mb': current - self.initial_memory
    }


# Глобальный оптимизатор памяти
MEMORY_OPTIMIZER = MemoryOptimizer()


@lru_cache(maxsize=128)
def cached_score_features(features_hash, model_hash):
  """Кэширование оценки признаков для ускорения"""
  # Эта функция будет кэшировать результаты оценки
  pass


def optimize_dataframe_memory(df):
  """Оптимизирует использование памяти DataFrame"""
  if df.empty:
    return df

  optimized_df = df.copy()

  # Оптимизация числовых колонок
  for col in optimized_df.select_dtypes(include=['int64']).columns:
    optimized_df[col] = pd.to_numeric(optimized_df[col], downcast='integer')

  for col in optimized_df.select_dtypes(include=['float64']).columns:
    optimized_df[col] = pd.to_numeric(optimized_df[col], downcast='float')

  # Оптимизация строковых колонок
  for col in optimized_df.select_dtypes(include=['object']).columns:
    if optimized_df[col].nunique() / len(optimized_df) < 0.5:  # Если много повторений
      optimized_df[col] = optimized_df[col].astype('category')

  return optimized_df


def batch_process_with_memory_management(items, batch_size=50, cleanup_every=100):
  """Пакетная обработка с управлением памятью"""
  for i in range(0, len(items), batch_size):
    batch = items[i:i + batch_size]

    # Обработка батча
    yield batch

    # Периодическая очистка памяти
    if i % cleanup_every == 0:
      MEMORY_OPTIMIZER.cleanup_memory()