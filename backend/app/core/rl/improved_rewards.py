"""
Улучшенная система наград с Reward Shaping
backend/app/core/rl/improved_rewards.py
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import logging
from collections import Counter

logger = logging.getLogger(__name__)


class ImprovedRewardCalculator:
    """
    Улучшенный калькулятор наград с reward shaping
    """

    def __init__(self, lottery_config: Dict):
        self.lottery_config = lottery_config
        self.field1_size = lottery_config['field1_size']
        self.field2_size = lottery_config['field2_size']
        self.field1_max = lottery_config['field1_max']
        self.field2_max = lottery_config['field2_max']

        # История для отслеживания повторений
        self.combination_history = []
        self.max_history = 1000

        # Счетчики для exploration bonus
        self.state_action_counts = {}

        # Настройка призовой структуры в зависимости от типа лотереи
        self.setup_prize_structure()

        logger.info(f"✅ ImprovedRewardCalculator инициализирован для {self.field1_size}x{self.field1_max}")

    def setup_prize_structure(self):
        """Настройка призовой структуры для конкретной лотереи"""
        self.ticket_cost = 100.0

        if self.field1_size == 4:  # 4x20 лотерея
            self.match_rewards = {
                (4, 4): 333333,  # Джекпот
                (4, 3): 2300,
                (4, 2): 650,
                (4, 1): 330,
                (4, 0): 140,
                (3, 3): 70,
                (3, 2): 7,
                (3, 1): 3,
                (3, 0): 6,
                (2, 2): 2,
                (2, 1): 1,
                (2, 0): 0
            }
        elif self.field1_size == 5:  # 5x36 лотерея
            self.match_rewards = {
                (5, 1): 290000,  # Суперджекпот
                (5, 0): 14500,   # Джекпот
                (4, 1): 1000,
                (4, 0): 100,
                (3, 1): 50,
                (3, 0): 10,
                (2, 1): 5,
                (2, 0): 0
            }
        else:
            # Универсальная схема
            self.match_rewards = {}
            for f1 in range(self.field1_size + 1):
                for f2 in range(self.field2_size + 1):
                    if f1 >= 2:
                        reward = (f1 ** 3) * (1 + f2) * 10
                        self.match_rewards[(f1, f2)] = reward
                    else:
                        self.match_rewards[(f1, f2)] = 0

    def calculate_reward(self,
                        predicted_f1: List[int],
                        predicted_f2: List[int],
                        actual_f1: List[int],
                        actual_f2: List[int],
                        state_features: Optional[Dict] = None) -> Tuple[float, Dict]:
        """
        Расчет награды с reward shaping

        Returns:
            (reward, info_dict) - награда и детали расчета
        """
        info = {
            'base_reward': 0,
            'match_reward': 0,
            'shaping_reward': 0,
            'exploration_reward': 0,
            'total_reward': 0,
            'matches_f1': 0,
            'matches_f2': 0
        }

        # Защита от пустых данных
        if not actual_f1 or not actual_f2:
            info['total_reward'] = -self.ticket_cost
            return -self.ticket_cost, info

        # 1. Базовая стоимость билета
        base_reward = -self.ticket_cost
        info['base_reward'] = base_reward

        # 2. Награда за совпадения
        matches_f1 = len(set(predicted_f1) & set(actual_f1))
        matches_f2 = len(set(predicted_f2) & set(actual_f2))
        info['matches_f1'] = matches_f1
        info['matches_f2'] = matches_f2

        # Основная награда из таблицы призов
        match_key = (matches_f1, matches_f2)
        match_reward = self.match_rewards.get(match_key, 0)
        info['match_reward'] = match_reward

        # Логируем крупные выигрыши
        if match_reward > 1000:
            logger.info(f"🎉 Крупный выигрыш: {matches_f1}+{matches_f2} = {match_reward}")

        # 3. Reward Shaping - промежуточные награды
        shaping_reward = 0

        # 3.1 Near-miss bonus (почти угадал)
        if matches_f1 == self.field1_size - 1:  # На 1 меньше максимума
            shaping_reward += 5.0  # Значительный бонус за близость
            info['near_miss'] = True
        elif matches_f1 == self.field1_size - 2:  # На 2 меньше
            shaping_reward += 1.0

        # 3.2 Частичные совпадения (градиент наград)
        partial_reward = matches_f1 * 0.5 + matches_f2 * 0.3
        shaping_reward += partial_reward

        # 3.3 Бонус за горячие числа
        if state_features and 'hot_numbers' in state_features:
            hot_numbers = state_features.get('hot_numbers', [])
            if hot_numbers and predicted_f1:
                hot_count = len(set(predicted_f1) & set(hot_numbers))
                hot_bonus = hot_count * 0.2
                shaping_reward += hot_bonus
                info['hot_numbers_used'] = hot_count

        # 3.4 Штраф за холодные числа (но не слишком большой)
        if state_features and 'cold_numbers' in state_features:
            cold_numbers = state_features.get('cold_numbers', [])
            if cold_numbers and predicted_f1:
                cold_count = len(set(predicted_f1) & set(cold_numbers))
                if cold_count > self.field1_size // 2:
                    cold_penalty = cold_count * -0.1
                    shaping_reward += cold_penalty
                    info['cold_penalty'] = cold_penalty

        # 3.5 Бонус за паттерны
        if self._has_interesting_pattern(predicted_f1):
            shaping_reward += 0.3
            info['pattern_bonus'] = True

        # 3.6 Бонус за разнообразие
        diversity = self._calculate_diversity(predicted_f1)
        if diversity > 0.6:
            shaping_reward += 0.2
            info['diversity_bonus'] = True

        info['shaping_reward'] = shaping_reward

        # 4. Exploration bonus (поощряем новые комбинации)
        exploration_reward = self._calculate_exploration_bonus(
            predicted_f1, predicted_f2, state_features
        )
        info['exploration_reward'] = exploration_reward

        # 5. Итоговая награда
        total_reward = base_reward + match_reward + shaping_reward + exploration_reward
        info['total_reward'] = total_reward

        # Сохраняем комбинацию в историю
        self._update_history(predicted_f1, predicted_f2)

        return total_reward, info

    def _has_interesting_pattern(self, numbers: List[int]) -> bool:
        """Проверка на интересные паттерны"""
        if len(numbers) < 3:
            return False

        sorted_nums = sorted(numbers)

        # Арифметическая прогрессия
        diffs = [sorted_nums[i+1] - sorted_nums[i] for i in range(len(sorted_nums)-1)]
        if len(set(diffs)) == 1 and diffs[0] > 0:
            return True

        # Последовательные числа (3+ подряд)
        consecutive = 1
        for i in range(len(sorted_nums)-1):
            if sorted_nums[i+1] - sorted_nums[i] == 1:
                consecutive += 1
                if consecutive >= 3:
                    return True
            else:
                consecutive = 1

        # Симметричный паттерн (относительно среднего)
        if len(sorted_nums) >= 4:
            mean = sum(sorted_nums) / len(sorted_nums)
            distances = [abs(n - mean) for n in sorted_nums]
            if len(set(distances)) <= 2:  # Максимум 2 разных расстояния
                return True

        return False

    def _calculate_diversity(self, numbers: List[int]) -> float:
        """Расчет разнообразия чисел (0-1)"""
        if not numbers:
            return 0

        sorted_nums = sorted(numbers)

        # Разброс по диапазону
        range_coverage = (max(numbers) - min(numbers)) / max(self.field1_max, 1)

        # Равномерность распределения
        gaps = [sorted_nums[i+1] - sorted_nums[i] for i in range(len(sorted_nums)-1)]
        if gaps:
            gap_variance = np.std(gaps) / np.mean(gaps) if np.mean(gaps) > 0 else 1
            uniformity = 1 / (1 + gap_variance)
        else:
            uniformity = 0

        # Четность/нечетность баланс
        even_count = sum(1 for n in numbers if n % 2 == 0)
        parity_balance = 1 - abs(0.5 - even_count/len(numbers)) * 2

        # Комбинированная метрика
        diversity = (range_coverage + uniformity + parity_balance) / 3

        return min(max(diversity, 0), 1)

    def _calculate_exploration_bonus(self,
                                    predicted_f1: List[int],
                                    predicted_f2: List[int],
                                    state_features: Optional[Dict]) -> float:
        """
        Бонус за исследование новых комбинаций
        Использует count-based exploration
        """
        # Создаем ключ для state-action пары
        state_key = self._get_state_key(state_features) if state_features else "default"
        action_key = f"{sorted(predicted_f1)}_{sorted(predicted_f2)}"
        sa_key = f"{state_key}_{action_key}"

        # Считаем, сколько раз эта комбинация использовалась
        if sa_key not in self.state_action_counts:
            self.state_action_counts[sa_key] = 0

        count = self.state_action_counts[sa_key]
        self.state_action_counts[sa_key] += 1

        # Exploration bonus обратно пропорционален частоте использования
        # Используем UCB-like формулу
        exploration_bonus = 1.0 / np.sqrt(count + 1)

        # Ограничиваем максимальный бонус
        exploration_bonus = min(exploration_bonus, 2.0)

        # Дополнительный бонус за полностью новую комбинацию
        if count == 0:
            exploration_bonus += 0.5

        return exploration_bonus

    def _get_state_key(self, state_features: Dict) -> str:
        """Создание ключа для состояния"""
        if not state_features:
            return "empty"

        # Используем основные признаки для ключа
        key_features = []
        for feature in ['hot_numbers_count', 'parity_ratio', 'diversity_index']:
            if feature in state_features:
                # Дискретизируем значения
                value = state_features[feature]
                if isinstance(value, (int, float)):
                    discretized = int(value * 10) / 10  # Округляем до 0.1
                    key_features.append(f"{feature}:{discretized}")

        return "_".join(key_features) if key_features else "default"

    def _update_history(self, predicted_f1: List[int], predicted_f2: List[int]):
        """Обновление истории комбинаций"""
        combo_key = f"{sorted(predicted_f1)}_{sorted(predicted_f2)}"
        self.combination_history.append(combo_key)

        # Ограничиваем размер истории
        if len(self.combination_history) > self.max_history:
            self.combination_history.pop(0)

    def get_statistics(self) -> Dict:
        """Получение статистики"""
        unique_combos = len(set(self.combination_history))
        total_combos = len(self.combination_history)

        exploration_rate = unique_combos / total_combos if total_combos > 0 else 0

        return {
            'total_combinations': total_combos,
            'unique_combinations': unique_combos,
            'exploration_rate': exploration_rate,
            'state_action_pairs': len(self.state_action_counts)
        }


class CuriosityDrivenBonus:
    """
    Дополнительный модуль для curiosity-driven exploration
    Награждает за обнаружение новых паттернов
    """

    def __init__(self, state_dim: int = 10):
        self.state_dim = state_dim
        self.seen_states = set()
        self.state_transitions = {}
        self.prediction_errors = []

    def calculate_curiosity_reward(self,
                                  state: np.ndarray,
                                  next_state: np.ndarray,
                                  action: Tuple) -> float:
        """
        Расчет награды за любопытство
        Основан на prediction error (как в ICM - Intrinsic Curiosity Module)
        """
        state_key = self._discretize_state(state)
        next_state_key = self._discretize_state(next_state)
        action_key = str(action)

        # Новое состояние - большая награда
        if next_state_key not in self.seen_states:
            self.seen_states.add(next_state_key)
            curiosity_reward = 1.0
        else:
            curiosity_reward = 0.1

        # Награда за неожиданный переход
        transition_key = f"{state_key}_{action_key}"
        if transition_key in self.state_transitions:
            expected_next = self.state_transitions[transition_key]
            if expected_next != next_state_key:
                # Неожиданный результат - награда
                prediction_error = self._calculate_prediction_error(
                    expected_next, next_state_key
                )
                curiosity_reward += prediction_error * 0.5

        # Обновляем модель переходов
        self.state_transitions[transition_key] = next_state_key

        return curiosity_reward

    def _discretize_state(self, state: np.ndarray) -> str:
        """Дискретизация состояния для хеширования"""
        discretized = np.round(state, decimals=1)
        return str(discretized.tolist())

    def _calculate_prediction_error(self, expected: str, actual: str) -> float:
        """Расчет ошибки предсказания"""
        # Простая метрика различия
        if expected == actual:
            return 0.0
        return 1.0  # Можно сделать более сложную метрику