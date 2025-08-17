"""
API для инструментов анализа
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Optional
from pydantic import BaseModel
import numpy as np
import pandas as pd
from datetime import datetime
from sklearn.cluster import KMeans, DBSCAN
from sklearn.preprocessing import StandardScaler
import json

from backend.app.core.auth import get_current_user
from backend.app.core.lottery_context import LotteryContext
from backend.app.core import data_manager, pattern_analyzer, ai_model
from backend.app.core.database import User, UserPreferences, get_db

router = APIRouter()


class PatternAnalysisRequest(BaseModel):
    """Запрос на анализ паттернов"""
    lottery_type: str = "4x20"
    depth: int = 100
    include_favorites: bool = True


class ClusterAnalysisRequest(BaseModel):
    """Запрос на кластерный анализ"""
    lottery_type: str = "4x20"
    n_clusters: int = 5
    method: str = "kmeans"  # kmeans, dbscan, hierarchical


class CombinationEvaluationRequest(BaseModel):
    """Запрос на оценку комбинации"""
    lottery_type: str = "4x20"
    field1: List[int]
    field2: List[int]
    use_favorites: bool = False


# @router.post("/patterns")
# async def analyze_patterns(
#     request: PatternAnalysisRequest,
#     current_user: User = Depends(get_current_user),
#     db: Session = Depends(get_db)
# ):
#     """Детальный анализ паттернов выпадения"""
#     try:
#         with LotteryContext(request.lottery_type):
#             # Загружаем историю
#             df_history = data_manager.fetch_draws_from_db()
#
#             if df_history.empty:
#                 raise HTTPException(status_code=404, detail="Нет данных для анализа")
#
#             # Используем последние N тиражей
#             df_analysis = df_history.tail(request.depth)
#
#             # Анализируем паттерны через GLOBAL_PATTERN_ANALYZER
#             hot_cold = pattern_analyzer.GLOBAL_PATTERN_ANALYZER.analyze_hot_cold_numbers(
#                 df_analysis,
#                 window_sizes=[20, 50],
#                 top_n=10
#             )
#
#             # Корреляции чисел
#             correlations = pattern_analyzer.GLOBAL_PATTERN_ANALYZER.find_number_correlations(
#                 df_analysis
#             )
#
#             # Циклы выпадения
#             cycles = pattern_analyzer.GLOBAL_PATTERN_ANALYZER.analyze_number_cycles(
#                 df_analysis,
#                 top_n=10
#             )
#
#             # Если включены избранные числа
#             favorite_analysis = None
#             if request.include_favorites:
#                 prefs = db.query(UserPreferences).filter_by(user_id=current_user.id).first()
#                 if prefs and prefs.favorite_numbers:
#                     favorites = json.loads(prefs.favorite_numbers)
#                     favorite_analysis = _analyze_favorite_numbers(
#                         df_analysis,
#                         favorites['field1'],
#                         favorites['field2']
#                     )
#
#             return {
#                 "status": "success",
#                 "patterns": {
#                     "hot_cold": hot_cold,
#                     "correlations": correlations,
#                     "cycles": cycles,
#                     "favorite_analysis": favorite_analysis
#                 },
#                 "analyzed_draws": len(df_analysis),
#                 "date_range": {
#                     "from": df_analysis['draw_date'].min().isoformat() if not df_analysis.empty else None,
#                     "to": df_analysis['draw_date'].max().isoformat() if not df_analysis.empty else None
#                 },
#                 "timestamp": datetime.utcnow().isoformat()
#             }
#
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

@router.post("/patterns")
async def analyze_patterns(
    request: PatternAnalysisRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Детальный анализ паттернов выпадения"""
    try:
        with LotteryContext(request.lottery_type):
            # Загружаем историю
            df_history = data_manager.fetch_draws_from_db()

            if df_history.empty:
                raise HTTPException(status_code=404, detail="Нет данных для анализа. Попробуйте обновить базу данных.")

            # Анализ горячих/холодных чисел
            hot_cold_analysis = pattern_analyzer.GLOBAL_PATTERN_ANALYZER.analyze_hot_cold_numbers(
                df_history.tail(request.depth),
                window_sizes=[20, 50],
                top_n=15
            )

            # Анализ корреляций
            correlations = pattern_analyzer.GLOBAL_PATTERN_ANALYZER.find_number_correlations(df_history)

            # Анализ избранных чисел (если включен)
            favorites_analysis = None
            if request.include_favorites:
                prefs = db.query(UserPreferences).filter_by(user_id=current_user.id).first()
                if prefs and prefs.favorite_numbers:
                    all_favorites = json.loads(prefs.favorite_numbers)
                    lottery_favorites = all_favorites.get(request.lottery_type, {"field1": [], "field2": []})
                    if lottery_favorites['field1'] or lottery_favorites['field2']:
                        favorites_analysis = _analyze_favorite_numbers(
                            df_history,
                            lottery_favorites['field1'],
                            lottery_favorites['field2']
                        )

            # Формируем результат
            result = {
                "status": "success",
                "hot_cold": {
                    "field1": {
                        "hot": hot_cold_analysis.get('field1_window_20', {}).get('hot_numbers', []),
                        "cold": hot_cold_analysis.get('field1_window_20', {}).get('cold_numbers', [])
                    },
                    "field2": {
                        "hot": hot_cold_analysis.get('field2_window_20', {}).get('hot_numbers', []),
                        "cold": hot_cold_analysis.get('field2_window_20', {}).get('cold_numbers', [])
                    }
                },
                "correlations": {
                    "field1": [
                        {
                            "pair": f"{p[0]}-{p[1]}",
                            "frequency_percent": round(freq, 1),
                            "count": count
                        }
                        for p, count, freq in correlations.get('field1', {}).get('frequent_pairs', [])[:10]
                    ],
                    "field2": [
                        {
                            "pair": f"{p[0]}-{p[1]}",
                            "frequency_percent": round(freq, 1),
                            "count": count
                        }
                        for p, count, freq in correlations.get('field2', {}).get('frequent_pairs', [])[:10]
                    ]
                },
                "favorites_analysis": favorites_analysis,
                "data_stats": {
                    "total_draws": len(df_history),
                    "analyzed_period": request.depth,
                    "lottery_type": request.lottery_type
                },
                "date_range": {
                    "from": df_history['Дата'].min().isoformat() if not df_history.empty else None,
                    "to": df_history['Дата'].max().isoformat() if not df_history.empty else None
                },
                "timestamp": datetime.utcnow().isoformat()
            }
        return result

    except Exception as e:
        import traceback
        print(f"Ошибка анализа паттернов: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Ошибка анализа: {str(e)}")


@router.post("/clusters")
async def analyze_clusters(
    request: ClusterAnalysisRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Кластерный анализ чисел на основе частот и паттернов"""
    try:
        with LotteryContext(request.lottery_type):
            df_history = data_manager.fetch_draws_from_db()

            if df_history.empty:
                raise HTTPException(status_code=404, detail="Нет данных для анализа")

            # Подготовка данных для кластеризации
            config = data_manager.get_current_config()

            # Создаём матрицу признаков для каждого числа
            features_f1 = _prepare_clustering_features(
                df_history, 'field1_numbers', config['field1_max']
            )
            features_f2 = _prepare_clustering_features(
                df_history, 'field2_numbers', config['field2_max']
            )

            # Выполняем кластеризацию
            if request.method == "kmeans":
                clusters_f1 = _kmeans_clustering(features_f1, request.n_clusters)
                clusters_f2 = _kmeans_clustering(features_f2, min(request.n_clusters, config['field2_max']))
            elif request.method == "dbscan":
                clusters_f1 = _dbscan_clustering(features_f1)
                clusters_f2 = _dbscan_clustering(features_f2)
            else:
                raise HTTPException(status_code=400, detail="Неподдерживаемый метод кластеризации")

            # Интерпретация кластеров
            cluster_interpretation = _interpret_clusters(
                clusters_f1, clusters_f2, df_history
            )

            return {
                "status": "success",
                "clusters": {
                    "field1": clusters_f1,
                    "field2": clusters_f2
                },
                "interpretation": cluster_interpretation,
                "method": request.method,
                "n_clusters_found": {
                    "field1": len(set(clusters_f1.values())),
                    "field2": len(set(clusters_f2.values()))
                },
                "timestamp": datetime.utcnow().isoformat()
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/evaluate")
async def evaluate_combination(
    request: CombinationEvaluationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Комплексная оценка комбинации с AI-скорингом"""
    try:
        with LotteryContext(request.lottery_type):
            df_history = data_manager.fetch_draws_from_db()

            if df_history.empty:
                raise HTTPException(status_code=404, detail="Нет данных для анализа")

            config = data_manager.get_current_config()
            score = 0.0
            factors = []

            # 1. Анализ горячих/холодных чисел
            hot_cold_analysis = pattern_analyzer.GLOBAL_PATTERN_ANALYZER.analyze_hot_cold_numbers(
                df_history.tail(50),
                window_sizes=[20],
                top_n=15
            )

            hot_f1 = hot_cold_analysis.get('field1_window_20', {}).get('hot_numbers', [])
            hot_f2 = hot_cold_analysis.get('field2_window_20', {}).get('hot_numbers', [])
            cold_f1 = hot_cold_analysis.get('field1_window_20', {}).get('cold_numbers', [])
            cold_f2 = hot_cold_analysis.get('field2_window_20', {}).get('cold_numbers', [])

            hot_count = len(set(request.field1) & set(hot_f1)) + len(set(request.field2) & set(hot_f2))
            cold_count = len(set(request.field1) & set(cold_f1)) + len(set(request.field2) & set(cold_f2))

            if hot_count >= 3:
                score += 25
                factors.append(f"✅ Содержит {hot_count} горячих чисел (+25)")
            elif hot_count >= 1:
                score += 15
                factors.append(f"➕ Содержит {hot_count} горячих чисел (+15)")

            if cold_count >= 2:
                score += 20
                factors.append(f"🔄 Содержит {cold_count} холодных чисел, готовых к выходу (+20)")

            # 2. Проверка последовательностей и интервалов
            seq_score = _evaluate_sequences(request.field1, request.field2)
            score += seq_score
            if seq_score > 0:
                factors.append(f"📊 Хорошее распределение чисел (+{seq_score})")

            # 3. AI-оценка через модель
            if ai_model.GLOBAL_AI_MODEL.models_trained:
                try:
                    ai_score = ai_model.GLOBAL_AI_MODEL.evaluate_combination(
                        request.field1, request.field2
                    )
                    normalized_ai_score = min(30, ai_score * 30)  # Нормализуем до 30 баллов
                    score += normalized_ai_score
                    factors.append(f"🤖 AI-оценка: {normalized_ai_score:.1f}/30")
                except:
                    pass  # Если модель не готова, пропускаем

            # 4. Проверка избранных чисел
            if request.use_favorites:
                prefs = db.query(UserPreferences).filter_by(user_id=current_user.id).first()
                if prefs and prefs.favorite_numbers:
                    favorites = json.loads(prefs.favorite_numbers)
                    fav_match_f1 = len(set(request.field1) & set(favorites.get('field1', [])))
                    fav_match_f2 = len(set(request.field2) & set(favorites.get('field2', [])))

                    if fav_match_f1 + fav_match_f2 > 0:
                        bonus = min(15, (fav_match_f1 + fav_match_f2) * 3)
                        score += bonus
                        factors.append(f"⭐ Использует {fav_match_f1 + fav_match_f2} избранных чисел (+{bonus})")

            # 5. Проверка на уникальность
            uniqueness = _check_uniqueness(request.field1, request.field2, df_history)
            score += uniqueness
            if uniqueness > 10:
                factors.append(f"💎 Уникальная комбинация (+{uniqueness})")

            # Нормализация скора
            score = min(100, max(0, score))

            # Генерация рекомендаций
            if score >= 80:
                recommendation = "🏆 Отличная комбинация! Высокий потенциал"
            elif score >= 60:
                recommendation = "✅ Хорошая комбинация с сбалансированными показателями"
            elif score >= 40:
                recommendation = "⚡ Средняя комбинация, можно улучшить"
            else:
                recommendation = "⚠️ Слабая комбинация, рекомендуется пересмотреть"

            return {
                "status": "success",
                "score": round(score, 1),
                "max_score": 100,
                "factors": factors,
                "recommendation": recommendation,
                "combination": {
                    "field1": request.field1,
                    "field2": request.field2
                },
                "suggestions": _generate_improvement_suggestions(
                    score, hot_count, cold_count, request.field1, request.field2
                ),
                "timestamp": datetime.utcnow().isoformat()
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Вспомогательные функции
def _analyze_favorite_numbers(df, favorites_f1, favorites_f2):
    """Анализ избранных чисел пользователя"""
    analysis = {
        "field1": {},
        "field2": {}
    }

    for num in favorites_f1:
        count = sum(num in row for row in df['field1_numbers'])
        analysis["field1"][num] = {
            "frequency": count,
            "percentage": (count / len(df)) * 100 if len(df) > 0 else 0
        }

    for num in favorites_f2:
        count = sum(num in row for row in df['field2_numbers'])
        analysis["field2"][num] = {
            "frequency": count,
            "percentage": (count / len(df)) * 100 if len(df) > 0 else 0
        }

    return analysis


def _prepare_clustering_features(df, field_name, max_num):
    """Подготовка признаков для кластеризации"""
    features = {}

    for num in range(1, max_num + 1):
        # Частота появления
        frequency = sum(num in row for row in df[field_name])

        # Среднее расстояние между появлениями
        appearances = [i for i, row in enumerate(df[field_name]) if num in row]
        avg_gap = np.mean(np.diff(appearances)) if len(appearances) > 1 else len(df)

        # Тренд (появления в последних 20% тиражей)
        recent_df = df.tail(max(1, len(df) // 5))
        recent_freq = sum(num in row for row in recent_df[field_name])

        features[num] = [frequency, avg_gap, recent_freq]

    return features


def _kmeans_clustering(features, n_clusters):
    """KMeans кластеризация"""
    if not features:
        return {}

    X = np.array(list(features.values()))
    numbers = list(features.keys())

    # Нормализация
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Кластеризация
    kmeans = KMeans(n_clusters=min(n_clusters, len(numbers)), random_state=42)
    labels = kmeans.fit_predict(X_scaled)

    return {num: int(label) for num, label in zip(numbers, labels)}


def _dbscan_clustering(features):
    """DBSCAN кластеризация"""
    if not features:
        return {}

    X = np.array(list(features.values()))
    numbers = list(features.keys())

    # Нормализация
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Кластеризация
    dbscan = DBSCAN(eps=0.5, min_samples=2)
    labels = dbscan.fit_predict(X_scaled)

    return {num: int(label) for num, label in zip(numbers, labels)}


def _interpret_clusters(clusters_f1, clusters_f2, df_history):
    """Интерпретация кластеров"""
    interpretation = {}

    # Группировка по кластерам
    for field, clusters in [("field1", clusters_f1), ("field2", clusters_f2)]:
        cluster_groups = {}
        for num, cluster_id in clusters.items():
            if cluster_id not in cluster_groups:
                cluster_groups[cluster_id] = []
            cluster_groups[cluster_id].append(num)

        # Интерпретация каждого кластера
        for cluster_id, numbers in cluster_groups.items():
            if cluster_id == -1:  # DBSCAN outliers
                interpretation[f"{field}_outliers"] = {
                    "numbers": numbers,
                    "description": "Аномальные числа с уникальными паттернами"
                }
            else:
                # Анализ характеристик кластера
                avg_frequency = np.mean([
                    sum(num in row for row in df_history[f'{field}_numbers'])
                    for num in numbers
                ])

                if avg_frequency > len(df_history) * 0.15:
                    desc = "Горячий кластер - числа с высокой частотой"
                elif avg_frequency < len(df_history) * 0.05:
                    desc = "Холодный кластер - редко выпадающие числа"
                else:
                    desc = "Нейтральный кластер - средняя активность"

                interpretation[f"{field}_cluster_{cluster_id}"] = {
                    "numbers": numbers,
                    "description": desc,
                    "avg_frequency": round(avg_frequency, 2)
                }

    return interpretation


def _evaluate_sequences(field1, field2):
    """Оценка последовательностей и интервалов"""
    score = 0

    # Проверка на последовательные числа
    for field in [field1, field2]:
        sorted_field = sorted(field)
        sequences = []
        current_seq = [sorted_field[0]]

        for i in range(1, len(sorted_field)):
            if sorted_field[i] == sorted_field[i-1] + 1:
                current_seq.append(sorted_field[i])
            else:
                if len(current_seq) > 1:
                    sequences.append(current_seq)
                current_seq = [sorted_field[i]]

        if len(current_seq) > 1:
            sequences.append(current_seq)

        # Оптимально иметь 1-2 коротких последовательности
        if len(sequences) == 1 and len(sequences[0]) <= 3:
            score += 5
        elif len(sequences) == 0:
            score += 3  # Хорошее распределение без последовательностей

    # Проверка интервалов
    for field in [field1, field2]:
        sorted_field = sorted(field)
        gaps = [sorted_field[i+1] - sorted_field[i] for i in range(len(sorted_field)-1)]

        # Оптимально иметь равномерные интервалы
        if gaps and np.std(gaps) < 3:
            score += 5

    return min(15, score)


def _check_uniqueness(field1, field2, df_history):
    """Проверка уникальности комбинации"""
    combo_str = f"{sorted(field1)}-{sorted(field2)}"

    # Проверяем, встречалась ли такая комбинация
    for _, row in df_history.iterrows():
        if (sorted(row['Числа_Поле1_list']) == sorted(field1) and
            sorted(row['Числа_Поле2_list']) == sorted(field2)):
            return 0  # Комбинация уже выпадала

    # Проверяем похожие комбинации (с пересечением > 80%)
    for _, row in df_history.iterrows():
        f1_intersection = len(set(field1) & set(row['Числа_Поле1_list']))
        f2_intersection = len(set(field2) & set(row['Числа_Поле2_list']))

        total_numbers = len(field1) + len(field2)
        total_intersections = f1_intersection + f2_intersection

        similarity = total_intersections / total_numbers

        if similarity > 0.8:
            return 5  # Очень похожая комбинация
        elif similarity > 0.6:
            return 10  # Частично похожая

    return 15  # Уникальная комбинация


def _generate_improvement_suggestions(score, hot_count, cold_count, field1, field2):
    """Генерация рекомендаций для улучшения"""
    suggestions = []

    if score < 40:
        if hot_count < 2:
            suggestions.append("Добавьте больше горячих чисел (2-3 шт)")
        if cold_count < 1:
            suggestions.append("Включите 1-2 холодных числа для баланса")

        # Проверка на последовательности
        sequences_f1 = _count_sequences(field1)
        sequences_f2 = _count_sequences(field2)

        if sequences_f1 > 2:
            suggestions.append("Уменьшите количество последовательных чисел в поле 1")
        if sequences_f2 > 1:
            suggestions.append("Избегайте последовательных чисел в поле 2")

        # Проверка распределения
        if len(field1) > 2:
            spread_f1 = max(field1) - min(field1)
            if spread_f1 < len(field1) * 2:
                suggestions.append("Увеличьте разброс чисел в поле 1")

    elif score < 70:
        suggestions.append("Хорошая база, попробуйте заменить 1-2 числа на более горячие")
        suggestions.append("Проверьте корреляции - возможно есть удачные пары")

    if not suggestions:
        suggestions.append("Отличная комбинация! Можно играть как есть")

    return suggestions



def _count_sequences(numbers):
    """Подсчет последовательных чисел"""
    if len(numbers) < 2:
        return 0

    sorted_nums = sorted(numbers)
    sequences = 0

    for i in range(1, len(sorted_nums)):
        if sorted_nums[i] == sorted_nums[i - 1] + 1:
            sequences += 1

    return sequences