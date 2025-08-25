"""
API эндпоинты для аутентификации
"""
from datetime import timedelta

from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.auth import (
    authenticate_user, create_user, create_access_token,
    verify_token, get_user_by_email, ACCESS_TOKEN_EXPIRE_MINUTES,
    get_current_user, get_premium_user  # ← Добавлены импорты
)
from backend.app.models.auth_schemas import (
    UserCreate, UserLogin, Token, UserResponse
)
from fastapi import APIRouter, Depends, HTTPException, status, Body
from pydantic import BaseModel

router = APIRouter()

# Удалите дублирующиеся определения функций get_current_user и get_premium_user
# Они теперь импортируются из core.auth

# Модель для JSON логина
class LoginRequest(BaseModel):
    email: str
    password: str

class JsonLoginRequest(BaseModel):
    email: str
    password: str

@router.get("/refresh", response_model=UserResponse, summary="Обновить профиль из БД")
def refresh_user_profile(current_user = Depends(get_current_user)):
    """
    Принудительно обновляет профиль пользователя из базы данных.
    Полезно после изменения подписки.
    """
    # current_user уже обновлен через исправленный get_current_user
    return current_user

@router.post("/register", response_model=UserResponse, summary="Регистрация пользователя")
def register_user(user_data: UserCreate):
    """
    Регистрирует нового пользователя в системе.
    """
    try:
        user = create_user(
            email=user_data.email,
            password=user_data.password,
            full_name=user_data.full_name
        )
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при создании пользователя"
        )

@router.get("/me", response_model=UserResponse, summary="Информация о текущем пользователе")
def get_current_user_info(current_user = Depends(get_current_user)):
    """
    Возвращает информацию о текущем аутентифицированном пользователе.
    """
    return current_user

@router.get("/profile", response_model=UserResponse, summary="Профиль пользователя")
def get_user_profile(current_user = Depends(get_current_user)):
    """
    Возвращает детальную информацию профиля пользователя.
    """
    return current_user

@router.post("/refresh-token", response_model=Token, summary="Обновить токен")
def refresh_token(current_user = Depends(get_current_user)):
    """
    Обновляет токен если он ещё валиден
    """
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": current_user.email},
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/verify-token", summary="Проверить валидность токена")
def verify_token(current_user = Depends(get_current_user)):
    """
    Проверяет валидность токена
    """
    return {"valid": True, "email": current_user.email}



# @router.post("/login-json", response_model=Token, summary="Вход через JSON (Frontend)")
# def login_json(credentials: JsonLoginRequest):
#     """
#     Аутентификация через JSON для Frontend приложения.
#     """
#     user = authenticate_user(credentials.email, credentials.password)
#
#     if not user:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Неверный email или пароль",
#             headers={"WWW-Authenticate": "Bearer"},
#         )
#
#     access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
#     access_token = create_access_token(
#         data={"sub": user.email},
#         expires_delta=access_token_expires
#     )
#
#     return {"access_token": access_token, "token_type": "bearer"}

@router.post("/login-json", response_model=Token, summary="Вход через JSON")
def login_user_json(user_credentials: UserLogin):
    """
    Альтернативный вход через JSON (для frontend).
    """
    try:
        user = authenticate_user(user_credentials.email, user_credentials.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверный email или пароль"
            )

        # Создаем токен доступа
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.email},
            expires_delta=access_token_expires
        )

        return {
            "access_token": access_token,
            "token_type": "bearer"
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка входа в систему"
        )


@router.get("/verify-token", summary="Проверить валидность токена")
def verify_token_endpoint(current_user = Depends(get_current_user)):
    """
    Проверяет валидность токена.
    """
    return {"valid": True, "email": current_user.email}

@router.post("/logout", summary="Выход из системы")
def logout(current_user = Depends(get_current_user)):
    """
    Выход из системы (опционально).
    На frontend'е просто удалите токен из localStorage.
    """
    # Здесь можно добавить логику для инвалидации токена
    # Например, добавить токен в черный список
    return {"message": "Успешный выход"}


@router.post("/login", response_model=Token, summary="Вход через OAuth2 (Swagger)")
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    OAuth2 совместимый вход (form-data).
    """
    try:
        user = authenticate_user(form_data.username, form_data.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверный email или пароль",
                headers={"WWW-Authenticate": "Bearer"},
            )

        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.email}, expires_delta=access_token_expires
        )

        return {"access_token": access_token, "token_type": "bearer"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка входа в систему"
        )
# def login_oauth2(form_data: OAuth2PasswordRequestForm = Depends()):
#     """
#     Аутентификация через OAuth2 форму для Swagger UI.
#     В поле username введите ваш email.
#     """
#     # OAuth2PasswordRequestForm использует username, но мы ожидаем email
#     user = authenticate_user(form_data.username, form_data.password)
#
#     if not user:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Неверный email или пароль",
#             headers={"WWW-Authenticate": "Bearer"},
#         )
#
#     access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
#     access_token = create_access_token(
#         data={"sub": user.email},
#         expires_delta=access_token_expires
#     )
#
#     return {"access_token": access_token, "token_type": "bearer"}


@router.get("/debug-subscription", summary="🔍 ДИАГНОСТИКА подписки")
def debug_subscription(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    """
    🔍 ДИАГНОСТИЧЕСКИЙ эндпоинт для проверки состояния подписки

    Показывает ВСЕ источники информации о подписке пользователя
    """
    from backend.app.core.database import UserPreferences
    import json

    result = {
        "user_id": current_user.id,
        "email": current_user.email,

        # Данные из таблицы User
        "user_table": {
            "subscription_status": current_user.subscription_status,
            "subscription_plan": current_user.subscription_plan,
            "subscription_expires_at": current_user.subscription_expires_at.isoformat() if current_user.subscription_expires_at else None,
        },

        # Данные из UserPreferences
        "user_preferences": {
            "exists": False,
            "preferred_strategies_raw": None,
            "preferred_strategies_parsed": None,
            "subscription_plan_from_json": None,
            "parsing_error": None
        }
    }

    # Проверяем UserPreferences
    user_prefs = db.query(UserPreferences).filter_by(user_id=current_user.id).first()
    if user_prefs:
        result["user_preferences"]["exists"] = True
        result["user_preferences"]["preferred_strategies_raw"] = user_prefs.preferred_strategies

        if user_prefs.preferred_strategies:
            try:
                strategies = json.loads(user_prefs.preferred_strategies)
                result["user_preferences"]["preferred_strategies_parsed"] = strategies

                if isinstance(strategies, dict):
                    result["user_preferences"]["subscription_plan_from_json"] = strategies.get('subscription_plan')

            except Exception as e:
                result["user_preferences"]["parsing_error"] = str(e)

    # Диагностика логики доступа
    from backend.app.core.subscription_protection import SubscriptionLevel

    result["access_check"] = {}
    for level_name, level_enum in [
        ("FREE", SubscriptionLevel.FREE),
        ("BASIC", SubscriptionLevel.BASIC),
        ("PREMIUM", SubscriptionLevel.PREMIUM),
        ("PRO", SubscriptionLevel.PRO)
    ]:
        try:
            from backend.app.core.subscription_protection import check_subscription_access
            has_access = check_subscription_access(current_user.id, level_enum, db)
            result["access_check"][level_name] = has_access
        except Exception as e:
            result["access_check"][level_name] = f"ERROR: {str(e)}"

    # Рекомендации
    recommendations = []

    if result["user_table"]["subscription_plan"] and result["user_table"]["subscription_status"] == "active":
        recommendations.append(f"✅ У вас {result['user_table']['subscription_plan']} подписка в основной таблице")
    else:
        recommendations.append("❌ Нет активной подписки в основной таблице User")

    if result["user_preferences"]["subscription_plan_from_json"]:
        recommendations.append(f"✅ У вас {result['user_preferences']['subscription_plan_from_json']} в UserPreferences")
    else:
        recommendations.append("❌ Нет подписки в UserPreferences")

    result["recommendations"] = recommendations

    return result