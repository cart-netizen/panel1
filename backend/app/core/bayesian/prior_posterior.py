"""
Управление априорными и апостериорными распределениями
для байесовского анализа лотерей
"""

import numpy as np
import pandas as pd
from scipy import stats
from scipy.special import gammaln, digamma
from typing import Dict, List, Tuple, Optional, Union
import logging
import json
import pickle

logger = logging.getLogger(__name__)


class PriorPosteriorManager:
  """Менеджер для работы с априорными и апостериорными распределениями"""

  def __init__(self, num_categories: int, prior_type: str = 'uniform'):
    """
    Args:
        num_categories: Количество категорий (чисел в лотерее)
        prior_type: Тип априорного распределения ('uniform', 'jeffreys', 'custom')
    """
    self.num_categories = num_categories
    self.prior_type = prior_type

    # Инициализация априорных параметров альфа
    self.prior_alpha = self._initialize_prior(prior_type)
    self.posterior_alpha = self.prior_alpha.copy()

    # История обновлений
    self.update_history = []
    self.observation_count = 0

    logger.info(f"Инициализирован менеджер с {num_categories} категориями, prior={prior_type}")

  def _initialize_prior(self, prior_type: str) -> np.ndarray:
    """
    Инициализация априорного распределения

    Args:
        prior_type: Тип априорного распределения

    Returns:
        Вектор параметров альфа для распределения Дирихле
    """
    if prior_type == 'uniform':
      # Равномерное априорное (неинформативное)
      alpha = np.ones(self.num_categories)
    elif prior_type == 'jeffreys':
      # Априорное Джеффриса (слабо информативное)
      alpha = np.ones(self.num_categories) * 0.5
    elif prior_type == 'weakly_informative':
      # Слабо информативное
      alpha = np.ones(self.num_categories) * 2.0
    else:
      # По умолчанию - равномерное
      alpha = np.ones(self.num_categories)

    logger.info(f"Априорное распределение: alpha_sum={alpha.sum():.2f}, alpha_mean={alpha.mean():.2f}")
    return alpha

  def update_posterior(self, observations: Union[List[int], np.ndarray]) -> np.ndarray:
    """
    Обновление апостериорного распределения на основе наблюдений

    Args:
        observations: Наблюдаемые числа (индексы категорий)

    Returns:
        Обновленные параметры альфа
    """
    # Подсчет частот для каждой категории
    counts = np.zeros(self.num_categories)
    for obs in observations:
      if 0 <= obs < self.num_categories:
        counts[obs] += 1

    # Байесовское обновление: posterior_alpha = prior_alpha + counts
    self.posterior_alpha = self.prior_alpha + counts
    self.observation_count += len(observations)

    # Сохранение в историю
    self.update_history.append({
      'observations': len(observations),
      'counts': counts.tolist(),
      'posterior_alpha_sum': float(self.posterior_alpha.sum()),
      'posterior_alpha_mean': float(self.posterior_alpha.mean())
    })

    logger.info(f"Обновлено апостериорное: {len(observations)} наблюдений, "
                f"alpha_sum={self.posterior_alpha.sum():.2f}")

    return self.posterior_alpha

  def get_posterior_mean(self) -> np.ndarray:
    """
    Получение среднего апостериорного распределения

    Returns:
        Вектор вероятностей для каждой категории
    """
    # Среднее распределения Дирихле: E[p_i] = alpha_i / sum(alpha)
    return self.posterior_alpha / self.posterior_alpha.sum()

  def get_posterior_variance(self) -> np.ndarray:
    """
    Получение дисперсии апостериорного распределения

    Returns:
        Вектор дисперсий для каждой категории
    """
    alpha_sum = self.posterior_alpha.sum()
    mean = self.posterior_alpha / alpha_sum

    # Дисперсия распределения Дирихле
    variance = (mean * (1 - mean)) / (alpha_sum + 1)
    return variance

  def get_posterior_mode(self) -> np.ndarray:
    """
    Получение моды апостериорного распределения

    Returns:
        Вектор наиболее вероятных значений
    """
    # Мода существует только если все alpha_i > 1
    if np.all(self.posterior_alpha > 1):
      mode = (self.posterior_alpha - 1) / (self.posterior_alpha.sum() - self.num_categories)
      return mode
    else:
      # Если мода не существует, возвращаем среднее
      return self.get_posterior_mean()

  def get_credible_intervals(self, confidence: float = 0.95) -> Dict[str, np.ndarray]:
    """
    Получение доверительных интервалов для вероятностей

    Args:
        confidence: Уровень доверия (0.95 для 95% интервала)

    Returns:
        Словарь с нижними и верхними границами интервалов
    """
    # Используем бета-распределение для маргинальных распределений
    alpha_sum = self.posterior_alpha.sum()
    lower_bounds = []
    upper_bounds = []

    alpha_level = (1 - confidence) / 2

    for i in range(self.num_categories):
      # Маргинальное распределение p_i ~ Beta(alpha_i, sum(alpha) - alpha_i)
      a = self.posterior_alpha[i]
      b = alpha_sum - a

      lower = stats.beta.ppf(alpha_level, a, b)
      upper = stats.beta.ppf(1 - alpha_level, a, b)

      lower_bounds.append(lower)
      upper_bounds.append(upper)

    return {
      'lower': np.array(lower_bounds),
      'upper': np.array(upper_bounds),
      'mean': self.get_posterior_mean()
    }

  def sample_from_posterior(self, n_samples: int = 1000) -> np.ndarray:
    """
    Сэмплирование из апостериорного распределения Дирихле

    Args:
        n_samples: Количество сэмплов

    Returns:
        Матрица сэмплов (n_samples x num_categories)
    """
    return np.random.dirichlet(self.posterior_alpha, size=n_samples)

  def calculate_entropy(self) -> float:
    """
    Расчет энтропии апостериорного распределения Дирихле

    Returns:
        Значение энтропии
    """
    alpha_sum = self.posterior_alpha.sum()
    k = self.num_categories

    # H(Dir(alpha)) = log(B(alpha)) + (alpha_0 - k) * psi(alpha_0) - sum((alpha_i - 1) * psi(alpha_i))
    log_beta = np.sum(gammaln(self.posterior_alpha)) - gammaln(alpha_sum)

    entropy = log_beta + (alpha_sum - k) * digamma(alpha_sum)
    entropy -= np.sum((self.posterior_alpha - 1) * digamma(self.posterior_alpha))

    return float(entropy)

  def calculate_kl_divergence(self, other_alpha: np.ndarray) -> float:
    """
    Расчет KL-дивергенции между текущим и другим распределением Дирихле

    Args:
        other_alpha: Параметры другого распределения Дирихле

    Returns:
        KL(current || other)
    """
    # KL(Dir(alpha) || Dir(beta))
    alpha = self.posterior_alpha
    beta = other_alpha

    alpha_sum = alpha.sum()
    beta_sum = beta.sum()

    # Log normalizing constants
    log_b_alpha = np.sum(gammaln(alpha)) - gammaln(alpha_sum)
    log_b_beta = np.sum(gammaln(beta)) - gammaln(beta_sum)

    kl = log_b_beta - log_b_alpha
    kl += np.sum((alpha - beta) * (digamma(alpha) - digamma(alpha_sum)))

    return float(kl)

  def reset_to_prior(self):
    """Сброс апостериорного распределения к априорному"""
    self.posterior_alpha = self.prior_alpha.copy()
    self.observation_count = 0
    self.update_history = []
    logger.info("Апостериорное распределение сброшено к априорному")

  def save_state(self, filepath: str):
    """
    Сохранение состояния менеджера

    Args:
        filepath: Путь для сохранения
    """
    state = {
      'num_categories': self.num_categories,
      'prior_type': self.prior_type,
      'prior_alpha': self.prior_alpha.tolist(),
      'posterior_alpha': self.posterior_alpha.tolist(),
      'observation_count': self.observation_count,
      'update_history': self.update_history
    }

    with open(filepath, 'w') as f:
      json.dump(state, f, indent=2)

    logger.info(f"Состояние сохранено в {filepath}")

  def load_state(self, filepath: str):
    """
    Загрузка состояния менеджера

    Args:
        filepath: Путь к файлу состояния
    """
    with open(filepath, 'r') as f:
      state = json.load(f)

    self.num_categories = state['num_categories']
    self.prior_type = state['prior_type']
    self.prior_alpha = np.array(state['prior_alpha'])
    self.posterior_alpha = np.array(state['posterior_alpha'])
    self.observation_count = state['observation_count']
    self.update_history = state['update_history']

    logger.info(f"Состояние загружено из {filepath}")

  def get_summary_statistics(self) -> Dict:
    """
    Получение сводной статистики

    Returns:
        Словарь со статистикой
    """
    mean = self.get_posterior_mean()
    variance = self.get_posterior_variance()
    mode = self.get_posterior_mode()

    return {
      'observation_count': self.observation_count,
      'prior_type': self.prior_type,
      'posterior_concentration': float(self.posterior_alpha.sum()),
      'entropy': self.calculate_entropy(),
      'mean_probability': float(mean.mean()),
      'max_probability': float(mean.max()),
      'min_probability': float(mean.min()),
      'most_likely_category': int(np.argmax(mean)),
      'least_likely_category': int(np.argmin(mean)),
      'variance_mean': float(variance.mean()),
      'effective_sample_size': float(self.posterior_alpha.sum() - self.num_categories)
    }