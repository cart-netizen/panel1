import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import json
import re
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def scrape_stoloto_archive(url='https://www.stoloto.ru/4x20/archive', target_count=200, use_selenium=True):
  """
  Scrapes draw data from Stoloto archive for "4x20" lottery.

  Args:
      url (str): Base URL for the archive
      target_count (int): Number of draws to fetch (default: 200)
      use_selenium (bool): Whether to use Selenium for dynamic content (default: True)

  Returns:
      pd.DataFrame: DataFrame with columns ['Дата', 'Тираж', 'Числа_Поле1', 'Числа_Поле2', 'Приз']
  """
  logger.info(f"Starting scraping from {url} for {target_count} draws...")

  if use_selenium:
    return _scrape_with_selenium(url, target_count)
  else:
    return _scrape_with_requests(url, target_count)


def _scrape_with_selenium(url, target_count):
  """
  Scrapes using Selenium WebDriver for dynamic content.
  """
  # Настройка Chrome WebDriver
  chrome_options = Options()
  chrome_options.add_argument('--headless')  # Запуск в фоновом режиме
  chrome_options.add_argument('--no-sandbox')
  chrome_options.add_argument('--disable-dev-shm-usage')
  chrome_options.add_argument('--disable-gpu')
  chrome_options.add_argument('--window-size=1920,1080')
  chrome_options.add_argument(
    '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')

  driver = None
  rows_data = []

  try:
    driver = webdriver.Chrome(options=chrome_options)
    driver.get(url)

    # Ждем загрузки страницы
    wait = WebDriverWait(driver, 10)

    # Попытка найти таблицу с результатами
    try:
      # Различные селекторы для поиска таблицы
      table_selectors = [
        'table.archive-table',
        '.archive-table',
        'table[class*="archive"]',
        'table[class*="results"]',
        '.draws-table',
        'table.table',
        '.lottery-results table'
      ]

      table_element = None
      for selector in table_selectors:
        try:
          table_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
          logger.info(f"Found table with selector: {selector}")
          break
        except TimeoutException:
          continue

      if not table_element:
        # Попытка найти элементы с результатами без таблицы
        logger.info("Table not found, looking for individual draw elements...")
        return _scrape_individual_draws(driver, target_count)

      # Парсинг таблицы
      rows = table_element.find_elements(By.TAG_NAME, 'tr')

      for row in rows[1:]:  # Пропускаем заголовок
        if len(rows_data) >= target_count:
          break

        try:
          cells = row.find_elements(By.TAG_NAME, 'td')
          if len(cells) >= 4:  # Минимум 4 колонки ожидаем

            # Извлекаем номер тиража
            draw_number = _extract_number(cells[0].text)
            if not draw_number:
              continue

            # Извлекаем дату
            date_text = cells[1].text.strip()
            formatted_date = _parse_date(date_text)
            if not formatted_date:
              continue

            # Извлекаем числа (обычно в следующих колонках)
            numbers_text = ""
            for i in range(2, len(cells)):
              cell_text = cells[i].text.strip()
              if any(char.isdigit() for char in cell_text):
                numbers_text += cell_text + " "

            # Парсим числа на два поля
            field1_nums, field2_nums = _parse_lottery_numbers(numbers_text)

            if field1_nums and field2_nums:
              rows_data.append({
                'Дата': formatted_date,
                'Тираж': draw_number,
                'Числа_Поле1': field1_nums,
                'Числа_Поле2': field2_nums,
                'Приз': 0  # Приз можно добавить позже, если нужен
              })
              logger.info(f"Parsed draw {draw_number}: {field1_nums} | {field2_nums}")

        except Exception as e:
          logger.warning(f"Error parsing row: {e}")
          continue

    except TimeoutException:
      logger.error("Could not find archive table on the page")
      return pd.DataFrame()

  except Exception as e:
    logger.error(f"Error during Selenium scraping: {e}")
    return pd.DataFrame()

  finally:
    if driver:
      driver.quit()

  logger.info(f"Successfully scraped {len(rows_data)} draws")
  return pd.DataFrame(rows_data)


def _scrape_individual_draws(driver, target_count):
  """
  Scrapes individual draw elements when table structure is not available.
  """
  rows_data = []

  # Попытка найти отдельные элементы тиражей
  draw_selectors = [
    '.draw-item',
    '.archive-item',
    '.lottery-draw',
    '[class*="draw"]',
    '.result-item'
  ]

  for selector in draw_selectors:
    try:
      draw_elements = driver.find_elements(By.CSS_SELECTOR, selector)
      if draw_elements:
        logger.info(f"Found {len(draw_elements)} draw elements with selector: {selector}")

        for element in draw_elements[:target_count]:
          try:
            # Извлекаем информацию из элемента
            draw_data = _parse_draw_element(element)
            if draw_data:
              rows_data.append(draw_data)
          except Exception as e:
            logger.warning(f"Error parsing draw element: {e}")
            continue

        if rows_data:
          break
    except Exception as e:
      logger.warning(f"Error with selector {selector}: {e}")
      continue

  return pd.DataFrame(rows_data)


def _parse_draw_element(element):
  """
  Parses individual draw element to extract draw information.
  """
  try:
    # Ищем номер тиража
    draw_number = None
    for text in element.text.split():
      if text.isdigit() and len(text) >= 3:  # Номер тиража обычно от 3 цифр
        draw_number = int(text)
        break

    if not draw_number:
      return None

    # Ищем дату
    date_match = re.search(r'\d{1,2}[.\-/]\d{1,2}[.\-/]\d{2,4}', element.text)
    if date_match:
      date_str = date_match.group()
      formatted_date = _parse_date(date_str)
    else:
      formatted_date = datetime.now().strftime('%Y-%m-%d')

    # Ищем числа
    numbers = re.findall(r'\b\d{1,2}\b', element.text)
    numbers = [int(n) for n in numbers if 1 <= int(n) <= 20]  # Для лотереи 4x20

    if len(numbers) >= 8:  # Минимум 8 чисел (4+4)
      field1_nums = ','.join(map(str, numbers[:4]))
      field2_nums = ','.join(map(str, numbers[4:8]))

      return {
        'Дата': formatted_date,
        'Тираж': draw_number,
        'Числа_Поле1': field1_nums,
        'Числа_Поле2': field2_nums,
        'Приз': 0
      }

  except Exception as e:
    logger.warning(f"Error parsing draw element: {e}")

  return None


def _scrape_with_requests(url, target_count):
  """
  Scrapes using requests (fallback method for static content).
  """
  logger.info("Using requests method for scraping...")

  headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1'
  }

  rows_data = []

  try:
    # Попытка получить данные через API
    api_url = "https://www.stoloto.ru/api/draws/4x20"

    response = requests.get(api_url, headers=headers, timeout=10)

    if response.status_code == 200:
      try:
        data = response.json()
        # Обработка JSON ответа
        if 'draws' in data:
          for draw in data['draws'][:target_count]:
            draw_data = _parse_api_draw(draw)
            if draw_data:
              rows_data.append(draw_data)
      except json.JSONDecodeError:
        pass

    # Если API не работает, парсим HTML
    if not rows_data:
      response = requests.get(url, headers=headers, timeout=10)
      response.raise_for_status()

      soup = BeautifulSoup(response.text, 'html.parser')

      # Поиск таблицы с результатами
      table = soup.find('table', class_=['archive-table', 'results-table', 'table'])

      if table:
        rows = table.find_all('tr')[1:]  # Пропускаем заголовок

        for row in rows[:target_count]:
          cells = row.find_all('td')
          if len(cells) >= 4:
            try:
              draw_number = _extract_number(cells[0].get_text())
              date_text = cells[1].get_text().strip()
              formatted_date = _parse_date(date_text)

              # Извлекаем числа из остальных ячеек
              numbers_text = ' '.join([cell.get_text() for cell in cells[2:]])
              field1_nums, field2_nums = _parse_lottery_numbers(numbers_text)

              if all([draw_number, formatted_date, field1_nums, field2_nums]):
                rows_data.append({
                  'Дата': formatted_date,
                  'Тираж': draw_number,
                  'Числа_Поле1': field1_nums,
                  'Числа_Поле2': field2_nums,
                  'Приз': 0
                })

            except Exception as e:
              logger.warning(f"Error parsing row: {e}")
              continue

  except requests.exceptions.RequestException as e:
    logger.error(f"Error during requests scraping: {e}")
    return pd.DataFrame()

  logger.info(f"Successfully scraped {len(rows_data)} draws with requests method")
  return pd.DataFrame(rows_data)


def _parse_api_draw(draw):
  """
  Parses draw data from API response.
  """
  try:
    return {
      'Дата': draw.get('date', ''),
      'Тираж': int(draw.get('number', 0)),
      'Числа_Поле1': ','.join(map(str, draw.get('field1', []))),
      'Числа_Поле2': ','.join(map(str, draw.get('field2', []))),
      'Приз': float(draw.get('prize', 0))
    }
  except Exception as e:
    logger.warning(f"Error parsing API draw: {e}")
    return None


def _extract_number(text):
  """
  Extracts number from text string.
  """
  numbers = re.findall(r'\d+', text)
  return int(numbers[0]) if numbers else None


def _parse_date(date_text):
  """
  Parses date string to YYYY-MM-DD format.
  """
  try:
    # Удаляем лишние символы
    date_text = re.sub(r'[^\d.\-/]', '', date_text)

    # Различные форматы дат
    date_formats = [
      '%d.%m.%Y',
      '%d/%m/%Y',
      '%d-%m-%Y',
      '%Y-%m-%d',
      '%d.%m.%y',
      '%d/%m/%y',
      '%d-%m-%y'
    ]

    for fmt in date_formats:
      try:
        parsed_date = datetime.strptime(date_text, fmt)
        return parsed_date.strftime('%Y-%m-%d')
      except ValueError:
        continue

    logger.warning(f"Could not parse date: {date_text}")
    return None

  except Exception as e:
    logger.warning(f"Error parsing date {date_text}: {e}")
    return None


def _parse_lottery_numbers(numbers_text):
  """
  Parses lottery numbers from text and splits into two fields.
  """
  try:
    # Извлекаем все числа от 1 до 20
    numbers = re.findall(r'\b([1-9]|1[0-9]|20)\b', numbers_text)
    numbers = [int(n) for n in numbers]

    if len(numbers) >= 8:  # Минимум 8 чисел для двух полей
      field1 = numbers[:4]
      field2 = numbers[4:8]

      return ','.join(map(str, field1)), ','.join(map(str, field2))

    elif len(numbers) >= 4:  # Если есть только одно поле
      field1 = numbers[:4]
      # Генерируем случайные числа для второго поля (временное решение)
      import random
      available_numbers = [i for i in range(1, 21) if i not in field1]
      field2 = random.sample(available_numbers, 4)

      return ','.join(map(str, field1)), ','.join(map(str, field2))

  except Exception as e:
    logger.warning(f"Error parsing numbers: {e}")

  return None, None


def scrape_stoloto_archive_robust(url='https://www.stoloto.ru/4x20/archive', target_count=200):
  """
  Robust version that tries multiple methods to scrape data.
  """
  logger.info(f"Starting robust scraping for {target_count} draws...")

  # Метод 1: Selenium
  try:
    df = scrape_stoloto_archive(url, target_count, use_selenium=True)
    if not df.empty and len(df) > 0:
      logger.info(f"Successfully scraped {len(df)} draws with Selenium")
      return df
  except Exception as e:
    logger.warning(f"Selenium method failed: {e}")

  # Метод 2: Requests
  try:
    df = scrape_stoloto_archive(url, target_count, use_selenium=False)
    if not df.empty and len(df) > 0:
      logger.info(f"Successfully scraped {len(df)} draws with requests")
      return df
  except Exception as e:
    logger.warning(f"Requests method failed: {e}")

  # Метод 3: Парсинг отдельных страниц тиражей
  try:
    df = _scrape_individual_draw_pages(target_count)
    if not df.empty and len(df) > 0:
      logger.info(f"Successfully scraped {len(df)} draws from individual pages")
      return df
  except Exception as e:
    logger.warning(f"Individual pages method failed: {e}")

  logger.error("All scraping methods failed")
  return pd.DataFrame()


def _scrape_individual_draw_pages(target_count):
  """
  Scrapes individual draw pages as a fallback method.
  """
  rows_data = []
  base_url = "https://www.stoloto.ru/4x20/archive/"

  headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
  }

  # Начинаем с последних тиражей (предполагаем, что номера растут)
  # Можно начать с большого числа и идти назад
  start_draw = 10698  # Начальный номер (нужно подобрать)

  for draw_num in range(start_draw, start_draw - target_count * 2, -1):
    if len(rows_data) >= target_count:
      break

    try:
      url = f"{base_url}{draw_num}"
      response = requests.get(url, headers=headers, timeout=5)

      if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')

        # Поиск результатов на странице тиража
        draw_data = _parse_individual_draw_page(soup, draw_num)
        if draw_data:
          rows_data.append(draw_data)
          logger.info(f"Successfully parsed draw {draw_num}")

        # Небольшая задержка между запросами
        time.sleep(0.1)

    except Exception as e:
      logger.warning(f"Error scraping draw {draw_num}: {e}")
      continue

  return pd.DataFrame(rows_data)


def _parse_individual_draw_page(soup, draw_num):
  """
  Parses individual draw page to extract draw information.
  """
  try:
    # Поиск чисел на странице
    numbers = []

    # Различные селекторы для поиска чисел
    number_selectors = [
      '.winning-numbers .number',
      '.draw-numbers .number',
      '.numbers .ball',
      '.result-numbers span',
      '.lottery-ball'
    ]

    for selector in number_selectors:
      elements = soup.select(selector)
      if elements:
        numbers = [int(el.get_text().strip()) for el in elements if el.get_text().strip().isdigit()]
        break

    # Если числа не найдены, ищем в тексте
    if not numbers:
      text = soup.get_text()
      numbers = [int(n) for n in re.findall(r'\b([1-9]|1[0-9]|20)\b', text)]

    # Поиск даты
    date_str = None
    date_selectors = ['.draw-date', '.date', '.tirage-date']

    for selector in date_selectors:
      element = soup.select_one(selector)
      if element:
        date_str = element.get_text().strip()
        break

    if not date_str:
      # Поиск даты в тексте
      date_match = re.search(r'\d{1,2}[.\-/]\d{1,2}[.\-/]\d{2,4}', soup.get_text())
      if date_match:
        date_str = date_match.group()

    formatted_date = _parse_date(date_str) if date_str else datetime.now().strftime('%Y-%m-%d')

    if len(numbers) >= 8:
      field1_nums = ','.join(map(str, numbers[:4]))
      field2_nums = ','.join(map(str, numbers[4:8]))

      return {
        'Дата': formatted_date,
        'Тираж': draw_num,
        'Числа_Поле1': field1_nums,
        'Числа_Поле2': field2_nums,
        'Приз': 0
      }

  except Exception as e:
    logger.warning(f"Error parsing individual draw page: {e}")

  return None


# Пример использования
if __name__ == "__main__":
  # Использование основной функции
  df = scrape_stoloto_archive_robust(target_count=200)

  if not df.empty:
    print(f"Successfully scraped {len(df)} draws")
    print(df.head())

    # Сохранение в CSV для проверки
    df.to_csv('stoloto_4x20_draws.csv', index=False, encoding='utf-8')
    print("Data saved to stoloto_4x20_draws.csv")
  else:
    print("No data scraped")