"""
Асинхронный менеджер данных для масштабирования
"""
import asyncio
from typing import Dict

import aiohttp
import pandas as pd
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import logging

from backend.app.core.data_manager import (
  LOTTERY_CONFIGS, get_current_config, scrape_stoloto_archive
)
from backend.app.core.database import DATABASE_URL, LotteryDraw

logger = logging.getLogger(__name__)

# Асинхронный движок БД
async_engine = create_async_engine(
  DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
  pool_size=30,
  max_overflow=50,
  echo=False
)

AsyncSessionLocal = sessionmaker(
  async_engine, class_=AsyncSession, expire_on_commit=False
)


class AsyncDataManager:
  """
  Асинхронный менеджер данных с пулом соединений
  """

  def __init__(self, max_workers: int = 8):
    self.max_workers = max_workers
    self.executor = ThreadPoolExecutor(max_workers=max_workers)
    self.update_locks: Dict[str, asyncio.Lock] = {}
    self.update_in_progress: Dict[str, bool] = {}

    # Создаем локи для каждой лотереи
    for lottery_type in LOTTERY_CONFIGS.keys():
      self.update_locks[lottery_type] = asyncio.Lock()
      self.update_in_progress[lottery_type] = False

  async def fetch_draws_async(self, lottery_type: str, limit: int = None) -> pd.DataFrame:
    """
    Асинхронная загрузка тиражей из БД
    """
    try:
      async with AsyncSessionLocal() as session:
        # Выполняем запрос в отдельном потоке
        query_func = lambda: self._sync_fetch_draws(lottery_type, limit)
        df = await asyncio.get_event_loop().run_in_executor(
          self.executor, query_func
        )
        return df

    except Exception as e:
      logger.error(f"Ошибка асинхронной загрузки {lottery_type}: {e}")
      return pd.DataFrame()

  def _sync_fetch_draws(self, lottery_type: str, limit: int = None) -> pd.DataFrame:
    """Синхронная функция для выполнения в потоке"""
    from backend.app.core.data_manager import fetch_draws_from_db
    from backend.app.core.lottery_context import LotteryContext

    with LotteryContext(lottery_type):
      return fetch_draws_from_db()

  async def update_lottery_data_background(self, lottery_type: str):
    """
    Фоновое обновление данных лотереи без блокировки API
    """
    # Проверяем, не идет ли уже обновление
    if self.update_in_progress.get(lottery_type, False):
      logger.info(f"⏭️ {lottery_type}: обновление уже выполняется, пропускаем")
      return False

    async with self.update_locks[lottery_type]:
      self.update_in_progress[lottery_type] = True
      logger.info(f"🔄 Фоновое обновление данных для {lottery_type}")

      try:
        # Выполняем в отдельном потоке
        update_func = lambda: self._sync_update_lottery(lottery_type)
        result = await asyncio.get_event_loop().run_in_executor(
          self.executor, update_func
        )

        return result
      finally:
        self.update_in_progress[lottery_type] = False

        logger.info(f"✅ Фоновое обновление {lottery_type} завершено: {result}")
        return result

  def _sync_update_lottery(self, lottery_type: str) -> bool:
    """Синхронное обновление в потоке"""
    try:
      from backend.app.core.data_manager import update_database_from_source
      from backend.app.core.lottery_context import LotteryContext

      with LotteryContext(lottery_type):
        update_database_from_source()
        return True

    except Exception as e:
      logger.error(f"Ошибка синхронного обновления {lottery_type}: {e}")
      return False

  async def parallel_update_all_lotteries(self):
    """
    Параллельное обновление всех лотерей
    """
    logger.info("🚀 Начало параллельного обновления всех лотерей")

    # Создаем задачи для всех лотерей
    tasks = []
    for lottery_type in LOTTERY_CONFIGS.keys():
      task = asyncio.create_task(
        self.update_lottery_data_background(lottery_type)
      )
      tasks.append((lottery_type, task))

    # Ждем завершения всех задач
    results = {}
    for lottery_type, task in tasks:
      try:
        result = await task
        results[lottery_type] = result
      except Exception as e:
        logger.error(f"Ошибка параллельного обновления {lottery_type}: {e}")
        results[lottery_type] = False

    logger.info(f"📊 Результаты параллельного обновления: {results}")
    return results


# Глобальный асинхронный менеджер данных
ASYNC_DATA_MANAGER = AsyncDataManager(max_workers=8)