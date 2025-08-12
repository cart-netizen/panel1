"""
Конфигурация для продакшен-развертывания
backend/app/core/production_config.py
"""

PRODUCTION_SETTINGS = {
  # Сервер
  "workers": 8,  # По 2 воркера на CPU ядро
  "max_requests": 1000,  # Перезапуск воркера после 1000 запросов
  "timeout": 30,

  # База данных
  "db_pool_size": 50,
  "db_max_overflow": 100,
  "db_pool_timeout": 30,

  # Кэширование
  "cache_ttl": {
    "lottery_history": 300,  # 5 минут
    "ml_predictions": 1800,  # 30 минут
    "pattern_analysis": 900,  # 15 минут
    "user_sessions": 3600  # 1 час
  },

  # Лимиты API
  "rate_limits": {
    "free_user": "10/minute",
    "basic_user": "100/minute",
    "premium_user": "500/minute",
    "pro_user": "2000/minute"
  },

  # ML модели
  "model_training": {
    "max_parallel_training": 4,
    "training_timeout": 1800,  # 30 минут
    "min_data_for_training": 100
  }
}