import logging
import asyncio
from datetime import datetime

import pandas as pd
from fastapi import APIRouter, Depends, Path, HTTPException, Query
from typing import List

# Импорты из вашего проекта
from backend.app.core import combination_generator, ai_model, data_manager, utils
from backend.app.models.schemas import GenerationParams, GenerationResponse, Combination
from backend.app.core.lottery_context import LotteryContext
from backend.app.core.subscription_protection import require_basic, SubscriptionLevel, check_subscription_access
from backend.app.core.async_ai_model import ASYNC_MODEL_MANAGER
from backend.app.core.async_data_manager import ASYNC_DATA_MANAGER
router = APIRouter()
logger = logging.getLogger(__name__)

# Зависимость для установки контекста лотереи
async def set_lottery_context(
    lottery_type: str = Path(..., description="Тип лотереи: '4x20' или '5x36plus'")
):
    if lottery_type not in data_manager.LOTTERY_CONFIGS:
        raise HTTPException(status_code=404, detail="Lottery type not found")
    with LotteryContext(lottery_type):
        yield


@router.post("/generate", response_model=GenerationResponse, summary="🔒 Генерация (асинхронная)")
async def generate_combinations_async(
    params: GenerationParams,
    context: None = Depends(set_lottery_context),
    current_user=Depends(require_basic)
):
  """
  🚀 АСИНХРОННАЯ генерация комбинаций - не блокирует сервер!

  **Особенности:**
  - Параллельная обработка запросов
  - Неблокирующий доступ к моделям
  - Быстрый ответ даже при обучении
  """
  try:
    lottery_type = data_manager.CURRENT_LOTTERY
    lottery_config = data_manager.get_current_config()

    # Асинхронно загружаем данные
    df_history = await ASYNC_DATA_MANAGER.fetch_draws_async(lottery_type)

    if df_history.empty:
      return GenerationResponse(combinations=[], rf_prediction=None, lstm_prediction=None)

    # Генерируем комбинации в отдельном потоке
    generated = await asyncio.get_event_loop().run_in_executor(
      None,  # Используем default executor
      _sync_generate_combinations,
      df_history, params
    )

    combinations_response = [
      Combination(field1=f1, field2=f2, description=desc)
      for f1, f2, desc in generated
    ]

    # Асинхронный RF прогноз
    rf_pred = None
    try:
      if not df_history.empty:
        last_draw = df_history.iloc[0]
        f1_pred, f2_pred = await ASYNC_MODEL_MANAGER.predict_combination(
          lottery_type, lottery_config,
          last_draw['Числа_Поле1_list'],
          last_draw['Числа_Поле2_list'],
          df_history
        )

        if f1_pred and f2_pred:
          rf_pred = Combination(
            field1=f1_pred, field2=f2_pred,
            description="RF Async Prediction"
          )
    except Exception as e:
      logger.warning(f"RF prediction error: {e}")

    return GenerationResponse(
      combinations=combinations_response,
      rf_prediction=rf_pred,
      lstm_prediction=None  # LSTM добавим позже
    )

  except Exception as e:
    logger.error(f"Async generation error: {e}")
    raise HTTPException(status_code=500, detail="Ошибка генерации")


def _sync_generate_combinations(df_history: pd.DataFrame, params: GenerationParams):
  """Синхронная генерация для выполнения в потоке"""
  strategy_map = {
    'multi_strategy': combination_generator.generate_multi_strategy_combinations,
    'ml_based_rf': combination_generator.generate_ml_based_combinations,
    'rf_ranked': combination_generator.generate_rf_ranked_combinations
  }

  pattern_map = {
    'hot': lambda df, n: combination_generator.generate_pattern_based_combinations(df, n, 'hot'),
    'cold': lambda df, n: combination_generator.generate_pattern_based_combinations(df, n, 'cold'),
    'balanced': lambda df, n: combination_generator.generate_pattern_based_combinations(df, n, 'balanced')
  }

  gen_func = strategy_map.get(params.generator_type) or pattern_map.get(params.generator_type)

  if not gen_func:
    raise ValueError(f"Недопустимый тип генератора: '{params.generator_type}'")

  return gen_func(df_history, params.num_combinations)

@router.get("/training-status", summary="Статус обучения моделей")
async def get_training_status():
    """
    Возвращает статус обучения AI моделей для всех лотерей
    """
    return {
        "training_status": ASYNC_MODEL_MANAGER.get_training_status(),
        "timestamp": datetime.now().isoformat()
    }


@router.post("/generate", response_model=GenerationResponse, summary="🔒 Сгенерировать комбинации и получить прогнозы")
def generate_combinations(params: GenerationParams, context: None = Depends(set_lottery_context),
                          current_user=Depends(require_basic)):
  """
  🔒 ЗАЩИЩЕННАЯ ФУНКЦИЯ: Генерирует лотерейные комбинации на основе выбранной стратегии.
  Также возвращает последние прогнозы от моделей RF и LSTM.

  **Требования:** Базовая подписка или выше

  **Лимиты по подпискам:**
  - 🆓 Бесплатно: 3 генерации в день
  - 💼 Базовая: 20 генераций в день
  - 🌟 Премиум: 100 генераций в день
  - 🚀 Про: Безлимит

  **Лимиты времени:**
  - Базовая подписка: до 30 секунд
  - Премиум/Про: до 60 секунд
  """
  # НОВАЯ ЛОГИКА: Отслеживание времени и оптимизация
  import time
  from backend.app.core import data_manager
  start_time = time.time()

  # Определяем лимит времени по подписке
  max_time = 15  # Базовый лимит
  user_plan = "basic"  # По умолчанию

  if hasattr(current_user, 'preferences') and current_user.preferences:
    user_plan = current_user.preferences.get('subscription_plan', 'basic')
    if user_plan in ['premium', 'pro']:
      max_time = 25  # Больше времени для премиум (было 60)

  print(f"🚀 БЫСТРАЯ генерация для '{user_plan}' (лимит: {max_time}с)")

  # ОРИГИНАЛЬНАЯ ЛОГИКА: Загрузка истории
  df_history = data_manager.fetch_draws_from_db()
  if df_history.empty:
    return GenerationResponse(combinations=[], rf_prediction=None, lstm_prediction=None)

  # НОВАЯ ЛОГИКА: Оптимизация для базовых планов
  optimized_params = params
  if user_plan == "basic" and params.num_combinations > 5:
    print(f"⚠️ Ограничение для базового плана - максимум 5 комбинаций (запрошено {params.num_combinations})")
    optimized_params = GenerationParams(
      generator_type=params.generator_type,
      num_combinations=min(params.num_combinations, 5)
    )

  # ОРИГИНАЛЬНАЯ ЛОГИКА: Выбор генератора
  strategy_map = {
    'multi_strategy': combination_generator.generate_multi_strategy_combinations,
    'ml_based_rf': combination_generator.generate_ml_based_combinations,
    'rf_ranked': combination_generator.generate_rf_ranked_combinations
  }
  pattern_map = {
    'hot': lambda df, n: combination_generator.generate_pattern_based_combinations(df, n, 'hot'),
    'cold': lambda df, n: combination_generator.generate_pattern_based_combinations(df, n, 'cold'),
    'balanced': lambda df, n: combination_generator.generate_pattern_based_combinations(df, n, 'balanced')
  }

  gen_func = strategy_map.get(optimized_params.generator_type) or pattern_map.get(optimized_params.generator_type)

  # ОРИГИНАЛЬНАЯ ЛОГИКА: Проверка генератора
  if not gen_func:
    # Эта проверка — защита от несоответствий между Pydantic моделью и реализацией.
    # Она предотвращает падение сервера.
    raise HTTPException(
      status_code=400,  # 400 Bad Request - ошибка в запросе клиента
      detail=f"Недопустимый тип генератора: '{optimized_params.generator_type}'. Проверьте документацию /docs для доступных значений."
    )

  # НОВАЯ ЛОГИКА: Турбо-режим для премиум пользователей
  use_turbo_mode = user_plan in ['premium', 'pro'] and params.num_combinations <= 3

  if use_turbo_mode:
    print(f"🚀 ТУРБО-РЕЖИМ для {user_plan}: максимальное ускорение")

    try:
      # ИСПРАВЛЕНИЕ: Более безопасная проверка импорта
      try:
        from backend.app.core.trend_analyzer import GLOBAL_TREND_ANALYZER
        trend_analyzer_available = True
      except ImportError:
        print("⚠️ Анализатор трендов недоступен, используем обычную генерацию")
        trend_analyzer_available = False

      turbo_combinations = []

      if trend_analyzer_available:
        # Быстрый анализ трендов (0.01-0.05с)
        trends = GLOBAL_TREND_ANALYZER.analyze_current_trends(df_history)

        # Генерируем комбинации на основе трендов
        for i in range(params.num_combinations):
          try:
            smart_f1 = _generate_turbo_field(trends.get('field1'), 1)
            smart_f2 = _generate_turbo_field(trends.get('field2'), 2)

            turbo_combinations.append((
              smart_f1,
              smart_f2,
              f"🚀Турбо #{i + 1} (умная)"
            ))
          except Exception as e:
            print(f"⚠️ Ошибка умной генерации #{i + 1}: {e}")
            # Fallback на случайную
            f1, f2 = combination_generator.generate_random_combination()
            turbo_combinations.append((f1, f2, f"🚀Турбо #{i + 1} (случайная)"))

      # Если анализатор недоступен или недостаточно комбинаций
      while len(turbo_combinations) < params.num_combinations:
        f1, f2 = combination_generator.generate_random_combination()
        turbo_combinations.append((f1, f2, f"🚀Турбо #{len(turbo_combinations) + 1}"))

      combinations_response = [
        Combination(field1=f1, field2=f2, description=desc)
        for f1, f2, desc in turbo_combinations
      ]

      turbo_time = time.time() - start_time
      print(f"🚀 ТУРБО завершен за {turbo_time:.3f}с")

      # В турбо-режиме пропускаем RF/LSTM прогнозы для максимальной скорости
      return GenerationResponse(
        combinations=combinations_response,
        rf_prediction=None,
        lstm_prediction=None
      )

    except Exception as e:
      print(f"❌ Ошибка турбо-режима: {e}")
      import traceback
      traceback.print_exc()
      # Fallback на обычную генерацию продолжается ниже

  # НОВАЯ ЛОГИКА: Проверка времени перед генерацией
  if time.time() - start_time > max_time * 0.1:  # 10% времени на подготовку
    raise HTTPException(status_code=408, detail="Превышено время ожидания на этапе подготовки")

  # ОРИГИНАЛЬНАЯ ЛОГИКА: Генерация комбинаций
  generated = gen_func(df_history, optimized_params.num_combinations)
  combinations_response = [Combination(field1=f1, field2=f2, description=desc) for f1, f2, desc in generated]


  # RF прогноз - используем ТУ ЖЕ кэшированную модель
  rf_pred = None
  if time.time() - start_time < 0.8:  # Еще меньше времени для прогноза
    try:
      # ИСПРАВЛЕНИЕ: Используем правильную проверку модели
      if ai_model.GLOBAL_RF_MODEL.is_trained:
        last_draw = df_history.iloc[0]
        f1_pred, f2_pred = ai_model.GLOBAL_RF_MODEL.predict_next_combination(
          last_draw['Числа_Поле1_list'],
          last_draw['Числа_Поле2_list'],
          df_history  # ВАЖНО: передаем df_history, а не cached_df
        )
        if f1_pred and f2_pred:
          rf_pred = Combination(field1=f1_pred, field2=f2_pred, description="⚡ RF Sonic Prediction")
          print(f"✅ RF прогноз за {time.time() - start_time:.1f}с")
        else:
          print(f"❌ RF прогноз вернул пустые результаты")
      else:
        print(f"❌ RF модель не обучена для прогноза")
    except Exception as e:
      print(f"❌ RF prediction error: {e}")
      import traceback
      traceback.print_exc()
  else:
    print(f"⏰ Пропуск RF прогноза - недостаточно времени")

  # ОРИГИНАЛЬНАЯ ЛОГИКА: Прогноз LSTM + НОВАЯ: проверка времени и плана
  lstm_pred = None
  lstm_model = None

  # НОВАЯ ЛОГИКА: LSTM только для премиум планов или если достаточно времени
  time_for_lstm = time.time() - start_time < max_time - 5  # Больше запаса для LSTM
  lstm_allowed = user_plan in ['premium', 'pro'] or time_for_lstm

  if lstm_allowed:
    try:
      # ОРИГИНАЛЬНАЯ ЛОГИКА: Получение LSTM модели
      from backend.app.core.ai_model import GLOBAL_MODEL_MANAGER
      config = data_manager.get_current_config()
      lstm_model = ai_model.GLOBAL_MODEL_MANAGER.get_lstm_model(data_manager.CURRENT_LOTTERY, config)

      if lstm_model and lstm_model.is_trained and not df_history.empty:
        print(f"LSTM Predict: Начало генерации прогноза для {data_manager.CURRENT_LOTTERY}")

        # ОРИГИНАЛЬНАЯ ЛОГИКА: Проверка количества тиражей
        n_steps_needed = lstm_model.n_steps_in

        if len(df_history) >= n_steps_needed:
          # ОРИГИНАЛЬНАЯ ЛОГИКА: Подготовка данных для LSTM
          recent_draws = df_history.head(n_steps_needed)
          recent_draws_chronological = recent_draws.iloc[::-1]  # Разворачиваем

          print(f"LSTM Predict: Используем {len(recent_draws_chronological)} последних тиражей")
          print(
            f"LSTM Predict: Диапазон тиражей: #{recent_draws_chronological.iloc[0]['Тираж']} - #{recent_draws_chronological.iloc[-1]['Тираж']}")

          # НОВАЯ ЛОГИКА: Проверка времени перед LSTM предсказанием
          if time.time() - start_time < max_time - 5:  # 5 секунд запаса
            # ОРИГИНАЛЬНАЯ ЛОГИКА: Генерация LSTM прогноза
            pred_f1, pred_f2 = lstm_model.predict_next_combination(recent_draws_chronological)

            if pred_f1 and pred_f2 and len(pred_f1) > 0 and len(pred_f2) > 0:
              # ОРИГИНАЛЬНАЯ ЛОГИКА: Валидация размеров
              expected_f1_size = config['field1_size']
              expected_f2_size = config['field2_size']

              if len(pred_f1) == expected_f1_size and len(pred_f2) == expected_f2_size:
                lstm_pred = Combination(
                  field1=pred_f1,
                  field2=pred_f2,
                  description=f"LSTM Prediction (на основе {n_steps_needed} тиражей)"
                )
                print(f"LSTM Predict: Успешно сгенерирован прогноз: {pred_f1} | {pred_f2}")
                print(f"✅ LSTM прогноз сгенерирован за {time.time() - start_time:.1f}с")
              else:
                print(
                  f"LSTM Predict: Неверный размер прогноза. Ожидалось {expected_f1_size}+{expected_f2_size}, получено {len(pred_f1)}+{len(pred_f2)}")
            else:
              print(f"LSTM Predict: Модель вернула пустой или некорректный прогноз")
          else:
            print(f"⏰ LSTM прогноз пропущен - недостаточно времени ({time.time() - start_time:.1f}с)")
        else:
          print(
            f"LSTM Predict: Недостаточно данных для прогноза. Требуется {n_steps_needed} тиражей, доступно {len(df_history)}")
      else:
        if not lstm_model:
          print(f"LSTM Predict: Модель не найдена для {data_manager.CURRENT_LOTTERY}")
        elif not lstm_model.is_trained:
          print(f"LSTM Predict: Модель не обучена для {data_manager.CURRENT_LOTTERY}")
        else:
          print(f"LSTM Predict: Нет исторических данных")

    except Exception as e:
      print(f"LSTM Predict: Ошибка при генерации прогноза - {e}")
      import traceback
      traceback.print_exc()
      # Не возвращаем ошибку пользователю, просто прогноз будет None
  else:
    if not time_for_lstm:
      print(f"⏰ LSTM прогноз пропущен для базового плана - недостаточно времени")
    else:
      print(f"🔒 LSTM прогноз доступен только для премиум планов (текущий: {user_plan})")

  # НОВАЯ ЛОГИКА: Финальная проверка времени
  total_elapsed = time.time() - start_time
  print(f"📊 Генерация завершена за {total_elapsed:.1f}с (лимит: {max_time}с)")

  if total_elapsed > max_time:
    print(f"⚠️ Превышен лимит времени, но результат уже готов")

  # ОРИГИНАЛЬНАЯ ЛОГИКА: Возврат результата
  return GenerationResponse(
    combinations=combinations_response,
    rf_prediction=rf_pred,
    lstm_prediction=lstm_pred
  )


# БЕСПЛАТНЫЙ эндпоинт - демо версия
@router.post("/generate-demo", response_model=GenerationResponse, summary="🆓 Демо генерация (бесплатно)")
def generate_combinations_demo(
    context: None = Depends(set_lottery_context)
):
  """
  🆓 БЕСПЛАТНАЯ ДЕМО-ВЕРСИЯ: Генерирует 1 случайную комбинацию.

  **Ограничения:**
  - Только 1 комбинация
  - Только случайная генерация
  - Без AI прогнозов
  """
  # Простая генерация без AI
  f1, f2 = combination_generator.generate_random_combination()
  demo_combo = Combination(
    field1=f1,
    field2=f2,
    description="Демо: случайная комбинация"
  )

  return GenerationResponse(
    combinations=[demo_combo],
    rf_prediction=None,
    lstm_prediction=None
  )


@router.get("/trends", summary="📊 Анализ текущих трендов")
async def get_current_trends(
    context: None = Depends(set_lottery_context),
    current_user=Depends(require_basic)
):
  """
  🔒 ЗАЩИЩЕННАЯ ФУНКЦИЯ: Возвращает анализ текущих трендов

  **Требования:** Базовая подписка или выше

  **Возвращает:**
  - Горячие числа с ускорением
  - Холодные числа готовые к развороту
  - Числа с импульсом
  - Сдвиг паттерна
  - Рекомендации по генерации
  """
  try:
    from backend.app.core.trend_analyzer import GLOBAL_TREND_ANALYZER

    # Загружаем историю
    df_history = data_manager.fetch_draws_from_db()

    if df_history.empty:
      return {
        "status": "no_data",
        "message": "Недостаточно данных для анализа трендов",
        "trends": {}
      }

    # Анализируем тренды
    trends = GLOBAL_TREND_ANALYZER.analyze_current_trends(df_history)
    trend_summary = GLOBAL_TREND_ANALYZER.get_trend_summary(trends)

    # Формируем ответ
    response = {
      "status": "success",
      "lottery_type": data_manager.CURRENT_LOTTERY,
      "analyzed_draws": len(df_history),
      "summary": trend_summary,
      "trends": {}
    }

    # Детализация по полям
    for field_name, trend_data in trends.items():
      response["trends"][field_name] = {
        "hot_acceleration": trend_data.hot_acceleration,
        "cold_reversal": trend_data.cold_reversal,
        "momentum_numbers": trend_data.momentum_numbers,
        "pattern_shift": trend_data.pattern_shift,
        "confidence_score": round(trend_data.confidence_score, 2),
        "trend_strength": round(trend_data.trend_strength, 2)
      }

    # Рекомендации
    recommendations = []
    for field_name, trend_data in trends.items():
      field_num = field_name[-1]

      if trend_data.hot_acceleration:
        recommendations.append(
          f"Поле {field_num}: Включить горячие {trend_data.hot_acceleration[:3]}"
        )

      if trend_data.cold_reversal:
        recommendations.append(
          f"Поле {field_num}: Рассмотреть холодные {trend_data.cold_reversal[:2]}"
        )

    response["recommendations"] = recommendations
    response["timestamp"] = datetime.now().isoformat()

    return response

  except Exception as e:
    logger.error(f"Ошибка анализа трендов: {e}")
    raise HTTPException(status_code=500, detail="Ошибка анализа трендов")


@router.post("/evaluate-combination", summary="🎯 Оценка комбинации по трендам")
async def evaluate_combination_trends(
    field1: List[int] = Query(..., description="Числа первого поля"),
    field2: List[int] = Query(..., description="Числа второго поля"),
    context: None = Depends(set_lottery_context),
    current_user=Depends(require_basic)
):
  """
  🔒 ЗАЩИЩЕННАЯ ФУНКЦИЯ: Оценивает комбинацию на основе текущих трендов
  """
  try:
    from backend.app.core.trend_analyzer import GLOBAL_TREND_ANALYZER

    # Валидация
    config = data_manager.get_current_config()
    if (len(field1) != config['field1_size'] or
        len(field2) != config['field2_size']):
      raise HTTPException(
        status_code=400,
        detail=f"Неверное количество чисел. Требуется {config['field1_size']} и {config['field2_size']}"
      )

    # Загружаем историю и анализируем тренды
    df_history = data_manager.fetch_draws_from_db()
    trends = GLOBAL_TREND_ANALYZER.analyze_current_trends(df_history)

    # Оцениваем комбинацию
    metrics = GLOBAL_TREND_ANALYZER.evaluate_combination(field1, field2, trends)

    return {
      "combination": {
        "field1": field1,
        "field2": field2
      },
      "evaluation": {
        "trend_alignment": round(metrics.trend_alignment, 3),
        "momentum_score": round(metrics.momentum_score, 3),
        "pattern_resonance": round(metrics.pattern_resonance, 3),
        "risk_assessment": metrics.risk_assessment,
        "expected_performance": round(metrics.expected_performance, 3)
      },
      "recommendation": _get_combination_recommendation(metrics),
      "timestamp": datetime.now().isoformat()
    }

  except Exception as e:
    logger.error(f"Ошибка оценки комбинации: {e}")
    raise HTTPException(status_code=500, detail="Ошибка оценки комбинации")


@router.get("/model-status", summary="📊 Статус AI моделей")
def get_model_status(context: None = Depends(set_lottery_context)):
  """Возвращает статус обучения AI моделей для текущей лотереи"""
  try:
    from backend.app.core.ai_model import GLOBAL_MODEL_MANAGER
    from backend.app.core import data_manager

    current_lottery = data_manager.CURRENT_LOTTERY
    config = data_manager.get_current_config()

    # Получаем модели
    rf_model = GLOBAL_MODEL_MANAGER.get_rf_model(current_lottery, config)
    lstm_model = GLOBAL_MODEL_MANAGER.get_lstm_model(current_lottery, config)

    # Статус данных
    df = data_manager.fetch_draws_from_db()
    data_count = len(df)
    limits = data_manager.get_lottery_limits()

    return {
      "lottery_type": current_lottery,
      "data_status": {
        "draws_count": data_count,
        "min_required": limits['min_for_training'],
        "has_enough_data": data_count >= limits['min_for_training']
      },
      "models_status": {
        "rf_trained": rf_model.is_trained if rf_model else False,
        "lstm_trained": lstm_model.is_trained if lstm_model else False
      },
      "last_draws_sample": df.head(3).to_dict('records') if not df.empty else []
    }

  except Exception as e:
    raise HTTPException(status_code=500, detail=f"Ошибка получения статуса: {str(e)}")


def _get_combination_recommendation(metrics: 'CombinationMetrics') -> str:
  """Генерирует рекомендацию на основе метрик"""
  if metrics.expected_performance >= 0.8:
    return "🟢 Отличная комбинация! Высокое соответствие трендам"
  elif metrics.expected_performance >= 0.6:
    return "🟡 Хорошая комбинация. Умеренное соответствие трендам"
  elif metrics.expected_performance >= 0.4:
    return "🟠 Средняя комбинация. Частичное соответствие трендам"
  else:
    return "🔴 Слабая комбинация. Низкое соответствие трендам"

# ДОБАВЬТЕ также GET версию для совместимости с тестами:
@router.get("/generate-demo", response_model=GenerationResponse, summary="🆓 Демо генерация GET (совместимость)")
def generate_combinations_demo_get(
    context: None = Depends(set_lottery_context)
):
  """GET версия демо генерации для обратной совместимости с тестами"""
  return generate_combinations_demo(context)


@router.post("/generate-turbo", response_model=GenerationResponse, summary="⚡ ТУРБО генерация (максимальная скорость)")
def generate_combinations_turbo(
    params: GenerationParams,
    context: None = Depends(set_lottery_context),
    current_user=Depends(require_basic)
):
  """
  ⚡ ТУРБО РЕЖИМ: Максимально быстрая генерация с использованием всех ядер CPU

  **Оптимизации:**
  - Параллельная обработка на всех ядрах
  - Оптимизация памяти
  - Минимальное количество кандидатов
  - Агрессивные таймауты
  """
  import time
  from backend.app.core.memory_optimizer import MEMORY_OPTIMIZER

  start_time = time.time()

  # Получаем план пользователя
  user_plan = "basic"
  if hasattr(current_user, 'preferences') and current_user.preferences:
    user_plan = current_user.preferences.get('subscription_plan', 'basic')

  print(f"⚡ ТУРБО режим для '{user_plan}' - используем ВСЕ ядра CPU!")

  # Сбор статистики памяти
  memory_before = MEMORY_OPTIMIZER.get_memory_stats()

  # Загружаем и оптимизируем историю
  df_history = data_manager.fetch_draws_from_db()
  if df_history.empty:
    return GenerationResponse(combinations=[], rf_prediction=None, lstm_prediction=None)

  # Турбо генерация только для RF
  try:
    if params.generator_type == 'rf_ranked':
      # Минимальное количество кандидатов для турбо режима
      turbo_candidates = min(30, params.num_combinations * 10)
      generated = combination_generator.generate_rf_ranked_combinations(
        df_history,
        params.num_combinations,
        turbo_candidates
      )
    else:
      # Для других типов - быстрая генерация без RF оценки
      generated = combination_generator.generate_pattern_based_combinations(
        df_history,
        params.num_combinations,
        params.generator_type if params.generator_type in ['hot', 'cold', 'balanced'] else 'balanced'
      )

    combinations_response = [Combination(field1=f1, field2=f2, description=f"⚡{desc}") for f1, f2, desc in generated]

  except Exception as e:
    print(f"Турбо генерация ошибка: {e}")
    # Супер быстрый fallback
    fallback_combos = []
    for i in range(params.num_combinations):
      f1, f2 = combination_generator.generate_random_combination()
      fallback_combos.append(Combination(
        field1=f1,
        field2=f2,
        description=f"⚡Турбо #{i + 1}"
      ))
    combinations_response = fallback_combos

  # Только быстрые прогнозы (без долгих операций)
  rf_pred = None
  lstm_pred = None

  # RF прогноз только если модель УЖЕ обучена и время < 3 сек
  if time.time() - start_time < 3:
    try:
      # ИСПРАВЛЕНИЕ: Используем правильную проверку
      if ai_model.GLOBAL_RF_MODEL.is_trained:
        last_draw = df_history.iloc[0]
        f1_pred, f2_pred = ai_model.GLOBAL_RF_MODEL.predict_next_combination(
          last_draw['Числа_Поле1_list'],
          last_draw['Числа_Поле2_list'],
          df_history
        )
        if f1_pred and f2_pred:
          rf_pred = Combination(field1=f1_pred, field2=f2_pred, description="⚡ RF Turbo")
    except Exception as e:
      print(f"❌ Турбо RF ошибка: {e}")

  # Очистка памяти
  MEMORY_OPTIMIZER.cleanup_memory()
  memory_after = MEMORY_OPTIMIZER.get_memory_stats()

  elapsed = time.time() - start_time
  print(f"⚡ ТУРБО завершен за {elapsed:.1f}с")
  print(f"📊 Память: {memory_before['current_mb']:.1f}МБ → {memory_after['current_mb']:.1f}МБ")

  return GenerationResponse(
    combinations=combinations_response,
    rf_prediction=rf_pred,
    lstm_prediction=lstm_pred
  )


def _generate_turbo_field(field_trends, field_num):
  """Быстрая генерация поля для турбо-режима"""
  from backend.app.core.data_manager import get_current_config
  import random

  config = get_current_config()
  field_size = config[f'field{field_num}_size']
  field_max = config[f'field{field_num}_max']

  if not field_trends:
    return sorted(random.sample(range(1, field_max + 1), field_size))

  combination = []

  # Добавляем 1-2 горячих числа
  if hasattr(field_trends, 'hot_acceleration') and field_trends.hot_acceleration:
    # ИСПРАВЛЕНИЕ: Принудительно конвертируем в список
    hot_list = list(field_trends.hot_acceleration) if field_trends.hot_acceleration else []
    hot_count = min(2, len(hot_list), field_size)
    if hot_count > 0:
      combination.extend(hot_list[:hot_count])

  # Добавляем 1 число с импульсом
  if (len(combination) < field_size and
      hasattr(field_trends, 'momentum_numbers') and
      field_trends.momentum_numbers):

    # ИСПРАВЛЕНИЕ: Принудительно конвертируем в список
    momentum_list = list(field_trends.momentum_numbers) if field_trends.momentum_numbers else []
    if momentum_list:
      momentum_pick = momentum_list[0]
      if momentum_pick not in combination:
        combination.append(momentum_pick)

  # Дополняем случайными
  available = [n for n in range(1, field_max + 1) if n not in combination]
  needed = field_size - len(combination)

  if needed > 0 and available:
    combination.extend(random.sample(available, min(needed, len(available))))

  # Гарантируем правильный размер
  while len(combination) < field_size:
    all_nums = list(range(1, field_max + 1))
    missing = [n for n in all_nums if n not in combination]
    if missing:
      combination.append(random.choice(missing))
    else:
      break

  return sorted(combination[:field_size])