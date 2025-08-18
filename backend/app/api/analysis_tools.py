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


@router.post("/patterns")
async def analyze_patterns(
    request: PatternAnalysisRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Детальный анализ паттернов выпадения"""
    try:
        print(f"🔍 Начинаем анализ паттернов для {request.lottery_type}")

        with LotteryContext(request.lottery_type):
            # Загружаем историю
            df_history = data_manager.fetch_draws_from_db()
            print(f"📊 Загружено {len(df_history)} тиражей")

            if df_history.empty:
                raise HTTPException(status_code=404, detail="Нет данных для анализа. Попробуйте обновить базу данных.")

            # Используем упрощенный анализ вместо GLOBAL_PATTERN_ANALYZER
            df_analysis = df_history.tail(request.depth)
            print(f"🔬 Анализируем последние {len(df_analysis)} тиражей")

            hot_cold_analysis = _analyze_hot_cold_simple(df_analysis)
            print("✅ Анализ горячих/холодных чисел завершен")

            # Анализ корреляций (упрощенный)
            correlations = _analyze_correlations_simple(df_analysis)
            print("✅ Анализ корреляций завершен")

            # Анализ избранных чисел (если включен)
            favorites_analysis = None
            if request.include_favorites:
                prefs = db.query(UserPreferences).filter_by(user_id=current_user.id).first()
                if prefs and prefs.favorite_numbers:
                    all_favorites = json.loads(prefs.favorite_numbers)
                    lottery_favorites = all_favorites.get(request.lottery_type, {"field1": [], "field2": []})
                    if lottery_favorites['field1'] or lottery_favorites['field2']:
                        favorites_analysis = _analyze_favorite_numbers(
                            df_analysis,
                            lottery_favorites['field1'],
                            lottery_favorites['field2']
                        )
                        print("✅ Анализ избранных чисел завершен")

            # Формируем результат
            result = {
                "status": "success",
                "hot_cold": hot_cold_analysis,
                "correlations": correlations,
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

            print("🔍 Отправляем результат анализа паттернов:", result)
            return result

    except Exception as e:
        import traceback
        print(f"❌ Ошибка анализа паттернов: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Ошибка анализа: {str(e)}")


def _analyze_correlations_simple(df_history, top_n=5):
    """Упрощенный анализ корреляций между числами"""

    correlations = {
        "field1": [],
        "field2": []
    }

    # Анализ пар в поле 1
    from collections import Counter
    field1_pairs = Counter()

    for _, row in df_history.iterrows():
        numbers = row['Числа_Поле1_list']
        # Генерируем все пары
        for i in range(len(numbers)):
            for j in range(i + 1, len(numbers)):
                pair = tuple(sorted([numbers[i], numbers[j]]))
                field1_pairs[pair] += 1

    # Топ пары для поля 1
    total_draws = len(df_history)
    for pair, count in field1_pairs.most_common(top_n):
        frequency = (count / total_draws) * 100
        correlations["field1"].append({
            "pair": f"{pair[0]}-{pair[1]}",
            "frequency_percent": round(frequency, 1),
            "count": count
        })

    # Анализ пар в поле 2
    field2_pairs = Counter()

    for _, row in df_history.iterrows():
        numbers = row['Числа_Поле2_list']
        if len(numbers) >= 2:  # Только если есть минимум 2 числа
            for i in range(len(numbers)):
                for j in range(i + 1, len(numbers)):
                    pair = tuple(sorted([numbers[i], numbers[j]]))
                    field2_pairs[pair] += 1

    # Топ пары для поля 2
    for pair, count in field2_pairs.most_common(top_n):
        frequency = (count / total_draws) * 100
        correlations["field2"].append({
            "pair": f"{pair[0]}-{pair[1]}",
            "frequency_percent": round(frequency, 1),
            "count": count
        })

    return correlations


@router.post("/clusters")
async def analyze_clusters(
    request: ClusterAnalysisRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Кластерный анализ чисел на основе частот и паттернов"""
    try:
        print(f"🔍 Начинаем кластерный анализ для {request.lottery_type}")

        with LotteryContext(request.lottery_type):
            df_history = data_manager.fetch_draws_from_db()
            print(f"📊 Загружено {len(df_history)} тиражей")

            if df_history.empty:
                raise HTTPException(status_code=404, detail="Нет данных для анализа")

            # Подготовка данных для кластеризации
            config = data_manager.get_current_config()

            # ИСПРАВЛЕНИЕ: Передаем правильные названия полей
            features_f1 = _prepare_clustering_features_fixed(
                df_history, 'field1', config['field1_max']
            )
            features_f2 = _prepare_clustering_features_fixed(
                df_history, 'field2', config['field2_max']
            )

            print(f"✅ Подготовлены признаки: поле1={len(features_f1)}, поле2={len(features_f2)}")

            # Выполняем кластеризацию
            if request.method == "kmeans":
                clusters_f1 = _kmeans_clustering(features_f1, request.n_clusters)
                clusters_f2 = _kmeans_clustering(features_f2, min(request.n_clusters, config['field2_max']))
            elif request.method == "dbscan":
                clusters_f1 = _dbscan_clustering(features_f1)
                clusters_f2 = _dbscan_clustering(features_f2)
            else:
                raise HTTPException(status_code=400, detail="Неподдерживаемый метод кластеризации")

            print(f"✅ Кластеризация завершена методом {request.method}")

            # Интерпретация кластеров
            cluster_interpretation = _interpret_clusters_fixed(
                clusters_f1, clusters_f2, df_history
            )

            result = {
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

            print("🔍 Отправляем результат кластерного анализа")
            return result

    except Exception as e:
        import traceback
        print(f"❌ Ошибка кластерного анализа: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Ошибка кластеризации: {str(e)}")


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

            # 1. Анализ горячих/холодных чисел (упрощенный без GLOBAL_PATTERN_ANALYZER)
            hot_cold_analysis = _analyze_hot_cold_simple(df_history)

            hot_f1 = hot_cold_analysis.get('field1', {}).get('hot_numbers', [])
            hot_f2 = hot_cold_analysis.get('field2', {}).get('hot_numbers', [])
            cold_f1 = hot_cold_analysis.get('field1', {}).get('cold_numbers', [])
            cold_f2 = hot_cold_analysis.get('field2', {}).get('cold_numbers', [])

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

            # 2. Анализ последовательностей
            sequence_score = _evaluate_sequences(request.field1, request.field2)
            score += sequence_score
            if sequence_score > 0:
                factors.append(f"📊 Хорошее распределение чисел (+{sequence_score})")

            # 3. Проверка на уникальность
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
        import traceback
        print(f"Ошибка оценки комбинации: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Ошибка оценки: {str(e)}")


def _analyze_hot_cold_simple(df_history, window=20, top_n=10):
    """Упрощенный анализ горячих/холодных чисел без GLOBAL_PATTERN_ANALYZER"""

    # Берем последние window тиражей
    recent_df = df_history.tail(window)

    analysis = {
        "field1": {"hot_numbers": [], "cold_numbers": []},
        "field2": {"hot_numbers": [], "cold_numbers": []}
    }

    # Анализ поля 1
    field1_counter = {}
    for _, row in recent_df.iterrows():
        for num in row['Числа_Поле1_list']:
            field1_counter[num] = field1_counter.get(num, 0) + 1

    # Сортируем по частоте
    sorted_f1 = sorted(field1_counter.items(), key=lambda x: x[1], reverse=True)
    analysis["field1"]["hot_numbers"] = [num for num, _ in sorted_f1[:top_n]]
    analysis["field1"]["cold_numbers"] = [num for num, _ in sorted_f1[-top_n:]]

    # Анализ поля 2
    field2_counter = {}
    for _, row in recent_df.iterrows():
        for num in row['Числа_Поле2_list']:
            field2_counter[num] = field2_counter.get(num, 0) + 1

    sorted_f2 = sorted(field2_counter.items(), key=lambda x: x[1], reverse=True)
    analysis["field2"]["hot_numbers"] = [num for num, _ in sorted_f2[:top_n]]
    analysis["field2"]["cold_numbers"] = [num for num, _ in sorted_f2[-top_n:]]

    return analysis

# Вспомогательные функции
def _analyze_favorite_numbers(df, favorites_f1, favorites_f2):
    """Анализ избранных чисел пользователя"""
    analysis = {
        "field1": {},
        "field2": {}
    }

    for num in favorites_f1:
        count = sum(num in row for row in df['Числа_Поле1_list'])  # ← Исправить
        analysis["field1"][num] = {
            "frequency": count,
            "percentage": (count / len(df)) * 100 if len(df) > 0 else 0
        }

    for num in favorites_f2:
        count = sum(num in row for row in df['Числа_Поле2_list'])  # ← Исправить
        analysis["field2"][num] = {
            "frequency": count,
            "percentage": (count / len(df)) * 100 if len(df) > 0 else 0
        }

    return analysis


def _prepare_clustering_features(df, field_name, max_num):
    """Подготовка признаков для кластеризации"""
    features = {}

    # Исправить определение колонки
    if 'field1' in field_name:
        column_name = 'Числа_Поле1_list'
    else:
        column_name = 'Числа_Поле2_list'


    for num in range(1, max_num + 1):
        # Частота появления
        frequency = sum(num in row for row in df[column_name])

        # Среднее расстояние между появлениями
        appearances = [i for i, row in enumerate(df[column_name]) if num in row]
        avg_gap = np.mean(np.diff(appearances)) if len(appearances) > 1 else len(df)

        # Тренд (появления в последних 20% тиражей)
        recent_df = df.tail(max(1, len(df) // 5))
        recent_freq = sum(num in row for row in recent_df[column_name])

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

    # Группировка по кластерам для обоих полей
    for field_name, clusters in [("field1", clusters_f1), ("field2", clusters_f2)]:
        cluster_groups = {}
        for num, cluster_id in clusters.items():
            if cluster_id not in cluster_groups:
                cluster_groups[cluster_id] = []
            cluster_groups[cluster_id].append(num)

        # Исправляем название колонки
        column_name = 'Числа_Поле1_list' if field_name == 'field1' else 'Числа_Поле2_list'

        # Интерпретация каждого кластера
        for cluster_id, numbers in cluster_groups.items():
            if cluster_id == -1:  # DBSCAN outliers
                interpretation[f"{field_name}_outliers"] = {
                    "numbers": numbers,
                    "description": "Аномальные числа с уникальными паттернами"
                }
            else:
                # Анализ характеристик кластера
                avg_frequency = np.mean([
                    sum(num in row for row in df_history[column_name])
                    for num in numbers
                ])

                if avg_frequency > len(df_history) * 0.15:
                    desc = "Горячий кластер - числа с высокой частотой"
                elif avg_frequency < len(df_history) * 0.05:
                    desc = "Холодный кластер - редко выпадающие числа"
                else:
                    desc = "Нейтральный кластер - средняя активность"

                interpretation[f"{field_name}_cluster_{cluster_id}"] = {
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


def _prepare_clustering_features_fixed(df, field_name, max_num):
    """Исправленная подготовка признаков для кластеризации"""
    features = {}

    # ИСПРАВЛЕНИЕ: Правильные названия колонок
    column_name = 'Числа_Поле1_list' if field_name == 'field1' else 'Числа_Поле2_list'

    print(f"🔧 Подготавливаем признаки для {field_name}, колонка: {column_name}")

    for num in range(1, max_num + 1):
        try:
            # Частота появления
            frequency = sum(num in row for row in df[column_name])

            # Среднее расстояние между появлениями
            appearances = [i for i, row in enumerate(df[column_name]) if num in row]
            avg_gap = np.mean(np.diff(appearances)) if len(appearances) > 1 else len(df)

            # Тренд (появления в последних 20% тиражей)
            recent_df = df.tail(max(1, len(df) // 5))
            recent_freq = sum(num in row for row in recent_df[column_name])

            features[num] = [frequency, avg_gap, recent_freq]
        except Exception as e:
            print(f"⚠️ Ошибка обработки числа {num}: {e}")
            features[num] = [0, len(df), 0]  # Дефолтные значения

    return features


def _interpret_clusters_fixed(clusters_f1, clusters_f2, df_history):
    """Исправленная интерпретация кластеров"""
    interpretation = {}

    # Группировка по кластерам для обоих полей
    for field_name, clusters in [("field1", clusters_f1), ("field2", clusters_f2)]:
        cluster_groups = {}
        for num, cluster_id in clusters.items():
            if cluster_id not in cluster_groups:
                cluster_groups[cluster_id] = []
            cluster_groups[cluster_id].append(num)

        # ИСПРАВЛЕНИЕ: Правильные названия колонок
        column_name = 'Числа_Поле1_list' if field_name == 'field1' else 'Числа_Поле2_list'

        # Интерпретация каждого кластера
        for cluster_id, numbers in cluster_groups.items():
            try:
                if cluster_id == -1:  # DBSCAN outliers
                    interpretation[f"{field_name}_outliers"] = {
                        "numbers": numbers,
                        "description": "Аномальные числа с уникальными паттернами"
                    }
                else:
                    # Анализ характеристик кластера
                    avg_frequency = np.mean([
                        sum(num in row for row in df_history[column_name])
                        for num in numbers
                    ])

                    if avg_frequency > len(df_history) * 0.15:
                        desc = "Горячий кластер - числа с высокой частотой"
                    elif avg_frequency < len(df_history) * 0.05:
                        desc = "Холодный кластер - редко выпадающие числа"
                    else:
                        desc = "Нейтральный кластер - средняя активность"

                    interpretation[f"{field_name}_cluster_{cluster_id}"] = {
                        "numbers": numbers,
                        "description": desc,
                        "avg_frequency": round(avg_frequency, 2)
                    }
            except Exception as e:
                print(f"⚠️ Ошибка интерпретации кластера {cluster_id}: {e}")
                interpretation[f"{field_name}_cluster_{cluster_id}"] = {
                    "numbers": numbers,
                    "description": "Ошибка анализа кластера",
                    "avg_frequency": 0
                }

    return interpretation