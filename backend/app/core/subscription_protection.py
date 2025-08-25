# """
# Защита эндпоинтов по уровням подписки
# """
# from enum import Enum
# from fastapi import HTTPException, status, Depends
# from backend.app.core.auth import get_current_user
# from typing import Optional
#
#
# class SubscriptionLevel(Enum):
#   FREE = "free"  # Бесплатный доступ
#   BASIC = "basic"  # Базовая подписка
#   PREMIUM = "premium"  # Премиум подписка
#   PRO = "pro"  # Профессиональная подписка
#
#
# # Ограничения для каждого уровня
# SUBSCRIPTION_LIMITS = {
#   SubscriptionLevel.FREE: {
#     "generations_per_day": 3,
#     "history_days": 30,
#     "patterns_access": False,
#     "clustering_access": False,
#     "simulations_per_day": 0,
#     "advanced_features": False
#   },
#   SubscriptionLevel.BASIC: {
#     "generations_per_day": 20,
#     "history_days": 180,
#     "patterns_access": True,
#     "clustering_access": False,
#     "simulations_per_day": 5,
#     "advanced_features": False
#   },
#   SubscriptionLevel.PREMIUM: {
#     "generations_per_day": 100,
#     "history_days": 365,
#     "patterns_access": True,
#     "clustering_access": True,
#     "simulations_per_day": 25,
#     "advanced_features": True
#   },
#   SubscriptionLevel.PRO: {
#     "generations_per_day": -1,  # Безлимит
#     "history_days": -1,  # Безлимит
#     "patterns_access": True,
#     "clustering_access": True,
#     "simulations_per_day": -1,  # Безлимит
#     "advanced_features": True
#   }
# }
#
#
# def check_subscription_access(required_level: SubscriptionLevel):
#   """Декоратор для проверки уровня подписки"""
#
#   def decorator(current_user=Depends(get_current_user)):
#     user_level = SubscriptionLevel.FREE
#
#     if current_user.subscription_status == "active":
#       # ИСПРАВЛЕНИЕ: Получаем план из preferences
#       plan = None
#       if current_user.preferences and isinstance(current_user.preferences, dict):
#         plan = current_user.preferences.get('subscription_plan', 'basic')
#       else:
#         plan = getattr(current_user, 'subscription_plan', 'basic')
#
#       print(f"🔒 Пользователь {current_user.email}: статус={current_user.subscription_status}, план={plan}")
#
#       if plan == 'pro':
#         user_level = SubscriptionLevel.PRO
#       elif plan == 'premium':
#         user_level = SubscriptionLevel.PREMIUM
#       elif plan == 'basic':
#         user_level = SubscriptionLevel.BASIC
#
#     print(f"🔒 Требуется: {required_level.value}, у пользователя: {user_level.value}")
#
#     # Проверяем доступ
#     if required_level == SubscriptionLevel.FREE:
#       return current_user  # Всем доступно
#     elif required_level == SubscriptionLevel.BASIC and user_level in [SubscriptionLevel.BASIC,
#                                                                       SubscriptionLevel.PREMIUM, SubscriptionLevel.PRO]:
#       return current_user
#     elif required_level == SubscriptionLevel.PREMIUM and user_level in [SubscriptionLevel.PREMIUM,
#                                                                         SubscriptionLevel.PRO]:
#       return current_user
#     elif required_level == SubscriptionLevel.PRO and user_level == SubscriptionLevel.PRO:
#       return current_user
#     else:
#       raise HTTPException(
#         status_code=status.HTTP_403_FORBIDDEN,
#         detail=f"Требуется подписка уровня {required_level.value} или выше. У вас: {user_level.value}"
#       )
#
#   return decorator
#
#
# async def get_current_user_optional():
#   """Получение текущего пользователя без обязательной авторизации"""
#   try:
#     from fastapi import Request, HTTPException
#     from fastapi.security import HTTPBearer
#     import jwt
#     from backend.app.core.database import SessionLocal, User
#     from backend.app.core.auth import JWT_SECRET, JWT_ALGORITHM
#
#     # Это упрощенная версия - в реальном проекте нужна полная реализация
#     # Возвращаем None если пользователь не авторизован
#     return None
#   except:
#     return None
#
# def get_current_user_optional_sync():
#   """Синхронная версия для использования в Depends"""
#   try:
#     return None  # Временная реализация
#   except:
#     return None
#
# # Готовые зависимости для использования
# require_basic = check_subscription_access(SubscriptionLevel.BASIC)
# require_premium = check_subscription_access(SubscriptionLevel.PREMIUM)
# require_pro = check_subscription_access(SubscriptionLevel.PRO)

from functools import wraps
from fastapi import HTTPException, status, Depends
from sqlalchemy.orm import Session
from backend.app.core.database import get_db, User, UserPreferences

from backend.app.core.auth import get_current_user
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class SubscriptionLevel(Enum):
  FREE = "free"
  BASIC = "basic"
  PREMIUM = "premium"
  PRO = "pro"


def check_subscription_access(user_id: int, required_level: SubscriptionLevel, db: Session) -> bool:
  """
  ИСПРАВЛЕНО: Проверяет доступ пользователя с учетом ОБОИХ источников подписки
  1. Сначала User.subscription_plan (основной источник)
  2. Потом UserPreferences.preferred_strategies (fallback)
  """
  print(f"🔍 Проверяем подписку для user_id={user_id}, требуется={required_level.value}")

  if required_level == SubscriptionLevel.FREE:
    return True

  # ИСПРАВЛЕНИЕ: Сначала проверяем основную таблицу User
  user = db.query(User).filter(User.id == user_id).first()
  user_plan = None

  if user:
    print(f"📊 User найден: subscription_status={user.subscription_status}, subscription_plan={user.subscription_plan}")

    # Проверяем основные поля User
    if user.subscription_status == "active" and user.subscription_plan:
      user_plan = user.subscription_plan
      print(f"✅ Используем User.subscription_plan: {user_plan}")
    else:
      print(f"⚠️ User.subscription_plan не подходит: status={user.subscription_status}, plan={user.subscription_plan}")

  # Fallback: Если нет в основной таблице, проверяем UserPreferences
  if not user_plan:
    print(f"🔄 Fallback: Проверяем UserPreferences...")
    user_prefs = db.query(UserPreferences).filter_by(user_id=user_id).first()

    if user_prefs and user_prefs.preferred_strategies:
      import json
      try:
        strategies = json.loads(user_prefs.preferred_strategies)
        if isinstance(strategies, dict):
          user_plan = strategies.get('subscription_plan', 'basic')
          print(f"✅ Используем UserPreferences: {user_plan}")
        else:
          user_plan = 'basic'
          print(f"⚠️ UserPreferences не dict, используем basic")
      except Exception as e:
        print(f"❌ Ошибка парсинга UserPreferences: {e}")
        user_plan = 'basic'
    else:
      print(f"⚠️ UserPreferences не найдены или пусты")
      user_plan = 'basic'

  # Дефолт если ничего не найдено
  if not user_plan:
    user_plan = 'basic'
    print(f"🔄 Используем дефолт: {user_plan}")

  print(f"📋 ИТОГ: user_plan={user_plan}")

  # Маппинг уровней
  plan_levels = {
    "free": 0,
    "basic": 1,
    "premium": 2,
    "pro": 3
  }

  required_level_map = {
    SubscriptionLevel.FREE: 0,
    SubscriptionLevel.BASIC: 1,
    SubscriptionLevel.PREMIUM: 2,
    SubscriptionLevel.PRO: 3
  }

  user_level = plan_levels.get(user_plan, 1)
  required_level_value = required_level_map.get(required_level, 1)

  result = user_level >= required_level_value
  print(f"🎯 РЕЗУЛЬТАТ: user_level={user_level} >= required={required_level_value} = {result}")

  return result


# def check_subscription_access(user_id: int, required_level: SubscriptionLevel, db: Session) -> bool:
#   """
#   Проверяет доступ пользователя на основе уровня подписки
#   Использует отдельный запрос для получения preferences
#   """
#   if required_level == SubscriptionLevel.FREE:
#     return True
#
#   # Загружаем preferences отдельным запросом
#   user_prefs = db.query(UserPreferences).filter_by(user_id=user_id).first()
#
#   # Если нет preferences - считаем как базовый уровень
#   if not user_prefs:
#     user_plan = "basic"
#   else:
#     # Получаем план из preferences (это уже JSON поле)
#     import json
#     try:
#       if user_prefs.preferred_strategies:  # Используем другое поле для хранения плана
#         strategies = json.loads(user_prefs.preferred_strategies)
#         user_plan = strategies.get('subscription_plan', 'basic') if isinstance(strategies, dict) else 'basic'
#       else:
#         user_plan = 'basic'
#     except:
#       user_plan = 'basic'
#
#   plan_levels = {
#     "free": 0,
#     "basic": 1,
#     "premium": 2,
#     "pro": 3
#   }
#
#   required_level_map = {
#     SubscriptionLevel.FREE: 0,
#     SubscriptionLevel.BASIC: 1,
#     SubscriptionLevel.PREMIUM: 2,
#     SubscriptionLevel.PRO: 3
#   }
#
#   user_level = plan_levels.get(user_plan, 1)
#   required_level_value = required_level_map.get(required_level, 1)
#
#   return user_level >= required_level_value


def require_subscription(level: SubscriptionLevel):
  """
  Декоратор для проверки уровня подписки с правильной работой с БД
  """

  def decorator(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
      # Получаем текущего пользователя и сессию БД
      current_user = kwargs.get('current_user')
      db = kwargs.get('db')

      # Если нет db в kwargs, пытаемся получить через Depends
      if not db:
        from backend.app.core.database import get_db
        db = next(get_db())

      if not current_user:
        raise HTTPException(
          status_code=status.HTTP_401_UNAUTHORIZED,
          detail="Authentication required"
        )

      # Проверяем доступ с использованием user_id
      if not check_subscription_access(current_user.id, level, db):
        raise HTTPException(
          status_code=status.HTTP_403_FORBIDDEN,
          detail=f"This feature requires {level.value} subscription or higher"
        )

      return func(*args, **kwargs)

    return wrapper

  return decorator


# Упрощенные функции для Depends
def require_basic(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
  """Требует базовую подписку или выше"""
  if not check_subscription_access(current_user.id, SubscriptionLevel.BASIC, db):
    raise HTTPException(
      status_code=status.HTTP_403_FORBIDDEN,
      detail="This feature requires basic subscription or higher"
    )
  return current_user


def require_premium(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
  """Требует премиум подписку или выше"""
  if not check_subscription_access(current_user.id, SubscriptionLevel.PREMIUM, db):
    raise HTTPException(
      status_code=status.HTTP_403_FORBIDDEN,
      detail="This feature requires premium subscription or higher"
    )
  return current_user


def require_pro(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
  """Требует про подписку"""
  if not check_subscription_access(current_user.id, SubscriptionLevel.PRO, db):
    raise HTTPException(
      status_code=status.HTTP_403_FORBIDDEN,
      detail="This feature requires pro subscription"
    )
  return current_user


def get_user_subscription_level(current_user=Depends(get_current_user), db: Session = Depends(get_db)) -> str:
  """
  Возвращает текущий уровень подписки пользователя
  """
  # Загружаем preferences
  user_prefs = db.query(UserPreferences).filter_by(user_id=current_user.id).first()

  if not user_prefs:
    return "basic"

  # Получаем план из preferences
  import json
  try:
    if user_prefs.preferred_strategies:
      strategies = json.loads(user_prefs.preferred_strategies)
      return strategies.get('subscription_plan', 'basic') if isinstance(strategies, dict) else 'basic'
  except:
    pass

  return "basic"

SUBSCRIPTION_LIMITS = {
  SubscriptionLevel.FREE: {
    "generations_per_day": 3,
    "history_days": 30,
    "patterns_access": False,
    "clustering_access": False,
    "simulations_per_day": 0,
    "advanced_features": False
  },
  SubscriptionLevel.BASIC: {
    "generations_per_day": 20,
    "history_days": 180,
    "patterns_access": True,
    "clustering_access": False,
    "simulations_per_day": 5,
    "advanced_features": False
  },
  SubscriptionLevel.PREMIUM: {
    "generations_per_day": 100,
    "history_days": 365,
    "patterns_access": True,
    "clustering_access": True,
    "simulations_per_day": 25,
    "advanced_features": True
  },
  SubscriptionLevel.PRO: {
    "generations_per_day": -1,  # Безлимит
    "history_days": -1,  # Безлимит
    "patterns_access": True,
    "clustering_access": True,
    "simulations_per_day": -1,  # Безлимит
    "advanced_features": True
  }
}

#
# def check_subscription_access(required_level: SubscriptionLevel):
#   """Декоратор для проверки уровня подписки"""
#
#   def decorator(current_user=Depends(get_current_user)):
#     user_level = SubscriptionLevel.FREE
#
#     if current_user.subscription_status == "active":
#       # ИСПРАВЛЕНИЕ: Получаем план из preferences
#       plan = None
#       if current_user.preferences and isinstance(current_user.preferences, dict):
#         plan = current_user.preferences.get('subscription_plan', 'basic')
#       else:
#         plan = getattr(current_user, 'subscription_plan', 'basic')
#
#       print(f"🔒 Пользователь {current_user.email}: статус={current_user.subscription_status}, план={plan}")
#
#       if plan == 'pro':
#         user_level = SubscriptionLevel.PRO
#       elif plan == 'premium':
#         user_level = SubscriptionLevel.PREMIUM
#       elif plan == 'basic':
#         user_level = SubscriptionLevel.BASIC
#
#     print(f"🔒 Требуется: {required_level.value}, у пользователя: {user_level.value}")
#
#     # Проверяем доступ
#     if required_level == SubscriptionLevel.FREE:
#       return current_user  # Всем доступно
#     elif required_level == SubscriptionLevel.BASIC and user_level in [SubscriptionLevel.BASIC,
#                                                                       SubscriptionLevel.PREMIUM, SubscriptionLevel.PRO]:
#       return current_user
#     elif required_level == SubscriptionLevel.PREMIUM and user_level in [SubscriptionLevel.PREMIUM,
#                                                                         SubscriptionLevel.PRO]:
#       return current_user
#     elif required_level == SubscriptionLevel.PRO and user_level == SubscriptionLevel.PRO:
#       return current_user
#     else:
#       raise HTTPException(
#         status_code=status.HTTP_403_FORBIDDEN,
#         detail=f"Требуется подписка уровня {required_level.value} или выше. У вас: {user_level.value}"
#       )
#
#   return decorator


async def get_current_user_optional():
  """Получение текущего пользователя без обязательной авторизации"""
  try:
    from fastapi import Request, HTTPException
    from fastapi.security import HTTPBearer
    import jwt
    from backend.app.core.database import SessionLocal, User
    from backend.app.core.auth import JWT_SECRET, JWT_ALGORITHM

    # Это упрощенная версия - в реальном проекте нужна полная реализация
    # Возвращаем None если пользователь не авторизован
    return None
  except:
    return None

def get_current_user_optional_sync():
  """Синхронная версия для использования в Depends"""
  try:
    return None  # Временная реализация
  except:
    return None

# # Готовые зависимости для использования
# require_basic = check_subscription_access(SubscriptionLevel.BASIC)
# require_premium = check_subscription_access(SubscriptionLevel.PREMIUM)
# require_pro = check_subscription_access(SubscriptionLevel.PRO)