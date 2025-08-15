import pandas as pd
import sqlite3
import requests
from backend.app.core.utils import format_numbers
from datetime import datetime
import os

import time
import random
from itertools import cycle
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
import json

# Импортируем модели PostgreSQL
from backend.app.core.database import LotteryDraw, SessionLocal, get_db, DATABASE_URL

LOTTERY_CONFIGS = {
    '4x20': {
        'db_table': 'draws_4x20',
        'api_url': 'https://www.stoloto.ru/p/api/mobile/api/v35/service/draws/archive?game=4x20&count={limit}&page={page_num}',
        'field1_size': 4,
        'field2_size': 4,
        'field1_max': 20,
        'field2_max': 20,
        'prize_categories': [
            {'f1': 4, 'f2': 4, 'name': "4+4 (Суперприз)"},
            {'f1': 4, 'f2': 3, 'name': "4+3"}, {'f1': 3, 'f2': 4, 'name': "3+4"},
            {'f1': 4, 'f2': 2, 'name': "4+2"}, {'f1': 2, 'f2': 4, 'name': "2+4"},
            {'f1': 3, 'f2': 3, 'name': "3+3"},
            {'f1': 4, 'f2': 1, 'name': "4+1"}, {'f1': 1, 'f2': 4, 'name': "1+4"},
            {'f1': 3, 'f2': 2, 'name': "3+2"}, {'f1': 2, 'f2': 3, 'name': "2+3"},
            {'f1': 4, 'f2': 0, 'name': "4+0"}, {'f1': 0, 'f2': 4, 'name': "0+4"},
            {'f1': 3, 'f2': 1, 'name': "3+1"}, {'f1': 1, 'f2': 3, 'name': "1+3"},
            {'f1': 3, 'f2': 0, 'name': "3+0"}, {'f1': 0, 'f2': 3, 'name': "0+3"},
            {'f1': 2, 'f2': 2, 'name': "2+2"},
            {'f1': 2, 'f2': 1, 'name': "2+1"}, {'f1': 1, 'f2': 2, 'name': "1+2"},
            {'f1': 2, 'f2': 0, 'name': "2+0"}, {'f1': 0, 'f2': 2, 'name': "0+2"},
        ],
        'prize_payouts': {
            "4+4 (Суперприз)": 100000000, "4+3": 100000, "3+4": 100000,
            "4+2": 17000, "2+4": 17000, "3+3": 3000, "4+1": 21000, "1+4": 21000,
            "3+2": 2500, "2+3": 2500, "4+0": 20000, "0+4": 20000, "3+1": 700,
            "1+3": 700, "3+0": 1400, "0+3": 1400, "2+2": 580, "2+1": 300,
            "1+2": 300, "2+0": 350, "0+2": 350
        }
    },
    '5x36plus': {
        'db_table': 'draws_5x36plus',
        'api_url': 'https://www.stoloto.ru/p/api/mobile/api/v35/service/draws/archive?game=5x36plus&count={limit}&page={page_num}',
        'field1_size': 5,
        'field2_size': 1,
        'field1_max': 36,
        'field2_max': 4,
        'prize_categories': [
            {'f1': 5, 'f2': 1, 'name': "5+1 (Суперприз)"},
            {'f1': 5, 'f2': 0, 'name': "5+0"},
            {'f1': 4, 'f2': None, 'name': "4 угаданных"}, # None означает "любое количество совпадений"
            {'f1': 3, 'f2': None, 'name': "3 угаданных"},
            {'f1': 2, 'f2': None, 'name': "2 угаданных"},
        ],
        'prize_payouts': {
            "5+1 (Суперприз)": 3000000, "5+0": 100000, "4 угаданных": 1000,
            "3 угаданных": 200, "2 угаданных": 50,
        }
    }
}


CURRENT_LOTTERY = '4x20'
# Глобальная переменная для хранения статистики инициализации
LAST_INITIALIZATION_STATS = None

def set_current_lottery(lottery_type):
  """Устанавливает текущую лотерею"""
  global CURRENT_LOTTERY
  if lottery_type in LOTTERY_CONFIGS:
    CURRENT_LOTTERY = lottery_type
    return True
  return False

def get_db_session():
  """Получает сессию PostgreSQL"""
  return SessionLocal()

def get_current_config():
  """Возвращает конфигурацию текущей лотереи"""
  return LOTTERY_CONFIGS[CURRENT_LOTTERY]

# DB_PATH = os.path.join('data', 'lottery_draws.db')
# TABLE_NAME = 'draws_4x20'

def get_db_path():
  return os.path.join('data', f'lottery_{CURRENT_LOTTERY}.db')


def get_table_name():
  return get_current_config()['db_table']

LOTTERY_DATA_LIMITS = {
    '4x20': {
        'max_draws_in_db': 1000,        # 4x20 проводится 7 раз в день = ~2555 в год
        'initial_fetch': 40,          # При первой загрузке
        'update_fetch': 50,            # При обновлениях
        'min_for_training': 200        # Минимум для качественного обучения
    },
    '5x36plus': {
        'max_draws_in_db': 2000,       # Каждые 15 мин = ~35000 в год, берем последние 1000
        'initial_fetch': 40,          # При первой загрузке
        'update_fetch': 100,           # При обновлениях
        'min_for_training': 300        # Минимум для качественного обучения
    }
}

def get_lottery_limits():
    """Получает лимиты для текущей лотереи"""
    return LOTTERY_DATA_LIMITS.get(CURRENT_LOTTERY, LOTTERY_DATA_LIMITS['4x20'])

# Для обратной совместимости
MAX_DRAWS_IN_DB = 500
STOLOTO_MOBILE_ARCHIVE_API_URL = "https://www.stoloto.ru/p/api/mobile/api/v35/service/draws/archive?game=4x20&count={limit}&page={page_num}"


def init_db():
  """Инициализация PostgreSQL (таблицы уже созданы при миграции)"""
  from backend.app.core.database import create_tables
  try:
    create_tables()
    print(f"PostgreSQL готов для {CURRENT_LOTTERY}")
    return True
  except Exception as e:
    print(f"ОШИБКА подключения к PostgreSQL: {e}")
    return False


def scrape_stoloto_archive(num_draws_to_fetch=MAX_DRAWS_IN_DB, lottery_type=None):
  """
  Fetches recent lottery draws from the Stoloto mobile API.
  """
  if lottery_type is None:
    lottery_type = CURRENT_LOTTERY
  config = LOTTERY_CONFIGS.get(lottery_type, get_current_config())
  api_url_template = config['api_url']
  field1_size = config['field1_size']
  field2_size = config['field2_size']

  print(f"Attempting to load {num_draws_to_fetch} most recent draws for {lottery_type}...")

  all_fetched_draws_data = []
  remaining_to_fetch = num_draws_to_fetch
  current_page = 1
  draws_per_request_limit = 30
  max_pages_to_try = (num_draws_to_fetch // draws_per_request_limit) + 2

  # Улучшенная защита от блокировки
  successful_pages = 0
  consecutive_failures = 0
  max_consecutive_failures = 3

  while remaining_to_fetch > 0 and current_page <= max_pages_to_try and consecutive_failures < max_consecutive_failures:
    limit_for_this_request = min(remaining_to_fetch, draws_per_request_limit)
    url = api_url_template.format(limit=limit_for_this_request, page_num=current_page)
    print(f"Requesting data from page {current_page}: {url}")

    try:
      # Увеличиваем задержки для избежания блокировки
      if current_page > 1:
        delay = min(5 + (current_page - 1) * 2, 15)  # От 5 до 15 секунд
        print(f"Waiting {delay} seconds before page {current_page} to avoid blocking...")
        time.sleep(delay)

      # Рандомизируем User-Agent для обхода блокировки
      user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0'
      ]

      headers = {
        'Accept': 'application/json, text/plain, */*',
        'Device-Platform': 'DESKTOP',
        'Device-Type': 'STOLOTO',
        'Gosloto-Partner': 'bXMjXFRXZ3coWXh6R3s1NTdUX3dnWlBMLUxmdg',
        'Gosloto-Token': '25813cf100-c6dc62-475a85-bf6a46-ef05d300addf06',
        'Referer': 'https://www.stoloto.ru/4x20/archive',
        'Sec-Ch-Ua': '"Opera GX";v="120", "Not-A.Brand";v="8", "Chromium";v="135"',
        'Sec-Ch-Ua-Mobile': '?0',
        'Sec-Ch-Ua-Platform': '"Windows"',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 OPR/120.0.0.0 (Edition Yx GX)'
      }

      response = requests.get(url, headers=headers, timeout=30)

      if response.status_code == 403:
        consecutive_failures += 1
        print(f"403 Forbidden on page {current_page}. Consecutive failures: {consecutive_failures}")

        if consecutive_failures < max_consecutive_failures:
          print(f"Waiting {30 + consecutive_failures * 30} seconds before retry...")
          time.sleep(30 + consecutive_failures * 30)  # Увеличиваем задержку
          continue
        else:
          print(f"Too many consecutive failures ({consecutive_failures}). Stopping requests.")
          break

      response.raise_for_status()
      consecutive_failures = 0  # Сбрасываем счетчик при успехе
      json_data = response.json()

      if json_data.get("requestStatus") != "success" or "draws" not in json_data:
        print(
          f"Error in API response (page {current_page}): status '{json_data.get('requestStatus')}' or 'draws' key missing.")
        print(f"API Response: {json_data}")
        break

      api_page_draws = json_data["draws"]
      if not api_page_draws:
        print(f"No more draws found on page {current_page}.")
        break

      for draw_item in api_page_draws:
        draw_id = draw_item.get("number")
        draw_date_raw = draw_item.get("date")
        winning_combination_raw = draw_item.get("winningCombination")
        draw_status = draw_item.get("status")

        if draw_status != "COMPLETED":
          print(f"Skipping draw {draw_id}: status '{draw_status}' (not COMPLETED).")
          continue

        expected_total_numbers = field1_size + field2_size
        if not (draw_id and draw_date_raw and winning_combination_raw and
                isinstance(winning_combination_raw, list) and len(winning_combination_raw) == expected_total_numbers):
          print(f"Skipping draw {draw_id}: missing or incorrect key data.")
          continue

        try:
          # Process date string
          if len(draw_date_raw) == 24 and draw_date_raw[-5] in ['+', '-'] and draw_date_raw[-3] != ':':
            draw_date_processed = draw_date_raw[:-2] + ":" + draw_date_raw[-2:]
          else:
            draw_date_processed = draw_date_raw
          draw_date_obj = datetime.fromisoformat(draw_date_processed)
          draw_date_formatted = draw_date_obj.strftime('%Y-%m-%d')
        except ValueError as ve:
          print(f"Error parsing date for draw {draw_id}: '{draw_date_raw}'. Error: {ve}")
          continue

        # Parse numbers according to lottery configuration
        numbers_f1 = sorted([int(n) for n in winning_combination_raw[:field1_size]])
        numbers_f2 = sorted([int(n) for n in winning_combination_raw[field1_size:field1_size + field2_size]])

        all_fetched_draws_data.append({
          "Дата": draw_date_formatted,
          "Тираж": int(draw_id),
          "Числа_Поле1": format_numbers(numbers_f1),
          "Числа_Поле2": format_numbers(numbers_f2),
          "Приз": 0
        })
        remaining_to_fetch -= 1
        if remaining_to_fetch <= 0:
          break

      if remaining_to_fetch <= 0:
        break
      current_page += 1
      if not api_page_draws or len(api_page_draws) < limit_for_this_request:
        print(f"Fetched {len(api_page_draws)} draws on page {current_page - 1}, likely all available.")
        break
      time.sleep(2)  # Пауза между запросами

    except requests.exceptions.RequestException as e:
      print(f"Network error during data request (page {current_page}): {e}")
      break
    except ValueError as e:
      print(f"Error decoding JSON response (page {current_page}): {e}")
      if 'response' in locals():
        print(f"Response text: {response.text}")
      break
    except Exception as e:
      print(f"Unexpected error during scraping (page {current_page}): {e}")
      break

  if all_fetched_draws_data:
    print(f"Successfully fetched and processed {len(all_fetched_draws_data)} draws from API.")
  else:
    print("No draws were fetched. Check API URL, structure, and internet connection.")

  return pd.DataFrame(all_fetched_draws_data)


def store_draws_to_db(df, lottery_type=None):
  """
  Сохраняет DataFrame тиражей в PostgreSQL.
  Обрабатывает дубликаты и соблюдает лимиты.
  """
  if lottery_type is None:
    lottery_type = CURRENT_LOTTERY

  if df.empty:
    print("PostgreSQL Store: Нет данных для сохранения")
    return

  config = get_current_config()
  limits = get_lottery_limits()
  max_draws = limits['max_draws_in_db']

  db = get_db_session()
  try:
    # Проверяем и удаляем возможные дубликаты в таблице
    from sqlalchemy import func
    duplicates = db.query(
      LotteryDraw.draw_number,
      func.count(LotteryDraw.draw_number).label('count')
    ).filter(
      LotteryDraw.lottery_type == lottery_type
    ).group_by(
      LotteryDraw.draw_number
    ).having(
      func.count(LotteryDraw.draw_number) > 1
    ).all()

    if duplicates:
      print(f"⚠️ Обнаружены дубликаты для {lottery_type}: {[d[0] for d in duplicates]}")
      # Удаляем дубликаты, оставляя только последнюю запись
      for dup_number, count in duplicates:
        dup_records = db.query(LotteryDraw).filter(
          LotteryDraw.lottery_type == lottery_type,
          LotteryDraw.draw_number == dup_number
        ).order_by(LotteryDraw.created_at.desc()).all()

        # Удаляем все кроме первой (самой новой)
        for record in dup_records[1:]:
          db.delete(record)

      db.commit()
      print(f"✅ Дубликаты удалены для {lottery_type}")

    # Подготавливаем записи для вставки
    new_records = []

    for _, row in df.iterrows():
      try:
        # Парсим числа из строкового формата
        field1_str = str(row.get('Числа_Поле1', ''))
        field2_str = str(row.get('Числа_Поле2', ''))

        field1_numbers = [int(x.strip()) for x in field1_str.split(',') if x.strip().isdigit()]
        field2_numbers = [int(x.strip()) for x in field2_str.split(',') if x.strip().isdigit()]

        # Валидация размеров
        if (len(field1_numbers) != config['field1_size'] or
            len(field2_numbers) != config['field2_size']):
          continue

        # Парсим дату
        date_str = str(row.get('Дата', ''))
        try:
          draw_date = pd.to_datetime(date_str).to_pydatetime()
        except:
          draw_date = datetime.now()

        draw_number = int(row.get('Тираж', 0))

        # Проверяем, есть ли уже такой тираж
        existing = db.query(LotteryDraw).filter(
          LotteryDraw.lottery_type == lottery_type,
          LotteryDraw.draw_number == draw_number
        ).first()

        if not existing:
          record = LotteryDraw(
            lottery_type=lottery_type,
            draw_number=draw_number,
            draw_date=draw_date,
            field1_numbers=field1_numbers,
            field2_numbers=field2_numbers,
            prize_info={'amount': float(row.get('Приз', 0))},
            created_at=datetime.now()
          )
          new_records.append(record)

      except Exception as e:
        print(f"PostgreSQL Store: Ошибка обработки записи: {e}")
        continue

    # Сохраняем новые записи
    if new_records:
      db.add_all(new_records)
      db.commit()
      print(f"PostgreSQL Store: Добавлено {len(new_records)} новых тиражей для {lottery_type}")
    else:
      print(f"PostgreSQL Store: Все тиражи уже существуют в БД для {lottery_type}")

    # Применяем лимит записей
    total_count = db.query(LotteryDraw).filter(
      LotteryDraw.lottery_type == lottery_type
    ).count()

    if total_count > max_draws:
      # Удаляем самые старые тиражи
      excess = total_count - max_draws
      oldest_draws = db.query(LotteryDraw).filter(
        LotteryDraw.lottery_type == lottery_type
      ).order_by(LotteryDraw.draw_number.asc()).limit(excess).all()

      for draw in oldest_draws:
        db.delete(draw)

      db.commit()
      print(f"PostgreSQL Store: Удалено {excess} старых тиражей, лимит: {max_draws}")

    final_count = db.query(LotteryDraw).filter(
      LotteryDraw.lottery_type == lottery_type
    ).count()
    print(f"PostgreSQL Store: Итого тиражей в БД: {final_count}")

  except SQLAlchemyError as e:
    db.rollback()
    print(f"PostgreSQL Store: Ошибка БД: {e}")
  except Exception as e:
    print(f"PostgreSQL Store: Неожиданная ошибка: {e}")
  finally:
    db.close()


def import_csv_data(csv_file_path, lottery_type):
  """
  Импортирует данные из CSV файла для любой лотереи с автоопределением кодировки
  """
  old_lottery = globals().get('CURRENT_LOTTERY', '4x20')
  set_current_lottery(lottery_type)
  # Устанавливаем лотерею ПЕРЕД получением конфигурации
  if not set_current_lottery(lottery_type):
    print(f"Ошибка: неизвестный тип лотереи {lottery_type}")
    return pd.DataFrame()
  config = get_current_config()
  print(f"Импорт для лотереи {lottery_type}, конфигурация: поле1={config['field1_size']}, поле2={config['field2_size']}")


  def try_read_file(file_path, encodings=['utf-8', 'windows-1251', 'cp1251', 'iso-8859-1']):
    """Пытается прочитать файл с разными кодировками"""
    for encoding in encodings:
      try:
        with open(file_path, 'r', encoding=encoding) as file:
          content = file.read()
          print(f"Успешно прочитан файл с кодировкой: {encoding}")
          return content.splitlines(), encoding
      except UnicodeDecodeError:
        print(f"Не удалось прочитать с кодировкой {encoding}")
        continue
    raise UnicodeDecodeError("Не удалось определить кодировку файла")

  try:
    df_list = []
    expected_numbers = config['field1_size'] + config['field2_size']
    print(f"Ожидается {expected_numbers} чисел ({config['field1_size']}+{config['field2_size']})")

    # Читаем файл с автоопределением кодировки
    lines, used_encoding = try_read_file(csv_file_path)
    print(f"Используется кодировка: {used_encoding}")

    for line_num, line in enumerate(lines, 1):
      line = line.strip()
      if not line:
        continue

      # Пропускаем заголовок CSV
      if line_num == 1 and ('тираж' in line.lower() or 'дата' in line.lower() or 'числа' in line.lower()):
        print(f"Пропуск строки {line_num}: заголовок CSV")
        continue

      # Более гибкий парсинг строки
      # Ищем последнюю кавычку для чисел
      if '"' in line:
        # Формат: номер,дата,"числа"
        last_quote = line.rfind('"')
        if last_quote > 0:
          first_quote = line.rfind('"', 0, last_quote)
          if first_quote >= 0:
            numbers_str = line[first_quote + 1:last_quote]
            prefix = line[:first_quote - 1]  # убираем запятую перед кавычкой
            parts = prefix.split(',', 1)  # разделяем на номер и дату
          else:
            parts = line.split(',', 2)
            numbers_str = parts[2].strip('"') if len(parts) > 2 else ""
        else:
          parts = line.split(',', 2)
          numbers_str = parts[2].strip('"') if len(parts) > 2 else ""
      else:
        parts = line.split(',', 2)
        numbers_str = parts[2] if len(parts) > 2 else ""

      if len(parts) < 2:
        print(f"Пропуск строки {line_num}: недостаточно частей")
        continue

      try:
        draw_num = int(parts[0].strip())
        datetime_str = parts[1].strip()

        # Парсим дату (поддерживаем разные форматы)
        date_obj = None
        date_formats = [
          '%d.%m.%Y %H:%M',
          '%Y-%m-%d %H:%M:%S',
          '%Y-%m-%d %H:%M',
          '%d/%m/%Y %H:%M',
          '%d.%m.%Y',
          '%Y-%m-%d'
        ]

        for fmt in date_formats:
          try:
            date_obj = datetime.strptime(datetime_str, fmt)
            break
          except ValueError:
            continue

        if not date_obj:
          print(f"Пропуск строки {line_num}: не удалось распарсить дату '{datetime_str}'")
          continue

        date_formatted = date_obj.strftime('%Y-%m-%d')

        # Парсим числа более тщательно
        numbers = []
        for n in numbers_str.split(','):
          n = n.strip()
          if n.isdigit():
            numbers.append(int(n))

        if len(numbers) < expected_numbers:
          print(f"Пропуск строки {line_num}: недостаточно чисел ({len(numbers)} < {expected_numbers})")
          print(f"  Строка: {line}")
          print(f"  Числа: {numbers_str}")
          continue

        # Проверяем диапазоны чисел
        field1_nums = numbers[:config['field1_size']]
        field2_nums = numbers[config['field1_size']:config['field1_size'] + config['field2_size']]

        # Валидация диапазонов
        if not all(1 <= n <= config['field1_max'] for n in field1_nums):
          print(f"Пропуск строки {line_num}: числа поля 1 вне диапазона 1-{config['field1_max']}")
          print(f"  Поле 1: {field1_nums}")
          continue

        if not all(1 <= n <= config['field2_max'] for n in field2_nums):
          print(f"Пропуск строки {line_num}: числа поля 2 вне диапазона 1-{config['field2_max']}")
          print(f"  Поле 2: {field2_nums}")
          continue

        df_list.append({
          "Дата": date_formatted,
          "Тираж": draw_num,
          "Числа_Поле1": format_numbers(sorted(field1_nums)),
          "Числа_Поле2": format_numbers(sorted(field2_nums)),
          "Приз": 0
        })

        # Выводим первые несколько успешных строк для отладки
        if len(df_list) <= 3:
          print(f"Успешно обработана строка {line_num}: тираж {draw_num}, дата {date_formatted}")
          print(f"  Поле 1: {field1_nums}, Поле 2: {field2_nums}")
          if df_list:
            df = pd.DataFrame(df_list)
            store_draws_to_db(df)  # Теперь использует PostgreSQL
            print(f"Импортировано {len(df_list)} тиражей из CSV для лотереи {lottery_type}")
            return df
          else:
            print(f"Не удалось импортировать данные из CSV для лотереи {lottery_type}")
            return pd.DataFrame()

      except (ValueError, IndexError) as e:
        print(f"Пропуск строки {line_num}: ошибка парсинга - {e}")
        print(f"  Строка: {line}")
        continue

    if df_list:
      df = pd.DataFrame(df_list)
      store_draws_to_db(df)
      print(f"Импортировано {len(df_list)} тиражей из CSV для лотереи {lottery_type}")
      return df
    else:
      print(f"Не удалось импортировать данные из CSV для лотереи {lottery_type}")
      return pd.DataFrame()

  except Exception as e:
    print(f"Ошибка при импорте CSV: {e}")
    return pd.DataFrame()

  finally:
    set_current_lottery(old_lottery)


USER_AGENTS = [
  'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
  'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
  'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
]


def scrape_with_pagination_protection(api_url_template, max_pages=20):
  """
  Скрейпинг с защитой от блокировки пагинации
  """
  all_data = []
  user_agents = cycle(USER_AGENTS)

  for page in range(1, max_pages + 1):
    try:
      headers = {
        'User-Agent': next(user_agents),
        'Accept': 'application/json',
        'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
        'Referer': 'https://www.stoloto.ru/',
        'X-Requested-With': 'XMLHttpRequest'
      }

      url = api_url_template.format(limit=30, page_num=page)

      # Случайная задержка между запросами
      time.sleep(random.uniform(2, 5))

      response = requests.get(url, headers=headers, timeout=15)

      if response.status_code == 403:
        print(f"Получена 403 ошибка на странице {page}, прекращаем запросы")
        break

      response.raise_for_status()
      data = response.json()

      if data.get("requestStatus") != "success":
        break

      page_draws = data.get("draws", [])
      if not page_draws:
        break

      all_data.extend(page_draws)
      print(f"Загружена страница {page}, получено {len(page_draws)} тиражей")

    except Exception as e:
      print(f"Ошибка на странице {page}: {e}")
      break

  return all_data


def fetch_draws_from_db(date_start=None, date_end=None, draw_start=None, draw_end=None):
  """
  Загружает тиражи из PostgreSQL с фильтрами.
  Возвращает DataFrame с колонками списков чисел.
  """
  db = get_db_session()
  try:
    # Строим запрос
    query = db.query(LotteryDraw).filter(
      LotteryDraw.lottery_type == CURRENT_LOTTERY
    )

    # Применяем фильтры
    if date_start:
      query = query.filter(LotteryDraw.draw_date >= pd.to_datetime(date_start))
    if date_end:
      query = query.filter(LotteryDraw.draw_date <= pd.to_datetime(date_end))
    if draw_start is not None:
      query = query.filter(LotteryDraw.draw_number >= int(draw_start))
    if draw_end is not None:
      query = query.filter(LotteryDraw.draw_number <= int(draw_end))

    # Сортировка по убыванию номера тиража
    query = query.order_by(LotteryDraw.draw_number.desc())

    draws = query.all()

    if not draws:
      # Возвращаем пустой DataFrame с правильными колонками
      return pd.DataFrame(columns=[
        "Дата", "Тираж", "Числа_Поле1", "Числа_Поле2", "Приз",
        "Числа_Поле1_list", "Числа_Поле2_list"
      ])

    # Конвертируем в DataFrame
    data = []
    for draw in draws:
      data.append({
        'Дата': draw.draw_date,
        'Тираж': draw.draw_number,
        'Числа_Поле1': ','.join(map(str, sorted(draw.field1_numbers))),
        'Числа_Поле2': ','.join(map(str, sorted(draw.field2_numbers))),
        'Приз': draw.prize_info.get('amount', 0) if draw.prize_info else 0,
        'Числа_Поле1_list': sorted(draw.field1_numbers),
        'Числа_Поле2_list': sorted(draw.field2_numbers)
      })

    df = pd.DataFrame(data)
    df['Дата'] = pd.to_datetime(df['Дата'])

    print(f"PostgreSQL Fetch: Загружено {len(df)} тиражей для {CURRENT_LOTTERY}")
    return df

  except SQLAlchemyError as e:
    print(f"PostgreSQL Fetch: Ошибка БД: {e}")
    return pd.DataFrame(columns=[
      "Дата", "Тираж", "Числа_Поле1", "Числа_Поле2", "Приз",
      "Числа_Поле1_list", "Числа_Поле2_list"
    ])
  except Exception as e:
    print(f"PostgreSQL Fetch: Неожиданная ошибка: {e}")
    return pd.DataFrame(columns=[
      "Дата", "Тираж", "Числа_Поле1", "Числа_Поле2", "Приз",
      "Числа_Поле1_list", "Числа_Поле2_list"
    ])
  finally:
    db.close()




def update_database_from_source():
    """
    Основная функция для обновления базы данных.
    Она сама определяет, нужно ли делать полную загрузку или только догружать свежие тиражи.
    """

    lottery_type = CURRENT_LOTTERY  # Сохраняем текущий тип для использования в функции
    print(f"Запущено обновление для лотереи: {lottery_type}...")
    init_db()  # На всякий случай проверяем, что БД и таблица существуют

    # Проверяем, есть ли в базе хоть какие-то данные
    existing_draws_df = fetch_draws_from_db()
    is_initial_setup = existing_draws_df.empty


    # Получаем лимиты для текущей лотереи
    limits = get_lottery_limits()
    current_count = len(existing_draws_df)
    target_count = limits['initial_fetch']

    if is_initial_setup:
      print(f"База данных пуста. Выполняется полная начальная загрузка для {lottery_type}...")
      num_to_fetch = target_count
      print(f"Целевое количество тиражей: {num_to_fetch}")
    elif current_count < target_count:
      print(f"База данных содержит {current_count} тиражей для {lottery_type}.")
      print(f"Целевое количество: {target_count}. Необходимо догрузить исторические данные...")
      num_to_fetch = target_count  # Загружаем полный объем для получения старых тиражей
      print(f"Загружаем {num_to_fetch} тиражей для получения недостающих исторических данных")
    else:
      print(f"База данных уже содержит достаточно данных для {lottery_type} ({current_count} тиражей).")
      print("Проверяем наличие новых тиражей...")
      num_to_fetch = limits['update_fetch']

    # Загружаем данные из источника
    df_new_draws = scrape_stoloto_archive(num_draws_to_fetch=num_to_fetch, lottery_type=lottery_type)

    if not df_new_draws.empty:
      # Функция store_draws_to_db сама отфильтрует дубликаты и добавит только новые
      store_draws_to_db(df_new_draws, lottery_type=lottery_type)
    else:
      print("Не удалось загрузить новые данные из источника.")


def force_load_historical_data(target_count=None):
  """
  Принудительная загрузка исторических данных для восполнения недостающих тиражей.
  Загружает большое количество тиражей для получения более старых данных.

  Args:
      target_count: Целевое количество тиражей (если None, берется из лимитов)
  """
  print(f"🕰️ Принудительная загрузка исторических данных для {CURRENT_LOTTERY}...")

  if target_count is None:
    limits = get_lottery_limits()
    target_count = limits['initial_fetch']

  current_df = fetch_draws_from_db()
  current_count = len(current_df)

  print(f"📊 Текущее состояние: {current_count} тиражей, цель: {target_count}")

  if current_count >= target_count:
    print(f"✅ Достаточно данных ({current_count} >= {target_count})")
    return current_df

  # Загружаем максимальное количество для получения исторических данных
  max_possible = max(target_count * 2, 800)  # Загружаем с запасом
  print(f"📥 Загружаем {max_possible} тиражей для получения исторических данных...")

  try:
    df_historical = scrape_stoloto_archive(num_draws_to_fetch=max_possible)

    if not df_historical.empty:
      print(f"✅ Загружено {len(df_historical)} тиражей из API")
      store_draws_to_db(df_historical)

      # Проверяем результат
      updated_df = fetch_draws_from_db()
      new_count = len(updated_df)
      added = new_count - current_count

      print(f"📈 Результат: было {current_count}, стало {new_count} (+{added} тиражей)")

      if new_count >= target_count:
        print(f"🎯 Цель достигнута! Загружено достаточно исторических данных")
      else:
        print(f"⚠️ Цель не достигнута. Возможно, доступно только {new_count} тиражей")

      return updated_df
    else:
      print(f"Не удалось загрузить исторические данные из API")
      return current_df

  except Exception as e:
    print(f"💥 Ошибка загрузки исторических данных: {e}")
    return current_df

def multi_stage_historical_load(target_count=400, max_attempts=5):
    """
    Многоэтапная загрузка исторических данных с защитой от блокировки.
    Загружает данные небольшими порциями с большими интервалами.

    Args:
        target_count: Целевое количество тиражей
        max_attempts: Максимальное количество попыток
    """
    print(f"🔄 Многоэтапная загрузка исторических данных для {CURRENT_LOTTERY}")
    print(f"🎯 Цель: {target_count} тиражей, максимум попыток: {max_attempts}")

    current_df = fetch_draws_from_db()
    initial_count = len(current_df)
    print(f"📊 Начальное состояние: {initial_count} тиражей")

    if initial_count >= target_count:
      print(f"✅ Уже достаточно данных ({initial_count} >= {target_count})")
      return current_df

    # Стратегия: загружаем небольшими порциями
    batch_sizes = [25, 20, 15, 10, 10]  # Уменьшающиеся размеры пакетов
    total_loaded = 0

    for attempt in range(max_attempts):
      current_count = len(fetch_draws_from_db())
      remaining_needed = target_count - current_count

      if remaining_needed <= 0:
        print(f"🎉 Цель достигнута! Загружено {current_count} тиражей")
        break

      # Выбираем размер пакета
      batch_size = batch_sizes[min(attempt, len(batch_sizes) - 1)]
      fetch_size = min(remaining_needed, batch_size)

      print(f"\n🔄 Попытка {attempt + 1}/{max_attempts}: загружаем {fetch_size} тиражей")
      print(f"📈 Прогресс: {current_count}/{target_count} тиражей")

      try:
        # Загружаем небольшую порцию
        df_batch = scrape_stoloto_archive(num_draws_to_fetch=fetch_size)

        if not df_batch.empty:
          old_count = current_count
          store_draws_to_db(df_batch)
          new_count = len(fetch_draws_from_db())
          added_this_batch = new_count - old_count
          total_loaded += added_this_batch

          print(f"✅ Пакет {attempt + 1}: +{added_this_batch} новых тиражей (всего: {new_count})")

          if added_this_batch == 0:
            print("💤 Новых тиражей в этом пакете нет, возможно достигнут лимит API")

        else:
          print(f"Пакет {attempt + 1}: не удалось загрузить данные")

        # Большая пауза между попытками для избежания блокировки
        if attempt < max_attempts - 1:  # Не ждем после последней попытки
          wait_time = 60 + attempt * 30  # От 60 до 180 секунд
          print(f"⏳ Пауза {wait_time} секунд перед следующей попыткой...")
          time.sleep(wait_time)

      except Exception as e:
        print(f"💥 Ошибка в попытке {attempt + 1}: {e}")
        if attempt < max_attempts - 1:
          wait_time = 120 + attempt * 60  # Еще больше ждем при ошибке
          print(f"⏳ Пауза {wait_time} секунд после ошибки...")
          time.sleep(wait_time)

    # Финальная статистика
    final_df = fetch_draws_from_db()
    final_count = len(final_df)
    total_added = final_count - initial_count

    print(f"\n📈 ИТОГИ МНОГОЭТАПНОЙ ЗАГРУЗКИ:")
    print(f"   📊 Было: {initial_count} тиражей")
    print(f"   📊 Стало: {final_count} тиражей")
    print(f"   ➕ Добавлено: {total_added} тиражей")
    print(f"   🎯 Прогресс к цели: {final_count}/{target_count} ({(final_count / target_count) * 100:.1f}%)")

    if final_count >= target_count:
      print(f"   🎉 ЦЕЛЬ ДОСТИГНУТА!")
    else:
      print(f"   ⚠️  Цель не достигнута, но получено максимально возможное количество")

    return final_df


def smart_historical_load_with_pagination(target_count=400):
  """
  Умная загрузка исторических данных с использованием правильной пагинации.
  Использует реальные заголовки браузера и корректные номера страниц.
  """
  print(f"🎯 Умная пагинационная загрузка для {CURRENT_LOTTERY}")
  print(f"📊 Цель: {target_count} тиражей")

  current_df = fetch_draws_from_db()
  current_count = len(current_df)

  if current_count >= target_count:
    print(f"✅ Уже достаточно данных ({current_count} >= {target_count})")
    return current_df

  missing_count = target_count - current_count
  print(f"📉 Нужно догрузить: {missing_count} тиражей")

  # Рассчитываем количество страниц для загрузки
  draws_per_page = 30  # Стандартный размер страницы
  pages_needed = (missing_count + draws_per_page - 1) // draws_per_page

  print(f"📄 Планируется загрузить {pages_needed} страниц по {draws_per_page} тиражей")

  all_new_draws = []
  successful_pages = 0
  start_page = 2  # Начинаем со 2-й страницы (1-я уже у нас есть)

  for page_num in range(start_page, start_page + pages_needed + 5):  # +5 для запаса
    if len(all_new_draws) >= missing_count:
      print(f"🎯 Собрано достаточно тиражей, останавливаем загрузку")
      break

    print(f"\n📄 Загружаем страницу {page_num}...")

    try:
      page_data = load_single_page_with_headers(page_num, draws_per_page)

      if page_data and len(page_data) > 0:
        # Фильтруем только новые тиражи
        existing_draw_numbers = set(current_df['Тираж'].tolist()) if not current_df.empty else set()
        new_draws_this_page = [
          draw for draw in page_data
          if draw.get('Тираж') and draw['Тираж'] not in existing_draw_numbers
        ]

        if new_draws_this_page:
          all_new_draws.extend(new_draws_this_page)
          successful_pages += 1

          draw_numbers = [d['Тираж'] for d in new_draws_this_page]
          min_draw = min(draw_numbers)
          max_draw = max(draw_numbers)

          print(f"✅ Страница {page_num}: +{len(new_draws_this_page)} новых тиражей")
          print(f"   📈 Диапазон: #{min_draw} - #{max_draw}")
          print(f"   📊 Всего собрано: {len(all_new_draws)}/{missing_count}")
        else:
          print(f"💤 Страница {page_num}: все тиражи уже есть в БД")

      else:
        print(f"Страница {page_num}: нет данных")

      # Пауза между страницами
      if page_num < start_page + pages_needed:
        delay = random.uniform(3, 7)  # Случайная пауза 3-7 секунд
        print(f"⏳ Пауза {delay:.1f}с перед следующей страницей...")
        time.sleep(delay)

    except Exception as e:
      print(f"💥 Ошибка загрузки страницы {page_num}: {e}")
      if "403" in str(e):
        print(f"🛑 Блокировка 403, увеличиваем паузу...")
        time.sleep(60)
      continue

  # Сохраняем все новые тиражи
  if all_new_draws:
    print(f"\n💾 Сохранение {len(all_new_draws)} новых тиражей в БД...")
    new_df = pd.DataFrame(all_new_draws)
    store_draws_to_db(new_df)

    # Проверяем финальный результат
    final_df = fetch_draws_from_db()
    final_count = len(final_df)
    total_added = final_count - current_count

    print(f"📈 РЕЗУЛЬТАТЫ ЗАГРУЗКИ:")
    print(f"   📊 Было: {current_count} тиражей")
    print(f"   📊 Стало: {final_count} тиражей")
    print(f"   ➕ Добавлено: {total_added} тиражей")
    print(f"   📄 Успешных страниц: {successful_pages}")
    print(f"   🎯 Прогресс к цели: {final_count}/{target_count} ({(final_count / target_count) * 100:.1f}%)")

    return final_df
  else:
    print(f"Не удалось загрузить новые тиражи")
    return current_df


def load_single_page_with_headers(page_number, count=30, lottery_type=None):
  """
  Загружает одну страницу тиражей с правильными заголовками
  """
  if lottery_type is None:
    lottery_type = CURRENT_LOTTERY
  config = LOTTERY_CONFIGS.get(lottery_type, get_current_config())
  api_url = config['api_url'].format(limit=count, page_num=page_number)

  headers = {
    'Accept': 'application/json, text/plain, */*',
    'Device-Platform': 'DESKTOP',
    'Device-Type': 'STOLOTO',
    'Gosloto-Partner': 'bXMjXFRXZ3coWXh6R3s1NTdUX3dnWlBMLUxmdg',
    'Gosloto-Token': '25813cf100-c6dc62-475a85-bf6a46-ef05d300addf06',
    'Referer': 'https://www.stoloto.ru/4x20/archive',
    'Sec-Ch-Ua': '"Opera GX";v="120", "Not-A.Brand";v="8", "Chromium";v="135"',
    'Sec-Ch-Ua-Mobile': '?0',
    'Sec-Ch-Ua-Platform': '"Windows"',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 OPR/120.0.0.0 (Edition Yx GX)'
  }

  try:
    response = requests.get(api_url, headers=headers, timeout=30)
    response.raise_for_status()

    json_data = response.json()

    if json_data.get("requestStatus") != "success" or "draws" not in json_data:
      print(f"API Error: {json_data.get('requestStatus')}")
      return []

    # Конвертируем в наш формат
    page_draws = []
    for draw_item in json_data["draws"]:
      converted = convert_api_draw_to_our_format(draw_item, lottery_type)
      if converted:
        page_draws.append(converted)

    return page_draws

  except Exception as e:
    print(f"Error loading page {page_number}: {e}")
    return []


def convert_api_draw_to_our_format(api_draw, lottery_type=None):
  """Конвертирует формат API в наш формат БД"""
  if lottery_type is None:
    lottery_type = CURRENT_LOTTERY

  # Используем конфигурацию переданной лотереи, а не глобальную
  config = LOTTERY_CONFIGS.get(lottery_type, get_current_config())
  try:
    # config = get_current_config()
    field1_size = config['field1_size']
    field2_size = config['field2_size']

    draw_id = api_draw.get("number")
    draw_date_raw = api_draw.get("date")
    winning_combination_raw = api_draw.get("winningCombination")

    if not all([draw_id, draw_date_raw, winning_combination_raw]):
      return None

    # Обрабатываем дату
    try:
      if len(draw_date_raw) == 24 and draw_date_raw[-5] in ['+', '-'] and draw_date_raw[-3] != ':':
        draw_date_processed = draw_date_raw[:-2] + ":" + draw_date_raw[-2:]
      else:
        draw_date_processed = draw_date_raw
      draw_date_obj = datetime.fromisoformat(draw_date_processed)
      draw_date_formatted = draw_date_obj.strftime('%Y-%m-%d')
    except ValueError:
      return None

    # Разбираем числа
    expected_total = field1_size + field2_size
    if len(winning_combination_raw) != expected_total:
      return None

    numbers_f1 = sorted([int(n) for n in winning_combination_raw[:field1_size]])
    numbers_f2 = sorted([int(n) for n in winning_combination_raw[field1_size:field1_size + field2_size]])

    return {
      "Дата": draw_date_formatted,
      "Тираж": int(draw_id),
      "Числа_Поле1": format_numbers(numbers_f1),
      "Числа_Поле2": format_numbers(numbers_f2),
      "Приз": 0
    }

  except Exception as e:
    print(f"Error converting draw: {e}")
    return None


if __name__ == '__main__':
  print("--- Тестирование PostgreSQL data_manager ---")

  # Тестируем подключение
  if not init_db():
    print("Не удалось инициализировать PostgreSQL")
    exit(1)

  # Тестируем загрузку данных
  print(f"\n--- Тест для {CURRENT_LOTTERY} ---")
  update_database_from_source()

  print("\n--- Проверка содержимого БД (последние 5 тиражей) ---")
  test_df = fetch_draws_from_db()
  if not test_df.empty:
    print(test_df.head())
    print(f"\nВсего тиражей в PostgreSQL: {len(test_df)}")
  else:
    print("База данных пуста или произошла ошибка")