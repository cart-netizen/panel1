"""
API эндпоинты для walk-forward валидации моделей
"""
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
import asyncio

from backend.app.core import data_manager
from backend.app.core.validation.walk_forward import WalkForwardValidator, ValidationResults
from backend.app.core.xgboost_model import XGBoostLotteryModel
from backend.app.core.ai_model import RFModel, LotteryLSTMOps
from backend.app.core.lottery_context import LotteryContext
from backend.app.core.subscription_protection import require_premium
from backend.app.api.analysis import set_lottery_context
from backend.app.api.auth import get_current_user
from backend.app.core.database import get_db, SessionLocal
from backend.app.api.dashboard import DashboardService

router = APIRouter(prefix="/validation", tags=["Model Validation"])
logger = logging.getLogger(__name__)

# Хранилище результатов валидации (в продакшене использовать БД)
validation_cache = {}


@router.post("/walk-forward", summary="🔬 Walk-forward валидация модели")
async def run_walk_forward_validation(
    model_type: str = Query(..., regex="^(xgboost|rf|lstm)$", description="Тип модели"),
    initial_train_size: int = Query(300, ge=100, le=1000, description="Начальный размер обучающей выборки"),
    test_size: int = Query(30, ge=10, le=100, description="Размер тестового окна"),
    step_size: int = Query(30, ge=10, le=100, description="Шаг сдвига окна"),
    expanding_window: bool = Query(True, description="Расширяющееся окно (True) или скользящее (False)"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    context: None = Depends(set_lottery_context),
    current_user = Depends(require_premium)
):
    """
    🔒 ПРЕМИУМ ФУНКЦИЯ: Walk-forward валидация для реалистичной оценки модели
    
    **Что это даёт:**
    - Предотвращает переобучение и lookahead bias
    - Реалистичная оценка производительности на будущих данных
    - Сравнение стабильности модели во времени
    - Выявление деградации модели
    
    **Параметры:**
    - model_type: Какую модель валидировать (xgboost, rf, lstm)
    - initial_train_size: Начальный размер обучающей выборки
    - test_size: Размер каждого тестового окна
    - step_size: На сколько сдвигать окно
    - expanding_window: Расширять окно обучения или сдвигать
    
    **Требования:** Премиум подписка
    """
    try:
        # Загружаем данные
        df_history = data_manager.fetch_draws_from_db()
        
        if df_history.empty or len(df_history) < initial_train_size + test_size:
            raise HTTPException(
                status_code=404,
                detail=f"Недостаточно данных: {len(df_history)} тиражей "
                      f"(минимум {initial_train_size + test_size})"
            )
        
        config = data_manager.get_current_config()
        
        # Создаем валидатор
        validator = WalkForwardValidator(
            initial_train_size=initial_train_size,
            test_size=test_size,
            step_size=step_size,
            expanding_window=expanding_window
        )
        
        # Выбираем модель
        if model_type == 'xgboost':
            from backend.app.core.xgboost_model import XGBoostLotteryModel
            model_class = XGBoostLotteryModel
            model_params = {}
        elif model_type == 'rf':
            model_class = RFModel
            model_params = {'n_estimators': 100}
        else:  # lstm
            model_class = LotteryLSTMOps
            model_params = {'n_steps_in': 5}
        
        # Генерируем уникальный ID для задачи
        task_id = f"{model_type}_{data_manager.CURRENT_LOTTERY}_{datetime.now().timestamp()}"
        
        # Запускаем валидацию в фоне
        background_tasks.add_task(
            run_validation_background,
            task_id, validator, model_class, model_params,
            df_history, config, current_user.id
        )
        
        return {
            'task_id': task_id,
            'status': 'started',
            'message': f'Валидация {model_type} запущена в фоновом режиме',
            'estimated_time': estimate_validation_time(len(df_history), initial_train_size, test_size, step_size),
            'check_status_url': f'/api/v1/{data_manager.CURRENT_LOTTERY}/validation/status/{task_id}'
        }
        
    except Exception as e:
        logger.error(f"Ошибка запуска валидации: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{task_id}", summary="📊 Статус валидации")
async def get_validation_status(
    task_id: str,
    context: None = Depends(set_lottery_context),
    current_user = Depends(get_current_user)
):
    """
    Получить статус и результаты валидации
    
    **Возвращает:**
    - Статус выполнения (running, completed, error)
    - Результаты валидации если завершено
    - Промежуточные метрики если выполняется
    """
    if task_id not in validation_cache:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    
    task_data = validation_cache[task_id]
    
    if task_data['status'] == 'completed':
        # Возвращаем полные результаты
        results = task_data['results']
        return {
            'task_id': task_id,
            'status': 'completed',
            'summary': results.get_summary(),
            'average_metrics': results.average_metrics,
            'std_metrics': results.std_metrics,
            'window_count': results.total_windows,
            'best_window': results.best_window,
            'worst_window': results.worst_window,
            'total_time': results.total_time,
            'window_details': [m.to_dict() for m in results.window_metrics[:10]]  # Первые 10 окон
        }
    elif task_data['status'] == 'error':
        return {
            'task_id': task_id,
            'status': 'error',
            'error': task_data.get('error', 'Unknown error')
        }
    else:
        return {
            'task_id': task_id,
            'status': 'running',
            'progress': task_data.get('progress', 0),
            'message': task_data.get('message', 'Валидация выполняется...')
        }


@router.post("/compare", summary="⚔️ Сравнение моделей")
async def compare_models_validation(
    models: List[str] = Query(['xgboost', 'rf'], description="Модели для сравнения"),
    initial_train_size: int = Query(200, ge=100, le=500),
    test_size: int = Query(20, ge=10, le=50),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    context: None = Depends(set_lottery_context),
    current_user = Depends(require_premium)
):
    """
    🔒 ПРЕМИУМ ФУНКЦИЯ: Сравнение нескольких моделей через walk-forward валидацию
    
    **Что вы получите:**
    - Объективное сравнение моделей на одинаковых данных
    - Выявление лучшей модели для вашей лотереи
    - Анализ стабильности каждой модели
    
    **Требования:** Премиум подписка
    """
    try:
        # Проверяем модели
        valid_models = ['xgboost', 'rf', 'lstm']
        for model in models:
            if model not in valid_models:
                raise HTTPException(
                    status_code=400,
                    detail=f"Неверная модель: {model}. Доступны: {valid_models}"
                )
        
        # Загружаем данные
        df_history = data_manager.fetch_draws_from_db()
        
        if df_history.empty or len(df_history) < initial_train_size + test_size:
            raise HTTPException(
                status_code=404,
                detail=f"Недостаточно данных для сравнения"
            )
        
        config = data_manager.get_current_config()
        
        # Генерируем ID задачи
        task_id = f"compare_{data_manager.CURRENT_LOTTERY}_{datetime.now().timestamp()}"
        
        # Запускаем сравнение в фоне
        background_tasks.add_task(
            run_comparison_background,
            task_id, models, initial_train_size, test_size,
            df_history, config, current_user.id
        )
        
        return {
            'task_id': task_id,
            'status': 'started',
            'models': models,
            'message': f'Сравнение {len(models)} моделей запущено',
            'check_status_url': f'/api/v1/{data_manager.CURRENT_LOTTERY}/validation/comparison/{task_id}'
        }
        
    except Exception as e:
        logger.error(f"Ошибка запуска сравнения: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/comparison/{task_id}", summary="📈 Результаты сравнения")
async def get_comparison_results(
    task_id: str,
    context: None = Depends(set_lottery_context),
    current_user = Depends(get_current_user)
):
    """
    Получить результаты сравнения моделей
    """
    if task_id not in validation_cache:
        raise HTTPException(status_code=404, detail="Сравнение не найдено")
    
    task_data = validation_cache[task_id]
    
    if task_data['status'] == 'completed':
        return {
            'task_id': task_id,
            'status': 'completed',
            'comparison': task_data['comparison'],
            'winner': task_data['winner'],
            'ranking': task_data['ranking']
        }
    elif task_data['status'] == 'error':
        return {
            'task_id': task_id,
            'status': 'error',
            'error': task_data.get('error')
        }
    else:
        return {
            'task_id': task_id,
            'status': 'running',
            'progress': task_data.get('progress', 0),
            'current_model': task_data.get('current_model')
        }


@router.get("/history", summary="📜 История валидаций")
async def get_validation_history(
    limit: int = Query(10, ge=1, le=50),
    context: None = Depends(set_lottery_context),
    current_user = Depends(get_current_user)
):
    """
    Получить историю выполненных валидаций
    """
    # Фильтруем по текущей лотерее и пользователю
    user_validations = [
        {
            'task_id': task_id,
            'status': data['status'],
            'model': data.get('model_type'),
            'started_at': data.get('started_at'),
            'completed_at': data.get('completed_at'),
            'summary': data['results'].get_summary() if data.get('results') else None
        }
        for task_id, data in validation_cache.items()
        if data.get('user_id') == current_user.id and 
           data.get('lottery_type') == data_manager.CURRENT_LOTTERY
    ]
    
    # Сортируем по времени
    user_validations.sort(key=lambda x: x.get('started_at', ''), reverse=True)
    
    return {
        'validations': user_validations[:limit],
        'total': len(user_validations)
    }


# Фоновые задачи

async def run_validation_background(task_id: str, validator: WalkForwardValidator,
                                   model_class: Any, model_params: Dict,
                                   df_history: pd.DataFrame, config: Dict,
                                   user_id: int):
    """Фоновая задача для выполнения валидации"""
    try:
        # Инициализируем запись в кэше
        validation_cache[task_id] = {
            'status': 'running',
            'progress': 0,
            'message': 'Инициализация валидации...',
            'started_at': datetime.now().isoformat(),
            'user_id': user_id,
            'lottery_type': data_manager.CURRENT_LOTTERY,
            'model_type': model_class.__name__
        }
        
        # Запускаем валидацию
        logger.info(f"🚀 Запуск фоновой валидации {task_id}")
        
        results = validator.validate_model(
            model_class, model_params,
            df_history, config
        )
        
        # Сохраняем результаты
        validation_cache[task_id] = {
            'status': 'completed',
            'results': results,
            'completed_at': datetime.now().isoformat(),
            'user_id': user_id,
            'lottery_type': data_manager.CURRENT_LOTTERY,
            'model_type': model_class.__name__
        }
        
        # Логируем в БД
        try:
            db = SessionLocal()
            dashboard_service = DashboardService(db)
            dashboard_service.log_activity(
                activity_type='validation_completed',
                description=f'Walk-forward валидация {model_class.__name__}: '
                          f'accuracy={results.average_metrics["accuracy"]:.3f}, '
                          f'f1={results.average_metrics["f1"]:.3f}',
                user_id=user_id,
                lottery_type=data_manager.CURRENT_LOTTERY,
                details={
                    'model': model_class.__name__,
                    'windows': results.total_windows,
                    'avg_accuracy': results.average_metrics['accuracy'],
                    'avg_f1': results.average_metrics['f1']
                }
            )
            db.close()
        except Exception as e:
            logger.warning(f"Ошибка логирования: {e}")
        
        logger.info(f"✅ Валидация {task_id} завершена успешно")
        
    except Exception as e:
        logger.error(f"❌ Ошибка валидации {task_id}: {e}")
        validation_cache[task_id] = {
            'status': 'error',
            'error': str(e),
            'user_id': user_id,
            'lottery_type': data_manager.CURRENT_LOTTERY
        }


async def run_comparison_background(task_id: str, models: List[str],
                                   initial_train_size: int, test_size: int,
                                   df_history: pd.DataFrame, config: Dict,
                                   user_id: int):
    """Фоновая задача для сравнения моделей"""
    try:
        validation_cache[task_id] = {
            'status': 'running',
            'progress': 0,
            'current_model': None,
            'started_at': datetime.now().isoformat(),
            'user_id': user_id,
            'lottery_type': data_manager.CURRENT_LOTTERY
        }
        
        validator = WalkForwardValidator(
            initial_train_size=initial_train_size,
            test_size=test_size,
            step_size=test_size,
            expanding_window=True
        )
        
        model_configs = []
        for model_name in models:
            if model_name == 'xgboost':
                from backend.app.core.xgboost_model import XGBoostLotteryModel
                model_configs.append((XGBoostLotteryModel, {}))
            elif model_name == 'rf':
                model_configs.append((RFModel, {'n_estimators': 100}))
            elif model_name == 'lstm':
                model_configs.append((LotteryLSTMOps, {'n_steps_in': 5}))
        
        # Запускаем сравнение
        comparison_df = validator.compare_models(model_configs, df_history, config)
        
        # Определяем победителя
        if 'avg_f1' in comparison_df.columns:
            winner_idx = comparison_df['avg_f1'].idxmax()
            winner = comparison_df.loc[winner_idx, 'model']
            ranking = comparison_df[['model', 'avg_accuracy', 'avg_f1']].to_dict('records')
        else:
            winner = 'Unknown'
            ranking = []
        
        validation_cache[task_id] = {
            'status': 'completed',
            'comparison': comparison_df.to_dict('records'),
            'winner': winner,
            'ranking': ranking,
            'completed_at': datetime.now().isoformat(),
            'user_id': user_id,
            'lottery_type': data_manager.CURRENT_LOTTERY
        }
        
        logger.info(f"✅ Сравнение {task_id} завершено. Победитель: {winner}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка сравнения {task_id}: {e}")
        validation_cache[task_id] = {
            'status': 'error',
            'error': str(e),
            'user_id': user_id,
            'lottery_type': data_manager.CURRENT_LOTTERY
        }


def estimate_validation_time(data_size: int, train_size: int, 
                            test_size: int, step_size: int) -> float:
    """Оценка времени выполнения валидации в секундах"""
    # Количество окон
    num_windows = (data_size - train_size - test_size) // step_size + 1
    # Примерное время на окно (секунды)
    time_per_window = 2.0  # Зависит от модели
    return num_windows * time_per_window
