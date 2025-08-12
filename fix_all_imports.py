"""
Универсальный поиск и исправление всех импортов в проекте
"""
import os
import re
import glob


def find_problematic_imports():
  """Находит все файлы с проблемными импортами"""
  print("🔍 ПОИСК ПРОБЛЕМНЫХ ИМПОРТОВ")
  print("=" * 50)

  problematic_files = []

  # Паттерны проблемных импортов
  patterns = [
    r'from app\.core',
    r'from app\.api',
    r'from app\.models',
    r'import app\.core',
    r'import app\.api',
    r'import app\.models'
  ]

  # Ищем во всех Python файлах
  for root, dirs, files in os.walk('.'):
    # Пропускаем .venv и другие ненужные папки
    dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']

    for file in files:
      if file.endswith('.py'):
        file_path = os.path.join(root, file)

        try:
          with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

          found_issues = []
          for pattern in patterns:
            matches = re.findall(pattern, content)
            if matches:
              found_issues.extend(matches)

          if found_issues:
            problematic_files.append({
              'path': file_path,
              'issues': found_issues
            })
            print(f"❌ {file_path}")
            for issue in set(found_issues):
              print(f"   📍 {issue}")

        except Exception as e:
          print(f"⚠️ Ошибка чтения {file_path}: {e}")

  return problematic_files


def fix_file_imports(file_path):
  """Исправляет импорты в одном файле"""
  try:
    with open(file_path, 'r', encoding='utf-8') as f:
      content = f.read()

    original_content = content

    # Исправляем импорты
    content = re.sub(r'from app\.core', 'from backend.app.core', content)
    content = re.sub(r'from app\.api', 'from backend.app.api', content)
    content = re.sub(r'from app\.models', 'from backend.app.models', content)
    content = re.sub(r'import app\.core', 'import backend.app.core', content)
    content = re.sub(r'import app\.api', 'import backend.app.api', content)
    content = re.sub(r'import app\.models', 'import backend.app.models', content)

    # Сохраняем если были изменения
    if content != original_content:
      with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
      print(f"✅ Исправлен: {file_path}")
      return True

    return False

  except Exception as e:
    print(f"❌ Ошибка исправления {file_path}: {e}")
    return False


def fix_all_imports():
  """Исправляет все найденные проблемы"""
  print("🔧 МАССОВОЕ ИСПРАВЛЕНИЕ ИМПОРТОВ")
  print("=" * 50)

  # 1. Находим проблемы
  problematic_files = find_problematic_imports()

  if not problematic_files:
    print("✅ Проблемных импортов не найдено!")
    return

  print(f"\n📊 Найдено проблемных файлов: {len(problematic_files)}")

  # 2. Исправляем
  fixed_count = 0
  for file_info in problematic_files:
    if fix_file_imports(file_info['path']):
      fixed_count += 1

  print(f"\n📈 РЕЗУЛЬТАТЫ:")
  print(f"   Обработано файлов: {len(problematic_files)}")
  print(f"   Исправлено файлов: {fixed_count}")

  # 3. Повторная проверка
  print(f"\n🔍 Повторная проверка...")
  remaining_issues = find_problematic_imports()

  if not remaining_issues:
    print("🎉 Все импорты исправлены!")
  else:
    print(f"⚠️ Осталось проблем в {len(remaining_issues)} файлах")


def check_specific_files():
  """Проверяет конкретные проблемные файлы"""
  print("\n🎯 ПРОВЕРКА КЛЮЧЕВЫХ ФАЙЛОВ")
  print("=" * 30)

  key_files = [
    'backend/app/main.py',
    'backend/app/core/lottery_context.py',
    'backend/app/core/ai_model.py',
    'backend/app/core/combination_generator.py',
    'backend/app/core/ticket_verifier.py',
    'backend/app/api/analysis.py',
    'backend/app/api/generation.py'
  ]

  for file_path in key_files:
    if os.path.exists(file_path):
      try:
        with open(file_path, 'r', encoding='utf-8') as f:
          content = f.read()

        # Ищем проблемные импорты
        if re.search(r'from app\.', content) or re.search(r'import app\.', content):
          print(f"❌ {file_path} - есть проблемы")
          # Показываем первые несколько строк с проблемами
          lines = content.split('\n')
          for i, line in enumerate(lines[:20], 1):
            if re.search(r'from app\.|import app\.', line):
              print(f"   Строка {i}: {line.strip()}")
        else:
          print(f"✅ {file_path} - импорты корректны")

      except Exception as e:
        print(f"⚠️ {file_path} - ошибка чтения: {e}")
    else:
      print(f"❓ {file_path} - файл не найден")


if __name__ == "__main__":
  print("🛠️ УНИВЕРСАЛЬНОЕ ИСПРАВЛЕНИЕ ИМПОРТОВ")
  print("=" * 60)

  # Проверяем ключевые файлы
  check_specific_files()

  # Исправляем все импорты
  fix_all_imports()

  print(f"\n🎯 После исправления перезапустите сервер:")
  print(f"uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000")