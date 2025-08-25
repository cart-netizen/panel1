"""
Кодирование и декодирование состояний для RL
Преобразование между различными представлениями состояний
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional
from sklearn.preprocessing import StandardScaler
import hashlib
import json
import logging

logger = logging.getLogger(__name__)


class StateEncoder:
  """
  Кодировщик состояний для эффективного хранения и обработки
  """

  def __init__(self, feature_dims: Dict[str, int], use_normalization: bool = True):
    """
    Args:
        feature_dims: Размерности признаков {'feature_name': max_value}
        use_normalization: Использовать нормализацию
    """
    self.feature_dims = feature_dims
    self.use_normalization = use_normalization

    # Для нормализации
    self.scaler = StandardScaler() if use_normalization else None
    self.is_fitted = False

    # Дискретизация для Q-таблицы
    self.discretization_bins = {
      'universe_length': 10,
      'parity_ratio': 5,
      'mean_gap': 10,
      'mean_frequency': 5,
      'hot_numbers_count': 5,
      'cold_numbers_count': 5,
      'sum_trend': 5,
      'diversity_index': 5
    }

    # Кэш кодирований
    self._encoding_cache = {}

    logger.info(f"✅ StateEncoder инициализирован с {len(feature_dims)} признаками")

  def encode_continuous(self, state_dict: Dict) -> np.ndarray:
    """
    Кодирование в непрерывный вектор для нейросетей

    Args:
        state_dict: Словарь признаков состояния

    Returns:
        Нормализованный вектор признаков
    """
    # Преобразуем в вектор
    vector = []
    for feature_name in self.feature_dims.keys():
      if feature_name in state_dict:
        value = state_dict[feature_name]
        # Нормализуем в [0, 1]
        max_val = self.feature_dims[feature_name]
        normalized = value / max_val if max_val > 0 else 0
        vector.append(normalized)
      else:
        vector.append(0.0)

    vector = np.array(vector, dtype=np.float32)

    # Дополнительная нормализация если нужно
    if self.use_normalization and self.scaler:
      if not self.is_fitted:
        # Для первого вызова просто возвращаем как есть
        return vector
      vector = self.scaler.transform(vector.reshape(1, -1))[0]

    return vector

  def encode_discrete(self, state_dict: Dict) -> str:
    """
    Дискретное кодирование для Q-таблицы

    Args:
        state_dict: Словарь признаков состояния

    Returns:
        Строковый ключ для Q-таблицы
    """
    # Проверяем кэш
    state_str = json.dumps(state_dict, sort_keys=True)
    if state_str in self._encoding_cache:
      return self._encoding_cache[state_str]

    # Дискретизируем каждый признак
    discrete_values = []

    for feature_name, num_bins in self.discretization_bins.items():
      if feature_name in state_dict:
        value = state_dict[feature_name]
        max_val = self.feature_dims.get(feature_name, 100)

        # Вычисляем бин
        normalized = value / max_val if max_val > 0 else 0
        bin_idx = min(int(normalized * num_bins), num_bins - 1)
        discrete_values.append(f"{feature_name}:{bin_idx}")

    # Создаем уникальный ключ
    key = "|".join(discrete_values)

    # Кэшируем
    self._encoding_cache[state_str] = key

    return key

  def encode_hash(self, state_dict: Dict) -> str:
    """
    Хэш-кодирование для компактного хранения

    Args:
        state_dict: Словарь признаков состояния

    Returns:
        Хэш состояния
    """
    # Сортируем для консистентности
    sorted_items = sorted(state_dict.items())
    state_str = json.dumps(sorted_items)

    # Вычисляем хэш
    hash_obj = hashlib.md5(state_str.encode())
    return hash_obj.hexdigest()[:16]  # Берем первые 16 символов

  def decode_discrete(self, encoded_state: str) -> Dict:
    """
    Декодирование дискретного состояния обратно в словарь

    Args:
        encoded_state: Закодированная строка

    Returns:
        Приблизительный словарь признаков
    """
    state_dict = {}

    parts = encoded_state.split("|")
    for part in parts:
      if ":" in part:
        feature_name, bin_idx = part.split(":")
        bin_idx = int(bin_idx)

        # Восстанавливаем приблизительное значение
        if feature_name in self.discretization_bins:
          num_bins = self.discretization_bins[feature_name]
          max_val = self.feature_dims.get(feature_name, 100)

          # Центр бина
          normalized = (bin_idx + 0.5) / num_bins
          value = normalized * max_val
          state_dict[feature_name] = value

    return state_dict

  def fit(self, states: List[Dict]):
    """
    Обучение нормализатора на наборе состояний

    Args:
        states: Список состояний для обучения
    """
    if not self.use_normalization or not self.scaler:
      return

    # Собираем все векторы
    vectors = []
    for state_dict in states:
      vector = self.encode_continuous(state_dict)
      vectors.append(vector)

    if vectors:
      vectors = np.array(vectors)
      self.scaler.fit(vectors)
      self.is_fitted = True
      logger.info(f"📊 Scaler обучен на {len(vectors)} состояниях")

  def get_feature_importance(self, state_dict: Dict) -> Dict[str, float]:
    """
    Оценка важности признаков в состоянии

    Args:
        state_dict: Словарь признаков

    Returns:
        Словарь с важностью каждого признака
    """
    importance = {}

    for feature_name, value in state_dict.items():
      if feature_name in self.feature_dims:
        max_val = self.feature_dims[feature_name]
        # Простая эвристика: отклонение от среднего
        normalized = value / max_val if max_val > 0 else 0
        deviation = abs(normalized - 0.5) * 2  # [0, 1]
        importance[feature_name] = deviation

    # Нормализуем важности
    total = sum(importance.values())
    if total > 0:
      for key in importance:
        importance[key] /= total

    return importance


class ActionEncoder:
  """
  Кодировщик действий (комбинаций чисел)
  """

  def __init__(self, lottery_config: Dict):
    """
    Args:
        lottery_config: Конфигурация лотереи
    """
    self.lottery_config = lottery_config
    self.field1_size = lottery_config['field1_size']
    self.field2_size = lottery_config['field2_size']
    self.field1_max = lottery_config['field1_max']
    self.field2_max = lottery_config['field2_max']

    # Кэш для быстрого доступа
    self._action_cache = {}
    self._index_cache = {}

    logger.info(f"✅ ActionEncoder инициализирован для лотереи {self.field1_size}/{self.field1_max}")

  def encode(self, field1: List[int], field2: List[int]) -> str:
    """
    Кодирование действия в строку

    Args:
        field1: Числа первого поля
        field2: Числа второго поля

    Returns:
        Закодированное действие
    """
    # Сортируем для консистентности
    f1_sorted = sorted(field1)
    f2_sorted = sorted(field2)

    # Создаем ключ
    key = f"F1:{','.join(map(str, f1_sorted))}|F2:{','.join(map(str, f2_sorted))}"
    return key

  def decode(self, encoded_action: str) -> Tuple[List[int], List[int]]:
    """
    Декодирование действия из строки

    Args:
        encoded_action: Закодированное действие

    Returns:
        (field1, field2)
    """
    parts = encoded_action.split("|")

    field1 = []
    field2 = []

    for part in parts:
      if part.startswith("F1:"):
        numbers = part[3:].split(",")
        field1 = [int(n) for n in numbers if n]
      elif part.startswith("F2:"):
        numbers = part[3:].split(",")
        field2 = [int(n) for n in numbers if n]

    return field1, field2

  def action_to_index(self, field1: List[int], field2: List[int]) -> int:
    """
    Преобразование действия в индекс (для нейросетей)

    Упрощенная версия - использует хэш
    """
    action_str = self.encode(field1, field2)

    if action_str in self._index_cache:
      return self._index_cache[action_str]

    # Простой хэш в диапазоне
    hash_val = hash(action_str)
    index = abs(hash_val) % 1000000  # Ограничиваем миллионом

    self._index_cache[action_str] = index
    return index

  def index_to_action(self, index: int) -> Optional[Tuple[List[int], List[int]]]:
    """
    Обратное преобразование индекса в действие

    Требует предварительного кэширования
    """
    # Ищем в кэше
    for action_str, cached_idx in self._index_cache.items():
      if cached_idx == index:
        return self.decode(action_str)

    # Не найдено - генерируем случайное
    import random
    field1 = sorted(random.sample(range(1, self.field1_max + 1), self.field1_size))
    field2 = sorted(random.sample(range(1, self.field2_max + 1), self.field2_size))

    return field1, field2

  def sample_random_action(self) -> Tuple[List[int], List[int]]:
    """Генерация случайного действия"""
    import random
    field1 = sorted(random.sample(range(1, self.field1_max + 1), self.field1_size))
    field2 = sorted(random.sample(range(1, self.field2_max + 1), self.field2_size))
    return field1, field2