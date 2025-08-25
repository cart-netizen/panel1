"""
Реалистичная система наград для RL агентов
Включает:
1. Математически корректные награды на основе реальных вероятностей
2. Систему валидации с разделением данных
3. Адаптивные гиперпараметры для разных лотерей
4. Метрики производительности
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from datetime import datetime
from math import comb
import json
import os

logger = logging.getLogger(__name__)


@dataclass
class ValidationMetrics:
  """Метрики валидации для оценки производительности"""
  win_rate: float
  average_reward: float
  roi: float  # Return on Investment
  sharpe_ratio: float  # Risk-adjusted return
  max_drawdown: float
  total_games: int
  profitable_games: int
  biggest_win: float
  biggest_loss: float


class RealisticRewardCalculator:
  """
  Реалистичная система расчета наград
  Основана на реальных призовых схемах лотерей
  """

  def __init__(self, lottery_config: Dict):
    self.field1_size = lottery_config['field1_size']
    self.field2_size = lottery_config['field2_size']
    self.field1_max = lottery_config['field1_max']
    self.field2_max = lottery_config['field2_max']

    # Стоимость билета
    self.ticket_cost = 10.0  # Базовая стоимость в условных единицах

    # Вычисляем вероятности для корректных наград
    self._compute_probabilities()
    self._setup_prize_structure()

    logger.info(f"✅ RealisticRewardCalculator инициализирован")
    logger.info(f"   Лотерея: {self.field1_size}x{self.field1_max} + {self.field2_size}x{self.field2_max}")
    logger.info(f"   Стоимость билета: {self.ticket_cost}")

  def _compute_probabilities(self):
    """Вычисляем вероятности совпадений"""
    # Вероятности для поля 1
    self.field1_probabilities = {}
    total_combinations = comb(self.field1_max, self.field1_size)

    for matches in range(self.field1_size + 1):
      if matches <= self.field1_size:
        # Вероятность угадать exactly 'matches' чисел
        prob = (comb(self.field1_size, matches) *
                comb(self.field1_max - self.field1_size, self.field1_size - matches)) / total_combinations
        self.field1_probabilities[matches] = prob

    # Вероятности для поля 2 (проще, так как обычно меньше чисел)
    self.field2_probabilities = {}
    if self.field2_size == 1:
      # Для одного числа
      self.field2_probabilities[0] = (self.field2_max - 1) / self.field2_max
      self.field2_probabilities[1] = 1 / self.field2_max
    else:
      # Для множественного выбора
      total_combinations_f2 = comb(self.field2_max, self.field2_size)
      for matches in range(self.field2_size + 1):
        prob = (comb(self.field2_size, matches) *
                comb(self.field2_max - self.field2_size, self.field2_size - matches)) / total_combinations_f2
        self.field2_probabilities[matches] = prob

  def _setup_prize_structure(self):
    """Настраиваем реалистичную призовую структуру"""
    # Основываем на реальных лотереях с отрицательным матожиданием

    if self.field1_size == 4:  # 4x20 лотерея
      self.prize_structure = {
        (4, 4): 3333333,  # Джекпот: все 4 + бонус
        (4, 3): 2300,  # Джекпот: все 4 + бонус
        (4, 2): 650,  # Джекпот: все 4 + бонус
        (4, 1): 330,  # Джекпот: все 4 + бонус
        (4, 0): 1400,  # Все 4 без бонуса
        (3, 3): 700,  # 3 + бонус
        (3, 2): 70,  # 3 + бонус
        (3, 1): 30,  # 3 + бонус
        (3, 0): 60,  # 3 без бонуса
        (2, 2): 20,  # 3 без бонуса

        (2, 1): 10,  # 2 + бонус
        (2, 0): 10,  # 2 без бонуса (не выигрывает)
      }
    elif self.field1_size == 5:  # 5x36 лотерея (сложнее)
      self.prize_structure = {
        (5, 1): 290000,  # Суперджекпот
        (5, 0): 145000,  # Джекпот
        # (4, 1): 10000,  # 4 + бонус
        (4, 0): 1000,  # 4 без бонуса
        # (3, 1): 100,  # 3 + бонус
        (3, 0): 100,  # 3 без бонуса
        # (2, 1): 5,  # 2 + бонус
        (2, 0): 10,  # Не выигрывает
      }
    else:
      # Универсальная схема для других конфигураций
      max_prize = 100000
      self.prize_structure = {}
      for f1_matches in range(self.field1_size + 1):
        for f2_matches in range(self.field2_size + 1):
          if f1_matches >= 2:  # Минимум для выигрыша
            multiplier = (f1_matches ** 3) * (1 + f2_matches)
            prize = min(max_prize, int(self.ticket_cost * multiplier))
            self.prize_structure[(f1_matches, f2_matches)] = prize
          else:
            self.prize_structure[(f1_matches, f2_matches)] = 0

  def calculate_reward(self, pred_field1: List[int], pred_field2: List[int],
                       actual_field1: List[int], actual_field2: List[int]) -> float:
    """
    Реалистичный расчет награды

    Returns:
        Награда (может быть отрицательной)
    """
    # Защита от пустых данных
    if not actual_field1 or not actual_field2:
      return -self.ticket_cost

    # Подсчет совпадений
    matches_f1 = len(set(pred_field1) & set(actual_field1))
    matches_f2 = len(set(pred_field2) & set(actual_field2))

    # Получаем приз по таблице
    prize = self.prize_structure.get((matches_f1, matches_f2), 0)

    # Итоговая награда = приз - стоимость билета
    reward = prize - self.ticket_cost

    # Логирование редких событий
    if prize > self.ticket_cost * 10:
      logger.debug(f"🎉 Крупный выигрыш: {matches_f1}+{matches_f2} = {prize} (награда: {reward})")

    return reward

  def get_expected_value(self) -> float:
    """Вычисляет математическое ожидание (должно быть отрицательным)"""
    expected_value = -self.ticket_cost  # Начинаем с стоимости билета

    for (f1_matches, f2_matches), prize in self.prize_structure.items():
      prob_f1 = self.field1_probabilities.get(f1_matches, 0)
      prob_f2 = self.field2_probabilities.get(f2_matches, 0)
      combined_prob = prob_f1 * prob_f2

      expected_value += prize * combined_prob

    return expected_value

  def get_statistics(self) -> Dict[str, Any]:
    """Возвращает статистику по призовой структуре"""
    ev = self.get_expected_value()
    rtp = (ev + self.ticket_cost) / self.ticket_cost  # Return to Player

    return {
      'expected_value': ev,
      'return_to_player': rtp,
      'house_edge': 1 - rtp,
      'ticket_cost': self.ticket_cost,
      'max_prize': max(self.prize_structure.values()),
      'prize_levels': len([p for p in self.prize_structure.values() if p > 0])
    }


class TrainValidationSplitter:
  """Разделение данных на обучение/валидацию/тест"""

  @staticmethod
  def split_data(df: pd.DataFrame, train_ratio: float = 0.7,
                 val_ratio: float = 0.15, test_ratio: float = 0.15) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Разделяет данные с сохранением временного порядка

    Args:
        df: Исходные данные (отсортированы по времени)
        train_ratio: Доля обучающих данных
        val_ratio: Доля валидационных данных
        test_ratio: Доля тестовых данных

    Returns:
        (train_df, val_df, test_df)
    """
    assert abs(train_ratio + val_ratio + test_ratio - 1.0) < 1e-6, "Сумма долей должна быть 1.0"

    n = len(df)
    train_end = int(n * train_ratio)
    val_end = int(n * (train_ratio + val_ratio))

    # Берем данные в хронологическом порядке (свежие - для теста)
    train_df = df.iloc[:train_end].copy()
    val_df = df.iloc[train_end:val_end].copy()
    test_df = df.iloc[val_end:].copy()

    logger.info(f"📊 Разделение данных:")
    logger.info(f"   Обучение: {len(train_df)} тиражей ({train_ratio:.1%})")
    logger.info(f"   Валидация: {len(val_df)} тиражей ({val_ratio:.1%})")
    logger.info(f"   Тест: {len(test_df)} тиражей ({test_ratio:.1%})")

    return train_df, val_df, test_df


class PerformanceValidator:
  """Валидация производительности агентов"""

  def __init__(self, reward_calculator: RealisticRewardCalculator):
    self.reward_calculator = reward_calculator

  def validate_agent(self, agent, val_df: pd.DataFrame, lottery_config: Dict,
                     num_episodes: int = 100) -> ValidationMetrics:
    """
    Валидация агента на отдельных данных

    Args:
        agent: Обученный агент (Q-Learning или DQN)
        val_df: Валидационные данные
        lottery_config: Конфигурация лотереи
        num_episodes: Количество эпизодов валидации

    Returns:
        Метрики производительности
    """
    from backend.app.core.rl.environment import LotteryEnvironment

    # Создаем среду для валидации
    env = LotteryEnvironment(val_df, lottery_config)

    rewards = []
    wins = 0
    total_invested = 0
    total_won = 0

    for episode in range(num_episodes):
      state = env.reset()
      episode_reward = 0
      episode_invested = 0
      episode_won = 0

      done = False
      while not done:
        # Получаем действие от агента (без обучения)
        if hasattr(agent, 'choose_action'):
          action = agent.choose_action(state, training=False)
        else:
          action = agent.predict(state)

        next_state, reward, done, info = env.step(action)

        episode_reward += reward
        episode_invested += self.reward_calculator.ticket_cost

        if reward > 0:
          episode_won += reward + self.reward_calculator.ticket_cost
          wins += 1

        state = next_state

      rewards.append(episode_reward)
      total_invested += episode_invested
      total_won += episode_won

    # Вычисляем метрики
    avg_reward = np.mean(rewards)
    roi = ((total_won - total_invested) / total_invested * 100) if total_invested > 0 else -100

    # Sharpe ratio (риск-скорректированная доходность)
    reward_std = np.std(rewards) if len(rewards) > 1 else 1
    sharpe_ratio = avg_reward / reward_std if reward_std > 0 else 0

    # Maximum drawdown
    cumulative_rewards = np.cumsum(rewards)
    running_max = np.maximum.accumulate(cumulative_rewards)
    drawdown = (cumulative_rewards - running_max)
    max_drawdown = np.min(drawdown)

    return ValidationMetrics(
      win_rate=wins / (num_episodes * len(val_df)) * 100 if num_episodes > 0 else 0,
      average_reward=avg_reward,
      roi=roi,
      sharpe_ratio=sharpe_ratio,
      max_drawdown=max_drawdown,
      total_games=num_episodes * len(val_df),
      profitable_games=wins,
      biggest_win=np.max(rewards) if rewards else 0,
      biggest_loss=np.min(rewards) if rewards else 0
    )


class AdaptiveHyperparameters:
  """Адаптивные гиперпараметры для разных типов лотерей"""

  @staticmethod
  def get_config(lottery_type: str, lottery_config: Dict) -> Dict[str, Any]:
    """
    Возвращает оптимальные гиперпараметры для конкретной лотереи

    Args:
        lottery_type: Тип лотереи (4x20, 5x36plus, etc.)
        lottery_config: Конфигурация лотереи

    Returns:
        Словарь с гиперпараметрами
    """
    field1_size = lottery_config['field1_size']
    field1_max = lottery_config['field1_max']
    complexity = field1_size * field1_max  # Мера сложности

    if complexity <= 80:  # Простые лотереи (типа 4x20)
      return {
        'q_learning': {
          'learning_rate': 0.1,
          'discount_factor': 0.95,
          'epsilon_start': 1.0,
          'epsilon_end': 0.01,
          'epsilon_decay': 0.995,
          'episodes': 1500,
          'memory_limit': 50000
        },
        'dqn': {
          'learning_rate': 0.001,
          'discount_factor': 0.99,
          'epsilon_start': 1.0,
          'epsilon_end': 0.05,
          'epsilon_decay': 0.995,
          'episodes': 800,
          'batch_size': 32,
          'memory_size': 10000,
          'target_update_freq': 100,
          'hidden_size': 256
        }
      }

    elif complexity <= 180:  # Средние лотереи (типа 5x36)
      return {
        'q_learning': {
          'learning_rate': 0.05,  # Меньше для стабильности
          'discount_factor': 0.99,
          'epsilon_start': 1.0,
          'epsilon_end': 0.02,
          'epsilon_decay': 0.998,
          'episodes': 2000,
          'memory_limit': 100000
        },
        'dqn': {
          'learning_rate': 0.0005,  # Меньше learning rate
          'discount_factor': 0.99,
          'epsilon_start': 1.0,
          'epsilon_end': 0.08,
          'epsilon_decay': 0.998,
          'episodes': 1200,  # Больше эпизодов
          'batch_size': 64,  # Больший батч
          'memory_size': 15000,
          'target_update_freq': 200,
          'hidden_size': 512  # Больше нейронов
        }
      }

    else:  # Сложные лотереи
      return {
        'q_learning': {
          'learning_rate': 0.01,
          'discount_factor': 0.99,
          'epsilon_start': 1.0,
          'epsilon_end': 0.05,
          'epsilon_decay': 0.999,
          'episodes': 3000,
          'memory_limit': 200000
        },
        'dqn': {
          'learning_rate': 0.0001,
          'discount_factor': 0.99,
          'epsilon_start': 1.0,
          'epsilon_end': 0.1,
          'epsilon_decay': 0.999,
          'episodes': 2000,
          'batch_size': 128,
          'memory_size': 25000,
          'target_update_freq': 300,
          'hidden_size': 1024
        }
      }

  @staticmethod
  def save_config(lottery_type: str, config: Dict, filepath: str):
    """Сохранение конфигурации в файл"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    with open(filepath, 'w') as f:
      json.dump({
        'lottery_type': lottery_type,
        'config': config,
        'created_at': datetime.now().isoformat()
      }, f, indent=2)

    logger.info(f"💾 Конфигурация сохранена: {filepath}")


# Интеграция в LotteryEnvironment
def _calculate_reward_realistic(self, pred_field1: List[int], pred_field2: List[int],
                                actual_field1: List[int], actual_field2: List[int]) -> float:
  """
  ЗАМЕНА для метода _calculate_reward в LotteryEnvironment

  Использует реалистичную систему наград
  """
  if not hasattr(self, '_reward_calculator'):
    self._reward_calculator = RealisticRewardCalculator(self.lottery_config)

    # Выводим статистику один раз при инициализации
    stats = self._reward_calculator.get_statistics()
    logger.info(f"📊 Статистика наград:")
    logger.info(f"   Матожидание: {stats['expected_value']:.2f}")
    logger.info(f"   RTP: {stats['return_to_player']:.1%}")
    logger.info(f"   House Edge: {stats['house_edge']:.1%}")
    logger.info(f"   Макс. приз: {stats['max_prize']:,.0f}")

  return self._reward_calculator.calculate_reward(pred_field1, pred_field2, actual_field1, actual_field2)


# Пример использования валидации
def validate_trained_models(lottery_type: str, lottery_config: Dict, df_full: pd.DataFrame):
  """
  Пример функции для валидации обученных моделей
  """
  # Разделяем данные
  train_df, val_df, test_df = TrainValidationSplitter.split_data(df_full)

  # Создаем валидатор
  reward_calc = RealisticRewardCalculator(lottery_config)
  validator = PerformanceValidator(reward_calc)

  # Загружаем обученные модели
  from backend.app.core.rl.rl_generator import GLOBAL_RL_MANAGER
  generator = GLOBAL_RL_MANAGER.get_generator(lottery_type, lottery_config)

  if generator.q_trained:
    # Валидируем Q-Learning
    q_metrics = validator.validate_agent(generator.q_agent, val_df, lottery_config)

    logger.info(f"📈 Q-Learning валидация:")
    logger.info(f"   Win rate: {q_metrics.win_rate:.2f}%")
    logger.info(f"   Средняя награда: {q_metrics.average_reward:.2f}")
    logger.info(f"   ROI: {q_metrics.roi:.2f}%")
    logger.info(f"   Sharpe ratio: {q_metrics.sharpe_ratio:.3f}")

  if generator.dqn_trained:
    # Валидируем DQN
    dqn_metrics = validator.validate_agent(generator.dqn_agent, val_df, lottery_config)

    logger.info(f"🧠 DQN валидация:")
    logger.info(f"   Win rate: {dqn_metrics.win_rate:.2f}%")
    logger.info(f"   Средняя награда: {dqn_metrics.average_reward:.2f}")
    logger.info(f"   ROI: {dqn_metrics.roi:.2f}%")
    logger.info(f"   Sharpe ratio: {dqn_metrics.sharpe_ratio:.3f}")