"""
API эндпоинты для XGBoost моделей и интерпретируемости
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from backend.app.core import data_manager
from backend.app.core.xgboost_model import GLOBAL_XGBOOST_MANAGER  
from backend.app.core.lottery_context import LotteryContext
from backend.app.core.subscription_protection import require_basic, require_premium
from backend.app.models.schemas import GenerationResponse, Combination
from backend.app.api.analysis import set_lottery_context
from backend.app.api.auth import get_current_user

router = APIRouter(prefix="/xgboost", tags=["XGBoost Analysis"])
logger = logging.getLogger(__name__)


@router.post("/generate", response_model=GenerationResponse, summary="🚀 XGBoost генерация")
async def generate_xgboost_combinations(
    num_combinations: int = Query(5, ge=1, le=20, description="Количество комбинаций"),
    num_candidates: int = Query(100, ge=50, le=500, description="Количество кандидатов для оценки"),
    context: None = Depends(set_lottery_context),
    current_user = Depends(require_basic)
):
    """
    🔒 ПРЕМИУМ ФУНКЦИЯ: Генерация комбинаций с XGBoost ранжированием
    
    **Преимущества XGBoost:**
    - Выше точность чем Random Forest
    - Быстрее обучение и предсказание
    - SHAP интерпретируемость
    - Автоматический отбор признаков
    
    **Требования:** Базовая подписка или выше
    """
    try:
        # Загружаем историю
        df_history = data_manager.fetch_draws_from_db()
        
        if df_history.empty:
            raise HTTPException(status_code=404, detail="Нет исторических данных")
        
        # Импортируем функцию генерации
        from backend.app.core.combination_generator import generate_xgboost_ranked_combinations, generate_xgboost_prediction
        
        # Генерируем комбинации
        generated = generate_xgboost_ranked_combinations(
            df_history, 
            num_combinations,
            num_candidates
        )
        
        # Форматируем ответ
        combinations = [
            Combination(field1=f1, field2=f2, description=desc)
            for f1, f2, desc in generated
        ]
        
        # Получаем чистое предсказание XGBoost
        xgb_f1, xgb_f2 = generate_xgboost_prediction(df_history)
        xgb_prediction = None
        if xgb_f1 and xgb_f2:
            xgb_prediction = Combination(
                field1=xgb_f1,
                field2=xgb_f2, 
                description="XGBoost ML Prediction"
            )
        
        # Логируем активность
        try:
            from backend.app.core.database import get_db
            from backend.app.api.dashboard import DashboardService
            
            db = next(get_db())
            dashboard_service = DashboardService(db)
            
            dashboard_service.log_activity(
                activity_type='xgboost_generation',
                description=f'XGBoost генерация {num_combinations} комбинаций',
                user_id=current_user.id if current_user else None,
                lottery_type=data_manager.CURRENT_LOTTERY,
                details={
                    'num_combinations': num_combinations,
                    'num_candidates': num_candidates,
                    'method': 'xgboost_ranked'
                }
            )
        except Exception as e:
            logger.warning(f"Ошибка логирования: {e}")
        
        return GenerationResponse(
            combinations=combinations,
            rf_prediction=xgb_prediction,  # Используем rf_prediction для совместимости
            lstm_prediction=None
        )
        
    except Exception as e:
        logger.error(f"Ошибка XGBoost генерации: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/explain", summary="🔍 SHAP объяснение комбинации")
async def explain_combination(
    field1: List[int] = Query(..., description="Числа первого поля"),
    field2: List[int] = Query(..., description="Числа второго поля"),
    context: None = Depends(set_lottery_context),
    current_user = Depends(require_premium)
):
    """
    🔒 ПРЕМИУМ ФУНКЦИЯ: Получить SHAP объяснение для комбинации
    
    **Что вы получите:**
    - Важность каждого признака для предсказания
    - Влияние исторических паттернов
    - Обоснование оценки комбинации
    - Визуализация факторов решения
    
    **Требования:** Премиум подписка или выше
    """
    try:
        # Валидация
        config = data_manager.get_current_config()
        if (len(field1) != config['field1_size'] or 
            len(field2) != config['field2_size']):
            raise HTTPException(
                status_code=400,
                detail=f"Неверное количество чисел. Ожидается {config['field1_size']}+{config['field2_size']}"
            )
        
        # Загружаем данные
        df_history = data_manager.fetch_draws_from_db()
        
        if df_history.empty or len(df_history) < 50:
            raise HTTPException(
                status_code=404, 
                detail="Недостаточно данных для анализа"
            )
        
        # Получаем модель
        xgb_model = GLOBAL_XGBOOST_MANAGER.get_model(
            data_manager.CURRENT_LOTTERY,
            config
        )
        
        # Обучаем если необходимо
        if not xgb_model.is_trained:
            logger.info("Обучение XGBoost для объяснений...")
            success = xgb_model.train(df_history)
            if not success:
                raise HTTPException(
                    status_code=500,
                    detail="Не удалось обучить модель"
                )
        
        # Получаем SHAP объяснения
        shap_data = xgb_model.get_shap_explanation(field1, field2, df_history)
        
        if 'error' in shap_data:
            raise HTTPException(
                status_code=500,
                detail=f"Ошибка SHAP: {shap_data['error']}"
            )
        
        # Форматируем ответ
        response = {
            'combination': {
                'field1': field1,
                'field2': field2
            },
            'score': shap_data.get('prediction_score', 0),
            'explanations': {
                'field1': shap_data.get('field1_explanations', []),
                'field2': shap_data.get('field2_explanations', [])
            },
            'top_factors': shap_data.get('top_important_features', []),
            'interpretation': _generate_interpretation(shap_data),
            'timestamp': datetime.now().isoformat()
        }
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка SHAP объяснения: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/feature-importance", summary="📊 Важность признаков")
async def get_feature_importance(
    field_type: str = Query('field1', regex='^(field1|field2)$'),
    number: int = Query(1, ge=1, le=36),
    context: None = Depends(set_lottery_context),
    current_user = Depends(require_basic)
):
    """
    🔒 ЗАЩИЩЕННАЯ ФУНКЦИЯ: Получить важность признаков для конкретного числа
    
    **Параметры:**
    - field_type: 'field1' или 'field2'
    - number: Номер числа для анализа (1-20 или 1-36)
    
    **Возвращает:**
    - Топ-20 самых важных признаков
    - Их относительную важность
    """
    try:
        config = data_manager.get_current_config()
        
        # Валидация номера
        max_num = config['field1_max'] if field_type == 'field1' else config['field2_max']
        if number > max_num:
            raise HTTPException(
                status_code=400,
                detail=f"Номер {number} вне диапазона для {field_type} (max: {max_num})"
            )
        
        # Получаем модель
        xgb_model = GLOBAL_XGBOOST_MANAGER.get_model(
            data_manager.CURRENT_LOTTERY,
            config
        )
        
        if not xgb_model.is_trained:
            # Обучаем модель
            df_history = data_manager.fetch_draws_from_db()
            if df_history.empty or len(df_history) < 50:
                raise HTTPException(
                    status_code=404,
                    detail="Недостаточно данных для обучения"
                )
            
            success = xgb_model.train(df_history)
            if not success:
                raise HTTPException(
                    status_code=500,
                    detail="Не удалось обучить модель"
                )
        
        # Получаем важность признаков
        importance = xgb_model.get_feature_importance(field_type, number)
        
        if not importance:
            raise HTTPException(
                status_code=404,
                detail=f"Нет данных важности для {field_type} число {number}"
            )
        
        # Берем топ-20
        top_features = list(importance.items())[:20]
        
        # Нормализуем важность (0-100)
        max_importance = max(importance.values()) if importance else 1
        normalized_features = [
            {
                'name': name,
                'importance': (value / max_importance) * 100,
                'raw_value': value,
                'description': _describe_feature(name)
            }
            for name, value in top_features
        ]
        
        return {
            'field_type': field_type,
            'number': number,
            'top_features': normalized_features,
            'total_features': len(importance),
            'lottery_type': data_manager.CURRENT_LOTTERY
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка получения важности признаков: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics", summary="📈 Метрики XGBoost моделей")
async def get_xgboost_metrics(
    current_user = Depends(require_basic)
):
    """
    🔒 ЗАЩИЩЕННАЯ ФУНКЦИЯ: Получить метрики производительности XGBoost
    
    **Возвращает:**
    - ROC-AUC оценки
    - Время обучения
    - Статистику кэша
    - Количество предсказаний
    """
    try:
        all_metrics = GLOBAL_XGBOOST_MANAGER.get_all_metrics()
        
        # Форматируем ответ
        response = {}
        for lottery_type, metrics in all_metrics.items():
            avg_roc_auc = 0
            if metrics.get('roc_auc'):
                avg_roc_auc = sum(metrics['roc_auc']) / len(metrics['roc_auc'])

            response[lottery_type] = {
                'average_roc_auc': float(round(avg_roc_auc, 3)),
                'training_time_seconds': float(round(metrics.get('training_time', 0), 2)),
                'total_predictions': int(metrics.get('total_predictions', 0)),
                'cache_hit_rate': float(round(metrics.get('cache_hit_rate', 0), 1)),
                'feature_count': len(metrics.get('feature_importance', {})),
                'top_features': list(metrics.get('feature_importance', {}).keys())[:5]
            }
        
        return {
            'models': response,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Ошибка получения метрик: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/train", summary="🎓 Принудительное обучение XGBoost")
async def train_xgboost_model(
    force: bool = Query(False, description="Переобучить даже если модель уже обучена"),
    context: None = Depends(set_lottery_context),
    current_user = Depends(require_premium)
):
    """
    🔒 ПРЕМИУМ ФУНКЦИЯ: Принудительное переобучение XGBoost модели
    
    **Использовать когда:**
    - Добавлено много новых данных
    - Хотите улучшить точность
    - Изменились паттерны в данных
    
    **Требования:** Премиум подписка или выше
    """
    try:
        config = data_manager.get_current_config()
        xgb_model = GLOBAL_XGBOOST_MANAGER.get_model(
            data_manager.CURRENT_LOTTERY,
            config
        )
        
        # Проверяем нужно ли обучение
        if xgb_model.is_trained and not force:
            return {
                'status': 'already_trained',
                'message': 'Модель уже обучена. Используйте force=true для переобучения',
                'metrics': xgb_model.get_metrics()
            }
        
        # Загружаем данные
        df_history = data_manager.fetch_draws_from_db()
        
        if df_history.empty or len(df_history) < 50:
            raise HTTPException(
                status_code=404,
                detail=f"Недостаточно данных: {len(df_history)} тиражей (минимум 50)"
            )
        
        # Обучаем модель
        logger.info(f"Запуск обучения XGBoost для {data_manager.CURRENT_LOTTERY}...")
        success = xgb_model.train(df_history)
        
        if not success:
            raise HTTPException(
                status_code=500,
                detail="Обучение не удалось. Проверьте логи"
            )
        
        # Получаем метрики после обучения
        metrics = xgb_model.get_metrics()
        avg_roc_auc = 0
        safe_metrics = {}

        if metrics.get('roc_auc'):
            avg_roc_auc = sum(metrics['roc_auc']) / len(metrics['roc_auc'])

        for key, value in metrics.items():
            if isinstance(value, list):
                safe_metrics[key] = [float(v) if hasattr(v, 'item') else v for v in value]
            elif hasattr(value, 'item'):  # numpy scalar
                safe_metrics[key] = float(value)
            else:
                safe_metrics[key] = value

        print(f"training_time: {round(metrics.get('training_time', 0), 2)}")
        print(f"average_roc_auc: {round(avg_roc_auc, 3)}")
        print(f"lottery_type: {len(metrics.get('roc_auc', []))}")
        return {
            'status': 'success',
            'message': f'Модель успешно обучена на {len(df_history)} тиражах',
            # 'training_time': round(metrics.get('training_time', 0), 2),
            # 'average_roc_auc': round(avg_roc_auc, 3),
            # 'models_trained': len(metrics.get('roc_auc', [])),
            'lottery_type': data_manager.CURRENT_LOTTERY,
            'metrics': safe_metrics
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка обучения XGBoost: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _describe_feature(feature_name: str) -> str:
    """Человекочитаемое описание признака"""
    descriptions = {
        'freq_f1': 'Частота числа в поле 1',
        'freq_f2': 'Частота числа в поле 2',
        'win': 'в окне',
        'mean': 'Среднее значение',
        'std': 'Стандартное отклонение',
        'median': 'Медиана',
        'diversity': 'Разнообразие чисел',
        'last_appear': 'Тиражей с последнего появления',
        'sin_year': 'Годовая цикличность (sin)',
        'cos_year': 'Годовая цикличность (cos)',
        'sin_month': 'Месячная цикличность (sin)',
        'cos_month': 'Месячная цикличность (cos)',
        'sin_week': 'Недельная цикличность (sin)',
        'cos_week': 'Недельная цикличность (cos)'
    }
    
    for key, desc in descriptions.items():
        if key in feature_name:
            return desc
    
    return feature_name


def _generate_interpretation(shap_data: Dict[str, Any]) -> str:
    """Генерация текстовой интерпретации SHAP данных"""
    score = shap_data.get('prediction_score', 50)
    top_features = shap_data.get('top_important_features', [])
    
    interpretation = []
    
    # Оценка качества
    if score >= 70:
        interpretation.append("🟢 Отличная комбинация с высокой вероятностью успеха.")
    elif score >= 55:
        interpretation.append("🟡 Хорошая комбинация с умеренными шансами.")
    else:
        interpretation.append("🔴 Слабая комбинация, рекомендуется пересмотреть выбор.")
    
    # Анализ топ факторов
    if top_features:
        positive_factors = [f for f in top_features if f.get('shap_value', 0) > 0]
        negative_factors = [f for f in top_features if f.get('shap_value', 0) < 0]
        
        if positive_factors:
            factor = positive_factors[0]
            interpretation.append(
                f"Положительный фактор: {_describe_feature(factor['name'])} "
                f"(влияние: +{abs(factor['shap_value']):.3f})"
            )
        
        if negative_factors:
            factor = negative_factors[0]
            interpretation.append(
                f"Отрицательный фактор: {_describe_feature(factor['name'])} "
                f"(влияние: {factor['shap_value']:.3f})"
            )
    
    return " ".join(interpretation)
