import asyncio
import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from fastapi.openapi.utils import get_openapi

from backend.app.core.async_ai_model import ASYNC_MODEL_MANAGER
from backend.app.api import generation, analysis, verification, strategies, patterns, data_management, auth, subscriptions, dashboard

from backend.app.core.data_manager import get_lottery_limits
from backend.app.core.lottery_context import LotteryContext
from backend.app.core.cache_manager import CACHE_MANAGER, logger
from backend.app.api import user_preferences
from backend.app.api import analysis_tools, simulation_tools
from backend.app.api import xgboost_api_endpoints
from backend.app.api import validation_routes
from backend.app.api import genetic_routes
from backend.app.core.rl.rl_generator import GLOBAL_RL_MANAGER
from backend.app.core.rl.environment import LotteryEnvironment
from backend.app.api import rl_router
from backend.app.api import timeseries_routes
from backend.app.api import bayesian_routes


@asynccontextmanager
async def lifespan(app: FastAPI):
  """
  Жизненный цикл приложения с правильной инициализацией каждой лотереи.
  """
  print(" Запуск приложения: Инициализация данных и ML моделей...")

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
    print(f"\n Инициализация лотереи: {lottery_type}")
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
        print(f"   [CONTEXT] Контекст установлен для {lottery_type}")

        limits = get_lottery_limits()
        print(f"   [LIMITS] Лимиты: макс_БД={limits['max_draws_in_db']}, "
              f"начальная_загрузка={limits['initial_fetch']}, "
              f"мин_для_обучения={limits['min_for_training']}")

        # 1. Инициализация базы данных и таблиц
        try:
          data_manager.init_db()
          lottery_stats['db_initialized'] = True
          print(f"   [OK] БД инициализирована для {lottery_type}")
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
          print(f"   [OK] Найдено {len(df)} тиражей в БД для {lottery_type} (достаточно)")

          # 3. Обучение моделей
          try:
            print(f"   [AI] Обучение AI моделей для {lottery_type} ({len(df)} тиражей)...")

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
              print(f"   [WARN]  LSTM модель для {lottery_type} не обучена: {e}")
              lstm_trained = False

            if rf_trained:
              lottery_stats['models_trained'] = True
              print(f"   [OK] RF модель обучена для {lottery_type}")
              print(f"   [CACHE] Прогрев RF кэша...")
              from backend.app.core.combination_generator import generate_random_combination
              for _ in range(10):  # Прогреваем 10 случайными комбинациями
                f1, f2 = generate_random_combination()
                rf_model.score_combination(sorted(f1), sorted(f2), df)
              print(f"   [READY] RF кэш прогрет")
              if lstm_trained:
                print(f"   [OK] LSTM модель обучена для {lottery_type}")
              else:
                print(f"   [WARN]  Только RF модель работает для {lottery_type}")
            else:
              print(f"   [FAIL] Модели не обучены для {lottery_type}")

            # 4. Обучение XGBoost моделей
            try:
              print(f"   [AI] Обучение XGBoost моделей для {lottery_type}...")

              from backend.app.core.xgboost_model import GLOBAL_XGBOOST_MANAGER

              # Получаем XGBoost модель
              xgb_model = GLOBAL_XGBOOST_MANAGER.get_model(lottery_type, config)

              # Обучаем XGBoost
              xgb_trained = xgb_model.train(df)

              if xgb_trained:
                lottery_stats['xgboost_trained'] = True
                print(f"   [OK] XGBoost модель обучена для {lottery_type}")

                # Получаем метрики
                xgb_metrics = xgb_model.get_metrics()
                if xgb_metrics.get('roc_auc'):
                  avg_auc = sum(xgb_metrics['roc_auc']) / len(xgb_metrics['roc_auc'])
                  print(f"   [XGB] Средний ROC-AUC: {avg_auc:.3f}")
              else:
                print(f"   [WARN] XGBoost модель не обучена для {lottery_type}")

            except Exception as e:
              print(f"   [WARN] Ошибка обучения XGBoost для {lottery_type}: {e}")
              lottery_stats['xgboost_error'] = str(e)


          except Exception as e:
            print(f"   [FAIL] Ошибка обучения моделей для {lottery_type}: {e}")
            lottery_stats['error'] = str(e)
        else:
          lottery_stats['data_loaded'] = False
          print(f"   [WARN]  Недостаточно данных для {lottery_type}: {len(df)} < {min_required}")

      # Успешная инициализация лотереи
      initialization_stats['successful_lotteries'] += 1
      initialization_stats['details'][lottery_type] = lottery_stats
      print(f"   [SUCCESS] Лотерея {lottery_type} инициализирована успешно")

    except Exception as e:
      # Ошибка инициализации лотереи
      initialization_stats['failed_lotteries'] += 1
      lottery_stats['error'] = str(e)
      initialization_stats['details'][lottery_type] = lottery_stats
      print(f"   [ERROR] Ошибка инициализации {lottery_type}: {e}")

  # Итоговая статистика
  print(f"\n[STATS] Итоги инициализации:")
  print(f"   Всего лотерей: {initialization_stats['total_lotteries']}")
  print(f"   Успешно: {initialization_stats['successful_lotteries']}")
  print(f"   С ошибками: {initialization_stats['failed_lotteries']}")

  if initialization_stats['successful_lotteries'] > 0:
    print(f"\n[SUCCESS] Приложение готово к работе!")
    # Статистика XGBoost
    xgb_stats = GLOBAL_XGBOOST_MANAGER.get_all_metrics()
    if xgb_stats:
      print(f"\n[XGBOOST] Статистика моделей:")
      for lottery_type, metrics in xgb_stats.items():
        if metrics.get('roc_auc'):
          avg_auc = sum(metrics['roc_auc']) / len(metrics['roc_auc'])
          print(f"   {lottery_type}: ROC-AUC={avg_auc:.3f}, время обучения={metrics.get('training_time', 0):.1f}с")
    print(f"   Доступно лотерей: {initialization_stats['successful_lotteries']}")
  else:
    print(f"\n[WARN]  Приложение запущено, но лотереи могут работать некорректно!")

  # =====================================
  # ИНИЦИАЛИЗАЦИЯ RL АГЕНТОВ
  # =====================================
  print(f"\n[RL] Инициализация Reinforcement Learning агентов...")

  rl_stats = {
    'total_agents': 0,
    'loaded_agents': 0,
    'errors': []
  }

  for lottery_type, config in data_manager.LOTTERY_CONFIGS.items():
    try:
      print(f"   [RL] Проверка агентов для {lottery_type}...")

      # Получаем RL генератор
      from backend.app.core.rl.rl_generator import GLOBAL_RL_MANAGER
      generator = GLOBAL_RL_MANAGER.get_generator(lottery_type, config)

      rl_stats['total_agents'] += 2  # Q-agent и DQN

      # Пытаемся загрузить сохраненные модели
      if generator.load_models():
        if generator.q_trained:
          print(f"   [OK] Q-Learning агент загружен для {lottery_type}")
          print(f"       Эпизодов: {generator.q_agent.total_episodes}, "
                f"Q-таблица: {generator.q_agent._get_q_table_size()} записей")
          rl_stats['loaded_agents'] += 1

        if generator.dqn_trained:
          print(f"   [OK] DQN агент загружен для {lottery_type}")
          print(f"       Эпизодов: {generator.dqn_agent.total_episodes}, "
                f"Память: {len(generator.dqn_agent.memory)} записей")
          rl_stats['loaded_agents'] += 1
      else:
        print(f"   [INFO] RL агенты для {lottery_type} не обучены (требуется обучение)")

    except Exception as e:
      print(f"   [WARN] Ошибка инициализации RL для {lottery_type}: {e}")
      rl_stats['errors'].append(str(e))

  print(f"\n[RL STATS] Итоги инициализации RL:")
  print(f"   Всего агентов: {rl_stats['total_agents']}")
  print(f"   Загружено: {rl_stats['loaded_agents']}")
  if rl_stats['errors']:
    print(f"   Ошибок: {len(rl_stats['errors'])}")

  # Загрузка свежих данных при запуске
  print(f"\n[DATA] Автоматическая загрузка свежих данных при запуске...")
  last_update_times = {}
  try:
    from backend.app.core.async_data_manager import ASYNC_DATA_MANAGER

    # Параллельно обновляем данные всех лотерей
    update_results = await ASYNC_DATA_MANAGER.parallel_update_all_lotteries()

    # Сохраняем время последнего обновления для каждой лотереи
    from datetime import datetime
    for lottery_type, updated in update_results.items():
      if updated:
        last_update_times[lottery_type] = datetime.now()
      status = "обновлены" if updated else "актуальны"
      print(f"   [DATA] {lottery_type}: {status}")

    print(f"[DATA] Автоматическое обновление завершено")
    
  except Exception as e:
    print(f"[WARN] Ошибка автообновления данных: {e}")

  # Запуск автоматического планировщика
  scheduler_task = None
  try:
    from backend.app.core.async_scheduler import GLOBAL_ASYNC_SCHEDULER
    # Передаем время последних обновлений, чтобы планировщик не дублировал
    GLOBAL_ASYNC_SCHEDULER.set_last_update_times(last_update_times)
    await GLOBAL_ASYNC_SCHEDULER.start_async_scheduler()
    print(f"\n[SCHEDULER] Асинхронный планировщик запущен")

    # Инициализация кэша последних тиражей
    logger.info("📦 Инициализация кэша...")
    CACHE_MANAGER.update_all_last_draws()

  except ImportError as e:
    print(f"[WARN] Модуль планировщика недоступен: {e}")
  except Exception as e:
    print(f"[WARN] Ошибка запуска планировщика: {e}")

  yield

  # ИСПРАВЛЕНИЕ: Корректная остановка
  print("\n[STOP] Остановка приложения...")

  # Останавливаем планировщик
  try:
    from backend.app.core.async_scheduler import GLOBAL_ASYNC_SCHEDULER
    await GLOBAL_ASYNC_SCHEDULER.stop_async_scheduler()
    print("   [OK] Планировщик остановлен")
  except Exception as e:
    print(f"   [WARN] Ошибка остановки планировщика: {e}")

  try:
    from backend.app.core.rl.rl_generator import GLOBAL_RL_MANAGER
    for lottery_type in data_manager.LOTTERY_CONFIGS.keys():
      generator = GLOBAL_RL_MANAGER.generators.get(lottery_type)
      if generator and (generator.q_trained or generator.dqn_trained):
        # Сохраняем обученные модели
        if generator.q_trained:
          q_path = os.path.join(generator.models_dir, "q_agent.pkl")
          generator.q_agent.save(q_path)
          print(f"   [SAVE] Q-агент сохранен для {lottery_type}")

        if generator.dqn_trained:
          dqn_path = os.path.join(generator.models_dir, "dqn_agent.pth")
          generator.dqn_agent.save(dqn_path)
          print(f"   [SAVE] DQN агент сохранен для {lottery_type}")
  except Exception as e:
    print(f"   [ERROR] Ошибка сохранения RL моделей: {e}")


  print("   [OK] Приложение корректно остановлено")


async def _background_initial_training(lottery_type: str, config: dict):
  """Фонов  ое первичное обучение"""
  try:
    from backend.app.core.async_data_manager import ASYNC_DATA_MANAGER

    # Загружаем данные
    df = await ASYNC_DATA_MANAGER.fetch_draws_async(lottery_type)

    if len(df) > 50:  # Минимум для обучения
      await ASYNC_MODEL_MANAGER.train_models_background(lottery_type, df, config)
      print(f"[OK] Фоновое обучение {lottery_type} завершено")
    else:
      print(f"[WARN] Недостаточно данных для {lottery_type}")

  except Exception as e:
    print(f"[FAIL] Ошибка фонового обучения {lottery_type}: {e}")
app = FastAPI(
  title="Lottery Analysis API",
  description="REST API для анализа лотерей, генерации комбинаций и симуляции стратегий.",
  version="1.0.0",
  lifespan=lifespan
)


def custom_openapi():
  if app.openapi_schema:
    return app.openapi_schema

  openapi_schema = get_openapi(
    title=app.title,
    version=app.version,
    description=app.description,
    routes=app.routes,
  )

  # Настройка схемы безопасности
  openapi_schema["components"]["securitySchemes"] = {
    "Bearer": {
      "type": "http",
      "scheme": "bearer",
      "bearerFormat": "JWT",
      "description": "Введите токен в формате: Bearer {ваш_токен}"
    }
  }
  # Применяем security глобально к защищенным эндпоинтам
  openapi_schema["security"] = [{"Bearer": []}]

  app.openapi_schema = openapi_schema
  return app.openapi_schema


app.openapi = custom_openapi

# Настройка CORS для разрешения запросов от фронтенда
app.add_middleware(
  CORSMiddleware,
  allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # В продакшене укажите домен вашего фронтенда
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
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["📊 Dashboard"])

app.include_router(
    user_preferences.router,
    prefix="/api/v1/user",
    tags=["user"]
)

app.include_router(
    analysis_tools.router,
    prefix="/api/v1/analysis",
    tags=["analysis"]
)

app.include_router(
    simulation_tools.router,
    prefix="/api/v1/simulation",
    tags=["simulation"]
)
app.include_router(xgboost_api_endpoints.router, prefix="/api/v1/{lottery_type}", tags=["XGBoost"])
app.include_router(validation_routes.router, prefix="/api/v1/{lottery_type}", tags=["Validation"])
app.include_router(genetic_routes.router, prefix="/api/v1/{lottery_type}", tags=["Genetic Algorithm"])

app.include_router(rl_router.router, prefix="/api/v1/{lottery_type}", tags=["RL Analysis"])

app.include_router(timeseries_routes.router, prefix="/api/v1/{lottery_type}", tags=["TimeSeries Analysis"])

app.include_router(bayesian_routes.router, prefix="/api/v1/{lottery_type}", tags=["Bayesian Analysis"])

@app.get("/", summary="Корневой эндпоинт")
def read_root():
  return {"message": "Welcome to the Lottery Analysis API. Visit /docs for documentation."}