"""
API эндпоинты для генетических алгоритмов
Профессиональная эволюционная оптимизация комбинаций
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
import asyncio
import uuid

from backend.app.core import data_manager
from backend.app.core.genetic.evolution import GeneticEvolution, EvolutionConfig
from backend.app.core.lottery_context import LotteryContext
from backend.app.core.subscription_protection import require_premium
from backend.app.api.analysis import set_lottery_context
from backend.app.api.auth import get_current_user
from backend.app.models.schemas import GenerationResponse, Combination
from backend.app.core.genetic.GeneticGenerator import GENETIC_GENERATOR, get_genetic_prediction

router = APIRouter(prefix="/genetic", tags=["Genetic Algorithm"])
logger = logging.getLogger(__name__)

# Хранилище задач эволюции (в продакшене использовать Redis)
evolution_tasks = {}


@router.post("/generate", response_model=GenerationResponse, summary="🧬 Генетическая генерация")
async def generate_genetic_combinations(
    num_combinations: int = Query(5, ge=1, le=20, description="Количество комбинаций"),
    generations: int = Query(30, ge=10, le=100, description="Количество поколений эволюции"),
    population_size: int = Query(50, ge=20, le=200, description="Размер популяции"),
    context: None = Depends(set_lottery_context),
    current_user=Depends(require_premium)
):
  """
  🔒 ПРЕМИУМ ФУНКЦИЯ: Генерация комбинаций с помощью генетического алгоритма

  **Преимущества генетического подхода:**
  - Эволюционная оптимизация на основе истории
  - Баланс между исследованием и эксплуатацией
  - Адаптивная мутация и кроссовер
  - Сохранение лучших решений (элитизм)

  **Параметры эволюции:**
  - generations: больше поколений = лучше результат, но дольше время
  - population_size: больше популяция = больше разнообразие

  **Требования:** Премиум подписка
  """
  try:
    # Загружаем историю
    df_history = data_manager.fetch_draws_from_db()

    if df_history.empty or len(df_history) < 10:
      raise HTTPException(
        status_code=400,
        detail="Недостаточно исторических данных для генетического алгоритма (минимум 10 тиражей)"
      )

    logger.info(f"🧬 Запуск генетической генерации для пользователя {current_user.email}")

    # Генерируем комбинации
    results = GENETIC_GENERATOR.generate_genetic_combinations(
      df_history=df_history,
      num_to_generate=num_combinations,
      generations=generations,
      population_size=population_size,
      use_cache=True
    )

    # Получаем статистику эволюции
    evolution_stats = GENETIC_GENERATOR.get_evolution_statistics()

    # Форматируем результаты
    combinations = []
    for field1, field2, description in results:
      combinations.append(Combination(
        field1=field1,
        field2=field2,
        description=description
      ))

    response = GenerationResponse(
      combinations=combinations,
      timestamp=datetime.now(),
      method="genetic_algorithm",
      statistics={
        "generations": generations,
        "population_size": population_size,
        "best_fitness": evolution_stats.get('best_fitness', 0) if evolution_stats else 0,
        "converged": evolution_stats.get('converged', False) if evolution_stats else False,
        "diversity": evolution_stats.get('final_diversity', 0) if evolution_stats else 0,
        "total_time": evolution_stats.get('total_time', 0) if evolution_stats else 0
      }
    )

    logger.info(f"✅ Генетическая генерация завершена: {len(combinations)} комбинаций")
    return response

  except Exception as e:
    logger.error(f"Ошибка генетической генерации: {e}")
    raise HTTPException(status_code=500, detail=str(e))


@router.post("/evolve", summary="🧬 Запуск эволюции (фоновая задача)")
async def start_evolution(
    generations: int = Query(50, ge=10, le=200, description="Количество поколений"),
    population_size: int = Query(100, ge=30, le=500, description="Размер популяции"),
    elite_size: int = Query(10, ge=2, le=50, description="Размер элиты"),
    mutation_rate: float = Query(0.1, ge=0.01, le=0.5, description="Вероятность мутации"),
    crossover_rate: float = Query(0.8, ge=0.5, le=1.0, description="Вероятность кроссовера"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    context: None = Depends(set_lottery_context),
    current_user=Depends(require_premium)
):
  """
  🔒 ПРЕМИУМ: Запуск полной эволюции в фоновом режиме

  Запускает долгую эволюцию с возможностью отслеживания прогресса.
  Используйте /evolution/status/{task_id} для проверки статуса.
  """
  try:
    # Загружаем историю
    df_history = data_manager.fetch_draws_from_db()

    if df_history.empty or len(df_history) < 10:
      raise HTTPException(
        status_code=400,
        detail="Недостаточно данных для эволюции"
      )

    # Создаем уникальный ID задачи
    task_id = str(uuid.uuid4())

    # Конфигурация эволюции
    config = EvolutionConfig(
      population_size=population_size,
      generations=generations,
      elite_size=elite_size,
      mutation_rate=mutation_rate,
      crossover_rate=crossover_rate,
      tournament_size=3,
      diversity_threshold=0.3,
      adaptive_rates=True,
      early_stopping_patience=max(5, generations // 10),
      parallel_evaluation=True,
      save_checkpoints=False
    )

    # Сохраняем начальный статус
    evolution_tasks[task_id] = {
      'status': 'started',
      'started_at': datetime.now(),
      'config': config.__dict__,
      'progress': 0,
      'result': None,
      'error': None
    }

    # Запускаем эволюцию в фоне
    background_tasks.add_task(
      run_evolution_task,
      task_id,
      df_history,
      data_manager.get_current_config(),
      config
    )

    return {
      'task_id': task_id,
      'status': 'started',
      'message': 'Эволюция запущена в фоновом режиме'
    }

  except Exception as e:
    logger.error(f"Ошибка запуска эволюции: {e}")
    raise HTTPException(status_code=500, detail=str(e))


async def run_evolution_task(task_id: str, df_history, lottery_config, config: EvolutionConfig):
  """Фоновая задача эволюции"""
  try:
    evolution_tasks[task_id]['status'] = 'running'

    # Создаем эволюционный движок
    evolution = GeneticEvolution(df_history, lottery_config, config)

    # Запускаем эволюцию
    result = await evolution.evolve_async()

    # Сохраняем результаты
    evolution_tasks[task_id].update({
      'status': 'completed',
      'completed_at': datetime.now(),
      'result': result.to_dict(),
      'progress': 100
    })

    logger.info(f"✅ Эволюция {task_id} завершена успешно")

  except Exception as e:
    logger.error(f"Ошибка в эволюции {task_id}: {e}")
    evolution_tasks[task_id].update({
      'status': 'error',
      'error': str(e),
      'completed_at': datetime.now()
    })


@router.get("/evolution/status/{task_id}", summary="📊 Статус эволюции")
async def get_evolution_status(
    task_id: str,
    current_user=Depends(get_current_user)
):
  """
  Получить статус задачи эволюции

  **Статусы:**
  - started: задача запущена
  - running: эволюция выполняется
  - completed: успешно завершено
  - error: произошла ошибка
  """
  if task_id not in evolution_tasks:
    raise HTTPException(status_code=404, detail="Задача не найдена")

  task = evolution_tasks[task_id]

  # Очищаем старые задачи (старше 1 часа)
  current_time = datetime.now()
  for tid, t in list(evolution_tasks.items()):
    if 'started_at' in t:
      elapsed = (current_time - t['started_at']).total_seconds()
      if elapsed > 3600:  # 1 час
        del evolution_tasks[tid]

  return task


@router.post("/predict", summary="🎯 Генетическое предсказание")
async def get_genetic_prediction_endpoint(
    context: None = Depends(set_lottery_context),
    current_user=Depends(require_premium)
):
  """
  🔒 ПРЕМИУМ: Быстрое предсказание на основе генетического алгоритма

  Использует упрощенную эволюцию для быстрого получения одной комбинации.
  """
  try:
    df_history = data_manager.fetch_draws_from_db()

    field1, field2 = get_genetic_prediction(df_history)

    if field1 is None or field2 is None:
      raise HTTPException(
        status_code=400,
        detail="Не удалось сгенерировать предсказание"
      )

    return {
      'field1': field1,
      'field2': field2,
      'method': 'genetic_quick',
      'confidence': 0.75  # Фиксированная уверенность для быстрого метода
    }

  except Exception as e:
    logger.error(f"Ошибка генетического предсказания: {e}")
    raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics", summary="📈 Статистика генетических алгоритмов")
async def get_genetic_statistics(
    context: None = Depends(set_lottery_context),
    current_user=Depends(get_current_user)
):
  """
  Получить статистику последней эволюции
  """
  stats = GENETIC_GENERATOR.get_evolution_statistics()

  if not stats:
    return {
      'message': 'Нет доступной статистики. Запустите генерацию сначала.',
      'has_data': False
    }

  return {
    'has_data': True,
    'best_fitness': stats['best_fitness'],
    'avg_final_fitness': stats['avg_final_fitness'],
    'generations_completed': stats['generations_completed'],
    'converged': stats['converged'],
    'convergence_generation': stats['convergence_generation'],
    'total_time': stats['total_time'],
    'final_diversity': stats['final_diversity'],
    'fitness_progression': stats['fitness_progression'],
    'best_solution': stats['best_solution']
  }