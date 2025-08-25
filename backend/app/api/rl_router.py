"""
API роутер для Reinforcement Learning функционала
backend/app/routers/rl_router.py
"""
from datetime import datetime

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Optional, List, Dict
import asyncio
import logging

from pydantic import BaseModel

from backend.app.core import data_manager
from backend.app.core.rl.rl_generator import GLOBAL_RL_MANAGER

logger = logging.getLogger(__name__)

# Создаем роутер с префиксом
router = APIRouter(
  prefix="/rl",
  tags=["Reinforcement Learning"],
  responses={404: {"description": "Not found"}}
)


class TrainRequest(BaseModel):
  episodes: int = 100
  quick: bool = False  # Быстрое обучение для тестов

class GenerateRequest(BaseModel):
  count: int = 5
  strategy: str = "ensemble"  # 'q_learning', 'dqn', 'ensemble'
  window_size: int = 50

class GeneratedCombination(BaseModel):
  field1: List[int]
  field2: List[int]
  method: str
  confidence: float
  q_value: Optional[float] = None
  state_features: Optional[Dict] = None

# @router.post("/train")
# async def train_rl_agents(
#     lottery_type: str,
#     q_episodes: int = 500,
#     dqn_episodes: int = 300,
#     window_size: int = 50
# ):
#   """
#   Обучение RL агентов для выбранной лотереи
#
#   Args:
#       lottery_type: Тип лотереи (5_36, 6_45, etc.)
#       q_episodes: Количество эпизодов для Q-Learning
#       dqn_episodes: Количество эпизодов для DQN
#       window_size: Размер окна для вычисления признаков
#
#   Returns:
#       Статистика обучения
#   """
#   try:
#     # Проверяем существование лотереи
#     if lottery_type not in data_manager.LOTTERY_CONFIGS:
#       raise HTTPException(status_code=404, detail=f"Лотерея {lottery_type} не найдена")
#
#     config = data_manager.LOTTERY_CONFIGS[lottery_type]
#
#     # Получаем генератор
#     generator = GLOBAL_RL_MANAGER.get_generator(lottery_type, config)
#
#     # Загружаем данные
#     # with data_manager.LotteryContext(lottery_type):
#     df = data_manager.fetch_draws_from_db()
#
#     if len(df) < window_size + 10:
#       raise HTTPException(
#         status_code=400,
#         detail=f"Недостаточно данных для обучения: {len(df)} < {window_size + 10}"
#       )
#
#     # Запускаем обучение асинхронно
#     logger.info(f"🚀 Запуск обучения RL агентов для {lottery_type}")
#     stats = await asyncio.get_event_loop().run_in_executor(
#       None,
#       generator.train,
#       df,
#       q_episodes,
#       dqn_episodes,
#       window_size,
#       True  # verbose
#     )
#
#     return {
#       "status": "success",
#       "lottery_type": lottery_type,
#       "training_stats": stats,
#       "message": f"RL агенты успешно обучены для {lottery_type}"
#     }
#
#   except HTTPException:
#     raise
#   except Exception as e:
#     logger.error(f"Ошибка обучения RL для {lottery_type}: {e}")
#     raise HTTPException(status_code=500, detail=str(e))
@router.post("/train")
async def train_agents(
    lottery_type: str,
    request: TrainRequest,
    background_tasks: BackgroundTasks
):
  """Запуск обучения RL агентов"""
  try:
    if lottery_type not in data_manager.LOTTERY_CONFIGS:
      raise HTTPException(status_code=404, detail=f"Unknown lottery type: {lottery_type}")

    config = data_manager.LOTTERY_CONFIGS[lottery_type]
    generator = GLOBAL_RL_MANAGER.get_generator(lottery_type, config)

    # Загружаем данные
    df_history = data_manager.fetch_draws_from_db()

    if len(df_history) < 60:
      raise HTTPException(
        status_code=400,
        detail=f"Not enough data for training: {len(df_history)} < 60"
      )

    # Определяем параметры обучения
    if request.quick:
      q_episodes = 100
      dqn_episodes = 50
    else:
      # Адаптивные параметры в зависимости от сложности
      complexity = config['field1_size'] * config['field1_max']
      if complexity <= 80:
        q_episodes = min(request.episodes * 2, 1500)
        dqn_episodes = min(request.episodes, 800)
      elif complexity <= 180:
        q_episodes = min(request.episodes * 2, 2000)
        dqn_episodes = min(request.episodes, 1200)
      else:
        q_episodes = min(request.episodes * 2, 3000)
        dqn_episodes = min(request.episodes, 2000)

    # Запускаем обучение в фоне
    def train_in_background():
      try:
        logger.info(f"Starting RL training for {lottery_type}: Q={q_episodes}, DQN={dqn_episodes}")
        stats = generator.train(
          df_history=df_history,
          q_episodes=q_episodes,
          dqn_episodes=dqn_episodes,
          verbose=True
        )
        logger.info(f"Training completed for {lottery_type}: {stats}")
      except Exception as e:
        logger.error(f"Training failed for {lottery_type}: {e}")

    background_tasks.add_task(train_in_background)

    return {
      "lottery_type": lottery_type,
      "status": "training_started",
      "q_episodes": q_episodes,
      "dqn_episodes": dqn_episodes,
      "quick_mode": request.quick,
      "timestamp": datetime.now().isoformat()
    }

  except Exception as e:
    logger.error(f"Error starting training: {e}")
    raise HTTPException(status_code=500, detail=str(e))

# @router.get("/generate")
# async def generate_rl_combinations(
#     lottery_type: str,
#     count: int = 5,
#     strategy: str = "ensemble"
# ):
#   """
#   Генерация комбинаций с помощью RL агентов
#
#   Args:
#       lottery_type: Тип лотереи
#       count: Количество комбинаций (1-20)
#       strategy: Стратегия генерации (q_learning, dqn, ensemble)
#
#   Returns:
#       Сгенерированные комбинации с метаданными
#   """
#   try:
#     # Валидация параметров
#     if lottery_type not in data_manager.LOTTERY_CONFIGS:
#       raise HTTPException(status_code=404, detail=f"Лотерея {lottery_type} не найдена")
#
#     if count < 1 or count > 20:
#       raise HTTPException(status_code=400, detail="Количество должно быть от 1 до 20")
#
#     if strategy not in ["q_learning", "dqn", "ensemble"]:
#       raise HTTPException(status_code=400, detail="Неверная стратегия. Доступны: q_learning, dqn, ensemble")
#
#     config = data_manager.LOTTERY_CONFIGS[lottery_type]
#
#     # Получаем генератор
#     generator = GLOBAL_RL_MANAGER.get_generator(lottery_type, config)
#
#     # Проверяем обученность
#     if not generator.q_trained and not generator.dqn_trained:
#       # Пытаемся загрузить модели
#       if not generator.load_models():
#         raise HTTPException(
#           status_code=400,
#           detail="RL агенты не обучены. Сначала выполните обучение через /api/rl/train/{lottery_type}"
#         )
#
#     # Загружаем данные
#     # with data_manager.LotteryContext(lottery_type):
#     df = data_manager.fetch_draws_from_db()
#
#     # Генерируем комбинации
#     combinations = generator.generate_combinations(
#       count=count,
#       df_history=df,
#       strategy=strategy,
#       window_size=50
#     )
#
#     # Форматируем результат
#     result = []
#     for i, combo in enumerate(combinations, 1):
#       result.append({
#         "id": i,
#         "field1": combo['field1'],
#         "field2": combo['field2'],
#         "method": combo['method'],
#         "confidence": round(combo['confidence'], 3),
#         "q_value": round(combo.get('q_value', 0), 3) if 'q_value' in combo else None,
#         "state_features": combo.get('state_features', {})
#       })
#
#     return {
#       "status": "success",
#       "lottery_type": lottery_type,
#       "strategy": strategy,
#       "combinations": result,
#       "statistics": generator.get_statistics()
#     }
#
#   except HTTPException:
#     raise
#   except Exception as e:
#     logger.error(f"Ошибка генерации RL комбинаций для {lottery_type}: {e}")
#     raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate")
async def generate_combinations(lottery_type: str, request: GenerateRequest):
  """Генерация комбинаций с помощью RL агентов"""
  try:
    if lottery_type not in data_manager.LOTTERY_CONFIGS:
      raise HTTPException(status_code=404, detail=f"Unknown lottery type: {lottery_type}")

    config = data_manager.LOTTERY_CONFIGS[lottery_type]
    generator = GLOBAL_RL_MANAGER.get_generator(lottery_type, config)

    # Проверяем, обучены ли агенты
    if not generator.q_trained and not generator.dqn_trained:
      # Пытаемся загрузить сохраненные модели
      if not generator.load_models():
        raise HTTPException(
          status_code=400,
          detail="RL agents not trained. Please train them first."
        )

    # Загружаем историю для контекста
    df_history = data_manager.fetch_draws_from_db()

    if len(df_history) < request.window_size:
      raise HTTPException(
        status_code=400,
        detail=f"Not enough historical data: {len(df_history)} < {request.window_size}"
      )

    # Генерируем комбинации
    combinations = generator.generate_combinations(
      count=request.count,
      df_history=df_history,
      strategy=request.strategy,
      window_size=request.window_size
    )

    # Обновляем статистику уверенности
    if combinations:
      avg_confidence = sum(c.get('confidence', 0) for c in combinations) / len(combinations)
      generator.generation_stats['average_confidence'] = avg_confidence

    logger.info(f"Generated {len(combinations)} combinations using {request.strategy}")

    return {
      "lottery_type": lottery_type,
      "strategy": request.strategy,
      "combinations": combinations,
      "timestamp": datetime.now().isoformat()
    }

  except Exception as e:
    logger.error(f"Error generating combinations: {e}")
    raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
async def get_rl_status(lottery_type: str):
  """
  Получение статуса RL агентов для лотереи

  Args:
      lottery_type: Тип лотереи

  Returns:
      Статус обученности и статистика агентов
  """
  try:
    if lottery_type not in data_manager.LOTTERY_CONFIGS:
      raise HTTPException(status_code=404, detail=f"Лотерея {lottery_type} не найдена")

    config = data_manager.LOTTERY_CONFIGS[lottery_type]
    generator = GLOBAL_RL_MANAGER.get_generator(lottery_type, config)

    # Пытаемся загрузить модели если не загружены
    if not generator.q_trained and not generator.dqn_trained:
      generator.load_models()

    # Собираем детальную статистику
    status = {
      "lottery_type": lottery_type,
      "q_trained": generator.q_trained,
      "dqn_trained": generator.dqn_trained,
      "total_generated": generator.generation_stats.get('total_generated', 0),
      "timestamp": datetime.now().isoformat(),
      "metrics": {}
    }

    # Метрики Q-Learning
    if generator.q_trained:
      q_agent = generator.q_agent
      status["metrics"]["q_learning"] = {
        "episodes": q_agent.total_episodes,
        "q_table_size": q_agent._get_q_table_size(),
        "win_rate": (q_agent.wins / max(q_agent.total_episodes, 1)) * 100,  # Исправленный расчет
        "average_reward": q_agent.total_reward / max(q_agent.total_episodes, 1),
        "epsilon": q_agent.epsilon,
        "unique_states": len(q_agent.q_table)
      }

    # Метрики DQN
    if generator.dqn_trained:
      dqn_agent = generator.dqn_agent
      status["metrics"]["dqn"] = {
        "episodes": dqn_agent.total_episodes,
        "memory_size": len(dqn_agent.memory),
        "win_rate": (dqn_agent.wins / max(dqn_agent.total_episodes, 1)) * 100,  # Исправленный расчет
        "average_reward": dqn_agent.total_reward / max(dqn_agent.total_episodes, 1),
        "epsilon": dqn_agent.epsilon,
        "loss": dqn_agent.losses[-1] if dqn_agent.losses else 0
      }

    # Общие метрики генератора
    if generator.generation_stats:
      total_generated = generator.generation_stats.get('total_generated', 0)
      if total_generated > 0:
        status["metrics"]["generation"] = {
          "total": total_generated,
          "q_used": generator.generation_stats.get('q_agent_used', 0),
          "dqn_used": generator.generation_stats.get('dqn_agent_used', 0),
          "ensemble_used": generator.generation_stats.get('ensemble_used', 0),
          "average_confidence": generator.generation_stats.get('average_confidence', 0)
        }

    # Метрики exploration (если есть улучшенная система наград)
    if hasattr(generator, 'reward_calculator'):
      reward_stats = generator.reward_calculator.get_statistics()
      status["metrics"]["exploration"] = {
        "unique_combinations": reward_stats.get('unique_combinations', 0),
        "exploration_rate": reward_stats.get('exploration_rate', 0),
        "state_action_pairs": reward_stats.get('state_action_pairs', 0)
      }

    return status

  except HTTPException:
    raise
  except Exception as e:
    logger.error(f"Ошибка получения статуса RL для {lottery_type}: {e}")
    raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_rl_statistics():
  """Получение общей статистики по всем RL агентам"""
  try:
    statistics = {
      "total_agents": 0,
      "trained_agents": 0,
      "lotteries": {},
      "timestamp": datetime.now().isoformat()
    }

    for lottery_type in data_manager.LOTTERY_CONFIGS.keys():
      config = data_manager.LOTTERY_CONFIGS[lottery_type]
      generator = GLOBAL_RL_MANAGER.get_generator(lottery_type, config)

      # Считаем агентов
      statistics["total_agents"] += 2  # Q и DQN
      if generator.q_trained:
        statistics["trained_agents"] += 1
      if generator.dqn_trained:
        statistics["trained_agents"] += 1

      # Статистика по лотерее
      statistics["lotteries"][lottery_type] = {
        "q_trained": generator.q_trained,
        "dqn_trained": generator.dqn_trained,
        "generation_stats": generator.generation_stats
      }

    return statistics

  except Exception as e:
    logger.error(f"Error getting RL statistics: {e}")
    raise HTTPException(status_code=500, detail=str(e))

# @router.post("/evaluate")
# async def evaluate_rl_agents(
#     lottery_type: str,
#     test_size: int = 100
# ):
#   """
#   Оценка производительности RL агентов на тестовых данных
#
#   Args:
#       lottery_type: Тип лотереи
#       test_size: Размер тестовой выборки
#
#   Returns:
#       Метрики производительности для каждого агента
#   """
#   try:
#     if lottery_type not in data_manager.LOTTERY_CONFIGS:
#       raise HTTPException(status_code=404, detail=f"Лотерея {lottery_type} не найдена")
#
#     if test_size < 10 or test_size > 500:
#       raise HTTPException(status_code=400, detail="Размер тестовой выборки должен быть от 10 до 500")
#
#     config = data_manager.LOTTERY_CONFIGS[lottery_type]
#     generator = GLOBAL_RL_MANAGER.get_generator(lottery_type, config)
#
#     # Проверяем обученность
#     if not generator.q_trained and not generator.dqn_trained:
#       if not generator.load_models():
#         raise HTTPException(
#           status_code=400,
#           detail="RL агенты не обучены. Сначала выполните обучение."
#         )
#
#     # Загружаем данные
#     # with data_manager.LotteryContext(lottery_type):
#     df = data_manager.fetch_draws_from_db()
#
#     if len(df) < test_size + 50:
#       raise HTTPException(
#         status_code=400,
#         detail=f"Недостаточно данных для оценки: {len(df)} < {test_size + 50}"
#       )
#
#     # Используем последние test_size тиражей для тестирования
#     df_test = df.tail(test_size)
#
#     # Запускаем оценку асинхронно
#     metrics = await asyncio.get_event_loop().run_in_executor(
#       None,
#       generator.evaluate,
#       df_test,
#       50  # window_size
#     )
#
#     return {
#       "status": "success",
#       "lottery_type": lottery_type,
#       "test_size": test_size,
#       "metrics": metrics
#     }
#
#   except HTTPException:
#     raise
#   except Exception as e:
#     logger.error(f"Ошибка оценки RL для {lottery_type}: {e}")
#     raise HTTPException(status_code=500, detail=str(e))
@router.post("/evaluate")
async def evaluate_agents(lottery_type: str, num_episodes: int = 100):
  """Оценка производительности RL агентов"""
  try:
    if lottery_type not in data_manager.LOTTERY_CONFIGS:
      raise HTTPException(status_code=404, detail=f"Unknown lottery type: {lottery_type}")

    config = data_manager.LOTTERY_CONFIGS[lottery_type]
    generator = GLOBAL_RL_MANAGER.get_generator(lottery_type, config)

    if not generator.q_trained and not generator.dqn_trained:
      raise HTTPException(status_code=400, detail="No trained agents to evaluate")

    # Загружаем данные для тестирования
    df_history = data_manager.fetch_draws_from_db()

    # Используем последние 20% данных для тестирования
    test_size = len(df_history) // 5
    df_test = df_history.tail(test_size)

    # Запускаем оценку
    metrics = generator.evaluate(df_test, window_size=50)

    logger.info(f"Evaluation completed for {lottery_type}: {metrics}")

    return {
      "lottery_type": lottery_type,
      "test_size": len(df_test),
      "metrics": metrics,
      "timestamp": datetime.now().isoformat()
    }

  except Exception as e:
    logger.error(f"Error evaluating agents: {e}")
    raise HTTPException(status_code=500, detail=str(e))

@router.delete("/reset")
async def reset_rl_agents(lottery_type: str):
  """
  Сброс RL агентов для лотереи (удаление обученных моделей)

  Args:
      lottery_type: Тип лотереи

  Returns:
      Статус операции
  """
  try:
    if lottery_type not in data_manager.LOTTERY_CONFIGS:
      raise HTTPException(status_code=404, detail=f"Лотерея {lottery_type} не найдена")

    config = data_manager.LOTTERY_CONFIGS[lottery_type]
    generator = GLOBAL_RL_MANAGER.get_generator(lottery_type, config)

    # Сбрасываем агентов
    generator.q_agent = generator.q_agent.__class__(config)
    generator.dqn_agent = generator.dqn_agent.__class__(config, device=generator.dqn_agent.device)
    generator.q_trained = False
    generator.dqn_trained = False

    # Удаляем сохраненные файлы
    import os
    q_path = os.path.join(generator.models_dir, "q_agent.pkl")
    dqn_path = os.path.join(generator.models_dir, "dqn_agent.pth")

    if os.path.exists(q_path):
      os.remove(q_path)
    if os.path.exists(dqn_path):
      os.remove(dqn_path)

    logger.info(f"✅ RL агенты сброшены для {lottery_type}")

    return {
      "status": "success",
      "message": f"RL агенты успешно сброшены для {lottery_type}"
    }

  except Exception as e:
    logger.error(f"Ошибка сброса RL для {lottery_type}: {e}")
    raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_training_history(lottery_type: str):
  """
  Получение истории обучения RL агентов

  Args:
      lottery_type: Тип лотереи

  Returns:
      История обучения с метриками по эпизодам
  """
  try:
    if lottery_type not in data_manager.LOTTERY_CONFIGS:
      raise HTTPException(status_code=404, detail=f"Лотерея {lottery_type} не найдена")

    config = data_manager.LOTTERY_CONFIGS[lottery_type]
    generator = GLOBAL_RL_MANAGER.get_generator(lottery_type, config)

    history = {
      "q_learning": generator.q_agent.learning_history if generator.q_trained else [],
      "dqn": generator.dqn_agent.learning_history if generator.dqn_trained else []
    }

    return {
      "status": "success",
      "lottery_type": lottery_type,
      "history": history
    }

  except Exception as e:
    logger.error(f"Ошибка получения истории RL для {lottery_type}: {e}")
    raise HTTPException(status_code=500, detail=str(e))