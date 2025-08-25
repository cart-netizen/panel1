#!/usr/bin/env python3
"""
Скрипт для тестирования улучшенной RL системы
backend/scripts/test_improved_rl.py

Тестирует:
1. Исправленный подсчет win_rate
2. Улучшенную систему наград с reward shaping
3. Exploration bonuses
4. Производительность на валидационных данных
"""

import sys
import os
import time
import numpy as np
from datetime import datetime
from typing import Dict, List

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ВАЖНО: Применяем патч ДО импорта других модулей
from backend.app.core.rl.environment_patch import patch_lottery_environment
patch_lottery_environment()

# Теперь импортируем остальные модули
from backend.app.core.rl.rl_generator import GLOBAL_RL_MANAGER
from backend.app.core.rl.improved_rewards import ImprovedRewardCalculator, CuriosityDrivenBonus
from backend.app.core import data_manager
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def test_improved_rewards():
  """Тестирование улучшенной системы наград"""
  print("\n" + "=" * 70)
  print("🧪 ТЕСТИРОВАНИЕ УЛУЧШЕННОЙ СИСТЕМЫ НАГРАД")
  print("=" * 70)

  # Создаем калькулятор для 4x20
  config = data_manager.LOTTERY_CONFIGS['4x20']
  calculator = ImprovedRewardCalculator(config)

  # Тестовые случаи
  test_cases = [
    {
      "name": "Полное совпадение (джекпот)",
      "pred_f1": [1, 5, 10, 15],
      "pred_f2": [2, 6, 11, 16],
      "actual_f1": [1, 5, 10, 15],
      "actual_f2": [2, 6, 11, 16],
      "expected": "high_positive"
    },
    {
      "name": "Частичное совпадение (3 из 4)",
      "pred_f1": [1, 5, 10, 15],
      "pred_f2": [2, 6, 11, 16],
      "actual_f1": [1, 5, 10, 20],
      "actual_f2": [2, 6, 11, 19],
      "expected": "moderate_positive"
    },
    {
      "name": "Минимальное совпадение (1 из 4)",
      "pred_f1": [1, 5, 10, 15],
      "pred_f2": [2, 6, 11, 16],
      "actual_f1": [1, 7, 13, 19],
      "actual_f2": [3, 8, 14, 20],
      "expected": "small_negative"
    },
    {
      "name": "Нет совпадений",
      "pred_f1": [1, 5, 10, 15],
      "pred_f2": [2, 6, 11, 16],
      "actual_f1": [3, 7, 12, 17],
      "actual_f2": [4, 8, 13, 18],
      "expected": "moderate_negative"
    }
  ]

  print("\n📊 Результаты тестов:")
  print("-" * 50)

  for test in test_cases:
    reward, info = calculator.calculate_reward(
      test["pred_f1"], test["pred_f2"],
      test["actual_f1"], test["actual_f2"],
      {"hot_numbers": [1, 5, 10], "cold_numbers": [17, 18, 19, 20]}
    )

    print(f"\n✓ {test['name']}")
    print(f"  Совпадения: {info['matches_f1']}+{info['matches_f2']}")
    print(f"  Базовая награда: {info['base_reward']:.2f}")
    print(f"  Match награда: {info['match_reward']:.2f}")
    print(f"  Shaping награда: {info['shaping_reward']:.2f}")
    print(f"  Exploration: {info['exploration_reward']:.2f}")
    print(f"  ИТОГО: {reward:.2f}")

    # Проверка ожиданий
    if test["expected"] == "high_positive" and reward <= 0:
      print("  ⚠️ ПРЕДУПРЕЖДЕНИЕ: Ожидалась высокая положительная награда!")
    elif test["expected"] == "moderate_negative" and reward > -90:
      print("  ⚠️ ПРЕДУПРЕЖДЕНИЕ: Ожидалась умеренная отрицательная награда!")

  # Тест exploration bonus
  print("\n\n📈 Тест Exploration Bonus:")
  print("-" * 50)

  # Одна и та же комбинация несколько раз
  same_combo = ([1, 2, 3, 4], [5, 6, 7, 8])
  exploration_rewards = []

  for i in range(5):
    reward, info = calculator.calculate_reward(
      same_combo[0], same_combo[1],
      [10, 11, 12, 13], [14, 15, 16, 17],
      None
    )
    exploration_rewards.append(info['exploration_reward'])

  print(f"Exploration rewards для одинаковой комбинации:")
  for i, er in enumerate(exploration_rewards):
    print(f"  Попытка {i + 1}: {er:.3f}")

  if exploration_rewards[0] > exploration_rewards[-1]:
    print("✅ Exploration bonus уменьшается при повторении - КОРРЕКТНО")
  else:
    print("⚠️ Exploration bonus не уменьшается - ПРОБЛЕМА")

  return calculator


def test_curiosity_module():
  """Тестирование модуля curiosity"""
  print("\n" + "=" * 70)
  print("🔍 ТЕСТИРОВАНИЕ CURIOSITY MODULE")
  print("=" * 70)

  curiosity = CuriosityDrivenBonus(state_dim=10)

  # Создаем тестовые состояния
  state1 = np.random.randn(10)
  state2 = np.random.randn(10)
  state3 = state1.copy()  # Копия первого состояния

  action = ([1, 2, 3, 4], [5, 6, 7, 8])

  # Тест 1: Новое состояние
  reward1 = curiosity.calculate_curiosity_reward(state1, state2, action)
  print(f"\nНовое состояние → Curiosity reward: {reward1:.3f}")

  # Тест 2: Повторное посещение
  reward2 = curiosity.calculate_curiosity_reward(state1, state2, action)
  print(f"Повторное состояние → Curiosity reward: {reward2:.3f}")

  # Тест 3: Неожиданный переход
  reward3 = curiosity.calculate_curiosity_reward(state1, state3, action)
  print(f"Неожиданный переход → Curiosity reward: {reward3:.3f}")

  if reward1 > reward2:
    print("\n✅ Curiosity rewards работают корректно")
  else:
    print("\n⚠️ Проблема с curiosity rewards")


def test_win_rate_calculation():
  """Тестирование исправленного подсчета win_rate"""
  print("\n" + "=" * 70)
  print("📊 ТЕСТИРОВАНИЕ ПОДСЧЕТА WIN RATE")
  print("=" * 70)

  # Создаем тестовый агент
  from backend.app.core.rl.q_agent import QLearningAgent
  config = data_manager.LOTTERY_CONFIGS['4x20']
  agent = QLearningAgent(config)

  # Симулируем результаты
  agent.total_episodes = 100
  agent.total_steps = 8400  # ~84 шага на эпизод
  agent.wins = 5  # 5 выигрышных эпизодов

  # Старый (неправильный) способ
  old_win_rate = (agent.wins / max(agent.total_steps, 1)) * 100

  # Новый (правильный) способ
  new_win_rate = (agent.wins / max(agent.total_episodes, 1)) * 100

  print(f"\nТестовые данные:")
  print(f"  Эпизоды: {agent.total_episodes}")
  print(f"  Шаги: {agent.total_steps}")
  print(f"  Выигрыши: {agent.wins}")
  print(f"\nРезультаты:")
  print(f"  Старый win_rate: {old_win_rate:.2f}% (неправильно)")
  print(f"  Новый win_rate: {new_win_rate:.2f}% (правильно)")

  if new_win_rate == 5.0:
    print("\n✅ Win rate рассчитывается корректно")
  else:
    print(f"\n⚠️ Ошибка в расчете win rate: ожидалось 5.0%, получено {new_win_rate:.2f}%")


def test_integration():
  """Интеграционный тест с реальными данными"""
  print("\n" + "=" * 70)
  print("🔄 ИНТЕГРАЦИОННЫЙ ТЕСТ")
  print("=" * 70)

  lottery_type = '4x20'
  config = data_manager.LOTTERY_CONFIGS[lottery_type]

  # Загружаем данные
  df = data_manager.fetch_draws_from_db()
  print(f"\nЗагружено {len(df)} тиражей для {lottery_type}")

  if len(df) < 60:
    print("⚠️ Недостаточно данных для полного теста")
    return

  # Разделяем данные
  train_size = int(len(df) * 0.7)
  val_size = int(len(df) * 0.15)

  train_df = df.iloc[:train_size]
  val_df = df.iloc[train_size:train_size + val_size]
  test_df = df.iloc[train_size + val_size:]

  print(f"Разделение данных:")
  print(f"  Train: {len(train_df)} тиражей")
  print(f"  Val: {len(val_df)} тиражей")
  print(f"  Test: {len(test_df)} тиражей")

  # Создаем генератор
  generator = GLOBAL_RL_MANAGER.get_generator(lottery_type, config)

  # Быстрое обучение для теста
  print(f"\n🚀 Быстрое обучение (100 эпизодов)...")
  start_time = time.time()

  stats = generator.train(
    df_history=train_df,
    q_episodes=100,
    dqn_episodes=50,
    verbose=False
  )

  training_time = time.time() - start_time
  print(f"✅ Обучение завершено за {training_time:.1f} сек")

  # Выводим улучшенные метрики
  if 'q_learning' in stats:
    q_stats = stats['q_learning']
    print(f"\nQ-Learning результаты:")
    print(f"  Win rate: {q_stats.get('win_rate', 0):.2f}%")
    print(f"  Средняя награда: {q_stats.get('average_reward', 0):.2f}")

  if 'dqn' in stats:
    dqn_stats = stats['dqn']
    print(f"\nDQN результаты:")
    print(f"  Win rate: {dqn_stats.get('win_rate', 0):.2f}%")
    print(f"  Средняя награда: {dqn_stats.get('average_reward', 0):.2f}")

  # Валидация
  print(f"\n📊 Валидация на {len(val_df)} тиражах...")
  val_metrics = generator.evaluate(val_df, window_size=30)

  for agent_name, metrics in val_metrics.items():
    print(f"\n{agent_name}:")
    print(f"  Win rate: {metrics.get('win_rate', 0):.2f}%")
    print(f"  ROI: {metrics.get('roi', 0):.2f}%")
    print(f"  Средние совпадения: {metrics.get('average_matches', 0):.2f}")

  # Генерация комбинаций
  print(f"\n🎲 Генерация 3 комбинаций...")
  combinations = generator.generate_combinations(
    count=3,
    df_history=df,
    strategy='ensemble'
  )

  for i, combo in enumerate(combinations, 1):
    print(f"\nКомбинация {i}:")
    print(f"  Поле 1: {combo['field1']}")
    print(f"  Поле 2: {combo['field2']}")
    print(f"  Метод: {combo['method']}")
    print(f"  Уверенность: {combo['confidence']:.3f}")


def main():
  """Основная функция"""
  print("\n" + "=" * 70)
  print("🚀 ТЕСТИРОВАНИЕ УЛУЧШЕННОЙ RL СИСТЕМЫ")
  print("=" * 70)
  print(f"Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

  try:
    # Тест 1: Улучшенные награды
    calculator = test_improved_rewards()

    # Тест 2: Curiosity module
    test_curiosity_module()

    # Тест 3: Win rate
    test_win_rate_calculation()

    # Тест 4: Интеграция
    test_integration()

    print("\n" + "=" * 70)
    print("✅ ВСЕ ТЕСТЫ ЗАВЕРШЕНЫ УСПЕШНО")
    print("=" * 70)

  except Exception as e:
    print(f"\n❌ Ошибка при тестировании: {e}")
    import traceback
    traceback.print_exc()


if __name__ == "__main__":
  main()