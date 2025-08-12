"""
Ультра быстрая RF оценка с глобальным кэшем данных
"""
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# Блокировка для thread-safe доступа к модели
model_lock = threading.Lock()

def score_combinations_ultra_fast(combinations_chunk, chunk_id, cached_df):
    """
    Ультра быстрая оценка с предзагруженными данными
    """
    try:
        from backend.app.core.ai_model import GLOBAL_RF_MODEL

        scores = []
        start_time = time.time()

        print(f"⚡ Thread {chunk_id}: старт оценки {len(combinations_chunk)} комбинаций")

        for i, (f1, f2) in enumerate(combinations_chunk):
            try:
                with model_lock:  # Минимальная блокировка
                    score = GLOBAL_RF_MODEL.score_combination(sorted(f1), sorted(f2), cached_df)
                scores.append((f1, f2, score))

            except Exception as e:
                scores.append((f1, f2, -float('inf')))

        elapsed = time.time() - start_time
        rate = len(combinations_chunk) / elapsed if elapsed > 0 else 0
        print(f"⚡ Thread {chunk_id}: завершен за {elapsed:.1f}с, скорость: {rate:.1f}/с")

        return scores

    except Exception as e:
        print(f"⚡ Thread {chunk_id}: критическая ошибка: {e}")
        return [(f1, f2, -float('inf')) for f1, f2 in combinations_chunk]

def ultra_fast_parallel_ranking(combinations, max_workers=3):
    """
    Ультра быстрая параллельная оценка с минимальными накладными расходами
    """
    if not combinations:
        return []

    # Ограничиваем количество потоков для снижения накладных расходов
    max_workers = min(max_workers, len(combinations), 3)

    print(f"⚡ УЛЬТРА БЫСТРАЯ оценка на {max_workers} потоках")

    # Получаем кэшированные данные ОДИН раз
    from backend.app.core.data_cache import GLOBAL_DATA_CACHE
    from backend.app.core import data_manager

    cached_df = GLOBAL_DATA_CACHE.get_cached_history(data_manager.CURRENT_LOTTERY)
    if cached_df.empty:
        print("❌ Нет кэшированных данных")
        return [(f1, f2, -float('inf')) for f1, f2 in combinations]

    # Разбиваем на небольшие чанки для лучшей балансировки
    chunk_size = max(1, len(combinations) // max_workers)
    chunks = [combinations[i:i + chunk_size] for i in range(0, len(combinations), chunk_size)]

    all_scores = []
    start_time = time.time()

    try:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Запускаем все чанки с предзагруженными данными
            future_to_chunk = {
                executor.submit(score_combinations_ultra_fast, chunk, idx, cached_df): chunk
                for idx, chunk in enumerate(chunks)
            }

            # Собираем результаты
            for future in as_completed(future_to_chunk):
                try:
                    chunk_scores = future.result(timeout=10)  # Сокращаем таймаут
                    all_scores.extend(chunk_scores)
                except Exception as e:
                    print(f"⚡ Chunk failed: {e}")
                    chunk = future_to_chunk[future]
                    all_scores.extend([(f1, f2, -float('inf')) for f1, f2 in chunk])

    except Exception as e:
        print(f"⚡ Ultra fast threading failed: {e}")
        # Быстрый fallback без дополнительной загрузки данных
        from backend.app.core.ai_model import GLOBAL_RF_MODEL
        for f1, f2 in combinations:
            score = GLOBAL_RF_MODEL.score_combination(sorted(f1), sorted(f2), cached_df)
            all_scores.append((f1, f2, score))

    elapsed = time.time() - start_time
    rate = len(combinations) / elapsed if elapsed > 0 else 0
    print(f"⚡ УЛЬТРА БЫСТРО: {len(combinations)} комбинаций за {elapsed:.1f}с (скорость: {rate:.1f}/с)")

    return all_scores

def smart_combination_generator(num_needed, avoid_duplicates=True):
    """Умная генерация комбинаций"""
    from backend.app.core.combination_generator import generate_random_combination

    combinations = []
    seen = set() if avoid_duplicates else None
    max_attempts = num_needed * 2  # Уменьшаем попытки

    for _ in range(max_attempts):
        if len(combinations) >= num_needed:
            break

        f1, f2 = generate_random_combination()

        if avoid_duplicates:
            combo_key = (tuple(sorted(f1)), tuple(sorted(f2)))
            if combo_key in seen:
                continue
            seen.add(combo_key)

        combinations.append((f1, f2))

    return combinations