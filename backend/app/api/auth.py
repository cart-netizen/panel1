"""
API эндпоинты для аутентификации
"""
from fastapi import APIRouter, Depends, HTTPException, status
from datetime import timedelta

from backend.app.core.auth import (
    authenticate_user, create_user, create_access_token,
    verify_token, get_user_by_email, ACCESS_TOKEN_EXPIRE_MINUTES,
    get_current_user, get_premium_user  # ← Добавлены импорты
)
from backend.app.models.auth_schemas import (
    UserCreate, UserLogin, Token, UserResponse
)

router = APIRouter()

# Удалите дублирующиеся определения функций get_current_user и get_premium_user
# Они теперь импортируются из core.auth

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

@router.post("/login", response_model=Token, summary="Вход в систему")
def login_user(user_credentials: UserLogin):
    """
    Аутентифицирует пользователя и возвращает JWT токен.
    """
    user = authenticate_user(user_credentials.email, user_credentials.password)

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