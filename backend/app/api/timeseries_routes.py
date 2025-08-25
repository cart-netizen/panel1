"""
API эндпоинты для анализа временных рядов
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, List, Optional
import pandas as pd
import logging

from ..core.timeseries import TimeSeriesGenerator
from ..core import data_manager
from ..core.lottery_context import LotteryContext

router = APIRouter(prefix="/timeseries", tags=["timeseries"])
logger = logging.getLogger(__name__)

# Глобальное хранилище генераторов
TIMESERIES_GENERATORS = {}


def get_or_create_generator(lottery_type: str) -> TimeSeriesGenerator:
  """Получить или создать генератор временных рядов"""
  if lottery_type not in TIMESERIES_GENERATORS:
    config = data_manager.LOTTERY_CONFIGS.get(lottery_type)
    if not config:
      raise ValueError(f"Неизвестный тип лотереи: {lottery_type}")
    TIMESERIES_GENERATORS[lottery_type] = TimeSeriesGenerator(config)
  return TIMESERIES_GENERATORS[lottery_type]


@router.post("/analyze")
async def analyze_timeseries(
    lottery_type: str,
    window_size: Optional[int] = Query(100, description="Размер окна для анализа")
) -> Dict:
  """
  Полный анализ временных рядов для лотереи
  """
  try:
    with LotteryContext(lottery_type):
      # Получаем данные
      df = data_manager.fetch_draws_from_db()

      if df is None or df.empty:
        raise HTTPException(status_code=404, detail="Нет данных для анализа")

      # Ограничиваем размер окна
      if window_size:
        df = df.tail(window_size)

      # Получаем генератор
      generator = get_or_create_generator(lottery_type)

      # Анализ без генерации
      generator.analyze_and_generate(df, count=0)

      # Получаем сводку анализа
      summary = generator.get_analysis_summary()

      return {
        "lottery_type": lottery_type,
        "draws_analyzed": len(df),
        "analysis_summary": summary,
        "status": "success"
      }

  except Exception as e:
    logger.error(f"Ошибка анализа временных рядов: {e}")
    raise HTTPException(status_code=500, detail=str(e))


@router.get("/generate")
async def generate_combinations(
    lottery_type: str,
    count: int = Query(5, ge=1, le=20, description="Количество комбинаций"),
    window_size: Optional[int] = Query(100, description="Размер окна истории")
) -> Dict:
  """
  Генерация комбинаций на основе анализа временных рядов
  """
  try:
    with LotteryContext(lottery_type):
      # Получаем данные
      df = data_manager.fetch_draws_from_db()

      if df is None or df.empty:
        raise HTTPException(status_code=404, detail="Нет данных для генерации")

      # Ограничиваем окно
      if window_size:
        df = df.tail(window_size)

      # Получаем генератор
      generator = get_or_create_generator(lottery_type)

      # Генерация комбинаций
      combinations = generator.analyze_and_generate(df, count=count)

      # Получаем сводку анализа
      summary = generator.get_analysis_summary()

      return {
        "lottery_type": lottery_type,
        "combinations": combinations,
        "analysis_summary": summary,
        "draws_analyzed": len(df),
        "status": "success"
      }

  except Exception as e:
    logger.error(f"Ошибка генерации: {e}")
    raise HTTPException(status_code=500, detail=str(e))


@router.get("/acf-pacf")
async def get_acf_pacf_analysis(
    lottery_type: str,
    field_name: str = Query(..., description="Название поля для анализа"),
    max_lag: int = Query(40, description="Максимальный лаг")
) -> Dict:
  """
  Анализ автокорреляций для конкретного поля
  """
  try:
    with LotteryContext(lottery_type):
      from ..core.timeseries import ACFPACFAnalyzer

      # Получаем данные
      df = data_manager.fetch_draws_from_db()

      if df is None or df.empty or field_name not in df.columns:
        raise HTTPException(status_code=404, detail="Данные не найдены")

      # Создаем временной ряд
      series = pd.Series(df[field_name].values, index=df.index)

      # Анализ
      analyzer = ACFPACFAnalyzer(max_lag=max_lag)
      results = analyzer.analyze(series)

      return {
        "lottery_type": lottery_type,
        "field_name": field_name,
        "analysis": results,
        "status": "success"
      }

  except Exception as e:
    logger.error(f"Ошибка ACF/PACF анализа: {e}")
    raise HTTPException(status_code=500, detail=str(e))


@router.get("/seasonality")
async def detect_seasonality(
    lottery_type: str,
    field_name: str = Query(..., description="Название поля"),
    max_period: int = Query(52, description="Максимальный период")
) -> Dict:
  """
  Обнаружение сезонности в данных
  """
  try:
    with LotteryContext(lottery_type):
      from ..core.timeseries import SeasonalityDetector

      # Получаем данные
      df = data_manager.fetch_draws_from_db()

      if df is None or df.empty or field_name not in df.columns:
        raise HTTPException(status_code=404, detail="Данные не найдены")

      # Создаем временной ряд
      series = pd.Series(df[field_name].values, index=df.index)

      # Анализ сезонности
      detector = SeasonalityDetector(max_period=max_period)
      results = detector.detect(series)

      return {
        "lottery_type": lottery_type,
        "field_name": field_name,
        "seasonality": results,
        "status": "success"
      }

  except Exception as e:
    logger.error(f"Ошибка обнаружения сезонности: {e}")
    raise HTTPException(status_code=500, detail=str(e))


@router.get("/trends")
async def analyze_trends(
    lottery_type: str,
    field_name: str = Query(..., description="Название поля")
) -> Dict:
  """
  Анализ трендов в данных
  """
  try:
    with LotteryContext(lottery_type):
      from ..core.timeseries import TrendDecomposer

      # Получаем данные
      df = data_manager.fetch_draws_from_db()

      if df is None or df.empty or field_name not in df.columns:
        raise HTTPException(status_code=404, detail="Данные не найдены")

      # Создаем временной ряд
      series = pd.Series(df[field_name].values, index=df.index)

      # Анализ трендов
      decomposer = TrendDecomposer()
      results = decomposer.analyze(series)

      return {
        "lottery_type": lottery_type,
        "field_name": field_name,
        "trends": results,
        "status": "success"
      }

  except Exception as e:
    logger.error(f"Ошибка анализа трендов: {e}")
    raise HTTPException(status_code=500, detail=str(e))


@router.post("/forecast")
async def forecast_arima(
    lottery_type: str,
    field_name: str = Query(..., description="Название поля"),
    steps: int = Query(5, ge=1, le=20, description="Шаги прогноза"),
    auto_arima: bool = Query(True, description="Автоподбор параметров")
) -> Dict:
  """
  ARIMA прогнозирование для конкретного поля
  """
  try:
    with LotteryContext(lottery_type):
      from ..core.timeseries import ARIMAModel

      # Получаем данные
      df = data_manager.fetch_draws_from_db()

      if df is None or df.empty or field_name not in df.columns:
        raise HTTPException(status_code=404, detail="Данные не найдены")

      # Создаем временной ряд
      series = pd.Series(df[field_name].values, index=df.index)

      # ARIMA модель
      model = ARIMAModel(use_auto=auto_arima)

      # Обучение
      fit_results = model.fit(series)

      # Прогноз
      forecast = model.predict(steps=steps)

      return {
        "lottery_type": lottery_type,
        "field_name": field_name,
        "model_params": fit_results['params'],
        "model_metrics": fit_results['metrics'],
        "forecast": forecast,
        "status": "success"
      }

  except Exception as e:
    logger.error(f"Ошибка ARIMA прогноза: {e}")
    raise HTTPException(status_code=500, detail=str(e))