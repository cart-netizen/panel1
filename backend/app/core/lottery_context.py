# core/lottery_context.py
"""
Контекстный менеджер для работы с разными лотереями
"""
from contextlib import contextmanager

from backend.app.core.data_manager import set_current_lottery, CURRENT_LOTTERY


class LotteryContext:
  """Контекстный менеджер для временного переключения лотереи"""

  def __init__(self, lottery_type):
    self.lottery_type = lottery_type
    self.old_lottery = None

  def __enter__(self):
    from backend.app.core.data_manager import CURRENT_LOTTERY
    self.old_lottery = CURRENT_LOTTERY
    set_current_lottery(self.lottery_type)
    return self

  def __exit__(self, exc_type, exc_val, exc_tb):
    if self.old_lottery:
      set_current_lottery(self.old_lottery)


def get_lottery_from_pathname(pathname):
  """Определяет тип лотереи на основе URL pathname"""
  if pathname == '/5x36plus':
    return '5x36plus'
  elif pathname == '/4x20':
    return '4x20'
  else:
    return CURRENT_LOTTERY or '4x20'  # По умолчанию


@contextmanager
def lottery_context(lottery_type):
    """Функция-контекст для временного переключения лотереи"""
    previous = CURRENT_LOTTERY
    set_current_lottery(lottery_type)
    try:
        yield
    finally:
        if previous:
            set_current_lottery(previous)