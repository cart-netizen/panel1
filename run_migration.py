# run_migration.py
"""
Запуск миграции данных из SQLite в PostgreSQL
"""
import os
import sys
from dotenv import load_dotenv

# Настройка путей
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
load_dotenv()


def main():
  print("🚀 ЗАПУСК МИГРАЦИИ ДАННЫХ SQLite → PostgreSQL")
  print("=" * 60)

  try:
    # Импортируем модули миграции
    from backend.app.core.migration import migrate_from_sqlite_to_postgresql
    from backend.app.core.database import get_db_stats

    # Показываем состояние ДО миграции
    print("\n📊 СОСТОЯНИЕ POSTGRESQL ДО МИГРАЦИИ:")
    initial_stats = get_db_stats()
    for lottery_type, stats in initial_stats.get('draws', []):
      print(f"   📈 {lottery_type}: {stats['count']} тиражей")

    if not initial_stats.get('draws'):
      print("   📭 PostgreSQL пуста")

    # Запускаем миграцию
    print("\n" + "=" * 60)
    total_migrated = migrate_from_sqlite_to_postgresql()

    # Показываем результат
    print("\n📊 ИТОГОВАЯ СТАТИСТИКА:")
    final_stats = get_db_stats()

    print(f"\n🐘 POSTGRESQL (финальное состояние):")
    total_final = 0
    for item in final_stats.get('draws', []):
      lottery_type = item['lottery_type']
      count = item['count']
      min_draw = item['min_draw']
      max_draw = item['max_draw']
      total_final += count
      print(f"   📊 {lottery_type}: {count} тиражей (#{min_draw} - #{max_draw})")

    print(f"\n🎯 РЕЗУЛЬТАТ МИГРАЦИИ:")
    print(f"   ✅ Успешно мигрировано: {total_migrated} тиражей")
    print(f"   📊 Всего в PostgreSQL: {total_final} тиражей")

    if total_migrated > 0:
      print(f"\n🎉 МИГРАЦИЯ ЗАВЕРШЕНА УСПЕШНО!")
      print(f"💡 Теперь можно запускать основное приложение с PostgreSQL")
    else:
      print(f"\n⚠️ Данные не были мигрированы")
      print(f"💡 Возможно, данные уже есть в PostgreSQL или файлы SQLite не найдены")

  except Exception as e:
    print(f"\n💥 КРИТИЧЕСКАЯ ОШИБКА МИГРАЦИИ: {e}")
    import traceback
    traceback.print_exc()
    return False

  return True


if __name__ == "__main__":
  success = main()
  if success:
    print(f"\n✅ Скрипт выполнен успешно")
  else:
    print(f"\n❌ Скрипт завершился с ошибками")