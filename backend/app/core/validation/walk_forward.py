"""
Walk-forward валидация для корректной оценки моделей на временных рядах
Критически важно для предотвращения переобучения и lookahead bias
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, mean_squared_error, mean_absolute_error
)
import json

from backend.app.core import data_manager

logger = logging.getLogger(__name__)


@dataclass
class ValidationWindow:
    """Окно для валидации"""
    train_start: int
    train_end: int
    test_start: int
    test_end: int
    window_id: int
    
    @property
    def train_size(self) -> int:
        return self.train_end - self.train_start + 1
    
    @property
    def test_size(self) -> int:
        return self.test_end - self.test_start + 1


@dataclass
class ValidationMetrics:
    """Метрики для одного окна валидации"""
    window_id: int
    accuracy: float
    precision: float
    recall: float
    f1: float
    roc_auc: Optional[float]
    mse: float
    mae: float
    matches_distribution: Dict[int, int]  # Распределение совпадений
    custom_metrics: Dict[str, float]
    
    def to_dict(self) -> Dict:
        return {
            'window_id': self.window_id,
            'accuracy': self.accuracy,
            'precision': self.precision,
            'recall': self.recall,
            'f1': self.f1,
            'roc_auc': self.roc_auc,
            'mse': self.mse,
            'mae': self.mae,
            'matches_distribution': self.matches_distribution,
            'custom_metrics': self.custom_metrics
        }


@dataclass
class ValidationResults:
    """Результаты walk-forward валидации"""
    model_name: str
    lottery_type: str
    total_windows: int
    window_metrics: List[ValidationMetrics]
    average_metrics: Dict[str, float]
    std_metrics: Dict[str, float]
    best_window: int
    worst_window: int
    training_times: List[float]
    prediction_times: List[float]
    total_time: float
    parameters: Dict[str, Any]
    
    def get_summary(self) -> Dict:
        """Получить сводку результатов"""
        return {
            'model': self.model_name,
            'lottery': self.lottery_type,
            'windows': self.total_windows,
            'avg_accuracy': self.average_metrics.get('accuracy', 0),
            'avg_f1': self.average_metrics.get('f1', 0),
            'avg_roc_auc': self.average_metrics.get('roc_auc', 0),
            'std_accuracy': self.std_metrics.get('accuracy', 0),
            'best_window_id': self.best_window,
            'worst_window_id': self.worst_window,
            'total_time_seconds': self.total_time
        }
    
    def to_json(self) -> str:
        """Сериализация в JSON"""
        data = {
            'model_name': self.model_name,
            'lottery_type': self.lottery_type,
            'total_windows': self.total_windows,
            'window_metrics': [m.to_dict() for m in self.window_metrics],
            'average_metrics': self.average_metrics,
            'std_metrics': self.std_metrics,
            'best_window': self.best_window,
            'worst_window': self.worst_window,
            'training_times': self.training_times,
            'prediction_times': self.prediction_times,
            'total_time': self.total_time,
            'parameters': self.parameters,
            'summary': self.get_summary()
        }
        return json.dumps(data, indent=2)


class WalkForwardValidator:
    """
    Walk-forward валидатор для временных рядов лотерей
    Предотвращает lookahead bias и даёт реалистичную оценку производительности
    """
    
    def __init__(self, 
                 initial_train_size: int = 500,
                 test_size: int = 50,
                 step_size: int = 50,
                 expanding_window: bool = True):
        """
        Args:
            initial_train_size: Начальный размер обучающего окна
            test_size: Размер тестового окна
            step_size: Шаг сдвига окна
            expanding_window: True = расширяющееся окно, False = скользящее
        """
        self.initial_train_size = initial_train_size
        self.test_size = test_size
        self.step_size = step_size
        self.expanding_window = expanding_window
        
        logger.info(f"✅ Walk-forward валидатор инициализирован: "
                   f"train={initial_train_size}, test={test_size}, "
                   f"step={step_size}, expanding={expanding_window}")
    
    def create_windows(self, data_size: int) -> List[ValidationWindow]:
        """
        Создание окон для валидации
        
        Args:
            data_size: Общий размер данных
            
        Returns:
            Список окон валидации
        """
        windows = []
        window_id = 0
        
        # Начальная позиция
        train_start = 0
        train_end = self.initial_train_size - 1
        
        while train_end + self.test_size < data_size:
            test_start = train_end + 1
            test_end = min(test_start + self.test_size - 1, data_size - 1)
            
            windows.append(ValidationWindow(
                train_start=train_start,
                train_end=train_end,
                test_start=test_start,
                test_end=test_end,
                window_id=window_id
            ))
            
            # Сдвигаем окно
            if self.expanding_window:
                # Расширяющееся окно - начало остается, конец сдвигается
                train_end += self.step_size
            else:
                # Скользящее окно - сдвигаются оба конца
                train_start += self.step_size
                train_end += self.step_size
            
            window_id += 1
        
        logger.info(f"📊 Создано {len(windows)} окон валидации")
        return windows
    
    def validate_model(self,
                       model_class: Any,
                       model_params: Dict,
                       df_history: pd.DataFrame,
                       lottery_config: Dict,
                       custom_evaluator: Optional[Callable] = None) -> ValidationResults:
        """
        Полная walk-forward валидация модели
        
        Args:
            model_class: Класс модели (XGBoostLotteryModel, LotteryRFOps и т.д.)
            model_params: Параметры для инициализации модели
            df_history: История тиражей
            lottery_config: Конфигурация лотереи
            custom_evaluator: Кастомная функция оценки (опционально)
            
        Returns:
            Результаты валидации
        """
        import time
        start_time = time.time()
        
        if df_history.empty or len(df_history) < self.initial_train_size + self.test_size:
            logger.error(f"Недостаточно данных для валидации: {len(df_history)} тиражей")
            raise ValueError("Недостаточно данных для walk-forward валидации")
        
        # Создаем окна
        windows = self.create_windows(len(df_history))
        
        if not windows:
            raise ValueError("Не удалось создать окна валидации")
        
        logger.info(f"🚀 Начало walk-forward валидации модели {model_class.__name__}")
        
        window_metrics = []
        training_times = []
        prediction_times = []
        
        for window in windows:
            logger.info(f"📍 Окно {window.window_id}: "
                       f"train[{window.train_start}:{window.train_end}], "
                       f"test[{window.test_start}:{window.test_end}]")
            
            # Разделяем данные
            train_data = df_history.iloc[window.train_start:window.train_end + 1].copy()
            test_data = df_history.iloc[window.test_start:window.test_end + 1].copy()

            # Создаем новый экземпляр модели для каждого окна
            model = model_class(lottery_config, **model_params)
            
            # Обучаем модель
            train_start = time.time()
            try:
                success = model.train(train_data)
                if not success:
                    logger.warning(f"Не удалось обучить модель для окна {window.window_id}")
                    continue
            except Exception as e:
                logger.error(f"Ошибка обучения для окна {window.window_id}: {e}")
                continue
            
            training_time = time.time() - train_start
            training_times.append(training_time)
            
            # Оцениваем модель
            pred_start = time.time()
            metrics = self._evaluate_window(
                model, train_data, test_data, 
                window, lottery_config, custom_evaluator
            )
            prediction_time = time.time() - pred_start
            prediction_times.append(prediction_time)
            
            window_metrics.append(metrics)
            
            logger.info(f"✅ Окно {window.window_id}: "
                       f"accuracy={metrics.accuracy:.3f}, "
                       f"f1={metrics.f1:.3f}")
        
        # Вычисляем агрегированные метрики
        avg_metrics, std_metrics = self._calculate_aggregate_metrics(window_metrics)
        
        # Находим лучшее и худшее окно
        best_window = max(window_metrics, key=lambda m: m.f1).window_id
        worst_window = min(window_metrics, key=lambda m: m.f1).window_id
        
        total_time = time.time() - start_time
        
        results = ValidationResults(
            model_name=model_class.__name__,
            lottery_type=lottery_config.get('name', 'unknown'),
            total_windows=len(windows),
            window_metrics=window_metrics,
            average_metrics=avg_metrics,
            std_metrics=std_metrics,
            best_window=best_window,
            worst_window=worst_window,
            training_times=training_times,
            prediction_times=prediction_times,
            total_time=total_time,
            parameters={
                'initial_train_size': self.initial_train_size,
                'test_size': self.test_size,
                'step_size': self.step_size,
                'expanding_window': self.expanding_window,
                'model_params': model_params
            }
        )
        
        logger.info(f"🎯 Валидация завершена за {total_time:.2f}с")
        logger.info(f"📊 Средние метрики: accuracy={avg_metrics['accuracy']:.3f}, "
                   f"f1={avg_metrics['f1']:.3f}, "
                   f"roc_auc={avg_metrics.get('roc_auc', 0):.3f}")
        
        return results
    
    def _evaluate_window(self,
                        model: Any,
                        train_data: pd.DataFrame,
                        test_data: pd.DataFrame,
                        window: ValidationWindow,
                        lottery_config: Dict,
                        custom_evaluator: Optional[Callable]) -> ValidationMetrics:
        """
        Оценка модели на одном окне
        """
        predictions = []
        actuals = []
        matches_distribution = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0, 8: 0}

        df_history = data_manager.fetch_draws_from_db()

        # Для каждого тиража в тесте
        for idx, test_row in test_data.iterrows():
            # Получаем предыдущий тираж для контекста
            if idx > 0:
                prev_idx = idx - 1
                prev_row = df_history.iloc[prev_idx] if prev_idx >= 0 else train_data.iloc[-1]
                
                prev_f1 = prev_row.get('Числа_Поле1_list', [])
                prev_f2 = prev_row.get('Числа_Поле2_list', [])
                
                # Предсказываем
                try:
                    if hasattr(model, 'predict_next_combination'):
                        pred_f1, pred_f2 = model.predict_next_combination(
                            prev_f1, prev_f2, train_data
                        )
                    else:
                        # Fallback для моделей без этого метода
                        pred_f1 = list(range(1, lottery_config['field1_size'] + 1))
                        pred_f2 = list(range(1, lottery_config['field2_size'] + 1))
                    
                    # Сравниваем с актуальными
                    actual_f1 = test_row.get('Числа_Поле1_list', [])
                    actual_f2 = test_row.get('Числа_Поле2_list', [])
                    
                    # Считаем совпадения
                    matches_f1 = len(set(pred_f1) & set(actual_f1))
                    matches_f2 = len(set(pred_f2) & set(actual_f2))
                    total_matches = matches_f1 + matches_f2
                    
                    matches_distribution[total_matches] = matches_distribution.get(total_matches, 0) + 1
                    
                    # Бинарная метрика для каждого числа
                    for num in range(1, lottery_config['field1_max'] + 1):
                        predictions.append(1 if num in pred_f1 else 0)
                        actuals.append(1 if num in actual_f1 else 0)
                    
                    for num in range(1, lottery_config['field2_max'] + 1):
                        predictions.append(1 if num in pred_f2 else 0)
                        actuals.append(1 if num in actual_f2 else 0)
                        
                except Exception as e:
                    logger.warning(f"Ошибка предсказания: {e}")
                    continue
        
        if not predictions or not actuals:
            # Возвращаем нулевые метрики если нет предсказаний
            return ValidationMetrics(
                window_id=window.window_id,
                accuracy=0, precision=0, recall=0, f1=0, roc_auc=None,
                mse=1.0, mae=1.0,
                matches_distribution=matches_distribution,
                custom_metrics={}
            )
        
        # Вычисляем метрики
        predictions = np.array(predictions)
        actuals = np.array(actuals)
        
        accuracy = accuracy_score(actuals, predictions)
        precision = precision_score(actuals, predictions, average='micro', zero_division=0)
        recall = recall_score(actuals, predictions, average='micro', zero_division=0)
        f1 = f1_score(actuals, predictions, average='micro', zero_division=0)
        
        # ROC-AUC если есть вероятности
        roc_auc = None
        if hasattr(model, 'score_combination'):
            # Можем попробовать получить вероятности
            try:
                # Упрощенный подход - используем score как вероятность
                roc_auc = 0.5  # Placeholder, так как нужны вероятности для каждого предсказания
            except:
                pass
        
        mse = mean_squared_error(actuals, predictions)
        mae = mean_absolute_error(actuals, predictions)
        
        # Кастомные метрики
        custom_metrics = {}
        if custom_evaluator:
            try:
                custom_metrics = custom_evaluator(model, train_data, test_data)
            except Exception as e:
                logger.warning(f"Ошибка кастомного evaluator: {e}")
        
        return ValidationMetrics(
            window_id=window.window_id,
            accuracy=accuracy,
            precision=precision,
            recall=recall,
            f1=f1,
            roc_auc=roc_auc,
            mse=mse,
            mae=mae,
            matches_distribution=matches_distribution,
            custom_metrics=custom_metrics
        )
    
    def _calculate_aggregate_metrics(self, 
                                    window_metrics: List[ValidationMetrics]) -> Tuple[Dict, Dict]:
        """
        Вычисление средних и стандартных отклонений метрик
        """
        if not window_metrics:
            return {}, {}
        
        # Собираем все метрики в массивы
        metrics_arrays = {
            'accuracy': [m.accuracy for m in window_metrics],
            'precision': [m.precision for m in window_metrics],
            'recall': [m.recall for m in window_metrics],
            'f1': [m.f1 for m in window_metrics],
            'mse': [m.mse for m in window_metrics],
            'mae': [m.mae for m in window_metrics]
        }
        
        # ROC-AUC может быть None
        roc_aucs = [m.roc_auc for m in window_metrics if m.roc_auc is not None]
        if roc_aucs:
            metrics_arrays['roc_auc'] = roc_aucs
        
        # Вычисляем средние
        avg_metrics = {
            name: np.mean(values) for name, values in metrics_arrays.items()
        }
        
        # Вычисляем стандартные отклонения
        std_metrics = {
            name: np.std(values) for name, values in metrics_arrays.items()
        }
        
        # Агрегируем распределение совпадений
        total_matches_dist = {}
        for m in window_metrics:
            for matches, count in m.matches_distribution.items():
                total_matches_dist[matches] = total_matches_dist.get(matches, 0) + count
        
        avg_metrics['avg_matches_distribution'] = total_matches_dist
        
        return avg_metrics, std_metrics
    
    def compare_models(self,
                       models: List[Tuple[Any, Dict]],
                       df_history: pd.DataFrame,
                       lottery_config: Dict) -> pd.DataFrame:
        """
        Сравнение нескольких моделей
        
        Args:
            models: Список кортежей (model_class, model_params)
            df_history: История тиражей
            lottery_config: Конфигурация лотереи
            
        Returns:
            DataFrame со сравнением моделей
        """
        results = []
        
        for model_class, model_params in models:
            logger.info(f"🔄 Валидация модели {model_class.__name__}")
            
            try:
                validation_results = self.validate_model(
                    model_class, model_params, 
                    df_history, lottery_config
                )
                
                summary = validation_results.get_summary()
                summary['status'] = 'success'
                results.append(summary)
                
            except Exception as e:
                logger.error(f"Ошибка валидации {model_class.__name__}: {e}")
                results.append({
                    'model': model_class.__name__,
                    'status': 'error',
                    'error': str(e)
                })
        
        # Создаем DataFrame для удобного сравнения
        comparison_df = pd.DataFrame(results)
        
        # Сортируем по F1 score
        if 'avg_f1' in comparison_df.columns:
            comparison_df = comparison_df.sort_values('avg_f1', ascending=False)
        
        return comparison_df
    
    def plot_validation_results(self, results: ValidationResults):
        """
        Визуализация результатов валидации (требует matplotlib)
        """
        try:
            import matplotlib.pyplot as plt
            
            # Извлекаем метрики по окнам
            windows = [m.window_id for m in results.window_metrics]
            accuracies = [m.accuracy for m in results.window_metrics]
            f1_scores = [m.f1 for m in results.window_metrics]
            
            fig, axes = plt.subplots(2, 2, figsize=(12, 8))
            fig.suptitle(f'Walk-Forward Validation: {results.model_name}', fontsize=16)
            
            # График accuracy
            axes[0, 0].plot(windows, accuracies, 'b-', marker='o')
            axes[0, 0].axhline(y=results.average_metrics['accuracy'], color='r', linestyle='--', label='Average')
            axes[0, 0].set_xlabel('Window ID')
            axes[0, 0].set_ylabel('Accuracy')
            axes[0, 0].set_title('Accuracy по окнам')
            axes[0, 0].legend()
            axes[0, 0].grid(True, alpha=0.3)
            
            # График F1
            axes[0, 1].plot(windows, f1_scores, 'g-', marker='s')
            axes[0, 1].axhline(y=results.average_metrics['f1'], color='r', linestyle='--', label='Average')
            axes[0, 1].set_xlabel('Window ID')
            axes[0, 1].set_ylabel('F1 Score')
            axes[0, 1].set_title('F1 Score по окнам')
            axes[0, 1].legend()
            axes[0, 1].grid(True, alpha=0.3)
            
            # Распределение совпадений
            total_matches = {}
            for m in results.window_metrics:
                for matches, count in m.matches_distribution.items():
                    total_matches[matches] = total_matches.get(matches, 0) + count
            
            if total_matches:
                matches_nums = list(total_matches.keys())
                matches_counts = list(total_matches.values())
                axes[1, 0].bar(matches_nums, matches_counts, color='purple', alpha=0.7)
                axes[1, 0].set_xlabel('Количество совпадений')
                axes[1, 0].set_ylabel('Частота')
                axes[1, 0].set_title('Распределение совпадений')
                axes[1, 0].grid(True, alpha=0.3)
            
            # Время обучения
            axes[1, 1].plot(range(len(results.training_times)), results.training_times, 'r-', marker='^')
            axes[1, 1].set_xlabel('Window ID')
            axes[1, 1].set_ylabel('Время (сек)')
            axes[1, 1].set_title('Время обучения по окнам')
            axes[1, 1].grid(True, alpha=0.3)
            
            plt.tight_layout()
            return fig
            
        except ImportError:
            logger.warning("matplotlib не установлен, визуализация недоступна")
            return None


# Глобальный валидатор с дефолтными настройками
DEFAULT_VALIDATOR = WalkForwardValidator(
    initial_train_size=300,
    test_size=30,
    step_size=30,
    expanding_window=True
)
