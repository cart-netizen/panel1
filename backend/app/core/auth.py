"""
Система аутентификации и авторизации
"""
from datetime import datetime, timedelta
from typing import Optional
import jwt
from jose import JWTError
from jwt import ExpiredSignatureError
from passlib.context import CryptContext
from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from backend.app.core.database import User, SessionLocal, get_db
# from fastapi.security import OAuth2PasswordBearer
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
# Конфигурация
SECRET_KEY = "your-super-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

# Хеширование паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
  """Проверяет пароль"""
  return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
  """Хеширует пароль"""
  return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
  """Создает JWT токен"""
  to_encode = data.copy()
  if expires_delta:
    expire = datetime.utcnow() + expires_delta
  else:
    expire = datetime.utcnow() + timedelta(minutes=15)

  to_encode.update({"exp": expire})
  encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
  return encoded_jwt


def verify_token(token: str) -> Optional[dict]:
  """Проверяет JWT токен"""
  try:
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    email: str = payload.get("sub")
    if email is None:
      return None
    return {"email": email}
  except jwt.PyJWTError:
    return None


# def authenticate_user(email: str, password: str) -> Optional[User]:
#   """Аутентифицирует пользователя"""
#   db = SessionLocal()
#   try:
#     user = db.query(User).filter(User.email == email).first()
#     if not user:
#       return None
#     if not verify_password(password, user.hashed_password):
#       return None
#     return user
#   finally:
#     db.close()
def authenticate_user(email_or_username: str, password: str):
    """
    Аутентификация пользователя.
    Принимает email или username (для совместимости с OAuth2).
    """
    from backend.app.core.database import SessionLocal

    db = SessionLocal()
    try:
      # Пытаемся найти по email
      user = db.query(User).filter(User.email == email_or_username).first()

      if not user:
        return False

      if not verify_password(password, user.hashed_password):
        return False

      return user
    finally:
      db.close()

def create_user(email: str, password: str, full_name: str = None) -> User:
  """Создает нового пользователя"""
  db = SessionLocal()
  try:
    # Проверяем, что пользователь не существует
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
      raise ValueError("Пользователь с таким email уже существует")

    # Создаем нового пользователя
    hashed_password = get_password_hash(password)
    user = User(
      email=email,
      hashed_password=hashed_password,
      full_name=full_name,
      is_active=True,
      is_verified=False,
      subscription_status="inactive",
      created_at=datetime.utcnow()
    )

    db.add(user)
    db.commit()
    db.refresh(user)
    return user

  finally:
    db.close()


def get_user_by_email(email: str) -> Optional[User]:
  """Получает пользователя по email"""
  db = SessionLocal()
  try:
    return db.query(User).filter(User.email == email).first()
  finally:
    db.close()


def update_subscription_status(user_id: int, status: str, expires_at: datetime = None, plan: str = None):
  """Обновляет статус подписки пользователя"""
  db = SessionLocal()
  try:
    user = db.query(User).filter(User.id == user_id).first()
    if user:
      # Обновляем основные поля
      user.subscription_status = status
      user.subscription_expires_at = expires_at

      # ИСПРАВЛЕНИЕ: Обновляем план в preferences
      if plan:
        if not user.preferences:
          user.preferences = {}
        user.preferences['subscription_plan'] = plan

        # ВАЖНО: Помечаем preferences как измененные для SQLAlchemy
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(user, "preferences")

      db.commit()
      db.refresh(user)

      print(f"🔄 Подписка обновлена: user_id={user_id}, status={status}, plan={plan}")
      print(f"🔄 Preferences: {user.preferences}")

      return user
    return None
  except Exception as e:
    print(f"❌ Ошибка обновления подписки: {e}")
    db.rollback()
    return None
  finally:
    db.close()

def refresh_user_from_db(user_id: int):
  """Получает свежие данные пользователя из БД"""
  db = SessionLocal()
  try:
    user = db.query(User).filter(User.id == user_id).first()
    if user:
      db.refresh(user)  # Принудительно обновляем из БД
    return user
  finally:
    db.close()

security = HTTPBearer()


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
  """
  Получает текущего пользователя из токена с улучшенной обработкой ошибок
  """
  credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
  )

  token_expired_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Token has expired. Please login again",
    headers={"WWW-Authenticate": "Bearer"},
  )

  try:
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    email: str = payload.get("sub")
    if email is None:
      raise credentials_exception
  except ExpiredSignatureError:
    # Специальная обработка истекших токенов
    raise token_expired_exception
  except JWTError:
    raise credentials_exception

  # Загружаем пользователя со всеми связями
  user = db.query(User).options(
    joinedload(User.preferences)
  ).filter(User.email == email).first()

  if user is None:
    raise credentials_exception

  return user
# def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
#   """Получает текущего пользователя из токена с обновлением из БД"""
#   token = credentials.credentials
#   payload = verify_token(token)
#
#   if payload is None:
#     raise HTTPException(
#       status_code=status.HTTP_401_UNAUTHORIZED,
#       detail="Недействительный токен",
#       headers={"WWW-Authenticate": "Bearer"},
#     )
#
#   # ИСПРАВЛЕНИЕ: Всегда получаем свежие данные из БД
#   user = refresh_user_from_db_by_email(payload["email"])
#   if user is None:
#     raise HTTPException(
#       status_code=status.HTTP_401_UNAUTHORIZED,
#       detail="Пользователь не найден"
#     )
#
#   return user

def refresh_user_from_db_by_email(email: str):
  """Получает свежие данные пользователя по email"""
  db = SessionLocal()
  try:
    user = db.query(User).filter(User.email == email).first()
    if user:
      db.refresh(user)  # Принудительно обновляем из БД
    return user
  finally:
    db.close()

def get_premium_user(current_user = Depends(get_current_user)):
    """Проверяет, что у пользователя есть активная подписка"""
    if current_user.subscription_status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Требуется активная подписка для доступа к этой функции"
        )
    return current_user