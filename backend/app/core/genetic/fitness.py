"""
Фитнесс-функции для генетического алгоритма
Комплексная оценка приспособленности комбинаций на основе исторических данных
"""

import numpy as np
import pandas as pd
from typing import List, Tuple, Dict, Optional, Callable
from collections import Counter
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class FitnessEvaluator:
  """
  Оценщик приспособленности хромосом
  Использует множественные критерии для комплексной оценки
  """

  def __init__(self, df_history: pd.DataFrame, lottery_config: Dict):
    """
    Args:
        df_history: История тиражей
        lottery_config: Конфигурация лотереи
    """
    self.df_history = df_history
    self.lottery_config = lottery_config

    # Параметры лотереи
    self.field1_size = lottery_config['field1_size']
    self.field2_size = lottery_config['field2_size']
    self.field1_max = lottery_config['field1_max']
    self.field2_max = lottery_config['field2_max']

    # Предварительные вычисления для ускорения
    self._precompute_statistics()

    # Веса компонентов фитнесс-функции
    self.weights = {
      'historical_matches': 0.3,  # Совпадения с историей
      'frequency_alignment': 0.2,  # Соответствие частотам
      'pattern_similarity': 0.15,  # Схожесть с паттернами
      'balance_score': 0.1,  # Баланс чет/нечет, малые/большие
      'sum_range': 0.1,  # Попадание в диапазон сумм
      'uniqueness': 0.05,  # Уникальность комбинации
      'trend_alignment': 0.1  # Соответствие трендам
    }

    # Кэш для ускорения
    self._fitness_cache = {}
    self._cache_hits = 0
    self._cache_misses = 0

    logger.info(f"✅ FitnessEvaluator инициализирован с {len(df_history)} тиражами")

  def _precompute_statistics(self):
    """Предварительные вычисления статистики для ускорения"""
    if self.df_history.empty:
      self._init_empty_stats()
      return

    # Частоты чисел
    self.freq_field1 = Counter()
    self.freq_field2 = Counter()

    # Суммы комбинаций
    self.sums_field1 = []
    self.sums_field2 = []

    # Паттерны чет/нечет
    self.parity_patterns = []

    # Обрабатываем историю
    for _, row in self.df_history.iterrows():
      f1_list = row.get('Числа_Поле1_list', [])
      f2_list = row.get('Числа_Поле2_list', [])

      if isinstance(f1_list, list):
        self.freq_field1.update(f1_list)
        self.sums_field1.append(sum(f1_list))

      if isinstance(f2_list, list):
        self.freq_field2.update(f2_list)
        self.sums_field2.append(sum(f2_list))

      # Паттерн четности
      if isinstance(f1_list, list) and isinstance(f2_list, list):
        even_count = sum(1 for n in f1_list + f2_list if n % 2 == 0)
        self.parity_patterns.append(even_count)

    # Статистика сумм
    if self.sums_field1:
      self.sum_stats_f1 = {
        'mean': np.mean(self.sums_field1),
        'std': np.std(self.sums_field1),
        'min': np.min(self.sums_field1),
        'max': np.max(self.sums_field1)
      }
    else:
      self.sum_stats_f1 = {'mean': 0, 'std': 1, 'min': 0, 'max': 100}

    if self.sums_field2:
      self.sum_stats_f2 = {
        'mean': np.mean(self.sums_field2),
        'std': np.std(self.sums_field2),
        'min': np.min(self.sums_field2),
        'max': np.max(self.sums_field2)
      }
    else:
      self.sum_stats_f2 = {'mean': 0, 'std': 1, 'min': 0, 'max': 100}

    # Горячие и холодные числа
    self._calculate_hot_cold_numbers()

    logger.info(f"📊 Предвычислено: частоты для {len(self.freq_field1)} чисел поля 1, "
                f"{len(self.freq_field2)} чисел поля 2")

  def _init_empty_stats(self):
    """Инициализация пустой статистики"""
    self.freq_field1 = Counter()
    self.freq_field2 = Counter()
    self.sums_field1 = []
    self.sums_field2 = []
    self.parity_patterns = []
    self.sum_stats_f1 = {'mean': 50, 'std': 10, 'min': 10, 'max': 90}
    self.sum_stats_f2 = {'mean': 50, 'std': 10, 'min': 10, 'max': 90}
    self.hot_numbers_f1 = []
    self.cold_numbers_f1 = []
    self.hot_numbers_f2 = []
    self.cold_numbers_f2 = []

  def _calculate_hot_cold_numbers(self, percentile: float = 0.2):
    """Вычисление горячих и холодных чисел"""
    # Field1
    if self.freq_field1:
      sorted_f1 = sorted(self.freq_field1.items(), key=lambda x: x[1], reverse=True)
      hot_count = max(1, int(len(sorted_f1) * percentile))
      self.hot_numbers_f1 = [num for num, _ in sorted_f1[:hot_count]]
      self.cold_numbers_f1 = [num for num, _ in sorted_f1[-hot_count:]]
    else:
      self.hot_numbers_f1 = []
      self.cold_numbers_f1 = []

    # Field2
    if self.freq_field2:
      sorted_f2 = sorted(self.freq_field2.items(), key=lambda x: x[1], reverse=True)
      hot_count = max(1, int(len(sorted_f2) * percentile))
      self.hot_numbers_f2 = [num for num, _ in sorted_f2[:hot_count]]
      self.cold_numbers_f2 = [num for num, _ in sorted_f2[-hot_count:]]
    else:
      self.hot_numbers_f2 = []
      self.cold_numbers_f2 = []

  def evaluate(self, field1: List[int], field2: List[int]) -> float:
    """
    Главная функция оценки приспособленности

    Args:
        field1: Числа первого поля
        field2: Числа второго поля

    Returns:
        Значение fitness от 0 до 100+
    """
    # Проверяем кэш
    cache_key = (tuple(sorted(field1)), tuple(sorted(field2)))
    if cache_key in self._fitness_cache:
      self._cache_hits += 1
      return self._fitness_cache[cache_key]

    self._cache_misses += 1

    # Вычисляем компоненты fitness
    scores = {}

    # 1. Исторические совпадения
    scores['historical_matches'] = self._evaluate_historical_matches(field1, field2)

    # 2. Соответствие частотам
    scores['frequency_alignment'] = self._evaluate_frequency_alignment(field1, field2)

    # 3. Схожесть с паттернами
    scores['pattern_similarity'] = self._evaluate_pattern_similarity(field1, field2)

    # 4. Баланс
    scores['balance_score'] = self._evaluate_balance(field1, field2)

    # 5. Диапазон сумм
    scores['sum_range'] = self._evaluate_sum_range(field1, field2)

    # 6. Уникальность
    scores['uniqueness'] = self._evaluate_uniqueness(field1, field2)

    # 7. Соответствие трендам
    scores['trend_alignment'] = self._evaluate_trend_alignment(field1, field2)

    # Взвешенная сумма
    total_fitness = sum(scores[key] * self.weights[key] for key in scores)

    # Нормализация и масштабирование (0-100+)
    total_fitness = total_fitness * 100

    # Сохраняем в кэш
    self._fitness_cache[cache_key] = total_fitness

    # Ограничиваем размер кэша
    if len(self._fitness_cache) > 10000:
      # Удаляем старые записи
      keys_to_remove = list(self._fitness_cache.keys())[:5000]
      for key in keys_to_remove:
        del self._fitness_cache[key]

    return total_fitness

  def _evaluate_historical_matches(self, field1: List[int], field2: List[int]) -> float:
    """Оценка совпадений с историческими тиражами"""
    if self.df_history.empty:
      return 0.5

    max_matches = 0
    total_matches = 0
    recent_weight = 1.5  # Больший вес недавним тиражам

    for idx, row in self.df_history.head(100).iterrows():  # Последние 100 тиражей
      f1_hist = set(row.get('Числа_Поле1_list', []))
      f2_hist = set(row.get('Числа_Поле2_list', []))

      matches_f1 = len(set(field1) & f1_hist)
      matches_f2 = len(set(field2) & f2_hist)

      # Взвешиваем по давности
      weight = recent_weight if idx < 20 else 1.0
      match_score = (matches_f1 / self.field1_size + matches_f2 / self.field2_size) / 2
      total_matches += match_score * weight

      max_matches = max(max_matches, matches_f1 + matches_f2)

    # Нормализуем
    avg_matches = total_matches / min(100, len(self.df_history))

    # Штраф за слишком точное совпадение (возможно, комбинация уже была)
    if max_matches == self.field1_size + self.field2_size:
      avg_matches *= 0.5

    return min(1.0, avg_matches)

  def _evaluate_frequency_alignment(self, field1: List[int], field2: List[int]) -> float:
    """Оценка соответствия частотным характеристикам"""
    if not self.freq_field1 and not self.freq_field2:
      return 0.5

    score = 0.0

    # Field1
    if self.freq_field1:
      hot_in_combo = len(set(field1) & set(self.hot_numbers_f1))
      cold_in_combo = len(set(field1) & set(self.cold_numbers_f1))

      # Оптимальное соотношение: больше горячих, меньше холодных
      hot_ratio = hot_in_combo / max(1, len(self.hot_numbers_f1))
      cold_ratio = 1 - (cold_in_combo / max(1, len(self.cold_numbers_f1)))

      score += (hot_ratio * 0.6 + cold_ratio * 0.4) * 0.5

    # Field2
    if self.freq_field2:
      hot_in_combo = len(set(field2) & set(self.hot_numbers_f2))
      cold_in_combo = len(set(field2) & set(self.cold_numbers_f2))

      hot_ratio = hot_in_combo / max(1, len(self.hot_numbers_f2))
      cold_ratio = 1 - (cold_in_combo / max(1, len(self.cold_numbers_f2)))

      score += (hot_ratio * 0.6 + cold_ratio * 0.4) * 0.5

    return score

  def _evaluate_pattern_similarity(self, field1: List[int], field2: List[int]) -> float:
    """Оценка схожести с историческими паттернами"""
    if not self.parity_patterns:
      return 0.5

    # Паттерн четности текущей комбинации
    all_numbers = field1 + field2
    even_count = sum(1 for n in all_numbers if n % 2 == 0)

    # Сравниваем с историческим распределением
    if self.parity_patterns:
      avg_even = np.mean(self.parity_patterns)
      std_even = np.std(self.parity_patterns) if len(self.parity_patterns) > 1 else 1

      # Z-score
      if std_even > 0:
        z_score = abs(even_count - avg_even) / std_even
        # Чем ближе к среднему, тем лучше
        score = max(0, 1 - z_score / 3)  # 3 сигмы
      else:
        score = 0.5
    else:
      score = 0.5

    # Проверяем последовательности
    sequence_score = self._check_sequences(all_numbers)

    return (score + sequence_score) / 2

  def _check_sequences(self, numbers: List[int]) -> float:
    """Проверка на последовательности чисел"""
    sorted_nums = sorted(numbers)
    max_seq = 1
    current_seq = 1

    for i in range(1, len(sorted_nums)):
      if sorted_nums[i] == sorted_nums[i - 1] + 1:
        current_seq += 1
        max_seq = max(max_seq, current_seq)
      else:
        current_seq = 1

    # Штраф за слишком длинные последовательности
    if max_seq >= 4:
      return 0.2
    elif max_seq == 3:
      return 0.5
    elif max_seq == 2:
      return 0.8
    else:
      return 1.0

  def _evaluate_balance(self, field1: List[int], field2: List[int]) -> float:
    """Оценка баланса комбинации"""
    all_numbers = field1 + field2

    # Баланс четных/нечетных
    even_count = sum(1 for n in all_numbers if n % 2 == 0)
    even_ratio = even_count / len(all_numbers)
    parity_score = 1 - abs(0.5 - even_ratio) * 2  # Оптимально 50/50

    # Баланс малых/больших
    mid_point1 = self.field1_max // 2
    mid_point2 = self.field2_max // 2

    small_f1 = sum(1 for n in field1 if n <= mid_point1)
    small_f2 = sum(1 for n in field2 if n <= mid_point2)

    small_ratio = (small_f1 + small_f2) / (len(field1) + len(field2))
    size_score = 1 - abs(0.5 - small_ratio) * 2

    # Распределение по декадам (для field1_max=20: 1-10, 11-20)
    decades_f1 = Counter((n - 1) // 10 for n in field1)
    decades_f2 = Counter((n - 1) // 10 for n in field2)

    # Проверяем равномерность распределения
    decade_score = 1.0
    if len(decades_f1) == 1:  # Все числа из одной декады
      decade_score *= 0.5
    if len(decades_f2) == 1:
      decade_score *= 0.5

    return (parity_score + size_score + decade_score) / 3

  def _evaluate_sum_range(self, field1: List[int], field2: List[int]) -> float:
    """Оценка попадания суммы в оптимальный диапазон"""
    sum_f1 = sum(field1)
    sum_f2 = sum(field2)

    score = 0.0

    # Field1
    if self.sum_stats_f1['std'] > 0:
      z_score_f1 = abs(sum_f1 - self.sum_stats_f1['mean']) / self.sum_stats_f1['std']
      score_f1 = max(0, 1 - z_score_f1 / 2)  # В пределах 2 сигм
    else:
      score_f1 = 0.5

    # Field2
    if self.sum_stats_f2['std'] > 0:
      z_score_f2 = abs(sum_f2 - self.sum_stats_f2['mean']) / self.sum_stats_f2['std']
      score_f2 = max(0, 1 - z_score_f2 / 2)
    else:
      score_f2 = 0.5

    return (score_f1 + score_f2) / 2

  def _evaluate_uniqueness(self, field1: List[int], field2: List[int]) -> float:
    """Оценка уникальности комбинации"""
    if self.df_history.empty:
      return 1.0

    # Проверяем, не встречалась ли точно такая комбинация
    for _, row in self.df_history.head(200).iterrows():
      f1_hist = row.get('Числа_Поле1_list', [])
      f2_hist = row.get('Числа_Поле2_list', [])

      if (isinstance(f1_hist, list) and isinstance(f2_hist, list) and
          set(field1) == set(f1_hist) and set(field2) == set(f2_hist)):
        return 0.0  # Комбинация уже была

    # Проверяем схожесть с недавними
    max_similarity = 0.0
    for _, row in self.df_history.head(50).iterrows():
      f1_hist = set(row.get('Числа_Поле1_list', []))
      f2_hist = set(row.get('Числа_Поле2_list', []))

      if f1_hist and f2_hist:
        similarity = (len(set(field1) & f1_hist) + len(set(field2) & f2_hist)) / \
                     (self.field1_size + self.field2_size)
        max_similarity = max(max_similarity, similarity)

    # Чем меньше схожесть, тем лучше уникальность
    return 1.0 - max_similarity * 0.5

  def _evaluate_trend_alignment(self, field1: List[int], field2: List[int]) -> float:
    """Оценка соответствия текущим трендам"""
    try:
      # Используем существующий анализатор трендов
      from backend.app.core.trend_analyzer import GLOBAL_TREND_ANALYZER

      trends = GLOBAL_TREND_ANALYZER.analyze_current_trends(self.df_history)

      score = 0.0
      count = 0

      # Проверяем соответствие горячим числам с ускорением
      if 'field1' in trends:
        hot_accel = set(trends['field1'].hot_acceleration)
        if hot_accel:
          overlap = len(set(field1) & hot_accel)
          score += overlap / len(hot_accel)
          count += 1

      if 'field2' in trends:
        hot_accel = set(trends['field2'].hot_acceleration)
        if hot_accel:
          overlap = len(set(field2) & hot_accel)
          score += overlap / len(hot_accel)
          count += 1

      return score / max(1, count) if count > 0 else 0.5

    except Exception as e:
      logger.warning(f"Ошибка оценки трендов: {e}")
      return 0.5

  def batch_evaluate(self, combinations: List[Tuple[List[int], List[int]]]) -> List[float]:
    """
    Пакетная оценка множества комбинаций

    Args:
        combinations: Список кортежей (field1, field2)

    Returns:
        Список fitness значений
    """
    results = []
    for field1, field2 in combinations:
      results.append(self.evaluate(field1, field2))

    logger.info(f"📊 Пакетная оценка {len(combinations)} комбинаций завершена. "
                f"Cache hits: {self._cache_hits}, misses: {self._cache_misses}")

    return results

  def update_weights(self, new_weights: Dict[str, float]):
    """Обновление весов компонентов fitness"""
    for key in new_weights:
      if key in self.weights:
        self.weights[key] = new_weights[key]

    # Нормализация весов
    total = sum(self.weights.values())
    if total > 0:
      for key in self.weights:
        self.weights[key] /= total

    # Очищаем кэш после изменения весов
    self._fitness_cache.clear()
    logger.info(f"📊 Веса fitness обновлены: {self.weights}")

  def get_statistics(self) -> Dict:
    """Получение статистики оценщика"""
    cache_hit_rate = self._cache_hits / max(1, self._cache_hits + self._cache_misses)

    return {
      'total_evaluations': self._cache_hits + self._cache_misses,
      'cache_hits': self._cache_hits,
      'cache_misses': self._cache_misses,
      'cache_hit_rate': cache_hit_rate,
      'cache_size': len(self._fitness_cache),
      'hot_numbers_f1': self.hot_numbers_f1[:5],
      'cold_numbers_f1': self.cold_numbers_f1[:5],
      'hot_numbers_f2': self.hot_numbers_f2[:5],
      'cold_numbers_f2': self.cold_numbers_f2[:5],
      'weights': self.weights.copy()
    }

  def clear_cache(self):
    """Очистка кэша"""
    self._fitness_cache.clear()
    self._cache_hits = 0
    self._cache_misses = 0
    logger.info("🧹 Кэш fitness очищен")


class MultiObjectiveFitness(FitnessEvaluator):
  """
  Многокритериальная fitness функция с Парето-оптимизацией
  Позволяет оптимизировать несколько конфликтующих целей
  """

  def __init__(self, df_history: pd.DataFrame, lottery_config: Dict):
    super().__init__(df_history, lottery_config)

    # Отдельные цели для оптимизации
    self.objectives = {
      'maximize_hot': self._objective_maximize_hot,
      'balance_distribution': self._objective_balance,
      'historical_similarity': self._objective_historical,
      'uniqueness': self._objective_uniqueness
    }

  def evaluate_multi_objective(self, field1: List[int], field2: List[int]) -> Dict[str, float]:
    """
    Оценка по множественным целям

    Returns:
        Словарь с оценками по каждой цели
    """
    scores = {}
    for name, func in self.objectives.items():
      scores[name] = func(field1, field2)
    return scores

  def _objective_maximize_hot(self, field1: List[int], field2: List[int]) -> float:
    """Цель: максимизировать горячие числа"""
    hot_count = 0
    hot_count += len(set(field1) & set(self.hot_numbers_f1))
    hot_count += len(set(field2) & set(self.hot_numbers_f2))

    max_possible = len(self.hot_numbers_f1) + len(self.hot_numbers_f2)
    return hot_count / max(1, max_possible)

  def _objective_balance(self, field1: List[int], field2: List[int]) -> float:
    """Цель: сбалансированное распределение"""
    return self._evaluate_balance(field1, field2)

  def _objective_historical(self, field1: List[int], field2: List[int]) -> float:
    """Цель: схожесть с историческими паттернами"""
    return self._evaluate_historical_matches(field1, field2)

  def _objective_uniqueness(self, field1: List[int], field2: List[int]) -> float:
    """Цель: уникальность комбинации"""
    return self._evaluate_uniqueness(field1, field2)

  def is_pareto_optimal(self, scores: Dict[str, float],
                        population_scores: List[Dict[str, float]]) -> bool:
    """
    Проверка Парето-оптимальности

    Args:
        scores: Оценки текущей особи
        population_scores: Оценки всей популяции

    Returns:
        True если особь Парето-оптимальна
    """
    for other_scores in population_scores:
      # Проверяем доминирование
      dominates = True
      for obj in scores:
        if scores[obj] > other_scores[obj]:
          dominates = False
          break

      # Если другая особь доминирует - текущая не оптимальна
      if dominates and any(other_scores[obj] > scores[obj] for obj in scores):
        return False

    return True