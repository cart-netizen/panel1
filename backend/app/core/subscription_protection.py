"""
Защита эндпоинтов по уровням подписки
"""
from enum import Enum
from fastapi import HTTPException, status, Depends
from backend.app.core.auth import get_current_user


class SubscriptionLevel(Enum):
  FREE = "free"  # Бесплатный доступ
  BASIC = "basic"  # Базовая подписка
  PREMIUM = "premium"  # Премиум подписка
  PRO = "pro"  # Профессиональная подписка


# Ограничения для каждого уровня
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


def check_subscription_access(required_level: SubscriptionLevel):
  """Декоратор для проверки уровня подписки"""

  def decorator(current_user=Depends(get_current_user)):
    user_level = SubscriptionLevel.FREE

    if current_user.subscription_status == "active":
      # ИСПРАВЛЕНИЕ: Получаем план из preferences
      plan = None
      if current_user.preferences and isinstance(current_user.preferences, dict):
        plan = current_user.preferences.get('subscription_plan', 'basic')
      else:
        plan = getattr(current_user, 'subscription_plan', 'basic')

      print(f"🔒 Пользователь {current_user.email}: статус={current_user.subscription_status}, план={plan}")

      if plan == 'pro':
        user_level = SubscriptionLevel.PRO
      elif plan == 'premium':
        user_level = SubscriptionLevel.PREMIUM
      elif plan == 'basic':
        user_level = SubscriptionLevel.BASIC

    print(f"🔒 Требуется: {required_level.value}, у пользователя: {user_level.value}")

    # Проверяем доступ
    if required_level == SubscriptionLevel.FREE:
      return current_user  # Всем доступно
    elif required_level == SubscriptionLevel.BASIC and user_level in [SubscriptionLevel.BASIC,
                                                                      SubscriptionLevel.PREMIUM, SubscriptionLevel.PRO]:
      return current_user
    elif required_level == SubscriptionLevel.PREMIUM and user_level in [SubscriptionLevel.PREMIUM,
                                                                        SubscriptionLevel.PRO]:
      return current_user
    elif required_level == SubscriptionLevel.PRO and user_level == SubscriptionLevel.PRO:
      return current_user
    else:
      raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"Требуется подписка уровня {required_level.value} или выше. У вас: {user_level.value}"
      )

  return decorator


# Готовые зависимости для использования
require_basic = check_subscription_access(SubscriptionLevel.BASIC)
require_premium = check_subscription_access(SubscriptionLevel.PREMIUM)
require_pro = check_subscription_access(SubscriptionLevel.PRO)