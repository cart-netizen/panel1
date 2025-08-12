"""
Асинхронный планировщик для обновлений и обучения
"""
import asyncio
from datetime import datetime, timedelta
import logging
from typing import Dict

from backend.app.core.async_data_manager import ASYNC_DATA_MANAGER
from backend.app.core.async_ai_model import ASYNC_MODEL_MANAGER
from backend.app.core.data_manager import LOTTERY_CONFIGS

logger = logging.getLogger(__name__)


class AsyncAutoScheduler:
  """
  Асинхронный планировщик для фонового обновления данных и обучения моделей
  """

  def __init__(self):
    self.is_running = False
    self.tasks: Dict[str, asyncio.Task] = {}
    self.update_intervals = {
      '4x20': 300,  # 5 минут
      '5x36plus': 900  # 15 минут
    }

  async def start_async_scheduler(self):
    """Запускает асинхронный планировщик"""
    if self.is_running:
      logger.warning("Асинхронный планировщик уже запущен")
      return

    self.is_running = True
    logger.info("🚀 Запуск асинхронного планировщика")

    # Запускаем задачи для каждой лотереи
    for lottery_type in LOTTERY_CONFIGS.keys():
      task = asyncio.create_task(
        self._schedule_lottery_updates_async(lottery_type)
      )
      self.tasks[lottery_type] = task
      logger.info(f"📅 Асинхронный планировщик запущен для {lottery_type}")

    logger.info(f"✅ Асинхронный планировщик активен для {len(LOTTERY_CONFIGS)} лотерей")

  async def stop_async_scheduler(self):
    """Останавливает асинхронный планировщик"""
    if not self.is_running:
      return

    self.is_running = False
    logger.info("🛑 Остановка асинхронного планировщика...")

    # Отменяем все задачи
    for lottery_type, task in self.tasks.items():
      if not task.done():
        task.cancel()
        try:
          await task
        except asyncio.CancelledError:
          pass
      logger.info(f"📅 Планировщик остановлен для {lottery_type}")

    self.tasks.clear()
    logger.info("✅ Асинхронный планировщик полностью остановлен")

  async def _schedule_lottery_updates_async(self, lottery_type: str):
    """Асинхронное планирование обновлений для лотереи"""
    interval = self.update_intervals.get(lottery_type, 600)

    while self.is_running:
      try:
        logger.info(f"🔄 Проверка обновлений для {lottery_type}")

        # Параллельно обновляем данные и планируем обучение
        update_task = asyncio.create_task(
          ASYNC_DATA_MANAGER.update_lottery_data_background(lottery_type)
        )

        # Ждем обновления данных
        data_updated = await update_task

        if data_updated:
          logger.info(f"📊 Данные {lottery_type} обновлены, запускаем фоновое обучение")

          # Загружаем свежие данные для обучения
          df_history = await ASYNC_DATA_MANAGER.fetch_draws_async(lottery_type)

          if not df_history.empty:
            # Запускаем обучение в фоне (не ждем завершения)
            lottery_config = LOTTERY_CONFIGS[lottery_type]
            asyncio.create_task(
              ASYNC_MODEL_MANAGER.train_models_background(
                lottery_type, df_history, lottery_config
              )
            )

        # Ждем до следующей проверки
        await asyncio.sleep(interval)

      except asyncio.CancelledError:
        break
      except Exception as e:
        logger.error(f"❌ Ошибка в асинхронном планировщике {lottery_type}: {e}")
        await asyncio.sleep(60)  # Пауза при ошибке

  def get_scheduler_status(self) -> Dict:
    """Возвращает статус планировщика"""
    return {
      'is_running': self.is_running,
      'active_tasks': len([t for t in self.tasks.values() if not t.done()]),
      'lottery_intervals': self.update_intervals,
      'model_training_status': ASYNC_MODEL_MANAGER.get_training_status()
    }


# Глобальный асинхронный планировщик
GLOBAL_ASYNC_SCHEDULER = AsyncAutoScheduler()