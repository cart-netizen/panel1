"""
Deep Q-Network (DQN) агент для лотереи
Использует нейронную сеть для аппроксимации Q-функции
"""

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
from typing import Dict, List, Tuple, Optional, Any
from collections import deque
import random
import logging
from datetime import datetime

from backend.app.core.rl.environment import LotteryEnvironment, LotteryState
from backend.app.core.rl.state_encoder import StateEncoder, ActionEncoder
from backend.app.core.rl.reward_calculator import RewardCalculator

logger = logging.getLogger(__name__)


class DQNNetwork(nn.Module):
    """
    Нейронная сеть для аппроксимации Q-функции
    """

    def __init__(self, state_size: int, action_embedding_size: int = 128, hidden_sizes: List[int] = None):
        """
        Args:
            state_size: Размерность входного состояния
            action_embedding_size: Размерность эмбеддинга действий
            hidden_sizes: Размеры скрытых слоев
        """
        super(DQNNetwork, self).__init__()

        if hidden_sizes is None:
            hidden_sizes = [256, 512, 256]

        self.state_size = state_size
        self.action_embedding_size = action_embedding_size

        # Кодировщик состояния
        self.state_encoder = nn.Sequential(
            nn.Linear(state_size, hidden_sizes[0]),
            nn.ReLU(),
            nn.BatchNorm1d(hidden_sizes[0]),
            nn.Dropout(0.2)
        )

        # Основная сеть
        layers = []
        for i in range(len(hidden_sizes) - 1):
            layers.extend([
                nn.Linear(hidden_sizes[i], hidden_sizes[i + 1]),
                nn.ReLU(),
                nn.BatchNorm1d(hidden_sizes[i + 1]),
                nn.Dropout(0.2)
            ])
        self.hidden_layers = nn.Sequential(*layers)

        # Дуэльная архитектура (Dueling DQN)
        self.value_stream = nn.Sequential(
            nn.Linear(hidden_sizes[-1], 128),
            nn.ReLU(),
            nn.Linear(128, 1)
        )

        self.advantage_stream = nn.Sequential(
            nn.Linear(hidden_sizes[-1], 128),
            nn.ReLU(),
            nn.Linear(128, action_embedding_size)
        )

        # Декодер для генерации действий
        self.action_decoder_f1 = nn.Sequential(
            nn.Linear(action_embedding_size, 256),
            nn.ReLU(),
            nn.Linear(256, 50),  # Максимум 50 чисел для field1
            nn.Sigmoid()
        )

        self.action_decoder_f2 = nn.Sequential(
            nn.Linear(action_embedding_size, 128),
            nn.ReLU(),
            nn.Linear(128, 12),  # Максимум 12 чисел для field2
            nn.Sigmoid()
        )

        # Головы для Q-значений и предсказаний
        self.q_head = nn.Sequential(
            nn.Linear(hidden_sizes[-1], 256),
            nn.ReLU(),
            nn.Linear(256, action_embedding_size)
        )

        self.field1_head = nn.Sequential(
            nn.Linear(hidden_sizes[-1], 256),
            nn.ReLU(),
            nn.Linear(256, 50)  # Максимум 50 чисел для field1
        )

        self.field2_head = nn.Sequential(
            nn.Linear(hidden_sizes[-1], 128),
            nn.ReLU(),
            nn.Linear(128, 12)  # Максимум 12 чисел для field2
        )

    # def forward(self, state: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    #     """
    #     Прямой проход сети
    #
    #     Args:
    #         state: Тензор состояния
    #
    #     Returns:
    #         (Q-значения, предсказание field1, предсказание field2)
    #     """
    #     # Кодируем состояние
    #     x = self.state_encoder(state)
    #     x = self.hidden_layers(x)
    #
    #     # Дуэльная архитектура для Q-значений
    #     value = self.value_stream(x)
    #     advantage = self.advantage_stream(x)
    #
    #     # Q = V(s) + A(s,a) - mean(A(s,a))
    #     q_values = value + advantage - advantage.mean(dim=1, keepdim=True)
    #
    #     # Генерация действий
    #     action_embedding = advantage  # Используем преимущества как эмбеддинг
    #     field1_probs = self.action_decoder_f1(action_embedding)
    #     field2_probs = self.action_decoder_f2(action_embedding)
    #
    #     return q_values, field1_probs, field2_probs

    def forward(self, state):
        # Проверяем размер батча для BatchNorm
        if state.size(0) == 1:
            # При размере батча = 1 переводим в eval режим для BatchNorm
            self.state_encoder.eval()
            with torch.no_grad():
                x = self.state_encoder(state)
            self.state_encoder.train()  # Возвращаем в train режим
        else:
            x = self.state_encoder(state)

        # Проходим через скрытые слои
        x = self.hidden_layers(x)

        # Q-values для комбинаций
        q_values = self.q_head(x)

        # Вероятности для каждого поля
        field1_logits = self.field1_head(x)
        field2_logits = self.field2_head(x)

        field1_probs = F.softmax(field1_logits, dim=-1)
        field2_probs = F.softmax(field2_logits, dim=-1)

        return q_values, field1_probs, field2_probs


class ReplayBuffer:
    """
    Буфер воспроизведения для хранения опыта
    """
    
    def __init__(self, capacity: int = 10000):
        """
        Args:
            capacity: Максимальный размер буфера
        """
        self.buffer = deque(maxlen=capacity)
    
    def push(self, state: np.ndarray, action: Tuple, reward: float, 
             next_state: Optional[np.ndarray], done: bool):
        """Добавление опыта в буфер"""
        self.buffer.append((state, action, reward, next_state, done))
    
    def sample(self, batch_size: int) -> List[Tuple]:
        """Случайная выборка из буфера"""
        return random.sample(self.buffer, batch_size)
    
    def __len__(self) -> int:
        return len(self.buffer)


class DQNAgent:
    """
    Deep Q-Network агент для оптимизации стратегии лотереи
    """
    
    def __init__(self,
                 lottery_config: Dict,
                 learning_rate: float = 0.001,
                 discount_factor: float = 0.99,
                 epsilon: float = 1.0,
                 epsilon_decay: float = 0.995,
                 epsilon_min: float = 0.01,
                 batch_size: int = 32,
                 memory_size: int = 10000,
                 target_update_freq: int = 100,
                 device: str = None):
        """
        Args:
            lottery_config: Конфигурация лотереи
            learning_rate: Скорость обучения
            discount_factor: Фактор дисконтирования
            epsilon: Начальное значение epsilon
            epsilon_decay: Затухание epsilon
            epsilon_min: Минимальное значение epsilon
            batch_size: Размер батча
            memory_size: Размер буфера воспроизведения
            target_update_freq: Частота обновления целевой сети
            device: Устройство (cuda/cpu)
        """
        self.lottery_config = lottery_config
        self.learning_rate = learning_rate
        self.discount_factor = discount_factor
        self.epsilon = epsilon
        self.epsilon_decay = epsilon_decay
        self.epsilon_min = epsilon_min
        self.batch_size = batch_size
        self.target_update_freq = target_update_freq
        
        # Устройство
        if device is None:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device)
        
        # Кодировщики
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
        
        # Размерности
        self.state_size = 10  # Количество признаков в состоянии
        self.field1_size = lottery_config['field1_size']
        self.field2_size = lottery_config['field2_size']
        self.field1_max = lottery_config['field1_max']
        self.field2_max = lottery_config['field2_max']
        
        # Нейронные сети
        self.q_network = DQNNetwork(self.state_size).to(self.device)
        self.target_network = DQNNetwork(self.state_size).to(self.device)
        self.target_network.load_state_dict(self.q_network.state_dict())

        # Оптимизатор
        self.optimizer = optim.Adam(self.q_network.parameters(), lr=learning_rate)
        
        # Буфер воспроизведения
        self.memory = ReplayBuffer(memory_size)
        
        # Статистика
        self.total_steps = 0
        self.total_episodes = 0
        self.total_reward = 0
        self.wins = 0
        self.losses = []
        self.episode_rewards = []
        self.learning_history = []
        
        logger.info(f"✅ DQN агент инициализирован на {self.device}")
        logger.info(f"   Архитектура: {sum(p.numel() for p in self.q_network.parameters())} параметров")
    
    def state_to_tensor(self, state: LotteryState) -> torch.Tensor:
        """Преобразование состояния в тензор"""
        state_vector = state.to_vector()
        return torch.FloatTensor(state_vector).unsqueeze(0).to(self.device)
    
    def choose_action(self, state: LotteryState, training: bool = True) -> Tuple[List[int], List[int]]:
        """
        Выбор действия с помощью epsilon-greedy стратегии
        
        Args:
            state: Текущее состояние
            training: Режим обучения
        
        Returns:
            Выбранное действие (field1, field2)
        """
        # Epsilon-greedy
        if training and random.random() < self.epsilon:
            # Случайное действие
            return self.action_encoder.sample_random_action()
        
        # Используем нейросеть
        state_tensor = self.state_to_tensor(state)

        # Устанавливаем правильный режим для BatchNorm
        if state_tensor.size(0) == 1:
            self.q_network.eval()

        with torch.no_grad():
            q_values, field1_probs, field2_probs = self.q_network(state_tensor)

        # Возвращаем в train режим если нужно
        if training and state_tensor.size(0) == 1:
            self.q_network.train()
            
        # Преобразуем вероятности в действия
        field1 = self._probs_to_numbers(field1_probs[0], self.field1_size, self.field1_max)
        field2 = self._probs_to_numbers(field2_probs[0], self.field2_size, self.field2_max)

        return field1, field2
    
    def _probs_to_numbers(self, probs: torch.Tensor, size: int, max_num: int) -> List[int]:
        """
        Преобразование вероятностей в числа
        
        Args:
            probs: Тензор вероятностей
            size: Количество чисел
            max_num: Максимальное число
        
        Returns:
            Список выбранных чисел
        """
        # Берем только нужное количество вероятностей
        probs = probs[:max_num].cpu().numpy()
        
        # Выбираем топ-K индексов с наибольшими вероятностями
        top_indices = np.argsort(probs)[-size:]
        
        # Преобразуем индексы в числа (индекс 0 = число 1)
        numbers = [int(idx) + 1 for idx in top_indices]
        
        return sorted(numbers)
    
    def remember(self, state: LotteryState, action: Tuple[List[int], List[int]], 
                reward: float, next_state: Optional[LotteryState], done: bool):
        """
        Сохранение опыта в буфер
        
        Args:
            state: Текущее состояние
            action: Выполненное действие
            reward: Полученная награда
            next_state: Следующее состояние
            done: Признак завершения
        """
        state_vector = state.to_vector()
        next_state_vector = next_state.to_vector() if next_state else None
        
        self.memory.push(state_vector, action, reward, next_state_vector, done)

    def replay(self):
        """h
        Обучение на случайной выборке из буфера воспроизведения
        """
        # Минимальный размер батча для BatchNorm
        min_batch_size = max(2, self.batch_size // 4)  # Минимум 2 образца

        if len(self.memory) < min_batch_size:
            return

        # Используем доступный размер батча
        actual_batch_size = min(self.batch_size, len(self.memory))
        if actual_batch_size < 2:
            actual_batch_size = 2  # Минимум для BatchNorm

        # Сэмплируем актуальный размер батча
        batch = self.memory.sample(actual_batch_size)

        states_array = np.array([e[0] for e in batch])
        states = torch.FloatTensor(states_array).to(self.device)
        actions = [e[1] for e in batch]
        rewards = torch.FloatTensor([e[2] for e in batch]).to(self.device)
        next_states = [e[3] for e in batch]
        dones = torch.FloatTensor([e[4] for e in batch]).to(self.device)

        # Устанавливаем правильный режим для BatchNorm
        if states.size(0) == 1:
            self.q_network.eval()
            self.target_network.eval()

        # Текущие Q-значения
        current_q_values, _, _ = self.q_network(states)

        # Целевые Q-значения
        target_q_values = rewards.clone()

        # Для не-терминальных состояний добавляем будущую награду
        non_terminal_mask = (dones == 0)
        if non_terminal_mask.any():
            non_terminal_list = [ns for ns, d in zip(next_states, dones) if d == 0 and ns is not None]
            if non_terminal_list:
                # Используем np.stack для быстрого объединения numpy массивов
                non_terminal_array = np.stack(non_terminal_list)
                non_terminal_next_states = torch.FloatTensor(non_terminal_array).to(self.device)
            else:
                # Создаем пустой тензор правильной формы
                non_terminal_next_states = torch.empty(0, 10).to(self.device)  # 10 = размер состояния

            if len(non_terminal_next_states) > 0:
                with torch.no_grad():
                    next_q_values, _, _ = self.target_network(non_terminal_next_states)
                    max_next_q = next_q_values.max(1)[0]

                    # Обновляем целевые значения для не-терминальных состояний
                    j = 0
                    for i, is_non_terminal in enumerate(non_terminal_mask):
                        if is_non_terminal and next_states[i] is not None:
                            target_q_values[i] += self.discount_factor * max_next_q[j]
                            j += 1

        # Вычисляем loss
        # Используем среднее Q-значение как прокси для оценки действия
        loss = F.mse_loss(current_q_values.mean(1), target_q_values)

        # Обратное распространение
        self.optimizer.zero_grad()
        loss.backward()

        # Градиентный клиппинг
        torch.nn.utils.clip_grad_norm_(self.q_network.parameters(), 1.0)

        self.optimizer.step()

        # Возвращаем в train режим
        if states.size(0) == 1:
            self.q_network.train()
            self.target_network.train()

        self.losses.append(loss.item())
    
    def update_target_network(self):
        """Обновление целевой сети"""
        self.target_network.load_state_dict(self.q_network.state_dict())
        logger.debug("🎯 Целевая сеть обновлена")
    
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
            
            # Сохраняем опыт
            self.remember(state, action, reward, next_state, done)
            
            # Обучаемся на опыте
            if len(self.memory) >= self.batch_size:
                self.replay()
            
            # Обновляем статистику
            episode_reward += reward
            if reward > 0:
                wins_episode += 1
            
            steps += 1
            self.total_steps += 1
            
            # Обновляем целевую сеть
            if self.total_steps % self.target_update_freq == 0:
                self.update_target_network()
            
            state = next_state
            
            if done:
                break
        
        # Затухание epsilon
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay
        
        # Обновляем статистику
        self.total_episodes += 1
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
            'loss': np.mean(self.losses[-100:]) if self.losses else 0
        }
        
        self.episode_rewards.append(episode_reward)
        self.learning_history.append(episode_stats)
        
        return episode_stats
    
    def train(self,
              df_history: pd.DataFrame,
              num_episodes: int = 500,
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
            Итоговая статистика
        """
        logger.info(f"🚀 Начало обучения DQN агента: {num_episodes} эпизодов")
        
        # Создаем среду
        env = LotteryEnvironment(df_history, self.lottery_config, window_size)
        
        best_episode_reward = -float('inf')
        best_episode = None
        
        for episode in range(num_episodes):
            # Обучение на эпизоде
            stats = self.train_episode(env)
            
            # Отслеживаем лучший эпизод
            if stats['reward'] > best_episode_reward:
                best_episode_reward = stats['reward']
                best_episode = stats['episode']
            
            # Периодический вывод
            if verbose and (episode + 1) % 50 == 0:
                avg_reward = np.mean(self.episode_rewards[-50:])
                avg_loss = np.mean(self.losses[-500:]) if self.losses else 0
                win_rate = (self.wins / max(self.total_steps, 1)) * 100
                # total_games = sum(len(episode) for episode in episode_history) if hasattr(self,
                #                                                                           'episode_history') else self.total_steps
                # win_rate = (self.wins / max(total_games, 1)) * 100 if total_games > 0 else 0


                logger.info(f"📈 Эпизод {episode + 1}/{num_episodes}: "
                          f"Средняя награда={avg_reward:.2f}, "
                          f"Loss={avg_loss:.4f}, "
                          f"Win rate={win_rate:.1f}%, "
                          f"ε={self.epsilon:.3f}")
        
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
            'final_loss': np.mean(self.losses[-100:]) if self.losses else 0,
            'memory_size': len(self.memory)
        }
        
        logger.info(f"✅ Обучение DQN завершено!")
        logger.info(f"📊 Итоговая статистика:")
        logger.info(f"   Средняя награда: {final_stats['average_reward']:.2f}")
        logger.info(f"   Win rate: {final_stats['win_rate']:.1f}%")
        logger.info(f"   Лучший эпизод: {final_stats['best_episode']} (награда={final_stats['best_reward']:.2f})")
        logger.info(f"   Финальный loss: {final_stats['final_loss']:.4f}")
        
        return final_stats
    
    def predict(self, state: LotteryState) -> Tuple[List[int], List[int]]:
        """
        Предсказание лучшего действия (режим эксплуатации)
        
        Args:
            state: Текущее состояние
        
        Returns:
            Лучшее действие
        """
        return self.choose_action(state, training=False)
    
    def save(self, filepath: str):
        """
        Сохранение модели
        
        Args:
            filepath: Путь к файлу
        """
        save_dict = {
            'q_network_state': self.q_network.state_dict(),
            'target_network_state': self.target_network.state_dict(),
            'optimizer_state': self.optimizer.state_dict(),
            'epsilon': self.epsilon,
            'total_steps': self.total_steps,
            'total_episodes': self.total_episodes,
            'total_reward': self.total_reward,
            'wins': self.wins,
            'learning_history': self.learning_history,
            'config': {
                'learning_rate': self.learning_rate,
                'discount_factor': self.discount_factor,
                'epsilon_decay': self.epsilon_decay,
                'epsilon_min': self.epsilon_min,
                'batch_size': self.batch_size,
                'target_update_freq': self.target_update_freq
            }
        }
        
        torch.save(save_dict, filepath)
        logger.info(f"💾 DQN модель сохранена в {filepath}")
    
    def load(self, filepath: str):
        """
        Загрузка модели
        
        Args:
            filepath: Путь к файлу
        """
        save_dict = torch.load(filepath, map_location=self.device, weights_only=False)
        
        self.q_network.load_state_dict(save_dict['q_network_state'])
        self.target_network.load_state_dict(save_dict['target_network_state'])
        self.optimizer.load_state_dict(save_dict['optimizer_state'])
        
        self.epsilon = save_dict['epsilon']
        self.total_steps = save_dict['total_steps']
        self.total_episodes = save_dict['total_episodes']
        self.total_reward = save_dict['total_reward']
        self.wins = save_dict['wins']
        self.learning_history = save_dict['learning_history']
        
        config = save_dict['config']
        self.learning_rate = config['learning_rate']
        self.discount_factor = config['discount_factor']
        self.epsilon_decay = config['epsilon_decay']
        self.epsilon_min = config['epsilon_min']
        self.batch_size = config['batch_size']
        self.target_update_freq = config['target_update_freq']
        
        logger.info(f"✅ DQN модель загружена из {filepath}")
        logger.info(f"   Эпизодов: {self.total_episodes}, Шагов: {self.total_steps}")