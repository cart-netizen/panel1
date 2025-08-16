# from datetime import datetime
#
# from sqlalchemy import Column, ForeignKey, Integer, String, Text, DateTime
# from sqlalchemy.orm import relationship
#
# from backend.app.core.database import Base
#
#
# class UserPreferences(Base):
#   """Предпочтения и настройки пользователя"""
#   __tablename__ = "user_preferences"
#
#   id = Column(Integer, primary_key=True, index=True)
#   user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
#
#   # Избранные числа в формате JSON
#   favorite_numbers = Column(Text, default='{"field1": [], "field2": []}')
#
#   # Дефолтная лотерея
#   default_lottery = Column(String(50), default="4x20")
#
#   # Предпочитаемые стратегии генерации
#   preferred_strategies = Column(Text, default='[]')  # JSON массив
#
#   # Настройки уведомлений
#   notification_settings = Column(Text, default='{}')  # JSON объект
#
#   # История действий пользователя (для персонализации)
#   action_history = Column(Text, default='[]')  # JSON массив последних действий
#
#   # Временные метки
#   created_at = Column(DateTime, default=datetime.utcnow)
#   updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
#
#   # Связь с пользователем
#   user = relationship("User", back_populates="preferences")
#
# # Добавить в класс User связь:
# # preferences = relationship("UserPreferences", back_populates="user", uselist=False)