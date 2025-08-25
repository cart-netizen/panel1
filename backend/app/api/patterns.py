from fastapi import APIRouter, Depends, Path, Query
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
from typing import List, Dict, Any
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

#
# @router.get("/analyze-patterns", summary="🔥 Упрощенный анализ паттернов")
# def analyze_patterns_simple(
#     context: None = Depends(set_lottery_context),
#     current_user=Depends(require_premium)
# ):
#   """
#   🔒 ПРЕМИУМ: Упрощенный анализ паттернов для фронтенда
#
#   Возвращает данные в формате, ожидаемом AnalysisPage.tsx
#   """
#   df_history = data_manager.fetch_draws_from_db()
#
#   if df_history.empty:
#     from fastapi import HTTPException
#     raise HTTPException(status_code=404, detail="Нет данных для анализа")
#
#   # Используем существующий анализатор
#   hot_cold_raw = pattern_analyzer.GLOBAL_PATTERN_ANALYZER.analyze_hot_cold_numbers(
#     df_history, window_sizes=[20], top_n=5
#   )
#
#   # Преобразуем в формат для фронтенда
#   result = {
#     "total_draws": len(df_history),
#     "analyzed_period": (df_history.index[0] - df_history.index[-1]).days if len(df_history) > 1 else 0,
#     "patterns_found": len(hot_cold_raw),
#     "confidence_score": 0.85,  # Пример значения
#     "hot_numbers": {},
#     "cold_numbers": {},
#     "timestamp": df_history.index[0].isoformat() if not df_history.empty else None
#   }
#
#   # Обработка горячих и холодных чисел
#   for key, data in hot_cold_raw.items():
#     field_key = f"field{data['field']}"
#     result["hot_numbers"][field_key] = [num for num, _ in data.get('hot_numbers', [])]
#     result["cold_numbers"][field_key] = [num for num, _ in data.get('cold_numbers', [])]
#
#   return result


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