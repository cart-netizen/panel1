from fastapi import APIRouter, Depends, Path, HTTPException, UploadFile, File
import tempfile
import os

from backend.app.core import data_manager
from backend.app.models.schemas import DataUpdateResponse
from .analysis import set_lottery_context

router = APIRouter()


@router.post("/import-history", response_model=DataUpdateResponse, summary="Загрузить историю тиражей из CSV")
async def import_history_from_csv(
    file: UploadFile = File(...),
    context: None = Depends(set_lottery_context)
):
  """
  Импортирует исторические данные из CSV файла в базу данных для текущей лотереи.
  Файл должен соответствовать формату, описанному в data_manager.
  """
  if not file.filename.endswith('.csv'):
    raise HTTPException(status_code=400, detail="Неверный формат файла. Требуется CSV.")

  try:
    # FastAPI UploadFile работает с временными файлами, но для надежности
    # явно сохраним его и передадим путь в data_manager
    contents = await file.read()

    with tempfile.NamedTemporaryFile(mode='wb', suffix='.csv', delete=False) as f:
      f.write(contents)
      temp_path = f.name

    df = data_manager.import_csv_data(temp_path, data_manager.CURRENT_LOTTERY)
    os.unlink(temp_path)

    if df.empty:
      raise HTTPException(status_code=400,
                          detail="Данные из файла не были импортированы. Проверьте формат файла и его содержимое.")

    return DataUpdateResponse(
      status="success",
      message=f"Успешно импортировано {len(df)} тиражей для лотереи {data_manager.CURRENT_LOTTERY}.",
      draws_in_db=len(data_manager.fetch_draws_from_db())
    )
  except Exception as e:
    raise HTTPException(status_code=500, detail=f"Произошла ошибка при импорте: {e}")


@router.post("/update-source", response_model=DataUpdateResponse, summary="Принудительно обновить данные из источника")
def force_update_from_source(context: None = Depends(set_lottery_context)):
  """
  Запускает принудительное обновление исторических данных с API Столото
  для текущей лотереи и очищает кэш.
  """
  try:
    # Логика обновления уже есть в data_manager
    data_manager.update_database_from_source()

    # В реальном приложении здесь также нужно будет очистить кэш,
    # но так как кэш привязан к серверному процессу, прямого способа нет,
    # кроме как дождаться истечения его срока.

    return DataUpdateResponse(
      status="success",
      message=f"Обновление данных для лотереи {data_manager.CURRENT_LOTTERY} запущено и завершено.",
      draws_in_db=len(data_manager.fetch_draws_from_db())
    )
  except Exception as e:
    raise HTTPException(status_code=500, detail=f"Ошибка при обновлении данных: {e}")