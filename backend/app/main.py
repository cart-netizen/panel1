import asyncio

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from backend.app.core.async_ai_model import ASYNC_MODEL_MANAGER
from backend.app.api import generation, analysis, verification, strategies, patterns, data_management, auth, subscriptions

from backend.app.core.data_manager import get_lottery_limits
from backend.app.core.lottery_context import LotteryContext
#
# @asynccontextmanager
# async def lifespan(app: FastAPI):
#   """
#   Жизненный цикл приложения с правильной инициализацией каждой лотереи.
#   Вариант A: изолированная обработка каждой лотереи.
#   """
#   print("🚀 Запуск приложения: Инициализация данных и ML моделей...")
#
#   # ИСПРАВЛЕННЫЕ ИМПОРТЫ
#   from backend.app.core import data_manager, ai_model
#   from backend.app.core.lottery_context import LotteryContext
#
#   # Статистика инициализации
#   initialization_stats = {
#     'total_lotteries': len(data_manager.LOTTERY_CONFIGS),
#     'successful_lotteries': 0,
#     'failed_lotteries': 0,
#     'details': {}
#   }
#
#   # Инициализируем данные и модели для каждой лотереи (Вариант A)
#   for lottery_type, config in data_manager.LOTTERY_CONFIGS.items():
#     print(f"\n📊 Инициализация лотереи: {lottery_type}")
#     lottery_stats = {
#       'db_initialized': False,
#       'data_loaded': False,
#       'models_trained': False,
#       'draws_count': 0,
#       'error': None
#     }
#
#     try:
#       # Устанавливаем контекст текущей лотереи
#       with LotteryContext(lottery_type):
#         print(f"   🔧 Контекст установлен для {lottery_type}")
#
#         limits = get_lottery_limits()
#         print(f"   📋 Лимиты: макс_БД={limits['max_draws_in_db']}, "
#               f"начальная_загрузка={limits['initial_fetch']}, "
#               f"мин_для_обучения={limits['min_for_training']}")
#
#         # 1. Инициализация базы данных и таблиц
#         try:
#           data_manager.init_db()
#           lottery_stats['db_initialized'] = True
#           print(f"   ✅ БД инициализирована для {lottery_type}")
#         except Exception as e:
#           raise Exception(f"Ошибка инициализации БД: {e}")
#
#         # 2. Проверка наличия данных в БД
#         df = data_manager.fetch_draws_from_db()
#         lottery_stats['draws_count'] = len(df)
#
#         # Получаем лимиты для проверки достаточности данных
#         limits = get_lottery_limits()
#         min_required = limits['min_for_training']
#         target_initial = limits['initial_fetch']
#
#         if df.empty:
#           print(f"   📥 БД пуста для {lottery_type}, загружаем данные из API...")
#           try:
#             data_manager.update_database_from_source()
#             df = data_manager.fetch_draws_from_db()
#             lottery_stats['draws_count'] = len(df)
#             if not df.empty:
#               lottery_stats['data_loaded'] = True
#               print(f"   ✅ Загружено {len(df)} тиражей для {lottery_type}")
#             else:
#               print(f"   ⚠️  Не удалось загрузить данные для {lottery_type}")
#           except Exception as e:
#             print(f"   ❌ Ошибка загрузки данных для {lottery_type}: {e}")
#             # Продолжаем без данных
#         elif len(df) < min_required:
#           print(f"   📊 Найдено {len(df)} тиражей в БД для {lottery_type}")
#           print(f"   📥 Недостаточно для качественного обучения, догружаем из API...")
#           lottery_stats['data_loaded'] = True  # Данные есть, но мало
#
#           try:
#             # Принудительно загружаем исторические данные
#             print(f"   🔄 Целевое количество: {target_initial} тиражей")
#             df_updated = data_manager.smart_historical_load_with_pagination(target_initial)
#
#             if len(df_updated) > len(df):
#               additional = len(df_updated) - len(df)
#               df = df_updated
#               lottery_stats['draws_count'] = len(df)
#               print(f"   ✅ Догружено +{additional} тиражей, итого: {len(df)} для {lottery_type}")
#
#               if len(df) >= min_required:
#                 print(f"   🎯 Достигнуто минимальное количество для качественного обучения!")
#             else:
#               print(f"   💤 Новых тиражей не найдено, остается {len(df)} тиражей")
#
#           except Exception as e:
#             print(f"   ❌ Ошибка догрузки данных для {lottery_type}: {e}")
#             # Продолжаем с имеющимися данными
#         else:
#           lottery_stats['data_loaded'] = True
#           print(f"   ✅ Найдено {len(df)} тиражей в БД для {lottery_type} (достаточно)")
#
#         # 3. Проверка минимального количества данных и обучение моделей
#         if len(df) >= min_required:
#           try:
#             print(f"   🧠 Обучение AI моделей для {lottery_type} ({len(df)} тиражей)...")
#
#             # Получаем модели для этой лотереи
#             rf_model = ai_model.GLOBAL_MODEL_MANAGER.get_rf_model(lottery_type, config)
#             lstm_model = ai_model.GLOBAL_MODEL_MANAGER.get_lstm_model(lottery_type, config)
#
#             # Обучаем RF модель
#             rf_model.train(df)
#             rf_trained = rf_model.is_trained
#
#             # Обучаем LSTM модель
#             try:
#               lstm_model.train(df)
#               lstm_trained = lstm_model.is_trained
#             except Exception as e:
#               print(f"   ⚠️  LSTM модель для {lottery_type} не обучена: {e}")
#               lstm_trained = False
#
#             if rf_trained:
#               lottery_stats['models_trained'] = True
#               print(f"   ✅ RF модель обучена для {lottery_type}")
#               if lstm_trained:
#                 print(f"   ✅ LSTM модель обучена для {lottery_type}")
#               else:
#                 print(f"   ⚠️  Только RF модель работает для {lottery_type}")
#             else:
#               print(f"   ❌ Модели не обучены для {lottery_type}")
#
#           except Exception as e:
#             print(f"   ❌ Ошибка обучения моделей для {lottery_type}: {e}")
#             lottery_stats['error'] = str(e)
#
#         elif len(df) > 0:
#           print(f"   ⚠️  Недостаточно данных для качественного обучения {lottery_type}")
#           print(f"   📊 Доступно: {len(df)} тиражей, требуется минимум: {min_required}")
#           print(f"   💡 Рекомендация: загрузить больше исторических данных")
#
#           # Попытаемся обучить хотя бы с минимальными данными (только RF)
#           if len(df) >= 30:  # Абсолютный минимум
#             try:
#               print(f"   🔬 Попытка обучения с минимальными данными...")
#               rf_model = ai_model.GLOBAL_MODEL_MANAGER.get_rf_model(lottery_type, config)
#               rf_model.train(df)
#               if rf_model.is_trained:
#                 lottery_stats['models_trained'] = True
#                 print(f"   ⚠️  RF модель обучена с ограниченными данными для {lottery_type}")
#             except Exception as e:
#               print(f"   ❌ Даже минимальное обучение не удалось: {e}")
#         else:
#           print(f"   ❌ Нет данных для обучения моделей {lottery_type}")
#
#       # Успешная инициализация лотереи
#       initialization_stats['successful_lotteries'] += 1
#       initialization_stats['details'][lottery_type] = lottery_stats
#       print(f"   🎯 Лотерея {lottery_type} инициализирована успешно")
#
#     except Exception as e:
#       # Ошибка инициализации лотереи
#       initialization_stats['failed_lotteries'] += 1
#       lottery_stats['error'] = str(e)
#       initialization_stats['details'][lottery_type] = lottery_stats
#       print(f"   💥 Ошибка инициализации {lottery_type}: {e}")
#       # Продолжаем с другими лотереями
#
#   # Итоговая статистика
#   print(f"\n📈 Итоги инициализации:")
#   print(f"   Всего лотерей: {initialization_stats['total_lotteries']}")
#   print(f"   Успешно: {initialization_stats['successful_lotteries']}")
#   print(f"   С ошибками: {initialization_stats['failed_lotteries']}")
#
#   # Детальная статистика по каждой лотерее
#   for lottery_type, stats in initialization_stats['details'].items():
#     status = "✅" if not stats.get('error') else "❌"
#     models_status = "✅" if stats['models_trained'] else ("⚠️" if stats['draws_count'] > 0 else "❌")
#
#     print(f"   {status} {lottery_type}: БД={stats['db_initialized']}, "
#           f"Данные={stats['data_loaded']} ({stats['draws_count']} тиражей), "
#           f"Модели={models_status}")
#
#     if stats.get('error'):
#       print(f"      ⚠️ Ошибка: {stats['error']}")
#     elif stats['draws_count'] > 0 and not stats['models_trained']:
#       limits = data_manager.LOTTERY_DATA_LIMITS.get(lottery_type, {})
#       min_req = limits.get('min_for_training', 200)
#       print(f"      💡 Нужно еще {min_req - stats['draws_count']} тиражей для полноценного обучения")
#
#   if initialization_stats['successful_lotteries'] > 0:
#     print(f"\n🎉 Приложение готово к работе!")
#     print(f"   Доступно лотерей: {initialization_stats['successful_lotteries']}")
#   else:
#     print(f"\n⚠️  Приложение запущено, но лотереи могут работать некорректно!")
#
#   # Сохраняем статистику в глобальную переменную для мониторинга
#   if hasattr(app, 'state'):
#     app.state.initialization_stats = initialization_stats
#   else:
#     # Для ранней стадии инициализации сохраняем в модуль
#     from backend.app.core import data_manager
#     data_manager.LAST_INITIALIZATION_STATS = initialization_stats
#
#   # Запуск автоматического планировщика обновлений
#   try:
#     from backend.app.core.ai_model import GLOBAL_AUTO_UPDATE_SCHEDULER
#     await GLOBAL_AUTO_UPDATE_SCHEDULER.start_scheduler()
#     print(f"\n🕐 Автоматический планировщик запущен")
#     print(f"   📅 4x20: проверка через 5 мин после тиражей (10:00, 12:00, 13:00, 16:00, 18:00, 20:00, 22:00)")
#     print(f"   📅 5x36plus: проверка каждые 15 мин + 2 мин задержка")
#   except ImportError as e:
#     print(f"⚠️ Модуль планировщика недоступен (возможно, отсутствует pytz): {e}")
#   except Exception as e:
#     print(f"⚠️ Ошибка запуска планировщика: {e}")
#
#   yield
#
#   # Остановка планировщика
#   try:
#     from backend.app.core.ai_model import GLOBAL_AUTO_UPDATE_SCHEDULER
#     await GLOBAL_AUTO_UPDATE_SCHEDULER.stop_scheduler()
#   except (ImportError, AttributeError):
#     pass  # Планировщик не был запущен
#   except Exception as e:
#     print(f"⚠️ Ошибка остановки планировщика: {e}")
#
#   # Код при остановке приложения
#   print("\n🛑 Остановка приложения...")
#   print("   Сохранение состояния моделей завершено.")
@asynccontextmanager
async def lifespan(app: FastAPI):
  """
  Жизненный цикл приложения с правильной инициализацией каждой лотереи.
  """
  print("🚀 Запуск приложения: Инициализация данных и ML моделей...")

  # Импорты
  from backend.app.core import data_manager, ai_model
  from backend.app.core.lottery_context import LotteryContext

  # Статистика инициализации
  initialization_stats = {
    'total_lotteries': len(data_manager.LOTTERY_CONFIGS),
    'successful_lotteries': 0,
    'failed_lotteries': 0,
    'details': {}
  }

  # Инициализируем данные и модели для каждой лотереи
  for lottery_type, config in data_manager.LOTTERY_CONFIGS.items():
    print(f"\n📊 Инициализация лотереи: {lottery_type}")
    lottery_stats = {
      'db_initialized': False,
      'data_loaded': False,
      'models_trained': False,
      'draws_count': 0,
      'error': None
    }

    try:
      # Устанавливаем контекст текущей лотереи
      with LotteryContext(lottery_type):
        print(f"   🔧 Контекст установлен для {lottery_type}")

        limits = get_lottery_limits()
        print(f"   📋 Лимиты: макс_БД={limits['max_draws_in_db']}, "
              f"начальная_загрузка={limits['initial_fetch']}, "
              f"мин_для_обучения={limits['min_for_training']}")

        # 1. Инициализация базы данных и таблиц
        try:
          data_manager.init_db()
          lottery_stats['db_initialized'] = True
          print(f"   ✅ БД инициализирована для {lottery_type}")
        except Exception as e:
          raise Exception(f"Ошибка инициализации БД: {e}")

        # 2. Проверка наличия данных в БД
        df = data_manager.fetch_draws_from_db()
        lottery_stats['draws_count'] = len(df)

        # Получаем лимиты для проверки достаточности данных
        limits = get_lottery_limits()
        min_required = limits['min_for_training']

        if len(df) >= min_required:
          lottery_stats['data_loaded'] = True
          print(f"   ✅ Найдено {len(df)} тиражей в БД для {lottery_type} (достаточно)")

          # 3. Обучение моделей
          try:
            print(f"   🧠 Обучение AI моделей для {lottery_type} ({len(df)} тиражей)...")

            # Получаем модели для этой лотереи
            rf_model = ai_model.GLOBAL_MODEL_MANAGER.get_rf_model(lottery_type, config)
            lstm_model = ai_model.GLOBAL_MODEL_MANAGER.get_lstm_model(lottery_type, config)

            # Обучаем RF модель
            rf_model.train(df)
            rf_trained = rf_model.is_trained

            # Обучаем LSTM модель
            try:
              lstm_model.train(df)
              lstm_trained = lstm_model.is_trained
            except Exception as e:
              print(f"   ⚠️  LSTM модель для {lottery_type} не обучена: {e}")
              lstm_trained = False

            if rf_trained:
              lottery_stats['models_trained'] = True
              print(f"   ✅ RF модель обучена для {lottery_type}")
              print(f"   🔥 Прогрев RF кэша...")
              from backend.app.core.combination_generator import generate_random_combination
              for _ in range(10):  # Прогреваем 10 случайными комбинациями
                f1, f2 = generate_random_combination()
                rf_model.score_combination(sorted(f1), sorted(f2), df)
              print(f"   ⚡ RF кэш прогрет")
              if lstm_trained:
                print(f"   ✅ LSTM модель обучена для {lottery_type}")
              else:
                print(f"   ⚠️  Только RF модель работает для {lottery_type}")
            else:
              print(f"   ❌ Модели не обучены для {lottery_type}")

          except Exception as e:
            print(f"   ❌ Ошибка обучения моделей для {lottery_type}: {e}")
            lottery_stats['error'] = str(e)
        else:
          lottery_stats['data_loaded'] = False
          print(f"   ⚠️  Недостаточно данных для {lottery_type}: {len(df)} < {min_required}")

      # Успешная инициализация лотереи
      initialization_stats['successful_lotteries'] += 1
      initialization_stats['details'][lottery_type] = lottery_stats
      print(f"   🎯 Лотерея {lottery_type} инициализирована успешно")

    except Exception as e:
      # Ошибка инициализации лотереи
      initialization_stats['failed_lotteries'] += 1
      lottery_stats['error'] = str(e)
      initialization_stats['details'][lottery_type] = lottery_stats
      print(f"   💥 Ошибка инициализации {lottery_type}: {e}")

  # Итоговая статистика
  print(f"\n📈 Итоги инициализации:")
  print(f"   Всего лотерей: {initialization_stats['total_lotteries']}")
  print(f"   Успешно: {initialization_stats['successful_lotteries']}")
  print(f"   С ошибками: {initialization_stats['failed_lotteries']}")

  if initialization_stats['successful_lotteries'] > 0:
    print(f"\n🎉 Приложение готово к работе!")
    print(f"   Доступно лотерей: {initialization_stats['successful_lotteries']}")
  else:
    print(f"\n⚠️  Приложение запущено, но лотереи могут работать некорректно!")

  # Запуск автоматического планировщика
  scheduler_task = None
  try:
    from backend.app.core.ai_model import GLOBAL_AUTO_UPDATE_SCHEDULER
    scheduler_task = asyncio.create_task(GLOBAL_AUTO_UPDATE_SCHEDULER.start_scheduler())
    print(f"\n🕐 Автоматический планировщик запущен")
  except ImportError as e:
    print(f"⚠️ Модуль планировщика недоступен: {e}")
  except Exception as e:
    print(f"⚠️ Ошибка запуска планировщика: {e}")

  yield

  # ИСПРАВЛЕНИЕ: Корректная остановка
  print("\n🛑 Остановка приложения...")

  # Останавливаем планировщик
  if scheduler_task and not scheduler_task.done():
    try:
      from backend.app.core.ai_model import GLOBAL_AUTO_UPDATE_SCHEDULER
      await GLOBAL_AUTO_UPDATE_SCHEDULER.stop_scheduler()
      scheduler_task.cancel()
      try:
        await scheduler_task
      except asyncio.CancelledError:
        pass
      print("   ✅ Планировщик остановлен")
    except Exception as e:
      print(f"   ⚠️ Ошибка остановки планировщика: {e}")

  print("   ✅ Приложение корректно остановлено")


async def _background_initial_training(lottery_type: str, config: dict):
  """Фонов  ое первичное обучение"""
  try:
    from backend.app.core.async_data_manager import ASYNC_DATA_MANAGER

    # Загружаем данные
    df = await ASYNC_DATA_MANAGER.fetch_draws_async(lottery_type)

    if len(df) > 50:  # Минимум для обучения
      await ASYNC_MODEL_MANAGER.train_models_background(lottery_type, df, config)
      print(f"✅ Фоновое обучение {lottery_type} завершено")
    else:
      print(f"⚠️ Недостаточно данных для {lottery_type}")

  except Exception as e:
    print(f"❌ Ошибка фонового обучения {lottery_type}: {e}")
app = FastAPI(
  title="Lottery Analysis API",
  description="REST API для анализа лотерей, генерации комбинаций и симуляции стратегий.",
  version="1.0.0",
  lifespan=lifespan
)

# Настройка CORS для разрешения запросов от фронтенда
app.add_middleware(
  CORSMiddleware,
  allow_origins=["*"],  # В продакшене укажите домен вашего фронтенда
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
)

# Подключаем роутеры
# Путь будет выглядеть как /api/v1/{lottery_type}/generate
app.include_router(generation.router, prefix="/api/v1/{lottery_type}", tags=["1. Generation & Predictions"])
app.include_router(analysis.router, prefix="/api/v1/{lottery_type}", tags=["2. Analysis & History"])
app.include_router(patterns.router, prefix="/api/v1/{lottery_type}", tags=["3. Pattern Analysis"])
app.include_router(verification.router, prefix="/api/v1/{lottery_type}", tags=["4. Ticket Verification"])
app.include_router(strategies.router, prefix="/api/v1/{lottery_type}", tags=["5. Strategies & Simulation"])
app.include_router(data_management.router, prefix="/api/v1/{lottery_type}", tags=["6. Data Management"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["0. Authentication"])
app.include_router(subscriptions.router, prefix="/api/v1/subscriptions", tags=["💰 Subscriptions"])


@app.get("/", summary="Корневой эндпоинт")
def read_root():
  return {"message": "Welcome to the Lottery Analysis API. Visit /docs for documentation."}