# check_migration.py
"""
Проверка результатов миграции
"""
import os
import sys
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
load_dotenv()


def check_migration_results():
  print("🔍 ПРОВЕРКА РЕЗУЛЬТАТОВ МИГРАЦИИ")
  print("=" * 50)

  try:
    from sqlalchemy import create_engine, text

    DATABASE_URL = os.getenv(
      "DATABASE_URL",
      "postgresql://postgres:Cartman89@localhost:5432/lottery_analytics"
    )

    engine = create_engine(DATABASE_URL)

    with engine.connect() as conn:
      # Общая статистика
      print("📊 ОБЩАЯ СТАТИСТИКА:")
      result = conn.execute(text("SELECT COUNT(*) FROM lottery_draws"))
      total_count = result.fetchone()[0]
      print(f"   📈 Всего тиражей в PostgreSQL: {total_count}")

      # Статистика по лотереям
      print(f"\n📊 ПО ЛОТЕРЕЯМ:")
      result = conn.execute(text("""
                SELECT lottery_type, 
                       COUNT(*) as count,
                       MIN(draw_number) as min_draw,
                       MAX(draw_number) as max_draw,
                       MIN(draw_date) as earliest_date,
                       MAX(draw_date) as latest_date
                FROM lottery_draws 
                GROUP BY lottery_type
                ORDER BY lottery_type
            """))

      for row in result:
        lottery_type, count, min_draw, max_draw, earliest_date, latest_date = row
        print(f"   🎯 {lottery_type}:")
        print(f"      📊 Тиражей: {count}")
        print(f"      🔢 Диапазон: #{min_draw} - #{max_draw}")
        print(f"      📅 Даты: {earliest_date.strftime('%Y-%m-%d')} - {latest_date.strftime('%Y-%m-%d')}")

      # Последние 5 тиражей каждой лотереи
      print(f"\n📋 ПОСЛЕДНИЕ ТИРАЖИ:")
      for lottery_type in ['4x20', '5x36plus']:
        print(f"\n   🎲 {lottery_type} (последние 5):")
        result = conn.execute(text("""
                    SELECT draw_number, draw_date, field1_numbers, field2_numbers
                    FROM lottery_draws 
                    WHERE lottery_type = :lottery_type
                    ORDER BY draw_number DESC
                    LIMIT 5
                """), {"lottery_type": lottery_type})

        for row in result:
          draw_number, draw_date, field1_numbers, field2_numbers = row
          date_str = draw_date.strftime('%Y-%m-%d')
          print(f"      #{draw_number} ({date_str}): {field1_numbers} | {field2_numbers}")

      # Проверка данных
      print(f"\n🔍 ПРОВЕРКА ЦЕЛОСТНОСТИ:")

      # Проверяем дубликаты
      result = conn.execute(text("""
                SELECT lottery_type, draw_number, COUNT(*) as count
                FROM lottery_draws
                GROUP BY lottery_type, draw_number
                HAVING COUNT(*) > 1
            """))

      duplicates = list(result)
      if duplicates:
        print(f"   ⚠️ Найдены дубликаты:")
        for lottery_type, draw_number, count in duplicates:
          print(f"      🔄 {lottery_type} #{draw_number}: {count} раз")
      else:
        print(f"   ✅ Дубликатов нет")

      # Проверяем валидность данных
      result = conn.execute(text("""
                SELECT lottery_type, COUNT(*) as invalid_count
                FROM lottery_draws
                WHERE field1_numbers IS NULL 
                   OR field2_numbers IS NULL 
                   OR draw_number IS NULL
                GROUP BY lottery_type
            """))

      invalid_data = list(result)
      if invalid_data:
        print(f"   ⚠️ Найдены невалидные данные:")
        for lottery_type, invalid_count in invalid_data:
          print(f"      ❌ {lottery_type}: {invalid_count} записей")
      else:
        print(f"   ✅ Все данные валидны")

    print(f"\n🎉 ПРОВЕРКА ЗАВЕРШЕНА!")
    return True

  except Exception as e:
    print(f"💥 ОШИБКА ПРОВЕРКИ: {e}")
    import traceback
    traceback.print_exc()
    return False


if __name__ == "__main__":
  check_migration_results()