# core/pattern_analyzer.py
"""
Модуль для продвинутого анализа паттернов в лотерейных данных.
Интегрируется с существующими модулями data_manager и utils.
"""

import numpy as np
from collections import Counter
import itertools

from backend.app.core.utils import format_numbers


class AdvancedPatternAnalyzer:
  """Класс для глубокого анализа паттернов в истории тиражей"""

  def __init__(self):
    self.analysis_cache = {}

  def analyze_hot_cold_numbers(self, df_history, window_sizes=[10, 20, 50], top_n=5):
    """
    Анализирует горячие и холодные числа в разных временных окнах.

    Args:
        df_history: DataFrame с историей (уже есть Числа_Поле1_list, Числа_Поле2_list)
        window_sizes: Размеры окон для анализа
        top_n: Количество топ горячих/холодных чисел

    Returns:
        dict: Словарь с анализом для каждого окна и поля
    """
    if df_history.empty:
      return {}

    results = {}

    for window in window_sizes:
      window_df = df_history.head(window) if len(df_history) >= window else df_history

      # Анализ для каждого поля
      for field_num, field_col in enumerate(['Числа_Поле1_list', 'Числа_Поле2_list'], 1):
        all_numbers = []
        for nums_list in window_df[field_col].dropna():
          if isinstance(nums_list, list):
            all_numbers.extend(nums_list)

        if not all_numbers:
          continue

        # Подсчет частот
        freq_counter = Counter(all_numbers)
        total_draws = len(window_df)

        # Вычисляем процент появления
        freq_percentages = {
          num: (count / total_draws) * 100
          for num, count in freq_counter.items()
        }

        # Ожидаемая частота (равномерное распределение)
        expected_freq = (4 / 20) * 100  # 4 числа из 20 = 20%

        # Горячие числа (выше ожидаемой частоты)
        hot_numbers = sorted(
          [(num, pct) for num, pct in freq_percentages.items() if pct > expected_freq],
          key=lambda x: x[1], reverse=True
        )[:top_n]

        # Холодные числа (все числа от 1 до 20)
        all_possible_numbers = set(range(1, 21))
        appeared_numbers = set(freq_counter.keys())
        never_appeared = all_possible_numbers - appeared_numbers

        cold_numbers = []
        # Сначала добавляем числа, которые не выпадали
        for num in never_appeared:
          cold_numbers.append((num, 0.0))

        # Затем числа с низкой частотой
        low_freq = sorted(
          [(num, pct) for num, pct in freq_percentages.items() if pct < expected_freq],
          key=lambda x: x[1]
        )
        cold_numbers.extend(low_freq)
        cold_numbers = cold_numbers[:top_n]

        # Статистика по позициям для горячих чисел
        position_stats = self._analyze_positions(window_df, field_col, [n[0] for n in hot_numbers])

        results[f'field{field_num}_window{window}'] = {
          'window_size': window,
          'field': field_num,
          'hot_numbers': hot_numbers,
          'cold_numbers': cold_numbers,
          'expected_frequency': expected_freq,
          'position_preferences': position_stats,
          'total_draws_analyzed': total_draws
        }

    return results

  def _analyze_positions(self, df, field_col, numbers):
    """Анализирует предпочтительные позиции для заданных чисел"""
    position_stats = {}

    for num in numbers:
      positions = []
      for nums_list in df[field_col].dropna():
        if isinstance(nums_list, list) and num in nums_list:
          positions.append(nums_list.index(num))

      if positions:
        position_counter = Counter(positions)
        total = sum(position_counter.values())
        position_stats[num] = {
          pos: (count / total) * 100
          for pos, count in position_counter.items()
        }

    return position_stats

  def find_number_correlations(self, df_history, min_support=0.02):  # ← СНИЖЕН С 0.1 ДО 0.02 (2%)
    """
    Находит числа, которые часто выпадают вместе.

    Args:
        df_history: DataFrame с историей
        min_support: Минимальная поддержка (доля тиражей) - СНИЖЕНО до 2%

    Returns:
        dict: Корреляции для каждого поля
    """
    results = {}

    for field_num, field_col in enumerate(['Числа_Поле1_list', 'Числа_Поле2_list'], 1):
      # Собираем все комбинации пар
      pair_counter = Counter()
      total_draws = 0

      print(f"🔍 Анализируем корреляции для поля {field_num}...")

      for nums_list in df_history[field_col].dropna():
        if isinstance(nums_list, list) and len(nums_list) >= 2:
          total_draws += 1
          # Все пары из чисел
          for pair in itertools.combinations(sorted(nums_list), 2):
            pair_counter[pair] += 1

      print(f"📊 Поле {field_num}: обработано {total_draws} тиражей, найдено {len(pair_counter)} уникальных пар")

      if total_draws == 0:
        print(f"⚠️ Поле {field_num}: нет данных для анализа")
        continue

      # ИСПРАВЛЕНИЕ 1: Адаптивный порог на основе количества данных
      if total_draws < 20:
        # Для малых выборок - берем пары встречающиеся хотя бы 1 раз
        adaptive_min_support = 1 / total_draws
      elif total_draws < 50:
        # Для средних выборок - 2% или минимум 1 раз
        adaptive_min_support = max(0.02, 1 / total_draws)
      else:
        # Для больших выборок - используем заданный min_support, но не менее 1%
        adaptive_min_support = max(min_support, 0.01)

      min_count = max(1, int(total_draws * adaptive_min_support))

      print(f"🎯 Поле {field_num}: порог = {adaptive_min_support:.3f} ({min_count} встреч)")

      # ИСПРАВЛЕНИЕ 2: Более умная фильтрация
      frequent_pairs = []
      for pair, count in pair_counter.items():
        frequency_percent = (count / total_draws) * 100
        if count >= min_count:
          frequent_pairs.append((pair, count, frequency_percent))

      # Сортируем по частоте
      frequent_pairs.sort(key=lambda x: x[1], reverse=True)

      # ИСПРАВЛЕНИЕ 3: Берем больше пар, но ограничиваем разумным числом
      max_pairs = min(50, len(frequent_pairs))  # Было 20, стало 50
      frequent_pairs = frequent_pairs[:max_pairs]

      print(f"✅ Поле {field_num}: найдено {len(frequent_pairs)} частых пар")
      if frequent_pairs:
        top_pair = frequent_pairs[0]
        print(f"🔥 Топ пара поля {field_num}: {top_pair[0]} ({top_pair[2]:.1f}%, {top_pair[1]}x)")

      # Также находим "антикорреляции" - числа, которые редко встречаются вместе
      all_pairs = set(itertools.combinations(range(1, 21), 2))
      appeared_pairs = set(pair_counter.keys())
      never_together = list(all_pairs - appeared_pairs)[:10]  # Топ-10

      results[f'field{field_num}'] = {
        'frequent_pairs': frequent_pairs,
        'never_together': never_together,
        'total_draws': total_draws,
        'total_unique_pairs': len(pair_counter),
        'min_count_used': min_count,
        'adaptive_threshold': adaptive_min_support
      }

    return results

  def analyze_draw_cycles(self, df_history, numbers_to_analyze=None):
    """
    Анализирует циклы выпадения чисел (через сколько тиражей повторяются).

    Args:
        df_history: DataFrame с историей
        numbers_to_analyze: Список чисел или None для всех

    Returns:
        dict: Статистика циклов
    """
    if numbers_to_analyze is None:
      numbers_to_analyze = list(range(1, 21))

    cycles_data = {}

    for field_num, field_col in enumerate(['Числа_Поле1_list', 'Числа_Поле2_list'], 1):
      field_cycles = {}

      for number in numbers_to_analyze:
        appearances = []

        # Находим все позиции (индексы), где появляется число
        for idx, nums_list in enumerate(df_history[field_col]):
          if isinstance(nums_list, list) and number in nums_list:
            appearances.append(idx)

        if len(appearances) >= 2:
          # Вычисляем интервалы между появлениями
          intervals = []
          for i in range(1, len(appearances)):
            interval = appearances[i] - appearances[i - 1]
            intervals.append(interval)

          if intervals:
            field_cycles[number] = {
              'appearances': len(appearances),
              'avg_cycle': np.mean(intervals),
              'min_cycle': min(intervals),
              'max_cycle': max(intervals),
              'std_cycle': np.std(intervals) if len(intervals) > 1 else 0,
              'last_seen': appearances[0],  # Сколько тиражей назад
              'overdue': appearances[0] > np.mean(intervals) if intervals else False
            }

      cycles_data[f'field{field_num}'] = field_cycles

    return cycles_data

  def detect_anomalies(self, df_history, zscore_threshold=2.5):
    """
    Обнаруживает статистические аномалии в тиражах.

    Args:
        df_history: DataFrame с историей
        zscore_threshold: Порог Z-score для определения аномалии

    Returns:
        dict: Информация об аномалиях
    """
    anomalies = {
      'unusual_sums': [],
      'unusual_spreads': [],
      'unusual_patterns': [],
      'consecutive_numbers': [],
      'all_even_odd': []
    }

    for idx, row in df_history.iterrows():
      draw_num = row.get('Тираж', idx)

      for field_num, field_col in enumerate(['Числа_Поле1_list', 'Числа_Поле2_list'], 1):
        nums = row[field_col]
        if not isinstance(nums, list) or len(nums) != 4:
          continue

        # Анализ суммы
        sum_nums = sum(nums)
        # Теоретические границы: мин 10 (1+2+3+4), макс 74 (17+18+19+20)
        # Среднее ожидаемое: 42
        if sum_nums < 20 or sum_nums > 64:  # Примерно 2.5 стандартных отклонения
          anomalies['unusual_sums'].append({
            'draw': draw_num,
            'field': field_num,
            'sum': sum_nums,
            'numbers': format_numbers(nums)
          })

        # Анализ размаха
        spread = max(nums) - min(nums)
        if spread < 5 or spread > 18:  # Очень узкий или широкий диапазон
          anomalies['unusual_spreads'].append({
            'draw': draw_num,
            'field': field_num,
            'spread': spread,
            'numbers': format_numbers(nums)
          })

        # Проверка на последовательные числа
        sorted_nums = sorted(nums)
        consecutive_count = 1
        for i in range(1, len(sorted_nums)):
          if sorted_nums[i] == sorted_nums[i - 1] + 1:
            consecutive_count += 1
          else:
            if consecutive_count >= 3:
              break
            consecutive_count = 1

        if consecutive_count >= 3:
          anomalies['consecutive_numbers'].append({
            'draw': draw_num,
            'field': field_num,
            'consecutive': consecutive_count,
            'numbers': format_numbers(nums)
          })

        # Проверка на все четные или все нечетные
        even_count = sum(1 for n in nums if n % 2 == 0)
        if even_count == 0 or even_count == 4:
          anomalies['all_even_odd'].append({
            'draw': draw_num,
            'field': field_num,
            'type': 'all_even' if even_count == 4 else 'all_odd',
            'numbers': format_numbers(nums)
          })

    # Подсчет частоты аномалий
    total_draws = len(df_history)
    anomaly_stats = {
      key: {
        'count': len(values),
        'percentage': (len(values) / total_draws) * 100 if total_draws > 0 else 0,
        'examples': values[:5]  # Первые 5 примеров
      }
      for key, values in anomalies.items()
    }

    return anomaly_stats

  def get_smart_filters(self, df_history, risk_level='medium'):
    """
    Генерирует умные фильтры для combination_generator на основе анализа.

    Args:
        df_history: DataFrame с историей
        risk_level: 'conservative', 'medium', 'aggressive'

    Returns:
        dict: Фильтры для генерации комбинаций
    """
    # Анализируем последние 50 тиражей для определения текущих трендов
    recent_df = df_history.head(50)

    filters = {}

    # Анализ сумм
    for field_num, field_col in enumerate(['Числа_Поле1_list', 'Числа_Поле2_list'], 1):
      sums = []
      for nums in recent_df[field_col].dropna():
        if isinstance(nums, list):
          sums.append(sum(nums))

      if sums:
        mean_sum = np.mean(sums)
        std_sum = np.std(sums)

        if risk_level == 'conservative':
          # Узкий диапазон около среднего
          filters[f'sum_f{field_num}_min'] = int(mean_sum - std_sum)
          filters[f'sum_f{field_num}_max'] = int(mean_sum + std_sum)
        elif risk_level == 'medium':
          # Средний диапазон
          filters[f'sum_f{field_num}_min'] = int(mean_sum - 1.5 * std_sum)
          filters[f'sum_f{field_num}_max'] = int(mean_sum + 1.5 * std_sum)
        else:  # aggressive
          # Широкий диапазон
          filters[f'sum_f{field_num}_min'] = max(10, int(mean_sum - 2 * std_sum))
          filters[f'sum_f{field_num}_max'] = min(74, int(mean_sum + 2 * std_sum))

    # Получаем горячие и холодные числа
    hot_cold = self.analyze_hot_cold_numbers(df_history, window_sizes=[20], top_n=3)

    # Добавляем рекомендации по горячим/холодным числам
    for field_data in hot_cold.values():
      field_num = field_data['field']
      if risk_level == 'conservative':
        # Включаем хотя бы одно горячее число
        if field_data['hot_numbers']:
          filters[f'include_hot_f{field_num}'] = [n[0] for n in field_data['hot_numbers'][:1]]
      elif risk_level == 'aggressive':
        # Включаем холодные числа (они "должны" выпасть)
        if field_data['cold_numbers']:
          filters[f'include_cold_f{field_num}'] = [n[0] for n in field_data['cold_numbers'][:2]]

    return filters


# Глобальный экземпляр анализатора
GLOBAL_PATTERN_ANALYZER = AdvancedPatternAnalyzer()