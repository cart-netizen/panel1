"""
API эндпоинты для аутентификации
"""
from datetime import timedelta

from fastapi.security import OAuth2PasswordRequestForm

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

# @router.post("/login-json", response_model=Token, summary="Вход через JSON")
# def login_user_json(user_credentials: UserLogin):
#     """
#     Альтернативный вход через JSON (для frontend).
#     """
#     user = authenticate_user(user_credentials.email, user_credentials.password)
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
#         data={"sub": user.email}, expires_delta=access_token_expires
#     )
#
#     return {"access_token": access_token, "token_type": "bearer"}


# @router.post("/login", response_model=Token, summary="Вход в систему")
# async def login_user(
#     # Пытаемся принять оба формата
#     form_data: OAuth2PasswordRequestForm = None,
#     json_data: LoginRequest = None,
#     email: str = Body(None),
#     password: str = Body(None)
# ):
#     """
#     Универсальный вход - поддерживает и OAuth2 форму (для Swagger) и JSON (для frontend)
#     """
#     # Определяем источник данных
#     login_email = None
#     login_password = None
#
#     if form_data:
#         # OAuth2 форма (Swagger UI)
#         login_email = form_data.username
#         login_password = form_data.password
#     elif email and password:
#         # Прямые поля JSON
#         login_email = email
#         login_password = password
#     else:
#         # Пробуем распарсить как JSON body
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Требуются email и password"
#         )
#
#     # Аутентификация
#     user = authenticate_user(login_email, login_password)
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


# @router.post("/login", response_model=Token, summary="Вход через OAuth2 форму (Swagger)")
# def login_form(form_data: OAuth2PasswordRequestForm = Depends()):
#     """
#     Аутентификация через OAuth2 форму для Swagger UI.
#     Используйте email в поле username.
#     """
#     # OAuth2PasswordRequestForm использует username, но мы принимаем email
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


@router.post("/login-json", response_model=Token, summary="Вход через JSON (Frontend)")
def login_json(credentials: JsonLoginRequest):
    """
    Аутентификация через JSON для Frontend приложения.
    """
    user = authenticate_user(credentials.email, credentials.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/refresh", response_model=UserResponse, summary="Обновить профиль из БД")
def refresh_user_profile(current_user = Depends(get_current_user)):
    """
    Принудительно обновляет профиль пользователя из базы данных.
    """
    return current_user

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
def login_oauth2(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Аутентификация через OAuth2 форму для Swagger UI.
    В поле username введите ваш email.
    """
    # OAuth2PasswordRequestForm использует username, но мы ожидаем email
    user = authenticate_user(form_data.username, form_data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}