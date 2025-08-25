"""
Генератор лотерейных комбинаций на основе CDM модели
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional
import logging

from .bayesian_updater import BayesianUpdater
from .dirichlet_model import DirichletMultinomialModel

logger = logging.getLogger(__name__)


class CDMGenerator:
  """
  Генератор комбинаций на основе Compound Dirichlet-Multinomial модели
  с байесовским обновлением
  """

  def __init__(self, config: Dict):
    """
    Args:
        config: Конфигурация лотереи
    """
    self.config = config
    self.updater = BayesianUpdater(
      config=config,
      window_size=100,
      decay_factor=0.98
    )
    self.is_trained = False
    self.training_metrics = {}

    logger.info(f"CDM генератор инициализирован для лотереи {config.get('name', 'unknown')}")

  def train(self, df: pd.DataFrame) -> Dict:
    """
    Обучение модели на исторических данных

    Args:
        df: DataFrame с историческими тиражами

    Returns:
        Метрики обучения
    """
    logger.info(f"Обучение CDM модели на {len(df)} тиражах")

    # Пакетное обновление
    metrics = self.updater.update_batch(df)

    # Кросс-валидация для оценки качества
    if len(df) >= 50:
      # Извлекаем данные field1 для валидации
      field1_cols = [col for col in df.columns if col.startswith('field1_')]
      if field1_cols:
        field1_data = df[field1_cols].values
        cv_metrics = self.updater.field_models['field1'].cross_validate(
          field1_data, folds=min(5, len(df) // 10)
        )
        metrics['cross_validation'] = cv_metrics

    self.is_trained = True
    self.training_metrics = metrics

    logger.info(f"Обучение завершено. Энтропия field1: "
                f"{metrics.get('field1', {}).get('entropy', 'N/A'):.3f}")

    return metrics

  def generate(self, count: int = 5, strategy: str = 'mixed') -> List[Dict]:
    """
    Генерация комбинаций

    Args:
        count: Количество комбинаций
        strategy: Стратегия генерации ('sampling', 'map', 'mean', 'mixed')

    Returns:
        Список сгенерированных комбинаций
    """
    if not self.is_trained:
      raise ValueError("Модель не обучена. Вызовите train() сначала.")

    logger.info(f"Генерация {count} комбинаций со стратегией '{strategy}'")

    combinations = []

    for i in range(count):
      # Выбор метода для этой комбинации
      if strategy == 'mixed':
        # Чередуем методы
        methods = ['sampling', 'map', 'mean']
        method = methods[i % len(methods)]
      else:
        method = strategy

      # Генерация через байесовский обновитель
      predictions = self.updater.get_predictions(1)
      combination = predictions[0]

      # Добавление дополнительной информации
      combination['strategy'] = method
      combination['bayesian_info'] = self._get_bayesian_info(combination)

      combinations.append(combination)

    # Сортировка по уверенности
    combinations.sort(key=lambda x: x['confidence'], reverse=True)

    return combinations

  def update_with_new_draw(self, new_draw: Dict) -> Dict:
    """
    Обновление модели с новым тиражом

    Args:
        new_draw: Новый тираж

    Returns:
        Метрики после обновления
    """
    logger.info("Инкрементальное обновление CDM модели")

    metrics = self.updater.update_incremental(new_draw)

    # Обновление статуса обученности
    if self.updater.update_count >= 10:
      self.is_trained = True

    return metrics

  def get_probability_analysis(self) -> Dict:
    """
    Получение полного анализа вероятностей

    Returns:
        Анализ вероятностей для всех полей
    """
    if not self.is_trained:
      raise ValueError("Модель не обучена")

    analysis = {}

    # Анализ field1
    field1_dist = self.updater.get_probability_distribution('field1')
    analysis['field1'] = field1_dist

    # Анализ field2 (если есть)
    if self.config.get('field2_size', 0) > 0:
      field2_dist = self.updater.get_probability_distribution('field2')
      analysis['field2'] = field2_dist

    # Общая статистика
    analysis['summary'] = {
      'total_observations': self.updater.update_count,
      'model_entropy': {
        'field1': self.updater.prior_managers['field1'].calculate_entropy()
      },
      'convergence_status': self._assess_convergence()
    }

    if 'field2' in self.updater.prior_managers:
      analysis['summary']['model_entropy']['field2'] = \
        self.updater.prior_managers['field2'].calculate_entropy()

    return analysis

  def get_hot_cold_analysis(self) -> Dict:
    """
    Анализ горячих и холодных чисел с байесовской точки зрения

    Returns:
        Анализ горячих/холодных чисел
    """
    if not self.is_trained:
      raise ValueError("Модель не обучена")

    analysis = {}

    for field in ['field1', 'field2']:
      if field not in self.updater.prior_managers:
        continue

      manager = self.updater.prior_managers[field]
      probs = manager.get_posterior_mean()

      # Сортировка чисел по вероятности
      numbers_sorted = np.argsort(probs)[::-1]

      # Определение горячих и холодных
      n_hot = min(10, len(numbers_sorted) // 3)
      n_cold = n_hot

      hot_numbers = (numbers_sorted[:n_hot] + 1).tolist()
      cold_numbers = (numbers_sorted[-n_cold:] + 1).tolist()

      # Доверительные интервалы для горячих/холодных
      ci = manager.get_credible_intervals()

      analysis[field] = {
        'hot_numbers': {
          'numbers': hot_numbers,
          'probabilities': [float(probs[n - 1]) for n in hot_numbers],
          'confidence_intervals': [
            (float(ci['lower'][n - 1]), float(ci['upper'][n - 1]))
            for n in hot_numbers
          ]
        },
        'cold_numbers': {
          'numbers': cold_numbers,
          'probabilities': [float(probs[n - 1]) for n in cold_numbers],
          'confidence_intervals': [
            (float(ci['lower'][n - 1]), float(ci['upper'][n - 1]))
            for n in cold_numbers
          ]
        },
        'temperature_metric': float(probs.max() / probs.min())
      }

    return analysis

  def simulate_performance(self, test_data: pd.DataFrame,
                           n_simulations: int = 100) -> Dict:
    """
    Симуляция производительности модели на тестовых данных

    Args:
        test_data: Тестовые тиражи
        n_simulations: Количество симуляций

    Returns:
        Результаты симуляции
    """
    if not self.is_trained:
      raise ValueError("Модель не обучена")

    logger.info(f"Симуляция производительности на {len(test_data)} тиражах")

    results = {
      'hits': [],
      'partial_hits': [],
      'roi': []
    }

    for _ in range(n_simulations):
      total_cost = 0
      total_wins = 0
      hits_distribution = {i: 0 for i in range(self.config['field1_size'] + 1)}

      for _, actual_draw in test_data.iterrows():
        # Генерация предсказания
        prediction = self.generate(1)[0]

        # Подсчет попаданий
        actual_field1 = set()
        for i in range(1, self.config['field1_size'] + 1):
          col_name = f'field1_{i}'
          if col_name in actual_draw:
            actual_field1.add(actual_draw[col_name])

        predicted_field1 = set(prediction['field1'])
        hits = len(actual_field1 & predicted_field1)

        hits_distribution[hits] += 1

        # Расчет выигрыша (упрощенный)
        total_cost += 1  # Стоимость билета
        if hits >= 3:  # Минимальный выигрыш
          win_amount = self._calculate_win(hits)
          total_wins += win_amount

      results['hits'].append(hits_distribution)
      results['partial_hits'].append(
        sum(hits_distribution[i] for i in range(3, self.config['field1_size'] + 1))
      )
      results['roi'].append((total_wins - total_cost) / total_cost * 100)

    # Агрегация результатов
    aggregated = {
      'mean_roi': float(np.mean(results['roi'])),
      'std_roi': float(np.std(results['roi'])),
      'mean_partial_hits': float(np.mean(results['partial_hits'])),
      'hit_distribution': {}
    }

    # Усредненное распределение попаданий
    for i in range(self.config['field1_size'] + 1):
      aggregated['hit_distribution'][i] = float(
        np.mean([h[i] for h in results['hits']])
      )

    return aggregated

  def _get_bayesian_info(self, combination: Dict) -> Dict:
    """
    Получение байесовской информации для комбинации

    Args:
        combination: Сгенерированная комбинация

    Returns:
        Байесовская информация
    """
    info = {}

    # Вероятности для чисел в комбинации
    field1_probs = []
    manager = self.updater.prior_managers['field1']
    probs = manager.get_posterior_mean()

    for number in combination['field1']:
      prob = probs[number - 1]
      field1_probs.append(float(prob))

    info['field1_probabilities'] = field1_probs
    info['field1_mean_probability'] = float(np.mean(field1_probs))
    info['field1_joint_probability'] = float(np.prod(field1_probs))

    # Энтропия
    info['model_entropy'] = manager.calculate_entropy()

    # Эффективный размер выборки
    info['effective_sample_size'] = float(
      manager.posterior_alpha.sum() - len(manager.posterior_alpha)
    )

    return info

  def _calculate_win(self, hits: int) -> float:
    """
    Упрощенный расчет выигрыша

    Args:
        hits: Количество угаданных чисел

    Returns:
        Сумма выигрыша
    """
    # Упрощенная таблица выигрышей
    win_table = {
      3: 10,
      4: 100,
      5: 1000,
      6: 10000
    }

    return win_table.get(hits, 0)

  def _assess_convergence(self) -> str:
    """
    Оценка сходимости модели

    Returns:
        Статус сходимости
    """
    if self.updater.update_count < 50:
      return "insufficient_data"

    # Проверяем изменение энтропии
    if len(self.updater.performance_history) >= 10:
      recent_entropy = [
        p.get('entropy', 0)
        for p in self.updater.performance_history[-10:]
        if 'entropy' in p
      ]

      if recent_entropy:
        entropy_change = abs(recent_entropy[-1] - recent_entropy[0])
        if entropy_change < 0.01:
          return "converged"
        elif entropy_change < 0.1:
          return "converging"

    return "not_converged"