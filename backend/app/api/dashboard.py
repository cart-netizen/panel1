from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, text
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import pandas as pd

from backend.app.core.database import get_db, UserActivity, ModelStatistics, DashboardCache, LotteryDraw
from backend.app.core import data_manager
from backend.app.core.lottery_context import LotteryContext
from backend.app.models.schemas import DashboardStats, ActivityItem, TrendAnalysis
from backend.app.core.subscription_protection import get_current_user_optional_sync as get_current_user_optional

router = APIRouter()


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
    
    def get_dashboard_stats(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """Получение статистики для дашборда"""
        today = datetime.utcnow().date()
        start_of_day = datetime.combine(today, datetime.min.time())
        
        # Генерации сегодня
        generations_today = self.db.query(UserActivity).filter(
            UserActivity.activity_type == 'generation',
            UserActivity.created_at >= start_of_day,
            UserActivity.user_id == user_id if user_id else True
        ).count()
        
        # Анализы трендов сегодня
        trend_analyses = self.db.query(UserActivity).filter(
            UserActivity.activity_type.in_(['analysis', 'trends']),
            UserActivity.created_at >= start_of_day,
            UserActivity.user_id == user_id if user_id else True
        ).count()
        
        # Общее количество генераций
        total_generations = self.db.query(UserActivity).filter(
            UserActivity.activity_type == 'generation',
            UserActivity.user_id == user_id if user_id else True
        ).count()
        
        # Точность прогнозов (среднее по всем моделям за последние 30 дней)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        accuracy_stats = self.db.query(func.avg(ModelStatistics.accuracy_percentage)).filter(
            ModelStatistics.period_start >= thirty_days_ago
        ).scalar()
        
        # Лучшая оценка RF
        best_score_stat = self.db.query(func.max(ModelStatistics.best_score)).filter(
            ModelStatistics.model_type == 'rf'
        ).scalar()
        
        # Недавняя активность (последние 10 записей)
        recent_activities_query = self.db.query(UserActivity).filter(
            UserActivity.user_id == user_id if user_id else True
        ).order_by(desc(UserActivity.created_at)).limit(10)
        
        recent_activities = []
        for activity in recent_activities_query:
            recent_activities.append({
                'type': activity.activity_type,
                'description': activity.activity_description,
                'timestamp': activity.created_at.isoformat(),
                'lottery_type': activity.lottery_type
            })
        
        return {
            'generations_today': generations_today,
            'trend_analyses': trend_analyses,
            'accuracy_percentage': round(accuracy_stats or 0, 1),
            'best_score': round(best_score_stat or 0, 3) if best_score_stat else 'N/A',
            'total_generations': total_generations,
            'recent_activities': recent_activities
        }
    
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


@router.get("/{lottery_type}/trends", summary="Анализ трендов лотереи")
async def get_lottery_trends(
    lottery_type: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_optional),
    request: Request = None
):
    """Получение анализа трендов для конкретной лотереи"""
    if lottery_type not in data_manager.LOTTERY_CONFIGS:
        raise HTTPException(status_code=404, detail="Неизвестный тип лотереи")
    
    try:
        dashboard_service = DashboardService(db)
        
        # Логируем активность
        if current_user:
            dashboard_service.log_activity(
                'trends', 
                f'Запросил анализ трендов для {lottery_type}',
                user_id=current_user.id,
                lottery_type=lottery_type,
                request=request
            )
        
        trends = dashboard_service.get_trends_analysis(lottery_type)
        return trends
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка анализа трендов: {str(e)}")


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