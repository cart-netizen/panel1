from fastapi import APIRouter, Depends, Path, HTTPException

from backend.app.core import bankroll_manager, combination_generator, data_manager
from backend.app.models.schemas import SimulationParams, SimulationResponse
from .analysis import set_lottery_context

router = APIRouter()


@router.post("/simulate", response_model=SimulationResponse, summary="Симулировать стратегию на исторических данных")
def simulate_strategy(params: SimulationParams, context: None = Depends(set_lottery_context)):
  """
  Выполняет симуляцию выбранной стратегии на исторических данных
  и возвращает полную финансовую статистику.
  """
  df_history = data_manager.fetch_draws_from_db()
  if len(df_history) < 50:  # Требуется достаточное количество данных для симуляции
    raise HTTPException(status_code=400,
                        detail="Недостаточно исторических данных для проведения симуляции (требуется минимум 50 тиражей).")

  # --- ПОЛНОСТЬЮ ЗАПОЛНЕННАЯ КАРТА СТРАТЕГИЙ ---
  strategy_map = {
    'multi': combination_generator.generate_multi_strategy_combinations,
    'hot': lambda df, n: combination_generator.generate_pattern_based_combinations(df, n, 'hot'),
    'cold': lambda df, n: combination_generator.generate_pattern_based_combinations(df, n, 'cold'),
    'balanced': lambda df, n: combination_generator.generate_pattern_based_combinations(df, n, 'balanced'),
    'rf_ranked': lambda df, n: combination_generator.generate_rf_ranked_combinations(df, n, num_candidates_to_score=200)
    # num_candidates можно сделать параметром
  }

  strategy_func = strategy_map.get(params.strategy)
  if not strategy_func:
    raise HTTPException(status_code=400, detail=f"Стратегия '{params.strategy}' не найдена.")

  # Обновляем параметры менеджера банкролла перед симуляцией
  bankroll_manager.GLOBAL_BANKROLL_MANAGER.initial_bankroll = params.initial_bankroll
  bankroll_manager.GLOBAL_BANKROLL_MANAGER.ticket_cost = params.ticket_cost

  results = bankroll_manager.GLOBAL_BANKROLL_MANAGER.simulate_strategy_performance(
    strategy_func=strategy_func,
    df_history=df_history,
    initial_bankroll=params.initial_bankroll,
    num_draws_to_simulate=params.num_draws_to_simulate,
    combos_per_draw=params.combos_per_draw
  )

  if "error" in results:
    raise HTTPException(status_code=500, detail=results["error"])

  # Убеждаемся, что все поля существуют в ответе перед созданием модели
  # Pydantic автоматически вызовет ошибку, если каких-то полей не будет
  return SimulationResponse(**results)