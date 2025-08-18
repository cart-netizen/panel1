# core/bankroll_manager.py
"""
Модуль для управления банкроллом и анализа финансовой эффективности стратегий.
Интегрируется с ticket_verifier для проверки выигрышей.
"""

import numpy as np
from collections import defaultdict

from backend.app.core.ticket_verifier import verify_ticket_against_history, get_prize_category, _check_single_ticket_against_draw
from backend.app.core.utils import format_numbers
from .data_manager import get_current_config


class BankrollManager:
  """Управление банкроллом и анализ стратегий"""

  def __init__(self, initial_bankroll=500000, ticket_cost=250):
    self.initial_bankroll = initial_bankroll
    self.current_bankroll = initial_bankroll  # ДОБАВИТЬ ЭТУ СТРОКУ
    self.ticket_cost = ticket_cost

  def update_bankroll(self, amount):
    """Обновляет текущий банкролл"""
    self.current_bankroll += amount
    return self.current_bankroll

  def calculate_kelly_criterion(self, win_probability, average_payout):
    """
    Рассчитывает оптимальный размер ставки по критерию Келли.

    Args:
        win_probability: Вероятность выигрыша (0-1)
        average_payout: Средний выигрыш при успехе

    Returns:
        float: Доля банкролла для ставки (0-1)
    """
    if win_probability <= 0 or win_probability >= 1:
      return 0.0

    if average_payout <= self.ticket_cost:
      return 0.0  # Отрицательное математическое ожидание

    # Формула Келли: f = (bp - q) / b
    # где b = коэффициент выплаты, p = вероятность выигрыша, q = 1-p
    b = (average_payout - self.ticket_cost) / self.ticket_cost
    p = win_probability
    q = 1 - p

    kelly_fraction = (b * p - q) / b

    # Ограничиваем для безопасности (четверть Келли)
    safe_kelly = max(0, min(kelly_fraction * 0.25, 0.1))  # Максимум 10% банкролла

    return safe_kelly

  def calculate_expected_value(self, combinations, df_history, sample_size=100):
    """
    Рассчитывает математическое ожидание для набора комбинаций.
    """
    if not combinations or df_history.empty:
      return {}

    config = get_current_config()
    prize_payouts = config.get('prize_payouts', {})

    test_df = df_history.head(sample_size) if len(df_history) >= sample_size else df_history
    total_cost = len(combinations) * self.ticket_cost
    total_winnings = 0
    wins_by_category = defaultdict(int)
    winning_draws = set()

    for f1, f2, _ in combinations:
      # Для EV-анализа нам не нужен полный verify_ticket_against_history,
      # так как он возвращает много лишней информации.
      # Оптимизируем, используя _check_single_ticket_against_draw.
      for _, draw in test_df.iterrows():
        winning_f1 = draw.get('Числа_Поле1_list')
        winning_f2 = draw.get('Числа_Поле2_list')

        matches_f1, matches_f2 = _check_single_ticket_against_draw(f1, f2, winning_f1, winning_f2)
        category = get_prize_category(matches_f1, matches_f2)
        if category:
          wins_by_category[category] += 1
          winning_draws.add(draw.get('Тираж'))
          total_winnings += prize_payouts.get(category, 0)

    profit = total_winnings - total_cost
    roi = (profit / total_cost) * 100 if total_cost > 0 else 0
    win_rate = (len(winning_draws) / len(test_df)) * 100 if len(test_df) > 0 else 0
    avg_win_per_draw = total_winnings / len(test_df) if len(test_df) > 0 else 0
    avg_cost_per_draw = total_cost

    return {
      'total_cost': total_cost, 'total_winnings': total_winnings, 'profit': profit,
      'roi_percent': roi, 'win_rate_percent': win_rate, 'winning_draws': len(winning_draws),
      'total_draws': len(test_df), 'wins_by_category': dict(wins_by_category),
      'expected_value_per_draw': avg_win_per_draw - avg_cost_per_draw,
      'combinations_tested': len(combinations)
    }

  def simulate_strategy_performance(self, strategy_func, df_history,
                                    initial_bankroll=None,
                                    num_draws_to_simulate=50,
                                    combos_per_draw=10):
    """
    Симулирует применение стратегии на исторических данных.

    Args:
        strategy_func: Функция генерации комбинаций (принимает df_history, возвращает комбинации)
        df_history: Полная история
        initial_bankroll: Начальный банкролл (если None, использует self.initial_bankroll)
        num_draws_to_simulate: Количество тиражей для симуляции
        combos_per_draw: Количество комбинаций на тираж

    Returns:
        dict: Результаты симуляции
    """
    if initial_bankroll is None:
      initial_bankroll = self.initial_bankroll

    config = get_current_config()
    prize_payouts = config.get('prize_payouts', {})  # Получаем выплаты из конфига

    if len(df_history) < num_draws_to_simulate + 50:
      return {'error': 'Недостаточно исторических данных для симуляции'}

    bankroll = initial_bankroll
    bankroll_history = [bankroll]
    draw_results = []
    total_spent = 0
    total_won = 0

    # Симулируем от старых к новым
    for i in range(num_draws_to_simulate - 1, -1, -1):
      # История до текущего момента
      history_before = df_history.iloc[i + 1:]
      current_draw = df_history.iloc[i]

      # Генерируем комбинации стратегией
      combinations = strategy_func(history_before, combos_per_draw)

      # Стоимость билетов
      draw_cost = len(combinations) * self.ticket_cost

      # Проверяем банкролл
      if bankroll < draw_cost:
        # Уменьшаем количество комбинаций
        max_combos = int(bankroll / self.ticket_cost)
        if max_combos == 0:
          break  # Банкрот
        combinations = combinations[:max_combos]
        draw_cost = max_combos * self.ticket_cost

      bankroll -= draw_cost
      total_spent += draw_cost

      # Проверяем выигрыши
      draw_winnings = 0
      wins = []

      winning_f1 = current_draw.get('Числа_Поле1_list')
      winning_f2 = current_draw.get('Числа_Поле2_list')

      if isinstance(winning_f1, list) and isinstance(winning_f2, list):
        for combo_f1, combo_f2, _ in combinations:
          matches_f1, matches_f2 = _check_single_ticket_against_draw(
            combo_f1, combo_f2, winning_f1, winning_f2
          )
          category = get_prize_category(matches_f1, matches_f2)
          if category:
            payout = prize_payouts.get(category, 0)  # Используем payouts из конфига
            draw_winnings += payout
            wins.append(category)

      bankroll += draw_winnings
      total_won += draw_winnings
      bankroll_history.append(bankroll)

      draw_results.append({
        'draw_num': current_draw.get('Тираж'),
        'spent': draw_cost,
        'won': draw_winnings,
        'profit': draw_winnings - draw_cost,
        'bankroll': bankroll,
        'wins': wins
      })

    # Вычисляем метрики
    final_profit = bankroll - initial_bankroll
    total_roi = (final_profit / initial_bankroll) * 100 if initial_bankroll > 0 else 0

    # Максимальная просадка
    peak = initial_bankroll
    max_drawdown = 0
    for value in bankroll_history:
      if value > peak:
        peak = value
      drawdown = (peak - value) / peak * 100 if peak > 0 else 0
      max_drawdown = max(max_drawdown, drawdown)

    # Коэффициент Шарпа (упрощенный)
    if len(bankroll_history) > 1:
      returns = np.diff(bankroll_history) / bankroll_history[:-1]
      sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252) if np.std(returns) > 0 else 0
    else:
      sharpe_ratio = 0

    return {
      'initial_bankroll': initial_bankroll,
      'final_bankroll': bankroll,
      'total_profit': final_profit,
      'total_roi_percent': total_roi,
      'total_spent': total_spent,
      'total_won': total_won,
      'max_drawdown_percent': max_drawdown,
      'sharpe_ratio': sharpe_ratio,
      'num_draws': len(draw_results),
      'bankroll_history': bankroll_history,
      'draw_results': draw_results,
      'went_broke': bankroll < self.ticket_cost
    }

  def get_optimal_combo_count(self, current_bankroll, confidence_level=0.95):
    """
    Рассчитывает оптимальное количество комбинаций на основе банкролла.

    Args:
        current_bankroll: Текущий банкролл
        confidence_level: Уровень уверенности (0.95 = хватит на 20 тиражей)

    Returns:
        int: Рекомендуемое количество комбинаций
    """
    # Хотим, чтобы денег хватило минимум на 20 тиражей
    min_draws = 20

    # Максимум, что можем потратить на один тираж
    max_per_draw = current_bankroll / min_draws

    # Количество билетов
    optimal_count = int(max_per_draw / self.ticket_cost)

    # Ограничения
    return max(1, min(optimal_count, 20))  # От 1 до 20 билетов

  def analyze_number_profitability(self, df_history, lookback=100):
    """
    Анализирует "прибыльность" чисел методом разделения выигрыша (Win Share).
    Чем чаще число появляется в комбинациях с высоким теоретическим выигрышем,
    тем выше его итоговый рейтинг.
    """
    config = get_current_config()
    prize_payouts = config.get('prize_payouts', {})

    # Определяем полный диапазон чисел для анализа
    all_possible_numbers = set(range(1, config['field1_max'] + 1)) | set(range(1, config['field2_max'] + 1))

    test_df = df_history.head(lookback)
    if test_df.empty:
      return []

    # Инициализируем статистику для каждого возможного числа
    number_stats = {num: {'appearances': 0, 'total_win_share': 0.0} for num in all_possible_numbers}

    # 1. Проходим по каждому историческому тиражу
    for _, draw in test_df.iterrows():
      winning_f1 = draw.get('Числа_Поле1_list', [])
      winning_f2 = draw.get('Числа_Поле2_list', [])

      if not winning_f1 and not winning_f2:
        continue

      # 2. Определяем теоретический максимальный выигрыш для этой комбинации
      # Для этого "проверяем" комбинацию саму на себя, чтобы получить высшую категорию
      matches_f1 = len(winning_f1)
      matches_f2 = len(winning_f2)
      top_category = get_prize_category(matches_f1, matches_f2)

      if not top_category:
        continue

      payout = prize_payouts.get(top_category, 0)

      # 3. Разделяем выигрыш между всеми числами в комбинации
      all_winning_numbers = winning_f1 + winning_f2
      total_numbers_in_combo = len(all_winning_numbers)

      if total_numbers_in_combo == 0:
        continue

      win_share_per_number = payout / total_numbers_in_combo

      # 4. Накапливаем статистику для каждого числа из этой комбинации
      for num in all_winning_numbers:
        if num in number_stats:
          number_stats[num]['appearances'] += 1
          number_stats[num]['total_win_share'] += win_share_per_number

    # 5. Формируем итоговый результат
    profitability = []
    for num, stats in number_stats.items():
      appearances = stats['appearances']
      total_win_share = stats['total_win_share']

      # Рассчитываем средний "вклад" в выигрыш на одно появление
      avg_payout_contribution = total_win_share / appearances if appearances > 0 else 0

      profitability.append({
        'number': num,
        'appearances': appearances,
        'avg_payout_contribution': round(avg_payout_contribution, 2),
        'total_win_share': round(total_win_share, 2)
      })

    # Сортируем по самому главному показателю - среднему вкладу в выигрыш
    profitability.sort(key=lambda x: x['avg_payout_contribution'], reverse=True)

    return profitability

  def calculate_kelly_bet(self, win_probability: float, odds: float, fraction: float = 0.25) -> float:
    """
    Расчёт ставки по критерию Келли

    Args:
        win_probability: Вероятность выигрыша (0-1)
        odds: Коэффициент выплаты
        fraction: Доля от полного Келли (обычно 0.25 для безопасности)

    Returns:
        Размер ставки
    """
    if win_probability <= 0 or win_probability >= 1:
      return self.ticket_cost

      # Формула Келли: f = (bp - q) / b
    b = odds - 1
    p = win_probability
    q = 1 - p

    kelly_fraction = (b * p - q) / b if b > 0 else 0
    kelly_fraction = kelly_fraction * fraction

    if kelly_fraction <= 0:
      return self.ticket_cost

    bet_size = self.current_bankroll * kelly_fraction
    return max(self.ticket_cost, min(bet_size, self.current_bankroll * 0.1))


  def calculate_bet_size(self, strategy, win_probability=0.05, odds=100, current_streak=0):
    """Расчёт размера ставки в зависимости от стратегии"""
    from enum import Enum

    # Если strategy это строка, преобразуем в enum
    if isinstance(strategy, str):
      strategy_map = {
        'FIXED': 'fixed',
        'KELLY': 'kelly',
        'PERCENTAGE': 'percentage',
        'MARTINGALE': 'martingale',
        'FIBONACCI': 'fibonacci'
      }
      strategy_str = strategy_map.get(strategy, strategy.lower())
    else:
      strategy_str = strategy.value.lower() if hasattr(strategy, 'value') else str(strategy).lower()

    if strategy_str == 'kelly':
      return self.calculate_kelly_bet(win_probability, odds)
    elif strategy_str == 'percentage':
      return self.current_bankroll * 0.02  # 2% от банкролла
    elif strategy_str == 'martingale':
      base_bet = self.ticket_cost
      bet = base_bet * (2 ** current_streak)
      return min(bet, self.current_bankroll * 0.5)
    elif strategy_str == 'fibonacci':
      fib_sequence = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55]
      fib_index = min(current_streak, len(fib_sequence) - 1)
      bet = self.ticket_cost * fib_sequence[fib_index]
      return min(bet, self.current_bankroll * 0.3)
    else:  # fixed
      return self.ticket_cost

# Глобальный экземпляр менеджера банкролла
GLOBAL_BANKROLL_MANAGER = BankrollManager()