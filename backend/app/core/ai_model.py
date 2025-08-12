import asyncio
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict

import numpy as np
import pandas as pd
try:
    import pytz
except ImportError:
    # Fallback для систем без pytz
    class MockTimezone:
        def localize(self, dt):
            return dt
        def __call__(self, zone_name):
            return self
    pytz = MockTimezone()
    pytz.timezone = lambda x: pytz
from sklearn.ensemble import RandomForestClassifier
import random
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import TensorDataset, DataLoader
from sklearn.preprocessing import MultiLabelBinarizer


class RFModel:
  """
  Универсальная Random Forest модель для предсказания лотерейных номеров.
  Автоматически адаптируется под любую конфигурацию лотереи.
  Обучает отдельные классификаторы для каждой позиции в каждом поле.
  """

  def __init__(self, lottery_config: dict, n_estimators=200, random_state=42, min_samples_leaf=3, max_depth=15):
    # Увеличиваем количество деревьев и добавляем ограничение глубины

    """
    Инициализация модели для конкретной конфигурации лотереи.

    Args:
        lottery_config: Словарь с конфигурацией лотереи (неизменяемый)
    """
    self.config = lottery_config.copy()  # Копия для защиты от мутаций
    self.lottery_type = self.config.get('db_table', '').replace('draws_', '')
    self.field1_size = self.config['field1_size']
    self.field2_size = self.config['field2_size']
    self.field1_max = self.config['field1_max']
    self.field2_max = self.config['field2_max']

    # Создаем модели для каждой позиции в каждом поле
    self.models_f1 = [
      RandomForestClassifier(
        n_estimators=n_estimators,
        random_state=random_state + i,  # Разные random_state для разнообразия
        min_samples_leaf=min_samples_leaf,
        max_depth=max_depth,
        n_jobs=-1
      )
      for i in range(self.field1_size)
    ]
    self.models_f2 = [
      RandomForestClassifier(
        n_estimators=n_estimators,
        random_state=random_state + i + self.field1_size,
        min_samples_leaf=min_samples_leaf,
        max_depth=max_depth,
        n_jobs=-1
      )
      for i in range(self.field2_size)
    ]

    self.is_trained = False
    self._classes_f1 = [np.array([]) for _ in range(self.field1_size)]
    self._classes_f2 = [np.array([]) for _ in range(self.field2_size)]

    # Кэш для признаков (для оптимизации)
    self._feature_cache = {}
    self._last_config_hash = None


  def _prepare_rf_data(self, df_history):
    """
    Универсальная подготовка расширенных данных для Random Forest обучения.
    Автоматически адаптируется под любую конфигурацию лотереи.

    Включает:
    - Числа из нескольких предыдущих тиражей
    - Частоты чисел за последние N тиражей
    - Время с последнего выпадения каждого числа
    - Статистики сумм и четности предыдущих тиражей
    - День недели тиража
    - Адаптивные признаки под размеры полей
    """


    if df_history.empty or 'Числа_Поле1_list' not in df_history.columns or 'Числа_Поле2_list' not in df_history.columns:
      print("AI Model (RF): Отсутствуют необходимые колонки для подготовки данных.")
      return None, None, None

    df_copy = df_history.copy()

    # Универсальная валидация списков чисел
    df_copy['Числа_Поле1_list'] = df_copy['Числа_Поле1_list'].apply(
      lambda x: x if isinstance(x, list) and len(x) == self.field1_size else None)
    df_copy['Числа_Поле2_list'] = df_copy['Числа_Поле2_list'].apply(
      lambda x: x if isinstance(x, list) and len(x) == self.field2_size else None)
    df_copy.dropna(subset=['Числа_Поле1_list', 'Числа_Поле2_list'], inplace=True)

    # Требуем больше истории для расширенных признаков
    lookback_draws = min(5, len(df_copy) // 2)  # Адаптивное окно
    min_required_rows = lookback_draws + 1

    if len(df_copy) < min_required_rows:
      print(f"AI Model (RF): Недостаточно строк данных для создания признаков (нужно минимум {min_required_rows}).")
      return None, None, None

    X_list = []
    Y_f1_list = [[] for _ in range(self.field1_size)]
    Y_f2_list = [[] for _ in range(self.field2_size)]

    # Предварительно вычисляем частоты для всех чисел
    from collections import Counter

    for i in range(lookback_draws, len(df_copy)):
      features = []

      # 1. Числа из последних N тиражей (отсортированные)
      total_numbers_per_draw = self.field1_size + self.field2_size
      for j in range(1, lookback_draws + 1):
        prev_f1 = sorted(df_copy.iloc[i - j]['Числа_Поле1_list'])
        prev_f2 = sorted(df_copy.iloc[i - j]['Числа_Поле2_list'])
        features.extend(prev_f1 + prev_f2)

      # 2. Частоты каждого числа за последние N тиражей
      freq_window = min(20, i)
      recent_draws_f1 = []
      recent_draws_f2 = []
      for k in range(max(0, i - freq_window), i):
        recent_draws_f1.extend(df_copy.iloc[k]['Числа_Поле1_list'])
        recent_draws_f2.extend(df_copy.iloc[k]['Числа_Поле2_list'])

      freq_counter_f1 = Counter(recent_draws_f1)
      freq_counter_f2 = Counter(recent_draws_f2)

      # Частоты для каждого числа в диапазонах полей
      for num in range(1, self.field1_max + 1):
        features.append(freq_counter_f1.get(num, 0))
      for num in range(1, self.field2_max + 1):
        features.append(freq_counter_f2.get(num, 0))

      # 3. Количество тиражей с последнего выпадения каждого числа
      last_appearance_f1 = {}
      last_appearance_f2 = {}
      for num in range(1, self.field1_max + 1):
        last_appearance_f1[num] = -1
      for num in range(1, self.field2_max + 1):
        last_appearance_f2[num] = -1

      # Ищем последнее появление каждого числа
      for k in range(i - 1, -1, -1):
        for num in df_copy.iloc[k]['Числа_Поле1_list']:
          if last_appearance_f1[num] == -1:
            last_appearance_f1[num] = i - k
        for num in df_copy.iloc[k]['Числа_Поле2_list']:
          if last_appearance_f2[num] == -1:
            last_appearance_f2[num] = i - k

      # Добавляем расстояния до последнего появления
      for num in range(1, self.field1_max + 1):
        features.append(last_appearance_f1[num] if last_appearance_f1[num] != -1 else freq_window)
      for num in range(1, self.field2_max + 1):
        features.append(last_appearance_f2[num] if last_appearance_f2[num] != -1 else freq_window)

      # 4. Статистики последних тиражей (адаптивно)
      stats_window = min(3, i)
      for j in range(1, stats_window + 1):
        prev_f1 = df_copy.iloc[i - j]['Числа_Поле1_list']
        prev_f2 = df_copy.iloc[i - j]['Числа_Поле2_list']

        # Сумма чисел
        features.append(sum(prev_f1))
        features.append(sum(prev_f2))

        # Количество четных чисел
        features.append(sum(1 for n in prev_f1 if n % 2 == 0))
        features.append(sum(1 for n in prev_f2 if n % 2 == 0))

        # Размах (макс - мин)
        features.append(max(prev_f1) - min(prev_f1))
        features.append(max(prev_f2) - min(prev_f2))

        # Дополнительные статистики для больших полей
        if self.field1_size >= 5:
          features.append(np.median(prev_f1))  # Медиана
          features.append(len(set(prev_f1) & set(range(1, self.field1_max // 2 + 1))))  # Низкие числа
        if self.field2_size >= 3:
          features.append(np.median(prev_f2))
          features.append(len(set(prev_f2) & set(range(1, self.field2_max // 2 + 1))))

      # Дополняем до фиксированного размера если статистик меньше
      while len(features) % 4 != 0:  # Выравниваем под кратность 4
        features.append(0)

      # 5. День недели (если есть дата)
      if 'Дата' in df_copy.columns and pd.notnull(df_copy.iloc[i]['Дата']):
        try:
          day_of_week = df_copy.iloc[i]['Дата'].weekday()
          # One-hot encoding дня недели (7 признаков)
          for d in range(7):
            features.append(1 if d == day_of_week else 0)
        except:
          features.extend([0] * 7)
      else:
        features.extend([0] * 7)

      # 6. Дополнительные признаки для специфических лотерей
      if self.field1_max > 20:  # Для больших лотерей (например, 5x36)
        # Анализ распределения по декадам
        prev_f1 = df_copy.iloc[i - 1]['Числа_Поле1_list']
        decades_f1 = [0] * (self.field1_max // 10 + 1)
        for num in prev_f1:
          decades_f1[num // 10] += 1
        features.extend(decades_f1)

        # Паттерны последовательности
        consecutive_count = self._count_consecutive(prev_f1)
        features.append(consecutive_count)

      # Целевые переменные - текущий тираж
      curr_f1 = df_copy.iloc[i]['Числа_Поле1_list']
      curr_f2 = df_copy.iloc[i]['Числа_Поле2_list']

      if (isinstance(curr_f1, list) and len(curr_f1) == self.field1_size and
          isinstance(curr_f2, list) and len(curr_f2) == self.field2_size):
        X_list.append(features)

        for pos in range(self.field1_size):
          Y_f1_list[pos].append(curr_f1[pos])
        for pos in range(self.field2_size):
          Y_f2_list[pos].append(curr_f2[pos])

    if not X_list:
      print("AI Model (RF): Не удалось сформировать ни одного набора признаков (X_list).")
      return None, None, None

    X = np.array(X_list)
    Y_f1 = [np.array(y_pos) for y_pos in Y_f1_list]
    Y_f2 = [np.array(y_pos) for y_pos in Y_f2_list]

    print(f"AI Model (RF): Подготовлено {X.shape[0]} образцов с {X.shape[1]} признаками")
    print(f"AI Model (RF): Поле1: {self.field1_size} позиций x {self.field1_max} чисел")
    print(f"AI Model (RF): Поле2: {self.field2_size} позиций x {self.field2_max} чисел")

    return X, Y_f1, Y_f2

  def _count_consecutive(self, numbers):
    """Подсчитывает количество последовательных чисел"""
    if len(numbers) < 2:
      return 0
    sorted_nums = sorted(numbers)
    consecutive = 0
    current_streak = 1
    for i in range(1, len(sorted_nums)):
      if sorted_nums[i] == sorted_nums[i - 1] + 1:
        current_streak += 1
      else:
        consecutive = max(consecutive, current_streak)
        current_streak = 1
    return max(consecutive, current_streak)

  def train(self, df_history):
    """
    Универсальное обучение Random Forest моделей на исторических данных.
    Автоматически адаптируется под любую конфигурацию лотереи.
    """


    X, Y_f1, Y_f2 = self._prepare_rf_data(df_history)

    min_samples_for_training = max(10, self.field1_size + self.field2_size)
    if X is None or Y_f1 is None or Y_f2 is None or len(X) < min_samples_for_training:
      print(
        f"AI Model (RF): Недостаточно данных для обучения. Требуется {min_samples_for_training} образцов, доступно {len(X) if X is not None else 0}. Обучение отменено.")
      self.is_trained = False
      return

    print(f"AI Model (RF): Начало обучения случайного леса на {X.shape[0]} образцах...")
    trained_at_least_one_model = False

    # Обучение моделей для поля 1
    for i in range(self.field1_size):
      if len(Y_f1[i]) == X.shape[0] and len(np.unique(Y_f1[i])) > 1:
        try:
          self.models_f1[i].fit(X, Y_f1[i])
          self._classes_f1[i] = self.models_f1[i].classes_
          trained_at_least_one_model = True
        except Exception as e:
          print(f"AI Model (RF): Ошибка обучения Поле1 Позиция {i + 1}: {e}")
          self._classes_f1[i] = np.array([])
      else:
        self._classes_f1[i] = np.array([])
        print(f"AI Model (RF) Предупреждение: Поле 1, Позиция {i + 1} - недостаточно образцов или только один класс.")

    # Обучение моделей для поля 2
    for i in range(self.field2_size):
      if len(Y_f2[i]) == X.shape[0] and len(np.unique(Y_f2[i])) > 1:
        try:
          self.models_f2[i].fit(X, Y_f2[i])
          self._classes_f2[i] = self.models_f2[i].classes_
          trained_at_least_one_model = True
        except Exception as e:
          print(f"AI Model (RF): Ошибка обучения Поле2 Позиция {i + 1}: {e}")
          self._classes_f2[i] = np.array([])
      else:
        self._classes_f2[i] = np.array([])
        print(f"AI Model (RF) Предупреждение: Поле 2, Позиция {i + 1} - недостаточно образцов или только один класс.")

    if trained_at_least_one_model:
      self.is_trained = True
      print(f"AI Model (RF): Обучение случайного леса завершено для {self.field1_size}+{self.field2_size} позиций.")
    else:
      self.is_trained = False
      print("AI Model (RF): Обучение случайного леса не удалось ни для одной из позиций из-за проблем с данными.")

  def predict_next_combination(self, last_draw_numbers_f1, last_draw_numbers_f2, df_history=None):
    """
    Универсальное предсказание следующей комбинации.
    Автоматически адаптируется под любую конфигурацию лотереи.
    """


    if not self.is_trained:
      print("AI Model (RF): Модель не обучена. Предсказание невозможно.")
      return None, None

    if not (isinstance(last_draw_numbers_f1, list) and len(last_draw_numbers_f1) == self.field1_size and
            isinstance(last_draw_numbers_f2, list) and len(last_draw_numbers_f2) == self.field2_size):
      print(f"AI Model (RF): Неверный ввод для предсказания. Ожидается {self.field1_size} и {self.field2_size} чисел.")
      return None, None

    # Проверяем диапазоны чисел
    if not all(1 <= n <= self.field1_max for n in last_draw_numbers_f1):
      print(f"AI Model (RF): Числа поля 1 вне диапазона 1-{self.field1_max}")
      return None, None
    if not all(1 <= n <= self.field2_max for n in last_draw_numbers_f2):
      print(f"AI Model (RF): Числа поля 2 вне диапазона 1-{self.field2_max}")
      return None, None

    # Проверяем, сколько признаков ожидает модель (совместимость с разными версиями scikit-learn)
    expected_features = None
    try:
      # Для scikit-learn >= 0.24
      if hasattr(self.models_f1[0], 'n_features_in_') and getattr(self.models_f1[0], 'n_features_in_',
                                                                  None) is not None:
        expected_features = self.models_f1[0].n_features_in_
      # Для старых версий scikit-learn
      elif hasattr(self.models_f1[0], 'n_features_') and getattr(self.models_f1[0], 'n_features_', None) is not None:
        expected_features = self.models_f1[0].n_features_
      # Через первое дерево в лесу
      elif hasattr(self.models_f1[0], 'estimators_') and len(self.models_f1[0].estimators_) > 0:
        first_tree = self.models_f1[0].estimators_[0]
        if hasattr(first_tree, 'n_features_') and getattr(first_tree, 'n_features_', None) is not None:
          expected_features = first_tree.n_features_
    except (AttributeError, TypeError, IndexError):
      expected_features = None

    # Для новой версии нужна история
    if df_history is None or len(df_history) < 5:
      print("AI Model (RF): Недостаточно истории для расширенных признаков. Используем упрощенный режим.")
      # Упрощенный режим - только последний тираж
      features = np.array(sorted(last_draw_numbers_f1) + sorted(last_draw_numbers_f2))

      # Если не удалось определить ожидаемое количество признаков автоматически
      if expected_features is None:
        # Используем базовую оценку
        base_features = (self.field1_size + self.field2_size) * 10  # примерная оценка
        expected_features = base_features
        print(f"AI Model (RF): Используем адаптивное количество признаков: {expected_features}")

      # Дополняем до нужного размера
      if len(features) < expected_features:
        extended_features = np.zeros(expected_features)
        extended_features[:len(features)] = features
        features = extended_features
      else:
        features = features[:expected_features]

      features = features.reshape(1, -1)
    else:
      # Полный набор признаков
      features = self._prepare_features_for_prediction(last_draw_numbers_f1, last_draw_numbers_f2, df_history)
      if features is None:
        print("AI Model (RF): Не удалось подготовить признаки")
        return None, None

      # Корректируем количество признаков если нужно
      if expected_features and features.shape[1] != expected_features:
        current = features.shape[1]
        if current < expected_features:
          padding = expected_features - current
          features = np.pad(features, ((0, 0), (0, padding)), 'constant', constant_values=0)
          print(f"AI Model (RF): Дополнено {padding} признаков нулями ({current} -> {expected_features})")
        else:
          features = features[:, :expected_features]
          print(f"AI Model (RF): Обрезано до {expected_features} признаков (было {current})")

    # Генерация предсказаний для поля 1
    predicted_f1 = []
    available_numbers_f1 = list(range(1, self.field1_max + 1))

    for i in range(self.field1_size):
      if hasattr(self.models_f1[i], 'classes_') and self.models_f1[i].classes_.size > 0:
        try:
          probabilities = self.models_f1[i].predict_proba(features)[0]
          sorted_class_indices = np.argsort(probabilities)[::-1]
          predicted_num_for_pos = None

          for class_idx in sorted_class_indices:
            num = int(self.models_f1[i].classes_[class_idx])
            if num in available_numbers_f1:
              predicted_num_for_pos = num
              break

          if predicted_num_for_pos is not None:
            predicted_f1.append(predicted_num_for_pos)
            available_numbers_f1.remove(predicted_num_for_pos)
          else:
            if available_numbers_f1:
              fallback_num = random.choice(available_numbers_f1)
              predicted_f1.append(fallback_num)
              available_numbers_f1.remove(fallback_num)
        except Exception as e:
          print(f"AI Model (RF): Ошибка предсказания для позиции {i}: {e}")
          if available_numbers_f1:
            fallback_num = random.choice(available_numbers_f1)
            predicted_f1.append(fallback_num)
            available_numbers_f1.remove(fallback_num)
      else:
        if available_numbers_f1:
          fallback_num = random.choice(available_numbers_f1)
          predicted_f1.append(fallback_num)
          available_numbers_f1.remove(fallback_num)

    # Дополняем если не хватает
    while len(predicted_f1) < self.field1_size and available_numbers_f1:
      predicted_f1.append(available_numbers_f1.pop(random.randrange(len(available_numbers_f1))))

    # Генерация предсказаний для поля 2
    predicted_f2 = []
    available_numbers_f2 = list(range(1, self.field2_max + 1))

    for i in range(self.field2_size):
      if hasattr(self.models_f2[i], 'classes_') and self.models_f2[i].classes_.size > 0:
        try:
          probabilities = self.models_f2[i].predict_proba(features)[0]
          sorted_class_indices = np.argsort(probabilities)[::-1]
          predicted_num_for_pos = None

          for class_idx in sorted_class_indices:
            num = int(self.models_f2[i].classes_[class_idx])
            if num in available_numbers_f2:
              predicted_num_for_pos = num
              break

          if predicted_num_for_pos is not None:
            predicted_f2.append(predicted_num_for_pos)
            available_numbers_f2.remove(predicted_num_for_pos)
          else:
            if available_numbers_f2:
              fallback_num = random.choice(available_numbers_f2)
              predicted_f2.append(fallback_num)
              available_numbers_f2.remove(fallback_num)
        except Exception as e:
          print(f"AI Model (RF): Ошибка предсказания для позиции {i} поля 2: {e}")
          if available_numbers_f2:
            fallback_num = random.choice(available_numbers_f2)
            predicted_f2.append(fallback_num)
            available_numbers_f2.remove(fallback_num)
      else:
        if available_numbers_f2:
          fallback_num = random.choice(available_numbers_f2)
          predicted_f2.append(fallback_num)
          available_numbers_f2.remove(fallback_num)

    # Дополняем если не хватает
    while len(predicted_f2) < self.field2_size and available_numbers_f2:
      predicted_f2.append(available_numbers_f2.pop(random.randrange(len(available_numbers_f2))))

    # Финальная проверка перед возвратом
    if len(predicted_f1) != self.field1_size or len(predicted_f2) != self.field2_size:
      print(
        f"AI Model (RF): Ошибка генерации - неверное количество чисел: f1={len(predicted_f1)}, f2={len(predicted_f2)}")
      return None, None

    return sorted(predicted_f1), sorted(predicted_f2)

  def _prepare_features_for_prediction(self, last_f1, last_f2, df_history):
    """
    Универсальная подготовка расширенных признаков для предсказания.
    Автоматически адаптируется под любую конфигурацию лотереи.
    """


    # Проверка входных данных
    if not isinstance(last_f1, list) or len(last_f1) != self.field1_size:
      print(f"AI Model (RF): Некорректные данные last_f1: {last_f1}")
      return None

    if not isinstance(last_f2, list) or len(last_f2) != self.field2_size:
      print(f"AI Model (RF): Некорректные данные last_f2: {last_f2}")
      return None

    if df_history is None or df_history.empty:
      print("AI Model (RF): df_history пуст или None")
      return None

    from datetime import datetime
    from collections import Counter
    import numpy as np

    features = []
    lookback_draws = min(5, len(df_history))

    # Создаем правильную историю для признаков
    if len(df_history) < lookback_draws:
      print(f"AI Model (RF): Недостаточно истории ({len(df_history)} < {lookback_draws})")
      return None

    # 1. Числа из последних N тиражей (отсортированные)
    for j in range(0, lookback_draws):
      if j == 0:
        # Текущий тираж (последний известный)
        features.extend(sorted(last_f1) + sorted(last_f2))
      else:
        # Предыдущие тиражи из истории
        prev_row = df_history.iloc[j - 1]
        prev_f1 = prev_row['Числа_Поле1_list']
        prev_f2 = prev_row['Числа_Поле2_list']
        if (isinstance(prev_f1, list) and len(prev_f1) == self.field1_size and
            isinstance(prev_f2, list) and len(prev_f2) == self.field2_size):
          features.extend(sorted(prev_f1) + sorted(prev_f2))
        else:
          # Если данные некорректны, используем нули
          features.extend([0] * (self.field1_size + self.field2_size))

    # 2. Частоты каждого числа за последние 20 тиражей
    freq_window = min(20, len(df_history) + 1)
    recent_draws_f1 = []
    recent_draws_f2 = []

    # Включаем текущий тираж
    recent_draws_f1.extend(last_f1)
    recent_draws_f2.extend(last_f2)

    # Добавляем из истории
    for k in range(min(freq_window - 1, len(df_history))):
      row = df_history.iloc[k]
      if isinstance(row['Числа_Поле1_list'], list):
        recent_draws_f1.extend(row['Числа_Поле1_list'])
      if isinstance(row['Числа_Поле2_list'], list):
        recent_draws_f2.extend(row['Числа_Поле2_list'])

    freq_counter_f1 = Counter(recent_draws_f1)
    freq_counter_f2 = Counter(recent_draws_f2)

    # Частоты для каждого числа в диапазонах полей
    for num in range(1, self.field1_max + 1):
      features.append(freq_counter_f1.get(num, 0))
    for num in range(1, self.field2_max + 1):
      features.append(freq_counter_f2.get(num, 0))

    # 3. Количество тиражей с последнего выпадения каждого числа
    last_appearance_f1 = {}
    last_appearance_f2 = {}
    for num in range(1, self.field1_max + 1):
      last_appearance_f1[num] = -1
    for num in range(1, self.field2_max + 1):
      last_appearance_f2[num] = -1

    # Текущий тираж - расстояние 0
    for num in last_f1:
      last_appearance_f1[num] = 0
    for num in last_f2:
      last_appearance_f2[num] = 0

    # Ищем последнее появление в истории
    for k in range(len(df_history)):
      row = df_history.iloc[k]
      if isinstance(row['Числа_Поле1_list'], list):
        for num in row['Числа_Поле1_list']:
          if num in last_appearance_f1 and last_appearance_f1[num] == -1:
            last_appearance_f1[num] = k + 1
      if isinstance(row['Числа_Поле2_list'], list):
        for num in row['Числа_Поле2_list']:
          if num in last_appearance_f2 and last_appearance_f2[num] == -1:
            last_appearance_f2[num] = k + 1

    # Добавляем расстояния до последнего появления
    for num in range(1, self.field1_max + 1):
      features.append(last_appearance_f1[num] if last_appearance_f1[num] != -1 else freq_window)
    for num in range(1, self.field2_max + 1):
      features.append(last_appearance_f2[num] if last_appearance_f2[num] != -1 else freq_window)

    # 4. Статистики последних тиражей (адаптивно)
    stats_window = min(3, len(df_history) + 1)
    for j in range(1, stats_window + 1):
      if j == 1:
        # Текущий тираж
        prev_f1 = last_f1
        prev_f2 = last_f2
      elif j - 1 < len(df_history):
        # Из истории
        row = df_history.iloc[j - 2]
        prev_f1 = row['Числа_Поле1_list']
        prev_f2 = row['Числа_Поле2_list']
      else:
        # Если не хватает истории, заполняем нулями
        features.extend([0] * 6)
        continue

      if (isinstance(prev_f1, list) and len(prev_f1) == self.field1_size and
          isinstance(prev_f2, list) and len(prev_f2) == self.field2_size):
        # Сумма чисел
        features.append(sum(prev_f1))
        features.append(sum(prev_f2))

        # Количество четных чисел
        features.append(sum(1 for n in prev_f1 if n % 2 == 0))
        features.append(sum(1 for n in prev_f2 if n % 2 == 0))

        # Размах (макс - мин)
        features.append(max(prev_f1) - min(prev_f1))
        features.append(max(prev_f2) - min(prev_f2))

        # Дополнительные статистики для больших полей
        if self.field1_size >= 5:
          features.append(np.median(prev_f1))
          features.append(len(set(prev_f1) & set(range(1, self.field1_max // 2 + 1))))
        if self.field2_size >= 3:
          features.append(np.median(prev_f2))
          features.append(len(set(prev_f2) & set(range(1, self.field2_max // 2 + 1))))
      else:
        base_features = 6
        if self.field1_size >= 5:
          base_features += 2
        if self.field2_size >= 3:
          base_features += 2
        features.extend([0] * base_features)

    # 5. День недели (7 признаков)
    try:
      day_of_week = datetime.now().weekday()
      for d in range(7):
        features.append(1 if d == day_of_week else 0)
    except:
      features.extend([0] * 7)

    # 6. Дополнительные признаки для больших лотерей
    if self.field1_max > 20:
      # Анализ распределения по декадам
      decades_f1 = [0] * (self.field1_max // 10 + 1)
      for num in last_f1:
        decades_f1[num // 10] += 1
      features.extend(decades_f1)

      # Паттерны последовательности
      consecutive_count = self._count_consecutive(last_f1)
      features.append(consecutive_count)

    return np.array(features).reshape(1, -1)

  def score_combination(self, combination_f1, combination_f2, df_history):
    """
    Универсальная оценка предложенной комбинации на основе обученных моделей RF.
    Автоматически адаптируется под любую конфигурацию лотереи.
    """


    if not self.is_trained:
      return -float('inf')

    if df_history is None or df_history.empty:
      return -float('inf')

    # Проверяем размеры комбинаций
    if (not isinstance(combination_f1, list) or len(combination_f1) != self.field1_size or
        not isinstance(combination_f2, list) or len(combination_f2) != self.field2_size):
      return -float('inf')

    # Проверяем диапазоны чисел
    if not all(1 <= n <= self.field1_max for n in combination_f1):
      return -float('inf')
    if not all(1 <= n <= self.field2_max for n in combination_f2):
      return -float('inf')

    # Получаем последний тираж для базовых признаков
    last_draw = df_history.iloc[0]
    last_f1 = last_draw.get('Числа_Поле1_list')
    last_f2 = last_draw.get('Числа_Поле2_list')

    if not (isinstance(last_f1, list) and len(last_f1) == self.field1_size and
            isinstance(last_f2, list) and len(last_f2) == self.field2_size):
      return -float('inf')

    # Готовим полный набор признаков
    features = self._prepare_features_for_prediction(last_f1, last_f2, df_history)
    if features is None:
      return -float('inf')

    total_log_proba = 0.0
    epsilon = 1e-9

    # Оценка Поля 1
    for i in range(self.field1_size):
      num_to_score = combination_f1[i]
      model_pos = self.models_f1[i]
      classes_pos = self._classes_f1[i]

      if hasattr(model_pos, 'predict_proba') and classes_pos.size > 0:
        try:
          class_idx_arr = np.where(classes_pos == num_to_score)[0]
          if class_idx_arr.size > 0:
            idx = class_idx_arr[0]
            proba_dist = model_pos.predict_proba(features)[0]
            if idx < len(proba_dist):
              proba = proba_dist[idx]
              total_log_proba += np.log(proba + epsilon)
            else:
              total_log_proba += np.log(epsilon)
          else:
            total_log_proba += np.log(epsilon)
        except Exception as e:
          total_log_proba += np.log(epsilon)
      else:
        return -float('inf')

    # Оценка Поля 2
    for i in range(self.field2_size):
      num_to_score = combination_f2[i]
      model_pos = self.models_f2[i]
      classes_pos = self._classes_f2[i]

      if hasattr(model_pos, 'predict_proba') and classes_pos.size > 0:
        try:
          class_idx_arr = np.where(classes_pos == num_to_score)[0]
          if class_idx_arr.size > 0:
            idx = class_idx_arr[0]
            proba_dist = model_pos.predict_proba(features)[0]
            if idx < len(proba_dist):
              proba = proba_dist[idx]
              total_log_proba += np.log(proba + epsilon)
            else:
              total_log_proba += np.log(epsilon)
          else:
            total_log_proba += np.log(epsilon)
        except Exception as e:
          total_log_proba += np.log(epsilon)
      else:
        return -float('inf')

    return total_log_proba


# --- УНИВЕРСАЛЬНАЯ СТРУКТУРА ДЛЯ LSTM МОДЕЛИ ---

class PyTorchLSTMNetwork(nn.Module):
  def __init__(self, input_size, hidden_size, num_layers, output_size, dropout_prob=0.2):
    super(PyTorchLSTMNetwork, self).__init__()
    self.hidden_size = hidden_size
    self.num_layers = num_layers

    self.lstm = nn.LSTM(input_size, hidden_size, num_layers,
                        batch_first=True, dropout=dropout_prob if num_layers > 1 else 0)
    self.fc = nn.Linear(hidden_size, output_size)
    self.dropout = nn.Dropout(dropout_prob)

  def forward(self, x, device):
    h0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size).to(device)
    c0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size).to(device)

    out, _ = self.lstm(x, (h0, c0))
    out = out[:, -1, :]  # Используем выход только последнего временного шага
    out = self.dropout(out)
    out = self.fc(out)
    return torch.sigmoid(out)  # Sigmoid для multi-label вероятностей


class LotteryLSTMOps:
  """
  Универсальный LSTM оркестратор для любых лотерей.
  Автоматически адаптируется под конфигурацию лотереи.
  """

  def __init__(self, lottery_config: dict, n_steps_in=5, hidden_size_lstm=64, num_lstm_layers=1, dropout_lstm=0.1):
    """
    Инициализация LSTM для конкретной конфигурации лотереи.

    Args:
        lottery_config: Словарь с конфигурацией лотереи (неизменяемый)
    """

    self.config = lottery_config.copy()  # Копия для защиты от мутаций
    self.lottery_type = self.config.get('db_table', '').replace('draws_', '')
    self.n_steps_in = n_steps_in
    self.field1_size = self.config['field1_size']
    self.field2_size = self.config['field2_size']
    self.field1_max = self.config['field1_max']
    self.field2_max = self.config['field2_max']

    # Общее количество признаков на временной шаг
    self.n_features_per_step = self.field1_max + self.field2_max

    # Создаем MultiLabelBinarizer для каждого поля отдельно
    self.mlb_f1 = MultiLabelBinarizer(classes=list(range(1, self.field1_max + 1)))
    self.mlb_f1.fit([list(range(1, self.field1_max + 1))])

    self.mlb_f2 = MultiLabelBinarizer(classes=list(range(1, self.field2_max + 1)))
    self.mlb_f2.fit([list(range(1, self.field2_max + 1))])

    self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"LSTM Ops: Используется устройство: {self.device}")

    self.model = PyTorchLSTMNetwork(
      input_size=self.n_features_per_step,
      hidden_size=hidden_size_lstm,
      num_layers=num_lstm_layers,
      output_size=self.n_features_per_step,
      dropout_prob=dropout_lstm
    )
    self.model.to(self.device)
    self.is_trained = False

    print(
      f"LotteryLSTMOps: Инициализирован для {self.field1_size}x{self.field1_max} + {self.field2_size}x{self.field2_max}")

  def _prepare_sequences(self, df_history):
    """
    Универсальная подготовка последовательностей для LSTM.
    Автоматически адаптируется под любую конфигурацию лотереи.
    """


    if len(df_history) < self.n_steps_in + 1:
      print(
        f"LSTM: Недостаточно данных ({len(df_history)} строк) для создания последовательностей длины {self.n_steps_in + 1}.")
      return None, None

    all_draw_features_np = []
    processed_indices = []

    for index, row in df_history.iterrows():
      f1_list = row.get('Числа_Поле1_list', [])
      f2_list = row.get('Числа_Поле2_list', [])

      # Универсальная валидация
      if (isinstance(f1_list, list) and isinstance(f2_list, list) and
          len(f1_list) == self.field1_size and len(f2_list) == self.field2_size and
          all(1 <= num <= self.field1_max for num in f1_list) and
          all(1 <= num <= self.field2_max for num in f2_list)):

        try:
          f1_mh = self.mlb_f1.transform([f1_list])[0]
          f2_mh = self.mlb_f2.transform([f2_list])[0]
          all_draw_features_np.append(np.concatenate((f1_mh, f2_mh)))
          processed_indices.append(index)
        except Exception as e:
          print(f"LSTM: Ошибка при MLB transform для тиража (индекс {index}): {e}")

    if len(all_draw_features_np) < self.n_steps_in + 1:
      print(f"LSTM: Недостаточно корректных тиражей ({len(all_draw_features_np)}) для создания последовательностей.")
      return None, None

    all_draw_features_np = np.array(all_draw_features_np)

    X_list, Y_list = [], []
    for i in range(len(all_draw_features_np) - self.n_steps_in):
      X_list.append(all_draw_features_np[i: i + self.n_steps_in])
      Y_list.append(all_draw_features_np[i + self.n_steps_in])

    if not X_list:
      print("LSTM: Не удалось создать ни одной последовательности X.")
      return None, None

    X_np = np.array(X_list, dtype=np.float32)
    Y_np = np.array(Y_list, dtype=np.float32)

    print(f"LSTM: Подготовлено X_shape: {X_np.shape}, Y_shape: {Y_np.shape}")
    print(f"LSTM: Конфигурация {self.field1_size}x{self.field1_max} + {self.field2_size}x{self.field2_max}")

    return torch.from_numpy(X_np).to(self.device), torch.from_numpy(Y_np).to(self.device)

  def train(self, df_history, epochs=10, batch_size=8, learning_rate=0.001):
    """
    Универсальное обучение LSTM модели.
    Автоматически адаптируется под любую конфигурацию лотереи.
    """


    X_tensor, Y_tensor = self._prepare_sequences(df_history)

    if X_tensor is None or Y_tensor is None or X_tensor.nelement() == 0 or Y_tensor.nelement() == 0:
      print("LSTM: Обучение невозможно, нет валидных данных для последовательностей.")
      self.is_trained = False
      return

    dataset = TensorDataset(X_tensor, Y_tensor)
    actual_batch_size = min(batch_size, len(dataset))
    if actual_batch_size == 0:
      print("LSTM: Размер датасета 0, обучение невозможно.")
      self.is_trained = False
      return

    dataloader = DataLoader(dataset, batch_size=actual_batch_size, shuffle=True)

    criterion = nn.BCELoss()
    optimizer = optim.Adam(self.model.parameters(), lr=learning_rate)

    print(f"LSTM: Начало обучения модели на {X_tensor.shape[0]} образцах...")
    self.model.train()

    for epoch in range(epochs):
      epoch_loss = 0
      num_batches = 0
      for inputs_batch, targets_batch in dataloader:
        optimizer.zero_grad()
        outputs = self.model(inputs_batch, self.device)
        loss = criterion(outputs, targets_batch)
        loss.backward()
        optimizer.step()
        epoch_loss += loss.item()
        num_batches += 1

      if num_batches > 0:
        avg_epoch_loss = epoch_loss / num_batches
        print(f"LSTM Эпоха [{epoch + 1}/{epochs}], Потери: {avg_epoch_loss:.4f}")
      else:
        print(f"LSTM Эпоха [{epoch + 1}/{epochs}], нет батчей для обработки.")
        break

    self.is_trained = True
    print("LSTM: Обучение завершено.")

  def predict_next_combination(self, df_last_n_draws):
    """
    Универсальное предсказание следующей комбинации на основе последних n_steps_in тиражей.
    Автоматически адаптируется под любую конфигурацию лотереи.

    Args:
        df_last_n_draws: DataFrame с последними n_steps_in тиражами в хронологическом порядке
    """
    if not self.is_trained:
      print("LSTM: Модель не обучена. Возвращаем случайную комбинацию.")
      return (random.sample(range(1, self.field1_max + 1), self.field1_size),
              random.sample(range(1, self.field2_max + 1), self.field2_size))

    if len(df_last_n_draws) != self.n_steps_in:
      print(f"LSTM: Для предсказания требуется {self.n_steps_in} тиражей, получено {len(df_last_n_draws)}.")

      # Если данных больше, берем последние n_steps_in
      if len(df_last_n_draws) > self.n_steps_in:
        df_last_n_draws = df_last_n_draws.tail(self.n_steps_in)
        print(f"LSTM: Используем последние {self.n_steps_in} тиражей")
      else:
        print("LSTM: Возвращаем случайную комбинацию из-за недостатка данных.")
        return (random.sample(range(1, self.field1_max + 1), self.field1_size),
                random.sample(range(1, self.field2_max + 1), self.field2_size))

    input_features_list = []
    valid_sequence = True

    print(f"LSTM Predict: Обработка {len(df_last_n_draws)} тиражей для прогноза")

    for idx, (_, row) in enumerate(df_last_n_draws.iterrows()):
      f1_list = row.get('Числа_Поле1_list', [])
      f2_list = row.get('Числа_Поле2_list', [])

      # Дополнительная диагностика
      print(f"LSTM Predict: Тираж {idx + 1}: Поле1={f1_list}, Поле2={f2_list}")

      if (isinstance(f1_list, list) and isinstance(f2_list, list) and
          len(f1_list) == self.field1_size and len(f2_list) == self.field2_size and
          all(1 <= num <= self.field1_max for num in f1_list) and
          all(1 <= num <= self.field2_max for num in f2_list)):
        try:
          f1_mh = self.mlb_f1.transform([f1_list])[0]
          f2_mh = self.mlb_f2.transform([f2_list])[0]
          combined_features = np.concatenate((f1_mh, f2_mh))
          input_features_list.append(combined_features)
          print(f"LSTM Predict: Тираж {idx + 1} успешно обработан, размер признаков: {len(combined_features)}")
        except Exception as e:
          print(f"LSTM Predict: Ошибка MLB transform для тиража {idx + 1}: {e}")
          valid_sequence = False
          break
      else:
        print(f"LSTM Predict: Некорректные данные в тираже {idx + 1}")
        print(
          f"  f1_list: {f1_list} (type: {type(f1_list)}, len: {len(f1_list) if isinstance(f1_list, list) else 'N/A'})")
        print(
          f"  f2_list: {f2_list} (type: {type(f2_list)}, len: {len(f2_list) if isinstance(f2_list, list) else 'N/A'})")
        print(
          f"  Ожидается: Поле1={self.field1_size} чисел 1-{self.field1_max}, Поле2={self.field2_size} чисел 1-{self.field2_max}")
        valid_sequence = False
        break

    if not valid_sequence or len(input_features_list) != self.n_steps_in:
      print("LSTM: Не удалось сформировать корректную входную последовательность. Возвращаем случайную.")
      return (random.sample(range(1, self.field1_max + 1), self.field1_size),
              random.sample(range(1, self.field2_max + 1), self.field2_size))

    # Подготавливаем тензор для модели
    input_np = np.array([input_features_list], dtype=np.float32)
    input_tensor = torch.from_numpy(input_np).to(self.device)

    print(f"LSTM Predict: Входной тензор готов, размер: {input_tensor.shape}")

    # Генерируем предсказание
    self.model.eval()
    with torch.no_grad():
      predicted_probs_both = self.model(input_tensor, self.device)[0].cpu().numpy()

    print(f"LSTM Predict: Предсказание получено, размер выхода: {len(predicted_probs_both)}")

    # Разделяем предсказания на поля
    proba_f1 = predicted_probs_both[:self.field1_max]
    proba_f2 = predicted_probs_both[self.field1_max:self.field1_max + self.field2_max]

    print(f"LSTM Predict: Поле1 вероятности: min={proba_f1.min():.3f}, max={proba_f1.max():.3f}")
    print(f"LSTM Predict: Поле2 вероятности: min={proba_f2.min():.3f}, max={proba_f2.max():.3f}")

    # Выбор топ-N УНИКАЛЬНЫХ номеров для каждого поля
    def select_top_unique(probabilities, k, max_val, field_name):
      sorted_indices = np.argsort(probabilities)[::-1]
      selected_numbers = []

      print(f"LSTM Predict: Топ-10 вероятностей для {field_name}:")
      for i in range(min(10, len(sorted_indices))):
        idx = sorted_indices[i]
        number = idx + 1
        prob = probabilities[idx]
        print(f"  #{number}: {prob:.4f}")

      for idx in sorted_indices:
        number = idx + 1
        if number not in selected_numbers and 1 <= number <= max_val:
          selected_numbers.append(number)
        if len(selected_numbers) == k:
          break

      # Дополняем случайными если не хватает
      if len(selected_numbers) < k:
        available_to_add = [n for n in range(1, max_val + 1) if n not in selected_numbers]
        needed = k - len(selected_numbers)
        if len(available_to_add) >= needed:
          selected_numbers.extend(random.sample(available_to_add, needed))
        else:
          selected_numbers.extend(available_to_add)
          print(f"LSTM Predict: Предупреждение - не хватает чисел для {field_name}")

      return sorted(selected_numbers[:k])

    pred_f1 = select_top_unique(proba_f1, self.field1_size, self.field1_max, "Поле1")
    pred_f2 = select_top_unique(proba_f2, self.field2_size, self.field2_max, "Поле2")

    # Финальная проверка размеров
    if len(pred_f1) != self.field1_size:
      print(f"LSTM Predict: Ошибка размера Поле1: получено {len(pred_f1)}, ожидалось {self.field1_size}")
      pred_f1 = random.sample(range(1, self.field1_max + 1), self.field1_size)

    if len(pred_f2) != self.field2_size:
      print(f"LSTM Predict: Ошибка размера Поле2: получено {len(pred_f2)}, ожидалось {self.field2_size}")
      pred_f2 = random.sample(range(1, self.field2_max + 1), self.field2_size)

    print(f"LSTM Predict: Финальный прогноз - Поле1: {pred_f1}, Поле2: {pred_f2}")

    return sorted(pred_f1), sorted(pred_f2)



class ModelManager:
  """
  Менеджер моделей для безопасной работы с несколькими лотереями.
  Поддерживает отдельные экземпляры моделей для каждой лотереи.
  Thread-safe операции.
  """

  def __init__(self):
    self._rf_models: Dict[str, RFModel] = {}
    self._lstm_models: Dict[str, LotteryLSTMOps] = {}
    self._lock = threading.RLock()  # Защита от конкурентного доступа

  def get_rf_model(self, lottery_type: str, lottery_config: dict) -> RFModel:
    """
    Получает RF модель для указанной лотереи.
    Создает новую, если не существует.

    Args:
        lottery_type: Тип лотереи ('4x20', '5x36plus')
        lottery_config: Конфигурация лотереи

    Returns:
        RFModel: Экземпляр модели для данной лотереи
    """
    with self._lock:
      if lottery_type not in self._rf_models:
        print(f"Model Manager: Создание RF модели для {lottery_type}")
        self._rf_models[lottery_type] = RFModel(lottery_config)
      return self._rf_models[lottery_type]

  def get_lstm_model(self, lottery_type: str, lottery_config: dict) -> LotteryLSTMOps:
    """
    Получает LSTM модель для указанной лотереи.
    Создает новую, если не существует.
    """
    with self._lock:
      if lottery_type not in self._lstm_models:
        print(f"Model Manager: Создание LSTM модели для {lottery_type}")
        self._lstm_models[lottery_type] = LotteryLSTMOps(lottery_config)
      return self._lstm_models[lottery_type]

  def train_all_models(self, lottery_configs: dict, data_fetcher_func):
    """
    Обучает все модели для всех лотерей при старте сервера.

    Args:
        lottery_configs: Словарь всех конфигураций лотерей
        data_fetcher_func: Функция для получения данных
    """
    for lottery_type, config in lottery_configs.items():
      try:
        print(f"Model Manager: Обучение моделей для {lottery_type}")

        # Получаем данные для этой лотереи
        from backend.app.core.lottery_context import LotteryContext
        with LotteryContext(lottery_type):
          df = data_fetcher_func()

        if not df.empty:
          # Обучаем RF модель
          rf_model = self.get_rf_model(lottery_type, config)
          rf_model.train(df)

          # Обучаем LSTM модель
          lstm_model = self.get_lstm_model(lottery_type, config)
          lstm_model.train(df)

          print(f"Model Manager: Модели для {lottery_type} обучены успешно")
        else:
          print(f"Model Manager: Нет данных для обучения {lottery_type}")

      except Exception as e:
        print(f"Model Manager: Ошибка обучения моделей для {lottery_type}: {e}")

  def get_model_status(self) -> dict:
    """Возвращает статус всех моделей"""
    status = {}
    with self._lock:
      for lottery_type, rf_model in self._rf_models.items():
        lstm_model = self._lstm_models.get(lottery_type)
        status[lottery_type] = {
          'rf_trained': rf_model.is_trained,
          'lstm_trained': lstm_model.is_trained if lstm_model else False
        }
    return status


# Глобальный менеджер моделей (thread-safe)
GLOBAL_MODEL_MANAGER = ModelManager()


# Функции для обратной совместимости с существующим кодом
def get_current_rf_model():
  """Получает RF модель для текущей лотереи"""
  from backend.app.core.data_manager import get_current_config, CURRENT_LOTTERY
  config = get_current_config()
  return GLOBAL_MODEL_MANAGER.get_rf_model(CURRENT_LOTTERY, config)


def get_current_lstm_model():
  """Получает LSTM модель для текущей лотереи"""
  from backend.app.core.data_manager import get_current_config, CURRENT_LOTTERY
  config = get_current_config()
  return GLOBAL_MODEL_MANAGER.get_lstm_model(CURRENT_LOTTERY, config)


# Глобальные экземпляры для обратной совместимости
# ВАЖНО: Эти объекты теперь динамические и безопасные!
class GlobalModelProxy:
  """Прокси для обратной совместимости с кэшированием + RF кэш"""

  def __init__(self):
    self._cached_model = None
    self._cached_lottery = None

  @property
  def is_trained(self):
    model = self._get_cached_model()
    return model.is_trained if model else False

  def _get_cached_model(self):
    """Получает кэшированную модель для текущей лотереи"""
    from backend.app.core import data_manager

    # Если модель для другой лотереи или не создана - обновляем
    if self._cached_lottery != data_manager.CURRENT_LOTTERY or self._cached_model is None:
      print(f"🔄 Кэширование RF модели для {data_manager.CURRENT_LOTTERY}")
      config = data_manager.get_current_config()
      self._cached_model = GLOBAL_MODEL_MANAGER.get_rf_model(data_manager.CURRENT_LOTTERY, config)
      self._cached_lottery = data_manager.CURRENT_LOTTERY

    return self._cached_model

  def train(self, df_history):
    model = self._get_cached_model()
    if model:
      # Очищаем кэш после переобучения
      from backend.app.core.rf_cache import GLOBAL_RF_CACHE
      GLOBAL_RF_CACHE.clear_cache()
      print("🗑️ RF кэш очищен после переобучения")
      return model.train(df_history)
    return False

  def predict_next_combination(self, last_f1, last_f2, df_history=None):
    model = self._get_cached_model()
    if model:
      return model.predict_next_combination(last_f1, last_f2, df_history)
    return None, None

  def score_combination(self, f1, f2, df_history):
    """УЛЬТРА БЫСТРАЯ оценка с кэшированием"""
    from backend.app.core.rf_cache import GLOBAL_RF_CACHE

    # Сначала проверяем кэш
    cached_score = GLOBAL_RF_CACHE.get_score(f1, f2)
    if cached_score is not None:
      return cached_score

    # Если не в кэше - вычисляем
    model = self._get_cached_model()
    if model:
      # ИСПРАВЛЕНИЕ: Принудительно обучаем модель если она не обучена
      if not model.is_trained and not df_history.empty:
        print(f"🎓 Принудительное обучение RF модели...")
        model.train(df_history)

      score = model.score_combination(f1, f2, df_history)
      # Сохраняем в кэш
      GLOBAL_RF_CACHE.set_score(f1, f2, score)
      return score

    return -float('inf')


GLOBAL_RF_MODEL = GlobalModelProxy()
GLOBAL_LSTM_MODEL = get_current_lstm_model  # Функция, а не объект


class LotteryScheduleConfig:
  """Конфигурация расписания для конкретной лотереи"""

  def __init__(self, lottery_type: str, schedule_type: str, **kwargs):
    self.lottery_type = lottery_type
    self.schedule_type = schedule_type  # 'fixed_times' или 'interval'
    self.timezone = pytz.timezone('Europe/Moscow')  # МСК

    if schedule_type == 'fixed_times':
      self.draw_times = kwargs.get('draw_times', [])  # Список времен в формате "HH:MM"
      self.check_offset_minutes = kwargs.get('check_offset_minutes', 5)  # Проверять через 5 мин после тиража
    elif schedule_type == 'interval':
      self.interval_minutes = kwargs.get('interval_minutes', 15)
      self.check_delay_minutes = kwargs.get('check_delay_minutes', 2)  # Задержка после тиража
      self.excluded_times = kwargs.get('excluded_times', [])  # Исключения (например, "Остатки сладки")

  def get_next_check_time(self, current_time: datetime = None) -> datetime:
    """Вычисляет следующее время проверки новых тиражей"""
    if current_time is None:
      current_time = datetime.now(self.timezone)

    if self.schedule_type == 'fixed_times':
      return self._get_next_fixed_check(current_time)
    elif self.schedule_type == 'interval':
      return self._get_next_interval_check(current_time)

  def _get_next_fixed_check(self, current_time: datetime) -> datetime:
    """Для лотерей с фиксированным расписанием (4x20)"""
    today = current_time.date()

    for time_str in self.draw_times:
      hour, minute = map(int, time_str.split(':'))
      draw_time = self.timezone.localize(datetime.combine(today, datetime.min.time().replace(hour=hour, minute=minute)))
      check_time = draw_time + timedelta(minutes=self.check_offset_minutes)

      if check_time > current_time:
        return check_time

    # Если все времена сегодня прошли, берем первое время завтра
    tomorrow = today + timedelta(days=1)
    first_time = self.draw_times[0]
    hour, minute = map(int, first_time.split(':'))
    draw_time = self.timezone.localize(
      datetime.combine(tomorrow, datetime.min.time().replace(hour=hour, minute=minute)))
    return draw_time + timedelta(minutes=self.check_offset_minutes)

  def _get_next_interval_check(self, current_time: datetime) -> datetime:
    """Для лотерей с интервальным расписанием (5x36plus)"""
    # Округляем до ближайшего интервала
    minutes_since_hour = current_time.minute
    intervals_passed = minutes_since_hour // self.interval_minutes
    next_interval_minute = (intervals_passed + 1) * self.interval_minutes

    if next_interval_minute >= 60:
      next_check = current_time.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    else:
      next_check = current_time.replace(minute=next_interval_minute, second=0, microsecond=0)

    # Добавляем задержку после тиража
    next_check += timedelta(minutes=self.check_delay_minutes)

    # TODO: Добавить логику исключений для "Остатки сладки"
    return next_check


class AutoUpdateScheduler:
  """
  Автоматический планировщик обновлений с учетом расписания каждой лотереи.
  Поддерживает различные типы расписаний и автоматическое переобучение моделей.
  """

  def __init__(self):
    self.is_running = False
    self.tasks: Dict[str, asyncio.Task] = {}
    self.schedules: Dict[str, LotteryScheduleConfig] = {}
    self.logger = logging.getLogger('AutoUpdateScheduler')

    # Конфигурация расписаний лотерей
    self._init_lottery_schedules()

  def _init_lottery_schedules(self):
    """Инициализация расписаний для всех лотерей"""

    # 4x20 - фиксированные времена тиражей
    self.schedules['4x20'] = LotteryScheduleConfig(
      lottery_type='4x20',
      schedule_type='fixed_times',
      draw_times=['10:00', '12:00', '13:00', '16:00', '18:00', '20:00', '22:00'],
      check_offset_minutes=5  # Проверяем через 5 минут после тиража
    )

    # 5x36plus - каждые 15 минут
    self.schedules['5x36plus'] = LotteryScheduleConfig(
      lottery_type='5x36plus',
      schedule_type='interval',
      interval_minutes=15,
      check_delay_minutes=2,  # Проверяем через 2 минуты после тиража
      excluded_times=[]  # TODO: Добавить времена "Остатки сладки"
    )

  async def start_scheduler(self):
    """Запуск планировщика для всех лотерей"""
    if self.is_running:
      self.logger.warning("Планировщик уже запущен")
      return

    self.is_running = True
    self.logger.info("🕐 Запуск автоматического планировщика обновлений")

    # Запускаем отдельную задачу для каждой лотереи
    for lottery_type, schedule in self.schedules.items():
      task = asyncio.create_task(self._schedule_lottery_updates(lottery_type))
      self.tasks[lottery_type] = task
      self.logger.info(f"📅 Планировщик запущен для {lottery_type}")

    self.logger.info(f"✅ Планировщик активен для {len(self.schedules)} лотерей")

  async def stop_scheduler(self):
    """Остановка планировщика"""
    if not self.is_running:
      return

    self.is_running = False
    self.logger.info("🛑 Остановка планировщика...")

    # Отменяем все задачи
    for lottery_type, task in self.tasks.items():
      if not task.done():
        task.cancel()
        try:
          await task
        except asyncio.CancelledError:
          pass
      self.logger.info(f"📅 Планировщик остановлен для {lottery_type}")

    self.tasks.clear()
    self.logger.info("✅ Планировщик полностью остановлен")

  async def _schedule_lottery_updates(self, lottery_type: str):
    """Планирование обновлений для конкретной лотереи"""
    schedule = self.schedules[lottery_type]

    while self.is_running:
      try:
        # Вычисляем следующее время проверки
        next_check = schedule.get_next_check_time()
        current_time = datetime.now(schedule.timezone)

        sleep_seconds = (next_check - current_time).total_seconds()

        if sleep_seconds > 0:
          self.logger.info(f"⏰ {lottery_type}: следующая проверка в {next_check.strftime('%H:%M:%S')} "
                           f"(через {sleep_seconds / 60:.1f} мин)")
          await asyncio.sleep(sleep_seconds)

        # Проверяем новые тиражи и переобучаем модели
        if self.is_running:  # Проверяем, что не остановлены
          await self._update_and_retrain_lottery(lottery_type)

      except asyncio.CancelledError:
        break
      except Exception as e:
        self.logger.error(f"❌ Ошибка в планировщике {lottery_type}: {e}")
        # Ждем 1 минуту перед повторной попыткой
        await asyncio.sleep(60)

  async def _update_and_retrain_lottery(self, lottery_type: str):
    """Обновление данных и переобучение модели для конкретной лотереи"""
    try:
      self.logger.info(f"🔄 Проверка новых тиражей для {lottery_type}...")

      # Импортируем модули
      from backend.app.core import data_manager, ai_model
      from backend.app.core.lottery_context import LotteryContext

      # Устанавливаем контекст лотереи
      with LotteryContext(lottery_type):
        # Получаем текущее количество тиражей
        old_df = data_manager.fetch_draws_from_db()
        old_count = len(old_df)

        # Обновляем данные из источника
        data_manager.update_database_from_source()

        # Проверяем, появились ли новые тиражи
        new_df = data_manager.fetch_draws_from_db()
        new_count = len(new_df)

        if new_count > old_count:
          new_draws = new_count - old_count
          self.logger.info(f"🎯 {lottery_type}: найдено {new_draws} новых тиражей")

          # Получаем конфигурацию лотереи
          config = data_manager.LOTTERY_CONFIGS[lottery_type]

          # Переобучаем модели
          rf_model = ai_model.GLOBAL_MODEL_MANAGER.get_rf_model(lottery_type, config)
          lstm_model = ai_model.GLOBAL_MODEL_MANAGER.get_lstm_model(lottery_type, config)

          # Переобучаем RF модель
          self.logger.info(f"🧠 Переобучение RF модели для {lottery_type}...")
          rf_model.train(new_df)

          # Переобучаем LSTM модель
          try:
            self.logger.info(f"🧠 Переобучение LSTM модели для {lottery_type}...")
            lstm_model.train(new_df)
            lstm_trained = lstm_model.is_trained
          except Exception as e:
            self.logger.warning(f"⚠️ LSTM модель {lottery_type} не переобучена: {e}")
            lstm_trained = False

          status = "✅" if rf_model.is_trained else "❌"
          lstm_status = "✅" if lstm_trained else "⚠️"
          self.logger.info(f"🎉 {lottery_type}: модели обновлены! RF={status}, LSTM={lstm_status}")

        else:
          self.logger.info(f"💤 {lottery_type}: новых тиражей нет ({old_count} тиражей)")

    except Exception as e:
      self.logger.error(f"💥 Ошибка обновления {lottery_type}: {e}")

  def get_scheduler_status(self) -> dict:
    """Возвращает статус планировщика"""
    status = {
      'is_running': self.is_running,
      'active_tasks': len([t for t in self.tasks.values() if not t.done()]),
      'lotteries': {}
    }

    for lottery_type, schedule in self.schedules.items():
      next_check = schedule.get_next_check_time()
      current_time = datetime.now(schedule.timezone)
      time_until_check = (next_check - current_time).total_seconds() / 60

      status['lotteries'][lottery_type] = {
        'schedule_type': schedule.schedule_type,
        'next_check': next_check.strftime('%Y-%m-%d %H:%M:%S'),
        'minutes_until_check': round(time_until_check, 1),
        'task_running': lottery_type in self.tasks and not self.tasks[lottery_type].done()
      }

    return status


# Глобальный экземпляр планировщика
GLOBAL_AUTO_UPDATE_SCHEDULER = AutoUpdateScheduler()