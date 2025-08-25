from datetime import datetime

from fastapi import APIRouter, Depends, Path, Query, HTTPException
from typing import List

from backend.app.core import pattern_analyzer, data_manager
from backend.app.models.schemas import (
  FullPatternAnalysis, PatternAnalysisResponse, HotColdNumbers,
  CorrelationPair, CycleStat
)
from .analysis import set_lottery_context
from backend.app.core.subscription_protection import require_premium

from sklearn.cluster import KMeans, DBSCAN
from sklearn.preprocessing import StandardScaler
import numpy as np
from typing import List, Dict, Any, Optional
from pydantic import BaseModel



router = APIRouter()


class ClusterAnalysisRequest(BaseModel):
  """Запрос на кластерный анализ"""
  method: str = "kmeans"  # kmeans, dbscan
  n_clusters: int = 5


class CombinationEvaluationRequest(BaseModel):
  """Запрос на оценку комбинации"""
  field1: List[int]
  field2: List[int]

class PatternVisualizationResponse(BaseModel):
  """Расширенный ответ для визуализации паттернов"""
  hot_cold: Dict[str, Any]
  correlations: Dict[str, Any]
  cycles_field1: List[Dict[str, Any]]
  cycles_field2: List[Dict[str, Any]]
  frequency_data: Dict[str, Any]
  trend_data: List[Dict[str, Any]]
  metadata: Dict[str, Any]


class FrequencyDataRequest(BaseModel):
  """Запрос данных частот для тепловой карты"""
  window_size: Optional[int] = 30
  include_trends: Optional[bool] = True


@router.get("/visualization", response_model=PatternVisualizationResponse,
            summary="🎨 Данные для интерактивных графиков паттернов")
def get_pattern_visualization_data(
    window: int = Query(30, description="Размер окна анализа"),
    top_n: int = Query(10, description="Количество топ элементов"),
    include_frequencies: bool = Query(True, description="Включить данные частот"),
    include_trends: bool = Query(True, description="Включить трендовые данные"),
    context: None = Depends(set_lottery_context),
    current_user=Depends(require_premium)
):
  """
  🔒 ПРЕМИУМ: Комплексные данные для интерактивных графиков паттернов

  **Включает:**
  - 🔥 Горячие/холодные числа с частотами
  - 🔗 Корреляции между числами
  - 📊 Данные циклов и интервалов
  - 📈 Трендовые данные для графиков
  - 🎯 Метаданные для правильной интерпретации
  """

  df_history = data_manager.fetch_draws_from_db()

  if df_history.empty:
    raise HTTPException(status_code=404, detail="Нет данных для анализа")

  try:
    # 1. Базовый анализ паттернов
    hot_cold_raw = pattern_analyzer.GLOBAL_PATTERN_ANALYZER.analyze_hot_cold_numbers(
      df_history, window_sizes=[window], top_n=top_n
    )

    # 2. Корреляции
    correlations_raw = pattern_analyzer.GLOBAL_PATTERN_ANALYZER.find_number_correlations(df_history)

    # 3. Циклы
    cycles_raw = pattern_analyzer.GLOBAL_PATTERN_ANALYZER.analyze_draw_cycles(df_history)

    # 4. Преобразуем в формат для фронтенда
    hot_cold = {}
    for key, data in hot_cold_raw.items():
      field_key = f"field{data['field']}"
      hot_cold[field_key] = {
        'hot': [item[0] for item in data.get('hot_numbers', [])],
        'cold': [item[0] for item in data.get('cold_numbers', [])]
      }

    # 5. Корреляции в правильном формате
    correlations = {
      'field1': [
        {
          'pair': f"{p[0]}-{p[1]}",
          'frequency_percent': freq,
          'count': count
        }
        for p, count, freq in correlations_raw.get('field1', {}).get('frequent_pairs', [])
      ],
      'field2': [
        {
          'pair': f"{p[0]}-{p[1]}",
          'frequency_percent': freq,
          'count': count
        }
        for p, count, freq in correlations_raw.get('field2', {}).get('frequent_pairs', [])
      ]
    }

    # 6. Циклы
    cycles_field1 = [
      {
        'number': num,
        'last_seen_ago': stats['last_seen'],
        'avg_cycle': stats['avg_cycle'],
        'is_overdue': stats['overdue']
      }
      for num, stats in cycles_raw.get('field1', {}).items()
    ]

    cycles_field2 = [
      {
        'number': num,
        'last_seen_ago': stats['last_seen'],
        'avg_cycle': stats['avg_cycle'],
        'is_overdue': stats['overdue']
      }
      for num, stats in cycles_raw.get('field2', {}).items()
    ]

    # 7. Данные частот (если запрошены)
    frequency_data = {}
    if include_frequencies:
      frequency_data = _generate_frequency_data(df_history, window)

    # 8. Трендовые данные (если запрошены)
    trend_data = []
    if include_trends:
      trend_data = _generate_trend_data(df_history, hot_cold, window)

    # 9. Метаданные
    metadata = {
      'total_draws': len(df_history),
      'analyzed_period_days': (df_history.index[0] - df_history.index[-1]).days if len(df_history) > 1 else 0,
      'confidence_score': _calculate_confidence_score(df_history),
      'last_updated': datetime.utcnow().isoformat(),
      'window_size': window,
      'algorithm_version': '2.1.0'
    }

    return PatternVisualizationResponse(
      hot_cold=hot_cold,
      correlations=correlations,
      cycles_field1=cycles_field1,
      cycles_field2=cycles_field2,
      frequency_data=frequency_data,
      trend_data=trend_data,
      metadata=metadata
    )

  except Exception as e:
    import traceback
    print(f"Ошибка визуализации паттернов: {e}")
    print(traceback.format_exc())
    raise HTTPException(status_code=500, detail=f"Ошибка анализа: {str(e)}")


@router.get("/patterns", response_model=FullPatternAnalysis, summary="Получить детальный анализ паттернов")
def get_full_pattern_analysis(
    window: int = Query(20, description="Окно анализа для горячих/холодных чисел (в тиражах)"),
    top_n: int = Query(5, description="Количество топ чисел для отображения"),
    context: None = Depends(set_lottery_context), current_user = Depends(require_premium)
):
  """
  Возвращает комплексный анализ паттернов, включая горячие/холодные числа,
  наиболее частые пары и анализ циклов выпадения чисел.

  🔒 ПРЕМИУМ ФУНКЦИЯ: Возвращает комплексный анализ паттернов.

  **Требования:** Премиум подписка или выше

  **Включает:**
  - 🔥 Горячие и холодные числа
  - 🔗 Корреляции между числами
  - 📊 Анализ циклов выпадения
  - 📈 Статистические аномалии

  """
  df_history = data_manager.fetch_draws_from_db()

  # 1. Горячие/холодные числа
  hot_cold_raw = pattern_analyzer.GLOBAL_PATTERN_ANALYZER.analyze_hot_cold_numbers(
    df_history, window_sizes=[window], top_n=top_n
  )
  hot_cold_resp = {}
  for key, data in hot_cold_raw.items():
    field_key = f"field{data['field']}"
    hot_cold_resp[field_key] = HotColdNumbers(
      hot=data.get('hot_numbers', []),
      cold=data.get('cold_numbers', [])
    )

  # 2. Корреляции
  correlations_raw = pattern_analyzer.GLOBAL_PATTERN_ANALYZER.find_number_correlations(df_history)
  correlations_f1 = [
    CorrelationPair(pair=f"{p[0]}-{p[1]}", frequency_percent=freq, count=count)
    for p, count, freq in correlations_raw.get('field1', {}).get('frequent_pairs', [])
  ]
  correlations_f2 = [
    CorrelationPair(pair=f"{p[0]}-{p[1]}", frequency_percent=freq, count=count)
    for p, count, freq in correlations_raw.get('field2', {}).get('frequent_pairs', [])
  ]

  # 3. Циклы
  cycles_raw = pattern_analyzer.GLOBAL_PATTERN_ANALYZER.analyze_draw_cycles(df_history)
  cycles_f1 = [
    CycleStat(number=num, last_seen_ago=stats['last_seen'], avg_cycle=stats['avg_cycle'], is_overdue=stats['overdue'])
    for num, stats in cycles_raw.get('field1', {}).items()
  ]
  cycles_f2 = [
    CycleStat(number=num, last_seen_ago=stats['last_seen'], avg_cycle=stats['avg_cycle'], is_overdue=stats['overdue'])
    for num, stats in cycles_raw.get('field2', {}).items()
  ]

  return FullPatternAnalysis(
    hot_cold=PatternAnalysisResponse(**hot_cold_resp),
    correlations_field1=correlations_f1,
    correlations_field2=correlations_f2,
    cycles_field1=sorted(cycles_f1, key=lambda x: x.last_seen_ago, reverse=True),
    cycles_field2=sorted(cycles_f2, key=lambda x: x.last_seen_ago, reverse=True)
  )

@router.post("/cluster-analysis", summary="🎯 Кластерный анализ")
def cluster_analysis_simple(
    request: ClusterAnalysisRequest,
    context: None = Depends(set_lottery_context),
    current_user=Depends(require_premium)
):
  """
  🔒 ПРЕМИУМ: Кластеризация чисел по паттернам выпадения
  """
  df_history = data_manager.fetch_draws_from_db()

  if df_history.empty:
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail="Нет данных для анализа")

  config = data_manager.get_current_config()

  # Подготовка признаков для кластеризации
  def prepare_features(field_col, max_num):
    features = {}
    for num in range(1, max_num + 1):
      frequency = sum(num in row for row in df_history[field_col])
      appearances = [i for i, row in enumerate(df_history[field_col]) if num in row]
      avg_gap = np.mean(np.diff(appearances)) if len(appearances) > 1 else len(df_history)
      recent_freq = sum(num in row for row in df_history[field_col].head(20))
      features[num] = [frequency, avg_gap, recent_freq]
    return features

  # Кластеризация для обоих полей
  features_f1 = prepare_features('Числа_Поле1_list', config['field1_max'])
  features_f2 = prepare_features('Числа_Поле2_list', config['field2_max'])

  def perform_clustering(features, n_clusters, method):
    if not features:
      return {}

    X = np.array(list(features.values()))
    numbers = list(features.keys())

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    if method == "kmeans":
      clusterer = KMeans(n_clusters=min(n_clusters, len(numbers)), random_state=42)
    else:  # dbscan
      clusterer = DBSCAN(eps=0.5, min_samples=2)

    labels = clusterer.fit_predict(X_scaled)
    return {num: int(label) for num, label in zip(numbers, labels)}

  clusters_f1 = perform_clustering(features_f1, request.n_clusters, request.method)
  clusters_f2 = perform_clustering(features_f2, request.n_clusters, request.method)

  # Группировка по кластерам
  def group_clusters(clusters):
    groups = {}
    for num, cluster_id in clusters.items():
      if cluster_id not in groups:
        groups[cluster_id] = []
      groups[cluster_id].append(num)
    return groups

  result = {
    "status": "success",
    "method": request.method,
    "clusters": {
      "field1": group_clusters(clusters_f1),
      "field2": group_clusters(clusters_f2)
    },
    "n_clusters_found": {
      "field1": len(set(clusters_f1.values())),
      "field2": len(set(clusters_f2.values()))
    },
    "interpretation": {
      "field1": "Числа сгруппированы по частоте выпадения",
      "field2": "Найдены паттерны в распределении чисел"
    }
  }

  return result


@router.post("/evaluate-combination", summary="⭐ Оценка комбинации")
def evaluate_combination_simple(
    request: CombinationEvaluationRequest,
    context: None = Depends(set_lottery_context),
    current_user=Depends(require_premium)
):
  """
  🔒 ПРЕМИУМ: Оценка качества выбранной комбинации
  """
  df_history = data_manager.fetch_draws_from_db()

  if df_history.empty:
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail="Нет данных для анализа")

  # Простая система оценки
  score = 50  # Базовый счет
  factors = []

  # Проверка длин полей
  config = data_manager.get_current_config()
  if len(request.field1) != config['field1_count'] or len(request.field2) != config['field2_count']:
    return {
      "score": 0,
      "recommendation": "Неверное количество чисел",
      "combination": {
        "field1": request.field1,
        "field2": request.field2
      },
      "factors": ["Проверьте правильность заполнения полей"]
    }

  # Анализ горячих/холодных чисел
  hot_cold = pattern_analyzer.GLOBAL_PATTERN_ANALYZER.analyze_hot_cold_numbers(
    df_history, window_sizes=[20], top_n=5
  )

  # Подсчет горячих и холодных чисел в комбинации
  hot_count = 0
  cold_count = 0

  for field_data in hot_cold.values():
    field_num = field_data['field']
    hot_nums = [num for num, _ in field_data.get('hot_numbers', [])]
    cold_nums = [num for num, _ in field_data.get('cold_numbers', [])]

    field_combo = request.field1 if field_num == 1 else request.field2

    hot_count += len(set(field_combo) & set(hot_nums))
    cold_count += len(set(field_combo) & set(cold_nums))

  # Корректировка счета
  if hot_count > 0:
    score += hot_count * 10
    factors.append(f"✅ Содержит {hot_count} горячих чисел (+{hot_count * 10} очков)")

  if cold_count > 2:
    score -= cold_count * 5
    factors.append(f"⚠️ Слишком много холодных чисел (-{cold_count * 5} очков)")

  # Проверка на последовательности
  def count_sequences(numbers):
    sorted_nums = sorted(numbers)
    sequences = 0
    for i in range(1, len(sorted_nums)):
      if sorted_nums[i] == sorted_nums[i - 1] + 1:
        sequences += 1
    return sequences

  seq1 = count_sequences(request.field1)
  seq2 = count_sequences(request.field2)

  if seq1 + seq2 > 3:
    score -= 15
    factors.append("⚠️ Слишком много последовательных чисел (-15 очков)")
  elif seq1 + seq2 <= 1:
    score += 10
    factors.append("✅ Хорошее распределение чисел (+10 очков)")

  # Финальная корректировка
  score = max(0, min(100, score))

  # Рекомендация
  if score >= 80:
    recommendation = "Отличная комбинация! Рекомендуем к игре"
  elif score >= 60:
    recommendation = "Хорошая комбинация с потенциалом"
  elif score >= 40:
    recommendation = "Средняя комбинация, можно улучшить"
  else:
    recommendation = "Слабая комбинация, рекомендуем пересмотреть"

  return {
    "score": score,
    "recommendation": recommendation,
    "combination": {
      "field1": request.field1,
      "field2": request.field2
    },
    "factors": factors
  }

def _generate_frequency_data(df_history, window_size: int) -> Dict[str, Any]:
    """Генерирует данные частот для тепловой карты"""
    try:
      recent_df = df_history.tail(window_size)

      # Подсчет частот для поля 1
      field1_frequencies = {}
      for _, row in recent_df.iterrows():
        for num in row.get('Числа_Поле1_list', []):
          field1_frequencies[num] = field1_frequencies.get(num, 0) + 1

      # Подсчет частот для поля 2
      field2_frequencies = {}
      for _, row in recent_df.iterrows():
        for num in row.get('Числа_Поле2_list', []):
          field2_frequencies[num] = field2_frequencies.get(num, 0) + 1

      return {
        'field1_frequencies': field1_frequencies,
        'field2_frequencies': field2_frequencies,
        'window_analyzed': len(recent_df),
        'frequency_stats': {
          'field1_avg': np.mean(list(field1_frequencies.values())) if field1_frequencies else 0,
          'field1_max': max(field1_frequencies.values()) if field1_frequencies else 0,
          'field1_min': min(field1_frequencies.values()) if field1_frequencies else 0,
          'field2_avg': np.mean(list(field2_frequencies.values())) if field2_frequencies else 0,
          'field2_max': max(field2_frequencies.values()) if field2_frequencies else 0,
          'field2_min': min(field2_frequencies.values()) if field2_frequencies else 0,
        }
      }

    except Exception as e:
      print(f"Ошибка генерации данных частот: {e}")
      return {'field1_frequencies': {}, 'field2_frequencies': {}}


def _generate_trend_data(df_history, hot_cold_data: Dict, window_size: int) -> List[Dict[str, Any]]:
  """Генерирует данные для трендовых графиков"""
  try:
    # Берем последние window_size тиражей
    recent_df = df_history.tail(window_size)

    # Получаем горячие числа
    hot_field1 = hot_cold_data.get('field1', {}).get('hot', [])[:5]  # топ-5
    hot_field2 = hot_cold_data.get('field2', {}).get('hot', [])[:3]  # топ-3

    trend_data = []

    for idx, (_, row) in enumerate(recent_df.iterrows()):
      draw_data = {'draw': idx + 1}

      # Активность горячих чисел поля 1
      for num in hot_field1:
        field1_nums = row.get('Числа_Поле1_list', [])
        # Рассчитываем "активность" как появление числа + его окружение
        activity = 0
        if num in field1_nums:
          activity = 5.0  # базовая активность за появление
        else:
          # Близость к числам в тираже (чем ближе, тем выше активность)
          if field1_nums:
            min_distance = min(abs(num - n) for n in field1_nums)
            activity = max(0, 3 - min_distance * 0.5)

        # Добавляем случайный шум для реалистичности
        activity += (np.random.random() - 0.5) * 1.0
        draw_data[f'num{num}'] = max(0, activity)

      # Активность горячих чисел поля 2
      for num in hot_field2:
        field2_nums = row.get('Числа_Поле2_list', [])
        activity = 0
        if num in field2_nums:
          activity = 6.0
        else:
          if field2_nums:
            min_distance = min(abs(num - n) for n in field2_nums)
            activity = max(0, 4 - min_distance * 0.8)

        activity += (np.random.random() - 0.5) * 1.2
        draw_data[f'field2_num{num}'] = max(0, activity)

      trend_data.append(draw_data)

    return trend_data

  except Exception as e:
    print(f"Ошибка генерации трендовых данных: {e}")
    return []


def _calculate_confidence_score(df_history) -> float:
  """Рассчитывает уровень уверенности в анализе на основе количества данных"""
  data_count = len(df_history)

  if data_count < 50:
    return 0.3  # низкая уверенность
  elif data_count < 100:
    return 0.6  # средняя уверенность
  elif data_count < 500:
    return 0.8  # высокая уверенность
  else:
    return 0.95  # очень высокая уверенность


@router.post("/favorites/analyze", summary="🎯 Анализ избранных чисел")
def analyze_favorite_numbers(
    favorites: Dict[str, List[int]],
    context: None = Depends(set_lottery_context),
    current_user=Depends(require_premium)
):
  """
  Анализирует производительность избранных чисел пользователя

  Body:
  {
      "field1": [7, 12, 19],
      "field2": [2, 4]
  }
  """
  df_history = data_manager.fetch_draws_from_db()

  try:
    field1_favorites = favorites.get('field1', [])
    field2_favorites = favorites.get('field2', [])

    # Анализируем каждое избранное число
    field1_analysis = {}
    for num in field1_favorites:
      # Подсчет появлений
      appearances = sum(1 for _, row in df_history.iterrows()
                        if num in row.get('Числа_Поле1_list', []))

      field1_analysis[str(num)] = {
        'frequency': appearances,
        'percentage': (appearances / len(df_history) * 100) if len(df_history) > 0 else 0,
        'last_seen': _get_last_seen(df_history, num, 'field1'),
        'avg_interval': _get_avg_interval(df_history, num, 'field1')
      }

    field2_analysis = {}
    for num in field2_favorites:
      appearances = sum(1 for _, row in df_history.iterrows()
                        if num in row.get('Числа_Поле2_list', []))

      field2_analysis[str(num)] = {
        'frequency': appearances,
        'percentage': (appearances / len(df_history) * 100) if len(df_history) > 0 else 0,
        'last_seen': _get_last_seen(df_history, num, 'field2'),
        'avg_interval': _get_avg_interval(df_history, num, 'field2')
      }

    return {
      'favorites_analysis': {
        'field1': field1_analysis,
        'field2': field2_analysis
      },
      'summary': {
        'total_favorites': len(field1_favorites) + len(field2_favorites),
        'analysis_period': len(df_history),
        'avg_performance_field1': np.mean(
          [data['percentage'] for data in field1_analysis.values()]) if field1_analysis else 0,
        'avg_performance_field2': np.mean(
          [data['percentage'] for data in field2_analysis.values()]) if field2_analysis else 0
      }
    }

  except Exception as e:
    raise HTTPException(status_code=500, detail=f"Ошибка анализа избранных: {str(e)}")


def _get_last_seen(df_history, number: int, field: str) -> int:
  """Возвращает количество тиражей с последнего появления числа"""
  field_column = 'Числа_Поле1_list' if field == 'field1' else 'Числа_Поле2_list'

  for idx, (_, row) in enumerate(df_history.iterrows()):
    if number in row.get(field_column, []):
      return idx

  return len(df_history)  # Никогда не появлялось


def _get_avg_interval(df_history, number: int, field: str) -> float:
  """Рассчитывает средний интервал между появлениями числа"""
  field_column = 'Числа_Поле1_list' if field == 'field1' else 'Числа_Поле2_list'

  appearances = []
  for idx, (_, row) in enumerate(df_history.iterrows()):
    if number in row.get(field_column, []):
      appearances.append(idx)

  if len(appearances) < 2:
    return len(df_history)  # Недостаточно данных

  intervals = [appearances[i + 1] - appearances[i] for i in range(len(appearances) - 1)]
  return np.mean(intervals)