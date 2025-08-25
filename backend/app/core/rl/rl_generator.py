"""
Интеграция RL агентов с генератором комбинаций
Объединяет Q-Learning и DQN для генерации оптимальных комбинаций
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any, Union
import logging
from datetime import datetime
import os
import json

import torch

from backend.app.core.rl.environment import LotteryEnvironment, LotteryState
from backend.app.core.rl.q_agent import QLearningAgent
from backend.app.core.rl.dqn_agent import DQNAgent
from backend.app.core.rl.reward_calculator import RewardCalculator, ShapedRewardCalculator
from backend.app.core import data_manager
from backend.app.core.combination_generator import _analyze_hot_cold_numbers_for_generator
from backend.app.core.lottery_context import LotteryContext
logger = logging.getLogger(__name__)


class RLGenerator:
    """
    Генератор комбинаций на основе Reinforcement Learning
    Управляет обучением и использованием RL агентов
    """
    
    def __init__(self, lottery_config: Dict, use_gpu: bool = True):
        """
        Args:
            lottery_config: Конфигурация лотереи
            use_gpu: Использовать GPU для DQN
        """
        self.lottery_config = lottery_config
        self.lottery_type = lottery_config.get('db_table', '').replace('draws_', '')
        
        # Инициализация агентов
        self.q_agent = QLearningAgent(lottery_config)
        
        # device = "cuda" if use_gpu else "cpu"
        # Принудительно используем CPU для стабильности
        device = 'cpu'
        if use_gpu and torch.cuda.is_available():
            try:
                # Тестируем CUDA
                test_tensor = torch.randn(1, 10).cuda()
                device = 'cuda'
                logger.info("✅ CUDA доступна и работает")
            except Exception as e:
                logger.warning(f"⚠️ CUDA недоступна: {e}, используем CPU")
                device = 'cpu'
        else:
            logger.info("✅ Используем CPU устройство")


        self.dqn_agent = DQNAgent(lottery_config, device=device)
        
        # Калькулятор наград
        # self.reward_calculator = ShapedRewardCalculator(lottery_config)
        
        # Путь для сохранения моделей
        self.models_dir = f"backend/models/rl/{self.lottery_type}"
        os.makedirs(self.models_dir, exist_ok=True)
        
        # Статистика
        self.generation_stats = {
            'total_generated': 0,
            'q_agent_used': 0,
            'dqn_agent_used': 0,
            'ensemble_used': 0,
            'average_confidence': 0
        }
        
        # Флаги обученности
        self.q_trained = False
        self.dqn_trained = False
        
        logger.info(f"✅ RLGenerator инициализирован для {self.lottery_type}")
    
    def train(self, 
              df_history: Optional[pd.DataFrame] = None,
              q_episodes: int = 1000,
              dqn_episodes: int = 500,
              window_size: int = 50,
              verbose: bool = True) -> Dict:
        """
        Обучение обоих RL агентов
        
        Args:
            df_history: История тиражей (если None, загружается из БД)
            q_episodes: Количество эпизодов для Q-Learning
            dqn_episodes: Количество эпизодов для DQN
            window_size: Размер окна для признаков
            verbose: Вывод прогресса
        
        Returns:
            Статистика обучения
        """
        logger.info(f"🚀 Начало обучения RL агентов для {self.lottery_type}")
        
        # Загружаем данные если не переданы
        if df_history is None:
            df_history = data_manager.fetch_draws_from_db()
            logger.info(f"📊 Загружено {len(df_history)} тиражей из БД")
        
        if len(df_history) < window_size + 10:
            logger.warning(f"⚠️ Недостаточно данных для обучения: {len(df_history)} < {window_size + 10}")
            return {'error': 'Недостаточно данных'}
        
        training_stats = {}
        
        # Обучение Q-Learning агента
        logger.info(f"📚 Обучение Q-Learning агента ({q_episodes} эпизодов)...")
        q_stats = self.q_agent.train(
            df_history=df_history,
            num_episodes=q_episodes,
            window_size=window_size,
            verbose=verbose
        )
        training_stats['q_learning'] = q_stats
        self.q_trained = True
        
        # Сохраняем Q-агента
        q_path = os.path.join(self.models_dir, "q_agent.pkl")
        self.q_agent.save(q_path)
        logger.info(f"💾 Q-агент сохранен: {q_path}")
        
        # Обучение DQN агента
        logger.info(f"🧠 Обучение DQN агента ({dqn_episodes} эпизодов)...")
        dqn_stats = self.dqn_agent.train(
            df_history=df_history,
            num_episodes=dqn_episodes,
            window_size=window_size,
            verbose=verbose
        )
        training_stats['dqn'] = dqn_stats
        self.dqn_trained = True
        
        # Сохраняем DQN агента
        dqn_path = os.path.join(self.models_dir, "dqn_agent.pth")
        self.dqn_agent.save(dqn_path)
        logger.info(f"💾 DQN агент сохранен: {dqn_path}")
        
        # Сохраняем статистику обучения
        stats_path = os.path.join(self.models_dir, "training_stats.json")
        with open(stats_path, 'w') as f:
            json.dump(training_stats, f, indent=2)
        
        logger.info(f"✅ Обучение RL агентов завершено!")
        self._print_training_summary(training_stats)
        
        return training_stats
    
    def _print_training_summary(self, stats: Dict):
        """Вывод итогов обучения"""
        logger.info("=" * 60)
        logger.info("📊 ИТОГИ ОБУЧЕНИЯ RL АГЕНТОВ")
        logger.info("=" * 60)
        
        if 'q_learning' in stats:
            q = stats['q_learning']
            logger.info(f"Q-Learning:")
            logger.info(f"  • Эпизодов: {q.get('total_episodes', 0)}")
            logger.info(f"  • Средняя награда: {q.get('average_reward', 0):.2f}")
            logger.info(f"  • Win rate: {q.get('win_rate', 0):.1f}%")
            logger.info(f"  • Размер Q-таблицы: {q.get('q_table_size', 0)}")
        
        if 'dqn' in stats:
            dqn = stats['dqn']
            logger.info(f"DQN:")
            logger.info(f"  • Эпизодов: {dqn.get('total_episodes', 0)}")
            logger.info(f"  • Средняя награда: {dqn.get('average_reward', 0):.2f}")
            logger.info(f"  • Win rate: {dqn.get('win_rate', 0):.1f}%")
            logger.info(f"  • Final loss: {dqn.get('final_loss', 0):.4f}")
        
        logger.info("=" * 60)
    
    def generate_combinations(self,
                             count: int = 5,
                             df_history: Optional[pd.DataFrame] = None,
                             strategy: str = 'ensemble',
                             window_size: int = 50) -> List[Dict]:
        """
        Генерация комбинаций с помощью обученных RL агентов
        
        Args:
            count: Количество комбинаций
            df_history: История тиражей
            strategy: Стратегия ('q_learning', 'dqn', 'ensemble')
            window_size: Размер окна для признаков
        
        Returns:
            Список сгенерированных комбинаций с метаданными
        """
        if not self.q_trained and not self.dqn_trained:
            logger.warning("⚠️ RL агенты не обучены! Используйте метод train() сначала.")
            return []
        
        # Загружаем данные если не переданы
        if df_history is None:
            df_history = data_manager.fetch_draws_from_db()
        
        if len(df_history) < window_size:
            logger.warning(f"⚠️ Недостаточно данных: {len(df_history)} < {window_size}")
            return []
        
        # Создаем среду для получения текущего состояния
        env = LotteryEnvironment(df_history, self.lottery_config, window_size)
        
        # Получаем текущее состояние (последнее в истории)
        current_state = env._compute_state(len(df_history) - 1)
        
        combinations = []
        
        for i in range(count):
            # Выбираем стратегию генерации
            if strategy == 'q_learning' and self.q_trained:
                combo = self._generate_q_learning(current_state)
                self.generation_stats['q_agent_used'] += 1
            elif strategy == 'dqn' and self.dqn_trained:
                combo = self._generate_dqn(current_state)
                self.generation_stats['dqn_agent_used'] += 1
            elif strategy == 'ensemble':
                combo = self._generate_ensemble(current_state)
                self.generation_stats['ensemble_used'] += 1
            else:
                # Fallback на случайную генерацию
                combo = self._generate_random()
            
            self.generation_stats['total_generated'] += 1
            combinations.append(combo)
        
        logger.info(f"✅ Сгенерировано {len(combinations)} комбинаций (стратегия: {strategy})")
        
        return combinations
    
    def _generate_q_learning(self, state: LotteryState) -> Dict:
        """Генерация с помощью Q-Learning агента"""
        field1, field2 = self.q_agent.predict(state)
        
        # Получаем Q-значение для оценки уверенности
        state_key = self.q_agent.get_state_key(state)
        action_key = self.q_agent.action_encoder.encode(field1, field2)
        
        q_value = 0
        if state_key in self.q_agent.q_table:
            q_value = self.q_agent.q_table[state_key].get(action_key, 0)
        
        return {
            'field1': sorted(field1),
            'field2': sorted(field2),
            'method': 'Q-Learning',
            'confidence': self._normalize_confidence(q_value, 'q'),
            'q_value': q_value,
            'state_features': state.to_dict()
        }
    
    def _generate_dqn(self, state: LotteryState) -> Dict:
        """Генерация с помощью DQN агента"""
        field1, field2 = self.dqn_agent.predict(state)
        
        # Получаем Q-значения из сети для оценки уверенности
        import torch
        with torch.no_grad():
            state_tensor = self.dqn_agent.state_to_tensor(state)
            q_values, _, _ = self.dqn_agent.q_network(state_tensor)
            max_q = q_values.max().item()
        
        return {
            'field1': sorted(field1),
            'field2': sorted(field2),
            'method': 'DQN',
            'confidence': self._normalize_confidence(max_q, 'dqn'),
            'q_value': max_q,
            'state_features': state.to_dict()
        }
    
    def _generate_ensemble(self, state: LotteryState) -> Dict:
        """Генерация ансамблевым методом"""
        combinations = []
        confidences = []
        
        # Получаем предсказания от обоих агентов
        if self.q_trained:
            q_combo = self._generate_q_learning(state)
            combinations.append((q_combo['field1'], q_combo['field2']))
            confidences.append(q_combo['confidence'])
        
        if self.dqn_trained:
            dqn_combo = self._generate_dqn(state)
            combinations.append((dqn_combo['field1'], dqn_combo['field2']))
            confidences.append(dqn_combo['confidence'])
        
        if not combinations:
            return self._generate_random()
        
        # Выбираем комбинацию с наибольшей уверенностью
        best_idx = np.argmax(confidences)
        field1, field2 = combinations[best_idx]
        
        # Альтернатива: усреднение (голосование)
        # Можно также использовать частотный подход для выбора чисел
        
        return {
            'field1': sorted(field1),
            'field2': sorted(field2),
            'method': 'Ensemble',
            'confidence': max(confidences),
            'avg_confidence': np.mean(confidences),
            'state_features': state.to_dict()
        }
    
    def _generate_random(self) -> Dict:
        """Случайная генерация как fallback"""
        import random
        field1 = sorted(random.sample(
            range(1, self.lottery_config['field1_max'] + 1),
            self.lottery_config['field1_size']
        ))
        field2 = sorted(random.sample(
            range(1, self.lottery_config['field2_max'] + 1),
            self.lottery_config['field2_size']
        ))
        
        return {
            'field1': field1,
            'field2': field2,
            'method': 'Random',
            'confidence': 0.0,
            'state_features': {}
        }
    
    def _normalize_confidence(self, value: float, agent_type: str) -> float:
        """
        Нормализация уверенности в диапазон [0, 1]
        
        Args:
            value: Q-значение
            agent_type: Тип агента ('q' или 'dqn')
        
        Returns:
            Нормализованная уверенность
        """
        # Простая сигмоидная нормализация
        # Можно настроить коэффициенты под конкретные диапазоны Q-значений
        if agent_type == 'q':
            # Q-Learning обычно имеет меньшие значения
            normalized = 1 / (1 + np.exp(-value / 10))
        else:
            # DQN может иметь больший разброс
            normalized = 1 / (1 + np.exp(-value / 100))
        
        return float(normalized)
    
    def load_models(self) -> bool:
        """
        Загрузка сохраненных моделей
        
        Returns:
            True если хотя бы одна модель загружена
        """
        loaded = False
        
        # Загрузка Q-агента
        q_path = os.path.join(self.models_dir, "q_agent.pkl")
        if os.path.exists(q_path):
            try:
                self.q_agent.load(q_path)
                self.q_trained = True
                loaded = True
                logger.info(f"✅ Q-агент загружен из {q_path}")
            except Exception as e:
                logger.error(f"❌ Ошибка загрузки Q-агента: {e}")
        
        # Загрузка DQN агента
        dqn_path = os.path.join(self.models_dir, "dqn_agent.pth")
        if os.path.exists(dqn_path):
            try:
                self.dqn_agent.load(dqn_path)
                self.dqn_trained = True
                loaded = True
                logger.info(f"✅ DQN агент загружен из {dqn_path}")
            except Exception as e:
                logger.error(f"❌ Ошибка загрузки DQN агента: {e}")
        
        return loaded

    def evaluate(self,
                 df_test: pd.DataFrame,
                 window_size: int = 50) -> Dict:
        """
        Оценка производительности RL агентов на тестовых данных

        Args:
            df_test: Тестовые данные
            window_size: Размер окна

        Returns:
            Метрики производительности
        """
        if not self.q_trained and not self.dqn_trained:
            logger.warning("⚠️ Нет обученных агентов для оценки")
            return {}

        logger.info(f"📊 Оценка RL агентов на {len(df_test)} тиражах...")

        env = LotteryEnvironment(df_test, self.lottery_config, window_size)

        results = {
            'q_learning': {'rewards': [], 'matches': []},
            'dqn': {'rewards': [], 'matches': []},
            'ensemble': {'rewards': [], 'matches': []}
        }

        # Проходим по тестовым данным
        for i in range(window_size, len(df_test) - 1):
            state = env._compute_state(i)
            actual_draw = df_test.iloc[i + 1]

            actual_f1 = eval(actual_draw['field1']) if isinstance(actual_draw['field1'], str) else actual_draw['field1']
            actual_f2 = eval(actual_draw['field2']) if isinstance(actual_draw['field2'], str) else actual_draw['field2']

            # Тестируем каждого агента
            if self.q_trained:
                pred_f1, pred_f2 = self.q_agent.predict(state)
                reward = env._calculate_reward(pred_f1, pred_f2, actual_f1, actual_f2)
                matches = len(set(pred_f1) & set(actual_f1))
                results['q_learning']['rewards'].append(reward)
                results['q_learning']['matches'].append(matches)

            if self.dqn_trained:
                pred_f1, pred_f2 = self.dqn_agent.predict(state)
                reward = env._calculate_reward(pred_f1, pred_f2, actual_f1, actual_f2)
                matches = len(set(pred_f1) & set(actual_f1))
                results['dqn']['rewards'].append(reward)
                results['dqn']['matches'].append(matches)

            if self.q_trained and self.dqn_trained:
                ensemble_combo = self._generate_ensemble(state)
                pred_f1, pred_f2 = ensemble_combo['field1'], ensemble_combo['field2']
                reward = env._calculate_reward(pred_f1, pred_f2, actual_f1, actual_f2)
                matches = len(set(pred_f1) & set(actual_f1))
                results['ensemble']['rewards'].append(reward)
                results['ensemble']['matches'].append(matches)

        # Вычисляем метрики
        metrics = {}
        for agent_name, agent_results in results.items():
            if agent_results['rewards']:
                rewards = np.array(agent_results['rewards'])
                matches = np.array(agent_results['matches'])

                metrics[agent_name] = {
                    'total_reward': float(np.sum(rewards)),
                    'average_reward': float(np.mean(rewards)),
                    'win_rate': float(np.mean(rewards > 0) * 100),
                    'average_matches': float(np.mean(matches)),
                    'max_matches': int(np.max(matches)),
                    'roi': float((np.sum(rewards) / len(rewards)) * 100)
                }

        self._print_evaluation_results(metrics)

        return metrics
    
    def _print_evaluation_results(self, metrics: Dict):
        """Вывод результатов оценки"""
        logger.info("=" * 60)
        logger.info("📊 РЕЗУЛЬТАТЫ ОЦЕНКИ RL АГЕНТОВ")
        logger.info("=" * 60)
        
        for agent_name, agent_metrics in metrics.items():
            logger.info(f"{agent_name}:")
            logger.info(f"  • Средняя награда: {agent_metrics['average_reward']:.2f}")
            logger.info(f"  • Win rate: {agent_metrics['win_rate']:.1f}%")
            logger.info(f"  • Среднее совпадений: {agent_metrics['average_matches']:.2f}")
            logger.info(f"  • Макс. совпадений: {agent_metrics['max_matches']}")
            logger.info(f"  • ROI: {agent_metrics['roi']:.2f}%")
        
        logger.info("=" * 60)
    
    def get_statistics(self) -> Dict:
        """Получение статистики генератора"""
        stats = self.generation_stats.copy()
        
        # Добавляем информацию об агентах
        stats['agents'] = {
            'q_learning': {
                'trained': self.q_trained,
                'episodes': self.q_agent.total_episodes if self.q_trained else 0,
                'q_table_size': self.q_agent._get_q_table_size() if self.q_trained else 0
            },
            'dqn': {
                'trained': self.dqn_trained,
                'episodes': self.dqn_agent.total_episodes if self.dqn_trained else 0,
                'memory_size': len(self.dqn_agent.memory) if self.dqn_trained else 0
            }
        }
        
        return stats


# Глобальный менеджер RL генераторов
class RLGeneratorManager:
    """
    Менеджер для управления RL генераторами разных лотерей
    """
    
    def __init__(self):
        self.generators = {}
        logger.info("✅ RLGeneratorManager инициализирован")
    
    def get_generator(self, lottery_type: str, lottery_config: Dict) -> RLGenerator:
        """
        Получение или создание RL генератора для лотереи
        
        Args:
            lottery_type: Тип лотереи
            lottery_config: Конфигурация лотереи
        
        Returns:
            RL генератор
        """
        if lottery_type not in self.generators:
            self.generators[lottery_type] = RLGenerator(lottery_config)
            
            # Пытаемся загрузить сохраненные модели
            if self.generators[lottery_type].load_models():
                logger.info(f"✅ Загружены сохраненные RL модели для {lottery_type}")
        
        return self.generators[lottery_type]
    
    def train_all(self, verbose: bool = True) -> Dict:
        """
        Обучение всех RL генераторов
        
        Args:
            verbose: Вывод прогресса
        
        Returns:
            Статистика обучения
        """
        results = {}
        
        for lottery_type in data_manager.LOTTERY_CONFIGS.keys():
            logger.info(f"🎯 Обучение RL для {lottery_type}...")
            
            config = data_manager.LOTTERY_CONFIGS[lottery_type]
            generator = self.get_generator(lottery_type, config)
            
            # Загружаем данные
            # with data_manager.LotteryContext(lottery_type):
            #     df = data_manager.fetch_draws_from_db()
            with data_manager.set_current_lottery(lottery_type):
                df = data_manager.fetch_draws_from_db()


            if len(df) >= 60:  # Минимум для обучения
                stats = generator.train(df, verbose=verbose)
                results[lottery_type] = stats
            else:
                logger.warning(f"⚠️ Недостаточно данных для {lottery_type}: {len(df)} тиражей")
                results[lottery_type] = {'error': 'Недостаточно данных'}
        
        return results


# Создаем глобальный экземпляр менеджера
GLOBAL_RL_MANAGER = RLGeneratorManager()