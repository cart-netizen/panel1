"""
API для управления предпочтениями пользователя
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, List, Optional
from pydantic import BaseModel

from backend.app.core.database import get_db, User, UserPreferences  # Импортируем всё из database.py!
from backend.app.core.auth import get_current_user
import json
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


class FavoriteNumbersUpdate(BaseModel):
    """Модель для обновления избранных чисел"""
    favorite_numbers: Dict[str, List[int]]
    lottery_type: Optional[str] = "4x20"


class UserPreferencesResponse(BaseModel):
    """Ответ с предпочтениями пользователя"""
    favorite_numbers: Optional[Dict[str, List[int]]] = None
    default_lottery: str = "4x20"
    preferred_strategies: List[str] = []
    notification_settings: Dict = {}


@router.get("/preferences", response_model=UserPreferencesResponse)
async def get_user_preferences(
    lottery_type: str = "4x20",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить предпочтения пользователя для конкретной лотереи"""
    try:
        # Ищем существующие предпочтения
        prefs = db.query(UserPreferences).filter_by(user_id=current_user.id).first()

        if not prefs:
            # Создаём дефолтные предпочтения
            return UserPreferencesResponse(
                favorite_numbers={"field1": [], "field2": []},
                default_lottery="4x20"
            )

        # Парсим JSON поля по лотереям
        all_favorites = json.loads(prefs.favorite_numbers) if prefs.favorite_numbers else {}

        # Получаем избранные числа для конкретной лотереи
        lottery_favorites = all_favorites.get(lottery_type, {"field1": [], "field2": []})

        return UserPreferencesResponse(
            favorite_numbers=lottery_favorites,
            default_lottery=prefs.default_lottery or "4x20",
            preferred_strategies=json.loads(prefs.preferred_strategies) if prefs.preferred_strategies else [],
            notification_settings=json.loads(prefs.notification_settings) if prefs.notification_settings else {}
        )

    except Exception as e:
        logger.error(f"Ошибка получения предпочтений: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения предпочтений")


@router.put("/preferences", response_model=UserPreferencesResponse)
async def update_user_preferences(
    data: FavoriteNumbersUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Обновить избранные числа пользователя для конкретной лотереи"""
    try:
        # Ищем существующие предпочтения
        prefs = db.query(UserPreferences).filter_by(user_id=current_user.id).first()

        if not prefs:
            # Создаём новые предпочтения
            all_favorites = {data.lottery_type: data.favorite_numbers}
            prefs = UserPreferences(
                user_id=current_user.id,
                favorite_numbers=json.dumps(all_favorites),
                default_lottery=data.lottery_type or "4x20"
            )
            db.add(prefs)
        else:
            # Обновляем существующие
            all_favorites = json.loads(prefs.favorite_numbers) if prefs.favorite_numbers else {}
            all_favorites[data.lottery_type] = data.favorite_numbers
            prefs.favorite_numbers = json.dumps(all_favorites)

            if data.lottery_type:
                prefs.default_lottery = data.lottery_type

        db.commit()
        db.refresh(prefs)

        # Возвращаем обновлённые предпочтения для текущей лотереи
        return UserPreferencesResponse(
            favorite_numbers=data.favorite_numbers,
            default_lottery=prefs.default_lottery,
            preferred_strategies=json.loads(prefs.preferred_strategies) if prefs.preferred_strategies else [],
            notification_settings=json.loads(prefs.notification_settings) if prefs.notification_settings else {}
        )

    except Exception as e:
        logger.error(f"Ошибка сохранения предпочтений: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Ошибка сохранения предпочтений")


@router.delete("/preferences/favorite-numbers")
async def clear_favorite_numbers(
    lottery_type: str = "4x20",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Очистить избранные числа для конкретной лотереи"""
    try:
        prefs = db.query(UserPreferences).filter_by(user_id=current_user.id).first()

        if prefs:
            all_favorites = json.loads(prefs.favorite_numbers) if prefs.favorite_numbers else {}
            all_favorites[lottery_type] = {"field1": [], "field2": []}
            prefs.favorite_numbers = json.dumps(all_favorites)
            db.commit()

        return {"status": "success", "message": f"Избранные числа очищены для {lottery_type}"}

    except Exception as e:
        logger.error(f"Ошибка очистки избранных чисел: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Ошибка очистки")


@router.put("/subscription")
async def update_user_subscription(
    plan: str = "basic",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Обновить план подписки пользователя"""
    try:
        # Ищем существующие предпочтения
        prefs = db.query(UserPreferences).filter_by(user_id=current_user.id).first()

        if not prefs:
            # Создаём новые предпочтения
            prefs = UserPreferences(
                user_id=current_user.id,
                favorite_numbers='{"field1": [], "field2": []}',
                default_lottery="4x20",
                preferred_strategies=json.dumps({"subscription_plan": plan})
            )
            db.add(prefs)
        else:
            # Обновляем существующие
            try:
                strategies = json.loads(prefs.preferred_strategies) if prefs.preferred_strategies else {}
            except:
                strategies = {}

            strategies['subscription_plan'] = plan
            prefs.preferred_strategies = json.dumps(strategies)

        db.commit()
        db.refresh(prefs)

        return {
            "status": "success",
            "subscription_plan": plan,
            "message": f"Подписка обновлена на {plan}"
        }

    except Exception as e:
        logger.error(f"Ошибка обновления подписки: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Ошибка обновления подписки")