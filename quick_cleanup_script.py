# quick_cleanup.py
"""
Быстрые команды для очистки базы данных лотерей
Простые в использовании функции без интерактивного режима
🚨 Экстренная очистка (все операции сразу)
🧠 Умная очистка (только необходимое)
⚡ Отдельные операции без интерактива
📊 Мгновенная статистика и диагностика
"""

import sys
import os
from datetime import datetime, timedelta

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.app.core.database import SessionLocal, LotteryDraw, ModelPrediction
from backend.app.core.data_manager import LOTTERY_CONFIGS
from sqlalchemy import text, desc, func
from sqlalchemy.exc import SQLAlchemyError


def remove_duplicates_quick(lottery_type: str = None) -> int:
    """
    Быстрое удаление дубликатов
    """
    print("🔄 БЫСТРОЕ УДАЛЕНИЕ ДУБЛИКАТОВ")
    
    session = SessionLocal()
    total_removed = 0
    
    try:
        lottery_types = [lottery_type] if lottery_type else list(LOTTERY_CONFIGS.keys())
        
        for ltype in lottery_types:
            print(f"   🎯 Обработка {ltype}...")
            
            # Находим дубликаты и удаляем все кроме самых старых
            duplicates = session.execute(text(f"""
                DELETE FROM lottery_draws 
                WHERE id NOT IN (
                    SELECT MIN(id) 
                    FROM lottery_draws 
                    WHERE lottery_type = '{ltype}'
                    GROUP BY draw_number
                )
                AND lottery_type = '{ltype}'
            """))
            
            removed = duplicates.rowcount
            total_removed += removed
            
            if removed > 0:
                print(f"       ❌ Удалено {removed} дубликатов")
            else:
                print(f"       ✅ Дубликатов не найдено")
        
        session.commit()
        print(f"✅ Всего удалено дубликатов: {total_removed}")
        
    except Exception as e:
        session.rollback()
        print(f"❌ Ошибка: {e}")
        total_removed = 0
    finally:
        session.close()
    
    return total_removed


def remove_old_predictions(days: int = 30) -> int:
    """
    Быстрое удаление старых предсказаний
    """
    print(f"🤖 УДАЛЕНИЕ ПРЕДСКАЗАНИЙ СТАРШЕ {days} ДНЕЙ")
    
    session = SessionLocal()
    removed = 0
    
    try:
        cutoff_date = datetime.now() - timedelta(days=days)
        
        deleted = session.query(ModelPrediction).filter(
            ModelPrediction.created_at < cutoff_date
        ).delete()
        
        session.commit()
        removed = deleted
        
        print(f"   ❌ Удалено предсказаний: {removed}")
        
    except Exception as e:
        session.rollback()
        print(f"❌ Ошибка: {e}")
    finally:
        session.close()
    
    return removed


def apply_size_limits_quick(lottery_type: str = None) -> int:
    """
    Быстрое применение лимитов размера
    """
    print("📦 ПРИМЕНЕНИЕ ЛИМИТОВ РАЗМЕРА")
    
    session = SessionLocal()
    total_removed = 0
    
    try:
        lottery_types = [lottery_type] if lottery_type else list(LOTTERY_CONFIGS.keys())
        
        for ltype in lottery_types:
            print(f"   🎯 Обработка {ltype}...")
            
            # Используем стандартный лимит 10000
            max_draws = 10000
            
            current_count = session.query(LotteryDraw).filter(
                LotteryDraw.lottery_type == ltype
            ).count()
            
            if current_count <= max_draws:
                print(f"       ✅ Лимит не превышен ({current_count}/{max_draws})")
                continue
            
            excess = current_count - max_draws
            print(f"       ⚠️  Превышение: {excess} записей")
            
            # Удаляем самые старые записи
            deleted = session.execute(text(f"""
                DELETE FROM lottery_draws 
                WHERE id IN (
                    SELECT id FROM lottery_draws 
                    WHERE lottery_type = '{ltype}'
                    ORDER BY draw_number ASC 
                    LIMIT {excess}
                )
            """))
            
            removed = deleted.rowcount
            total_removed += removed
            
            print(f"       ❌ Удалено старых записей: {removed}")
        
        session.commit()
        print(f"✅ Всего удалено старых записей: {total_removed}")
        
    except Exception as e:
        session.rollback()
        print(f"❌ Ошибка: {e}")
        total_removed = 0
    finally:
        session.close()
    
    return total_removed


def remove_invalid_records_quick(lottery_type: str = None) -> int:
    """
    Быстрое удаление явно некорректных записей
    """
    print("❌ УДАЛЕНИЕ НЕКОРРЕКТНЫХ ЗАПИСЕЙ")
    
    session = SessionLocal()
    total_removed = 0
    
    try:
        lottery_types = [lottery_type] if lottery_type else list(LOTTERY_CONFIGS.keys())
        
        for ltype in lottery_types:
            print(f"   🎯 Обработка {ltype}...")
            
            # Удаляем записи с NULL в критических полях
            removed_nulls = session.execute(text(f"""
                DELETE FROM lottery_draws 
                WHERE lottery_type = '{ltype}' 
                AND (
                    field1_numbers IS NULL 
                    OR field2_numbers IS NULL 
                    OR draw_number IS NULL 
                    OR draw_number <= 0
                    OR draw_date IS NULL
                )
            """)).rowcount
            
            # Удаляем записи с пустыми массивами
            removed_empty = session.execute(text(f"""
                DELETE FROM lottery_draws 
                WHERE lottery_type = '{ltype}' 
                AND (
                    field1_numbers = '[]'::json
                    OR field2_numbers = '[]'::json
                    OR json_array_length(field1_numbers) = 0
                    OR json_array_length(field2_numbers) = 0
                )
            """)).rowcount
            
            removed = removed_nulls + removed_empty
            total_removed += removed
            
            if removed > 0:
                print(f"       ❌ Удалено некорректных записей: {removed}")
            else:
                print(f"       ✅ Некорректных записей не найдено")
        
        session.commit()
        print(f"✅ Всего удалено некорректных записей: {total_removed}")
        
    except Exception as e:
        session.rollback()
        print(f"❌ Ошибка: {e}")
        total_removed = 0
    finally:
        session.close()
    
    return total_removed


def vacuum_database():
    """
    Быстрая оптимизация базы данных
    """
    print("⚡ ОПТИМИЗАЦИЯ БАЗЫ ДАННЫХ")
    
    session = SessionLocal()
    
    try:
        print("   🧹 Выполнение VACUUM...")
        session.execute(text("VACUUM ANALYZE lottery_draws;"))
        
        print("   📊 Обновление статистики...")
        session.execute(text("ANALYZE;"))
        
        session.commit()
        print("✅ Оптимизация завершена")
        
    except Exception as e:
        print(f"⚠️  Оптимизация завершена с предупреждениями: {e}")
    finally:
        session.close()


def emergency_cleanup():
    """
    Экстренная очистка - выполняет все основные операции
    """
    print("🚨 ЭКСТРЕННАЯ ОЧИСТКА БАЗЫ ДАННЫХ")
    print("=" * 50)
    
    stats = {
        'duplicates': 0,
        'invalid': 0,
        'old_records': 0,
        'old_predictions': 0
    }
    
    # 1. Удаляем дубликаты
    stats['duplicates'] = remove_duplicates_quick()
    
    # 2. Удаляем некорректные записи
    stats['invalid'] = remove_invalid_records_quick()
    
    # 3. Применяем лимиты размера
    stats['old_records'] = apply_size_limits_quick()
    
    # 4. Очищаем старые предсказания
    stats['old_predictions'] = remove_old_predictions(30)
    
    # 5. Оптимизируем базу
    vacuum_database()
    
    # Итоги
    total_removed = sum(stats.values())
    
    print(f"\n" + "=" * 50)
    print(f"🎉 ЭКСТРЕННАЯ ОЧИСТКА ЗАВЕРШЕНА")
    print(f"📊 СТАТИСТИКА:")
    print(f"   🔄 Дубликатов удалено: {stats['duplicates']}")
    print(f"   ❌ Некорректных удалено: {stats['invalid']}")
    print(f"   📦 Старых записей удалено: {stats['old_records']}")
    print(f"   🤖 Предсказаний удалено: {stats['old_predictions']}")
    print(f"   🗑️  ВСЕГО УДАЛЕНО: {total_removed}")
    
    if total_removed > 0:
        print(f"   💾 Примерно освобождено: {total_removed * 0.5 / 1024:.1f} MB")
    
    return stats


def get_cleanup_recommendations() -> dict:
    """
    Быстрая диагностика и рекомендации по очистке
    """
    print("🔍 ДИАГНОСТИКА И РЕКОМЕНДАЦИИ")
    print("-" * 30)
    
    session = SessionLocal()
    recommendations = {
        'duplicates_needed': False,
        'invalid_cleanup_needed': False,
        'size_limit_needed': False,
        'predictions_cleanup_needed': False,
        'optimization_needed': False,
        'issues': [],
        'actions': []
    }
    
    try:
        # Проверяем дубликаты
        for lottery_type in LOTTERY_CONFIGS.keys():
            duplicates = session.query(
                LotteryDraw.draw_number,
                func.count(LotteryDraw.id)
            ).filter(
                LotteryDraw.lottery_type == lottery_type
            ).group_by(LotteryDraw.draw_number).having(
                func.count(LotteryDraw.id) > 1
            ).count()
            
            if duplicates > 0:
                recommendations['duplicates_needed'] = True
                recommendations['issues'].append(f"{lottery_type}: {duplicates} дубликатов")
                recommendations['actions'].append(f"Удалить дубликаты для {lottery_type}")
        
        # Проверяем превышение лимитов
        for lottery_type in LOTTERY_CONFIGS.keys():
            count = session.query(LotteryDraw).filter(
                LotteryDraw.lottery_type == lottery_type
            ).count()
            
            if count > 10000:
                excess = count - 10000
                recommendations['size_limit_needed'] = True
                recommendations['issues'].append(f"{lottery_type}: превышение лимита на {excess}")
                recommendations['actions'].append(f"Применить лимиты для {lottery_type}")
        
        # Проверяем старые предсказания
        old_predictions = session.query(ModelPrediction).filter(
            ModelPrediction.created_at < datetime.now() - timedelta(days=30)
        ).count()
        
        if old_predictions > 0:
            recommendations['predictions_cleanup_needed'] = True
            recommendations['issues'].append(f"Старых предсказаний: {old_predictions}")
            recommendations['actions'].append("Очистить старые предсказания")
        
        # Проверяем производительность
        import time
        start_time = time.time()
        session.query(LotteryDraw).limit(100).all()
        query_time = time.time() - start_time
        
        if query_time > 0.1:
            recommendations['optimization_needed'] = True
            recommendations['issues'].append(f"Медленные запросы: {query_time:.3f}s")
            recommendations['actions'].append("Оптимизировать базу данных")
        
        # Выводим результаты
        if recommendations['issues']:
            print("⚠️  ОБНАРУЖЕННЫЕ ПРОБЛЕМЫ:")
            for issue in recommendations['issues']:
                print(f"   • {issue}")
            
            print("\n💡 РЕКОМЕНДУЕМЫЕ ДЕЙСТВИЯ:")
            for action in recommendations['actions']:
                print(f"   • {action}")
        else:
            print("✅ Проблем не обнаружено, очистка не требуется")
        
    except Exception as e:
        print(f"❌ Ошибка диагностики: {e}")
        recommendations['issues'].append(f"Ошибка диагностики: {e}")
    finally:
        session.close()
    
    return recommendations


def smart_cleanup():
    """
    Умная очистка - выполняет только необходимые операции
    """
    print("🧠 УМНАЯ ОЧИСТКА БАЗЫ ДАННЫХ")
    print("=" * 40)
    
    # Сначала диагностируем
    recommendations = get_cleanup_recommendations()
    
    if not recommendations['issues']:
        print("✅ Очистка не требуется!")
        return {'status': 'no_cleanup_needed'}
    
    print(f"\n🔧 ВЫПОЛНЕНИЕ НЕОБХОДИМЫХ ОПЕРАЦИЙ...")
    
    stats = {
        'duplicates': 0,
        'invalid': 0,
        'old_records': 0,
        'old_predictions': 0,
        'optimized': False
    }
    
    # Выполняем только необходимые операции
    if recommendations['duplicates_needed']:
        print("🔄 Удаление дубликатов...")
        stats['duplicates'] = remove_duplicates_quick()
    
    if recommendations['invalid_cleanup_needed']:
        print("❌ Удаление некорректных записей...")
        stats['invalid'] = remove_invalid_records_quick()
    
    if recommendations['size_limit_needed']:
        print("📦 Применение лимитов размера...")
        stats['old_records'] = apply_size_limits_quick()
    
    if recommendations['predictions_cleanup_needed']:
        print("🤖 Очистка старых предсказаний...")
        stats['old_predictions'] = remove_old_predictions()
    
    if recommendations['optimization_needed']:
        print("⚡ Оптимизация базы данных...")
        vacuum_database()
        stats['optimized'] = True
    
    # Итоги
    total_removed = stats['duplicates'] + stats['invalid'] + stats['old_records'] + stats['old_predictions']
    
    print(f"\n✅ УМНАЯ ОЧИСТКА ЗАВЕРШЕНА")
    print(f"📊 Удалено записей: {total_removed}")
    if stats['optimized']:
        print(f"⚡ База данных оптимизирована")
    
    return {
        'status': 'completed',
        'stats': stats,
        'total_removed': total_removed
    }


def cleanup_specific_lottery(lottery_type: str):
    """
    Очистка конкретной лотереи
    """
    if lottery_type not in LOTTERY_CONFIGS:
        print(f"❌ Неверный тип лотереи: {lottery_type}")
        return
    
    print(f"🎯 ОЧИСТКА ЛОТЕРЕИ {lottery_type.upper()}")
    print("-" * 30)
    
    stats = {
        'duplicates': remove_duplicates_quick(lottery_type),
        'invalid': remove_invalid_records_quick(lottery_type),
        'old_records': apply_size_limits_quick(lottery_type)
    }
    
    total_removed = sum(stats.values())
    
    print(f"\n✅ ОЧИСТКА {lottery_type} ЗАВЕРШЕНА")
    print(f"📊 Всего удалено: {total_removed} записей")
    
    return stats


def show_quick_stats():
    """
    Быстрая статистика базы данных
    """
    print("📊 БЫСТРАЯ СТАТИСТИКА")
    print("-" * 20)
    
    session = SessionLocal()
    
    try:
        for lottery_type in LOTTERY_CONFIGS.keys():
            count = session.query(LotteryDraw).filter(
                LotteryDraw.lottery_type == lottery_type
            ).count()
            
            if count > 0:
                latest = session.query(LotteryDraw).filter(
                    LotteryDraw.lottery_type == lottery_type
                ).order_by(desc(LotteryDraw.draw_number)).first()
                
                print(f"🎯 {lottery_type}: {count} тиражей (до #{latest.draw_number})")
            else:
                print(f"🎯 {lottery_type}: нет данных")
        
        # Предсказания
        predictions = session.query(ModelPrediction).count()
        print(f"🤖 Предсказания: {predictions}")
        
        # Общий размер (приблизительно)
        total_draws = session.query(LotteryDraw).count()
        estimated_size = (total_draws * 0.5 + predictions * 0.3) / 1024
        print(f"💾 Примерный размер: {estimated_size:.1f} MB")
        
    except Exception as e:
        print(f"❌ Ошибка получения статистики: {e}")
    finally:
        session.close()


# Быстрые команды для командной строки
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Быстрая очистка базы данных лотерей')
    parser.add_argument('command', choices=[
        'emergency', 'smart', 'duplicates', 'invalid', 'limits', 'predictions', 
        'vacuum', 'stats', 'recommend', 'lottery'
    ], help='Команда для выполнения')
    
    parser.add_argument('--lottery', choices=['4x20', '5x36plus'], 
                       help='Тип лотереи для специфичных команд')
    parser.add_argument('--days', type=int, default=30,
                       help='Количество дней для очистки предсказаний')
    
    args = parser.parse_args()
    
    try:
        if args.command == 'emergency':
            print("🚨 Экстренная очистка...")
            emergency_cleanup()
            
        elif args.command == 'smart':
            print("🧠 Умная очистка...")
            smart_cleanup()
            
        elif args.command == 'duplicates':
            print("🔄 Удаление дубликатов...")
            remove_duplicates_quick(args.lottery)
            
        elif args.command == 'invalid':
            print("❌ Удаление некорректных записей...")
            remove_invalid_records_quick(args.lottery)
            
        elif args.command == 'limits':
            print("📦 Применение лимитов...")
            apply_size_limits_quick(args.lottery)
            
        elif args.command == 'predictions':
            print(f"🤖 Очистка предсказаний старше {args.days} дней...")
            remove_old_predictions(args.days)
            
        elif args.command == 'vacuum':
            print("⚡ Оптимизация базы данных...")
            vacuum_database()
            
        elif args.command == 'stats':
            show_quick_stats()
            
        elif args.command == 'recommend':
            get_cleanup_recommendations()
            
        elif args.command == 'lottery':
            if not args.lottery:
                print("❌ Укажите тип лотереи с --lottery")
                sys.exit(1)
            cleanup_specific_lottery(args.lottery)
            
    except KeyboardInterrupt:
        print("\n⏹️  Операция прервана пользователем")
    except Exception as e:
        print(f"💥 Ошибка: {e}")
        sys.exit(1)