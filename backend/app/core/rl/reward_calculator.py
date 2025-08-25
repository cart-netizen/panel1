"""
Расчет наград для RL агента
Различные схемы вознаграждения для обучения
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class RewardScheme:
  """Схема вознаграждения"""
  name: str
  ticket_cost: float = 1.0

  # Награды за совпадения в поле 1
  match_2_f1: float = 2.0
  match_3_f1: float = 10.0
  match_4_f1: float = 100.0
  match_5_f1: float = 1000.0
  jackpot_f1: float = 10000.0

  # Награды за поле 2
  match_1_f2: float = 5.0
  match_all_f2: float = 50.0
  super_jackpot: float = 100000.0

  # Дополнительные бонусы
  hot_number_bonus: float = 0.1
  cold_number_penalty: float = -0.05
  diversity_bonus: float = 0.2
  pattern_bonus: float = 0.5


class RewardCalculator:
  """
  Калькулятор наград для различных схем лотереи
  """

  def __init__(self, lottery_config: Dict, scheme: Optional[RewardScheme] = None):
    """
    Args:
        lottery_config: Конфигурация лотереи
        scheme: Схема вознаграждения
    """
    self.lottery_config = lottery_config
    self.scheme = scheme or RewardScheme(name="default")

    self.field1_size = lottery_config['field1_size']
    self.field2_size = lottery_config['field2_size']

    # Статистика наград
    self.reward_history = []
    self.total_rewards = 0
    self.total_tickets = 0

    logger.info(f"✅ RewardCalculator инициализирован со схемой '{self.scheme.name}'")

  def calculate(self,
                predicted_f1: List[int],
                predicted_f2: List[int],
                actual_f1: List[int],
                actual_f2: List[int],
                state_features: Optional[Dict] = None) -> float:
    """
    Расчет награды за предсказание

    Args:
        predicted_f1: Предсказанные числа поля 1
        predicted_f2: Предсказанные числа поля 2
        actual_f1: Фактические числа поля 1
        actual_f2: Фактические числа поля 2
        state_features: Дополнительные признаки состояния

    Returns:
        Награда (может быть отрицательной)
    """
    # Базовая стоимость билета (отрицательная)
    reward = -self.scheme.ticket_cost

    # Подсчет совпадений
    matches_f1 = len(set(predicted_f1) & set(actual_f1))
    matches_f2 = len(set(predicted_f2) & set(actual_f2))

    # Награды за поле 1
    if matches_f1 >= 2:
      reward += self.scheme.match_2_f1
    if matches_f1 >= 3:
      reward += self.scheme.match_3_f1
    if matches_f1 >= 4:
      reward += self.scheme.match_4_f1
    if matches_f1 >= 5:
      reward += self.scheme.match_5_f1
    if matches_f1 == self.field1_size:
      reward += self.scheme.jackpot_f1
      logger.info(f"🎯 ДЖЕКПОТ в поле 1! Совпадений: {matches_f1}")

    # Награды за поле 2
    if matches_f2 >= 1 and matches_f1 >= 2:
      reward += self.scheme.match_1_f2
    if matches_f2 == self.field2_size and matches_f1 >= 3:
      reward += self.scheme.match_all_f2
    if matches_f2 == self.field2_size and matches_f1 == self.field1_size:
      reward += self.scheme.super_jackpot
      logger.info(f"💎 СУПЕР-ДЖЕКПОТ! Полное совпадение!")

    # Дополнительные бонусы на основе признаков состояния
    if state_features:
      reward = self._apply_feature_bonuses(reward, predicted_f1, predicted_f2, state_features)

    # Сохраняем статистику
    self.reward_history.append(reward)
    self.total_rewards += reward
    self.total_tickets += 1

    return reward

  def _apply_feature_bonuses(self, base_reward: float,
                             predicted_f1: List[int],
                             predicted_f2: List[int],
                             state_features: Dict) -> float:
    """
    Применение дополнительных бонусов на основе признаков

    Args:
        base_reward: Базовая награда
        predicted_f1: Предсказанные числа поля 1
        predicted_f2: Предсказанные числа поля 2
        state_features: Признаки состояния

    Returns:
        Модифицированная награда
    """
    reward = base_reward

    # Бонус за использование горячих чисел
    if 'hot_numbers' in state_features:
      hot_numbers = state_features['hot_numbers']
      hot_count = len(set(predicted_f1) & set(hot_numbers))
      reward += hot_count * self.scheme.hot_number_bonus

    # Штраф за слишком много холодных чисел
    if 'cold_numbers' in state_features:
      cold_numbers = state_features['cold_numbers']
      cold_count = len(set(predicted_f1) & set(cold_numbers))
      if cold_count > self.field1_size // 2:
        reward += cold_count * self.scheme.cold_number_penalty

    # Бонус за разнообразие
    if 'diversity_index' in state_features:
      diversity = state_features['diversity_index']
      if diversity > 0.7:
        reward += self.scheme.diversity_bonus

    # Бонус за паттерны
    if self._check_patterns(predicted_f1):
      reward += self.scheme.pattern_bonus

    return reward

  def _check_patterns(self, numbers: List[int]) -> bool:
    """
    Проверка на наличие паттернов в числах

    Args:
        numbers: Список чисел

    Returns:
        True если найден интересный паттерн
    """
    if len(numbers) < 3:
      return False

    sorted_nums = sorted(numbers)

    # Проверка на арифметическую прогрессию
    diffs = [sorted_nums[i + 1] - sorted_nums[i] for i in range(len(sorted_nums) - 1)]
    if len(set(diffs)) == 1:  # Все разности одинаковые
      return True

    # Проверка на последовательные числа
    consecutive_count = 1
    for i in range(len(sorted_nums) - 1):
      if sorted_nums[i + 1] - sorted_nums[i] == 1:
        consecutive_count += 1
        if consecutive_count >= 3:
          return True
      else:
        consecutive_count = 1

    return False

  def calculate_expected_value(self, num_simulations: int = 10000) -> float:
    """
    Расчет математического ожидания на основе истории

    Args:
        num_simulations: Количество симуляций

    Returns:
        Математическое ожидание
    """
    if not self.reward_history:
      return -self.scheme.ticket_cost

    # Используем последние награды для оценки
    recent_rewards = self.reward_history[-min(num_simulations, len(self.reward_history)):]
    return np.mean(recent_rewards)

  def get_statistics(self) -> Dict:
    """
    Получение статистики наград

    Returns:
        Словарь со статистикой
    """
    if not self.reward_history:
      return {
        'total_tickets': 0,
        'total_rewards': 0,
        'average_reward': 0,
        'max_reward': 0,
        'min_reward': 0,
        'roi': 0,
        'win_rate': 0
      }

    rewards = np.array(self.reward_history)
    wins = rewards > 0

    return {
      'total_tickets': self.total_tickets,
      'total_rewards': self.total_rewards,
      'average_reward': np.mean(rewards),
      'max_reward': np.max(rewards),
      'min_reward': np.min(rewards),
      'std_reward': np.std(rewards),
      'roi': (self.total_rewards / (
            self.total_tickets * self.scheme.ticket_cost)) * 100 if self.total_tickets > 0 else 0,
      'win_rate': np.mean(wins) * 100,
      'expected_value': self.calculate_expected_value()
    }

  def reset_statistics(self):
    """Сброс накопленной статистики"""
    self.reward_history = []
    self.total_rewards = 0
    self.total_tickets = 0
    logger.info("📊 Статистика наград сброшена")


class ShapedRewardCalculator(RewardCalculator):
  """
  Калькулятор с reward shaping для ускорения обучения
  """

  def __init__(self, lottery_config: Dict):
    super().__init__(lottery_config)
    self.scheme.name = "shaped"

    # Дополнительные параметры для shaping
    self.proximity_weight = 0.01  # Вес за близость к правильным числам
    self.improvement_weight = 0.05  # Вес за улучшение
    self.previous_matches = 0

  def calculate(self,
                predicted_f1: List[int],
                predicted_f2: List[int],
                actual_f1: List[int],
                actual_f2: List[int],
                state_features: Optional[Dict] = None) -> float:
    """
    Расчет shaped награды с дополнительными сигналами
    """
    # Базовая награда
    base_reward = super().calculate(predicted_f1, predicted_f2, actual_f1, actual_f2, state_features)

    # Дополнительный shaping
    shaped_reward = base_reward

    # Награда за близость к правильным числам
    proximity_bonus = self._calculate_proximity_bonus(predicted_f1, actual_f1)
    shaped_reward += proximity_bonus * self.proximity_weight

    # Награда за улучшение
    current_matches = len(set(predicted_f1) & set(actual_f1))
    if current_matches > self.previous_matches:
      shaped_reward += (current_matches - self.previous_matches) * self.improvement_weight
    self.previous_matches = current_matches

    return shaped_reward

  def _calculate_proximity_bonus(self, predicted: List[int], actual: List[int]) -> float:
    """
    Бонус за близость предсказанных чисел к фактическим
    """
    proximity_sum = 0

    for pred_num in predicted:
      # Находим минимальное расстояние до любого правильного числа
      min_distance = min(abs(pred_num - act_num) for act_num in actual)
      # Инвертируем расстояние в бонус
      proximity_sum += 1.0 / (1.0 + min_distance)

    return proximity_sum