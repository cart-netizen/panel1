"""
Тесты для модуля Reinforcement Learning
Проверка работоспособности всех компонентов
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import tempfile
import os

from backend.app.core.rl.environment import LotteryEnvironment, LotteryState
from backend.app.core.rl.q_agent import QLearningAgent
from backend.app.core.rl.dqn_agent import DQNAgent
from backend.app.core.rl.state_encoder import StateEncoder, ActionEncoder
from backend.app.core.rl.reward_calculator import RewardCalculator, ShapedRewardCalculator
from backend.app.core.rl.rl_generator import RLGenerator


@pytest.fixture
def lottery_config():
  """Конфигурация тестовой лотереи"""
  return {
    'field1_size': 5,
    'field2_size': 1,
    'field1_max': 36,
    'field2_max': 4,
    'db_table': 'test_lottery'
  }


@pytest.fixture
def sample_history():
  """Создание тестовой истории тиражей"""
  data = []
  for i in range(100):
    data.append({
      'draw_date': datetime.now() - timedelta(days=100 - i),
      'draw_number': i + 1,
      'field1': [1, 5, 10, 15, 20],
      'field2': [1]
    })

  # Добавляем вариативность
  for i in range(50, 100):
    data[i]['field1'] = list(np.random.choice(range(1, 37), 5, replace=False))
    data[i]['field2'] = [np.random.randint(1, 5)]

  return pd.DataFrame(data)


class TestLotteryEnvironment:
  """Тесты для среды лотереи"""

  def test_environment_creation(self, lottery_config, sample_history):
    """Тест создания среды"""
    env = LotteryEnvironment(sample_history, lottery_config)
    assert env is not None
    assert env.field1_size == 5
    assert env.field2_size == 1

  def test_reset(self, lottery_config, sample_history):
    """Тест сброса среды"""
    env = LotteryEnvironment(sample_history, lottery_config)
    state = env.reset()

    assert isinstance(state, LotteryState)
    assert state.draw_number >= 50  # После окна

  def test_step(self, lottery_config, sample_history):
    """Тест выполнения шага"""
    env = LotteryEnvironment(sample_history, lottery_config)
    state = env.reset(position=60)

    action = ([1, 2, 3, 4, 5], [1])
    next_state, reward, done, info = env.step(action)

    assert next_state is not None or done
    assert isinstance(reward, float)
    assert isinstance(done, bool)
    assert isinstance(info, dict)

  def test_compute_state(self, lottery_config, sample_history):
    """Тест вычисления состояния"""
    env = LotteryEnvironment(sample_history, lottery_config, window_size=10)
    state = env._compute_state(50)

    assert isinstance(state, LotteryState)
    assert state.universe_length > 0
    assert 0 <= state.parity_ratio <= 1
    assert state.mean_gap > 0


class TestStateEncoder:
  """Тесты для кодировщика состояний"""

  def test_continuous_encoding(self):
    """Тест непрерывного кодирования"""
    feature_dims = {'feature1': 100, 'feature2': 50}
    encoder = StateEncoder(feature_dims)

    state_dict = {'feature1': 50, 'feature2': 25}
    vector = encoder.encode_continuous(state_dict)

    assert isinstance(vector, np.ndarray)
    assert len(vector) == 2
    assert vector[0] == 0.5  # 50/100
    assert vector[1] == 0.5  # 25/50

  def test_discrete_encoding(self):
    """Тест дискретного кодирования"""
    feature_dims = {'universe_length': 100, 'parity_ratio': 1}
    encoder = StateEncoder(feature_dims)

    state_dict = {'universe_length': 50, 'parity_ratio': 0.5}
    key = encoder.encode_discrete(state_dict)

    assert isinstance(key, str)
    assert 'universe_length' in key
    assert 'parity_ratio' in key

  def test_hash_encoding(self):
    """Тест хэш-кодирования"""
    feature_dims = {'feature1': 100}
    encoder = StateEncoder(feature_dims)

    state_dict = {'feature1': 50}
    hash_key = encoder.encode_hash(state_dict)

    assert isinstance(hash_key, str)
    assert len(hash_key) == 16


class TestActionEncoder:
  """Тесты для кодировщика действий"""

  def test_encode_decode(self, lottery_config):
    """Тест кодирования и декодирования действий"""
    encoder = ActionEncoder(lottery_config)

    field1 = [1, 5, 10, 15, 20]
    field2 = [2]

    encoded = encoder.encode(field1, field2)
    decoded_f1, decoded_f2 = encoder.decode(encoded)

    assert set(decoded_f1) == set(field1)
    assert set(decoded_f2) == set(field2)

  def test_sample_random_action(self, lottery_config):
    """Тест генерации случайного действия"""
    encoder = ActionEncoder(lottery_config)

    field1, field2 = encoder.sample_random_action()

    assert len(field1) == lottery_config['field1_size']
    assert len(field2) == lottery_config['field2_size']
    assert all(1 <= n <= lottery_config['field1_max'] for n in field1)
    assert all(1 <= n <= lottery_config['field2_max'] for n in field2)


class TestRewardCalculator:
  """Тесты для калькулятора наград"""

  def test_basic_reward(self, lottery_config):
    """Тест базового расчета награды"""
    calc = RewardCalculator(lottery_config)

    # Полное совпадение
    reward = calc.calculate(
      [1, 2, 3, 4, 5], [1],
      [1, 2, 3, 4, 5], [1]
    )
    assert reward > 0  # Должна быть положительная награда

    # Нет совпадений
    reward = calc.calculate(
      [1, 2, 3, 4, 5], [1],
      [10, 20, 30, 31, 32], [2]
    )
    assert reward < 0  # Только стоимость билета

  def test_shaped_reward(self, lottery_config):
    """Тест shaped награды"""
    calc = ShapedRewardCalculator(lottery_config)

    # Частичное совпадение
    reward = calc.calculate(
      [1, 2, 3, 4, 5], [1],
      [1, 2, 10, 20, 30], [2]
    )

    # Должна быть награда за 2 совпадения + proximity bonus
    assert reward > -calc.scheme.ticket_cost


class TestQLearningAgent:
  """Тесты для Q-Learning агента"""

  def test_agent_creation(self, lottery_config):
    """Тест создания агента"""
    agent = QLearningAgent(lottery_config)

    assert agent is not None
    assert agent.epsilon == 1.0
    assert len(agent.q_table) == 0

  def test_choose_action(self, lottery_config, sample_history):
    """Тест выбора действия"""
    agent = QLearningAgent(lottery_config)
    env = LotteryEnvironment(sample_history, lottery_config)
    state = env.reset()

    action = agent.choose_action(state)

    assert len(action) == 2
    assert len(action[0]) == lottery_config['field1_size']
    assert len(action[1]) == lottery_config['field2_size']

  def test_update_q_value(self, lottery_config, sample_history):
    """Тест обновления Q-значения"""
    agent = QLearningAgent(lottery_config)
    env = LotteryEnvironment(sample_history, lottery_config)

    state = env.reset()
    action = agent.choose_action(state)
    next_state, reward, done, _ = env.step(action)

    # Обновляем Q-значение
    agent.update_q_value(state, action, reward, next_state, done)

    # Проверяем, что Q-таблица обновилась
    state_key = agent.get_state_key(state)
    assert state_key in agent.q_table

  def test_save_load(self, lottery_config):
    """Тест сохранения и загрузки агента"""
    agent = QLearningAgent(lottery_config)

    # Добавляем данные в Q-таблицу
    agent.q_table['test_state']['test_action'] = 0.5
    agent.total_episodes = 100

    # Сохраняем
    with tempfile.NamedTemporaryFile(suffix='.pkl', delete=False) as tmp:
      agent.save(tmp.name)
      tmp_path = tmp.name

    # Создаем нового агента и загружаем
    new_agent = QLearningAgent(lottery_config)
    new_agent.load(tmp_path)

    assert 'test_state' in new_agent.q_table
    assert new_agent.q_table['test_state']['test_action'] == 0.5
    assert new_agent.total_episodes == 100

    # Удаляем временный файл
    os.unlink(tmp_path)


class TestDQNAgent:
  """Тесты для DQN агента"""

  def test_agent_creation(self, lottery_config):
    """Тест создания DQN агента"""
    agent = DQNAgent(lottery_config, device='cpu')

    assert agent is not None
    assert agent.epsilon == 1.0
    assert len(agent.memory) == 0

  def test_state_to_tensor(self, lottery_config, sample_history):
    """Тест преобразования состояния в тензор"""
    agent = DQNAgent(lottery_config, device='cpu')
    env = LotteryEnvironment(sample_history, lottery_config)
    state = env.reset()

    tensor = agent.state_to_tensor(state)

    assert tensor.shape == (1, 10)  # batch_size=1, features=10

  def test_choose_action(self, lottery_config, sample_history):
    """Тест выбора действия DQN"""
    agent = DQNAgent(lottery_config, device='cpu')
    env = LotteryEnvironment(sample_history, lottery_config)
    state = env.reset()

    action = agent.choose_action(state)

    assert len(action) == 2
    assert len(action[0]) == lottery_config['field1_size']
    assert len(action[1]) == lottery_config['field2_size']

  def test_remember(self, lottery_config, sample_history):
    """Тест сохранения опыта"""
    agent = DQNAgent(lottery_config, device='cpu')
    env = LotteryEnvironment(sample_history, lottery_config)

    state = env.reset()
    action = agent.choose_action(state)
    next_state, reward, done, _ = env.step(action)

    agent.remember(state, action, reward, next_state, done)

    assert len(agent.memory) == 1


class TestRLGenerator:
  """Тесты для RL генератора"""

  def test_generator_creation(self, lottery_config):
    """Тест создания генератора"""
    generator = RLGenerator(lottery_config, use_gpu=False)

    assert generator is not None
    assert not generator.q_trained
    assert not generator.dqn_trained

  def test_generate_combinations(self, lottery_config, sample_history):
    """Тест генерации комбинаций"""
    import logging
    logging.disable(logging.WARNING)
    generator = RLGenerator(lottery_config, use_gpu=False)

    # Быстрое обучение для теста
    generator.train(sample_history, q_episodes=10, dqn_episodes=5, verbose=False)

    # Генерируем комбинации
    combinations = generator.generate_combinations(
      count=3,
      df_history=sample_history,
      strategy='ensemble'
    )

    assert len(combinations) == 3
    assert all('field1' in c for c in combinations)
    assert all('field2' in c for c in combinations)
    assert all('confidence' in c for c in combinations)

  def test_evaluate(self, lottery_config, sample_history):
    """Тест оценки производительности"""
    generator = RLGenerator(lottery_config, use_gpu=False)

    # Проверяем начальное состояние
    print(f"\nНачальное состояние: q_trained={generator.q_trained}, dqn_trained={generator.dqn_trained}")

    # Быстрое обучение
    print("Запускаем обучение...")
    stats = generator.train(sample_history[:80], q_episodes=10, dqn_episodes=5, verbose=False)

    # Проверяем результаты обучения
    print(f"Результаты обучения: {stats.keys() if stats else 'None'}")
    print(f"После обучения: q_trained={generator.q_trained}, dqn_trained={generator.dqn_trained}")

    # Проверяем что агенты обучены
    assert generator.q_trained or generator.dqn_trained, "Агенты не были обучены"

    # Оценка на тестовых данных
    print("Запускаем оценку...")
    metrics = generator.evaluate(sample_history[80:], window_size=10)

    # Проверяем метрики
    print(f"Метрики оценки: {metrics.keys() if metrics else 'Empty'}")

    # Проверяем наличие метрик
    assert len(metrics) > 0, "Метрики пустые"
    assert 'q_learning' in metrics or 'dqn' in metrics, f"Нет метрик агентов в {metrics.keys()}"

    # Проверяем структуру метрик
    for agent_name, agent_metrics in metrics.items():
      assert 'average_reward' in agent_metrics
      assert 'win_rate' in agent_metrics
      # Win rate должен быть между 0 и 100
      assert 0 <= agent_metrics['win_rate'] <= 100, f"Win rate вне диапазона: {agent_metrics['win_rate']}"

    print(f"✅ Тест evaluate прошел успешно с метриками: {list(metrics.keys())}")


# Запуск тестов
if __name__ == "__main__":
  pytest.main([__file__, "-v"])