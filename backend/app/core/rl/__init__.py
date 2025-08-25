"""
Модуль Reinforcement Learning для анализа лотерей
Содержит Q-Learning и DQN агентов для оптимизации стратегий
"""

from backend.app.core.rl.environment import LotteryEnvironment, LotteryState
from backend.app.core.rl.q_agent import QLearningAgent
from backend.app.core.rl.dqn_agent import DQNAgent, DQNNetwork
from backend.app.core.rl.state_encoder import StateEncoder, ActionEncoder
from backend.app.core.rl.reward_calculator import RewardCalculator, RewardScheme, ShapedRewardCalculator
from backend.app.core.rl.rl_generator import RLGenerator, RLGeneratorManager, GLOBAL_RL_MANAGER
from backend.app.core.rl.validation_utils import (
    RealisticRewardCalculator,
    PerformanceValidator,
    AdaptiveHyperparameters,
    ValidationMetrics
)
__all__ = [
  # Environment
  'LotteryEnvironment',
  'LotteryState',

  # Agents
  'QLearningAgent',
  'DQNAgent',
  'DQNNetwork',

  # Encoders
  'StateEncoder',
  'ActionEncoder',

  # Rewards
  'RewardCalculator',
  'RewardScheme',
  'ShapedRewardCalculator',

  # Generator
  'RLGenerator',
  'RLGeneratorManager',
  'GLOBAL_RL_MANAGER',
  'RealisticRewardCalculator',
    'PerformanceValidator',
    'AdaptiveHyperparameters',
    'ValidationMetrics'
]

# Версия модуля
__version__ = '1.0.0'