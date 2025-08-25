"""
Реализация Compound Dirichlet-Multinomial (CDM) модели
для байесовского анализа лотерей
"""

import numpy as np
import pandas as pd
from scipy import stats
from scipy.special import gammaln, loggamma
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class DirichletMultinomialModel:
  """
  Compound Dirichlet-Multinomial модель для анализа лотерейных данных

  Модель предполагает:
  1. Вероятности чисел следуют распределению Дирихле
  2. Наблюдения следуют мультиномиальному распределению
  3. Байесовское обновление параметров на основе истории
  """

  def __init__(self, num_balls: int, draws_size: int,
               concentration: float = 1.0, adaptive: bool = True):
    """
    Args:
        num_balls: Общее количество чисел в лотерее
        draws_size: Количество чисел в одном тираже
        concentration: Параметр концентрации для априорного Дирихле
        adaptive: Адаптивное обновление концентрации
    """
    self.num_balls = num_balls
    self.draws_size = draws_size
    self.concentration = concentration
    self.adaptive = adaptive

    # Инициализация параметров модели
    self.alpha = np.ones(num_balls) * concentration
    self.counts = np.zeros(num_balls)
    self.num_observations = 0

    # Кэш для оптимизации вычислений
    self._cache = {}

    logger.info(f"CDM модель инициализирована: {num_balls} чисел, "
                f"размер тиража {draws_size}, концентрация {concentration}")

  def fit(self, historical_draws: np.ndarray) -> Dict:
    """
    Обучение модели на исторических данных

    Args:
        historical_draws: Массив исторических тиражей (n_draws x draws_size)

    Returns:
        Словарь с метриками обучения
    """
    logger.info(f"Обучение CDM модели на {len(historical_draws)} тиражах")

    # Сброс счетчиков
    self.counts = np.zeros(self.num_balls)
    self.num_observations = 0

    # Подсчет частот
    for draw in historical_draws:
      for number in draw:
        if 0 <= number < self.num_balls:
          self.counts[number] += 1
      self.num_observations += 1

    # Обновление параметров альфа
    self.alpha = np.ones(self.num_balls) * self.concentration + self.counts

    # Адаптивное обновление концентрации
    if self.adaptive:
      self._update_concentration()

    # Расчет метрик
    metrics = self._calculate_metrics()

    logger.info(f"Обучение завершено. Эффективный размер выборки: "
                f"{metrics['effective_sample_size']:.1f}")

    return metrics

  def predict_probabilities(self, lookback: Optional[int] = None) -> np.ndarray:
    """
    Предсказание вероятностей для каждого числа

    Args:
        lookback: Количество последних тиражей для учета (None = все)

    Returns:
        Вектор вероятностей для каждого числа
    """
    # Апостериорное среднее распределения Дирихле
    alpha_sum = self.alpha.sum()
    probabilities = self.alpha / alpha_sum

    # Корректировка на размер тиража
    # P(число i в тираже) = 1 - (1 - p_i)^draws_size
    draw_probabilities = 1 - np.power(1 - probabilities, self.draws_size)

    # Нормализация
    draw_probabilities = draw_probabilities / draw_probabilities.sum() * self.draws_size

    return draw_probabilities

  def predict_next_draw(self, n_predictions: int = 1,
                        method: str = 'sampling') -> List[np.ndarray]:
    """
    Предсказание следующих тиражей

    Args:
        n_predictions: Количество предсказаний
        method: Метод предсказания ('sampling', 'map', 'mean')

    Returns:
        Список предсказанных комбинаций
    """
    predictions = []

    for _ in range(n_predictions):
      if method == 'sampling':
        # Сэмплирование из апостериорного распределения
        theta = np.random.dirichlet(self.alpha)
        # Взвешенная выборка без возвращения
        prediction = np.random.choice(
          self.num_balls,
          size=self.draws_size,
          replace=False,
          p=theta
        )

      elif method == 'map':
        # Maximum a posteriori оценка
        if np.all(self.alpha > 1):
          theta = (self.alpha - 1) / (self.alpha.sum() - self.num_balls)
        else:
          theta = self.alpha / self.alpha.sum()

        # Выбор наиболее вероятных чисел
        prediction = np.argsort(theta)[-self.draws_size:]

      elif method == 'mean':
        # Использование среднего апостериорного
        theta = self.alpha / self.alpha.sum()

        # Стохастический выбор с учетом вероятностей
        prediction = self._weighted_sample_without_replacement(
          theta, self.draws_size
        )

      else:
        raise ValueError(f"Неизвестный метод: {method}")

      predictions.append(np.sort(prediction))

    return predictions

  def calculate_likelihood(self, draw: np.ndarray) -> float:
    """
    Расчет правдоподобия для конкретного тиража

    Args:
        draw: Тираж для оценки

    Returns:
        Логарифмическое правдоподобие
    """
    # Подсчет вхождений
    x = np.zeros(self.num_balls)
    for number in draw:
      if 0 <= number < self.num_balls:
        x[number] += 1

    # Log P(x | alpha) для Дирихле-Мультиномиального
    n = x.sum()
    alpha_sum = self.alpha.sum()

    # Логарифмическая функция бета
    log_likelihood = loggamma(alpha_sum) - loggamma(n + alpha_sum)
    log_likelihood += np.sum(loggamma(x + self.alpha) - loggamma(self.alpha))

    return float(log_likelihood)

  def update_online(self, new_draw: np.ndarray) -> Dict:
    """
    Онлайн обновление модели с новым тиражом

    Args:
        new_draw: Новый тираж

    Returns:
        Метрики после обновления
    """
    # Обновление счетчиков
    for number in new_draw:
      if 0 <= number < self.num_balls:
        self.counts[number] += 1

    self.num_observations += 1

    # Обновление параметров
    self.alpha = np.ones(self.num_balls) * self.concentration + self.counts

    # Адаптивное обновление концентрации
    if self.adaptive and self.num_observations % 10 == 0:
      self._update_concentration()

    metrics = {
      'num_observations': self.num_observations,
      'concentration': self.concentration,
      'entropy': self._calculate_entropy()
    }

    return metrics

  def _weighted_sample_without_replacement(self, weights: np.ndarray,
                                           k: int) -> np.ndarray:
    """
    Взвешенная выборка без возвращения

    Args:
        weights: Веса для каждого элемента
        k: Количество элементов для выборки

    Returns:
        Индексы выбранных элементов
    """
    # Алгоритм A-ExpJ для взвешенной выборки
    v = np.random.uniform(0, 1, self.num_balls)
    keys = np.power(v, 1.0 / weights)
    indices = np.argsort(keys)[-k:]

    return indices

  def _update_concentration(self):
    """
    Адаптивное обновление параметра концентрации
    методом максимального правдоподобия
    """
    if self.num_observations < 10:
      return

    # Эмпирический метод моментов для оценки концентрации
    observed_variance = np.var(self.counts / self.num_observations)
    expected_variance = 1 / (self.num_balls * (self.concentration + self.num_observations))

    if expected_variance > 0:
      new_concentration = max(0.1, min(10.0,
                                       observed_variance / expected_variance * self.concentration))

      # Плавное обновление
      self.concentration = 0.9 * self.concentration + 0.1 * new_concentration

  def _calculate_entropy(self) -> float:
    """
    Расчет энтропии апостериорного распределения
    """
    alpha_sum = self.alpha.sum()
    k = self.num_balls

    # Энтропия распределения Дирихле
    from scipy.special import digamma

    log_beta = np.sum(gammaln(self.alpha)) - gammaln(alpha_sum)
    entropy = log_beta + (alpha_sum - k) * digamma(alpha_sum)
    entropy -= np.sum((self.alpha - 1) * digamma(self.alpha))

    return float(entropy)

  def _calculate_metrics(self) -> Dict:
    """
    Расчет метрик модели
    """
    alpha_sum = self.alpha.sum()
    probabilities = self.alpha / alpha_sum

    return {
      'num_observations': self.num_observations,
      'concentration': self.concentration,
      'effective_sample_size': float(alpha_sum - self.num_balls),
      'entropy': self._calculate_entropy(),
      'max_probability': float(probabilities.max()),
      'min_probability': float(probabilities.min()),
      'probability_variance': float(probabilities.var()),
      'most_likely_numbers': np.argsort(probabilities)[-self.draws_size:].tolist(),
      'least_likely_numbers': np.argsort(probabilities)[:self.draws_size].tolist()
    }

  def cross_validate(self, historical_draws: np.ndarray,
                     folds: int = 5) -> Dict:
    """
    Кросс-валидация модели

    Args:
        historical_draws: Исторические данные
        folds: Количество фолдов

    Returns:
        Метрики кросс-валидации
    """
    n_draws = len(historical_draws)
    fold_size = n_draws // folds

    likelihoods = []
    accuracies = []

    for fold in range(folds):
      # Разделение на обучение и тест
      test_start = fold * fold_size
      test_end = test_start + fold_size

      test_indices = list(range(test_start, test_end))
      train_indices = list(range(0, test_start)) + list(range(test_end, n_draws))

      train_data = historical_draws[train_indices]
      test_data = historical_draws[test_indices]

      # Обучение на тренировочных данных
      self.fit(train_data)

      # Оценка на тестовых данных
      fold_likelihoods = []
      fold_hits = []

      for test_draw in test_data:
        # Правдоподобие
        likelihood = self.calculate_likelihood(test_draw)
        fold_likelihoods.append(likelihood)

        # Точность предсказания
        prediction = self.predict_next_draw(1, method='mean')[0]
        hits = len(set(prediction) & set(test_draw))
        fold_hits.append(hits / self.draws_size)

      likelihoods.extend(fold_likelihoods)
      accuracies.extend(fold_hits)

    return {
      'mean_log_likelihood': float(np.mean(likelihoods)),
      'std_log_likelihood': float(np.std(likelihoods)),
      'mean_accuracy': float(np.mean(accuracies)),
      'std_accuracy': float(np.std(accuracies)),
      'folds': folds
    }