# core/migration.py
"""
Скрипт миграции данных из SQLite в PostgreSQL
Объединяет данные из всех существующих БД
"""

import sqlite3
import pandas as pd
from datetime import datetime
from typing import List, Dict
import json

from backend.app.core.database import SessionLocal, LotteryDraw, create_tables, engine
from backend.app.core.data_manager import LOTTERY_CONFIGS


def migrate_from_sqlite_to_postgresql():
  """
  Основная функция миграции всех данных из SQLite в PostgreSQL
  """
  print("🚀 НАЧАЛО МИГРАЦИИ ДАННЫХ SQLite → PostgreSQL")

  # Создаем таблицы в PostgreSQL
  create_tables()

  # Файлы SQLite для миграции
  sqlite_files = [
    {'path': 'data/lottery_4x20.db', 'lottery_type': '4x20'},
    {'path': 'data/lottery_5x36plus.db', 'lottery_type': '5x36plus'},
    {'path': 'data/lottery_draws.db', 'lottery_type': '4x20'},  # Старая БД 4x20
  ]

  total_migrated = 0
  migration_stats = {}

  for file_info in sqlite_files:
    try:
      migrated_count = migrate_single_sqlite_file(
        file_info['path'],
        file_info['lottery_type']
      )
      total_migrated += migrated_count
      migration_stats[file_info['path']] = migrated_count

    except Exception as e:
      print(f"❌ Ошибка миграции {file_info['path']}: {e}")
      migration_stats[file_info['path']] = 0

  # Итоговая статистика
  print(f"\n📈 ИТОГИ МИГРАЦИИ:")
  print(f"   📊 Всего мигрировано: {total_migrated} тиражей")

  for file_path, count in migration_stats.items():
    status = "✅" if count > 0 else "❌"
    print(f"   {status} {file_path}: {count} тиражей")

  # Проверяем результат в PostgreSQL
  final_stats = get_postgresql_stats()
  print(f"\n🐘 СТАТИСТИКА POSTGRESQL:")
  for lottery_type, stats in final_stats.items():
    print(f"   📊 {lottery_type}: {stats['count']} тиражей "
          f"(#{stats['min_draw']} - #{stats['max_draw']})")

  print(f"\n🎉 МИГРАЦИЯ ЗАВЕРШЕНА!")
  return total_migrated


def migrate_single_sqlite_file(sqlite_path: str, lottery_type: str) -> int:
  """
  Мигрирует данные из одного SQLite файла
  """
  print(f"\n📁 Миграция файла: {sqlite_path} ({lottery_type})")

  try:
    # Подключаемся к SQLite
    conn = sqlite3.connect(sqlite_path)

    # Определяем таблицу
    table_name = LOTTERY_CONFIGS[lottery_type]['db_table']

    # Читаем данные
    query = f'SELECT * FROM {table_name} ORDER BY "Тираж" DESC'
    df = pd.read_sql_query(query, conn)
    conn.close()

    if df.empty:
      print(f"   💤 Файл пуст")
      return 0

    print(f"   📊 Найдено {len(df)} записей")

    # Конвертируем в формат PostgreSQL
    postgresql_records = []
    config = LOTTERY_CONFIGS[lottery_type]

    for _, row in df.iterrows():
      try:
        # Парсим числа
        field1_str = str(row.get('Числа_Поле1', ''))
        field2_str = str(row.get('Числа_Поле2', ''))

        field1_numbers = [int(x.strip()) for x in field1_str.split(',') if x.strip().isdigit()]
        field2_numbers = [int(x.strip()) for x in field2_str.split(',') if x.strip().isdigit()]

        # Валидация
        if (len(field1_numbers) != config['field1_size'] or
            len(field2_numbers) != config['field2_size']):
          continue

        # Парсим дату
        date_str = str(row.get('Дата', ''))
        try:
          draw_date = pd.to_datetime(date_str).to_pydatetime()
        except:
          draw_date = datetime.now()

        record = LotteryDraw(
          lottery_type=lottery_type,
          draw_number=int(row.get('Тираж', 0)),
          draw_date=draw_date,
          field1_numbers=field1_numbers,
          field2_numbers=field2_numbers,
          prize_info={'amount': float(row.get('Приз', 0))},
          created_at=datetime.now()
        )

        postgresql_records.append(record)

      except Exception as e:
        print(f"   ⚠️ Ошибка обработки записи: {e}")
        continue

    # Сохраняем в PostgreSQL
    if postgresql_records:
      migrated_count = save_to_postgresql(postgresql_records)
      print(f"   ✅ Мигрировано: {migrated_count} записей")
      return migrated_count
    else:
      print(f"   ❌ Нет валидных записей для миграции")
      return 0

  except Exception as e:
    print(f"   💥 Ошибка файла {sqlite_path}: {e}")
    return 0


def save_to_postgresql(records: List[LotteryDraw]) -> int:
  """
  Сохраняет записи в PostgreSQL с обработкой дубликатов
  """
  db = SessionLocal()
  try:
    # Получаем существующие номера тиражей для предотвращения дубликатов
    existing_draws = {}
    for lottery_type in LOTTERY_CONFIGS.keys():
      existing = db.query(LotteryDraw.draw_number).filter(
        LotteryDraw.lottery_type == lottery_type
      ).all()
      existing_draws[lottery_type] = set(draw[0] for draw in existing)

    # Фильтруем дубликаты
    new_records = []
    for record in records:
      if record.draw_number not in existing_draws.get(record.lottery_type, set()):
        new_records.append(record)

    # Сохраняем новые записи
    if new_records:
      db.add_all(new_records)
      db.commit()

      # Обновляем кэш существующих
      for record in new_records:
        existing_draws.setdefault(record.lottery_type, set()).add(record.draw_number)

    return len(new_records)

  except Exception as e:
    db.rollback()
    print(f"   💥 Ошибка сохранения: {e}")
    return 0
  finally:
    db.close()


def get_postgresql_stats() -> Dict:
  """
  Возвращает статистику по данным в PostgreSQL
  """
  db = SessionLocal()
  try:
    stats = {}

    for lottery_type in LOTTERY_CONFIGS.keys():
      result = db.query(
        LotteryDraw.draw_number
      ).filter(
        LotteryDraw.lottery_type == lottery_type
      ).all()

      if result:
        draw_numbers = [r[0] for r in result]
        stats[lottery_type] = {
          'count': len(draw_numbers),
          'min_draw': min(draw_numbers),
          'max_draw': max(draw_numbers)
        }
      else:
        stats[lottery_type] = {'count': 0, 'min_draw': 0, 'max_draw': 0}

    return stats

  finally:
    db.close()


if __name__ == "__main__":
  # Запуск миграции
  migrate_from_sqlite_to_postgresql()