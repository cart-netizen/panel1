import pandas as pd

from backend.app.core.utils import parse_numbers, format_numbers
from backend.app.core.data_manager import get_current_config


def _check_single_ticket_against_draw(user_numbers_f1, user_numbers_f2, winning_numbers_f1, winning_numbers_f2):
  """
  Helper to check one ticket against one winning draw.
  Returns: (matches_f1, matches_f2)
  """
  config = get_current_config()
  f1_size = config['field1_size']
  f2_size = config['field2_size']

  if not (isinstance(user_numbers_f1, list) and len(user_numbers_f1) == f1_size and
          isinstance(user_numbers_f2, list) and len(user_numbers_f2) == f2_size and
          isinstance(winning_numbers_f1, list) and len(winning_numbers_f1) == f1_size and
          isinstance(winning_numbers_f2, list) and len(winning_numbers_f2) == f2_size):
    return 0, 0

  matches_f1 = len(set(user_numbers_f1) & set(winning_numbers_f1))
  matches_f2 = len(set(user_numbers_f2) & set(winning_numbers_f2))
  return matches_f1, matches_f2

# def get_prize_category(matches_f1, matches_f2):
#   """
#   Determines the prize category based on matches in Field 1 and Field 2.
#   Based on user's specified categories: 2+0, 2+1, 2+2, 3+0, 3+1, 3+2, 3+3, 3+4, 4+4.
#   The order of checks is important (highest win first).
#
#   Args:
#       matches_f1 (int): Number of matches in Field 1.
#       matches_f2 (int): Number of matches in Field 2.
#
#   Returns:
#       str or None: Description of the prize category, or None if no win.
#   """
#   config = get_current_config()
#   lottery_type = config.get('db_table', '').replace('draws_', '')
#   if lottery_type == '4x20':
#     # Top tier
#     if matches_f1 == 4 and matches_f2 == 4: return "4+4 (Суперприз)"
#
#     # Next tiers (combinations involving 3 or 4 matches in one field)
#     if matches_f1 == 3 and matches_f2 == 4: return "3+4"  # User specified
#     if matches_f1 == 4 and matches_f2 == 3: return "4+3"  # Symmetric to above, often a category
#
#     if matches_f1 == 3 and matches_f2 == 3: return "3+3"  # User specified
#
#     if matches_f1 == 4 and matches_f2 == 2: return "4+2"
#     if matches_f1 == 2 and matches_f2 == 4: return "2+4"
#
#     if matches_f1 == 3 and matches_f2 == 2: return "3+2"  # User specified
#     if matches_f1 == 2 and matches_f2 == 3: return "2+3"
#
#     if matches_f1 == 4 and matches_f2 == 1: return "4+1"
#     if matches_f1 == 1 and matches_f2 == 4: return "1+4"
#
#     if matches_f1 == 3 and matches_f2 == 1: return "3+1"  # User specified
#     if matches_f1 == 1 and matches_f2 == 3: return "1+3"
#
#     if matches_f1 == 4 and matches_f2 == 0: return "4+0"
#     if matches_f1 == 0 and matches_f2 == 4: return "0+4"
#
#     if matches_f1 == 3 and matches_f2 == 0: return "3+0"  # User specified
#     if matches_f1 == 0 and matches_f2 == 3: return "0+3"
#
#     # Lower tiers (combinations involving 2 matches)
#     if matches_f1 == 2 and matches_f2 == 2: return "2+2"  # User specified
#     if matches_f1 == 2 and matches_f2 == 1: return "2+1"  # User specified
#     if matches_f1 == 1 and matches_f2 == 2: return "1+2"
#     if matches_f1 == 2 and matches_f2 == 0: return "2+0"  # User specified
#
#     return None  # No winning category based on the specified rules
#
#   elif lottery_type == '5x36plus':
#     # Логика для 5x36plus
#     if matches_f1 == 5 and matches_f2 == 1: return "5+1 (Суперприз)"
#     if matches_f1 == 5 and matches_f2 == 0: return "5+0"
#     if matches_f1 == 4: return "4+1" if matches_f2 == 1 else "4+0"
#     if matches_f1 == 3: return "3+1" if matches_f2 == 1 else "3+0"
#     if matches_f1 == 2: return "2+1" if matches_f2 == 1 else "2+0"
#
#   return None
def get_prize_category(matches_f1, matches_f2):
    """
    Determines the prize category based on matches, using rules from the current lottery config.
    The order of categories in the config is important (highest win first).
    """
    config = get_current_config()
    prize_categories = config.get('prize_categories', [])

    for category in prize_categories:
      f1_req = category.get('f1')
      f2_req = category.get('f2')

      # Проверка совпадений
      f1_match = (f1_req is None) or (matches_f1 == f1_req)
      f2_match = (f2_req is None) or (matches_f2 == f2_req)

      if f1_match and f2_match:
        return category.get('name')

    return None


def verify_ticket_against_history(user_f1_str, user_f2_str, df_history):
  """
  Verifies a single user ticket against all draws in history.
  """
  config = get_current_config()
  f1_size = config['field1_size']
  f2_size = config['field2_size']

  # parse_numbers теперь использует конфиг внутри себя
  user_numbers_f1 = parse_numbers(user_f1_str, field_num=1)
  user_numbers_f2 = parse_numbers(user_f2_str, field_num=2)

  if not user_numbers_f1 or not user_numbers_f2:
    return [{"Тираж": "Ошибка ввода",
             "Совпадения": f"Неверный формат номеров. Введите {f1_size} чисел в Поле 1 и {f2_size} в Поле 2.",
             "Категория": "-", "Дата тиража": "-", "Выигрышные номера": "-"}]

  results = []
  if df_history.empty:
    return [{"Тираж": "Информация", "Совпадения": "История тиражей пуста.",
             "Категория": "-", "Дата тиража": "-", "Выигрышные номера": "-"}]

  for _, draw in df_history.iterrows():
    winning_f1 = draw.get('Числа_Поле1_list')
    winning_f2 = draw.get('Числа_Поле2_list')
    draw_num = draw.get('Тираж')
    draw_date = draw.get('Дата').strftime('%Y-%m-%d') if pd.notnull(draw.get('Дата')) else 'N/A'

    if not (isinstance(winning_f1, list) and len(winning_f1) == f1_size and
            isinstance(winning_f2, list) and len(winning_f2) == f2_size):
      continue

    matches_f1, matches_f2 = _check_single_ticket_against_draw(user_numbers_f1, user_numbers_f2, winning_f1, winning_f2)
    prize_category = get_prize_category(matches_f1, matches_f2)

    if prize_category:
      results.append({
        "Тираж": draw_num,
        "Дата тиража": draw_date,
        "Выигрышные номера": f"Поле1: {format_numbers(winning_f1)}; Поле2: {format_numbers(winning_f2)}",
        "Совпадения": f"{matches_f1} (П1) + {matches_f2} (П2)",
        "Категория": prize_category
      })

  if not results:
    return [{"Тираж": "Без выигрыша",
             "Совпадения": "Ваша комбинация не выиграла ни в одном из прошедших тиражей.",
             "Категория": "-", "Дата тиража": "-", "Выигрышные номера": "-"}]
  return results


def verify_multiple_tickets_from_df(tickets_df, df_history):
  """
  Verifies multiple tickets from a DataFrame against historical draws.
  """
  all_results = []
  if tickets_df.empty:
    return [{"Билет": "Ошибка файла", "Совпадения": "Файл с билетами пуст.", "Категория": "-"}]

  if 'Поле1' not in tickets_df.columns or 'Поле2' not in tickets_df.columns:
    return [{"Билет": "Ошибка колонок", "Совпадения": "В CSV файле отсутствуют колонки 'Поле1' и/или 'Поле2'.",
             "Категория": "-"}]

  for index, ticket_row in tickets_df.iterrows():
    user_f1_str = str(ticket_row['Поле1'])
    user_f2_str = str(ticket_row['Поле2'])
    ticket_identifier = f"Билет {index + 1} ({user_f1_str} | {f2_str})"

    ticket_wins_or_info = verify_ticket_against_history(user_f1_str, user_f2_str, df_history)

    first_result = ticket_wins_or_info[0]
    if first_result.get("Тираж") in ["Ошибка ввода", "Информация", "Без выигрыша"]:
      all_results.append({
        "Билет": ticket_identifier,
        "Тираж": first_result.get("Тираж"),
        "Дата тиража": "-", "Выигрышные номера": "-",
        "Совпадения": first_result.get("Совпадения"),
        "Категория": first_result.get("Категория", "-")
      })
    else:
      for win_info in ticket_wins_or_info:
        all_results.append({"Билет": ticket_identifier, **win_info})

  if not all_results:
    return [{"Билет": "Нет данных", "Совпадения": "Проверка билетов не дала результатов.", "Категория": "-"}]

  return all_results