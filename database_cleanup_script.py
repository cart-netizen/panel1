# database_cleanup.py
"""
Профессиональный скрипт очистки базы данных тиражей лотерей
Поддерживает различные режимы очистки с сохранением важных данных
"""

import sys
import os
import pandas as pd
from datetime import datetime, timedelta
import json
from typing import List, Dict, Optional
import time

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.app.core.database import SessionLocal, LotteryDraw, ModelPrediction, create_tables
from backend.app.core.data_manager import (
  LOTTERY_CONFIGS,
  set_current_lottery,
  fetch_draws_from_db,
  get_current_config,
  get_lottery_limits
)
from backend.app.core.lottery_context import LotteryContext
from sqlalchemy import text, desc, asc, func
from sqlalchemy.exc import SQLAlchemyError


class DatabaseCleaner:
  """
    Профессиональный менеджер очистки базы данных тиражей
    """

  def __init__(self):
    self.session = None
    self.backup_data = {}
    self.cleanup_stats = {
      'total_processed': 0,
      'duplicates_removed': 0,
      'invalid_removed': 0,
      'old_removed': 0,
      'predictions_cleaned': 0,
      'space_freed_mb': 0
    }

  def __enter__(self):
    self.session = SessionLocal()
    return self

  def __exit__(self, exc_type, exc_val, exc_tb):
    if self.session:
      if exc_type:
        self.session.rollback()
      self.session.close()

  def analyze_database_state(self) -> Dict:
    """
        Анализирует текущее состояние базы данных перед очисткой
        """
    print("🔍 АНАЛИЗ СОСТОЯНИЯ БАЗЫ ДАННЫХ")
    print("=" * 60)

    analysis = {
      'lotteries': {},
      'total_draws': 0,
      'total_predictions': 0,
      'disk_usage_estimate': 0,
      'issues_found': []
    }

    for lottery_type in LOTTERY_CONFIGS.keys():
      print(f"\n📊 Анализ лотереи: {lottery_type}")

      # Статистика тиражей
      draws_count = self.session.query(LotteryDraw).filter(
        LotteryDraw.lottery_type == lottery_type
      ).count()

      if draws_count > 0:
        # Диапазон номеров
        min_draw = self.session.query(func.min(LotteryDraw.draw_number)).filter(
          LotteryDraw.lottery_type == lottery_type
        ).scalar()

        max_draw = self.session.query(func.max(LotteryDraw.draw_number)).filter(
          LotteryDraw.lottery_type == lottery_type
        ).scalar()

        # Дубликаты
        duplicates = self.session.query(
          LotteryDraw.draw_number,
          func.count(LotteryDraw.id).label('count')
        ).filter(
          LotteryDraw.lottery_type == lottery_type
        ).group_by(LotteryDraw.draw_number).having(
          func.count(LotteryDraw.id) > 1
        ).all()

        # Некорректные записи
        invalid_count = self._count_invalid_records(lottery_type)

        # Устаревшие записи (старше лимита)
        limits = self._get_lottery_limits_safe(lottery_type)
        max_allowed = limits.get('max_draws_in_db', 10000)
        excess_count = max(0, draws_count - max_allowed)

        lottery_stats = {
          'total_draws': draws_count,
          'draw_range': f"#{min_draw} - #{max_draw}",
          'duplicates': len(duplicates),
          'invalid_records': invalid_count,
          'excess_records': excess_count,
          'max_allowed': max_allowed
        }

        analysis['lotteries'][lottery_type] = lottery_stats
        analysis['total_draws'] += draws_count

        print(f"   📈 Всего тиражей: {draws_count}")
        print(f"   🎯 Диапазон: {lottery_stats['draw_range']}")
        print(f"   🔄 Дубликатов: {len(duplicates)}")
        print(f"   ❌ Некорректных: {invalid_count}")
        print(f"   📦 Превышение лимита: {excess_count}")

        # Добавляем проблемы в общий список
        if len(duplicates) > 0:
          analysis['issues_found'].append(f"{lottery_type}: {len(duplicates)} дубликатов")
        if invalid_count > 0:
          analysis['issues_found'].append(f"{lottery_type}: {invalid_count} некорректных записей")
        if excess_count > 0:
          analysis['issues_found'].append(f"{lottery_type}: {excess_count} записей сверх лимита")
      else:
        print(f"   📭 Нет данных")

    # Статистика предсказаний моделей
    predictions_count = self.session.query(ModelPrediction).count()
    analysis['total_predictions'] = predictions_count

    if predictions_count > 0:
      print(f"\n🤖 Предсказания AI моделей: {predictions_count}")

      # Устаревшие предсказания (старше 30 дней)
      cutoff_date = datetime.now() - timedelta(days=30)
      old_predictions = self.session.query(ModelPrediction).filter(
        ModelPrediction.created_at < cutoff_date
      ).count()

      if old_predictions > 0:
        print(f"   🗑️  Устаревших (>30 дней): {old_predictions}")
        analysis['issues_found'].append(f"AI Predictions: {old_predictions} устаревших записей")

    # Оценка размера БД
    analysis['disk_usage_estimate'] = self._estimate_db_size(analysis['total_draws'], predictions_count)

    print(f"\n📊 ОБЩАЯ СТАТИСТИКА:")
    print(f"   🎯 Всего тиражей: {analysis['total_draws']}")
    print(f"   🤖 Предсказаний: {analysis['total_predictions']}")
    print(f"   💾 Примерный размер БД: {analysis['disk_usage_estimate']:.1f} MB")
    print(f"   ⚠️  Найдено проблем: {len(analysis['issues_found'])}")

    if analysis['issues_found']:
      print(f"\n🔧 ОБНАРУЖЕННЫЕ ПРОБЛЕМЫ:")
      for issue in analysis['issues_found']:
        print(f"   • {issue}")

    return analysis

  def _count_invalid_records(self, lottery_type: str) -> int:
    """
        Подсчитывает количество некорректных записей для лотереи
        """
    try:
      with LotteryContext(lottery_type):
        config = get_current_config()
        expected_f1_size = config['field1_size']
        expected_f2_size = config['field2_size']
        f1_max = config['field1_max']
        f2_max = config['field2_max']

      invalid_count = 0

      # Получаем все записи для проверки
      records = self.session.query(LotteryDraw).filter(
        LotteryDraw.lottery_type == lottery_type
      ).all()

      for record in records:
        try:
          # НОВОЕ: Проверка на тестовые данные в зависимости от типа лотереи
          if lottery_type == '4x20' and record.draw_number >= 100000:
            invalid_count += 1
            continue
          elif lottery_type == '5x36plus' and record.draw_number >= 200000:
            invalid_count += 1
            continue

          f1_nums = record.field1_numbers
          f2_nums = record.field2_numbers

          # Проверки валидности
          if not isinstance(f1_nums, list) or not isinstance(f2_nums, list):
            invalid_count += 1
            continue

          if len(f1_nums) != expected_f1_size or len(f2_nums) != expected_f2_size:
            invalid_count += 1
            continue

          # Проверка диапазонов чисел
          if (any(n < 1 or n > f1_max for n in f1_nums) or
              any(n < 1 or n > f2_max for n in f2_nums)):
            invalid_count += 1
            continue

          # Проверка дубликатов в одном поле
          if len(set(f1_nums)) != len(f1_nums) or len(set(f2_nums)) != len(f2_nums):
            invalid_count += 1
            continue

        except Exception:
          invalid_count += 1
          continue

      return invalid_count

    except Exception as e:
      print(f"   ⚠️  Ошибка подсчета некорректных записей: {e}")
      return 0

  def _get_lottery_limits_safe(self, lottery_type: str) -> Dict:
    """
        Безопасно получает лимиты для лотереи
        """
    try:
      with LotteryContext(lottery_type):
        return get_lottery_limits()
    except:
      return {'max_draws_in_db': 10000, 'initial_fetch': 500, 'min_for_training': 100}

  def _estimate_db_size(self, total_draws: int, total_predictions: int) -> float:
    """
        Оценивает размер базы данных в MB
        """
    # Примерные размеры на запись
    draw_size_kb = 0.5  # JSON поля + метаданные
    prediction_size_kb = 0.3

    total_size_kb = (total_draws * draw_size_kb) + (total_predictions * prediction_size_kb)
    return total_size_kb / 1024  # Конвертируем в MB

  def create_backup(self, lottery_types: Optional[List[str]] = None) -> bool:
    """
        Создает резервную копию данных перед очисткой
        """
    print("\n💾 СОЗДАНИЕ РЕЗЕРВНОЙ КОПИИ")
    print("-" * 40)

    try:
      backup_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

      if not lottery_types:
        lottery_types = list(LOTTERY_CONFIGS.keys())

      for lottery_type in lottery_types:
        print(f"📦 Резервное копирование {lottery_type}...")

        # Получаем тиражи
        draws = self.session.query(LotteryDraw).filter(
          LotteryDraw.lottery_type == lottery_type
        ).order_by(desc(LotteryDraw.draw_number)).all()

        if draws:
          backup_data = []
          for draw in draws:
            backup_data.append({
              'draw_number': draw.draw_number,
              'draw_date': draw.draw_date.isoformat(),
              'field1_numbers': draw.field1_numbers,
              'field2_numbers': draw.field2_numbers,
              'prize_info': draw.prize_info,
              'created_at': draw.created_at.isoformat()
            })

          # Сохраняем в файл
          backup_filename = f"backup_{lottery_type}_{backup_timestamp}.json"

          with open(backup_filename, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=2, ensure_ascii=False)

          print(f"   ✅ Сохранено {len(draws)} записей в {backup_filename}")
          self.backup_data[lottery_type] = backup_filename
        else:
          print(f"   📭 Нет данных для резервного копирования")

      return True

    except Exception as e:
      print(f"   ❌ Ошибка создания резервной копии: {e}")
      return False

  def remove_duplicates(self, lottery_type: str) -> int:
    """
        Удаляет дубликаты тиражей для указанной лотереи
        """
    print(f"\n🔄 УДАЛЕНИЕ ДУБЛИКАТОВ для {lottery_type}")

    try:
      # Находим дубликаты
      duplicates_query = self.session.query(
        LotteryDraw.draw_number,
        func.count(LotteryDraw.id).label('count'),
        func.min(LotteryDraw.id).label('keep_id')
      ).filter(
        LotteryDraw.lottery_type == lottery_type
      ).group_by(LotteryDraw.draw_number).having(
        func.count(LotteryDraw.id) > 1
      )

      duplicates = duplicates_query.all()
      removed_count = 0

      for dup in duplicates:
        draw_number = dup.draw_number
        keep_id = dup.keep_id
        total_count = dup.count

        print(f"   🎯 Тираж #{draw_number}: найдено {total_count} копий")

        # Удаляем все кроме самой старой записи
        deleted = self.session.query(LotteryDraw).filter(
          LotteryDraw.lottery_type == lottery_type,
          LotteryDraw.draw_number == draw_number,
          LotteryDraw.id != keep_id
        ).delete()

        removed_count += deleted
        print(f"       ❌ Удалено {deleted} дубликатов")

      self.session.commit()
      self.cleanup_stats['duplicates_removed'] += removed_count

      if removed_count > 0:
        print(f"   ✅ Всего удалено дубликатов: {removed_count}")
      else:
        print(f"   ✅ Дубликатов не найдено")

      return removed_count

    except Exception as e:
      self.session.rollback()
      print(f"   ❌ Ошибка удаления дубликатов: {e}")
      return 0

  def remove_invalid_records(self, lottery_type: str) -> int:
    """
        Удаляет некорректные записи для указанной лотереи
        """
    print(f"\n❌ УДАЛЕНИЕ НЕКОРРЕКТНЫХ ЗАПИСЕЙ для {lottery_type}")

    try:
      with LotteryContext(lottery_type):
        config = get_current_config()
        expected_f1_size = config['field1_size']
        expected_f2_size = config['field2_size']
        f1_max = config['field1_max']
        f2_max = config['field2_max']

      records = self.session.query(LotteryDraw).filter(
        LotteryDraw.lottery_type == lottery_type
      ).all()

      invalid_ids = []

      for record in records:
        is_invalid = False
        reason = ""

        try:
          f1_nums = record.field1_numbers
          f2_nums = record.field2_numbers

          # НОВОЕ: Проверка на тестовые данные в зависимости от типа лотереи
          if lottery_type == '4x20' and record.draw_number >= 100000:
            is_invalid = True
            reason = f"тестовые данные 4x20 (номер >= 100000)"
          elif lottery_type == '5x36plus' and record.draw_number >= 200000:
            is_invalid = True
            reason = f"тестовые данные 5x36plus (номер >= 200000)"
          # Проверки валидности
          elif not isinstance(f1_nums, list) or not isinstance(f2_nums, list):
            is_invalid = True
            reason = "не список"
          elif len(f1_nums) != expected_f1_size or len(f2_nums) != expected_f2_size:
            is_invalid = True
            reason = f"неверный размер ({len(f1_nums)}/{len(f2_nums)})"
          elif (any(n < 1 or n > f1_max for n in f1_nums) or
                any(n < 1 or n > f2_max for n in f2_nums)):
            is_invalid = True
            reason = "числа вне диапазона"
          elif len(set(f1_nums)) != len(f1_nums) or len(set(f2_nums)) != len(f2_nums):
            is_invalid = True
            reason = "дубликаты чисел в поле"
          elif record.draw_number <= 0:
            is_invalid = True
            reason = "некорректный номер тиража"

        except Exception as e:
          is_invalid = True
          reason = f"ошибка парсинга: {e}"

        if is_invalid:
          invalid_ids.append(record.id)
          print(f"   ❌ Тираж #{record.draw_number}: {reason}")

      # Удаляем некорректные записи
      if invalid_ids:
        deleted = self.session.query(LotteryDraw).filter(
          LotteryDraw.id.in_(invalid_ids)
        ).delete(synchronize_session=False)

        self.session.commit()
        self.cleanup_stats['invalid_removed'] += deleted

        print(f"   ✅ Удалено некорректных записей: {deleted}")
        return deleted
      else:
        print(f"   ✅ Некорректных записей не найдено")
        return 0

    except Exception as e:
      self.session.rollback()
      print(f"   ❌ Ошибка удаления некорректных записей: {e}")
      return 0

  def apply_size_limits(self, lottery_type: str) -> int:
    """
        Применяет лимиты размера БД, удаляя старые записи
        """
    print(f"\n📦 ПРИМЕНЕНИЕ ЛИМИТОВ РАЗМЕРА для {lottery_type}")

    try:
      limits = self._get_lottery_limits_safe(lottery_type)
      max_draws = limits.get('max_draws_in_db', 10000)

      current_count = self.session.query(LotteryDraw).filter(
        LotteryDraw.lottery_type == lottery_type
      ).count()

      print(f"   📊 Текущее количество: {current_count}")
      print(f"   🎯 Максимально разрешено: {max_draws}")

      if current_count <= max_draws:
        print(f"   ✅ Лимит не превышен")
        return 0

      excess = current_count - max_draws
      print(f"   ⚠️  Превышение: {excess} записей")

      # Удаляем самые старые записи
      oldest_records = self.session.query(LotteryDraw).filter(
        LotteryDraw.lottery_type == lottery_type
      ).order_by(asc(LotteryDraw.draw_number)).limit(excess).all()

      deleted_draw_numbers = []
      for record in oldest_records:
        deleted_draw_numbers.append(record.draw_number)
        self.session.delete(record)

      self.session.commit()
      self.cleanup_stats['old_removed'] += excess

      if deleted_draw_numbers:
        print(f"   ❌ Удалены тиражи: #{min(deleted_draw_numbers)} - #{max(deleted_draw_numbers)}")

      print(f"   ✅ Удалено старых записей: {excess}")
      return excess

    except Exception as e:
      self.session.rollback()
      print(f"   ❌ Ошибка применения лимитов: {e}")
      return 0

  def clean_old_predictions(self, days_old: int = 30) -> int:
    """
        Удаляет старые предсказания AI моделей
        """
    print(f"\n🤖 ОЧИСТКА СТАРЫХ ПРЕДСКАЗАНИЙ (старше {days_old} дней)")

    try:
      cutoff_date = datetime.now() - timedelta(days=days_old)

      old_predictions = self.session.query(ModelPrediction).filter(
        ModelPrediction.created_at < cutoff_date
      )

      count_before = old_predictions.count()

      if count_before == 0:
        print(f"   ✅ Старых предсказаний не найдено")
        return 0

      # Удаляем старые предсказания
      deleted = old_predictions.delete()
      self.session.commit()

      self.cleanup_stats['predictions_cleaned'] += deleted

      print(f"   ❌ Удалено предсказаний: {deleted}")
      return deleted

    except Exception as e:
      self.session.rollback()
      print(f"   ❌ Ошибка очистки предсказаний: {e}")
      return 0

  def optimize_database(self) -> bool:
    """
        Оптимизирует базу данных (VACUUM, REINDEX)
        """
    print(f"\n⚡ ОПТИМИЗАЦИЯ БАЗЫ ДАННЫХ")

    try:
      # Для PostgreSQL выполняем VACUUM и ANALYZE
      self.session.execute(text("VACUUM ANALYZE lottery_draws;"))
      self.session.execute(text("VACUUM ANALYZE model_predictions;"))
      self.session.commit()

      print(f"   ✅ Выполнен VACUUM ANALYZE")

      # Обновляем статистику планировщика
      self.session.execute(text("ANALYZE;"))
      self.session.commit()

      print(f"   ✅ Обновлена статистика планировщика")

      return True

    except Exception as e:
      print(f"   ⚠️  Оптимизация завершена с предупреждениями: {e}")
      return False

  def full_cleanup(self, lottery_types: Optional[List[str]] = None,
                   create_backup: bool = True) -> Dict:
    """
        Полная очистка базы данных со всеми проверками
        """
    print("🧹 ЗАПУСК ПОЛНОЙ ОЧИСТКИ БАЗЫ ДАННЫХ")
    print("=" * 60)

    start_time = time.time()

    if not lottery_types:
      lottery_types = list(LOTTERY_CONFIGS.keys())

    # 1. Анализ перед очисткой
    analysis = self.analyze_database_state()

    if not analysis['issues_found']:
      print(f"\n✅ База данных в отличном состоянии, очистка не требуется!")
      return {'status': 'no_cleanup_needed', 'analysis': analysis}

    # 2. Создание резервной копии
    if create_backup:
      if not self.create_backup(lottery_types):
        print(f"\n❌ Не удалось создать резервную копию. Прерываем очистку.")
        return {'status': 'backup_failed'}

    # 3. Очистка для каждой лотереи
    for lottery_type in lottery_types:
      print(f"\n🎯 ОЧИСТКА ЛОТЕРЕИ: {lottery_type}")
      print("-" * 30)

      # Удаляем дубликаты
      self.remove_duplicates(lottery_type)

      # Удаляем некорректные записи
      self.remove_invalid_records(lottery_type)

      # Применяем лимиты размера
      self.apply_size_limits(lottery_type)

    # 4. Очистка предсказаний AI
    self.clean_old_predictions()

    # 5. Оптимизация базы данных
    self.optimize_database()

    # 6. Итоговая статистика
    execution_time = time.time() - start_time

    print(f"\n" + "=" * 60)
    print(f"🎉 ОЧИСТКА ЗАВЕРШЕНА за {execution_time:.1f} секунд")
    print(f"📊 СТАТИСТИКА ОЧИСТКИ:")
    print(f"   🔄 Дубликатов удалено: {self.cleanup_stats['duplicates_removed']}")
    print(f"   ❌ Некорректных удалено: {self.cleanup_stats['invalid_removed']}")
    print(f"   📦 Старых удалено: {self.cleanup_stats['old_removed']}")
    print(f"   🤖 Предсказаний очищено: {self.cleanup_stats['predictions_cleaned']}")

    total_removed = (self.cleanup_stats['duplicates_removed'] +
                     self.cleanup_stats['invalid_removed'] +
                     self.cleanup_stats['old_removed'] +
                     self.cleanup_stats['predictions_cleaned'])

    if total_removed > 0:
      print(f"   🗑️  Всего записей удалено: {total_removed}")
      print(f"   💾 Примерно освобождено: {total_removed * 0.5 / 1024:.1f} MB")

    return {
      'status': 'completed',
      'execution_time': execution_time,
      'cleanup_stats': self.cleanup_stats,
      'backup_files': self.backup_data,
      'total_removed': total_removed
    }


def interactive_cleanup():
  """
    Интерактивный режим очистки с выбором параметров
    """
  print("🧹 ИНТЕРАКТИВНАЯ ОЧИСТКА БАЗЫ ДАННЫХ")
  print("=" * 50)

  try:
    # Выбор лотерей
    available_lotteries = list(LOTTERY_CONFIGS.keys())
    print(f"\nДоступные лотереи: {', '.join(available_lotteries)}")

    lottery_input = input("Выберите лотереи (через запятую, или 'all' для всех): ").strip()

    if lottery_input.lower() == 'all':
      selected_lotteries = available_lotteries
    else:
      selected_lotteries = [l.strip() for l in lottery_input.split(',') if l.strip() in available_lotteries]

    if not selected_lotteries:
      print("❌ Не выбрано ни одной корректной лотереи")
      return

    print(f"✅ Выбранные лотереи: {', '.join(selected_lotteries)}")

    # Создание резервной копии
    backup_choice = input("\nСоздать резервную копию перед очисткой? (y/N): ").strip().lower()
    create_backup = backup_choice in ['y', 'yes', 'да']

    # Подтверждение
    print(f"\n⚠️  ВНИМАНИЕ: Будет выполнена очистка базы данных!")
    print(f"   🎯 Лотереи: {', '.join(selected_lotteries)}")
    print(f"   💾 Резервная копия: {'Да' if create_backup else 'Нет'}")

    confirm = input("\nПродолжить очистку? (y/N): ").strip().lower()

    if confirm not in ['y', 'yes', 'да']:
      print("❌ Очистка отменена пользователем")
      return

    # Выполняем очистку
    with DatabaseCleaner() as cleaner:
      result = cleaner.full_cleanup(selected_lotteries, create_backup)

      if result['status'] == 'completed':
        print(f"\n🎉 Очистка успешно завершена!")

        if result.get('backup_files'):
          print(f"📦 Созданы резервные копии:")
          for lottery, filename in result['backup_files'].items():
            print(f"   {lottery}: {filename}")
      else:
        print(f"\n❌ Очистка завершена с ошибками: {result.get('status')}")

  except KeyboardInterrupt:
    print(f"\n⏹️  Очистка прервана пользователем")
  except Exception as e:
    print(f"\n💥 Критическая ошибка: {e}")
    import traceback
    traceback.print_exc()


# Быстрые команды для командной строки
def quick_analysis():
  """Быстрый анализ без очистки"""
  with DatabaseCleaner() as cleaner:
    cleaner.analyze_database_state()


def quick_cleanup_4x20():
  """Быстрая очистка только 4x20"""
  with DatabaseCleaner() as cleaner:
    result = cleaner.full_cleanup(['4x20'], create_backup=True)
    return result


def quick_cleanup_all():
  """Быстрая очистка всех лотерей"""
  with DatabaseCleaner() as cleaner:
    result = cleaner.full_cleanup(create_backup=True)
    return result


if __name__ == "__main__":
  import argparse

  parser = argparse.ArgumentParser(description='Очистка базы данных тиражей лотерей')
  parser.add_argument('--mode', choices=['interactive', 'analysis', '4x20', 'all'],
                      default='interactive', help='Режим работы')
  parser.add_argument('--no-backup', action='store_true',
                      help='Не создавать резервную копию')

  args = parser.parse_args()

  try:
    if args.mode == 'interactive':
      interactive_cleanup()

    elif args.mode == 'analysis':
      print("🔍 РЕЖИМ: Только анализ")
      quick_analysis()

    elif args.mode == '4x20':
      print("🎯 РЕЖИМ: Очистка 4x20")
      with DatabaseCleaner() as cleaner:
        result = cleaner.full_cleanup(['4x20'], create_backup=not args.no_backup)
        print(f"✅ Результат: {result['status']}")

    elif args.mode == 'all':
      print("🌐 РЕЖИМ: Очистка всех лотерей")
      with DatabaseCleaner() as cleaner:
        result = cleaner.full_cleanup(create_backup=not args.no_backup)
        print(f"✅ Результат: {result['status']}")

  except Exception as e:
    print(f"💥 Критическая ошибка: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)

  print(f"\n👋 Работа завершена")