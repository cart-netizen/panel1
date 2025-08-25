#!/usr/bin/env python3
"""
Скрипт для обучения Reinforcement Learning агентов
Обучает Q-Learning и DQN агентов на реальных данных лотерей

Механизм сохранения/загрузки RL моделей:
📁 Где хранятся модели:
backend/models/rl/
├── 4x20/
│   ├── q_agent.pkl           # Q-Learning таблица
│   ├── dqn_agent.pth         # DQN нейросеть
│   └── training_stats.json   # Статистика обучения
└── 5x36plus/
    ├── q_agent.pkl
    ├── dqn_agent.pth
    └── training_stats.json
🔄 Автоматическая загрузка:

При запуске сервера - модели автоматически загружаются из файлов
При остановке сервера - модели автоматически сохраняются
После обучения - модели сразу сохраняются

🚀 Варианты запуска обучения:
Вариант 1: Простой (как в прошлых чатах)
bashcd backend
python -c "from backend.app.core.rl.rl_generator import GLOBAL_RL_MANAGER; GLOBAL_RL_MANAGER.train_all(verbose=True)"
Вариант 2: Быстрый скрипт
bashpython quick_train.py
Вариант 3: Полный скрипт с опциями
bash# Обучить все лотереи (полное обучение)
python train_rl_agents.py

# Обучить конкретную лотерею
python train_rl_agents.py --lottery 4x20

# Быстрое обучение (меньше эпизодов)
python train_rl_agents.py --quick

# Только проверить состояние моделей
python train_rl_agents.py --check-only

# Кастомные параметры
python train_rl_agents.py --q-episodes 2000 --dqn-episodes 1000
✅ Что происходит после обучения:

Модели сохраняются в файлы - больше не нужно переобучать
При запуске сервера - модели загружаются автоматически
В логах видно: ✅ Загружены сохраненные RL модели для 4x20
RL готов к использованию через API эндпоинты

🔍 Проверка статуса моделей:
Через скрипт:
bashpython train_rl_agents.py --check-only
Через API:
bashcurl http://127.0.0.1:8002/api/rl/status/4x20
В логах при запуске сервера:
[RL STATS] Итоги инициализации RL:
   Всего агентов: 4
   Загружено: 4  ← Вместо 0 будет 4 после обучения
🎯 Рекомендуемый план действий:

Запустите обучение одним из способов выше
Дождитесь завершения (может занять 10-30 минут)
Проверьте логи - должны быть сообщения о сохранении
Перезапустите сервер - модели загрузятся автоматически
Используйте RL через API или фронтенд

⚡ Примерное время обучения:

Q-Learning: ~5-10 минут на лотерею
DQN: ~10-20 минут на лотерею
Общее время: ~30-60 минут для всех лотерей

После обучения агенты будут готовы генерировать комбинации через:

API: /api/rl/generate/4x20
Frontend: раздел "Анализ" → вкладка "RL Analysis"

🎉 Главное преимущество: Обучение делается один раз, потом модели работают мгновенно!

"""

import sys
import os
import time
import argparse
from datetime import datetime
from typing import Dict

import numpy as np
import pandas as pd

# Добавляем корневую директорию в PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.core.rl.rl_generator import GLOBAL_RL_MANAGER
from backend.app.core import data_manager


def print_header():
  """Вывод заголовка"""
  print("=" * 70)
  print("🤖 ОБУЧЕНИЕ REINFORCEMENT LEARNING АГЕНТОВ")
  print("=" * 70)
  print(f"⏰ Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
  print()


def check_data_availability():
  """Проверка доступности данных для всех лотерей"""
  print("📊 Проверка доступности данных...")

  data_status = {}
  for lottery_type in data_manager.LOTTERY_CONFIGS.keys():
    # with data_manager.LotteryContext(lottery_type):
    df = data_manager.fetch_draws_from_db()
    data_status[lottery_type] = len(df)
    print(f"   📈 {lottery_type}: {len(df)} тиражей")

  print()
  return data_status


def train_specific_lottery(lottery_type: str, q_episodes: int = 1000, dqn_episodes: int = 500):
  """Обучение агентов для конкретной лотереи"""
  print(f"🎯 Обучение агентов для лотереи: {lottery_type}")
  print("-" * 50)

  if lottery_type not in data_manager.LOTTERY_CONFIGS:
    print(f"❌ Неизвестный тип лотереи: {lottery_type}")
    print(f"   Доступные: {list(data_manager.LOTTERY_CONFIGS.keys())}")
    return False

  config = data_manager.LOTTERY_CONFIGS[lottery_type]
  generator = GLOBAL_RL_MANAGER.get_generator(lottery_type, config)

  # Загружаем данные
  # with data_manager.LotteryContext(lottery_type):
  #   df = data_manager.fetch_draws_from_db()
  df = data_manager.fetch_draws_from_db()

  if len(df) < 60:
    print(f"❌ Недостаточно данных для обучения: {len(df)} < 60")
    return False

  print(f"   📊 Данных для обучения: {len(df)} тиражей")
  print(f"   ⚙️ Q-Learning эпизодов: {q_episodes}")
  print(f"   🧠 DQN эпизодов: {dqn_episodes}")
  print()

  start_time = time.time()

  try:
    # Запускаем обучение
    stats = generator.train(
      df_history=df,
      q_episodes=q_episodes,
      dqn_episodes=dqn_episodes,
      verbose=True
    )

    training_time = time.time() - start_time

    print(f"✅ Обучение завершено за {training_time:.1f} секунд")
    print()

    # Выводим статистику
    if 'q_learning' in stats:
      q_stats = stats['q_learning']
      print("📈 Q-Learning результаты:")
      print(f"   • Средняя награда: {q_stats.get('average_reward', 0):.3f}")
      print(f"   • Лучшая награда: {q_stats.get('best_reward', 0):.3f}")
      print(f"   • Размер Q-таблицы: {q_stats.get('q_table_size', 0)}")
      print(f"   • Коэффициент выигрышей: {q_stats.get('win_rate', 0):.1%}")

    if 'dqn' in stats:
      dqn_stats = stats['dqn']
      print("🧠 DQN результаты:")
      print(f"   • Средняя награда: {dqn_stats.get('average_reward', 0):.3f}")
      print(f"   • Лучшая награда: {dqn_stats.get('best_reward', 0):.3f}")
      print(f"   • Размер памяти: {dqn_stats.get('memory_size', 0)}")
      print(f"   • Коэффициент выигрышей: {dqn_stats.get('win_rate', 0):.1%}")

    print()
    return True

  except Exception as e:
    print(f"❌ Ошибка при обучении: {e}")
    return False

def train_with_validation(lottery_type: str, df_full: pd.DataFrame, config: Dict):
    """Обучение с валидацией и адаптивными гиперпараметрами"""
    print(f"🎯 Обучение с валидацией для лотереи: {lottery_type}")
    print("-" * 50)

    # Разделяем данные на train/val/test
    n = len(df_full)
    train_end = int(n * 0.7)
    val_end = int(n * 0.85)

    train_df = df_full.iloc[:train_end]
    val_df = df_full.iloc[train_end:val_end]
    test_df = df_full.iloc[val_end:]

    print(f"   📊 Данные разделены:")
    print(f"      Обучение: {len(train_df)} тиражей (70%)")
    print(f"      Валидация: {len(val_df)} тиражей (15%)")
    print(f"      Тест: {len(test_df)} тиражей (15%)")

    # Получаем адаптивные гиперпараметры
    complexity = config['field1_size'] * config['field1_max']

    if complexity <= 80:  # Простые лотереи
      q_episodes = 1500
      dqn_episodes = 800
      print(f"   ⚙️ Простая лотерея (сложность: {complexity})")
    elif complexity <= 180:  # Средние лотереи
      q_episodes = 2000
      dqn_episodes = 1200
      print(f"   ⚙️ Средняя лотерея (сложность: {complexity})")
    else:  # Сложные лотереи
      q_episodes = 3000
      dqn_episodes = 2000
      print(f"   ⚙️ Сложная лотерея (сложность: {complexity})")

    print(f"   📈 Адаптивные параметры: Q={q_episodes}, DQN={dqn_episodes}")
    print()

    # Обучаем на train_df
    generator = GLOBAL_RL_MANAGER.get_generator(lottery_type, config)

    start_time = time.time()
    stats = generator.train(
      df_history=train_df,
      q_episodes=q_episodes,
      dqn_episodes=dqn_episodes,
      verbose=True
    )
    training_time = time.time() - start_time

    print(f"✅ Обучение завершено за {training_time:.1f} секунд")
    print()

    # Валидация на val_df
    print("🔍 ВАЛИДАЦИЯ НА ОТДЕЛЬНЫХ ДАННЫХ")
    print("-" * 50)

    try:
      from backend.app.core.rl.environment import LotteryEnvironment

      val_env = LotteryEnvironment(val_df, config)

      if generator.q_trained:
        q_rewards = []
        q_wins = 0
        total_plays = 0

        # 20 эпизодов по 30 ходов = 600 тестовых игр
        for episode in range(20):
          state = val_env.reset()

          for step in range(30):
            if state is None:
              break

            action = generator.q_agent.choose_action(state, training=False)
            next_state, reward, done, info = val_env.step(action)

            q_rewards.append(reward)
            total_plays += 1

            # Считаем выигрышем только реальный приз (не просто возврат билета)
            if reward > 0:
              q_wins += 1

            if done:
              break
            state = next_state

        q_avg_reward = sum(q_rewards) / len(q_rewards) if q_rewards else 0
        q_win_rate = (q_wins / total_plays) * 100 if total_plays > 0 else 0

        print(f"📈 Q-Learning валидация:")
        print(f"   Средняя награда: {q_avg_reward:.2f}")
        print(f"   Win rate: {q_win_rate:.2f}%")
        print(f"   Всего игр: {total_plays}")
        print(f"   Выигрышных: {q_wins}")
        print(f"   Лучший результат: {max(q_rewards) if q_rewards else 0:.2f}")
        print(f"   Худший результат: {min(q_rewards) if q_rewards else 0:.2f}")

        if q_win_rate > 10:
          print("   ⚠️  ВНИМАНИЕ: Слишком высокий win rate!")
        elif q_win_rate > 0.1:
          print("   ✅ Реалистичный win rate для лотереи")
        else:
          print("   📊 Очень консервативный результат")

      # Аналогично для DQN
      if generator.dqn_trained:
        dqn_rewards = []
        dqn_wins = 0
        total_plays_dqn = 0

        for episode in range(20):
          state = val_env.reset()

          for step in range(30):
            if state is None:
              break

            action = generator.dqn_agent.choose_action(state, training=False)
            next_state, reward, done, info = val_env.step(action)

            dqn_rewards.append(reward)
            total_plays_dqn += 1

            if reward > 0:
              dqn_wins += 1

            if done:
              break
            state = next_state

        dqn_avg_reward = sum(dqn_rewards) / len(dqn_rewards) if dqn_rewards else 0
        dqn_win_rate = (dqn_wins / total_plays_dqn) * 100 if total_plays_dqn > 0 else 0

        print(f"🧠 DQN валидация:")
        print(f"   Средняя награда: {dqn_avg_reward:.2f}")
        print(f"   Win rate: {dqn_win_rate:.2f}%")
        print(f"   Всего игр: {total_plays_dqn}")
        print(f"   Выигрышных: {dqn_wins}")
        print(f"   Лучший результат: {max(dqn_rewards) if dqn_rewards else 0:.2f}")
        print(f"   Худший результат: {min(dqn_rewards) if dqn_rewards else 0:.2f}")

        if dqn_win_rate > 10:
          print("   ⚠️  ВНИМАНИЕ: Слишком высокий win rate!")
        elif dqn_win_rate > 0.1:
          print("   ✅ Реалистичный win rate для лотереи")
        else:
          print("   📊 Очень консервативный результат")

    except Exception as e:
      print(f"❌ Ошибка валидации: {e}")
      print()

    return True

def train_all_lotteries(q_episodes: int = 1000, dqn_episodes: int = 500):
  """Обучение агентов для всех лотерей"""
  print("🌟 МАССОВОЕ ОБУЧЕНИЕ ВСЕХ ЛОТЕРЕЙ")
  print("=" * 50)

  data_status = check_data_availability()

  success_count = 0
  total_count = 0

  for lottery_type in data_manager.LOTTERY_CONFIGS.keys():
    total_count += 1

    if data_status[lottery_type] < 60:
      print(f"⏭️ Пропуск {lottery_type}: недостаточно данных ({data_status[lottery_type]} < 60)")
      continue

    if train_with_validation(lottery_type, data_manager.fetch_draws_from_db(),
                             data_manager.LOTTERY_CONFIGS[lottery_type]):
      success_count += 1

  print("=" * 70)
  print("📊 ИТОГИ ОБУЧЕНИЯ:")
  print(f"   ✅ Успешно обучено: {success_count}/{total_count} лотерей")
  print(f"   📁 Модели сохранены в: backend/models/rl/")
  print("=" * 70)


def check_trained_models():
  """Проверка обученных моделей"""
  print("🔍 ПРОВЕРКА ОБУЧЕННЫХ МОДЕЛЕЙ")
  print("-" * 50)

  for lottery_type in data_manager.LOTTERY_CONFIGS.keys():
    config = data_manager.LOTTERY_CONFIGS[lottery_type]
    generator = GLOBAL_RL_MANAGER.get_generator(lottery_type, config)

    # Пытаемся загрузить модели
    loaded = generator.load_models()

    status = "🟢 Обучены" if (generator.q_trained or generator.dqn_trained) else "🔴 Не обучены"
    details = []

    if generator.q_trained:
      details.append("Q-Learning ✓")
    if generator.dqn_trained:
      details.append("DQN ✓")

    details_str = " | ".join(details) if details else "Нет обученных агентов"

    print(f"   {lottery_type}: {status} ({details_str})")

  print()


def main():
  """Основная функция"""
  parser = argparse.ArgumentParser(description="Обучение RL агентов для лотерей")

  parser.add_argument(
    "--lottery",
    type=str,
    help="Обучить конкретную лотерею (4x20, 5x36plus)",
    choices=list(data_manager.LOTTERY_CONFIGS.keys())
  )

  parser.add_argument(
    "--q-episodes",
    type=int,
    default=1000,
    help="Количество эпизодов для Q-Learning (по умолчанию: 1000)"
  )

  parser.add_argument(
    "--dqn-episodes",
    type=int,
    default=500,
    help="Количество эпизодов для DQN (по умолчанию: 500)"
  )

  parser.add_argument(
    "--quick",
    action="store_true",
    help="Быстрое обучение (Q=200, DQN=100 эпизодов)"
  )

  parser.add_argument(
    "--check-only",
    action="store_true",
    help="Только проверить состояние обученных моделей"
  )

  args = parser.parse_args()

  print_header()

  # Быстрое обучение
  if args.quick:
    args.q_episodes = 200
    args.dqn_episodes = 100
    print("⚡ Режим быстрого обучения активирован")
    print()

  # Только проверка
  if args.check_only:
    check_trained_models()
    return

  # Обучение конкретной лотереи
  if args.lottery:
    train_specific_lottery(args.lottery, args.q_episodes, args.dqn_episodes)
  else:
    # Обучение всех лотерей
    train_all_lotteries(args.q_episodes, args.dqn_episodes)

  print()
  check_trained_models()

  print("🎉 Скрипт завершен!")
  print(f"⏰ Время завершения: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
  main()