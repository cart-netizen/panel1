"""
ARIMA/SARIMA модель для прогнозирования лотерейных чисел
"""

import numpy as np
import pandas as pd
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.statespace.sarimax import SARIMAX
from pmdarima import auto_arima
from typing import Dict, List, Tuple, Optional
import warnings
import logging

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)


class ARIMAModel:
  """ARIMA/SARIMA модель для анализа временных рядов лотереи"""

  def __init__(self, use_auto: bool = True, seasonal: bool = False):
    """
    Args:
        use_auto: Использовать автоматический подбор параметров
        seasonal: Использовать сезонную модель (SARIMA)
    """
    self.use_auto = use_auto
    self.seasonal = seasonal
    self.model = None
    self.fitted_model = None
    self.params = None
    self.residuals = None
    self.metrics = {}

  def fit(self, data: pd.Series,
          order: Optional[Tuple[int, int, int]] = None,
          seasonal_order: Optional[Tuple[int, int, int, int]] = None) -> Dict:
    """
    Обучение ARIMA модели

    Args:
        data: Временной ряд
        order: (p, d, q) параметры ARIMA
        seasonal_order: (P, D, Q, s) параметры сезонности

    Returns:
        Словарь с метриками и параметрами модели
    """
    logger.info(f"Обучение ARIMA модели на {len(data)} точках данных")

    if self.use_auto:
      # Автоматический подбор параметров
      logger.info("Используем auto_arima для подбора параметров")

      self.model = auto_arima(
        data,
        start_p=0, start_q=0,
        max_p=3, max_q=3,
        seasonal=self.seasonal,
        stepwise=True,
        suppress_warnings=True,
        error_action='ignore',
        n_jobs=-1
      )

      self.params = {
        'order': self.model.order,
        'seasonal_order': self.model.seasonal_order if self.seasonal else None
      }
      self.fitted_model = self.model

    else:
      # Ручные параметры
      if order is None:
        order = (1, 1, 1)  # Параметры по умолчанию

      logger.info(f"Обучение ARIMA{order}")

      if self.seasonal and seasonal_order:
        self.model = SARIMAX(
          data,
          order=order,
          seasonal_order=seasonal_order,
          enforce_stationarity=False,
          enforce_invertibility=False
        )
      else:
        self.model = ARIMA(
          data,
          order=order,
          enforce_stationarity=False,
          enforce_invertibility=False
        )

      self.fitted_model = self.model.fit(disp=0)
      self.params = {
        'order': order,
        'seasonal_order': seasonal_order if self.seasonal else None
      }

    # Сохранение остатков и метрик
    self.residuals = self.fitted_model.resid
    self._calculate_metrics()

    results = {
      'params': self.params,
      'metrics': self.metrics,
      'aic': float(self.fitted_model.aic),
      'bic': float(self.fitted_model.bic),
      'residuals_stats': {
        'mean': float(np.mean(self.residuals)),
        'std': float(np.std(self.residuals)),
        'skewness': float(pd.Series(self.residuals).skew()),
        'kurtosis': float(pd.Series(self.residuals).kurtosis())
      }
    }

    logger.info(f"Модель обучена. AIC: {results['aic']:.2f}, BIC: {results['bic']:.2f}")
    return results

  def predict(self, steps: int = 1, return_confidence: bool = True) -> Dict:
    """
    Прогнозирование будущих значений

    Args:
        steps: Количество шагов прогноза
        return_confidence: Возвращать доверительные интервалы

    Returns:
        Словарь с прогнозами
    """
    if self.fitted_model is None:
      raise ValueError("Модель не обучена. Вызовите fit() сначала.")

    # Прогноз
    if self.use_auto:
      forecast, conf_int = self.fitted_model.predict(
        n_periods=steps,
        return_conf_int=return_confidence
      )
      forecast = pd.Series(forecast)
    else:
      forecast_result = self.fitted_model.forecast(steps=steps)
      forecast = forecast_result

      if return_confidence:
        # Получаем доверительные интервалы
        forecast_df = self.fitted_model.get_forecast(steps=steps)
        conf_int = forecast_df.conf_int()
      else:
        conf_int = None

    result = {
      'forecast': forecast.tolist() if hasattr(forecast, 'tolist') else forecast,
      'steps': steps
    }

    if return_confidence and conf_int is not None:
      if isinstance(conf_int, pd.DataFrame):
        result['confidence_intervals'] = {
          'lower': conf_int.iloc[:, 0].tolist(),
          'upper': conf_int.iloc[:, 1].tolist()
        }
      else:
        result['confidence_intervals'] = {
          'lower': conf_int[:, 0].tolist(),
          'upper': conf_int[:, 1].tolist()
        }

    return result

  def _calculate_metrics(self):
    """Расчет метрик качества модели"""
    if self.residuals is not None:
      # Метрики ошибок
      self.metrics['mae'] = float(np.mean(np.abs(self.residuals)))
      self.metrics['rmse'] = float(np.sqrt(np.mean(self.residuals ** 2)))
      self.metrics['mape'] = float(np.mean(np.abs(self.residuals / (self.residuals + 1e-10))) * 100)

  def forecast_lottery_numbers(self, data: pd.DataFrame,
                               field: str, steps: int = 5) -> List[int]:
    """
    Специальный метод для прогнозирования лотерейных чисел

    Args:
        data: DataFrame с историей тиражей
        field: Название поля для анализа ('field1_1', 'field1_2', etc.)
        steps: Количество прогнозов

    Returns:
        Список предсказанных чисел
    """
    # Подготовка временного ряда
    series = pd.Series(data[field].values, index=data.index)

    # Обучение модели
    self.fit(series)

    # Прогноз
    prediction = self.predict(steps=steps, return_confidence=False)

    # Преобразование в целые числа в допустимом диапазоне
    forecast_values = prediction['forecast']

    # Определяем диапазон на основе истории
    min_val = int(series.min())
    max_val = int(series.max())

    # Округление и ограничение диапазона
    predicted_numbers = []
    for val in forecast_values:
      num = int(round(val))
      num = max(min_val, min(num, max_val))
      predicted_numbers.append(num)

    return predicted_numbers