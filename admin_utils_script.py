# admin_utils.py
"""
Административные утилиты для управления базой данных лотерей
Дополнительные инструменты для мониторинга и обслуживания
admin_utils.py - Административные утилиты

📊 Детальная статистика по всем аспектам БД
🔍 Поиск аномалий в данных тиражей
📤 Экспорт данных в JSON/CSV форматах
🏥 Генерация отчетов о здоровье БД (0-100 баллов)
⚡ Тесты производительности запросов
"""

import sys
import os
import pandas as pd
from datetime import datetime, timedelta
import json
from typing import List, Dict, Optional, Tuple
import time
import shutil
from pathlib import Path

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.app.core.database import SessionLocal, LotteryDraw, ModelPrediction, User
from backend.app.core.data_manager import (
    LOTTERY_CONFIGS, 
    set_current_lottery, 
    fetch_draws_from_db,
    get_current_config
)
from backend.app.core.lottery_context import LotteryContext
from sqlalchemy import text, desc, asc, func, and_, or_
from sqlalchemy.exc import SQLAlchemyError


class DatabaseAdminUtils:
    """
    Административные утилиты для управления базой данных
    """
    
    def __init__(self):
        self.session = None
    
    def __enter__(self):
        self.session = SessionLocal()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            if exc_type:
                self.session.rollback()
            self.session.close()
    
    def get_comprehensive_stats(self) -> Dict:
        """
        Получает всестороннюю статистику базы данных
        """
        print("📊 КОМПЛЕКСНАЯ СТАТИСТИКА БАЗЫ ДАННЫХ")
        print("=" * 60)
        
        stats = {
            'database_info': {},
            'lotteries': {},
            'predictions': {},
            'users': {},
            'performance': {},
            'storage': {}
        }
        
        # Общая информация о базе
        try:
            # Размер базы данных (PostgreSQL)
            db_size_query = text("""
                SELECT pg_size_pretty(pg_database_size(current_database())) as db_size,
                       pg_database_size(current_database()) as db_size_bytes
            """)
            db_info = self.session.execute(db_size_query).first()
            
            stats['database_info'] = {
                'size_pretty': db_info.db_size if db_info else 'N/A',
                'size_bytes': db_info.db_size_bytes if db_info else 0,
                'connection_info': str(self.session.bind.url)
            }
            
            print(f"💾 Размер базы данных: {stats['database_info']['size_pretty']}")
            
        except Exception as e:
            print(f"⚠️  Не удалось получить размер БД: {e}")
            stats['database_info'] = {'error': str(e)}
        
        # Статистика по лотереям
        for lottery_type in LOTTERY_CONFIGS.keys():
            lottery_stats = self._get_lottery_detailed_stats(lottery_type)
            stats['lotteries'][lottery_type] = lottery_stats
            
            print(f"\n🎯 {lottery_type.upper()}:")
            print(f"   📊 Тиражей: {lottery_stats['total_draws']}")
            print(f"   📅 Период: {lottery_stats['date_range']}")
            print(f"   🔢 Номера: {lottery_stats['number_range']}")
            print(f"   📈 Прирост за неделю: {lottery_stats['weekly_growth']}")
            print(f"   💾 Размер данных: {lottery_stats['estimated_size_mb']:.1f} MB")
        
        # Статистика предсказаний
        prediction_stats = self._get_prediction_stats()
        stats['predictions'] = prediction_stats
        
        print(f"\n🤖 ПРЕДСКАЗАНИЯ AI МОДЕЛЕЙ:")
        print(f"   📊 Всего предсказаний: {prediction_stats['total']}")
        print(f"   📈 RF предсказаний: {prediction_stats['rf_count']}")
        print(f"   🧠 LSTM предсказаний: {prediction_stats['lstm_count']}")
        print(f"   📅 За последний день: {prediction_stats['last_day']}")
        print(f"   🗑️  Устаревших (>30 дней): {prediction_stats['old_predictions']}")
        
        # Статистика пользователей (если таблица существует)
        try:
            user_stats = self._get_user_stats()
            stats['users'] = user_stats
            
            print(f"\n👥 ПОЛЬЗОВАТЕЛИ:")
            print(f"   📊 Всего пользователей: {user_stats['total']}")
            print(f"   ✅ Активных: {user_stats['active']}")
            print(f"   💎 С подписками: {user_stats['subscribed']}")
            print(f"   📅 Новых за неделю: {user_stats['new_this_week']}")
            
        except Exception as e:
            print(f"👥 ПОЛЬЗОВАТЕЛИ: таблица недоступна")
            stats['users'] = {'error': 'table_not_exists'}
        
        # Производительность
        performance_stats = self._get_performance_stats()
        stats['performance'] = performance_stats
        
        print(f"\n⚡ ПРОИЗВОДИТЕЛЬНОСТЬ:")
        print(f"   🔍 Средний запрос тиражей: {performance_stats['avg_query_time']:.3f}s")
        print(f"   📊 Самая большая таблица: {performance_stats['largest_table']}")
        print(f"   🔧 Нужна оптимизация: {'Да' if performance_stats['needs_optimization'] else 'Нет'}")
        
        return stats
    
    def _get_lottery_detailed_stats(self, lottery_type: str) -> Dict:
        """
        Получает детальную статистику для конкретной лотереи
        """
        try:
            # Основные метрики
            total_draws = self.session.query(LotteryDraw).filter(
                LotteryDraw.lottery_type == lottery_type
            ).count()
            
            if total_draws == 0:
                return {
                    'total_draws': 0,
                    'date_range': 'Нет данных',
                    'number_range': 'Нет данных',
                    'weekly_growth': 0,
                    'estimated_size_mb': 0,
                    'data_quality': 'N/A'
                }
            
            # Диапазоны
            draw_range = self.session.query(
                func.min(LotteryDraw.draw_number),
                func.max(LotteryDraw.draw_number),
                func.min(LotteryDraw.draw_date),
                func.max(LotteryDraw.draw_date)
            ).filter(LotteryDraw.lottery_type == lottery_type).first()
            
            # Прирост за неделю
            week_ago = datetime.now() - timedelta(days=7)
            weekly_new = self.session.query(LotteryDraw).filter(
                LotteryDraw.lottery_type == lottery_type,
                LotteryDraw.created_at >= week_ago
            ).count()
            
            # Качество данных
            data_quality = self._assess_data_quality(lottery_type, total_draws)
            
            return {
                'total_draws': total_draws,
                'date_range': f"{draw_range[2].strftime('%Y-%m-%d')} - {draw_range[3].strftime('%Y-%m-%d')}",
                'number_range': f"#{draw_range[0]} - #{draw_range[1]}",
                'weekly_growth': weekly_new,
                'estimated_size_mb': total_draws * 0.5 / 1024,
                'data_quality': data_quality
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def _assess_data_quality(self, lottery_type: str, total_draws: int) -> str:
        """
        Оценивает качество данных для лотереи
        """
        if total_draws == 0:
            return "Нет данных"
        
        try:
            # Проверяем несколько записей на корректность
            sample_size = min(100, total_draws)
            samples = self.session.query(LotteryDraw).filter(
                LotteryDraw.lottery_type == lottery_type
            ).order_by(desc(LotteryDraw.draw_number)).limit(sample_size).all()
            
            valid_records = 0
            for record in samples:
                try:
                    if (isinstance(record.field1_numbers, list) and 
                        isinstance(record.field2_numbers, list) and
                        len(record.field1_numbers) > 0 and 
                        len(record.field2_numbers) > 0):
                        valid_records += 1
                except:
                    pass
            
            quality_ratio = valid_records / sample_size
            
            if quality_ratio >= 0.95:
                return "Отличное"
            elif quality_ratio >= 0.85:
                return "Хорошее"
            elif quality_ratio >= 0.70:
                return "Удовлетворительное"
            else:
                return "Требует внимания"
                
        except:
            return "Не удалось оценить"
    
    def _get_prediction_stats(self) -> Dict:
        """
        Получает статистику предсказаний AI моделей
        """
        try:
            total = self.session.query(ModelPrediction).count()
            
            if total == 0:
                return {
                    'total': 0,
                    'rf_count': 0,
                    'lstm_count': 0,
                    'last_day': 0,
                    'old_predictions': 0,
                    'accuracy_data': {}
                }
            
            # Подсчет по типам моделей
            rf_count = self.session.query(ModelPrediction).filter(
                ModelPrediction.model_type == 'rf'
            ).count()
            
            lstm_count = self.session.query(ModelPrediction).filter(
                ModelPrediction.model_type == 'lstm'
            ).count()
            
            # Активность за последний день
            day_ago = datetime.now() - timedelta(days=1)
            last_day = self.session.query(ModelPrediction).filter(
                ModelPrediction.created_at >= day_ago
            ).count()
            
            # Устаревшие предсказания
            month_ago = datetime.now() - timedelta(days=30)
            old_predictions = self.session.query(ModelPrediction).filter(
                ModelPrediction.created_at < month_ago
            ).count()
            
            return {
                'total': total,
                'rf_count': rf_count,
                'lstm_count': lstm_count,
                'last_day': last_day,
                'old_predictions': old_predictions
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def _get_user_stats(self) -> Dict:
        """
        Получает статистику пользователей
        """
        # Проверяем наличие таблицы пользователей
        total = self.session.query(User).count()
        
        active = self.session.query(User).filter(
            User.is_active == True
        ).count()
        
        subscribed = self.session.query(User).filter(
            and_(
                User.subscription_status == 'active',
                User.subscription_expires_at > datetime.now()
            )
        ).count()
        
        # Новые пользователи за неделю
        week_ago = datetime.now() - timedelta(days=7)
        new_this_week = self.session.query(User).filter(
            User.created_at >= week_ago
        ).count()
        
        return {
            'total': total,
            'active': active,
            'subscribed': subscribed,
            'new_this_week': new_this_week
        }
    
    def _get_performance_stats(self) -> Dict:
        """
        Получает статистику производительности
        """
        try:
            # Тест скорости запроса
            start_time = time.time()
            self.session.query(LotteryDraw).limit(100).all()
            query_time = time.time() - start_time
            
            # Размеры таблиц (PostgreSQL)
            table_sizes = self.session.execute(text("""
                SELECT 
                    schemaname,
                    tablename,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
                FROM pg_tables 
                WHERE schemaname = 'public'
                ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
                LIMIT 5
            """)).fetchall()
            
            largest_table = table_sizes[0].tablename if table_sizes else 'unknown'
            
            # Нужна ли оптимизация
            needs_optimization = query_time > 0.1 or len(table_sizes) > 3
            
            return {
                'avg_query_time': query_time,
                'largest_table': largest_table,
                'needs_optimization': needs_optimization,
                'table_sizes': [(t.tablename, t.size) for t in table_sizes]
            }
            
        except Exception as e:
            return {
                'avg_query_time': 0,
                'largest_table': 'unknown',
                'needs_optimization': False,
                'error': str(e)
            }
    
    def find_data_anomalies(self, lottery_type: str) -> Dict:
        """
        Ищет аномалии в данных лотереи
        """
        print(f"🔍 ПОИСК АНОМАЛИЙ В ДАННЫХ {lottery_type}")
        print("-" * 40)
        
        anomalies = {
            'gaps_in_numbering': [],
            'duplicate_dates': [],
            'suspicious_patterns': [],
            'data_inconsistencies': []
        }
        
        try:
            # Получаем все тиражи
            draws = self.session.query(LotteryDraw).filter(
                LotteryDraw.lottery_type == lottery_type
            ).order_by(LotteryDraw.draw_number).all()
            
            if not draws:
                print("   📭 Нет данных для анализа")
                return anomalies
            
            # Поиск пропусков в нумерации
            draw_numbers = [d.draw_number for d in draws]
            expected_range = set(range(min(draw_numbers), max(draw_numbers) + 1))
            actual_numbers = set(draw_numbers)
            gaps = sorted(expected_range - actual_numbers)
            
            if gaps:
                anomalies['gaps_in_numbering'] = gaps
                print(f"   ⚠️  Найдено пропусков в нумерации: {len(gaps)}")
                if len(gaps) <= 10:
                    print(f"       Пропущенные тиражи: {gaps}")
                else:
                    print(f"       Примеры пропусков: {gaps[:5]} ... {gaps[-5:]}")
            
            # Поиск дубликатов дат
            date_counts = {}
            for draw in draws:
                date_key = draw.draw_date.date()
                date_counts[date_key] = date_counts.get(date_key, 0) + 1
            
            duplicate_dates = [(date, count) for date, count in date_counts.items() if count > 7]  # Больше 7 тиражей в день
            if duplicate_dates:
                anomalies['duplicate_dates'] = duplicate_dates
                print(f"   ⚠️  Подозрительно много тиражей в день:")
                for date, count in duplicate_dates[:5]:
                    print(f"       {date}: {count} тиражей")
            
            # Поиск подозрительных паттернов в числах
            with LotteryContext(lottery_type):
                config = get_current_config()
                suspicious_patterns = self._find_number_patterns(draws, config)
                
                if suspicious_patterns:
                    anomalies['suspicious_patterns'] = suspicious_patterns
                    print(f"   🔍 Найдены подозрительные паттерны:")
                    for pattern in suspicious_patterns[:3]:
                        print(f"       {pattern}")
            
            # Проверка консистентности данных
            inconsistencies = self._check_data_consistency(draws, lottery_type)
            if inconsistencies:
                anomalies['data_inconsistencies'] = inconsistencies
                print(f"   ❌ Найдены несоответствия в данных:")
                for issue in inconsistencies[:3]:
                    print(f"       {issue}")
            
            if not any(anomalies.values()):
                print("   ✅ Аномалий не обнаружено")
            
            return anomalies
            
        except Exception as e:
            print(f"   ❌ Ошибка поиска аномалий: {e}")
            return {'error': str(e)}
    
    def _find_number_patterns(self, draws: List[LotteryDraw], config: Dict) -> List[str]:
        """
        Ищет подозрительные паттерны в числах
        """
        patterns = []
        
        try:
            # Проверяем последние 100 тиражей
            recent_draws = draws[-100:] if len(draws) > 100 else draws
            
            for draw in recent_draws:
                f1_nums = draw.field1_numbers
                f2_nums = draw.field2_numbers
                
                if not isinstance(f1_nums, list) or not isinstance(f2_nums, list):
                    continue
                
                # Проверка на арифметическую прогрессию
                if len(f1_nums) >= 3:
                    sorted_f1 = sorted(f1_nums)
                    if self._is_arithmetic_sequence(sorted_f1):
                        patterns.append(f"Тираж #{draw.draw_number}: арифметическая прогрессия в поле 1")
                
                # Проверка на одинаковые числа
                if len(set(f1_nums)) == 1:
                    patterns.append(f"Тираж #{draw.draw_number}: все числа одинаковые в поле 1")
                
                if len(set(f2_nums)) == 1:
                    patterns.append(f"Тираж #{draw.draw_number}: все числа одинаковые в поле 2")
                
                # Проверка на экстремальные значения
                if all(n <= 5 for n in f1_nums):
                    patterns.append(f"Тираж #{draw.draw_number}: все числа <= 5 в поле 1")
                
                if all(n >= config['field1_max'] - 5 for n in f1_nums):
                    patterns.append(f"Тираж #{draw.draw_number}: все числа >= {config['field1_max'] - 5} в поле 1")
            
            return patterns
            
        except Exception:
            return []
    
    def _is_arithmetic_sequence(self, numbers: List[int]) -> bool:
        """
        Проверяет, является ли последовательность арифметической прогрессией
        """
        if len(numbers) < 3:
            return False
        
        diff = numbers[1] - numbers[0]
        for i in range(2, len(numbers)):
            if numbers[i] - numbers[i-1] != diff:
                return False
        return True
    
    def _check_data_consistency(self, draws: List[LotteryDraw], lottery_type: str) -> List[str]:
        """
        Проверяет консистентность данных
        """
        issues = []
        
        try:
            with LotteryContext(lottery_type):
                config = get_current_config()
                expected_f1_size = config['field1_size']
                expected_f2_size = config['field2_size']
            
            for draw in draws[-50:]:  # Проверяем последние 50
                # Проверка размеров полей
                if len(draw.field1_numbers) != expected_f1_size:
                    issues.append(f"Тираж #{draw.draw_number}: неверный размер поля 1 ({len(draw.field1_numbers)} != {expected_f1_size})")
                
                if len(draw.field2_numbers) != expected_f2_size:
                    issues.append(f"Тираж #{draw.draw_number}: неверный размер поля 2 ({len(draw.field2_numbers)} != {expected_f2_size})")
                
                # Проверка диапазонов
                for num in draw.field1_numbers:
                    if not (1 <= num <= config['field1_max']):
                        issues.append(f"Тираж #{draw.draw_number}: число {num} вне диапазона поля 1")
                
                for num in draw.field2_numbers:
                    if not (1 <= num <= config['field2_max']):
                        issues.append(f"Тираж #{draw.draw_number}: число {num} вне диапазона поля 2")
                
                # Проверка на дубликаты внутри поля
                if len(set(draw.field1_numbers)) != len(draw.field1_numbers):
                    issues.append(f"Тираж #{draw.draw_number}: дубликаты в поле 1")
                
                if len(set(draw.field2_numbers)) != len(draw.field2_numbers):
                    issues.append(f"Тираж #{draw.draw_number}: дубликаты в поле 2")
            
            return issues[:10]  # Возвращаем максимум 10 проблем
            
        except Exception:
            return []
    
    def export_data(self, lottery_type: str, output_format: str = 'json', 
                   limit: Optional[int] = None) -> str:
        """
        Экспортирует данные лотереи в различных форматах
        """
        print(f"📤 ЭКСПОРТ ДАННЫХ {lottery_type} в формате {output_format.upper()}")
        
        try:
            query = self.session.query(LotteryDraw).filter(
                LotteryDraw.lottery_type == lottery_type
            ).order_by(desc(LotteryDraw.draw_number))
            
            if limit:
                query = query.limit(limit)
            
            draws = query.all()
            
            if not draws:
                print("   📭 Нет данных для экспорта")
                return ""
            
            # Подготавливаем данные
            export_data = []
            for draw in draws:
                export_data.append({
                    'draw_number': draw.draw_number,
                    'draw_date': draw.draw_date.isoformat(),
                    'field1_numbers': draw.field1_numbers,
                    'field2_numbers': draw.field2_numbers,
                    'prize_info': draw.prize_info,
                    'created_at': draw.created_at.isoformat() if draw.created_at else None
                })
            
            # Генерируем имя файла
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"export_{lottery_type}_{timestamp}.{output_format}"
            
            # Экспортируем в нужном формате
            if output_format == 'json':
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)
                    
            elif output_format == 'csv':
                # Конвертируем в DataFrame для CSV
                df_data = []
                for item in export_data:
                    row = {
                        'Тираж': item['draw_number'],
                        'Дата': item['draw_date'][:10],  # Только дата
                        'Поле1': ','.join(map(str, sorted(item['field1_numbers']))),
                        'Поле2': ','.join(map(str, sorted(item['field2_numbers']))),
                        'Приз': item['prize_info'].get('amount', 0) if item['prize_info'] else 0
                    }
                    df_data.append(row)
                
                df = pd.DataFrame(df_data)
                df.to_csv(filename, index=False, encoding='utf-8')
                
            else:
                raise ValueError(f"Неподдерживаемый формат: {output_format}")
            
            file_size = os.path.getsize(filename) / 1024  # KB
            
            print(f"   ✅ Экспортировано {len(export_data)} записей")
            print(f"   📄 Файл: {filename}")
            print(f"   💾 Размер: {file_size:.1f} KB")
            
            return filename
            
        except Exception as e:
            print(f"   ❌ Ошибка экспорта: {e}")
            return ""
    
    def generate_health_report(self) -> Dict:
        """
        Генерирует отчет о состоянии здоровья базы данных
        """
        print("🏥 ОТЧЕТ О СОСТОЯНИИ БАЗЫ ДАННЫХ")
        print("=" * 60)
        
        health_report = {
            'timestamp': datetime.now().isoformat(),
            'overall_health': 'unknown',
            'score': 0,
            'issues': [],
            'recommendations': [],
            'details': {}
        }
        
        total_score = 0
        max_score = 0
        
        # Проверяем каждую лотерею
        for lottery_type in LOTTERY_CONFIGS.keys():
            print(f"\n🎯 Проверка {lottery_type}...")
            
            lottery_health = self._assess_lottery_health(lottery_type)
            health_report['details'][lottery_type] = lottery_health
            
            # Добавляем к общему счету
            total_score += lottery_health.get('score', 0)
            max_score += 100
            
            # Собираем проблемы и рекомендации
            health_report['issues'].extend(lottery_health.get('issues', []))
            health_report['recommendations'].extend(lottery_health.get('recommendations', []))
        
        # Проверяем общие аспекты
        general_health = self._assess_general_health()
        health_report['details']['general'] = general_health
        total_score += general_health.get('score', 0)
        max_score += 100
        
        # Рассчитываем общую оценку
        if max_score > 0:
            health_report['score'] = int((total_score / max_score) * 100)
        
        # Определяем общее состояние
        if health_report['score'] >= 90:
            health_report['overall_health'] = 'excellent'
            health_status = "🟢 ОТЛИЧНОЕ"
        elif health_report['score'] >= 75:
            health_report['overall_health'] = 'good'
            health_status = "🟡 ХОРОШЕЕ"
        elif health_report['score'] >= 60:
            health_report['overall_health'] = 'fair'
            health_status = "🟠 УДОВЛЕТВОРИТЕЛЬНОЕ"
        else:
            health_report['overall_health'] = 'poor'
            health_status = "🔴 ТРЕБУЕТ ВНИМАНИЯ"
        
        print(f"\n" + "=" * 60)
        print(f"🏥 ОБЩАЯ ОЦЕНКА ЗДОРОВЬЯ: {health_status}")
        print(f"📊 Балл: {health_report['score']}/100")
        
        if health_report['issues']:
            print(f"\n⚠️  ОБНАРУЖЕННЫЕ ПРОБЛЕМЫ ({len(health_report['issues'])}):")
            for i, issue in enumerate(health_report['issues'][:10], 1):
                print(f"   {i}. {issue}")
        
        if health_report['recommendations']:
            print(f"\n💡 РЕКОМЕНДАЦИИ ({len(health_report['recommendations'])}):")
            for i, rec in enumerate(health_report['recommendations'][:10], 1):
                print(f"   {i}. {rec}")
        
        # Сохраняем отчет в файл
        report_filename = f"health_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_filename, 'w', encoding='utf-8') as f:
            json.dump(health_report, f, indent=2, ensure_ascii=False)
        
        print(f"\n📄 Отчет сохранен: {report_filename}")
        
        return health_report
    
    def _assess_lottery_health(self, lottery_type: str) -> Dict:
        """
        Оценивает здоровье конкретной лотереи
        """
        health = {
            'score': 0,
            'issues': [],
            'recommendations': [],
            'metrics': {}
        }
        
        try:
            # Получаем базовую статистику
            total_draws = self.session.query(LotteryDraw).filter(
                LotteryDraw.lottery_type == lottery_type
            ).count()
            
            if total_draws == 0:
                health['issues'].append(f"{lottery_type}: Нет данных")
                health['recommendations'].append(f"Загрузить данные для {lottery_type}")
                return health
            
            score = 0
            
            # Критерий 1: Количество данных (25 баллов)
            with LotteryContext(lottery_type):
                limits = get_lottery_limits()
                min_required = limits.get('min_for_training', 100)
                optimal_amount = limits.get('initial_fetch', 500)
            
            if total_draws >= optimal_amount:
                score += 25
            elif total_draws >= min_required:
                score += 15
                health['recommendations'].append(f"{lottery_type}: Желательно больше исторических данных")
            else:
                health['issues'].append(f"{lottery_type}: Недостаточно данных для обучения моделей")
                health['recommendations'].append(f"Загрузить больше данных для {lottery_type}")
            
            # Критерий 2: Актуальность данных (25 баллов)
            latest_draw = self.session.query(LotteryDraw).filter(
                LotteryDraw.lottery_type == lottery_type
            ).order_by(desc(LotteryDraw.draw_date)).first()
            
            if latest_draw:
                days_old = (datetime.now() - latest_draw.draw_date).days
                if days_old <= 1:
                    score += 25
                elif days_old <= 3:
                    score += 20
                elif days_old <= 7:
                    score += 15
                    health['recommendations'].append(f"{lottery_type}: Данные устарели на {days_old} дней")
                else:
                    score += 5
                    health['issues'].append(f"{lottery_type}: Данные устарели на {days_old} дней")
                    health['recommendations'].append(f"Обновить данные для {lottery_type}")
            
            # Критерий 3: Целостность данных (25 баллов)
            # Проверяем дубликаты
            duplicates = self.session.query(
                LotteryDraw.draw_number,
                func.count(LotteryDraw.id)
            ).filter(
                LotteryDraw.lottery_type == lottery_type
            ).group_by(LotteryDraw.draw_number).having(
                func.count(LotteryDraw.id) > 1
            ).count()
            
            if duplicates == 0:
                score += 10
            else:
                health['issues'].append(f"{lottery_type}: Найдено {duplicates} дубликатов")
                health['recommendations'].append(f"Удалить дубликаты для {lottery_type}")
            
            # Проверяем качество структуры данных
            sample_size = min(50, total_draws)
            sample_draws = self.session.query(LotteryDraw).filter(
                LotteryDraw.lottery_type == lottery_type
            ).order_by(desc(LotteryDraw.draw_number)).limit(sample_size).all()
            
            valid_structure = 0
            for draw in sample_draws:
                if (isinstance(draw.field1_numbers, list) and 
                    isinstance(draw.field2_numbers, list) and
                    len(draw.field1_numbers) > 0 and 
                    len(draw.field2_numbers) > 0):
                    valid_structure += 1
            
            structure_quality = valid_structure / sample_size
            if structure_quality >= 0.95:
                score += 15
            elif structure_quality >= 0.85:
                score += 10
                health['recommendations'].append(f"{lottery_type}: Некоторые записи имеют проблемы со структурой")
            else:
                health['issues'].append(f"{lottery_type}: Многие записи имеют некорректную структуру")
                health['recommendations'].append(f"Очистить некорректные записи для {lottery_type}")
            
            # Критерий 4: Производительность (25 баллов)
            # Тест скорости запроса
            start_time = time.time()
            self.session.query(LotteryDraw).filter(
                LotteryDraw.lottery_type == lottery_type
            ).order_by(desc(LotteryDraw.draw_number)).limit(100).all()
            query_time = time.time() - start_time
            
            if query_time <= 0.05:
                score += 25
            elif query_time <= 0.1:
                score += 20
            elif query_time <= 0.2:
                score += 15
                health['recommendations'].append(f"{lottery_type}: Производительность запросов можно улучшить")
            else:
                score += 5
                health['issues'].append(f"{lottery_type}: Медленные запросы ({query_time:.3f}s)")
                health['recommendations'].append(f"Оптимизировать индексы для {lottery_type}")
            
            health['score'] = score
            health['metrics'] = {
                'total_draws': total_draws,
                'days_since_update': days_old if latest_draw else 999,
                'duplicates': duplicates,
                'structure_quality': structure_quality,
                'query_time': query_time
            }
            
            return health
            
        except Exception as e:
            health['issues'].append(f"{lottery_type}: Ошибка анализа - {e}")
            return health
    
    def _assess_general_health(self) -> Dict:
        """
        Оценивает общие аспекты здоровья базы данных
        """
        health = {
            'score': 0,
            'issues': [],
            'recommendations': [],
            'metrics': {}
        }
        
        try:
            score = 0
            
            # Критерий 1: Размер базы данных (25 баллов)
            try:
                db_size_query = text("SELECT pg_database_size(current_database())")
                db_size_bytes = self.session.execute(db_size_query).scalar()
                db_size_mb = db_size_bytes / (1024 * 1024)
                
                if db_size_mb < 100:
                    score += 25
                elif db_size_mb < 500:
                    score += 20
                elif db_size_mb < 1000:
                    score += 15
                    health['recommendations'].append("Рассмотрите архивирование старых данных")
                else:
                    score += 10
                    health['issues'].append(f"Большой размер базы данных: {db_size_mb:.1f} MB")
                    health['recommendations'].append("Необходима оптимизация размера БД")
                
                health['metrics']['db_size_mb'] = db_size_mb
                
            except Exception as e:
                health['issues'].append(f"Не удалось определить размер БД: {e}")
            
            # Критерий 2: Статус предсказаний (25 баллов)
            total_predictions = self.session.query(ModelPrediction).count()
            
            if total_predictions > 0:
                # Проверяем свежесть предсказаний
                recent_predictions = self.session.query(ModelPrediction).filter(
                    ModelPrediction.created_at >= datetime.now() - timedelta(days=7)
                ).count()
                
                if recent_predictions > 0:
                    score += 25
                else:
                    score += 10
                    health['recommendations'].append("AI модели давно не создавали предсказания")
                
                # Проверяем устаревшие предсказания
                old_predictions = self.session.query(ModelPrediction).filter(
                    ModelPrediction.created_at < datetime.now() - timedelta(days=30)
                ).count()
                
                if old_predictions > 100:
                    health['recommendations'].append(f"Много устаревших предсказаний: {old_predictions}")
                
                health['metrics']['total_predictions'] = total_predictions
                health['metrics']['recent_predictions'] = recent_predictions
                health['metrics']['old_predictions'] = old_predictions
            else:
                score += 15
                health['recommendations'].append("Нет предсказаний AI моделей")
            
            # Критерий 3: Подключение к базе данных (25 баллов)
            try:
                # Тест простого запроса
                self.session.execute(text("SELECT 1")).scalar()
                score += 25
            except Exception as e:
                health['issues'].append(f"Проблемы с подключением к БД: {e}")
            
            # Критерий 4: Общая производительность (25 баллов)
            try:
                # Комплексный тест производительности
                start_time = time.time()
                
                # Несколько разных запросов
                self.session.query(func.count(LotteryDraw.id)).scalar()
                self.session.query(func.max(LotteryDraw.draw_number)).scalar()
                
                total_time = time.time() - start_time
                
                if total_time <= 0.1:
                    score += 25
                elif total_time <= 0.3:
                    score += 20
                elif total_time <= 0.5:
                    score += 15
                else:
                    score += 10
                    health['issues'].append(f"Медленная производительность БД: {total_time:.3f}s")
                    health['recommendations'].append("Рассмотрите оптимизацию индексов")
                
                health['metrics']['performance_test_time'] = total_time
                
            except Exception as e:
                health['issues'].append(f"Ошибка теста производительности: {e}")
            
            health['score'] = score
            return health
            
        except Exception as e:
            health['issues'].append(f"Ошибка общего анализа: {e}")
            return health


def interactive_admin_menu():
    """
    Интерактивное меню административных утилит
    """
    print("🔧 АДМИНИСТРАТИВНЫЕ УТИЛИТЫ БАЗЫ ДАННЫХ")
    print("=" * 50)
    
    while True:
        print(f"\n📋 МЕНЮ КОМАНД:")
        print(f"   1. 📊 Комплексная статистика")
        print(f"   2. 🔍 Поиск аномалий в данных")
        print(f"   3. 📤 Экспорт данных")
        print(f"   4. 🏥 Отчет о состоянии здоровья")
        print(f"   5. 🧹 Быстрая очистка")
        print(f"   6. ⚡ Тест производительности")
        print(f"   0. 🚪 Выход")
        
        try:
            choice = input("\nВыберите команду (0-6): ").strip()
            
            if choice == '0':
                print("👋 До свидания!")
                break
            elif choice == '1':
                with DatabaseAdminUtils() as admin:
                    admin.get_comprehensive_stats()
            elif choice == '2':
                lottery = input("Введите тип лотереи (4x20/5x36plus): ").strip()
                if lottery in LOTTERY_CONFIGS:
                    with DatabaseAdminUtils() as admin:
                        admin.find_data_anomalies(lottery)
                else:
                    print("❌ Неверный тип лотереи")
            elif choice == '3':
                lottery = input("Введите тип лотереи (4x20/5x36plus): ").strip()
                format_choice = input("Формат (json/csv): ").strip().lower()
                limit_input = input("Лимит записей (Enter для всех): ").strip()
                
                limit = int(limit_input) if limit_input.isdigit() else None
                
                if lottery in LOTTERY_CONFIGS and format_choice in ['json', 'csv']:
                    with DatabaseAdminUtils() as admin:
                        admin.export_data(lottery, format_choice, limit)
                else:
                    print("❌ Неверные параметры")
            elif choice == '4':
                with DatabaseAdminUtils() as admin:
                    admin.generate_health_report()
            elif choice == '5':
                print("🧹 Запуск быстрой очистки...")
                from database_cleanup import quick_cleanup_all
                quick_cleanup_all()
            elif choice == '6':
                performance_test()
            else:
                print("❌ Неверный выбор")
                
        except KeyboardInterrupt:
            print("\n⏹️  Операция прервана пользователем")
        except Exception as e:
            print(f"❌ Ошибка: {e}")


def performance_test():
    """
    Тестирует производительность базы данных
    """
    print("⚡ ТЕСТ ПРОИЗВОДИТЕЛЬНОСТИ БАЗЫ ДАННЫХ")
    print("-" * 40)
    
    try:
        with DatabaseAdminUtils() as admin:
            results = {}
            
            # Тест 1: Простые запросы
            start_time = time.time()
            total_draws = admin.session.query(LotteryDraw).count()
            results['count_query'] = time.time() - start_time
            
            # Тест 2: Сложные запросы с сортировкой
            start_time = time.time()
            latest_draws = admin.session.query(LotteryDraw).order_by(
                desc(LotteryDraw.draw_number)
            ).limit(100).all()
            results['sort_query'] = time.time() - start_time
            
            # Тест 3: Агрегация
            start_time = time.time()
            lottery_counts = admin.session.query(
                LotteryDraw.lottery_type,
                func.count(LotteryDraw.id)
            ).group_by(LotteryDraw.lottery_type).all()
            results['aggregate_query'] = time.time() - start_time
            
            # Тест 4: Фильтрация по дате
            start_time = time.time()
            recent_draws = admin.session.query(LotteryDraw).filter(
                LotteryDraw.draw_date >= datetime.now() - timedelta(days=30)
            ).count()
            results['filter_query'] = time.time() - start_time
            
            # Результаты
            print(f"📊 РЕЗУЛЬТАТЫ ТЕСТОВ:")
            print(f"   📈 Подсчет записей: {results['count_query']:.3f}s ({total_draws} записей)")
            print(f"   🔄 Сортировка: {results['sort_query']:.3f}s (100 записей)")
            print(f"   📊 Агрегация: {results['aggregate_query']:.3f}s ({len(lottery_counts)} групп)")
            print(f"   🔍 Фильтрация: {results['filter_query']:.3f}s ({recent_draws} записей)")
            
            # Общая оценка
            avg_time = sum(results.values()) / len(results)
            
            if avg_time <= 0.05:
                performance_rating = "🟢 ОТЛИЧНАЯ"
            elif avg_time <= 0.1:
                performance_rating = "🟡 ХОРОШАЯ"
            elif avg_time <= 0.2:
                performance_rating = "🟠 УДОВЛЕТВОРИТЕЛЬНАЯ"
            else:
                performance_rating = "🔴 ТРЕБУЕТ ОПТИМИЗАЦИИ"
            
            print(f"\n⚡ ОБЩАЯ ПРОИЗВОДИТЕЛЬНОСТЬ: {performance_rating}")
            print(f"📊 Среднее время запроса: {avg_time:.3f}s")
            
            if avg_time > 0.1:
                print(f"\n💡 РЕКОМЕНДАЦИИ:")
                print(f"   • Добавить индексы на часто используемые поля")
                print(f"   • Выполнить VACUUM ANALYZE")
                print(f"   • Рассмотреть архивирование старых данных")
        
    except Exception as e:
        print(f"❌ Ошибка теста производительности: {e}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Административные утилиты для базы данных лотерей')
    parser.add_argument('--mode', choices=['interactive', 'stats', 'health', 'performance', 'anomalies'], 
                       default='interactive', help='Режим работы')
    parser.add_argument('--lottery', choices=['4x20', '5x36plus'], 
                       help='Тип лотереи для специфичных команд')
    parser.add_argument('--export', choices=['json', 'csv'], 
                       help='Экспорт данных в указанном формате')
    parser.add_argument('--limit', type=int, 
                       help='Лимит записей для экспорта')
    
    args = parser.parse_args()
    
    try:
        if args.mode == 'interactive':
            interactive_admin_menu()
            
        elif args.mode == 'stats':
            print("📊 РЕЖИМ: Комплексная статистика")
            with DatabaseAdminUtils() as admin:
                admin.get_comprehensive_stats()
                
        elif args.mode == 'health':
            print("🏥 РЕЖИМ: Отчет о здоровье")
            with DatabaseAdminUtils() as admin:
                admin.generate_health_report()
                
        elif args.mode == 'performance':
            print("⚡ РЕЖИМ: Тест производительности")
            performance_test()
            
        elif args.mode == 'anomalies':
            if not args.lottery:
                print("❌ Для поиска аномалий требуется указать --lottery")
                sys.exit(1)
            
            print(f"🔍 РЕЖИМ: Поиск аномалий в {args.lottery}")
            with DatabaseAdminUtils() as admin:
                admin.find_data_anomalies(args.lottery)
        
        # Обработка экспорта
        if args.export and args.lottery:
            print(f"📤 Экспорт данных {args.lottery} в формате {args.export}")
            with DatabaseAdminUtils() as admin:
                admin.export_data(args.lottery, args.export, args.limit)
                
    except Exception as e:
        print(f"💥 Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    print(f"\n✅ Работа утилит завершена")