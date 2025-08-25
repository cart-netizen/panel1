"""
Детектор сезонности в лотерейных данных
"""

import numpy as np
import pandas as pd
from statsmodels.tsa.seasonal import seasonal_decompose
from scipy import signal
from typing import Dict, Optional, List
import logging

logger = logging.getLogger(__name__)


class SeasonalityDetector:
  """Детектор сезонных паттернов в лотерейных данных"""

  def __init__(self, min_period: int = 2, max_period: int = 52):
    """
    Args:
        min_period: Минимальный период для поиска
        max_period: Максимальный период для поиска
    """
    self.min_period = min_period
    self.max_period = max_period
    self.decomposition = None
    self.best_period = None

  def detect(self, data: pd.Series) -> Dict:
    """
    Обнаружение сезонности в данных

    Args:
        data: Временной ряд для анализа

    Returns:
        Словарь с результатами анализа сезонности
    """
    logger.info(f"Поиск сезонности в {len(data)} точках данных")

    # Поиск доминирующего периода через периодограмму
    dominant_periods = self._find_dominant_periods(data)

    # Тест на наличие сезонности для каждого периода
    seasonality_tests = {}
    for period in dominant_periods[:3]:  # Проверяем топ-3 периода
      if period >= self.min_period and period <= min(self.max_period, len(data) // 2):
        test_result = self._test_seasonality(data, period)
        seasonality_tests[period] = test_result

    # Выбор лучшего периода
    if seasonality_tests:
      self.best_period = max(seasonality_tests.keys(),
                             key=lambda k: seasonality_tests[k]['strength'])

      # Декомпозиция с лучшим периодом
      if self.best_period and len(data) >= 2 * self.best_period:
        self.decomposition = self._decompose(data, self.best_period)

    results = {
      'has_seasonality': self.best_period is not None,
      'best_period': self.best_period,
      'dominant_periods': dominant_periods[:5],
      'seasonality_tests': seasonality_tests,
      'decomposition': self._format_decomposition() if self.decomposition else None
    }

    logger.info(f"Сезонность {'обнаружена' if results['has_seasonality'] else 'не обнаружена'}")
    if self.best_period:
      logger.info(f"Лучший период: {self.best_period}")

    return results

  def _find_dominant_periods(self, data: pd.Series) -> List[int]:
    """
    Поиск доминирующих периодов через спектральный анализ
    """
    # Удаление тренда
    detrended = signal.detrend(data.dropna().values)

    # Периодограмма
    frequencies, power = signal.periodogram(detrended)

    # Исключаем нулевую частоту
    frequencies = frequencies[1:]
    power = power[1:]

    # Преобразование частот в периоды
    periods = 1 / frequencies

    # Фильтрация по допустимым периодам
    valid_mask = (periods >= self.min_period) & (periods <= self.max_period)
    periods = periods[valid_mask]
    power = power[valid_mask]

    # Сортировка по мощности
    sorted_indices = np.argsort(power)[::-1]
    dominant_periods = [int(round(periods[i])) for i in sorted_indices]

    # Удаление дубликатов с сохранением порядка
    seen = set()
    unique_periods = []
    for p in dominant_periods:
      if p not in seen:
        seen.add(p)
        unique_periods.append(p)

    return unique_periods

  def _test_seasonality(self, data: pd.Series, period: int) -> Dict:
    """
    Тестирование силы сезонности для заданного периода
    """
    if len(data) < 2 * period:
      return {'strength': 0.0, 'valid': False}

    try:
      # Декомпозиция
      decompose = seasonal_decompose(data, model='additive', period=period)

      # Расчет силы сезонности
      seasonal_var = np.var(decompose.seasonal.dropna())
      residual_var = np.var(decompose.resid.dropna())
      total_var = seasonal_var + residual_var

      if total_var > 0:
        strength = 1 - (residual_var / total_var)
      else:
        strength = 0.0

      return {
        'strength': float(strength),
        'seasonal_std': float(np.std(decompose.seasonal.dropna())),
        'valid': True
      }
    except Exception as e:
      logger.warning(f"Ошибка при тестировании периода {period}: {e}")
      return {'strength': 0.0, 'valid': False}

  def _decompose(self, data: pd.Series, period: int):
    """
    Декомпозиция временного ряда
    """
    try:
      return seasonal_decompose(data, model='additive', period=period)
    except Exception as e:
      logger.error(f"Ошибка декомпозиции: {e}")
      return None

  def _format_decomposition(self) -> Dict:
    """
    Форматирование результатов декомпозиции
    """
    if not self.decomposition:
      return None

    return {
      'trend': self.decomposition.trend.dropna().tolist(),
      'seasonal': self.decomposition.seasonal.dropna().tolist(),
      'residual': self.decomposition.resid.dropna().tolist(),
      'observed': self.decomposition.observed.dropna().tolist()
    }