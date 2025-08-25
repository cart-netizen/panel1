"""
Модуль роутеров API
backend/app/routers/__init__.py
"""

# Импортируем все роутеры для удобного доступа
from app.api.rl_router import router as rl_router

__all__ = [
    'rl_router'
]