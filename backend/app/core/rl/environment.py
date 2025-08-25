"""
Среда лотереи для Reinforcement Learning
Определяет состояния, действия и награды для обучения агента

ИСПРАВЛЕНИЯ:
- Универсальная обработка названий колонок (field1/field2 и Числа_Поле1_list/Числа_Поле2_list)
- Корректное извлечение чисел из разных форматов данных
- Защита от ошибок при отсутствующих данных
- Улучшенное логирование для отладки
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from datetime import datetime

from backend.app.core import data_manager
from backend.app.core.combination_generator import _analyze_hot_cold_numbers_for_generator
from backend.app.core.rl.validation_utils import RealisticRewardCalculator

logger = logging.getLogger(__name__)
try:
    from backend.app.core.rl.improved_rewards import ImprovedRewardCalculator, CuriosityDrivenBonus
    USE_IMPROVED_REWARDS = True
except ImportError:
    logger.warning("Improved rewards not available, using basic rewards")
    USE_IMPROVED_REWARDS = False

@dataclass
class LotteryState:
    """Представление состояния среды лотереи"""
    # Основные признаки
    universe_length: int  # Количество уникальных чисел за окно
    parity_ratio: float  # Соотношение четных/нечетных
    mean_gap: float  # Среднее расстояние между выпадениями
    mean_frequency: float  # Средняя частота чисел

    # Дополнительные признаки
    hot_numbers_count: int  # Количество горячих чисел
    cold_numbers_count: int  # Количество холодных чисел
    sum_trend: float  # Тренд суммы чисел
    diversity_index: float  # Индекс разнообразия

    # Временные признаки
    days_since_jackpot: int  # Дней с последнего джекпота
    draw_number: int  # Номер тиража

    def to_vector(self) -> np.ndarray:
        """Преобразование в вектор для нейросети"""
        return np.array([
            self.universe_length / 100,  # Нормализация
            self.parity_ratio,
            self.mean_gap / 50,
            self.mean_frequency / 10,
            self.hot_numbers_count / 20,
            self.cold_numbers_count / 20,
            self.sum_trend / 100,
            self.diversity_index,
            self.days_since_jackpot / 365,
            self.draw_number / 1000
        ], dtype=np.float32)

    def to_dict(self) -> Dict:
        """Преобразование в словарь"""
        return {
            'universe_length': self.universe_length,
            'parity_ratio': self.parity_ratio,
            'mean_gap': self.mean_gap,
            'mean_frequency': self.mean_frequency,
            'hot_numbers_count': self.hot_numbers_count,
            'cold_numbers_count': self.cold_numbers_count,
            'sum_trend': self.sum_trend,
            'diversity_index': self.diversity_index,
            'days_since_jackpot': self.days_since_jackpot,
            'draw_number': self.draw_number
        }


class LotteryEnvironment:
    """
    Среда лотереи для RL-агента
    Управляет состояниями, действиями и наградами
    """

    def __init__(self, df_history: pd.DataFrame, lottery_config: Dict, window_size: int = 50):
        """
        Args:
            df_history: История тиражей
            lottery_config: Конфигурация лотереи
            window_size: Размер окна для расчета признаков
        """
        self.df_history = df_history
        self.lottery_config = lottery_config
        self.window_size = window_size

        # Параметры лотереи
        self.field1_size = lottery_config['field1_size']
        self.field2_size = lottery_config['field2_size']
        self.field1_max = lottery_config['field1_max']
        self.field2_max = lottery_config['field2_max']

        # Текущее состояние
        self.current_state: Optional[LotteryState] = None
        self.current_position: int = window_size  # Начинаем с позиции после окна

        # История эпизода
        self.episode_history = []
        self.total_reward = 0
        self.actions_taken = 0

        # Кэш состояний
        self._state_cache = {}

        # Отладочная информация о структуре данных
        if not df_history.empty:
            logger.debug(f"Колонки DataFrame: {list(df_history.columns)}")
            sample_row = df_history.iloc[0]
            logger.debug(f"Пример строки: {dict(sample_row)}")

        # Инициализация системы наград
        try:
            if USE_IMPROVED_REWARDS:
                self.reward_calculator = ImprovedRewardCalculator(lottery_config)
                self.curiosity_module = CuriosityDrivenBonus(state_dim=10)
                logger.info("✅ Используется улучшенная система наград")
            else:
                self.reward_calculator = None
                self.curiosity_module = None
        except Exception as e:
            logger.warning(f"Не удалось инициализировать улучшенную систему наград: {e}")
            self.reward_calculator = None
            self.curiosity_module = None

        logger.info(f"✅ Среда лотереи инициализирована: окно={window_size}, история={len(df_history)}")

    def _extract_numbers(self, row, field_num: int) -> List[int]:
        """
        Универсальная функция для извлечения чисел из строки DataFrame
        Поддерживает как реальные колонки БД, так и тестовые данные

        Args:
            row: Строка DataFrame
            field_num: Номер поля (1 или 2)

        Returns:
            Список чисел или пустой список при ошибке
        """
        try:
            # Попробуем сначала реальные колонки БД
            if field_num == 1:
                if 'Числа_Поле1_list' in row and row['Числа_Поле1_list'] is not None:
                    data = row['Числа_Поле1_list']
                elif 'field1' in row:
                    data = row['field1']
                else:
                    logger.warning(f"Не найдены данные поля 1 в строке: {list(row.index)}")
                    return []
            else:  # field_num == 2
                if 'Числа_Поле2_list' in row and row['Числа_Поле2_list'] is not None:
                    data = row['Числа_Поле2_list']
                elif 'field2' in row:
                    data = row['field2']
                else:
                    logger.warning(f"Не найдены данные поля 2 в строке: {list(row.index)}")
                    return []

            # Обработка разных форматов данных
            if isinstance(data, list):
                return [int(x) for x in data if isinstance(x, (int, float, str)) and str(x).isdigit()]
            elif isinstance(data, str):
                if data.strip():
                    return [int(x.strip()) for x in data.split(',') if x.strip().isdigit()]
                else:
                    return []
            elif isinstance(data, (int, float)):
                return [int(data)]
            else:
                logger.warning(f"Неизвестный тип данных поля {field_num}: {type(data)} = {data}")
                return []

        except Exception as e:
            logger.error(f"Ошибка извлечения чисел поля {field_num}: {e}")
            return []

    def reset(self, position: Optional[int] = None) -> LotteryState:
        """
        Сброс среды к начальному состоянию

        Args:
            position: Позиция в истории (None = случайная)

        Returns:
            Начальное состояние
        """
        if position is None:
            # Случайная позиция, но не слишком близко к концу
            max_pos = len(self.df_history) - 10
            min_pos = self.window_size
            position = np.random.randint(min_pos, max_pos) if max_pos > min_pos else min_pos

        self.current_position = position
        self.episode_history = []
        self.total_reward = 0
        self.actions_taken = 0

        # Вычисляем начальное состояние
        self.current_state = self._compute_state(position)

        logger.debug(f"🔄 Среда сброшена: позиция={position}")
        return self.current_state

    def step(self, action: Tuple[List[int], List[int]]) -> Tuple[LotteryState, float, bool, Dict]:
        """
        Выполнение действия в среде

        Args:
            action: Выбранная комбинация (field1, field2)

        Returns:
            (новое_состояние, награда, завершен_эпизод, инфо)
        """
        if self.current_state is None:
            raise ValueError("Среда не инициализирована. Вызовите reset() сначала")

        field1, field2 = action

        # Получаем реальный результат текущего тиража
        actual_draw = self.df_history.iloc[self.current_position]
        actual_field1 = self._extract_numbers(actual_draw, 1)
        actual_field2 = self._extract_numbers(actual_draw, 2)

        # Проверяем, что данные извлечены корректно
        if not actual_field1 or not actual_field2:
            logger.warning(f"Пустые данные в тираже {self.current_position}: f1={actual_field1}, f2={actual_field2}")

        # Вычисляем награду
        reward = self._calculate_reward(field1, field2, actual_field1, actual_field2)

        # Сохраняем в историю
        self.episode_history.append({
            'state': self.current_state.to_dict(),
            'action': {'field1': field1, 'field2': field2},
            'reward': reward,
            'actual': {'field1': actual_field1, 'field2': actual_field2}
        })

        self.total_reward += reward
        self.actions_taken += 1

        # Переходим к следующему состоянию
        self.current_position += 1
        done = self.current_position >= len(self.df_history) - 1

        if not done:
            self.current_state = self._compute_state(self.current_position)
        else:
            self.current_state = None

        # Информация для отладки
        info = {
            'position': self.current_position,
            'total_reward': self.total_reward,
            'actions_taken': self.actions_taken,
            'matches_field1': len(set(field1) & set(actual_field1)),
            'matches_field2': len(set(field2) & set(actual_field2)),
            'actual_field1': actual_field1,
            'actual_field2': actual_field2
        }

        return self.current_state, reward, done, info

    def _compute_state(self, position: int) -> LotteryState:
        """Вычисление состояния для заданной позиции"""

        # Проверяем кэш
        if position in self._state_cache:
            return self._state_cache[position]

        # Берем окно истории
        window_start = max(0, position - self.window_size)
        window_df = self.df_history.iloc[window_start:position]

        if len(window_df) == 0:
            # Возвращаем дефолтное состояние
            logger.warning(f"Пустое окно для позиции {position}, возвращаем дефолтное состояние")
            return LotteryState(
                universe_length=0,
                parity_ratio=0.5,
                mean_gap=25,
                mean_frequency=5,
                hot_numbers_count=10,
                cold_numbers_count=10,
                sum_trend=0,
                diversity_index=0.5,
                days_since_jackpot=30,
                draw_number=position
            )

        # Вычисляем признаки
        all_numbers_f1 = []
        all_numbers_f2 = []

        for _, row in window_df.iterrows():
            f1 = self._extract_numbers(row, 1)
            f2 = self._extract_numbers(row, 2)
            all_numbers_f1.extend(f1)
            all_numbers_f2.extend(f2)

        # Universe length (уникальные числа)
        universe_length = len(set(all_numbers_f1)) + len(set(all_numbers_f2))

        # Parity ratio (четность)
        if all_numbers_f1:
            even_count = sum(1 for n in all_numbers_f1 if n % 2 == 0)
            parity_ratio = even_count / len(all_numbers_f1)
        else:
            parity_ratio = 0.5

        # Mean gap (среднее расстояние между выпадениями)
        from collections import Counter
        freq_f1 = Counter(all_numbers_f1)
        gaps = []
        for num in range(1, self.field1_max + 1):
            if freq_f1[num] > 0:
                gap = len(window_df) / max(freq_f1[num], 1)
                gaps.append(gap)
        mean_gap = np.mean(gaps) if gaps else 25

        # Mean frequency
        mean_frequency = np.mean(list(freq_f1.values())) if freq_f1 else 1

        # Hot/Cold numbers - используем безопасную версию
        try:
            hot_f1, cold_f1 = _analyze_hot_cold_numbers_for_generator(window_df, 1)
            hot_f2, cold_f2 = _analyze_hot_cold_numbers_for_generator(window_df, 2)
            hot_numbers_count = len(hot_f1[:10]) + len(hot_f2[:5])
            cold_numbers_count = len(cold_f1[:10]) + len(cold_f2[:5])
        except Exception as e:
            logger.warning(f"Ошибка анализа горячих/холодных чисел: {e}")
            hot_numbers_count = 10
            cold_numbers_count = 10

        # Sum trend (тренд суммы)
        sums = []
        for _, row in window_df.tail(10).iterrows():
            f1 = self._extract_numbers(row, 1)
            if f1:  # Проверяем что список не пустой
                sums.append(sum(f1))

        if len(sums) >= 2:
            sum_trend = (sums[-1] - sums[0]) / max(len(sums), 1)
        else:
            sum_trend = 0

        # Diversity index
        total_possible = self.field1_max + self.field2_max
        diversity_index = universe_length / total_possible if total_possible > 0 else 0

        # Days since jackpot (условно)
        days_since_jackpot = position % 100  # Упрощение

        state = LotteryState(
            universe_length=universe_length,
            parity_ratio=parity_ratio,
            mean_gap=mean_gap,
            mean_frequency=mean_frequency,
            hot_numbers_count=hot_numbers_count,
            cold_numbers_count=cold_numbers_count,
            sum_trend=sum_trend,
            diversity_index=diversity_index,
            days_since_jackpot=days_since_jackpot,
            draw_number=position
        )

        # Сохраняем в кэш
        self._state_cache[position] = state

        return state

    def _calculate_reward(self, pred_field1: List[int], pred_field2: List[int],
                          actual_field1: List[int], actual_field2: List[int]) -> float:
        """
        Расчет награды с использованием улучшенной системы или базовой
        """
        # Если есть улучшенный калькулятор - используем его
        if hasattr(self, 'reward_calculator') and self.reward_calculator is not None:
            # Получаем дополнительные признаки для reward shaping
            state_features = {}
            if self.current_state:
                state_features = self.current_state.to_dict()

                # Добавляем горячие/холодные числа если есть
                try:
                    window_df = self.df_history.iloc[
                                max(0, self.current_position - self.window_size):self.current_position]
                    from backend.app.core.combination_generator import _analyze_hot_cold_numbers_for_generator
                    hot_f1, cold_f1 = _analyze_hot_cold_numbers_for_generator(window_df, 1)
                    state_features['hot_numbers'] = hot_f1[:10] if hot_f1 else []
                    state_features['cold_numbers'] = cold_f1[:10] if cold_f1 else []
                except Exception as e:
                    logger.debug(f"Не удалось получить hot/cold числа: {e}")

            # Используем улучшенный калькулятор
            reward, info = self.reward_calculator.calculate_reward(
                pred_field1, pred_field2,
                actual_field1, actual_field2,
                state_features
            )

            # Добавляем curiosity bonus если есть модуль
            if hasattr(self, 'curiosity_module') and self.curiosity_module and self.current_state:
                try:
                    if self.current_position < len(self.df_history) - 2:
                        next_state = self._compute_state(self.current_position + 1)
                        curiosity_reward = self.curiosity_module.calculate_curiosity_reward(
                            self.current_state.to_vector(),
                            next_state.to_vector(),
                            (pred_field1, pred_field2)
                        )
                        reward += curiosity_reward

                        if curiosity_reward > 0.5:
                            logger.debug(f"🔍 Curiosity bonus: {curiosity_reward:.2f}")
                except Exception as e:
                    logger.debug(f"Ошибка при расчете curiosity: {e}")

            # Логируем детали награды для отладки
            if info.get('matches_f1', 0) > 0 or info.get('matches_f2', 0) > 0:
                logger.debug(f"📊 Reward details: matches={info.get('matches_f1', 0)}+{info.get('matches_f2', 0)}, "
                             f"total={reward:.2f}, shaping={info.get('shaping_reward', 0):.2f}")

            return reward

        # Иначе используем базовую систему наград
        else:
            # Базовая реалистичная система наград
            if not hasattr(self, '_prize_structure'):
                from math import comb

                ticket_cost = 100.0

                if self.field1_size == 4:  # 4x20 лотерея
                    prize_structure = {
                        (4, 4): 3333333,  # Джекпот
                        (4, 3): 2300,
                        (4, 2): 650,
                        (4, 1): 330,
                        (4, 0): 1400,
                        (3, 3): 700,
                        (3, 2): 70,
                        (3, 1): 30,
                        (3, 0): 60,
                        (2, 2): 20,
                        (2, 1): 10,
                        (2, 0): 10,
                    }
                elif self.field1_size == 5:  # 5x36 лотерея
                    prize_structure = {
                        (5, 1): 290000,  # Суперджекпот
                        (5, 0): 145000,  # Джекпот
                        (4, 0): 1000,
                        (3, 0): 100,
                        (2, 0): 10,
                    }
                else:
                    # Универсальная схема
                    prize_structure = {
                        (self.field1_size, self.field2_size): 100000,
                        (self.field1_size - 1, 1): 1000,
                        (self.field1_size - 1, 0): 100,
                        (self.field1_size - 2, 1): 10,
                        (self.field1_size - 2, 0): 5,
                    }

                self._prize_structure = prize_structure
                self._ticket_cost = ticket_cost

            # Защита от пустых данных
            if not actual_field1 or not actual_field2:
                return -self._ticket_cost

            # Подсчет совпадений
            matches_f1 = len(set(pred_field1) & set(actual_field1))
            matches_f2 = len(set(pred_field2) & set(actual_field2))

            # Получаем приз по таблице
            prize = self._prize_structure.get((matches_f1, matches_f2), 0)

            # Итоговая награда = приз - стоимость билета
            reward = prize - self._ticket_cost

            # Логируем крупные выигрыши (редкие события)
            if prize > self._ticket_cost * 50:
                logger.info(f"🎉 Крупный выигрыш: {matches_f1}+{matches_f2} = {prize} (награда: {reward})")

            return reward

    def get_action_space_size(self) -> int:
        """Получить размер пространства действий"""
        from math import comb
        return comb(self.field1_max, self.field1_size) * comb(self.field2_max, self.field2_size)

    def get_state_space_size(self) -> int:
        """Получить размерность пространства состояний"""
        return 10  # Количество признаков в векторе состояния

    def render(self, mode: str = 'human'):
        """Визуализация текущего состояния"""
        if self.current_state is None:
            print("Среда не инициализирована")
            return

        print(f"\n{'=' * 50}")
        print(f"Позиция: {self.current_position}/{len(self.df_history)}")
        print(f"Состояние:")
        for key, value in self.current_state.to_dict().items():
            print(f"  {key}: {value:.2f}" if isinstance(value, float) else f"  {key}: {value}")
        print(f"Общая награда: {self.total_reward:.2f}")
        print(f"Действий выполнено: {self.actions_taken}")
        print(f"{'=' * 50}\n")

    def get_episode_summary(self) -> Dict[str, Any]:
        """Получить сводку по эпизоду"""
        if not self.episode_history:
            return {}

        total_matches_f1 = sum(len(set(ep['action']['field1']) & set(ep['actual']['field1']))
                              for ep in self.episode_history if ep['actual']['field1'])
        total_matches_f2 = sum(len(set(ep['action']['field2']) & set(ep['actual']['field2']))
                              for ep in self.episode_history if ep['actual']['field2'])

        return {
            'total_reward': self.total_reward,
            'actions_taken': self.actions_taken,
            'average_reward': self.total_reward / max(self.actions_taken, 1),
            'total_matches_field1': total_matches_f1,
            'total_matches_field2': total_matches_f2,
            'win_rate': sum(1 for ep in self.episode_history if ep['reward'] > 0) / max(len(self.episode_history), 1)
        }