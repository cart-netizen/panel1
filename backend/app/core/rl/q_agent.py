"""
Q-Learning агент для лотереи
Использует Q-таблицу с оптимизацией памяти
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from collections import defaultdict, deque
import pickle
import json
import logging
from datetime import datetime
import random

from backend.app.core.rl.environment import LotteryEnvironment, LotteryState
from backend.app.core.rl.state_encoder import StateEncoder, ActionEncoder
from backend.app.core.rl.reward_calculator import RewardCalculator

logger = logging.getLogger(__name__)


class QLearningAgent:
    """
    Q-Learning агент для оптимизации стратегии выбора лотерейных комбинаций
    """
    
    def __init__(self, 
                 lottery_config: Dict,
                 learning_rate: float = 0.1,
                 discount_factor: float = 0.95,
                 epsilon: float = 1.0,
                 epsilon_decay: float = 0.995,
                 epsilon_min: float = 0.01,
                 memory_limit: int = 100000):
        """
        Args:
            lottery_config: Конфигурация лотереи
            learning_rate: Скорость обучения (alpha)
            discount_factor: Фактор дисконтирования (gamma)
            epsilon: Начальное значение для epsilon-greedy
            epsilon_decay: Скорость затухания epsilon
            epsilon_min: Минимальное значение epsilon
            memory_limit: Максимальный размер Q-таблицы
        """
        self.lottery_config = lottery_config
        self.learning_rate = learning_rate
        self.discount_factor = discount_factor
        self.epsilon = epsilon
        self.epsilon_decay = epsilon_decay
        self.epsilon_min = epsilon_min
        self.memory_limit = memory_limit
        
        # Инициализация кодировщиков
        feature_dims = {
            'universe_length': 100,
            'parity_ratio': 1,
            'mean_gap': 50,
            'mean_frequency': 10,
            'hot_numbers_count': 20,
            'cold_numbers_count': 20,
            'sum_trend': 100,
            'diversity_index': 1,
            'days_since_jackpot': 365,
            'draw_number': 1000
        }
        self.state_encoder = StateEncoder(feature_dims)
        self.action_encoder = ActionEncoder(lottery_config)
        
        # Q-таблица с оптимизацией памяти
        self.q_table = defaultdict(lambda: defaultdict(float))
        self.state_visits = defaultdict(int)
        self.action_visits = defaultdict(lambda: defaultdict(int))
        
        # История для анализа
        self.episode_rewards = []
        self.learning_history = []
        self.best_actions = deque(maxlen=100)
        
        # Статистика
        self.total_episodes = 0
        self.total_steps = 0
        self.total_reward = 0
        self.wins = 0
        
        # Кэш для ускорения
        self.action_cache = {}
        self.state_cache = {}
        
        logger.info(f"✅ Q-Learning агент инициализирован: α={learning_rate}, γ={discount_factor}, ε={epsilon}")
    
    def get_state_key(self, state: LotteryState) -> str:
        """Получение ключа состояния для Q-таблицы"""
        state_dict = state.to_dict()
        return self.state_encoder.encode_discrete(state_dict)
    
    def choose_action(self, state: LotteryState, training: bool = True) -> Tuple[List[int], List[int]]:
        """
        Выбор действия по epsilon-greedy стратегии
        
        Args:
            state: Текущее состояние
            training: Режим обучения
        
        Returns:
            Выбранное действие (field1, field2)
        """
        state_key = self.get_state_key(state)
        
        # Epsilon-greedy стратегия
        if training and random.random() < self.epsilon:
            # Исследование: случайное действие
            action = self.action_encoder.sample_random_action()
            logger.debug(f"🎲 Случайное действие (ε={self.epsilon:.3f})")
        else:
            # Эксплуатация: лучшее известное действие
            action = self._get_best_action(state_key)
            if action is None:
                # Если нет известных действий, выбираем случайное
                action = self.action_encoder.sample_random_action()
                logger.debug("🆕 Новое состояние, случайное действие")
            else:
                logger.debug(f"🎯 Лучшее действие для состояния")
        
        # Обновляем статистику посещений
        self.state_visits[state_key] += 1
        action_key = self.action_encoder.encode(*action)
        self.action_visits[state_key][action_key] += 1
        
        return action
    
    def _get_best_action(self, state_key: str) -> Optional[Tuple[List[int], List[int]]]:
        """
        Получение лучшего действия для состояния
        
        Args:
            state_key: Ключ состояния
        
        Returns:
            Лучшее действие или None
        """
        if state_key not in self.q_table or not self.q_table[state_key]:
            return None
        
        # Находим действие с максимальным Q-значением
        best_action_key = max(self.q_table[state_key], 
                              key=lambda a: self.q_table[state_key][a])
        
        return self.action_encoder.decode(best_action_key)
    
    def update_q_value(self, 
                      state: LotteryState,
                      action: Tuple[List[int], List[int]],
                      reward: float,
                      next_state: Optional[LotteryState],
                      done: bool):
        """
        Обновление Q-значения по формуле Беллмана
        
        Q(s,a) ← Q(s,a) + α[r + γ·max_a'Q(s',a') - Q(s,a)]
        
        Args:
            state: Текущее состояние
            action: Выполненное действие
            reward: Полученная награда
            next_state: Следующее состояние
            done: Признак завершения эпизода
        """
        state_key = self.get_state_key(state)
        action_key = self.action_encoder.encode(*action)
        
        # Текущее Q-значение
        current_q = self.q_table[state_key][action_key]
        
        # Вычисляем целевое значение
        if done or next_state is None:
            target_q = reward
        else:
            next_state_key = self.get_state_key(next_state)
            max_next_q = max(self.q_table[next_state_key].values()) if self.q_table[next_state_key] else 0
            target_q = reward + self.discount_factor * max_next_q
        
        # Обновляем Q-значение
        new_q = current_q + self.learning_rate * (target_q - current_q)
        self.q_table[state_key][action_key] = new_q
        
        logger.debug(f"📊 Q обновление: {current_q:.3f} → {new_q:.3f} (награда={reward:.2f})")
        
        # Сохраняем хорошие действия
        if reward > 0:
            self.best_actions.append((state_key, action_key, reward))
    
    def train_episode(self, env: LotteryEnvironment, max_steps: int = 100) -> Dict:
        """
        Обучение на одном эпизоде
        
        Args:
            env: Среда лотереи
            max_steps: Максимальное количество шагов
        
        Returns:
            Статистика эпизода
        """
        state = env.reset()
        episode_reward = 0
        steps = 0
        wins_episode = 0
        
        for step in range(max_steps):
            # Выбираем действие
            action = self.choose_action(state, training=True)
            
            # Выполняем действие
            next_state, reward, done, info = env.step(action)
            
            # Обновляем Q-значение
            self.update_q_value(state, action, reward, next_state, done)
            
            # Обновляем статистику
            episode_reward += reward
            if reward > 0:
                wins_episode += 1
            
            steps += 1
            state = next_state
            
            if done:
                break
        
        # Затухание epsilon
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay
        
        # Обновляем общую статистику
        self.total_episodes += 1
        self.total_steps += steps
        self.total_reward += episode_reward
        # if wins_episode > 0:
        #     self.wins += 1
        self.wins += wins_episode

        # Сохраняем историю
        episode_stats = {
            'episode': self.total_episodes,
            'steps': steps,
            'reward': episode_reward,
            'wins': wins_episode,
            'epsilon': self.epsilon,
            'q_table_size': self._get_q_table_size()
        }
        
        self.episode_rewards.append(episode_reward)
        self.learning_history.append(episode_stats)
        
        # Оптимизация памяти
        if self._get_q_table_size() > self.memory_limit:
            self._optimize_memory()
        
        return episode_stats
    
    def train(self, 
              df_history: pd.DataFrame,
              num_episodes: int = 1000,
              window_size: int = 50,
              verbose: bool = True) -> Dict:
        """
        Полный цикл обучения
        
        Args:
            df_history: История тиражей
            num_episodes: Количество эпизодов
            window_size: Размер окна для признаков
            verbose: Вывод прогресса
        
        Returns:
            Итоговая статистика обучения
        """
        logger.info(f"🚀 Начало обучения Q-агента: {num_episodes} эпизодов")
        
        # Создаем среду
        env = LotteryEnvironment(df_history, self.lottery_config, window_size)
        
        # Калькулятор наград
        # reward_calc = RewardCalculator(self.lottery_config)
        
        best_episode_reward = -float('inf')
        best_episode = None
        
        for episode in range(num_episodes):
            # Обучение на эпизоде
            stats = self.train_episode(env)
            
            # Отслеживаем лучший эпизод
            if stats['reward'] > best_episode_reward:
                best_episode_reward = stats['reward']
                best_episode = stats['episode']
            
            # Периодический вывод прогресса
            if verbose and (episode + 1) % 100 == 0:
                avg_reward = np.mean(self.episode_rewards[-100:])
                win_rate = (self.wins / max(self.total_steps, 1)) * 100
                # Win rate считаем от общего количества шагов, а не эпизодов
                # total_games = sum(len(episode) for episode in episode_history) if hasattr(self,
                #                                                                           'episode_history') else self.total_steps
                # win_rate = (self.wins / max(total_games, 1)) * 100 if total_games > 0 else 0
                logger.info(f"📈 Эпизод {episode + 1}/{num_episodes}: "
                          f"Средняя награда={avg_reward:.2f}, "
                          f"Win rate={win_rate:.1f}%, "
                          f"ε={self.epsilon:.3f}, "
                          f"Q-размер={self._get_q_table_size()}")
        
        # Итоговая статистика
        final_stats = {
            'total_episodes': self.total_episodes,
            'total_steps': self.total_steps,
            'total_reward': self.total_reward,
            'average_reward': self.total_reward / self.total_episodes,
            'win_rate': (self.wins / max(self.total_steps, 1)) * 100,
            'best_episode': best_episode,
            'best_reward': best_episode_reward,
            'final_epsilon': self.epsilon,
            'q_table_size': self._get_q_table_size(),
            'unique_states': len(self.q_table),
            'unique_actions': sum(len(actions) for actions in self.q_table.values())
        }
        
        logger.info(f"✅ Обучение завершено!")
        logger.info(f"📊 Итоговая статистика:")
        logger.info(f"   Средняя награда: {final_stats['average_reward']:.2f}")
        logger.info(f"   Win rate: {final_stats['win_rate']:.1f}%")
        logger.info(f"   Лучший эпизод: {final_stats['best_episode']} (награда={final_stats['best_reward']:.2f})")
        logger.info(f"   Размер Q-таблицы: {final_stats['q_table_size']} записей")
        
        return final_stats
    
    def predict(self, state: LotteryState) -> Tuple[List[int], List[int]]:
        """
        Предсказание лучшего действия для состояния (режим эксплуатации)
        
        Args:
            state: Текущее состояние
        
        Returns:
            Лучшее действие
        """
        return self.choose_action(state, training=False)
    
    def _get_q_table_size(self) -> int:
        """Получение размера Q-таблицы"""
        return sum(len(actions) for actions in self.q_table.values())
    
    def _optimize_memory(self):
        """
        Оптимизация памяти путем удаления редко используемых записей
        """
        logger.info(f"🧹 Оптимизация памяти Q-таблицы (текущий размер: {self._get_q_table_size()})")
        
        # Сортируем состояния по частоте посещений
        states_by_visits = sorted(self.state_visits.items(), key=lambda x: x[1])
        
        # Удаляем 20% наименее посещаемых состояний
        num_to_remove = len(states_by_visits) // 5
        
        for state_key, _ in states_by_visits[:num_to_remove]:
            if state_key in self.q_table:
                del self.q_table[state_key]
            if state_key in self.state_visits:
                del self.state_visits[state_key]
            if state_key in self.action_visits:
                del self.action_visits[state_key]
        
        logger.info(f"✅ Удалено {num_to_remove} состояний, новый размер: {self._get_q_table_size()}")
    
    def save(self, filepath: str):
        """
        Сохранение агента в файл
        
        Args:
            filepath: Путь к файлу
        """
        save_data = {
            'q_table': dict(self.q_table),
            'state_visits': dict(self.state_visits),
            'action_visits': dict(self.action_visits),
            'epsilon': self.epsilon,
            'total_episodes': self.total_episodes,
            'total_steps': self.total_steps,
            'total_reward': self.total_reward,
            'wins': self.wins,
            'learning_history': self.learning_history,
            'best_actions': list(self.best_actions),
            'config': {
                'learning_rate': self.learning_rate,
                'discount_factor': self.discount_factor,
                'epsilon_decay': self.epsilon_decay,
                'epsilon_min': self.epsilon_min
            }
        }
        
        with open(filepath, 'wb') as f:
            pickle.dump(save_data, f)
        
        logger.info(f"💾 Агент сохранен в {filepath}")
    
    def load(self, filepath: str):
        """
        Загрузка агента из файла
        
        Args:
            filepath: Путь к файлу
        """
        with open(filepath, 'rb') as f:
            save_data = pickle.load(f)
        
        self.q_table = defaultdict(lambda: defaultdict(float), save_data['q_table'])
        self.state_visits = defaultdict(int, save_data['state_visits'])
        self.action_visits = defaultdict(lambda: defaultdict(int), save_data['action_visits'])
        self.epsilon = save_data['epsilon']
        self.total_episodes = save_data['total_episodes']
        self.total_steps = save_data['total_steps']
        self.total_reward = save_data['total_reward']
        self.wins = save_data['wins']
        self.learning_history = save_data['learning_history']
        self.best_actions = deque(save_data['best_actions'], maxlen=100)
        
        # Восстанавливаем конфигурацию
        config = save_data['config']
        self.learning_rate = config['learning_rate']
        self.discount_factor = config['discount_factor']
        self.epsilon_decay = config['epsilon_decay']
        self.epsilon_min = config['epsilon_min']
        
        logger.info(f"✅ Агент загружен из {filepath}")
        logger.info(f"   Эпизодов: {self.total_episodes}, Q-размер: {self._get_q_table_size()}")
    
    def get_best_combinations(self, state: LotteryState, top_k: int = 5) -> List[Tuple[Tuple[List[int], List[int]], float]]:
        """
        Получение топ-K лучших комбинаций для состояния
        
        Args:
            state: Текущее состояние
            top_k: Количество комбинаций
        
        Returns:
            Список кортежей (комбинация, Q-значение)
        """
        state_key = self.get_state_key(state)
        
        if state_key not in self.q_table:
            # Если состояние новое, возвращаем случайные комбинации
            return [(self.action_encoder.sample_random_action(), 0.0) for _ in range(top_k)]
        
        # Сортируем действия по Q-значению
        sorted_actions = sorted(self.q_table[state_key].items(), 
                              key=lambda x: x[1], 
                              reverse=True)
        
        # Декодируем и возвращаем топ-K
        result = []
        for action_key, q_value in sorted_actions[:top_k]:
            action = self.action_encoder.decode(action_key)
            result.append((action, q_value))
        
        # Если меньше top_k, добавляем случайные
        while len(result) < top_k:
            result.append((self.action_encoder.sample_random_action(), 0.0))
        
        return result