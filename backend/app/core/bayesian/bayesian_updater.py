"""
Байесовский обновитель для инкрементального обучения
и адаптации модели к новым данным
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from collections import deque
import logging

from .prior_posterior import PriorPosteriorManager
from .dirichlet_model import DirichletMultinomialModel

logger = logging.getLogger(__name__)


class BayesianUpdater:
  """
  Класс для байесовского обновления моделей
  с учетом новых наблюдений и временной адаптации
  """

  def __init__(self, config: Dict, window_size: int = 100,
               decay_factor: float = 0.95):
    """
    Args:
        config: Конфигурация лотереи
        window_size: Размер скользящего окна для адаптации
        decay_factor: Фактор затухания для старых наблюдений
    """
    self.config = config
    self.window_size = window_size
    self.decay_factor = decay_factor

    # Инициализация моделей для каждого поля
    self.field_models = {}
    self.prior_managers = {}

    # История наблюдений
    self.observation_window = deque(maxlen=window_size)
    self.update_count = 0

    # Метрики производительности
    self.performance_history = []

    self._initialize_models()

  def _initialize_models(self):
    """Инициализация байесовских моделей для каждого поля"""

    # Модели для field1 (основные числа)
    num_balls = self.config['field1_max']
    draws_size = self.config['field1_size']

    self.field_models['field1'] = DirichletMultinomialModel(
      num_balls=num_balls,
      draws_size=draws_size,
      concentration=1.0,
      adaptive=True
    )

    self.prior_managers['field1'] = PriorPosteriorManager(
      num_categories=num_balls,
      prior_type='uniform'
    )

    # Модели для field2 (если есть)
    if self.config.get('field2_size', 0) > 0:
      num_balls_2 = self.config['field2_max']
      draws_size_2 = self.config['field2_size']

      self.field_models['field2'] = DirichletMultinomialModel(
        num_balls=num_balls_2,
        draws_size=draws_size_2,
        concentration=1.0,
        adaptive=True
      )

      self.prior_managers['field2'] = PriorPosteriorManager(
        num_categories=num_balls_2,
        prior_type='uniform'
      )

    logger.info(f"Инициализированы байесовские модели для {len(self.field_models)} полей")

  def update_batch(self, historical_data: pd.DataFrame) -> Dict:
    """
    Пакетное обновление на исторических данных

    Args:
        historical_data: DataFrame с историческими тиражами

    Returns:
        Метрики обновления
    """
    logger.info(f"Пакетное обновление на {len(historical_data)} тиражах")

    metrics = {}

    # Обновление модели field1
    field1_data = self._extract_field_data(historical_data, 'field1')
    if field1_data is not None:
      # Обновление CDM модели
      cdm_metrics = self.field_models['field1'].fit(field1_data)

      # Обновление Prior/Posterior менеджера
      flattened_data = field1_data.flatten() - 1  # Преобразование в индексы 0-based
      self.prior_managers['field1'].update_posterior(flattened_data)

      metrics['field1'] = {
        **cdm_metrics,
        'posterior_entropy': self.prior_managers['field1'].calculate_entropy()
      }

    # Обновление модели field2
    if 'field2' in self.field_models:
      field2_data = self._extract_field_data(historical_data, 'field2')
      if field2_data is not None:
        cdm_metrics = self.field_models['field2'].fit(field2_data)

        flattened_data = field2_data.flatten() - 1
        self.prior_managers['field2'].update_posterior(flattened_data)

        metrics['field2'] = {
          **cdm_metrics,
          'posterior_entropy': self.prior_managers['field2'].calculate_entropy()
        }

    self.update_count = len(historical_data)

    return metrics

  def update_incremental(self, new_draw: Dict) -> Dict:
    """
    Инкрементальное обновление с новым тиражом

    Args:
        new_draw: Новый тираж {'field1': [...], 'field2': [...]}

    Returns:
        Метрики после обновления
    """
    logger.info(f"Инкрементальное обновление, тираж #{self.update_count + 1}")

    # Добавление в окно наблюдений
    self.observation_window.append(new_draw)
    self.update_count += 1

    metrics = {}

    # Обновление field1
    if 'field1' in new_draw:
      field1_array = np.array(new_draw['field1']) - 1  # 0-based индексы

      # Обновление CDM
      cdm_metrics = self.field_models['field1'].update_online(field1_array)

      # Обновление Prior/Posterior с учетом decay
      if self.decay_factor < 1.0:
        # Применяем затухание к старым наблюдениям
        self.prior_managers['field1'].posterior_alpha *= self.decay_factor

      self.prior_managers['field1'].update_posterior(field1_array)

      metrics['field1'] = {
        **cdm_metrics,
        'posterior_mean': self.prior_managers['field1'].get_posterior_mean().tolist()
      }

    # Обновление field2
    if 'field2' in new_draw and 'field2' in self.field_models:
      field2_array = np.array(new_draw['field2']) - 1

      cdm_metrics = self.field_models['field2'].update_online(field2_array)

      if self.decay_factor < 1.0:
        self.prior_managers['field2'].posterior_alpha *= self.decay_factor

      self.prior_managers['field2'].update_posterior(field2_array)

      metrics['field2'] = {
        **cdm_metrics,
        'posterior_mean': self.prior_managers['field2'].get_posterior_mean().tolist()
      }

    # Оценка производительности
    if len(self.observation_window) >= 10:
      performance = self._evaluate_recent_performance()
      self.performance_history.append(performance)
      metrics['performance'] = performance

    return metrics

  def get_predictions(self, n_predictions: int = 5) -> List[Dict]:
    """
    Получение предсказаний на основе текущего состояния

    Args:
        n_predictions: Количество предсказаний

    Returns:
        Список предсказанных комбинаций
    """
    predictions = []

    for i in range(n_predictions):
      prediction = {
        'field1': [],
        'field2': [],
        'confidence': 0.0,
        'method': 'bayesian_cdm'
      }

      # Предсказание field1
      # Комбинируем предсказания CDM и Prior/Posterior
      cdm_pred = self.field_models['field1'].predict_next_draw(1, method='sampling')[0]

      # Получаем вероятности из Prior/Posterior
      posterior_probs = self.prior_managers['field1'].get_posterior_mean()

      # Взвешенное комбинирование
      if i % 2 == 0:
        # Четные - используем CDM
        prediction['field1'] = (cdm_pred + 1).tolist()  # Обратно к 1-based
      else:
        # Нечетные - сэмплируем из posterior
        sampled = np.random.choice(
          len(posterior_probs),
          size=self.config['field1_size'],
          replace=False,
          p=posterior_probs
        )
        prediction['field1'] = sorted((sampled + 1).tolist())

      # Предсказание field2
      if 'field2' in self.field_models:
        if i % 2 == 0:
          cdm_pred_2 = self.field_models['field2'].predict_next_draw(1, method='sampling')[0]
          prediction['field2'] = (cdm_pred_2 + 1).tolist()
        else:
          posterior_probs_2 = self.prior_managers['field2'].get_posterior_mean()
          sampled_2 = np.random.choice(
            len(posterior_probs_2),
            size=self.config['field2_size'],
            replace=False,
            p=posterior_probs_2
          )
          prediction['field2'] = sorted((sampled_2 + 1).tolist())

      # Оценка уверенности на основе энтропии
      entropy = self.prior_managers['field1'].calculate_entropy()
      max_entropy = np.log(self.config['field1_max'])  # Максимальная энтропия

      # Чем меньше энтропия, тем выше уверенность
      prediction['confidence'] = max(0.3, min(0.8, 1.0 - entropy / max_entropy))

      predictions.append(prediction)

    return predictions

  def get_probability_distribution(self, field: str = 'field1') -> Dict:
    """
    Получение распределения вероятностей для поля

    Args:
        field: Название поля ('field1' или 'field2')

    Returns:
        Словарь с распределением и статистикой
    """
    if field not in self.prior_managers:
      raise ValueError(f"Поле {field} не найдено")

    manager = self.prior_managers[field]
    model = self.field_models[field]

    # Получаем различные оценки вероятностей
    posterior_mean = manager.get_posterior_mean()
    posterior_mode = manager.get_posterior_mode()
    cdm_probs = model.predict_probabilities()

    # Доверительные интервалы
    credible_intervals = manager.get_credible_intervals(confidence=0.95)

    # Формирование результата
    distribution = {}
    for i in range(len(posterior_mean)):
      number = i + 1  # 1-based нумерация
      distribution[number] = {
        'posterior_mean': float(posterior_mean[i]),
        'posterior_mode': float(posterior_mode[i]),
        'cdm_probability': float(cdm_probs[i]),
        'combined': float((posterior_mean[i] + cdm_probs[i]) / 2),
        'ci_lower': float(credible_intervals['lower'][i]),
        'ci_upper': float(credible_intervals['upper'][i])
      }

    # Сортировка по combined вероятности
    sorted_numbers = sorted(
      distribution.keys(),
      key=lambda x: distribution[x]['combined'],
      reverse=True
    )

    return {
      'distribution': distribution,
      'top_numbers': sorted_numbers[:self.config[f'{field}_size']],
      'statistics': manager.get_summary_statistics()
    }

  def _extract_field_data(self, df: pd.DataFrame, field: str) -> Optional[np.ndarray]:
    """
    Извлечение данных поля из DataFrame

    Args:
        df: DataFrame с тиражами
        field: Название поля

    Returns:
        Массив данных или None
    """
    field_columns = [col for col in df.columns if col.startswith(field)]

    if not field_columns:
      return None

    data = df[field_columns].values
    return data

  def _evaluate_recent_performance(self) -> Dict:
    """
    Оценка производительности на последних наблюдениях

    Returns:
        Метрики производительности
    """
    if len(self.observation_window) < 2:
      return {}

    # Берем последние 10 наблюдений для оценки
    recent_draws = list(self.observation_window)[-10:]

    hits = []
    likelihoods = []

    for i in range(len(recent_draws) - 1):
      # Предсказываем следующий тираж
      prediction = self.get_predictions(1)[0]
      actual = recent_draws[i + 1]

      # Считаем попадания
      pred_set = set(prediction['field1'])
      actual_set = set(actual['field1'])
      hit_rate = len(pred_set & actual_set) / len(actual_set)
      hits.append(hit_rate)

      # Считаем правдоподобие
      if 'field1' in actual:
        likelihood = self.field_models['field1'].calculate_likelihood(
          np.array(actual['field1']) - 1
        )
        likelihoods.append(likelihood)

    return {
      'mean_hit_rate': float(np.mean(hits)) if hits else 0.0,
      'max_hit_rate': float(np.max(hits)) if hits else 0.0,
      'mean_likelihood': float(np.mean(likelihoods)) if likelihoods else 0.0
    }

  def reset(self):
    """Сброс всех моделей к начальному состоянию"""
    self._initialize_models()
    self.observation_window.clear()
    self.update_count = 0
    self.performance_history = []
    logger.info("Байесовский обновитель сброшен")