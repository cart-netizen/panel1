"""
Динамический анализ текущих трендов для профессионального бота
Адаптивный алгоритм анализа паттернов в реальном времени
"""
import time
import threading
from datetime import datetime, timedelta
from collections import Counter, deque
from typing import Dict, List, Tuple, Optional
import numpy as np
import pandas as pd
from dataclasses import dataclass


@dataclass
class TrendMetrics:
  """Метрики текущих трендов"""
  hot_acceleration: List[int]  # Числа с возрастающей частотой
  cold_reversal: List[int]  # Холодные числа готовые к выходу
  momentum_numbers: List[int]  # Числа с импульсом
  pattern_shift: str  # Сдвиг паттерна: 'stable', 'ascending', 'descending'
  confidence_score: float  # Уверенность в тренде (0-1)
  trend_strength: float  # Сила тренда (0-1)


@dataclass
class CombinationMetrics:
  """Метрики для конкретной комбинации"""
  trend_alignment: float  # Соответствие тренду (0-1)
  momentum_score: float  # Импульс комбинации (0-1)
  pattern_resonance: float  # Резонанс с паттерном (0-1)
  risk_assessment: str  # 'low', 'medium', 'high'
  expected_performance: float  # Ожидаемая производительность (0-1)


class DynamicTrendAnalyzer:
  """
  Профессиональный анализатор трендов для реальной игры
  Анализирует микро-тренды и адаптируется к изменениям паттернов
  """

  def __init__(self, max_cache_size=500):
    self.trend_cache = {}
    self.pattern_memory = deque(maxlen=100)  # Память последних 100 анализов
    self.lock = threading.Lock()

    # Настройки анализа
    self.micro_trend_window = 10  # Окно микро-трендов
    self.macro_trend_window = 50  # Окно макро-трендов
    self.momentum_threshold = 0.6  # Порог для определения импульса

    # Адаптивные параметры
    self.adaptive_weights = {
      'recent_bias': 0.7,  # Вес недавних событий
      'pattern_stability': 0.3,  # Вес стабильности паттерна
      'momentum_factor': 0.8,  # Фактор импульса
      'reversal_sensitivity': 0.5  # Чувствительность к разворотам
    }

  def analyze_current_trends(self, df_history: pd.DataFrame) -> Dict[str, TrendMetrics]:
    """
    Анализирует текущие тренды для обоих полей

    Returns:
        Dict с ключами 'field1', 'field2', содержащими TrendMetrics
    """
    if df_history.empty:
      return self._get_default_trends()

    with self.lock:
      trends = {}

      for field_num in [1, 2]:
        field_col = f'Числа_Поле{field_num}_list'
        if field_col not in df_history.columns:
          continue

        # Получаем метрики тренда для поля
        trend_metrics = self._analyze_field_trends(
          df_history, field_col, field_num
        )
        trends[f'field{field_num}'] = trend_metrics

      # Сохраняем в память паттернов
      self.pattern_memory.append({
        'timestamp': datetime.now(),
        'trends': trends,
        'data_signature': self._calculate_data_signature(df_history)
      })

      return trends

  def _analyze_field_trends(self, df_history: pd.DataFrame,
                            field_col: str, field_num: int) -> TrendMetrics:
    """Анализирует тренды для конкретного поля"""

    # Извлекаем последние тиражи
    recent_draws = df_history.head(self.micro_trend_window)
    macro_draws = df_history.head(self.macro_trend_window)

    # Анализ горячих чисел с ускорением
    hot_acceleration = self._find_accelerating_numbers(
      recent_draws, macro_draws, field_col, field_num
    )

    # Анализ холодных чисел готовых к развороту
    cold_reversal = self._find_reversal_candidates(
      recent_draws, macro_draws, field_col, field_num
    )

    # Числа с импульсом
    momentum_numbers = self._calculate_momentum_numbers(
      recent_draws, field_col, field_num
    )

    # Определение сдвига паттерна
    pattern_shift = self._detect_pattern_shift(
      recent_draws, macro_draws, field_col
    )

    # Расчет уверенности и силы тренда
    confidence_score = self._calculate_confidence(
      recent_draws, macro_draws, field_col
    )

    trend_strength = self._calculate_trend_strength(
      hot_acceleration, cold_reversal, momentum_numbers
    )

    return TrendMetrics(
      hot_acceleration=hot_acceleration[:5],  # Топ-5
      cold_reversal=cold_reversal[:3],  # Топ-3
      momentum_numbers=momentum_numbers[:4],  # Топ-4
      pattern_shift=pattern_shift,
      confidence_score=confidence_score,
      trend_strength=trend_strength
    )

  def _find_accelerating_numbers(self, recent_draws: pd.DataFrame,
                                 macro_draws: pd.DataFrame, field_col: str,
                                 field_num: int) -> List[int]:
    """Находит числа с возрастающей частотой (ускорение)"""

    # Частота в недавних тиражах
    recent_freq = self._calculate_frequencies(recent_draws, field_col)

    # Частота в более длинном периоде
    macro_freq = self._calculate_frequencies(macro_draws, field_col)

    # Находим числа с положительным ускорением
    accelerating = []
    for num in range(1, self._get_field_max(field_num) + 1):
      recent_rate = recent_freq.get(num, 0) / len(recent_draws) if len(recent_draws) > 0 else 0
      macro_rate = macro_freq.get(num, 0) / len(macro_draws) if len(macro_draws) > 0 else 0

      # Ускорение = недавняя частота значительно выше общей
      if recent_rate > macro_rate * 1.5 and recent_rate > 0.2:
        acceleration_factor = recent_rate / (macro_rate + 0.01)
        accelerating.append((num, acceleration_factor))

    # Сортируем по фактору ускорения
    accelerating.sort(key=lambda x: x[1], reverse=True)
    return [num for num, _ in accelerating]

  def _find_reversal_candidates(self, recent_draws: pd.DataFrame,
                                macro_draws: pd.DataFrame, field_col: str,
                                field_num: int) -> List[int]:
    """Находит холодные числа готовые к развороту"""

    # Анализ циклов выпадения
    reversal_candidates = []
    field_max = self._get_field_max(field_num)

    for num in range(1, field_max + 1):
      # Сколько тиражей назад последний раз выпадало
      last_appearance = self._find_last_appearance(recent_draws, field_col, num)

      # Средний цикл в макро-периоде
      avg_cycle = self._calculate_average_cycle(macro_draws, field_col, num)

      # Если число "просрочено" относительно своего цикла
      if last_appearance > avg_cycle * 1.3 and avg_cycle > 0:
        overdue_factor = last_appearance / avg_cycle
        reversal_candidates.append((num, overdue_factor))

    # Сортируем по фактору "просроченности"
    reversal_candidates.sort(key=lambda x: x[1], reverse=True)
    return [num for num, _ in reversal_candidates]

  def _calculate_momentum_numbers(self, recent_draws: pd.DataFrame,
                                  field_col: str, field_num: int) -> List[int]:
    """Рассчитывает числа с текущим импульсом"""

    momentum_scores = {}
    field_max = self._get_field_max(field_num)

    # Анализируем последние 5 тиражей с весами
    weights = [0.4, 0.3, 0.2, 0.08, 0.02]  # Больший вес последним тиражам

    for i, (_, row) in enumerate(recent_draws.head(5).iterrows()):
      numbers = row.get(field_col, [])
      if not isinstance(numbers, list):
        continue

      weight = weights[i] if i < len(weights) else 0.01

      for num in numbers:
        if 1 <= num <= field_max:
          momentum_scores[num] = momentum_scores.get(num, 0) + weight

    # Сортируем по импульсу
    sorted_momentum = sorted(momentum_scores.items(), key=lambda x: x[1], reverse=True)

    # Возвращаем только числа с значимым импульсом
    return [num for num, score in sorted_momentum if score >= self.momentum_threshold]

  def _detect_pattern_shift(self, recent_draws: pd.DataFrame,
                            macro_draws: pd.DataFrame, field_col: str) -> str:
    """Определяет сдвиг паттерна"""

    if len(recent_draws) < 3 or len(macro_draws) < 10:
      return 'stable'

    # Анализ сумм последних тиражей
    recent_sums = self._calculate_sums(recent_draws, field_col)
    macro_sums = self._calculate_sums(macro_draws, field_col)

    recent_avg = np.mean(recent_sums) if recent_sums else 0
    macro_avg = np.mean(macro_sums) if macro_sums else 0

    # Определяем направление сдвига
    if recent_avg > macro_avg * 1.1:
      return 'ascending'
    elif recent_avg < macro_avg * 0.9:
      return 'descending'
    else:
      return 'stable'

  def _calculate_confidence(self, recent_draws: pd.DataFrame,
                            macro_draws: pd.DataFrame, field_col: str) -> float:
    """Рассчитывает уверенность в анализе"""

    # Базовая уверенность зависит от количества данных
    data_confidence = min(len(recent_draws) / self.micro_trend_window, 1.0)

    # Стабильность паттерна
    pattern_variance = self._calculate_pattern_variance(recent_draws, field_col)
    stability_confidence = max(0, 1 - pattern_variance)

    # Общая уверенность
    confidence = (data_confidence * 0.6 + stability_confidence * 0.4)

    return min(max(confidence, 0.1), 0.95)  # Ограничиваем между 0.1 и 0.95

  def _calculate_trend_strength(self, hot_acceleration: List[int],
                                cold_reversal: List[int],
                                momentum_numbers: List[int]) -> float:
    """Рассчитывает силу тренда"""

    # Сила основана на количестве значимых индикаторов
    indicators = len(hot_acceleration) + len(cold_reversal) + len(momentum_numbers)
    max_possible = 12  # 5 + 3 + 4

    strength = min(indicators / max_possible, 1.0)

    # Бонус за согласованность индикаторов
    if len(hot_acceleration) > 2 and len(momentum_numbers) > 2:
      strength *= 1.2

    return min(strength, 1.0)

  def evaluate_combination(self, field1: List[int], field2: List[int],
                           trends: Dict[str, TrendMetrics]) -> CombinationMetrics:
    """
    Оценивает комбинацию на основе текущих трендов

    Returns:
        CombinationMetrics с оценкой комбинации
    """

    if not trends:
      return self._get_default_combination_metrics()

    # Оценка для каждого поля
    field1_metrics = self._evaluate_field_combination(
      field1, trends.get('field1'), 1
    )
    field2_metrics = self._evaluate_field_combination(
      field2, trends.get('field2'), 2
    )

    # Общие метрики
    trend_alignment = (field1_metrics['alignment'] + field2_metrics['alignment']) / 2
    momentum_score = (field1_metrics['momentum'] + field2_metrics['momentum']) / 2
    pattern_resonance = (field1_metrics['resonance'] + field2_metrics['resonance']) / 2

    # Оценка риска
    risk_assessment = self._assess_combination_risk(
      trend_alignment, momentum_score, pattern_resonance
    )

    # Ожидаемая производительность
    expected_performance = self._calculate_expected_performance(
      trend_alignment, momentum_score, pattern_resonance, trends
    )

    return CombinationMetrics(
      trend_alignment=trend_alignment,
      momentum_score=momentum_score,
      pattern_resonance=pattern_resonance,
      risk_assessment=risk_assessment,
      expected_performance=expected_performance
    )

  def _evaluate_field_combination(self, numbers: List[int],
                                  trend_metrics: Optional[TrendMetrics],
                                  field_num: int) -> Dict[str, float]:
    """Оценивает числа поля относительно трендов"""

    if not trend_metrics or not numbers:
      return {'alignment': 0.5, 'momentum': 0.5, 'resonance': 0.5}

    # Проверка соответствия трендам
    hot_matches = len(set(numbers) & set(trend_metrics.hot_acceleration))
    cold_matches = len(set(numbers) & set(trend_metrics.cold_reversal))
    momentum_matches = len(set(numbers) & set(trend_metrics.momentum_numbers))

    # Нормализация оценок
    total_numbers = len(numbers)
    alignment = (hot_matches + cold_matches) / total_numbers if total_numbers > 0 else 0
    momentum = momentum_matches / total_numbers if total_numbers > 0 else 0

    # Резонанс с паттерном
    resonance = self._calculate_pattern_resonance(numbers, trend_metrics)

    return {
      'alignment': min(alignment, 1.0),
      'momentum': min(momentum, 1.0),
      'resonance': min(resonance, 1.0)
    }

  def _calculate_pattern_resonance(self, numbers: List[int],
                                   trend_metrics: TrendMetrics) -> float:
    """Рассчитывает резонанс с паттерном"""

    # Базовый резонанс на основе силы тренда
    base_resonance = trend_metrics.trend_strength

    # Бонус за соответствие направлению паттерна
    pattern_bonus = 0
    if trend_metrics.pattern_shift == 'ascending':
      # Проверяем, есть ли числа из верхней половины диапазона
      high_numbers = [n for n in numbers if n > 10]  # Для 1-20
      pattern_bonus = len(high_numbers) / len(numbers) * 0.3
    elif trend_metrics.pattern_shift == 'descending':
      # Проверяем, есть ли числа из нижней половины
      low_numbers = [n for n in numbers if n <= 10]
      pattern_bonus = len(low_numbers) / len(numbers) * 0.3

    return min(base_resonance + pattern_bonus, 1.0)

  def _assess_combination_risk(self, alignment: float, momentum: float,
                               resonance: float) -> str:
    """Оценивает риск комбинации"""

    overall_score = (alignment + momentum + resonance) / 3

    if overall_score >= 0.7:
      return 'low'
    elif overall_score >= 0.4:
      return 'medium'
    else:
      return 'high'

  def _calculate_expected_performance(self, alignment: float, momentum: float,
                                      resonance: float, trends: Dict) -> float:
    """Рассчитывает ожидаемую производительность"""

    # Базовая производительность
    base_performance = (alignment + momentum + resonance) / 3

    # Бонус за общую силу трендов
    avg_trend_strength = np.mean([
      trends[key].trend_strength for key in trends.keys()
      if hasattr(trends[key], 'trend_strength')
    ])

    # Бонус за уверенность
    avg_confidence = np.mean([
      trends[key].confidence_score for key in trends.keys()
      if hasattr(trends[key], 'confidence_score')
    ])

    # Итоговая производительность
    performance = base_performance * (1 + avg_trend_strength * 0.2 + avg_confidence * 0.1)

    return min(performance, 1.0)

  # Вспомогательные методы
  def _calculate_frequencies(self, df: pd.DataFrame, field_col: str) -> Dict[int, int]:
    """Рассчитывает частоты чисел"""
    freq = Counter()
    for _, row in df.iterrows():
      numbers = row.get(field_col, [])
      if isinstance(numbers, list):
        freq.update(numbers)
    return dict(freq)

  def _calculate_sums(self, df: pd.DataFrame, field_col: str) -> List[int]:
    """Рассчитывает суммы комбинаций"""
    sums = []
    for _, row in df.iterrows():
      numbers = row.get(field_col, [])
      if isinstance(numbers, list) and numbers:
        sums.append(sum(numbers))
    return sums

  def _find_last_appearance(self, df: pd.DataFrame, field_col: str, number: int) -> int:
    """Находит, сколько тиражей назад последний раз выпадало число"""
    for i, (_, row) in enumerate(df.iterrows()):
      numbers = row.get(field_col, [])
      if isinstance(numbers, list) and number in numbers:
        return i
    return len(df)  # Если не найдено

  def _calculate_average_cycle(self, df: pd.DataFrame, field_col: str, number: int) -> float:
    """Рассчитывает средний цикл выпадения числа"""
    appearances = []
    for i, (_, row) in enumerate(df.iterrows()):
      numbers = row.get(field_col, [])
      if isinstance(numbers, list) and number in numbers:
        appearances.append(i)

    if len(appearances) < 2:
      return 10.0  # Значение по умолчанию

    cycles = []
    for i in range(1, len(appearances)):
      cycles.append(appearances[i] - appearances[i - 1])

    return np.mean(cycles) if cycles else 10.0

  def _calculate_pattern_variance(self, df: pd.DataFrame, field_col: str) -> float:
    """Рассчитывает вариативность паттерна"""
    sums = self._calculate_sums(df, field_col)
    return np.var(sums) / np.mean(sums) if sums and np.mean(sums) > 0 else 1.0

  def _get_field_max(self, field_num: int) -> int:
    """Получает максимальное число для поля"""
    from backend.app.core.data_manager import get_current_config
    config = get_current_config()
    return config.get(f'field{field_num}_max', 20)

  def _calculate_data_signature(self, df: pd.DataFrame) -> str:
    """Создает подпись данных для кэширования"""
    if df.empty:
      return "empty"
    latest_draw = df.iloc[0].get('Тираж', 0)
    data_size = len(df)
    return f"{latest_draw}_{data_size}"

  def _get_default_trends(self) -> Dict[str, TrendMetrics]:
    """Возвращает дефолтные тренды"""
    default_trend = TrendMetrics(
      hot_acceleration=[],
      cold_reversal=[],
      momentum_numbers=[],
      pattern_shift='stable',
      confidence_score=0.3,
      trend_strength=0.1
    )
    return {'field1': default_trend, 'field2': default_trend}

  def _get_default_combination_metrics(self) -> CombinationMetrics:
    """Возвращает дефолтные метрики комбинации"""
    return CombinationMetrics(
      trend_alignment=0.5,
      momentum_score=0.5,
      pattern_resonance=0.5,
      risk_assessment='medium',
      expected_performance=0.5
    )

  def get_trend_summary(self, trends: Dict[str, TrendMetrics]) -> str:
    """Создает текстовое описание трендов"""
    if not trends:
      return "Тренды не определены"

    summary_parts = []

    for field_name, trend in trends.items():
      field_num = field_name[-1]
      parts = [f"Поле {field_num}:"]

      if trend.hot_acceleration:
        parts.append(f"🔥 Горячие: {trend.hot_acceleration[:3]}")

      if trend.cold_reversal:
        parts.append(f"❄️ Готовы: {trend.cold_reversal[:2]}")

      if trend.momentum_numbers:
        parts.append(f"⚡ Импульс: {trend.momentum_numbers[:2]}")

      parts.append(f"📊 Сила: {trend.trend_strength:.1f}")
      parts.append(f"🎯 Паттерн: {trend.pattern_shift}")

      summary_parts.append(" ".join(parts))

    return " | ".join(summary_parts)


# Глобальный экземпляр анализатора трендов
GLOBAL_TREND_ANALYZER = DynamicTrendAnalyzer()


def analyze_combination_with_trends(field1: List[int], field2: List[int],
                                    df_history: pd.DataFrame) -> Tuple[float, str]:
  """
  Быстрая функция для оценки комбинации с учетом трендов

  Returns:
      Tuple[float, str]: (оценка_тренда, описание)
  """
  try:
    trends = GLOBAL_TREND_ANALYZER.analyze_current_trends(df_history)
    metrics = GLOBAL_TREND_ANALYZER.evaluate_combination(field1, field2, trends)

    description = f"Тренд: {metrics.expected_performance:.2f}, Риск: {metrics.risk_assessment}"

    return metrics.expected_performance, description

  except Exception as e:
    return 0.5, f"Ошибка анализа: {str(e)[:50]}"