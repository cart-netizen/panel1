import random

import numpy as np
import pandas as pd
from collections import Counter
from backend.app.core.ai_model import GLOBAL_RF_MODEL  # Using the global RF model instance
from backend.app.core.pattern_analyzer import GLOBAL_PATTERN_ANALYZER
from backend.app.core.data_manager import get_current_config


def generate_random_combination():
  """
  Генерирует случайную комбинацию на основе ТЕКУЩЕЙ конфигурации лотереи.
  """
  config = get_current_config()
  field1_size = config['field1_size']
  field2_size = config['field2_size']
  field1_max = config['field1_max']
  field2_max = config['field2_max']

  field1 = sorted(random.sample(range(1, field1_max + 1), field1_size))
  field2 = sorted(random.sample(range(1, field2_max + 1), field2_size))
  return field1, field2


def get_number_frequencies(df_history, field_column_name):
  """
    Calculates frequency of each number in a specified field from historical data.

    Args:
        df_history (pd.DataFrame): DataFrame with historical draws.
        field_column_name (str): Name of the column containing lists of numbers (e.g., 'Числа_Поле1_list').

    Returns:
        Counter: A Counter object with number frequencies.
    """
  frequency_counter = Counter()
  if not df_history.empty and field_column_name in df_history.columns:
    for numbers_list in df_history[field_column_name].dropna():
      if isinstance(numbers_list, list):
        frequency_counter.update(numbers_list)
  return frequency_counter


def generate_filtered_combination(df_history, filters=None):
  """
    Generates a random combination that satisfies a set of user-defined filters.
    This is a basic implementation; complex filter interactions can be challenging.

    Args:
        df_history (pd.DataFrame): Historical data, potentially for frequency-based filters.
        filters (dict, optional): A dictionary of filters. Example:
            {
                'sum_f1_min': 10, 'sum_f1_max': 70,
                'sum_f2_min': 10, 'sum_f2_max': 70,
                'parity_f1': {'even': 2, 'odd': 2}, # Exact count of even/odd in field 1
                'parity_f2': {'any': True}, # No parity filter for field 2
                'include_f1': [5, 10], # Must include these numbers in field 1
                'exclude_f1': [1, 20], # Must not include these numbers in field 1
                # Similar include/exclude for f2
                # 'hot_numbers_f1': 2, # Include N hottest numbers
                # 'cold_numbers_f1': 1 # Include N coldest numbers
            }

    Returns:
        tuple: (field1, field2) satisfying filters, or (None, None) if no combination
               found after max_attempts.
    """
  if filters is None:
    filters = {}
  max_attempts = 1000
  for attempt in range(max_attempts):
    f1, f2 = generate_random_combination()
    valid_f1 = True
    if 'sum_f1_min' in filters and sum(f1) < filters['sum_f1_min']: valid_f1 = False
    if valid_f1 and 'sum_f1_max' in filters and sum(f1) > filters['sum_f1_max']: valid_f1 = False
    if valid_f1 and 'parity_f1' in filters and not filters['parity_f1'].get('any', False):
      even_count = sum(1 for n in f1 if n % 2 == 0)
      odd_count = 4 - even_count
      if 'even' in filters['parity_f1'] and even_count != filters['parity_f1']['even']: valid_f1 = False
      if 'odd' in filters['parity_f1'] and odd_count != filters['parity_f1']['odd']: valid_f1 = False
    if valid_f1 and 'include_f1' in filters:
      if not all(num in f1 for num in filters['include_f1']): valid_f1 = False
    if valid_f1 and 'exclude_f1' in filters:
      if any(num in f1 for num in filters['exclude_f1']): valid_f1 = False
    valid_f2 = True
    if 'sum_f2_min' in filters and sum(f2) < filters['sum_f2_min']: valid_f2 = False
    if valid_f2 and 'sum_f2_max' in filters and sum(f2) > filters['sum_f2_max']: valid_f2 = False
    if valid_f2 and 'parity_f2' in filters and not filters['parity_f2'].get('any', False):
      even_count = sum(1 for n in f2 if n % 2 == 0)
      odd_count = 4 - even_count
      if 'even' in filters['parity_f2'] and even_count != filters['parity_f2']['even']: valid_f2 = False
      if 'odd' in filters['parity_f2'] and odd_count != filters['parity_f2']['odd']: valid_f2 = False
    if valid_f2 and 'include_f2' in filters:
      if not all(num in f2 for num in filters['include_f2']): valid_f2 = False
    if valid_f2 and 'exclude_f2' in filters:
      if any(num in f2 for num in filters['exclude_f2']): valid_f2 = False
    if valid_f1 and valid_f2:
      return f1, f2
  return None, None


def generate_ml_based_combinations(df_history, num_combinations=5):
  """
    Generates lottery combinations using the trained ML model and random generation.
    Aims to provide one "best guess" from the AI and supplement with random ones.

    Args:
        df_history (pd.DataFrame): DataFrame with historical draws, needed for training
                                   the model if not already trained, and for getting the last draw.
        num_combinations (int): Total number of combinations to generate.

    Returns:
        list: A list of tuples, where each tuple is (field1_list, field2_list, type_str).
              Example: [([1,2,3,4], [5,6,7,8], "AI Prediction"), ([...], [...], "Random")]
    """
  results = []
  config = get_current_config()
  if df_history.empty:
    print("ML Generator (simple): История пуста. Генерация случайных комбинаций.")
    for _ in range(num_combinations):
      f1, f2 = generate_random_combination()
      results.append((f1, f2, "Случайная (Нет Истории)"))
    return results

  if not GLOBAL_RF_MODEL.is_trained:
    print("ML Generator (simple): Модель не обучена. Попытка обучения...")
    GLOBAL_RF_MODEL.train(df_history)
    if not GLOBAL_RF_MODEL.is_trained:
      print("ML Generator (simple): Обучение модели не удалось. Генерация случайных комбинаций.")
      for _ in range(num_combinations):
        f1, f2 = generate_random_combination()
        results.append((f1, f2, "Случайная (Ошибка AI)"))
      return results
    else:
      print("ML Generator (simple): Модель успешно обучена.")

  last_draw = df_history.iloc[0]
  last_f1 = last_draw.get('Числа_Поле1_list')
  last_f2 = last_draw.get('Числа_Поле2_list')

  if not (isinstance(last_f1, list) and len(last_f1) == 4 and
          isinstance(last_f2, list) and len(last_f2) == 4):
    print("ML Generator (simple): Некорректные данные последнего тиража. Генерация случайных.")
    for _ in range(num_combinations):
      f1, f2 = generate_random_combination()
      results.append((f1, f2, "Случайная (Плохой Посл. Тираж)"))
    return results

  pred_f1, pred_f2 = GLOBAL_RF_MODEL.predict_next_combination(last_f1, last_f2)
  if pred_f1 and pred_f2 and len(pred_f1) == 4 and len(pred_f2) == 4:
    results.append((pred_f1, pred_f2, "AI Предсказание"))
  else:
    print("ML Generator (simple): AI модель не дала валидного предсказания. Добавление случайной комбинации.")
    f1_rand_ai, f2_rand_ai = generate_random_combination()
    results.append((f1_rand_ai, f2_rand_ai, "Случайная (Ошибка Предсказания AI)"))

  while len(results) < num_combinations:
    f1_rand, f2_rand = generate_random_combination()
    is_duplicate = False
    if results and pred_f1 and pred_f2:
      if sorted(f1_rand) == sorted(pred_f1) and sorted(f2_rand) == sorted(pred_f2):
        is_duplicate = True
    if not is_duplicate:
      results.append((f1_rand, f2_rand, "Случайная"))
  return results[:num_combinations]


def generate_rf_ranked_combinations(df_history, num_to_generate, num_candidates_to_score=500):
  """
  Генерирует комбинации с использованием "умного" подхода + динамический анализ трендов:
  1. Анализирует текущие тренды и паттерны
  2. Генерирует `num_candidates_to_score` умных комбинаций на основе трендов
  3. Оценивает каждую из них с помощью RF-модели (`score_combination`)
  4. Ранжирует комбинации по оценке с учетом трендов
  5. Возвращает топ `num_to_generate` комбинаций

  Args:
      df_history (pd.DataFrame): DataFrame с историей тиражей.
      num_to_generate (int): Количество лучших комбинаций для возврата.
      num_candidates_to_score (int): Количество случайных комбинаций для генерации и оценки.

  Returns:
      list: Список кортежей (field1_list, field2_list, type_str_with_score).
  """
  import time
  from backend.app.core.data_cache import GLOBAL_DATA_CACHE
  from backend.app.core import data_manager
  from backend.app.core.rf_cache import GLOBAL_RF_CACHE

  results_with_scores = []

  if df_history.empty or len(df_history) < 2:
    print("RF Ranked Gen: Недостаточно данных. Генерация случайных.")
    return [(r1, r2, "Случайная (нет данных)") for r1, r2 in
            [generate_random_combination() for _ in range(num_to_generate)]]

  print("⚡ КЭШИРОВАННАЯ УЛЬТРА БЫСТРАЯ RF генерация с анализом трендов...")

  # Статистика кэша
  cache_stats = GLOBAL_RF_CACHE.get_stats()
  print(f"📊 RF кэш: {cache_stats['cache_size']} записей, hit rate: {cache_stats['hit_rate_percent']:.1f}%")

  # Обновляем кэш данных
  cached_df = GLOBAL_DATA_CACHE.get_cached_history(data_manager.CURRENT_LOTTERY)

  # НОВОЕ: Анализ текущих трендов
  print(f"🔍 Анализ текущих трендов...")
  trends_start = time.time()

  try:
    from backend.app.core.trend_analyzer import GLOBAL_TREND_ANALYZER, analyze_combination_with_trends
    current_trends = GLOBAL_TREND_ANALYZER.analyze_current_trends(df_history)
    trend_summary = GLOBAL_TREND_ANALYZER.get_trend_summary(current_trends)
    print(f"📊 Тренды ({time.time() - trends_start:.2f}с): {trend_summary}")
    use_trends = True
  except Exception as e:
    print(f"⚠️ Ошибка анализа трендов: {e}")
    current_trends = {}
    use_trends = False

  # Проверяем и обучаем RF модель
  if not GLOBAL_RF_MODEL.is_trained:
    print("🎓 RF модель требует обучения...")
    start_training = time.time()
    GLOBAL_RF_MODEL.train(df_history)
    training_time = time.time() - start_training

    if not GLOBAL_RF_MODEL.is_trained:
      print("❌ RF обучение не удалось.")
      return [(r1, r2, "Случайная (ошибка обучения)") for r1, r2 in
              [generate_random_combination() for _ in range(num_to_generate)]]
    else:
      print(f"✅ RF модель обучена за {training_time:.1f}с")
  else:
    print("✅ RF модель готова")

  # АДАПТИВНОЕ количество кандидатов на основе требуемого результата
  if num_to_generate <= 1:
    candidates_count = max(6, num_to_generate * 4)  # Увеличено для лучшего качества
  elif num_to_generate <= 3:
    candidates_count = max(10, num_to_generate * 3)
  elif num_to_generate <= 5:
    candidates_count = max(15, num_to_generate * 3)
  else:
    candidates_count = min(num_candidates_to_score, max(20, num_to_generate * 2))

  print(f"⚡ Генерация {candidates_count} кандидатов для {num_to_generate} итоговых...")

  start_time = time.time()
  max_time_seconds = 10.0  # Достаточно времени для оценки всех комбинаций

  try:
    from backend.app.core.parallel_rf import smart_combination_generator

    # НОВОЕ: Умная генерация кандидатов на основе трендов
    if use_trends and current_trends:
      print(f"🎯 Генерация с учетом трендов...")
      candidates = _generate_trend_aware_candidates(
        current_trends, candidates_count, num_to_generate
      )
    else:
      print(f"🔄 Обычная генерация кандидатов...")
      candidates = smart_combination_generator(candidates_count, avoid_duplicates=True)

    # Кэшированная обработка с RF оценкой
    print(f"⚡ Кэшированная обработка {len(candidates)} кандидатов")
    scored_combinations = []

    eval_start = time.time()
    cache_hits = 0

    for i, (f1, f2) in enumerate(candidates):
      if time.time() - start_time > max_time_seconds:
        print(f"⏰ Таймаут {max_time_seconds}с на {i}/{len(candidates)}")
        break

      # Проверяем кэш ПЕРЕД оценкой
      cached_score = GLOBAL_RF_CACHE.get_score(f1, f2)
      if cached_score is not None:
        cache_hits += 1
        rf_score = cached_score
      else:
        # RF оценка только если нет в кэше
        rf_score = GLOBAL_RF_MODEL.score_combination(sorted(f1), sorted(f2), cached_df)

      # НОВОЕ: Комбинированная оценка RF + тренды
      if use_trends and current_trends:
        trend_score, trend_desc = analyze_combination_with_trends(f1, f2, df_history)
        # Взвешенная комбинация: 70% RF, 30% тренды
        combined_score = rf_score * 0.7 + (trend_score * 100) * 0.3
        score_desc = f"RF+тренд"
      else:
        combined_score = rf_score
        score_desc = "RF"

      scored_combinations.append((f1, f2, combined_score, score_desc))

    eval_time = time.time() - eval_start
    rate = len(scored_combinations) / eval_time if eval_time > 0 else 0
    print(f"⚡ Кэшированная обработка: {len(scored_combinations)} за {eval_time:.1f}с (скорость: {rate:.1f}/с)")
    print(f"📊 Кэш хиты: {cache_hits}/{len(scored_combinations)} ({cache_hits / len(scored_combinations) * 100:.1f}%)")

    # Быстрая фильтрация валидных результатов
    results_with_scores = [
      {'f1': f1, 'f2': f2, 'score': score, 'desc': desc}
      for f1, f2, score, desc in scored_combinations
      if score > -float('inf')
    ]

    print(f"📊 Валидных: {len(results_with_scores)} из {len(scored_combinations)}")

  except Exception as e:
    print(f"❌ Ошибка кэшированной генерации: {e}")
    import traceback
    traceback.print_exc()

    # Супер быстрый fallback
    print("🔄 Fallback к минимальной генерации...")
    for i in range(min(3, num_to_generate)):
      if time.time() - start_time > max_time_seconds:
        break
      f1, f2 = generate_random_combination()
      score = GLOBAL_RF_MODEL.score_combination(sorted(f1), sorted(f2), cached_df)
      if score > -float('inf'):
        results_with_scores.append({'f1': f1, 'f2': f2, 'score': score, 'desc': 'fallback'})

  if not results_with_scores:
    print("❌ Нет результатов. Генерация случайных.")
    return [(r1, r2, "Случайная (нет результатов)") for r1, r2 in
            [generate_random_combination() for _ in range(num_to_generate)]]

  # Быстрая сортировка по комбинированной оценке
  ranked_results = sorted(results_with_scores, key=lambda x: x['score'], reverse=True)

  # Формирование результата с улучшенными описаниями
  final_combinations = []
  for i in range(min(num_to_generate, len(ranked_results))):
    res = ranked_results[i]
    score_display = f"{res['score']:.1f}"
    rank_suffix = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else f"#{i + 1}"

    # НОВОЕ: Улучшенное описание с трендами
    if use_trends and current_trends:
      trend_info = ""
      # Проверяем соответствие трендам
      field1_trends = current_trends['field1'] if 'field1' in current_trends else None
      field2_trends = current_trends['field2'] if 'field2' in current_trends else None

      if field1_trends:
        hot_match = len(set(res['f1']) & set(field1_trends.hot_acceleration))
        momentum_match = len(set(res['f1']) & set(field1_trends.momentum_numbers))
        if hot_match > 0 or momentum_match > 0:
          trend_info = f" 🔥H{hot_match}⚡M{momentum_match}"

      description = f"⚡{res['desc']} {rank_suffix}{trend_info} ({score_display})"
    else:
      description = f"⚡Cache {rank_suffix} ({score_display})"

    final_combinations.append((res['f1'], res['f2'], description))

  # Дополнение случайными при необходимости
  while len(final_combinations) < num_to_generate:
    f1_rand, f2_rand = generate_random_combination()
    final_combinations.append((f1_rand, f2_rand, "Случайная"))

  elapsed_total = time.time() - start_time
  efficiency = len(results_with_scores) / elapsed_total if elapsed_total > 0 else 0

  # НОВОЕ: Расширенная статистика
  trend_suffix = " с трендами" if use_trends else ""
  print(f"⚡ КЭШИРОВАННАЯ СКОРОСТЬ{trend_suffix}: {elapsed_total:.1f}с, эффективность: {efficiency:.1f}/с")

  if use_trends and current_trends:
    field1_strength = current_trends['field1'].trend_strength if 'field1' in current_trends else 0
    field2_strength = current_trends['field2'].trend_strength if 'field2' in current_trends else 0
    print(f"🎯 Качество трендов: Поле1 сила={field1_strength:.2f}, Поле2 сила={field2_strength:.2f}")

  return final_combinations

def _generate_trend_aware_candidates(trends, total_candidates, target_results):
    """
    Генерирует кандидатов с учетом текущих трендов

    Args:
        trends: Словарь с трендами от GLOBAL_TREND_ANALYZER
        total_candidates: Общее количество кандидатов
        target_results: Целевое количество результатов

    Returns:
        List[Tuple]: Список кандидатов (f1, f2)
    """
    candidates = []

    # Получаем тренды для полей
    field1_trends = trends['field1'] if 'field1' in trends else None
    field2_trends = trends['field2'] if 'field2' in trends else None

    # 40% кандидатов - на основе горячих чисел и импульса
    trend_candidates = min(total_candidates * 4 // 10, target_results * 3)

    for _ in range(trend_candidates):
      try:
        f1 = _generate_smart_field_combination(field1_trends, 1)
        f2 = _generate_smart_field_combination(field2_trends, 2)
        candidates.append((f1, f2))
      except Exception:
        # Fallback на случайную генерацию
        f1, f2 = generate_random_combination()
        candidates.append((f1, f2))

    # 30% кандидатов - смешанные
    mixed_candidates = min(total_candidates * 3 // 10, target_results * 2)

    for _ in range(mixed_candidates):
      try:
        # Одно поле - тренд, другое - случайное
        if random.choice([True, False]):
          f1 = _generate_smart_field_combination(field1_trends, 1)
          f2 = _generate_random_field(2)
        else:
          f1 = _generate_random_field(1)
          f2 = _generate_smart_field_combination(field2_trends, 2)
        candidates.append((f1, f2))
      except Exception:
        f1, f2 = generate_random_combination()
        candidates.append((f1, f2))

    # Остальные 30% - случайные
    remaining = total_candidates - len(candidates)
    for _ in range(remaining):
      f1, f2 = generate_random_combination()
      candidates.append((f1, f2))

    return candidates[:total_candidates]


def _generate_random_field(field_num):
  """Генерирует случайное поле"""
  from backend.app.core import data_manager
  config = data_manager.get_current_config()
  field_size = config[f'field{field_num}_size']
  max_num = config[f'field{field_num}_max']
  return sorted(random.sample(range(1, max_num + 1), field_size))


def _generate_smart_field_combination(field_trends, field_num):
  """
  Генерирует умную комбинацию для поля на основе трендов

  Args:
      field_trends: TrendMetrics для поля
      field_num: Номер поля (1 или 2)

  Returns:
      List[int]: Комбинация чисел для поля
  """
  from backend.app.core import data_manager
  config = data_manager.get_current_config()
  field_size = config[f'field{field_num}_size']
  max_num = config[f'field{field_num}_max']

  if not field_trends:
    # Fallback на случайную генерацию
    return sorted(random.sample(range(1, max_num + 1), field_size))

  result = []
  all_numbers = list(range(1, max_num + 1))

  # 50% - горячие числа
  hot_count = min(len(field_trends.hot_acceleration), field_size // 2)
  if hot_count > 0:
    result.extend(field_trends.hot_acceleration[:hot_count])

  # 25% - числа с импульсом
  momentum_count = min(len(field_trends.momentum_numbers), field_size // 4)
  if momentum_count > 0:
    momentum_to_add = [n for n in field_trends.momentum_numbers[:momentum_count] if n not in result]
    result.extend(momentum_to_add[:momentum_count])

  # Дополняем случайными
  remaining = field_size - len(result)
  if remaining > 0:
    available = [n for n in all_numbers if n not in result]
    if len(available) >= remaining:
      result.extend(random.sample(available, remaining))
    else:
      result.extend(available)
      # Если все еще не хватает, заполняем любыми доступными
      while len(result) < field_size:
        result.append(random.randint(1, max_num))

  return sorted(result[:field_size])


def _generate_random_field_combination(field_num):
  """Генерирует случайную комбинацию для поля"""
  from backend.app.core.data_manager import get_current_config
  import random

  config = get_current_config()
  field_size = config[f'field{field_num}_size']
  field_max = config[f'field{field_num}_max']

  return sorted(random.sample(range(1, field_max + 1), field_size))


def generate_pattern_based_combinations(df_history, num_to_generate, strategy='balanced'):
  """
  Генерирует комбинации на основе анализа паттернов.
  Использует горячие/холодные числа, корреляции и циклы.

  Args:
      df_history: DataFrame с историей
      num_to_generate: Количество комбинаций
      strategy: 'hot' (горячие), 'cold' (холодные), 'balanced' (сбалансированные),
               'correlated' (с учетом корреляций), 'overdue' (просроченные)

  Returns:
      list: Список кортежей (field1, field2, описание)
  """
  if df_history.empty:
    print("Pattern Generator: История пуста. Генерация случайных комбинаций.")
    return [(f1, f2, "Случайная (нет истории)") for f1, f2 in
            [generate_random_combination() for _ in range(num_to_generate)]]

  # --- ГЛАВНОЕ ИСПРАВЛЕНИЕ: ПОЛУЧАЕМ КОНФИГУРАЦИЮ ---
  config = get_current_config()
  f1_size = config['field1_size']
  f2_size = config['field2_size']
  f1_max = config['field1_max']
  f2_max = config['field2_max']

  results = []

  hot_cold = GLOBAL_PATTERN_ANALYZER.analyze_hot_cold_numbers(df_history, window_sizes=[20], top_n=10)
  correlations = GLOBAL_PATTERN_ANALYZER.find_number_correlations(df_history)
  cycles = GLOBAL_PATTERN_ANALYZER.analyze_draw_cycles(df_history)

  field1_data = hot_cold.get('field1_window20', {})
  field2_data = hot_cold.get('field2_window20', {})

  field1_hot = [n[0] for n in field1_data.get('hot_numbers', [])]
  field1_cold = [n[0] for n in field1_data.get('cold_numbers', [])]
  field2_hot = [n[0] for n in field2_data.get('hot_numbers', [])]
  field2_cold = [n[0] for n in field2_data.get('cold_numbers', [])]

  field1_pairs = correlations.get('field1', {}).get('frequent_pairs', [])
  field2_pairs = correlations.get('field2', {}).get('frequent_pairs', [])

  field1_cycles = cycles.get('field1', {})
  field2_cycles = cycles.get('field2', {})
  field1_overdue = [num for num, data in field1_cycles.items() if data.get('overdue', False)]
  field2_overdue = [num for num, data in field2_cycles.items() if data.get('overdue', False)]

  all_numbers_f1 = list(range(1, f1_max + 1))
  all_numbers_f2 = list(range(1, f2_max + 1))

  for i in range(num_to_generate):
    # --- ИСПОЛЬЗУЕМ ДИНАМИЧЕСКИЕ РАЗМЕРЫ ПОЛЕЙ ВМЕСТО '4' ---
    if strategy == 'hot':
      f1 = _generate_with_preference(field1_hot, all_numbers_f1, f1_size, min_preferred=2)
      f2 = _generate_with_preference(field2_hot, all_numbers_f2, f2_size, min_preferred=1 if f2_size < 3 else 2)
      desc = "Горячие числа"
    elif strategy == 'cold':
      f1 = _generate_with_preference(field1_cold, all_numbers_f1, f1_size, min_preferred=2)
      f2 = _generate_with_preference(field2_cold, all_numbers_f2, f2_size, min_preferred=1 if f2_size < 3 else 2)
      desc = "Холодные числа"
    elif strategy == 'balanced':
      f1 = _generate_balanced(field1_hot, field1_cold, all_numbers_f1, f1_size)
      f2 = _generate_balanced(field2_hot, field2_cold, all_numbers_f2, f2_size)
      desc = "Сбалансированная (горячие+холодные)"
    elif strategy == 'correlated':
      f1 = _generate_with_correlations(field1_pairs, all_numbers_f1, f1_size)
      f2 = _generate_with_correlations(field2_pairs, all_numbers_f2, f2_size)
      desc = "Коррелированные пары"
    elif strategy == 'overdue':
      f1 = _generate_with_preference(field1_overdue, all_numbers_f1, f1_size, min_preferred=1)
      f2 = _generate_with_preference(field2_overdue, all_numbers_f2, f2_size, min_preferred=1)
      desc = "Просроченные числа"
    else:
      f1, f2 = generate_random_combination()
      desc = "Случайная"

    results.append((sorted(f1), sorted(f2), desc))

  return results


def _generate_with_preference(preferred_numbers, all_numbers, count, min_preferred=1):
  """Генерирует комбинацию с предпочтением определенных чисел"""
  result = []
  available = list(all_numbers)

  if not preferred_numbers:
    # Если нет предпочитаемых чисел, просто берем случайные
    return random.sample(available, count)

  preferred_available = [n for n in preferred_numbers if n in available]
  num_to_take = min(min_preferred, len(preferred_available), count)

  if preferred_available and num_to_take > 0:
    selected = random.sample(preferred_available, num_to_take)
    result.extend(selected)
    for n in selected:
      available.remove(n)

  remaining = count - len(result)
  if remaining > 0:
    if not available:  # На случай если preferred_numbers содержали все числа
      # Восстановим доступные и удалим уже выбранные
      available = list(all_numbers)
      available = [n for n in available if n not in result]

    # Убедимся, что оставшихся достаточно
    if len(available) < remaining:
      # Если не хватает, дополняем изначальным списком (минус уже взятые)
      available_fallback = [n for n in all_numbers if n not in result]
      result.extend(random.sample(available_fallback, remaining))
    else:
      result.extend(random.sample(available, remaining))

  return result[:count]


def _generate_balanced(hot_numbers, cold_numbers, all_numbers, count):
  """Генерирует сбалансированную комбинацию."""
  result = []
  available = list(all_numbers)

  # 1-2 горячих числа
  hot_available = [n for n in hot_numbers if n in available]
  if hot_available and len(result) < count:
    num_hot = random.randint(1, min(2, len(hot_available), count - len(result)))
    selected_hot = random.sample(hot_available, num_hot)
    result.extend(selected_hot)
    for n in selected_hot:
      available.remove(n)

  # 1-2 холодных числа
  cold_available = [n for n in cold_numbers if n in available]
  if cold_available and len(result) < count:
    num_cold = random.randint(1, min(2, len(cold_available), count - len(result)))
    selected_cold = random.sample(cold_available, num_cold)
    result.extend(selected_cold)
    for n in selected_cold:
      available.remove(n)

  # Дополняем нейтральными числами
  remaining = count - len(result)
  if remaining > 0 and available:
    result.extend(random.sample(available, remaining))

  # Если после всех шагов не набралось нужное количество
  while len(result) < count:
    fallback_available = [n for n in all_numbers if n not in result]
    if not fallback_available: break
    result.append(random.choice(fallback_available))

  return result[:count]


def _generate_with_correlations(frequent_pairs, all_numbers, count):
  """Генерирует комбинацию используя частые пары."""
  result = []
  available = list(all_numbers)

  if frequent_pairs:
    # Выбираем 1-2 частые пары
    num_pairs_to_try = random.randint(1, min(2, len(frequent_pairs)))
    selected_pairs = random.sample(frequent_pairs[:10], num_pairs_to_try)

    for pair_data in selected_pairs:
      pair = pair_data[0]
      if len(result) + 2 <= count:
        if pair[0] in available and pair[1] in available:
          result.extend(pair)
          available.remove(pair[0])
          available.remove(pair[1])

  # Дополняем случайными
  remaining = count - len(result)
  if remaining > 0 and available:
    if len(available) >= remaining:
      result.extend(random.sample(available, remaining))
    else:  # Если доступных не хватает, берем что есть и дополняем
      result.extend(available)
      needed = count - len(result)
      fallback_available = [n for n in all_numbers if n not in result]
      result.extend(random.sample(fallback_available, needed))

  return result[:count]


def generate_multi_strategy_combinations(df_history, num_per_strategy=10):
  """
  Генерирует оптимальный набор комбинаций используя все стратегии.

  Args:
      df_history: DataFrame с историей
      num_per_strategy: Количество комбинаций на каждую стратегию

  Returns:
      list: Оптимизированный список комбинаций
  """
  all_combinations = []

  # 1. RF-ранжированные (лучшие по ML)
  rf_combos = generate_rf_ranked_combinations(df_history, num_per_strategy, num_candidates_to_score=500)
  all_combinations.extend(rf_combos)

  # 2. Паттерн-based стратегии
  strategies = ['hot', 'cold', 'balanced', 'correlated', 'overdue']
  for strategy in strategies:
    pattern_combos = generate_pattern_based_combinations(
      df_history,
      num_per_strategy // len(strategies),
      strategy
    )
    all_combinations.extend(pattern_combos)

  # 3. Удаляем дубликаты (если комбинации совпадают)
  unique_combinations = []
  seen = set()

  for f1, f2, desc in all_combinations:
    combo_key = (tuple(sorted(f1)), tuple(sorted(f2)))
    if combo_key not in seen:
      seen.add(combo_key)
      unique_combinations.append((f1, f2, desc))

  # 4. Финальная оптимизация: оцениваем все комбинации через RF
  if GLOBAL_RF_MODEL.is_trained and not df_history.empty:
    scored_combos = []
    for f1, f2, desc in unique_combinations:
      score = GLOBAL_RF_MODEL.score_combination(sorted(f1), sorted(f2), df_history)
      scored_combos.append((f1, f2, desc, score))

    # Сортируем по скору
    scored_combos.sort(key=lambda x: x[3], reverse=True)

    # Возвращаем топ-20 с обновленными описаниями
    final_combos = []
    for i, (f1, f2, desc, score) in enumerate(scored_combos[:20]):
      new_desc = f"#{i + 1} {desc} (скор: {score:.2f})"
      final_combos.append((f1, f2, new_desc))

    return final_combos

  # if GLOBAL_RF_MODEL.is_trained and not df_history.empty:
  #   last_draw = df_history.iloc[0]
  #   last_f1 = last_draw.get('Числа_Поле1_list')
  #   last_f2 = last_draw.get('Числа_Поле2_list')
  #
  #   if isinstance(last_f1, list) and len(last_f1) == 4 and isinstance(last_f2, list) and len(last_f2) == 4:
  #     scoring_features = np.array(sorted(last_f1) + sorted(last_f2)).reshape(1, -1)
  #
  #     scored_combos = []
  #     for f1, f2, desc in unique_combinations:
  #       score = GLOBAL_RF_MODEL.score_combination(sorted(f1), sorted(f2), scoring_features)
  #       scored_combos.append((f1, f2, desc, score))
  #
  #     # Сортируем по скору
  #     scored_combos.sort(key=lambda x: x[3], reverse=True)
  #
  #     # Возвращаем топ-20 с обновленными описаниями
  #     final_combos = []
  #     for i, (f1, f2, desc, score) in enumerate(scored_combos[:20]):
  #       new_desc = f"#{i + 1} {desc} (скор: {score:.2f})"
  #       final_combos.append((f1, f2, new_desc))
  #
  #     return final_combos

  # Если RF не готов, возвращаем первые 20
  return unique_combinations[:20]

def record_rf_performance(rf_score: float, combination_count: int, lottery_type: str):
    """Записывает производительность RF модели"""
    try:
      from backend.app.core.database import get_db
      from backend.app.api.dashboard import DashboardService

      db = next(get_db())
      dashboard_service = DashboardService(db)

      dashboard_service.update_model_statistics(
        lottery_type=lottery_type,
        model_type='rf',
        accuracy=75.0,  # Можно вычислять динамически
        best_score=rf_score,
        predictions_count=combination_count,
        correct_predictions=0  # Обновится после проверки
      )

    except Exception as e:
      print(f"Ошибка записи производительности RF: {e}")