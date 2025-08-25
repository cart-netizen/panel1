# test_cleanup.py
"""
Простой тестовый скрипт для проверки работы очистки
"""

import sys
import os
from datetime import datetime, timedelta

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.app.core.database import SessionLocal, LotteryDraw, ModelPrediction
from backend.app.core.data_manager import LOTTERY_CONFIGS, get_lottery_limits
from backend.app.core.lottery_context import LotteryContext
from sqlalchemy import text, desc, func
from sqlalchemy.exc import SQLAlchemyError


def test_database_connection():
    """
    Простая проверка подключения к базе данных
    """
    print("🔌 ТЕСТ ПОДКЛЮЧЕНИЯ К БАЗЕ ДАННЫХ")
    print("-" * 40)
    
    try:
        session = SessionLocal()
        
        # Простой тест
        result = session.execute(text("SELECT 1")).scalar()
        
        if result == 1:
            print("✅ Подключение к базе данных работает")
            
            # Проверяем таблицы
            total_draws = session.query(LotteryDraw).count()
            print(f"📊 Всего тиражей в БД: {total_draws}")
            
            if total_draws > 0:
                # Показываем последние тиражи
                latest = session.query(LotteryDraw).order_by(
                    desc(LotteryDraw.draw_number)
                ).limit(3).all()
                
                print(f"🎲 Последние тиражи:")
                for draw in latest:
                    print(f"   #{draw.draw_number} ({draw.lottery_type}) - {draw.draw_date.date()}")
            
            # Проверяем предсказания
            try:
                predictions_count = session.query(ModelPrediction).count()
                print(f"🤖 Предсказаний AI: {predictions_count}")
            except Exception as e:
                print(f"⚠️  Таблица предсказаний недоступна: {e}")
            
            session.close()
            return True
            
        else:
            print("❌ Тест подключения не прошел")
            session.close()
            return False
            
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        return False


def test_lottery_contexts():
    """
    Тестирует работу с контекстами лотерей
    """
    print("\n🎯 ТЕСТ КОНТЕКСТОВ ЛОТЕРЕЙ")
    print("-" * 40)
    
    try:
        for lottery_type in LOTTERY_CONFIGS.keys():
            print(f"\n   Тестирование {lottery_type}...")
            
            with LotteryContext(lottery_type):
                # Получаем лимиты
                limits = get_lottery_limits()
                print(f"   📋 Лимиты: макс={limits['max_draws_in_db']}, "
                      f"загрузка={limits['initial_fetch']}")
                
                # Считаем тиражи
                session = SessionLocal()
                count = session.query(LotteryDraw).filter(
                    LotteryDraw.lottery_type == lottery_type
                ).count()
                session.close()
                
                print(f"   📊 Тиражей в БД: {count}")
        
        print("✅ Все контексты работают корректно")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка тестирования контекстов: {e}")
        return False


def test_find_duplicates():
    """
    Ищет дубликаты без их удаления
    """
    print("\n🔍 ПОИСК ДУБЛИКАТОВ (без удаления)")
    print("-" * 40)
    
    try:
        session = SessionLocal()
        total_duplicates = 0
        
        for lottery_type in LOTTERY_CONFIGS.keys():
            print(f"\n   Проверка {lottery_type}...")
            
            # Ищем дубликаты
            duplicates_query = session.query(
                LotteryDraw.draw_number,
                func.count(LotteryDraw.id).label('count')
            ).filter(
                LotteryDraw.lottery_type == lottery_type
            ).group_by(LotteryDraw.draw_number).having(
                func.count(LotteryDraw.id) > 1
            )
            
            duplicates = duplicates_query.all()
            
            if duplicates:
                print(f"   ⚠️  Найдено дубликатов: {len(duplicates)}")
                total_duplicates += len(duplicates)
                
                # Показываем первые несколько
                for i, dup in enumerate(duplicates[:3]):
                    print(f"      Тираж #{dup.draw_number}: {dup.count} копий")
                
                if len(duplicates) > 3:
                    print(f"      ... и еще {len(duplicates) - 3}")
            else:
                print(f"   ✅ Дубликатов не найдено")
        
        session.close()
        
        if total_duplicates > 0:
            print(f"\n⚠️  ИТОГО найдено дубликатов: {total_duplicates}")
            print("💡 Для удаления используйте: python quick_cleanup.py duplicates")
        else:
            print(f"\n✅ ДУБЛИКАТОВ НЕ ОБНАРУЖЕНО")
        
        return total_duplicates
        
    except Exception as e:
        print(f"❌ Ошибка поиска дубликатов: {e}")
        return -1


def test_check_limits():
    """
    Проверяет превышение лимитов размера
    """
    print("\n📦 ПРОВЕРКА ЛИМИТОВ РАЗМЕРА")
    print("-" * 40)
    
    try:
        session = SessionLocal()
        total_excess = 0
        
        for lottery_type in LOTTERY_CONFIGS.keys():
            print(f"\n   Проверка {lottery_type}...")
            
            count = session.query(LotteryDraw).filter(
                LotteryDraw.lottery_type == lottery_type
            ).count()
            
            # Получаем лимиты
            with LotteryContext(lottery_type):
                limits = get_lottery_limits()
                max_allowed = limits['max_draws_in_db']
            
            print(f"   📊 Тиражей в БД: {count}")
            print(f"   🎯 Максимум разрешено: {max_allowed}")
            
            if count > max_allowed:
                excess = count - max_allowed
                print(f"   ⚠️  Превышение: {excess} записей")
                total_excess += excess
            else:
                print(f"   ✅ Лимит не превышен")
        
        session.close()
        
        if total_excess > 0:
            print(f"\n⚠️  ИТОГО превышений: {total_excess} записей")
            print("💡 Для очистки используйте: python quick_cleanup.py limits")
        else:
            print(f"\n✅ ВСЕ ЛИМИТЫ СОБЛЮДЕНЫ")
        
        return total_excess
        
    except Exception as e:
        print(f"❌ Ошибка проверки лимитов: {e}")
        return -1


def test_old_predictions():
    """
    Проверяет наличие старых предсказаний
    """
    print("\n🤖 ПРОВЕРКА СТАРЫХ ПРЕДСКАЗАНИЙ")
    print("-" * 40)
    
    try:
        session = SessionLocal()
        
        total_predictions = session.query(ModelPrediction).count()
        print(f"   📊 Всего предсказаний: {total_predictions}")
        
        if total_predictions == 0:
            print("   ✅ Предсказаний нет")
            session.close()
            return 0
        
        # Проверяем старые предсказания (> 30 дней)
        cutoff_date = datetime.now() - timedelta(days=30)
        old_predictions = session.query(ModelPrediction).filter(
            ModelPrediction.created_at < cutoff_date
        ).count()
        
        print(f"   🗓️  Старых (>30 дней): {old_predictions}")
        
        # Самое старое предсказание
        oldest = session.query(ModelPrediction).order_by(
            ModelPrediction.created_at.asc()
        ).first()
        
        if oldest:
            days_old = (datetime.now() - oldest.created_at).days
            print(f"   📅 Самое старое: {days_old} дней назад")
        
        session.close()
        
        if old_predictions > 0:
            print(f"\n💡 Для очистки используйте: python quick_cleanup.py predictions")
        
        return old_predictions
        
    except Exception as e:
        print(f"❌ Ошибка проверки предсказаний: {e}")
        return -1


def run_full_test():
    """
    Запускает все тесты
    """
    print("🧪 ПОЛНАЯ ПРОВЕРКА БАЗЫ ДАННЫХ")
    print("=" * 50)
    
    # Тест подключения
    if not test_database_connection():
        print("\n❌ Подключение к БД не работает!")
        return False
    
    # Тест контекстов
    if not test_lottery_contexts():
        print("\n❌ Проблемы с контекстами лотерей!")
        return False
    
    # Поиск проблем
    duplicates = test_find_duplicates()
    excess_records = test_check_limits()
    old_predictions = test_old_predictions()
    
    # Итоги
    print("\n" + "=" * 50)
    print("📊 ИТОГИ ДИАГНОСТИКИ:")
    
    issues_found = 0
    
    if duplicates > 0:
        print(f"   🔄 Дубликатов: {duplicates}")
        issues_found += 1
    
    if excess_records > 0:
        print(f"   📦 Превышений лимита: {excess_records}")
        issues_found += 1
    
    if old_predictions > 0:
        print(f"   🤖 Старых предсказаний: {old_predictions}")
        issues_found += 1
    
    if issues_found == 0:
        print("   ✅ Проблем не обнаружено!")
        print("\n🎉 База данных в отличном состоянии!")
    else:
        print(f"\n⚠️  Обнаружено проблем: {issues_found}")
        print("\n💡 РЕКОМЕНДАЦИИ:")
        
        if duplicates > 0:
            print("   • Удалить дубликаты: python quick_cleanup.py duplicates")
        
        if excess_records > 0:
            print("   • Применить лимиты: python quick_cleanup.py limits")
        
        if old_predictions > 0:
            print("   • Очистить предсказания: python quick_cleanup.py predictions")
        
        print("   • Полная очистка: python quick_cleanup.py smart")
    
    return True


if __name__ == "__main__":
    try:
        success = run_full_test()
        
        if success:
            print("\n✅ Тестирование завершено успешно")
        else:
            print("\n❌ Тестирование завершено с ошибками")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⏹️  Тестирование прервано пользователем")
    except Exception as e:
        print(f"\n💥 Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)