from fastapi import APIRouter, Depends, Path, HTTPException, UploadFile, File
import tempfile
import os

from backend.app.core import data_manager
from backend.app.models.schemas import DataUpdateResponse
from backend.app.core.lottery_context import LotteryContext

router = APIRouter()


@router.post("/import-history", response_model=DataUpdateResponse, summary="Загрузить историю тиражей из CSV")
async def import_history_from_csv(
    file: UploadFile = File(...),
    lottery_type: str = Path(..., description="Тип лотереи: '4x20' или '5x36plus'")
):
  """
  Импортирует исторические данные из CSV файла в базу данных для текущей лотереи.
  Файл должен соответствовать формату, описанному в data_manager.
  """
  if lottery_type not in data_manager.LOTTERY_CONFIGS:
    raise HTTPException(status_code=404, detail="Lottery type not found")
    
  if not file.filename.endswith('.csv'):
    raise HTTPException(status_code=400, detail="Неверный формат файла. Требуется CSV.")

  try:
    # FastAPI UploadFile работает с временными файлами, но для надежности
    # явно сохраним его и передадим путь в data_manager
    contents = await file.read()

    with tempfile.NamedTemporaryFile(mode='wb', suffix='.csv', delete=False) as f:
      f.write(contents)
      temp_path = f.name

    df = data_manager.import_csv_data(temp_path, lottery_type)
    os.unlink(temp_path)

    if df.empty:
      raise HTTPException(status_code=400,
                          detail="Данные из файла не были импортированы. Проверьте формат файла и его содержимое.")

    with LotteryContext(lottery_type):
      draws_in_db = len(data_manager.fetch_draws_from_db())

    return DataUpdateResponse(
      status="success",
      message=f"Успешно импортировано {len(df)} тиражей для лотереи {lottery_type}.",
      draws_in_db=draws_in_db
    )
  except Exception as e:
    raise HTTPException(status_code=500, detail=f"Произошла ошибка при импорте: {e}")


@router.post("/update-source", response_model=DataUpdateResponse, summary="Принудительно обновить данные из источника")
def force_update_from_source(lottery_type: str = Path(..., description="Тип лотереи: '4x20' или '5x36plus'")):
  """
  Запускает принудительное обновление исторических данных с API Столото
  для текущей лотереи и очищает кэш.
  """
  if lottery_type not in data_manager.LOTTERY_CONFIGS:
    raise HTTPException(status_code=404, detail="Lottery type not found")
    
  try:
    # Логика обновления уже есть в data_manager
    with LotteryContext(lottery_type):
      data_manager.update_database_from_source()
      draws_in_db = len(data_manager.fetch_draws_from_db())

    # В реальном приложении здесь также нужно будет очистить кэш,
    # но так как кэш привязан к серверному процессу, прямого способа нет,
    # кроме как дождаться истечения его срока.

    return DataUpdateResponse(
      status="success",
      message=f"Обновление данных для лотереи {lottery_type} запущено и завершено.",
      draws_in_db=draws_in_db
    )
  except Exception as e:
    raise HTTPException(status_code=500, detail=f"Ошибка при обновлении данных: {e}")


@router.get("/scheduler/status", summary="Статус планировщика автообновления")
async def get_scheduler_status():
  """
  Возвращает статус планировщика автоматического обновления данных
  """
  try:
    from backend.app.core.async_scheduler import GLOBAL_ASYNC_SCHEDULER
    return GLOBAL_ASYNC_SCHEDULER.get_scheduler_status()
  except Exception as e:
    raise HTTPException(status_code=500, detail=f"Ошибка получения статуса планировщика: {e}")


@router.post("/scheduler/manual-update", summary="Ручное обновление данных")
async def manual_update_all():
  """
  Запускает ручное обновление данных для всех лотерей
  """
  try:
    from backend.app.core.async_data_manager import ASYNC_DATA_MANAGER
    
    results = await ASYNC_DATA_MANAGER.parallel_update_all_lotteries()
    
    return {
      "status": "success",
      "message": "Ручное обновление завершено",
      "results": results
    }
    
  except Exception as e:
    raise HTTPException(status_code=500, detail=f"Ошибка ручного обновления: {e}")


@router.post("/scheduler/manual-update-current", summary="Ручное обновление текущей лотереи")  
async def manual_update_current_lottery(lottery_type: str = Path(..., description="Тип лотереи: '4x20' или '5x36plus'")):
  """
  Запускает ручное обновление данных для текущей лотереи
  """
  if lottery_type not in data_manager.LOTTERY_CONFIGS:
    raise HTTPException(status_code=404, detail="Lottery type not found")
    
  try:
    from backend.app.core.async_data_manager import ASYNC_DATA_MANAGER
    
    # Получаем количество тиражей до обновления
    with LotteryContext(lottery_type):
      draws_before = len(data_manager.fetch_draws_from_db())
    
    # Запускаем обновление
    updated = await ASYNC_DATA_MANAGER.update_lottery_data_background(lottery_type)
    
    # Получаем количество тиражей после обновления
    with LotteryContext(lottery_type):
      draws_after = len(data_manager.fetch_draws_from_db())
      
    new_draws = draws_after - draws_before
    
    return {
      "status": "success" if updated else "no_updates",
      "lottery_type": lottery_type,
      "updated": updated,
      "draws_before": draws_before,
      "draws_after": draws_after,
      "new_draws": new_draws,
      "message": f"Обновление {lottery_type}: {'найдены новые тиражи' if new_draws > 0 else 'новых тиражей нет'}"
    }
    
  except Exception as e:
    raise HTTPException(status_code=500, detail=f"Ошибка обновления {lottery_type}: {e}")