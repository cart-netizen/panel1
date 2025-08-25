"""
Генератор комбинаций на основе анализа временных рядов
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional
from .arima_model import ARIMAModel
from .acf_pacf_analysis import ACFPACFAnalyzer
from .seasonality import SeasonalityDetector
from .trend_decomposition import TrendDecomposer
import logging

logger = logging.getLogger(__name__)


class TimeSeriesGenerator:
  """Генератор лотерейных комбинаций на основе анализа временных рядов"""

  def __init__(self, config: Dict):
    """
    Args:
        config: Конфигурация лотереи
    """
    self.config = config
    self.arima = ARIMAModel(use_auto=True)
    self.acf_analyzer = ACFPACFAnalyzer()
    self.seasonality = SeasonalityDetector()
    self.trend_decomposer = TrendDecomposer()
    self.analysis_results = {}

  def analyze_and_generate(self, df: pd.DataFrame, count: int = 5) -> List[Dict]:
    """
    Анализ временных рядов и генерация комбинаций

    Args:
        df: DataFrame с историей тиражей
        count: Количество комбинаций для генерации

    Returns:
        Список сгенерированных комбинаций
    """
    logger.info(f"Начинаем анализ временных рядов для {len(df)} тиражей")

    # Анализ каждого числового поля
    field_predictions = {}
    field_analysis = {}

    # Анализируем field1 (основные числа)
    for i in range(1, self.config['field1_size'] + 1):
      field_name = f'field1_{i}'
      if field_name in df.columns:
        series = pd.Series(df[field_name].values, index=df.index)

        # Комплексный анализ
        analysis = self._analyze_series(series, field_name)
        field_analysis[field_name] = analysis

        # Прогнозирование
        predictions = self._predict_numbers(series, analysis, count)
        field_predictions[field_name] = predictions

    # Анализируем field2 (дополнительные числа)
    if self.config.get('field2_size', 0) > 0:
      for i in range(1, self.config['field2_size'] + 1):
        field_name = f'field2_{i}'
        if field_name in df.columns:
          series = pd.Series(df[field_name].values, index=df.index)
          analysis = self._analyze_series(series, field_name)
          field_analysis[field_name] = analysis
          predictions = self._predict_numbers(series, analysis, count)
          field_predictions[field_name] = predictions

    # Сохранение результатов анализа
    self.analysis_results = field_analysis

    # Генерация комбинаций
    combinations = self._create_combinations(field_predictions, count)

    logger.info(f"Сгенерировано {len(combinations)} комбинаций")
    return combinations

  def _analyze_series(self, series: pd.Series, field_name: str) -> Dict:
    """
    Комплексный анализ временного ряда
    """
    logger.info(f"Анализ поля {field_name}")

    analysis = {
      'field_name': field_name,
      'statistics': {
        'mean': float(series.mean()),
        'std': float(series.std()),
        'min': int(series.min()),
        'max': int(series.max())
      }
    }

    # ACF/PACF анализ
    try:
      acf_results = self.acf_analyzer.analyze(series)
      analysis['acf_pacf'] = acf_results
    except Exception as e:
      logger.warning(f"Ошибка ACF/PACF анализа для {field_name}: {e}")
      analysis['acf_pacf'] = None

    # Поиск сезонности
    try:
      seasonality_results = self.seasonality.detect(series)
      analysis['seasonality'] = seasonality_results
    except Exception as e:
      logger.warning(f"Ошибка анализа сезонности для {field_name}: {e}")
      analysis['seasonality'] = None

    # Анализ трендов
    try:
      trend_results = self.trend_decomposer.analyze(series)
      analysis['trends'] = trend_results
    except Exception as e:
      logger.warning(f"Ошибка анализа трендов для {field_name}: {e}")
      analysis['trends'] = None

    return analysis

  def _predict_numbers(self, series: pd.Series, analysis: Dict, count: int) -> List[int]:
    """
    Прогнозирование чисел на основе анализа
    """
    predictions = []

    try:
      # ARIMA прогноз
      if analysis.get('acf_pacf') and analysis['acf_pacf'].get('suggested_arima_params'):
        params = analysis['acf_pacf']['suggested_arima_params']

        # Обучение ARIMA с предложенными параметрами
        self.arima.fit(series, order=params)

        # Прогноз
        forecast = self.arima.predict(steps=count)
        raw_predictions = forecast['forecast']

        # Учет сезонности
        if analysis.get('seasonality') and analysis['seasonality'].get('has_seasonality'):
          period = analysis['seasonality']['best_period']
          seasonal_adjustment = series.tail(period).mean() - series.mean()
          raw_predictions = [p + seasonal_adjustment for p in raw_predictions]

        # Учет тренда
        if analysis.get('trends') and analysis['trends'].get('trend_type'):
          trend_info = analysis['trends']['trend_type']
          if trend_info.get('slope'):
            trend_adjustment = trend_info['slope'] * np.arange(1, count + 1)
            raw_predictions = [p + ta for p, ta in zip(raw_predictions, trend_adjustment)]

        # Преобразование в допустимые числа
        min_val = analysis['statistics']['min']
        max_val = analysis['statistics']['max']

        for pred in raw_predictions:
          num = int(round(pred))
          num = max(min_val, min(num, max_val))
          predictions.append(num)

      else:
        # Fallback - случайные числа на основе статистики
        mean = analysis['statistics']['mean']
        std = analysis['statistics']['std']
        min_val = analysis['statistics']['min']
        max_val = analysis['statistics']['max']

        for _ in range(count):
          num = int(np.random.normal(mean, std))
          num = max(min_val, min(num, max_val))
          predictions.append(num)

    except Exception as e:
      logger.error(f"Ошибка прогнозирования: {e}")
      # Возвращаем случайные числа в диапазоне
      min_val = int(series.min())
      max_val = int(series.max())
      predictions = [np.random.randint(min_val, max_val + 1) for _ in range(count)]

    return predictions

  def _create_combinations(self, field_predictions: Dict, count: int) -> List[Dict]:
    """
    Создание комбинаций из предсказанных чисел
    """
    combinations = []

    for i in range(count):
      combination = {
        'field1': [],
        'field2': [],
        'confidence': 0.0,
        'method': 'time_series_analysis',
        'analysis_details': {}
      }

      # Собираем числа field1
      field1_numbers = []
      confidence_scores = []

      for j in range(1, self.config['field1_size'] + 1):
        field_name = f'field1_{j}'
        if field_name in field_predictions and i < len(field_predictions[field_name]):
          num = field_predictions[field_name][i]
          field1_numbers.append(num)

          # Оценка уверенности на основе качества анализа
          if self.analysis_results.get(field_name):
            analysis = self.analysis_results[field_name]
            conf = self._calculate_confidence(analysis)
            confidence_scores.append(conf)

      # Проверка уникальности и корректировка
      field1_numbers = self._ensure_unique_numbers(
        field1_numbers,
        1,
        self.config['field1_max']
      )
      combination['field1'] = sorted(field1_numbers[:self.config['field1_size']])

      # Собираем числа field2
      if self.config.get('field2_size', 0) > 0:
        field2_numbers = []
        for j in range(1, self.config['field2_size'] + 1):
          field_name = f'field2_{j}'
          if field_name in field_predictions and i < len(field_predictions[field_name]):
            num = field_predictions[field_name][i]
            field2_numbers.append(num)

            if self.analysis_results.get(field_name):
              analysis = self.analysis_results[field_name]
              conf = self._calculate_confidence(analysis)
              confidence_scores.append(conf)

        field2_numbers = self._ensure_unique_numbers(
          field2_numbers,
          1,
          self.config['field2_max']
        )
        combination['field2'] = sorted(field2_numbers[:self.config['field2_size']])

      # Средняя уверенность
      if confidence_scores:
        combination['confidence'] = np.mean(confidence_scores)
      else:
        combination['confidence'] = 0.3  # Базовая уверенность

      # Детали анализа для первой комбинации
      if i == 0:
        combination['analysis_details'] = {
          'has_seasonality': any(
            self.analysis_results.get(f'field1_{j}', {}).get('seasonality', {}).get('has_seasonality', False)
            for j in range(1, self.config['field1_size'] + 1)
          ),
          'trend_detected': any(
            not self.analysis_results.get(f'field1_{j}', {}).get('trends', {}).get('trend_type', {}).get(
              'is_stationary', True)
            for j in range(1, self.config['field1_size'] + 1)
          ),
          'arima_used': True
        }

      combinations.append(combination)

    return combinations

  def _calculate_confidence(self, analysis: Dict) -> float:
    """
    Расчет уверенности на основе качества анализа
    """
    confidence = 0.3  # Базовая уверенность

    # Повышаем уверенность при обнаружении паттернов
    if analysis.get('seasonality') and analysis['seasonality'].get('has_seasonality'):
      confidence += 0.2

    if analysis.get('trends') and not analysis['trends'].get('trend_type', {}).get('is_stationary', True):
      confidence += 0.1

    if analysis.get('acf_pacf') and analysis['acf_pacf'].get('stationarity', {}).get('is_stationary'):
      confidence += 0.1

    # Ограничиваем максимальную уверенность
    return min(confidence, 0.7)

  def _ensure_unique_numbers(self, numbers: List[int], min_val: int, max_val: int) -> List[int]:
    """
    Обеспечение уникальности чисел в комбинации
    """
    unique_numbers = list(set(numbers))

    # Добавляем числа, если не хватает
    while len(unique_numbers) < len(numbers):
      new_num = np.random.randint(min_val, max_val + 1)
      if new_num not in unique_numbers:
        unique_numbers.append(new_num)

    return unique_numbers

  def get_analysis_summary(self) -> Dict:
    """
    Получение сводки по анализу временных рядов
    """
    if not self.analysis_results:
      return {}

    summary = {
      'total_fields_analyzed': len(self.analysis_results),
      'seasonality_detected': [],
      'trends_detected': [],
      'stationary_fields': [],
      'recommended_arima_params': {}
    }

    for field_name, analysis in self.analysis_results.items():
      # Сезонность
      if analysis.get('seasonality') and analysis['seasonality'].get('has_seasonality'):
        summary['seasonality_detected'].append({
          'field': field_name,
          'period': analysis['seasonality']['best_period']
        })

      # Тренды
      if analysis.get('trends') and not analysis['trends'].get('trend_type', {}).get('is_stationary', True):
        summary['trends_detected'].append({
          'field': field_name,
          'direction': analysis['trends']['trend_type'].get('direction', 'unknown')
        })

      # Стационарность
      if analysis.get('acf_pacf') and analysis['acf_pacf'].get('stationarity', {}).get('is_stationary'):
        summary['stationary_fields'].append(field_name)

      # ARIMA параметры
      if analysis.get('acf_pacf') and analysis['acf_pacf'].get('suggested_arima_params'):
        summary['recommended_arima_params'][field_name] = analysis['acf_pacf']['suggested_arima_params']

    return summary