# core/database.py
"""
Конфигурация базы данных для PostgreSQL
Миграция от SQLite к PostgreSQL для коммерческого сервиса
"""

import os
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, Text, JSON, MetaData

# Конфигурация базы данных
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:Cartman89@localhost:5432/lottery_analytics?client_encoding=utf8"
)

# Fallback на SQLite для разработки
if not DATABASE_URL.startswith("postgresql"):
  DATABASE_URL = "sqlite:///./data/lottery_unified.db"
  print("Используется SQLite (режим разработки)")
else:
  print(f"Подключение к PostgreSQL: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'localhost'}")

# Создание движка БД
engine = create_engine(
    DATABASE_URL,
    # Для SQLite
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {
        "client_encoding": "utf8",
        "options": "-c timezone=UTC"
    },
    # Для PostgreSQL
    pool_size=20 if "postgresql" in DATABASE_URL else None,
    max_overflow=30 if "postgresql" in DATABASE_URL else None,
    echo=False  # Добавляем для подавления лишних логов
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Метаданные для миграций
db_metadata = MetaData()


def get_db():
  """Dependency для получения сессии БД"""
  db = SessionLocal()
  try:
    yield db
  finally:
    db.close()


# ============== МОДЕЛИ ДАННЫХ ==============

class LotteryDraw(Base):
  """Универсальная модель для всех лотерей"""
  __tablename__ = "lottery_draws"

  id = Column(Integer, primary_key=True, index=True)
  lottery_type = Column(String(20), nullable=False, index=True)  # '4x20', '5x36plus'
  draw_number = Column(Integer, nullable=False, index=True)
  draw_date = Column(DateTime, nullable=False, index=True)

  # Гибкое хранение чисел
  field1_numbers = Column(JSON, nullable=False)  # [1,5,12,18]
  field2_numbers = Column(JSON, nullable=False)  # [2,7,11,20]

  # Дополнительные данные
  prize_info = Column(JSON, nullable=True)  # Информация о призах
  created_at = Column(DateTime, nullable=False)
  updated_at = Column(DateTime, nullable=True)

  # Составные индексы для быстрого поиска
  __table_args__ = (
    # Создаем индексы стандартным способом SQLAlchemy
    {'comment': 'Lottery draws table with optimized indexes'}
  )


class User(Base):
  """Модель пользователя для коммерческого сервиса"""
  __tablename__ = "users"

  id = Column(Integer, primary_key=True, index=True)
  email = Column(String(255), unique=True, index=True, nullable=False)
  hashed_password = Column(String(255), nullable=False)

  # Профиль
  full_name = Column(String(255), nullable=True)
  is_active = Column(Boolean, default=True)
  is_verified = Column(Boolean, default=False)

  # Подписка
  subscription_status = Column(String(50), default="inactive")  # inactive, active, canceled, expired
  subscription_plan = Column(String(50), nullable=True)  # basic, premium, pro
  subscription_expires_at = Column(DateTime, nullable=True)

  # Платежи
  customer_id = Column(String(255), nullable=True)  # ID в платежной системе

  # Метаданные
  created_at = Column(DateTime, nullable=False)
  last_login_at = Column(DateTime, nullable=True)

  # Настройки
  preferences = Column(JSON, nullable=True)  # Пользовательские настройки


class UserSession(Base):
  """Сессии пользователей для безопасности"""
  __tablename__ = "user_sessions"

  id = Column(Integer, primary_key=True, index=True)
  user_id = Column(Integer, nullable=False, index=True)
  token_hash = Column(String(255), nullable=False, unique=True)
  expires_at = Column(DateTime, nullable=False)
  created_at = Column(DateTime, nullable=False)
  last_used_at = Column(DateTime, nullable=True)

  # Метаданные сессии
  ip_address = Column(String(45), nullable=True)
  user_agent = Column(Text, nullable=True)


class PaymentTransaction(Base):
  """История платежей"""
  __tablename__ = "payment_transactions"

  id = Column(Integer, primary_key=True, index=True)
  user_id = Column(Integer, nullable=False, index=True)

  # Платежная информация
  payment_id = Column(String(255), nullable=False, unique=True)  # ID в платежной системе
  amount = Column(Float, nullable=False)
  currency = Column(String(3), default="RUB")
  status = Column(String(50), nullable=False)  # pending, completed, failed, refunded

  # Подписка
  subscription_plan = Column(String(50), nullable=False)
  subscription_period_months = Column(Integer, nullable=False)

  # Метаданные
  payment_method = Column(String(50), nullable=True)  # card, wallet, etc.
  created_at = Column(DateTime, nullable=False)
  completed_at = Column(DateTime, nullable=True)


class UserActivity(Base):
  """Активность пользователей для дашборда"""
  __tablename__ = "user_activities"

  id = Column(Integer, primary_key=True, index=True)
  user_id = Column(Integer, nullable=True, index=True)  # null для анонимных
  
  # Тип активности
  activity_type = Column(String(50), nullable=False, index=True)  # generation, analysis, clustering, verification
  activity_description = Column(String(500), nullable=False)
  
  # Детали активности
  lottery_type = Column(String(20), nullable=True)  # '4x20', '5x36plus'
  details = Column(JSON, nullable=True)  # Дополнительные данные
  
  # Метаданные
  created_at = Column(DateTime, nullable=False, index=True)
  ip_address = Column(String(45), nullable=True)
  user_agent = Column(String(500), nullable=True)


class ModelStatistics(Base):
  """Статистика работы ML моделей"""
  __tablename__ = "model_statistics"

  id = Column(Integer, primary_key=True, index=True)
  lottery_type = Column(String(20), nullable=False, index=True)
  model_type = Column(String(20), nullable=False, index=True)  # rf, lstm
  
  # Метрики точности
  accuracy_percentage = Column(Float, nullable=True)
  best_score = Column(Float, nullable=True)
  predictions_count = Column(Integer, default=0)
  correct_predictions = Column(Integer, default=0)
  
  # Статистика по периодам
  date_period = Column(String(20), nullable=False, index=True)  # daily, weekly, monthly
  period_start = Column(DateTime, nullable=False, index=True)
  period_end = Column(DateTime, nullable=False)
  
  # Детальная статистика
  statistics_data = Column(JSON, nullable=True)  # Подробные метрики
  
  created_at = Column(DateTime, nullable=False)
  updated_at = Column(DateTime, nullable=True)


class DashboardCache(Base):
  """Кэш для данных дашборда"""
  __tablename__ = "dashboard_cache"

  id = Column(Integer, primary_key=True, index=True)
  cache_key = Column(String(255), nullable=False, unique=True, index=True)
  cache_type = Column(String(50), nullable=False, index=True)  # stats, trends, activity
  
  # Данные
  cached_data = Column(JSON, nullable=False)
  
  # TTL
  expires_at = Column(DateTime, nullable=False, index=True)
  created_at = Column(DateTime, nullable=False)
  updated_at = Column(DateTime, nullable=True)

  # Дополнительные данные
  extra_data = Column(JSON, nullable=True)


class ModelPrediction(Base):
  """История предсказаний AI моделей"""
  __tablename__ = "model_predictions"

  id = Column(Integer, primary_key=True, index=True)
  lottery_type = Column(String(20), nullable=False, index=True)
  model_type = Column(String(20), nullable=False)  # 'rf', 'lstm'

  # Предсказание
  predicted_field1 = Column(JSON, nullable=False)
  predicted_field2 = Column(JSON, nullable=False)
  confidence_score = Column(Float, nullable=True)

  # Контекст
  based_on_draw = Column(Integer, nullable=True)  # На основе какого тиража
  created_at = Column(DateTime, nullable=False)

  # Результат (заполняется после фактического тиража)
  actual_field1 = Column(JSON, nullable=True)
  actual_field2 = Column(JSON, nullable=True)
  accuracy_score = Column(Float, nullable=True)


def create_tables():
  """Создает все таблицы в БД"""
  print("🏗️ Создание таблиц в базе данных...")
  Base.metadata.create_all(bind=engine)
  print("✅ Таблицы созданы успешно")


def get_db_stats():
  """Возвращает статистику по базе данных"""
  from sqlalchemy import text

  with engine.connect() as conn:
    stats = {}

    # Статистика по тиражам
    result = conn.execute(text("""
            SELECT lottery_type, COUNT(*) as count, 
                   MIN(draw_number) as min_draw, 
                   MAX(draw_number) as max_draw
            FROM lottery_draws 
            GROUP BY lottery_type
        """))

    stats['draws'] = [dict(row._mapping) for row in result]

    # Статистика по пользователям (если таблица существует)
    try:
      result = conn.execute(text("""
                SELECT subscription_status, COUNT(*) as count
                FROM users 
                GROUP BY subscription_status
            """))
      stats['users'] = [dict(row) for row in result]
    except:
      stats['users'] = []

    return stats