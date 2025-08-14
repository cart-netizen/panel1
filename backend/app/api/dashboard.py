

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, text
from sqlalchemy import or_
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import pandas as pd

from backend.app.core.database import get_db, UserActivity, ModelStatistics, DashboardCache, LotteryDraw
from backend.app.core import data_manager
from backend.app.core.lottery_context import LotteryContext
from backend.app.models.schemas import DashboardStats, ActivityItem, TrendAnalysis
from backend.app.core.subscription_protection import get_current_user_optional_sync as get_current_user_optional

router = APIRouter()

# --- Pydantic модели для ответов ---

class PredictionAccuracy(BaseModel):
    value: float
    change: float

class LatestDraw(BaseModel):
    draw_number: int
    draw_date: str
    field1_numbers: List[int]
    field2_numbers: List[int]

class DashboardService:
    """Сервис для работы с данными дашборда"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def log_activity(self, activity_type: str, description: str, 
                    user_id: Optional[int] = None, lottery_type: Optional[str] = None,
                    details: Optional[Dict] = None, request: Optional[Request] = None):
        """Логирование активности пользователя"""
        activity = UserActivity(
            user_id=user_id,
            activity_type=activity_type,
            activity_description=description,
            lottery_type=lottery_type,
            details=details or {},
            created_at=datetime.utcnow(),
            ip_address=request.client.host if request else None,
            user_agent=str(request.headers.get("user-agent", "")) if request else None
        )
        self.db.add(activity)
        self.db.commit()
        return activity

    def get_dashboard_stats(self, user_id: Optional[int] = None) -> DashboardStats:
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        # Активность за сегодня
        generations_today = self.db.query(UserActivity).filter(
            UserActivity.activity_type == 'generation',
            UserActivity.created_at >= today_start,
            (UserActivity.user_id == user_id if user_id else True)
        ).count()

        # ИСПРАВЛЕНО: Подсчет анализов трендов (включая автозапросы от frontend)
        trend_analyses = self.db.query(UserActivity).filter(
            UserActivity.activity_type.in_(['trends', 'analysis']),
            UserActivity.created_at >= today_start,
            (UserActivity.user_id == user_id if user_id else True)
        ).count()

        total_generations = self.db.query(UserActivity).filter(
            UserActivity.activity_type == 'generation',
            (UserActivity.user_id == user_id if user_id else True)
        ).count()

        # ИСПРАВЛЕНО: Точность прогнозов и её динамика
        thirty_days_ago = today_start - timedelta(days=30)
        one_week_ago = today_start - timedelta(days=7)
        two_weeks_ago = today_start - timedelta(days=14)

        # Средняя точность за последние 30 дней
        try:
            current_accuracy_result = self.db.query(func.avg(ModelStatistics.accuracy_percentage)).filter(
                ModelStatistics.period_start >= thirty_days_ago,
                ModelStatistics.model_type == 'rf'  # Фокусируемся на RF модели
            ).scalar()
            current_accuracy_avg = float(current_accuracy_result) if current_accuracy_result else 0.0
        except:
            current_accuracy_avg = 0.0

        # Динамика: сравниваем последнюю неделю с предпоследней
        try:
            last_week_result = self.db.query(func.avg(ModelStatistics.accuracy_percentage)).filter(
                ModelStatistics.period_start >= one_week_ago,
                ModelStatistics.model_type == 'rf'
            ).scalar()
            last_week_avg = float(last_week_result) if last_week_result else 0.0

            previous_week_result = self.db.query(func.avg(ModelStatistics.accuracy_percentage)).filter(
                ModelStatistics.period_start >= two_weeks_ago,
                ModelStatistics.period_start < one_week_ago,
                ModelStatistics.model_type == 'rf'
            ).scalar()
            previous_week_avg = float(previous_week_result) if previous_week_result else 0.0

            accuracy_change = last_week_avg - previous_week_avg if previous_week_avg > 0 else 0.0
        except:
            last_week_avg = 0.0
            previous_week_avg = 0.0
            accuracy_change = 0.0

        # ИСПРАВЛЕНО: Лучшая оценка RF
        best_score_result = self.db.query(func.max(ModelStatistics.best_score)).filter(
            ModelStatistics.model_type == 'rf'
        ).scalar()
        best_score = float(best_score_result) if best_score_result else None

        # Недавняя активность
        recent_activities_db = self.db.query(UserActivity).filter(
            (UserActivity.user_id == user_id if user_id else True)
        ).order_by(desc(UserActivity.created_at)).limit(5).all()

        recent_activities = [ActivityItem.from_orm(act) for act in recent_activities_db]

        return DashboardStats(
            generations_today=generations_today,
            trend_analyses=trend_analyses,
            accuracy_percentage=PredictionAccuracy(
                value=round(current_accuracy_avg, 1),
                change=round(accuracy_change, 1)
            ),
            best_score=round(best_score, 3) if best_score is not None else 'N/A',
            total_generations=total_generations,
            recent_activities=recent_activities
        )
    
    def get_trends_analysis(self, lottery_type: str) -> Dict[str, Any]:
        """Получение анализа трендов для лотереи"""
        with LotteryContext(lottery_type):
            df = data_manager.fetch_draws_from_db()
            
            if df.empty:
                return {
                    'lottery_type': lottery_type,
                    'trends': None,
                    'analyzed_draws': 0,
                    'timestamp': datetime.utcnow().isoformat(),
                    'summary': 'Недостаточно данных для анализа трендов',
                    'recommendations': []
                }
            
            config = data_manager.LOTTERY_CONFIGS[lottery_type]
            analyzed_draws = len(df)
            
            # Анализируем последние 20 тиражей для трендов
            recent_df = df.head(20) if len(df) >= 20 else df
            
            # Подсчитываем частоту каждого числа в последних тиражах
            field1_counts = {}
            field2_counts = {}
            
            for _, row in recent_df.iterrows():
                for num in row['Числа_Поле1_list']:
                    field1_counts[num] = field1_counts.get(num, 0) + 1
                for num in row['Числа_Поле2_list']:
                    field2_counts[num] = field2_counts.get(num, 0) + 1
            
            # Горячие числа (встречаются чаще среднего)
            avg_freq_f1 = sum(field1_counts.values()) / len(field1_counts) if field1_counts else 0
            avg_freq_f2 = sum(field2_counts.values()) / len(field2_counts) if field2_counts else 0
            
            hot_f1 = sorted([num for num, count in field1_counts.items() if count > avg_freq_f1], 
                           key=lambda x: field1_counts[x], reverse=True)[:8]
            hot_f2 = sorted([num for num, count in field2_counts.items() if count > avg_freq_f2],
                           key=lambda x: field2_counts[x], reverse=True)[:8]
            
            # Холодные числа (давно не выпадали или выпадают редко)
            all_f1_nums = list(range(1, config['field1_max'] + 1))
            all_f2_nums = list(range(1, config['field2_max'] + 1))
            
            cold_f1 = sorted([num for num in all_f1_nums if field1_counts.get(num, 0) < avg_freq_f1],
                           key=lambda x: field1_counts.get(x, 0))[:6]
            cold_f2 = sorted([num for num in all_f2_nums if field2_counts.get(num, 0) < avg_freq_f2],
                           key=lambda x: field2_counts.get(x, 0))[:4]
            
            # Генерируем рекомендации
            recommendations = []
            if hot_f1:
                recommendations.append(f"Рассмотрите горячие числа поля 1: {', '.join(map(str, hot_f1[:3]))}")
            if hot_f2:
                recommendations.append(f"Рассмотрите горячие числа поля 2: {', '.join(map(str, hot_f2[:2]))}")
            if cold_f1:
                recommendations.append(f"Холодные числа поля 1 могут быть готовы к выходу: {', '.join(map(str, cold_f1[:2]))}")
            
            summary = f"Проанализировано {analyzed_draws} тиражей. "
            if hot_f1 and hot_f2:
                summary += f"Активные тренды: поле 1 - число {hot_f1[0]}, поле 2 - число {hot_f2[0]}."
            else:
                summary += "Стабильная картина распределения чисел."
            
            return {
                'lottery_type': lottery_type,
                'trends': {
                    'field1': {
                        'hot_acceleration': hot_f1,
                        'cold_reversal': cold_f1
                    },
                    'field2': {
                        'hot_acceleration': hot_f2,
                        'cold_reversal': cold_f2
                    }
                },
                'analyzed_draws': analyzed_draws,
                'timestamp': datetime.utcnow().isoformat(),
                'summary': summary,
                'recommendations': recommendations
            }
    
    def update_model_statistics(self, lottery_type: str, model_type: str, 
                              accuracy: float, best_score: float, 
                              predictions_count: int, correct_predictions: int):
        """Обновление статистики модели"""
        today = datetime.utcnow().date()
        period_start = datetime.combine(today, datetime.min.time())
        period_end = datetime.combine(today, datetime.max.time())
        
        # Ищем существующую запись за сегодня
        existing = self.db.query(ModelStatistics).filter(
            ModelStatistics.lottery_type == lottery_type,
            ModelStatistics.model_type == model_type,
            ModelStatistics.date_period == 'daily',
            ModelStatistics.period_start == period_start
        ).first()
        
        if existing:
            existing.accuracy_percentage = accuracy
            existing.best_score = best_score
            existing.predictions_count = predictions_count
            existing.correct_predictions = correct_predictions
            existing.updated_at = datetime.utcnow()
        else:
            stat = ModelStatistics(
                lottery_type=lottery_type,
                model_type=model_type,
                accuracy_percentage=accuracy,
                best_score=best_score,
                predictions_count=predictions_count,
                correct_predictions=correct_predictions,
                date_period='daily',
                period_start=period_start,
                period_end=period_end,
                created_at=datetime.utcnow()
            )
            self.db.add(stat)
        
        self.db.commit()


@router.get("/stats", summary="Статистика дашборда")
async def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_optional)
):
    """Получение основной статистики для дашборда"""
    try:
        dashboard_service = DashboardService(db)
        user_id = current_user.id if current_user else None
        
        stats = dashboard_service.get_dashboard_stats(user_id)
        return stats
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения статистики: {str(e)}")

@router.get("/stats", response_model=DashboardStats, summary="Статистика дашборда")
def get_dashboard_stats_endpoint(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_optional)
):
    service = DashboardService(db)
    user_id = current_user.id if current_user else None
    return service.get_dashboard_stats(user_id)


@router.get("/{lottery_type}/trends", summary="Анализ трендов лотереи")
async def get_lottery_trends(
    lottery_type: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_optional),
    request: Request = None
):
    """Получение анализа трендов для конкретной лотереи"""
    if lottery_type not in data_manager.LOTTERY_CONFIGS:
        raise HTTPException(status_code=404, detail="Неизвестный тип лотереи")

    try:
        dashboard_service = DashboardService(db)

        # ДОБАВЛЕНО: ВСЕГДА логируем запрос трендов
        user_id = current_user.id if current_user else None
        dashboard_service.log_activity(
            'trends',
            f'Запросил анализ трендов для {lottery_type}',
            user_id=user_id,
            lottery_type=lottery_type,
            request=request
        )

        trends = dashboard_service.get_trends_analysis(lottery_type)
        return trends

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка анализа трендов: {str(e)}")


@router.get("/{lottery_type}/latest-draw", summary="Последний тираж лотереи")
async def get_latest_draw_detailed(
    lottery_type: str,
    db: Session = Depends(get_db)
):
    """Получение подробной информации о последнем тираже"""
    if lottery_type not in data_manager.LOTTERY_CONFIGS:
        raise HTTPException(status_code=404, detail="Неизвестный тип лотереи")

    try:
        # Сначала пробуем получить с правильным lottery_type
        latest_draw = db.query(LotteryDraw).filter(
            LotteryDraw.lottery_type == lottery_type
        ).order_by(
            LotteryDraw.draw_number.desc()
        ).first()

        # Если не нашли, проверяем есть ли записи с пустым lottery_type
        if not latest_draw:
            # Проверяем есть ли вообще записи в БД
            any_draw = db.query(LotteryDraw).first()

            if any_draw:
                # Если есть записи, но lottery_type пустой или неправильный
                # Автоматически исправляем для текущей лотереи
                empty_count = db.query(LotteryDraw).filter(
                    or_(
                        LotteryDraw.lottery_type == None,
                        LotteryDraw.lottery_type == '',
                        LotteryDraw.lottery_type != '4x20',
                        LotteryDraw.lottery_type != '5x36plus'
                    )
                ).count()

                if empty_count > 0:
                    # Исправляем на 4x20 (так как это основная лотерея)
                    db.query(LotteryDraw).filter(
                        or_(
                            LotteryDraw.lottery_type == None,
                            LotteryDraw.lottery_type == '',
                            ~LotteryDraw.lottery_type.in_(['4x20', '5x36plus'])
                        )
                    ).update(
                        {LotteryDraw.lottery_type: '4x20'},
                        synchronize_session=False
                    )
                    db.commit()

                    # Пробуем снова получить
                    latest_draw = db.query(LotteryDraw).filter(
                        LotteryDraw.lottery_type == lottery_type
                    ).order_by(
                        LotteryDraw.draw_number.desc()
                    ).first()

        if not latest_draw:
            return {
                "draw_number": 0,
                "draw_date": datetime.utcnow().isoformat(),
                "field1_numbers": [],
                "field2_numbers": [],
                "lottery_type": lottery_type,
                "status": "no_data"
            }

        # Форматируем дату правильно
        draw_date = latest_draw.draw_date
        if isinstance(draw_date, datetime):
            draw_date_str = draw_date.isoformat()
        elif isinstance(draw_date, str):
            draw_date_str = draw_date
        else:
            draw_date_str = str(draw_date)

        return {
            "draw_number": int(latest_draw.draw_number),
            "draw_date": draw_date_str,
            "field1_numbers": sorted(list(latest_draw.field1_numbers)) if latest_draw.field1_numbers else [],
            "field2_numbers": sorted(list(latest_draw.field2_numbers)) if latest_draw.field2_numbers else [],
            "lottery_type": lottery_type,
            "status": "ok"
        }

    except Exception as e:
        print(f"Ошибка получения последнего тиража для {lottery_type}: {e}")
        import traceback
        traceback.print_exc()

        return {
            "draw_number": 0,
            "draw_date": datetime.utcnow().isoformat(),
            "field1_numbers": [],
            "field2_numbers": [],
            "lottery_type": lottery_type,
            "status": "error",
            "error_message": str(e)
        }


@router.get("/database-status", summary="Статус базы данных")
async def get_database_status():
    """Получение статуса базы данных и количества тиражей"""
    try:
        from backend.app.core.database_monitor import get_database_stats

        stats = get_database_stats()

        return {
            "status": "online",
            "total_draws": stats.get('total_draws', 0),
            "lotteries": stats.get('lotteries', {}),
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@router.get("/debug/database-check", summary="🔍 Диагностика БД")
async def debug_database_check(db: Session = Depends(get_db)):
    """Проверка содержимого таблицы lottery_draws"""
    try:
        # Проверяем общее количество записей
        total_count = db.query(LotteryDraw).count()

        # Проверяем записи по типам лотерей
        lottery_stats = {}
        for lottery_type in ['4x20', '5x36plus', None, '']:
            count = db.query(LotteryDraw).filter(
                LotteryDraw.lottery_type == lottery_type
            ).count()
            if count > 0:
                lottery_stats[f"lottery_type='{lottery_type}'"] = count

        # Получаем первые 5 записей для анализа
        sample_records = db.query(LotteryDraw).limit(5).all()
        sample_data = []
        for record in sample_records:
            sample_data.append({
                'id': record.id,
                'lottery_type': record.lottery_type,
                'draw_number': record.draw_number,
                'draw_date': str(record.draw_date)
            })

        # Проверяем уникальные значения lottery_type
        unique_types = db.execute(
            text("SELECT DISTINCT lottery_type FROM lottery_draws")
        ).fetchall()

        return {
            'total_records': total_count,
            'by_lottery_type': lottery_stats,
            'unique_lottery_types': [t[0] for t in unique_types],
            'sample_records': sample_data,
            'problem': 'lottery_type field is empty or has wrong values' if '4x20' not in lottery_stats else None
        }

    except Exception as e:
        return {'error': str(e)}


@router.post("/fix/lottery-types", summary="🔧 Исправить типы лотерей в БД")
async def fix_lottery_types(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_optional)
):
    """Исправляет пустые или неправильные типы лотерей в БД"""
    try:
        # Сначала проверяем, есть ли записи с пустым lottery_type
        empty_type_count = db.query(LotteryDraw).filter(
            or_(
                LotteryDraw.lottery_type == None,
                LotteryDraw.lottery_type == '',
                LotteryDraw.lottery_type == 'null'
            )
        ).count()

        if empty_type_count > 0:
            # Обновляем все записи с пустым lottery_type на '4x20'
            # (так как у вас загружена БД именно для 4x20)
            updated = db.query(LotteryDraw).filter(
                or_(
                    LotteryDraw.lottery_type == None,
                    LotteryDraw.lottery_type == '',
                    LotteryDraw.lottery_type == 'null'
                )
            ).update(
                {LotteryDraw.lottery_type: '4x20'},
                synchronize_session=False
            )

            db.commit()

            return {
                'success': True,
                'message': f'Исправлено {updated} записей',
                'updated_count': updated,
                'lottery_type_set_to': '4x20'
            }
        else:
            return {
                'success': True,
                'message': 'Все записи уже имеют корректный lottery_type',
                'updated_count': 0
            }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка исправления: {str(e)}")

@router.post("/activity", summary="Логирование активности")
async def log_user_activity(
    activity_type: str,
    description: str,
    lottery_type: str = None,
    details: Dict[str, Any] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_optional),
    request: Request = None
):
    """Ручное логирование активности пользователя"""
    try:
        dashboard_service = DashboardService(db)
        user_id = current_user.id if current_user else None
        
        activity = dashboard_service.log_activity(
            activity_type, description, user_id, lottery_type, details, request
        )
        
        return {
            "success": True,
            "activity_id": activity.id,
            "message": "Активность зарегистрирована"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка логирования активности: {str(e)}")


@router.post("/model-stats", summary="Обновление статистики модели")
async def update_model_statistics(
    lottery_type: str,
    model_type: str,
    accuracy: float,
    best_score: float,
    predictions_count: int = 0,
    correct_predictions: int = 0,
    db: Session = Depends(get_db)
):
    """Обновление статистики работы ML модели"""
    if lottery_type not in data_manager.LOTTERY_CONFIGS:
        raise HTTPException(status_code=404, detail="Неизвестный тип лотереи")
    
    if model_type not in ['rf', 'lstm']:
        raise HTTPException(status_code=400, detail="Неизвестный тип модели")
    
    try:
        dashboard_service = DashboardService(db)
        dashboard_service.update_model_statistics(
            lottery_type, model_type, accuracy, best_score, 
            predictions_count, correct_predictions
        )
        
        return {
            "success": True,
            "message": f"Статистика модели {model_type} для {lottery_type} обновлена"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка обновления статистики: {str(e)}")


# Middleware для автоматического логирования активности генерации
@router.post("/seed-data", summary="Создать тестовые данные")
async def create_seed_data(db: Session = Depends(get_db)):
    """Создание тестовых данных для дашборда"""
    try:
        dashboard_service = DashboardService(db)
        
        # Создаем несколько тестовых активностей
        activities = [
            ("generation", "Создано 5 комбинаций методом multi_strategy", "4x20"),
            ("analysis", "Выполнен анализ трендов для 4x20", "4x20"),
            ("generation", "Создано 3 комбинации методом rf_ranked", "5x36plus"),
            ("trends", "Запросил анализ трендов для 5x36plus", "5x36plus"),
            ("generation", "Создано 8 комбинаций методом hot", "4x20"),
        ]
        
        for activity_type, description, lottery_type in activities:
            dashboard_service.log_activity(activity_type, description, None, lottery_type)
        
        # Создаем статистику моделей
        dashboard_service.update_model_statistics(
            '4x20', 'rf', 75.5, 0.845, 25, 19
        )
        dashboard_service.update_model_statistics(
            '5x36plus', 'rf', 68.2, 0.752, 18, 12
        )
        
        return {
            "success": True,
            "message": "Тестовые данные созданы успешно"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка создания тестовых данных: {str(e)}")


def log_generation_activity(db: Session, user_id: Optional[int], lottery_type: str, 
                          combination_count: int, method: str):
    """Автоматическое логирование генерации комбинаций"""
    dashboard_service = DashboardService(db)
    description = f"Сгенерировано {combination_count} комбинаций методом {method}"
    dashboard_service.log_activity(
        'generation', 
        description,
        user_id=user_id,
        lottery_type=lottery_type,
        details={'method': method, 'count': combination_count}
    )