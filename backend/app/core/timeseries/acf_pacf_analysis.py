"""
Анализ автокорреляций и частичных автокорреляций
для определения параметров ARIMA
"""

import numpy as np
import pandas as pd
from statsmodels.stats.diagnostic import acorr_ljungbox
from statsmodels.tsa.stattools import acf, pacf, adfuller
from typing import Dict, Tuple, List, Optional
import logging

logger = logging.getLogger(__name__)


class ACFPACFAnalyzer:
  """Анализатор автокорреляционных функций"""

  def __init__(self, max_lag: int = 40):
    """
    Args:
        max_lag: Максимальный лаг для анализа
    """
    self.max_lag = max_lag
    self.acf_values = None
    self.pacf_values = None
    self.confidence_intervals = None

  def analyze(self, data: pd.Series) -> Dict:
    """
    Полный анализ автокорреляций

    Args:
        data: Временной ряд для анализа

    Returns:
        Словарь с результатами анализа
    """
    logger.info(f"Начинаем ACF/PACF анализ для {len(data)} точек данных")

    # Проверка стационарности
    stationarity = self._test_stationarity(data)

    # Расчет ACF и PACF
    self.acf_values, acf_confint = acf(data, nlags=self.max_lag, alpha=0.05)
    self.pacf_values, pacf_confint = pacf(data, nlags=self.max_lag, alpha=0.05)

    # Определение значимых лагов
    significant_acf_lags = self._find_significant_lags(self.acf_values, acf_confint)
    significant_pacf_lags = self._find_significant_lags(self.pacf_values, pacf_confint)

    # Предложение параметров ARIMA
    suggested_params = self._suggest_arima_params(
      significant_acf_lags,
      significant_pacf_lags,
      stationarity['needs_differencing']
    )

    # Тест Льюнга-Бокса на автокорреляцию остатков
    ljung_box = acorr_ljungbox(data, lags=min(10, len(data) // 5), return_df=True)

    results = {
      'acf_values': self.acf_values.tolist(),
      'pacf_values': self.pacf_values.tolist(),
      'acf_confidence': acf_confint.tolist(),
      'pacf_confidence': pacf_confint.tolist(),
      'significant_acf_lags': significant_acf_lags,
      'significant_pacf_lags': significant_pacf_lags,
      'stationarity': stationarity,
      'suggested_arima_params': suggested_params,
      'ljung_box_test': {
        'p_values': ljung_box['lb_pvalue'].tolist(),
        'statistics': ljung_box['lb_stat'].tolist()
      }
    }

    logger.info(f"Анализ завершен. Предложенные параметры ARIMA: {suggested_params}")
    return results

  def _test_stationarity(self, data: pd.Series) -> Dict:
    """
    Тест Дики-Фуллера на стационарность
    """
    result = adfuller(data.dropna())

    return {
      'adf_statistic': float(result[0]),
      'p_value': float(result[1]),
      'critical_values': result[4],
      'is_stationary': result[1] < 0.05,
      'needs_differencing': result[1] >= 0.05
    }

  def _find_significant_lags(self, values: np.ndarray, confint: np.ndarray) -> List[int]:
    """
    Поиск статистически значимых лагов
    """
    significant_lags = []
    for i in range(1, len(values)):
      lower, upper = confint[i]
      if values[i] < lower or values[i] > upper:
        significant_lags.append(i)
    return significant_lags[:10]  # Ограничиваем первыми 10 значимыми лагами

  def _suggest_arima_params(self, acf_lags: List[int], pacf_lags: List[int],
                            needs_diff: bool) -> Tuple[int, int, int]:
    """
    Эвристический подбор параметров ARIMA на основе ACF/PACF

    Returns:
        (p, d, q) - параметры ARIMA
    """
    # d - порядок интегрирования
    d = 1 if needs_diff else 0

    # p - порядок авторегрессии (AR) на основе PACF
    p = 0
    if pacf_lags:
      # Ищем точку отсечения в PACF
      if len(pacf_lags) > 0 and pacf_lags[0] <= 3:
        p = pacf_lags[0]
      else:
        p = 1  # По умолчанию

    # q - порядок скользящего среднего (MA) на основе ACF
    q = 0
    if acf_lags:
      # Ищем точку отсечения в ACF
      if len(acf_lags) > 0 and acf_lags[0] <= 3:
        q = acf_lags[0]
      else:
        q = 1  # По умолчанию

    # Ограничиваем сложность модели
    p = min(p, 3)
    q = min(q, 3)

    return (p, d, q)