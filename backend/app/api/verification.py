from fastapi import APIRouter, Depends, Path, HTTPException, UploadFile, File
from typing import List
import pandas as pd
import io
from collections import defaultdict

from backend.app.core import ticket_verifier, data_manager, utils
from backend.app.models.schemas import TicketVerificationRequest, TicketCheckResponse, VerificationResult
from .analysis import set_lottery_context  # Используем ту же зависимость

router = APIRouter()


@router.post("/verify-ticket", response_model=TicketCheckResponse, summary="Проверить один билет по всей истории")
def verify_single_ticket(ticket: TicketVerificationRequest, context: None = Depends(set_lottery_context)):
  """
  Проверяет одну комбинацию (билет) по всей доступной истории тиражей.
  """
  df_history = data_manager.fetch_draws_from_db()
  if df_history.empty:
    raise HTTPException(status_code=404, detail="История тиражей не найдена.")

  # Используем существующую логику из ticket_verifier
  f1_str = utils.format_numbers(ticket.field1)
  f2_str = utils.format_numbers(ticket.field2)

  results_list = ticket_verifier.verify_ticket_against_history(f1_str, f2_str, df_history)

  # Проверяем, является ли результат сообщением "Без выигрыша"
  is_winner = not (len(results_list) == 1 and results_list[0].get("Категория") == "-")

  # Преобразуем результат в Pydantic модель
  wins = [VerificationResult(
    draw_number=res.get("Тираж"),
    draw_date=res.get("Дата тиража"),
    winning_numbers=res.get("Выигрышные номера"),
    matches=res.get("Совпадения"),
    category=res.get("Категория")
  ) for res in results_list if is_winner]

  return TicketCheckResponse(
    ticket_checked=f"П1: {f1_str} | П2: {f2_str}",
    is_winner=is_winner,
    wins=wins
  )


@router.post("/verify-csv", response_model=List[TicketCheckResponse], summary="Проверить все билеты из CSV файла")
async def verify_csv_tickets(file: UploadFile = File(...), context: None = Depends(set_lottery_context)):
  """
  Загружает CSV файл с колонками 'Поле1' и 'Поле2', проверяет каждый билет
  и возвращает сгруппированный результат для каждого билета.
  """
  if not file.filename.endswith('.csv'):
    raise HTTPException(status_code=400, detail="Неверный формат файла. Требуется CSV.")

  df_history = data_manager.fetch_draws_from_db()
  if df_history.empty:
    raise HTTPException(status_code=404, detail="История тиражей не найдена.")

  try:
    contents = await file.read()
    buffer = io.StringIO(contents.decode('utf-8'))
    tickets_df = pd.read_csv(buffer)
    if 'Поле1' not in tickets_df.columns or 'Поле2' not in tickets_df.columns:
      raise HTTPException(status_code=400, detail="В CSV файле отсутствуют обязательные колонки 'Поле1' и/или 'Поле2'.")
  except Exception as e:
    raise HTTPException(status_code=400, detail=f"Ошибка чтения или парсинга CSV файла: {e}")

  # --- КОРРЕКТНАЯ ЛОГИКА ВМЕСТО ЗАГЛУШКИ ---

  # 1. Получаем плоский список всех выигрышей по всем билетам
  all_wins_flat = ticket_verifier.verify_multiple_tickets_from_df(tickets_df, df_history)

  # 2. Группируем выигрыши по идентификатору билета
  grouped_wins = defaultdict(list)
  for win in all_wins_flat:
    # Пропускаем сообщения "без выигрыша"
    if win.get("Категория") != "-":
      ticket_id = win.get("Билет")
      grouped_wins[ticket_id].append(win)

  # 3. Формируем финальный ответ, проходя по исходному списку билетов
  final_response = []
  for index, row in tickets_df.iterrows():
    f1_str = str(row['Поле1'])
    f2_str = str(row['Поле2'])
    ticket_id = f"Билет {index + 1} ({f1_str} | {f2_str})"

    ticket_wins = grouped_wins.get(ticket_id, [])
    is_winner = len(ticket_wins) > 0

    # Преобразуем выигрыши в Pydantic модель
    wins_models = [VerificationResult(
      draw_number=res.get("Тираж"),
      draw_date=res.get("Дата тиража"),
      winning_numbers=res.get("Выигрышные номера"),
      matches=res.get("Совпадения"),
      category=res.get("Категория")
    ) for res in ticket_wins]

    final_response.append(
      TicketCheckResponse(
        ticket_checked=ticket_id,
        is_winner=is_winner,
        wins=wins_models
      )
    )

  return final_response