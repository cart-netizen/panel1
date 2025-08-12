"""
Управление подписками и платежами
"""
from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime, timedelta
from typing import List

from backend.app.core.auth import get_current_user, update_subscription_status
from backend.app.models.auth_schemas import SubscriptionUpdate, UserResponse

router = APIRouter()


@router.get("/plans", summary="Доступные планы подписки")
def get_subscription_plans():
  """
  Возвращает список доступных планов подписки с ценами и функциями.
  """
  return {
    "plans": [
      {
        "id": "basic",
        "name": "Базовый",
        "price_monthly": 990,
        "price_yearly": 9900,
        "currency": "RUB",
        "features": [
          "20 генераций в день",
          "История за 6 месяцев",
          "Анализ паттернов",
          "5 симуляций в день",
          "Email поддержка"
        ],
        "limits": {
          "generations_per_day": 20,
          "history_days": 180,
          "simulations_per_day": 5
        }
      },
      {
        "id": "premium",
        "name": "Премиум",
        "price_monthly": 1990,
        "price_yearly": 19900,
        "currency": "RUB",
        "features": [
          "100 генераций в день",
          "Полная история",
          "Продвинутые паттерны",
          "Кластерный анализ",
          "25 симуляций в день",
          "Priority поддержка"
        ],
        "limits": {
          "generations_per_day": 100,
          "history_days": 365,
          "simulations_per_day": 25
        },
        "popular": True
      },
      {
        "id": "pro",
        "name": "Профессиональный",
        "price_monthly": 4990,
        "price_yearly": 49900,
        "currency": "RUB",
        "features": [
          "Безлимитные генерации",
          "Полная история",
          "Все продвинутые функции",
          "API доступ",
          "Безлимитные симуляции",
          "Персональный менеджер"
        ],
        "limits": {
          "generations_per_day": -1,
          "history_days": -1,
          "simulations_per_day": -1
        }
      }
    ]
  }


@router.get("/my-subscription", response_model=UserResponse, summary="Моя подписка")
def get_my_subscription(current_user=Depends(get_current_user)):
  """
  Возвращает информацию о текущей подписке пользователя.
  """
  return current_user


@router.post("/upgrade", summary="Активация подписки (DEMO)")
def demo_upgrade_subscription(
    plan_data: SubscriptionUpdate,
    current_user=Depends(get_current_user)
):
  """
  🚧 ДЕМО функция активации подписки.
  """

  # Валидация плана
  valid_plans = ["basic", "premium", "pro"]
  if plan_data.plan not in valid_plans:
    raise HTTPException(
      status_code=400,
      detail=f"Недопустимый план. Доступны: {valid_plans}"
    )

  # DEMO: Активируем подписку сразу
  expires_at = datetime.utcnow() + timedelta(days=30 * plan_data.duration_months)

  # ИСПРАВЛЕНИЕ: Передаем план
  updated_user = update_subscription_status(
    user_id=current_user.id,
    status="active",
    expires_at=expires_at,
    plan=plan_data.plan  # ← Добавлено!
  )

  if not updated_user:
    raise HTTPException(
      status_code=500,
      detail="Ошибка обновления подписки"
    )

  return {
    "success": True,
    "message": f"Подписка {plan_data.plan} активирована на {plan_data.duration_months} мес.",
    "expires_at": expires_at.isoformat(),
    "status": "active",
    "plan": plan_data.plan,
    "demo_note": "Это демо-активация. В продакшене будет реальная оплата."
  }


@router.post("/cancel", summary="Отмена подписки")
def cancel_subscription(current_user=Depends(get_current_user)):
  """
  Отменяет текущую подписку пользователя.
  """
  if current_user.subscription_status != "active":
    raise HTTPException(
      status_code=400,
      detail="У вас нет активной подписки"
    )

  updated_user = update_subscription_status(
    user_id=current_user.id,
    status="canceled"
  )

  return {
    "success": True,
    "message": "Подписка отменена",
    "status": "canceled"
  }