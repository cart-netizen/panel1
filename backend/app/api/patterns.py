from fastapi import APIRouter, Depends, Path, Query
from typing import List

from backend.app.core import pattern_analyzer, data_manager
from backend.app.models.schemas import (
  FullPatternAnalysis, PatternAnalysisResponse, HotColdNumbers,
  CorrelationPair, CycleStat
)
from .analysis import set_lottery_context
from backend.app.core.subscription_protection import require_premium

router = APIRouter()


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