"""
API эндпоинты для байесовского анализа (CDM модель)
"""

from fastapi import APIRouter, HTTPException, Query, Body
from typing import Dict, List, Optional
import logging
import pandas as pd

from ..core.bayesian import CDMGenerator
from ..core import data_manager
from ..core.lottery_context import LotteryContext

router = APIRouter(prefix="/bayesian", tags=["bayesian"])
logger = logging.getLogger(__name__)

# Глобальное хранилище CDM генераторов
CDM_GENERATORS = {}


def get_or_create_cdm_generator(lottery_type: str) -> CDMGenerator:
  """Получить или создать CDM генератор"""
  if lottery_type not in CDM_GENERATORS:
    config = data_manager.LOTTERY_CONFIGS.get(lottery_type)
    if not config:
      raise ValueError(f"Неизвестный тип лотереи: {lottery_type}")
    CDM_GENERATORS[lottery_type] = CDMGenerator(config)
  return CDM_GENERATORS[lottery_type]


@router.post("/train")
async def train_cdm_model(
    lottery_type: str,
    window_size: Optional[int] = Query(None, description="Размер окна для обучения")
) -> Dict:
  """
  Обучение CDM модели на исторических данных
  """
  try:
    with LotteryContext(lottery_type):
      # Получаем данные
      df = data_manager.fetch_draws_from_db()

      if df is None or df.empty:
        raise HTTPException(status_code=404, detail="Нет данных для обучения")

      # Ограничиваем окно если указано
      if window_size:
        df = df.tail(window_size)

      # Получаем генератор
      generator = get_or_create_cdm_generator(lottery_type)

      # Обучение
      metrics = generator.train(df)

      return {
        "lottery_type": lottery_type,
        "draws_used": len(df),
        "training_metrics": metrics,
        "status": "success"
      }

  except Exception as e:
    logger.error(f"Ошибка обучения CDM модели: {e}")
    raise HTTPException(status_code=500, detail=str(e))


@router.get("/generate")
async def generate_combinations(
    lottery_type: str,
    count: int = Query(5, ge=1, le=20, description="Количество комбинаций"),
    strategy: str = Query("mixed", description="Стратегия: sampling, map, mean, mixed")
) -> Dict:
  """
  Генерация комбинаций с помощью CDM модели
  """
  try:
    with LotteryContext(lottery_type):
      generator = get_or_create_cdm_generator(lottery_type)

      # Проверка обученности
      if not generator.is_trained:
        # Автоматическое обучение
        df = data_manager.fetch_draws_from_db()
        if df is None or df.empty:
          raise HTTPException(status_code=404, detail="Нет данных для обучения")
        generator.train(df)

      # Генерация
      combinations = generator.generate(count=count, strategy=strategy)

      return {
        "lottery_type": lottery_type,
        "combinations": combinations,
        "strategy": strategy,
        "status": "success"
      }

  except Exception as e:
    logger.error(f"Ошибка генерации CDM: {e}")
    raise HTTPException(status_code=500, detail=str(e))


@router.post("/update")
async def update_with_new_draw(
    lottery_type: str,
    new_draw: Dict = Body(..., description="Новый тираж для обновления")
) -> Dict:
  """
  Инкрементальное обновление модели с новым тиражом
  """
  try:
    with LotteryContext(lottery_type):
      generator = get_or_create_cdm_generator(lottery_type)

      # Обновление
      metrics = generator.update_with_new_draw(new_draw)

      return {
        "lottery_type": lottery_type,
        "update_metrics": metrics,
        "status": "success"
      }

  except Exception as e:
    logger.error(f"Ошибка обновления CDM: {e}")
    raise HTTPException(status_code=500, detail=str(e))


@router.get("/probability-analysis")
async def get_probability_analysis(lottery_type: str) -> Dict:
  """
  Получение полного байесовского анализа вероятностей
  """
  try:
    with LotteryContext(lottery_type):
      generator = get_or_create_cdm_generator(lottery_type)

      if not generator.is_trained:
        raise HTTPException(status_code=400, detail="Модель не обучена")

      analysis = generator.get_probability_analysis()

      return {
        "lottery_type": lottery_type,
        "analysis": analysis,
        "status": "success"
      }

  except Exception as e:
    logger.error(f"Ошибка анализа вероятностей: {e}")
    raise HTTPException(status_code=500, detail=str(e))


@router.get("/hot-cold-analysis")
async def get_hot_cold_analysis(lottery_type: str) -> Dict:
  """
  Байесовский анализ горячих и холодных чисел
  """
  try:
    with LotteryContext(lottery_type):
      generator = get_or_create_cdm_generator(lottery_type)

      if not generator.is_trained:
        # Автообучение
        df = data_manager.fetch_draws_from_db()
        if df is None or df.empty:
          raise HTTPException(status_code=404, detail="Нет данных")
        generator.train(df)

      analysis = generator.get_hot_cold_analysis()

      return {
        "lottery_type": lottery_type,
        "hot_cold_analysis": analysis,
        "status": "success"
      }

  except Exception as e:
    logger.error(f"Ошибка анализа горячих/холодных: {e}")
    raise HTTPException(status_code=500, detail=str(e))


@router.post("/simulate")
async def simulate_performance(
    lottery_type: str,
    test_size: int = Query(100, description="Размер тестовой выборки"),
    n_simulations: int = Query(100, description="Количество симуляций")
) -> Dict:
  """
  Симуляция производительности CDM модели
  """
  try:
    with LotteryContext(lottery_type):
      generator = get_or_create_cdm_generator(lottery_type)

      # Получаем данные
      df = data_manager.fetch_draws_from_db()

      if df is None or len(df) < test_size + 50:
        raise HTTPException(status_code=404, detail="Недостаточно данных")

      # Разделение на обучение и тест
      train_df = df[:-test_size]
      test_df = df[-test_size:]

      # Обучение на тренировочных данных
      generator.train(train_df)

      # Симуляция на тестовых
      results = generator.simulate_performance(test_df, n_simulations)

      return {
        "lottery_type": lottery_type,
        "train_size": len(train_df),
        "test_size": len(test_df),
        "n_simulations": n_simulations,
        "simulation_results": results,
        "status": "success"
      }

  except Exception as e:
    logger.error(f"Ошибка симуляции: {e}")
    raise HTTPException(status_code=500, detail=str(e))


@router.get("/posterior-distribution")
async def get_posterior_distribution(
    lottery_type: str,
    field: str = Query("field1", description="Поле для анализа")
) -> Dict:
  """
  Получение апостериорного распределения для поля
  """
  try:
    with LotteryContext(lottery_type):
      generator = get_or_create_cdm_generator(lottery_type)

      if not generator.is_trained:
        raise HTTPException(status_code=400, detail="Модель не обучена")

      # Получаем распределение
      distribution = generator.updater.get_probability_distribution(field)

      return {
        "lottery_type": lottery_type,
        "field": field,
        "posterior_distribution": distribution,
        "status": "success"
      }

  except Exception as e:
    logger.error(f"Ошибка получения распределения: {e}")
    raise HTTPException(status_code=500, detail=str(e))