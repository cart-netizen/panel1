"""
Декомпозиция и анализ трендов в лотерейных данных
"""

import numpy as np
import pandas as pd
from scipy import signal
from scipy.optimize import curve_fit
from sklearn.linear_model import LinearRegression
from typing import Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)


class TrendDecomposer:
  """Анализатор трендов в временных рядах"""

  def __init__(self):
    self.trend_type = None
    self.trend_params = None
    self.detrended_data = None

  def analyze(self, data: pd.Series) -> Dict:
    """
    Полный анализ трендов

    Args:
        data: Временной ряд

    Returns:
        Словарь с результатами анализа
    """
    logger.info(f"Анализ трендов для {len(data)} точек")

    # Определение типа тренда
    trend_analysis = self._identify_trend_type(data)

    # Извлечение тренда различными методами
    trends = {
      'linear': self._extract_linear_trend(data),
      'polynomial': self._extract_polynomial_trend(data),
      'moving_average': self._extract_ma_trend(data),
      'hodrick_prescott': self._extract_hp_trend(data)
    }

    # Выбор лучшего тренда
    best_trend = self._select_best_trend(data, trends)

    # Детрендирование
    self.detrended_data = data - trends[best_trend]['values']

    # Анализ цикличности в детрендированных данных
    cycles = self._analyze_cycles(self.detrended_data)

    results = {
      'trend_type': trend_analysis,
      'trends': trends,
      'best_trend_method': best_trend,
      'detrended_stats': {
        'mean': float(self.detrended_data.mean()),
        'std': float(self.detrended_data.std()),
        'variance': float(self.detrended_data.var())
      },
      'cycles': cycles
    }

    logger.info(f"Лучший метод тренда: {best_trend}")
    return results

  def _identify_trend_type(self, data: pd.Series) -> Dict:
    """
    Идентификация типа тренда
    """
    x = np.arange(len(data))
    y = data.values

    # Линейная регрессия
    linear_model = LinearRegression()
    linear_model.fit(x.reshape(-1, 1), y)
    linear_score = linear_model.score(x.reshape(-1, 1), y)

    # Полиномиальная регрессия 2-й степени
    poly_coeffs = np.polyfit(x, y, 2)
    poly_values = np.polyval(poly_coeffs, x)
    poly_score = 1 - np.sum((y - poly_values) ** 2) / np.sum((y - y.mean()) ** 2)

    # Определение направления тренда
    if linear_model.coef_[0] > 0:
      direction = 'возрастающий'
    elif linear_model.coef_[0] < 0:
      direction = 'убывающий'
    else:
      direction = 'горизонтальный'

    return {
      'direction': direction,
      'linear_score': float(linear_score),
      'polynomial_score': float(poly_score),
      'slope': float(linear_model.coef_[0]),
      'is_stationary': abs(linear_model.coef_[0]) < 0.01
    }

  def _extract_linear_trend(self, data: pd.Series) -> Dict:
    """
    Извлечение линейного тренда
    """
    x = np.arange(len(data))
    model = LinearRegression()
    model.fit(x.reshape(-1, 1), data.values)
    trend = model.predict(x.reshape(-1, 1))

    return {
      'values': pd.Series(trend, index=data.index),
      'params': {
        'slope': float(model.coef_[0]),
        'intercept': float(model.intercept_)
      },
      'r2_score': float(model.score(x.reshape(-1, 1), data.values))
    }

  def _extract_polynomial_trend(self, data: pd.Series, degree: int = 3) -> Dict:
    """
    Извлечение полиномиального тренда
    """
    x = np.arange(len(data))
    coeffs = np.polyfit(x, data.values, degree)
    trend = np.polyval(coeffs, x)

    # R2 score
    r2 = 1 - np.sum((data.values - trend) ** 2) / np.sum((data.values - data.mean()) ** 2)

    return {
      'values': pd.Series(trend, index=data.index),
      'params': {'coefficients': coeffs.tolist()},
      'r2_score': float(r2)
    }

  def _extract_ma_trend(self, data: pd.Series, window: int = None) -> Dict:
    """
    Извлечение тренда скользящим средним
    """
    if window is None:
      window = max(3, len(data) // 10)

    trend = data.rolling(window=window, center=True).mean()

    # Заполнение пропусков на краях
    trend = trend.fillna(method='bfill').fillna(method='ffill')

    return {
      'values': trend,
      'params': {'window': window},
      'smoothness': float(1 - trend.diff().std() / data.std())
    }

  def _extract_hp_trend(self, data: pd.Series, lamb: float = 1600) -> Dict:
    """
    Фильтр Ходрика-Прескотта для извлечения тренда
    """
    # Упрощенная реализация HP-фильтра
    T = len(data)

    # Матрица для второй разности
    K = np.zeros((T - 2, T))
    for i in range(T - 2):
      K[i, i] = 1
      K[i, i + 1] = -2
      K[i, i + 2] = 1

    # Решение оптимизационной задачи
    I = np.eye(T)
    trend = np.linalg.inv(I + lamb * K.T @ K) @ data.values

    return {
      'values': pd.Series(trend, index=data.index),
      'params': {'lambda': lamb},
      'smoothness': float(1 - np.std(np.diff(trend)) / data.std())
    }

  def _select_best_trend(self, data: pd.Series, trends: Dict) -> str:
    """
    Выбор наилучшего метода извлечения тренда
    """
    scores = {}

    for method, trend_data in trends.items():
      if 'values' in trend_data:
        residuals = data - trend_data['values']
        # Критерий - минимальная дисперсия остатков
        scores[method] = residuals.var()

    return min(scores, key=scores.get)

  def _analyze_cycles(self, detrended: pd.Series) -> Dict:
    """
    Анализ циклических паттернов в детрендированных данных
    """
    # Спектральный анализ
    frequencies, power = signal.periodogram(detrended.dropna())

    # Топ-3 доминирующих частоты
    top_indices = np.argsort(power)[-3:][::-1]

    dominant_cycles = []
    for idx in top_indices:
      if frequencies[idx] > 0:
        period = 1 / frequencies[idx]
        dominant_cycles.append({
          'period': float(period),
          'frequency': float(frequencies[idx]),
          'power': float(power[idx])
        })

    return {
      'dominant_cycles': dominant_cycles,
      'has_cycles': len(dominant_cycles) > 0 and dominant_cycles[0]['power'] > np.mean(power) * 2
    }