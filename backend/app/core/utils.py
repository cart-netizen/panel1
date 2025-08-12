import re
import pandas as pd
import random
from datetime import datetime, timedelta
import numpy as np


# Импорт data_manager убран с верхнего уровня, чтобы разорвать цикл.

def parse_numbers(numbers_str, field_num=1):
  """
  Разбирает строку чисел в отсортированный список уникальных целых чисел.
  Правила (количество, макс. число) берутся из конфигурации текущей лотереи.
  """
  # --- ИСПРАВЛЕНИЕ: Импорт выполняется здесь, во время выполнения функции, а не при загрузке модуля ---
  from .data_manager import get_current_config

  config = get_current_config()
  expected_count = config.get(f'field{field_num}_size')
  max_num = config.get(f'field{field_num}_max')

  if not numbers_str or not isinstance(numbers_str, str):
    return []
  try:
    processed_str = re.sub(r'[,;\s]+', ' ', numbers_str.strip())
    nums_str_list = processed_str.split(' ')

    nums = []
    for n_str in nums_str_list:
      if n_str:
        num = int(n_str)
        if 1 <= num <= max_num:
          nums.append(num)
        else:
          return []  # Число вне допустимого диапазона

    unique_nums = sorted(list(set(nums)))

    if len(unique_nums) == expected_count:
      return unique_nums
    else:
      return []
  except ValueError:
    return []


def format_numbers(numbers_list):
  """
  Форматирует список чисел в строку с числами, разделенными запятыми и отсортированными.
  """
  if not isinstance(numbers_list, (list, np.ndarray)):
    return ""

  processed_ints = []
  for item in numbers_list:
    if isinstance(item, (int, np.integer)):
      processed_ints.append(int(item))
    elif isinstance(item, (float, np.floating)) and item.is_integer():
      processed_ints.append(int(item))

  if not processed_ints:
    return ""

  return ",".join(map(str, sorted(list(set(processed_ints)))))

def generate_sample_draws(num_draws=100):
  """
  Генерирует примерные данные тиражей. Динамически использует конфигурацию.
  """
  from .data_manager import get_current_config
  config = get_current_config()

  data = []
  start_date = datetime.now() - timedelta(days=num_draws * 3)
  latest_draw_number = 10000 + num_draws

  for i in range(num_draws):
    field1 = sorted(random.sample(range(1, config['field1_max'] + 1), config['field1_size']))
    field2 = sorted(random.sample(range(1, config['field2_max'] + 1), config['field2_size']))
    prize = random.choice([0, 0, 0, 50, 100, 200, 500, 1000, 5000])
    draw_date = start_date + timedelta(days=i * 3)
    data.append({
      "Дата": draw_date.strftime('%Y-%m-%d'),
      "Тираж": latest_draw_number - i,
      "Числа_Поле1": format_numbers(field1),
      "Числа_Поле2": format_numbers(field2),
      "Приз": prize
    })
  return pd.DataFrame(data)