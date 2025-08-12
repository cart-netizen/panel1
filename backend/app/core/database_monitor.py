"""
Мониторинг состояния PostgreSQL базы данных
"""
from datetime import datetime

import pandas as pd
from sqlalchemy import text
from .database import SessionLocal, LotteryDraw
from .data_manager import LOTTERY_CONFIGS


def get_database_stats():
  """Получает детальную статистику по всем лотереям"""
  db = SessionLocal()
  try:
    stats = {
      'total_draws': 0,
      'lotteries': {},
      'database_info': {}
    }

    # Статистика по каждой лотерее
    for lottery_type in LOTTERY_CONFIGS.keys():
      result = db.query(
        LotteryDraw.lottery_type,
        LotteryDraw.draw_number,
        LotteryDraw.draw_date
      ).filter(
        LotteryDraw.lottery_type == lottery_type
      ).all()

      if result:
        draw_numbers = [r.draw_number for r in result]
        dates = [r.draw_date for r in result]

        lottery_stats = {
          'count': len(result),
          'min_draw': min(draw_numbers),
          'max_draw': max(draw_numbers),
          'earliest_date': min(dates).strftime('%Y-%m-%d'),
          'latest_date': max(dates).strftime('%Y-%m-%d'),
          'status': '✅ Активна' if len(result) > 50 else '⚠️ Мало данных'
        }
      else:
        lottery_stats = {
          'count': 0,
          'status': '❌ Нет данных'
        }

      stats['lotteries'][lottery_type] = lottery_stats
      stats['total_draws'] += lottery_stats['count']

    # Информация о БД
    db_info = db.execute(text("SELECT version()")).fetchone()
    stats['database_info'] = {
      'version': str(db_info[0])[:50] if db_info else 'Unknown',
      'connection_status': '✅ Подключена'
    }

    return stats

  except Exception as e:
    return {
      'error': str(e),
      'database_info': {'connection_status': '❌ Ошибка подключения'}
    }
  finally:
    db.close()


def cleanup_old_data(days_to_keep=90):
  """Очистка старых данных (опционально)"""
  from datetime import timedelta

  db = SessionLocal()
  try:
    cutoff_date = datetime.now() - timedelta(days=days_to_keep)

    deleted_total = 0
    for lottery_type in LOTTERY_CONFIGS.keys():
      deleted = db.query(LotteryDraw).filter(
        LotteryDraw.lottery_type == lottery_type,
        LotteryDraw.draw_date < cutoff_date
      ).delete()

      if deleted > 0:
        print(f"Удалено {deleted} старых записей для {lottery_type}")
        deleted_total += deleted

    if deleted_total > 0:
      db.commit()
      print(f"Всего удалено {deleted_total} старых записей")
    else:
      print("Старых записей для удаления не найдено")

    return deleted_total

  except Exception as e:
    db.rollback()
    print(f"Ошибка очистки: {e}")
    return 0
  finally:
    db.close()