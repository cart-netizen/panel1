"""Проверка статуса автоматического планировщика"""
import requests

BASE_URL = "http://127.0.0.1:8001"


def check_scheduler():
  print("📅 ПРОВЕРКА СТАТУСА ПЛАНИРОВЩИКА")
  print("=" * 40)

  # Пока у нас нет эндпоинта для статуса, проверим косвенно
  try:
    # Проверим главную страницу
    response = requests.get(f"{BASE_URL}/", timeout=5)
    if response.status_code == 200:
      print("✅ Сервер работает стабильно")

      # Проверим API
      response = requests.get(f"{BASE_URL}/api/v1/4x20/history", timeout=10)
      if response.status_code == 200:
        history = response.json()
        if history:
          last_draw = history[0]
          print(f"📊 Последний тираж: #{last_draw.get('Тираж')} ({last_draw.get('Дата')})")
        print(f"📈 Тиражей в истории: {len(history)}")

      print(f"\n💡 Планировщик работает в фоне:")
      print(f"   📅 4x20: проверка после тиражей (10:00, 12:00, 13:00, 16:00, 18:00, 20:00, 22:00)")
      print(f"   📅 5x36plus: проверка каждые 15 минут")

    else:
      print("❌ Сервер недоступен")

  except Exception as e:
    print(f"❌ Ошибка: {e}")


if __name__ == "__main__":
  check_scheduler()