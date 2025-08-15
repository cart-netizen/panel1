"""
Асинхронные AI модели для масштабирования
"""
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Optional
import logging
from datetime import datetime

from backend.app.core.ai_model import RFModel, LotteryLSTMOps, ModelManager, GLOBAL_MODEL_MANAGER
from backend.app.core.data_manager import LOTTERY_CONFIGS

logger = logging.getLogger(__name__)


class AsyncModelManager:
  """
  Асинхронный менеджер моделей с фоновым обучением
  """

  def __init__(self, max_workers: int = 4):
    self.max_workers = max_workers
    self.executor = ThreadPoolExecutor(max_workers=max_workers)

    # Используем глобальный менеджер для общих моделей
    self.sync_manager = GLOBAL_MODEL_MANAGER

    # Состояние обучения
    self.training_status: Dict[str, Dict] = {}
    self.training_locks: Dict[str, asyncio.Lock] = {}

    # Инициализируем локи для каждой лотереи
    for lottery_type in LOTTERY_CONFIGS.keys():
      self.training_locks[lottery_type] = asyncio.Lock()
      self.training_status[lottery_type] = {
        'is_training': False,
        'last_trained': None,
        'training_progress': 0,
        'error': None
      }

  async def get_rf_model(self, lottery_type: str, lottery_config: dict) -> RFModel:
    """Асинхронно получает RF модель"""
    return await asyncio.get_event_loop().run_in_executor(
      self.executor,
      self.sync_manager.get_rf_model,
      lottery_type,
      lottery_config
    )

  async def get_lstm_model(self, lottery_type: str, lottery_config: dict) -> LotteryLSTMOps:
    """Асинхронно получает LSTM модель"""
    return await asyncio.get_event_loop().run_in_executor(
      self.executor,
      self.sync_manager.get_lstm_model,
      lottery_type,
      lottery_config
    )

  async def train_models_background(self, lottery_type: str, df_history, lottery_config: dict):
    """
    Фоновое обучение моделей без блокировки API
    """
    async with self.training_locks[lottery_type]:
      if self.training_status[lottery_type]['is_training']:
        logger.info(f"Обучение {lottery_type} уже в процессе, пропускаем")
        return

      # Помечаем как обучающуюся
      self.training_status[lottery_type].update({
        'is_training': True,
        'training_progress': 0,
        'error': None
      })

    try:
      logger.info(f"🧠 Начало фонового обучения моделей для {lottery_type}")

      # Обучение в отдельном потоке
      await self._train_models_async(lottery_type, df_history, lottery_config)

      # Обновляем статус
      self.training_status[lottery_type].update({
        'is_training': False,
        'last_trained': datetime.now(),
        'training_progress': 100,
        'error': None
      })

      logger.info(f"✅ Фоновое обучение {lottery_type} завершено успешно")

    except Exception as e:
      logger.error(f"❌ Ошибка фонового обучения {lottery_type}: {e}")
      self.training_status[lottery_type].update({
        'is_training': False,
        'training_progress': 0,
        'error': str(e)
      })

  async def _train_models_async(self, lottery_type: str, df_history, lottery_config: dict):
    """Асинхронное обучение в отдельном потоке"""

    def train_rf():
      try:
        self.training_status[lottery_type]['training_progress'] = 25
        rf_model = self.sync_manager.get_rf_model(lottery_type, lottery_config)
        rf_model.train(df_history)
        return rf_model.is_trained
      except Exception as e:
        logger.error(f"RF обучение {lottery_type}: {e}")
        return False

    def train_lstm():
      try:
        self.training_status[lottery_type]['training_progress'] = 75
        lstm_model = self.sync_manager.get_lstm_model(lottery_type, lottery_config)
        lstm_model.train(df_history)
        return lstm_model.is_trained
      except Exception as e:
        logger.error(f"LSTM обучение {lottery_type}: {e}")
        return False

    # Обучаем RF модель
    rf_success = await asyncio.get_event_loop().run_in_executor(
      self.executor, train_rf
    )

    # Обучаем LSTM модель
    lstm_success = await asyncio.get_event_loop().run_in_executor(
      self.executor, train_lstm
    )

    logger.info(f"Обучение {lottery_type}: RF={rf_success}, LSTM={lstm_success}")

  def get_training_status(self, lottery_type: str = None) -> Dict:
    """Возвращает статус обучения"""
    if lottery_type:
      return self.training_status.get(lottery_type, {})
    return self.training_status

  async def predict_combination(self, lottery_type: str, lottery_config: dict,
                                last_f1, last_f2, df_history=None):
    """Асинхронное предсказание комбинации"""
    try:
      rf_model = await self.get_rf_model(lottery_type, lottery_config)

      # Предсказание в отдельном потоке
      prediction = await asyncio.get_event_loop().run_in_executor(
        self.executor,
        rf_model.predict_next_combination,
        last_f1, last_f2, df_history
      )

      return prediction

    except Exception as e:
      logger.error(f"Ошибка асинхронного предсказания {lottery_type}: {e}")
      return None, None


# Глобальный асинхронный менеджер
ASYNC_MODEL_MANAGER = AsyncModelManager(max_workers=6)