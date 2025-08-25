# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Architecture

This is a full-stack lottery analysis application with AI/ML capabilities for predicting lottery numbers and analyzing patterns.

### Backend Structure
- **Framework**: FastAPI with async support
- **Database**: PostgreSQL with SQLAlchemy ORM 
- **AI/ML**: Random Forest and LSTM models using scikit-learn and PyTorch
- **Architecture**: Modular API with separate routers for different functionalities
- **Key Components**:
  - `backend/app/core/ai_model.py` - ML model management and training
  - `backend/app/core/data_manager.py` - Data fetching and database operations
  - `backend/app/core/lottery_context.py` - Context switching between lottery types
  - `backend/app/api/` - REST API endpoints organized by functionality
  - `backend/app/models/` - Pydantic schemas and data models

### Frontend Structure
- **Framework**: React 18 with TypeScript
- **UI**: Material-UI (MUI) + Tailwind CSS
- **State Management**: Zustand + React Query for server state
- **Routing**: React Router v6
- **Key Features**:
  - Authentication with JWT
  - Real-time lottery analysis and predictions
  - Interactive charts using Recharts
  - Responsive design with mobile support

### Data Architecture
- Multiple lottery types supported (4x20, 5x36plus)
- Context-based switching between lottery configurations
- Automated data scraping from lottery sources
- ML model training with caching and optimization

## Development Commands

### Backend Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run development server (FastAPI with uvicorn)
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8002

# Run with Docker Compose (full stack)
docker-compose up
```

### Frontend Development
```bash
cd frontend

# Install dependencies
npm install

# Development server
npm run dev
# or
npm start

# Build for production
npm run build

# Type checking
npm run type-check

# Linting
npm run lint

# Testing
npm test
```

### Database Operations
- Database initialization is handled automatically on application startup
- SQLite databases are stored in `data/` directory
- Each lottery type has its own database file

## Key Development Patterns

### Lottery Context System
The application uses a context system to handle multiple lottery types:
```python
from backend.app.core.lottery_context import LotteryContext

with LotteryContext('4x20'):
    # All operations will use 4x20 lottery configuration
    data = data_manager.fetch_draws_from_db()
```

### ML Model Management
- Models are trained automatically on startup if sufficient data exists
- RF (Random Forest) models are preferred for reliability
- LSTM models provide additional prediction capabilities
- Model caching is implemented for performance

### API Structure
- All lottery-specific endpoints use path parameter: `/api/v1/{lottery_type}/endpoint`
- Authentication endpoints are separate: `/api/v1/auth/`
- Subscription management: `/api/v1/subscriptions/`

### Frontend State Management
- Zustand for client state (auth, UI preferences)
- React Query for server state with automatic caching
- Form handling with React Hook Form + Yup validation

## Production Deployment

The application is configured for Docker deployment with:
- 4 API replicas with load balancing
- PostgreSQL with data persistence
- Redis for caching
- RabbitMQ for background tasks
- Nginx reverse proxy

## Environment Configuration

### Backend Environment Variables
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string
- `RABBITMQ_URL` - RabbitMQ connection string

### Frontend Environment Variables
- `REACT_APP_API_URL` - Backend API base URL (defaults to development server)

### 1. XGBoost с SHAP интерпретируемостью

- `backend/app/core/xgboost_model.py` - полноценная XGBoost модель с автоматическим feature engineering
- `backend/app/api/xgboost_routes.py` - API эндпоинты для генерации и объяснений
- `frontend/src/components/analysis/XGBoostAnalysis.tsx` - интерактивный UI компонент
- Интеграция с существующей системой генерации комбинаций
- SHAP объяснения показывают влияние каждого признака на решение

2. Walk-forward валидация

- `backend/app/core/validation/walk_forward.py` - корректная временная валидация без lookahead bias
- `backend/app/api/validation_routes.py` - API для запуска валидации и сравнения моделей
- `frontend/src/components/analysis/ValidationAnalysis.tsx` - UI для управления валидацией
- Фоновое выполнение длительных задач
- Объективное сравнение всех моделей на одинаковых данных

## Ключевые улучшения проекта:

- Предотвращение переобучения - теперь есть инструмент для реалистичной оценки моделей
- Прозрачность решений - SHAP объясняет каждое предсказание
- Повышение точности - XGBoost превосходит Random Forest
- Профессиональный уровень - критически важные компоненты для production ML

## Последние изменения Фаза 2 (Генетические алгоритмы)

### Добавленные файлы:
1. **backend/app/api/genetic_routes.py** - API эндпоинты для генетического алгоритма
   - POST /genetic/generate - генерация комбинаций
   - POST /genetic/evolve - запуск фоновой эволюции
   - GET /genetic/evolution/status/{task_id} - статус эволюции
   - GET /genetic/statistics - статистика последней эволюции
   - POST /genetic/predict - быстрое предсказание

2. **frontend/src/components/analysis/GeneticAnalysis.tsx** - React компонент
   - Управление параметрами эволюции
   - Отображение результатов
   - Фоновые задачи
   - Визуализация статистики

### Интеграция:
- Роутер зарегистрирован в backend/app/main.py
- Компонент добавлен в AnalysisPage.tsx
- Использует премиум подписку для доступа

### Архитектурные решения:
- Кэширование результатов эволюции
- Фоновое выполнение долгих задач
- Адаптивные параметры мутации/кроссовера
- Параллельная оценка fitness

### Зависимости:
- genetic_generator_integration.py - интеграция с combination_generator
- backend/app/core/genetic/* - основные модули GA
- Требует минимум 10 тиражей в истории

### Параметры эволюции:
- population_size: 20-200 (по умолчанию 50)
- generations: 10-100 (по умолчанию 30)
- elite_size: 2-50 (по умолчанию 10)
- mutation_rate: 0.01-0.5 (по умолчанию 0.1)
- crossover_rate: 0.5-1.0 (по умолчанию 0.8)

# Reinforcement Learning модуль для анализа лотерей

## Обзор

Модуль RL (Reinforcement Learning) использует методы обучения с подкреплением для оптимизации стратегий выбора лотерейных комбинаций. Модуль включает два основных алгоритма:

- **Q-Learning**: Классический табличный метод с оптимизацией памяти
- **Deep Q-Network (DQN)**: Нейросетевой подход с дуэльной архитектурой

## Архитектура

### Компоненты системы

```
backend/
├── app/
│   ├── core/
│   │   ├── rl/                      # Reinforcement Learning модуль
│   │   │   ├── environment.py       # Среда лотереи
│   │   │   ├── q_agent.py          # Q-Learning агент
│   │   │   ├── dqn_agent.py        # Deep Q-Network агент (ИСПРАВЛЕН)
│   │   │   ├── state_encoder.py    # Кодирование состояний
│   │   │   ├── reward_calculator.py # Расчет наград
│   │   │   └── rl_generator.py     # Интеграция агентов
│   │   ├── genetic/                 # Генетические алгоритмы
│   │   ├── ml_model.py             # Random Forest модель
│   │   ├── lstm_predictor.py       # LSTM модель
│   │   └── combination_generator.py # Базовый генератор
│   ├── api/
│   │   ├── rl_routes.py           # API для RL
│   │   └── genetic_routes.py      # API для GA
│   └── main.py                     # Главный файл FastAPI
├── models/                         # Сохраненные модели
│   └── rl/                        # RL модели
│       └── {lottery_type}/
│           ├── q_agent.pkl
│           └── dqn_agent.pth
└── tests/
    └── test_rl.py                  # Тесты RL модуля (22 теста)
```

### Основные классы

#### LotteryEnvironment
Среда для RL агентов, управляет:
- Состояниями (статистические признаки)
- Действиями (выбор комбинаций)
- Наградами (выигрыши/проигрыши)

#### LotteryState
Представление состояния среды:
- `universe_length`: Количество уникальных чисел за окно
- `parity_ratio`: Соотношение четных/нечетных
- `mean_gap`: Среднее расстояние между выпадениями
- `mean_frequency`: Средняя частота чисел
- `hot_numbers_count`: Количество горячих чисел
- `cold_numbers_count`: Количество холодных чисел
- `sum_trend`: Тренд суммы чисел
- `diversity_index`: Индекс разнообразия

#### QLearningAgent
- Использует Q-таблицу для хранения значений состояние-действие
- Epsilon-greedy стратегия для баланса исследования/эксплуатации
- Оптимизация памяти при превышении лимита

#### DQNAgent
- Нейронная сеть для аппроксимации Q-функции
- Дуэльная архитектура (Value + Advantage streams)
- Experience replay buffer для стабильного обучения
- Target network для уменьшения нестабильности

## Использование

### Обучение агентов

```python
from backend.app.core.rl.rl_generator import RLGenerator

# Создание генератора
config = {
    'field1_size': 5,
    'field2_size': 1,
    'field1_max': 36,
    'field2_max': 4,
    'db_table': 'draws_5_36'
}

generator = RLGenerator(config)

# Обучение
stats = generator.train(
    df_history=lottery_data,
    q_episodes=1000,      # Эпизоды для Q-Learning
    dqn_episodes=500,     # Эпизоды для DQN
    window_size=50        # Размер окна для признаков
)
```

### Генерация комбинаций

```python
# Генерация с помощью обученных агентов
combinations = generator.generate_combinations(
    count=5,                    # Количество комбинаций
    strategy='ensemble',        # 'q_learning', 'dqn', или 'ensemble'
    df_history=lottery_data
)

# Результат
for combo in combinations:
    print(f"Поле 1: {combo['field1']}")
    print(f"Поле 2: {combo['field2']}")
    print(f"Уверенность: {combo['confidence']:.2%}")
```

### Оценка производительности

```python
# Оценка на тестовых данных
metrics = generator.evaluate(
    df_test=test_data,
    window_size=50
)

# Метрики для каждого агента
for agent_name, agent_metrics in metrics.items():
    print(f"{agent_name}:")
    print(f"  Средняя награда: {agent_metrics['average_reward']:.2f}")
    print(f"  Win rate: {agent_metrics['win_rate']:.1f}%")
    print(f"  ROI: {agent_metrics['roi']:.2f}%")
```

## API Эндпоинты

### Обучение агентов
```http
POST /api/rl/train/{lottery_type}
```

Параметры:
- `q_episodes`: Количество эпизодов Q-Learning (по умолчанию 500)
- `dqn_episodes`: Количество эпизодов DQN (по умолчанию 300)
- `window_size`: Размер окна признаков (по умолчанию 50)

### Генерация комбинаций
```http
GET /api/rl/generate/{lottery_type}?count=5&strategy=ensemble
```

Параметры:
- `count`: Количество комбинаций (1-20)
- `strategy`: Стратегия генерации (q_learning, dqn, ensemble)

### Статус агентов
```http
GET /api/rl/status/{lottery_type}
```

Возвращает:
- Статус обученности агентов
- Статистику обучения
- Текущие параметры

### Оценка производительности
```http
POST /api/rl/evaluate/{lottery_type}
```

Параметры:
- `test_size`: Размер тестовой выборки (по умолчанию 100)

## Настройка параметров

### Q-Learning параметры

| Параметр | По умолчанию | Описание |
|----------|--------------|----------|
| learning_rate | 0.1 | Скорость обучения (α) |
| discount_factor | 0.95 | Фактор дисконтирования (γ) |
| epsilon | 1.0 | Начальная вероятность случайного действия |
| epsilon_decay | 0.995 | Скорость затухания epsilon |
| epsilon_min | 0.01 | Минимальное значение epsilon |
| memory_limit | 100000 | Максимальный размер Q-таблицы |

### DQN параметры

| Параметр | По умолчанию | Описание |
|----------|--------------|----------|
| learning_rate | 0.001 | Скорость обучения нейросети |
| discount_factor | 0.99 | Фактор дисконтирования |
| batch_size | 32 | Размер батча для обучения |
| memory_size | 10000 | Размер replay buffer |
| target_update_freq | 100 | Частота обновления target network |

## Схемы наград

### Базовая схема
- Стоимость билета: -1.0
- 2 совпадения: +2.0
- 3 совпадения: +10.0
- 4 совпадения: +100.0
- 5 совпадений: +1000.0
- Джекпот: +10000.0

### Shaped Reward
Дополнительно к базовой схеме:
- Proximity bonus: награда за близость к правильным числам
- Improvement bonus: награда за улучшение результатов
- Hot number bonus: +0.1 за использование горячих чисел
- Pattern bonus: +0.5 за обнаружение паттернов

## Оптимизация производительности

### Кэширование
- Состояния кэшируются в `StateEncoder`
- Действия кэшируются в `ActionEncoder`
- Q-значения хранятся в оптимизированной таблице

### Управление памятью
- Автоматическая очистка Q-таблицы при превышении лимита
- Удаление наименее посещаемых состояний
- Сжатие replay buffer в DQN

### GPU ускорение
DQN автоматически использует GPU если доступна:
```python
generator = RLGenerator(config, use_gpu=True)
```

## Интерпретация результатов

### Уверенность (Confidence)
- 0-30%: Низкая уверенность, почти случайный выбор
- 30-60%: Средняя уверенность, некоторые паттерны обнаружены
- 60-80%: Высокая уверенность, устойчивые паттерны
- 80-100%: Очень высокая уверенность (редко достигается)

### Win Rate
- < 1%: Типично для случайной стратегии
- 1-5%: Небольшое улучшение над случайным выбором
- 5-10%: Заметное улучшение (хороший результат)
- > 10%: Исключительный результат (проверьте на переобучение)

### ROI (Return on Investment)
- < -50%: Значительные потери
- -50% до -20%: Типичные потери в лотерее
- -20% до 0%: Лучше среднего
- > 0%: Прибыльная стратегия (маловероятно в честной лотерее)

## Рекомендации

1. **Обучение**: Начните с 500-1000 эпизодов для Q-Learning и 300-500 для DQN
2. **Window Size**: Используйте 50-100 для достаточного контекста
3. **Стратегия**: Ensemble обычно дает лучшие результаты
4. **Валидация**: Всегда проверяйте на отложенных данных
5. **Переобучение**: Следите за слишком высокими метриками на обучении

## Ограничения

- RL агенты не могут предсказать истинно случайные события
- Результаты зависят от качества исторических данных
- Требуется минимум 60 тиражей для обучения
- GPU рекомендуется для DQN при больших объемах данных

## Примеры использования

### Полный цикл работы

```python
# 1. Импорт
from backend.app.core.rl.rl_generator import GLOBAL_RL_MANAGER
from backend.app.core import data_manager

# 2. Получение данных
lottery_type = '5_36'
config = data_manager.LOTTERY_CONFIGS[lottery_type]
df = data_manager.fetch_draws_from_db()

# 3. Получение генератора
generator = GLOBAL_RL_MANAGER.get_generator(lottery_type, config)

# 4. Обучение (если не обучен)
if not generator.q_trained and not generator.dqn_trained:
    stats = generator.train(df, verbose=True)
    print(f"Q-Learning Win Rate: {stats['q_learning']['win_rate']:.1f}%")
    print(f"DQN Win Rate: {stats['dqn']['win_rate']:.1f}%")

# 5. Генерация комбинаций
combos = generator.generate_combinations(count=5, strategy='ensemble')

# 6. Вывод результатов
for i, combo in enumerate(combos, 1):
    print(f"\nКомбинация #{i}")
    print(f"Числа: {combo['field1']} + {combo['field2']}")
    print(f"Метод: {combo['method']}")
    print(f"Уверенность: {combo['confidence']:.1%}")

# 7. Оценка на новых данных
test_metrics = generator.evaluate(df.tail(50))
print(f"\nРезультаты тестирования:")
for agent, metrics in test_metrics.items():
    print(f"{agent}: ROI = {metrics['roi']:.2f}%")
```

## Troubleshooting

### Проблема: Агенты не обучаются
- Проверьте наличие достаточного количества данных (минимум 60 тиражей)
- Увеличьте количество эпизодов
- Проверьте правильность конфигурации лотереи

### Проблема: Низкая производительность
- Уменьшите window_size для ускорения
- Используйте GPU для DQN
- Оптимизируйте memory_limit для Q-Learning

### Проблема: Переобучение
- Уменьшите количество эпизодов
- Увеличьте epsilon_min
- Используйте больше данных для обучения

## Дальнейшее развитие

Планируемые улучшения:
- Добавление PPO (Proximal Policy Optimization) агента
- Multi-agent обучение
- Автоматический подбор гиперпараметров
- Визуализация процесса обучения
- Экспорт моделей в ONNX формат

Компоненты RL модуля
Статус тестирования
✅ 22/22 тестов пройдено успешно:

4 теста LotteryEnvironment
3 теста StateEncoder
2 теста ActionEncoder
2 теста RewardCalculator
4 теста QLearningAgent
4 теста DQNAgent
3 теста RLGenerator

LotteryEnvironment

Управляет состояниями, действиями, наградами
Вычисляет статистические признаки
Окно по умолчанию: 50 тиражей

LotteryState
Признаки состояния:

universe_length: Уникальные числа за окно
parity_ratio: Соотношение четных/нечетных
mean_gap: Среднее расстояние между выпадениями
mean_frequency: Средняя частота чисел
hot_numbers_count: Горячие числа
cold_numbers_count: Холодные числа
sum_trend: Тренд суммы
diversity_index: Индекс разнообразия

QLearningAgent

Q-таблица для хранения значений
Epsilon-greedy стратегия
Оптимизация памяти при превышении лимита (100k записей)

DQNAgent

Нейронная сеть для аппроксимации Q-функции
Архитектура: 625,917 параметров (после исправлений)
Дуэльная архитектура (Value + Advantage)
Experience replay buffer (10k образцов)
Target network для стабильности
Поддержка GPU (автоопределение)
Три головы нейросети:

q_head: Q-значения действий (128 → 256 → action_embedding_size)
field1_head: Предсказание field1 (256 → 50 чисел)
field2_head: Предсказание field2 (128 → 12 чисел)



Схемы наград
Базовая схема:

Билет: -1.0
2 совпадения: +2.0
3 совпадения: +10.0
4 совпадения: +100.0
5 совпадений: +1000.0
Джекпот: +10000.0

Shaped Reward (дополнительно):

Proximity bonus за близость к числам
Hot number bonus +0.1
Pattern bonus +0.5

Параметры обучения
Q-Learning

learning_rate: 0.1
discount_factor: 0.95
epsilon: 1.0 → 0.01
epsilon_decay: 0.995
episodes: 500-1000 (рекомендуется)

DQN

learning_rate: 0.001
discount_factor: 0.99
batch_size: 32
memory_size: 10000
target_update_freq: 100 шагов
episodes: 300-500 (рекомендуется)

API эндпоинты
Обучение
httpPOST /api/rl/train/{lottery_type}
Параметры: q_episodes, dqn_episodes, window_size
Генерация
httpGET /api/rl/generate/{lottery_type}?count=5&strategy=ensemble
Стратегии: q_learning, dqn, ensemble
Статус
httpGET /api/rl/status/{lottery_type}
Оценка
httpPOST /api/rl/evaluate/{lottery_type}
Интерпретация метрик
Win Rate

< 1%: Случайная стратегия
1-5%: Небольшое улучшение
5-10%: Хороший результат


10%: Проверить на переобучение



Confidence (уверенность)

0-30%: Низкая
30-60%: Средняя
60-80%: Высокая
80-100%: Очень высокая

Требования к данным

Минимум 60 тиражей для обучения
Оптимально 100+ тиражей
Window size: 50-100 тиражей

Известные ограничения

RL не может предсказать истинно случайные события
Результаты зависят от качества исторических данных
GPU рекомендуется для DQN при больших объемах

TODO (планируемые улучшения)

✅ Исправить DQNNetwork - добавить недостающие головы
✅ Исправить replay() - использовать self.batch_size
✅ Все 22 теста успешно проходят
⏳ Оптимизировать создание тензоров в replay()
⏳ Добавить PPO (Proximal Policy Optimization) агента
⏳ Реализовать A3C (Asynchronous Advantage Actor-Critic)
⏳ Добавить визуализацию обучения в реальном времени
⏳ Интегрировать SHAP для интерпретации решений

Критические замечания

Всегда проверять на отложенных данных
Следить за переобучением
Ensemble стратегия обычно дает лучшие результаты
Не доверять слишком высоким метрикам (> 10% win rate)


## Последние изменения (Фаза 4: Временные ряды)

### Добавленные модули:
1. **backend/app/core/timeseries/** - Полный модуль анализа временных рядов
   - `arima_model.py` - ARIMA/SARIMA модели с auto_arima
   - `acf_pacf_analysis.py` - Анализ автокорреляций и подбор параметров
   - `seasonality.py` - Детектор сезонности через спектральный анализ
   - `trend_decomposition.py` - Декомпозиция трендов (линейный, полиномиальный, HP-фильтр)
   - `timeseries_generator.py` - Интегрированный генератор на основе всех методов

2. **backend/app/api/timeseries_routes.py** - API эндпоинты
   - POST /timeseries/analyze/{lottery_type} - Полный анализ
   - GET /timeseries/generate/{lottery_type} - Генерация комбинаций
   - GET /timeseries/acf-pacf/{lottery_type} - ACF/PACF анализ
   - GET /timeseries/seasonality/{lottery_type} - Поиск сезонности
   - GET /timeseries/trends/{lottery_type} - Анализ трендов
   - POST /timeseries/forecast/{lottery_type} - ARIMA прогноз

3. **frontend/src/components/analysis/TimeSeriesAnalysis.tsx** - UI компонент
   - 4 вкладки: Генерация, ACF/PACF, Сезонность, Тренды
   - Интерактивные графики с Recharts
   - Настраиваемые параметры анализа
   - Визуализация результатов

### Ключевые возможности:
- Автоматический подбор ARIMA параметров через auto_arima
- Тест Дики-Фуллера на стационарность
- Спектральный анализ для поиска сезонности
- Множественные методы извлечения трендов
- Интеграция всех методов в единый генератор
- Оценка уверенности на основе найденных паттернов


## Последние изменения (Фаза 5: Байесовские методы)

### Добавленные модули:
1. **backend/app/core/bayesian/** - Полный модуль байесовских методов
   - `prior_posterior.py` - Управление априорными/апостериорными распределениями Дирихле
   - `dirichlet_model.py` - Реализация Compound Dirichlet-Multinomial (CDM) модели
   - `bayesian_updater.py` - Инкрементальное байесовское обновление с адаптацией
   - `cdm_generator.py` - Генератор комбинаций на основе CDM

2. **backend/app/api/bayesian_routes.py** - API эндпоинты
   - POST /bayesian/train/{lottery_type} - Обучение CDM модели
   - GET /bayesian/generate/{lottery_type} - Генерация комбинаций
   - POST /bayesian/update/{lottery_type} - Инкрементальное обновление
   - GET /bayesian/probability-analysis/{lottery_type} - Анализ вероятностей
   - GET /bayesian/hot-cold-analysis/{lottery_type} - Байесовский анализ горячих/холодных
   - POST /bayesian/simulate/{lottery_type} - Симуляция производительности
   - GET /bayesian/posterior-distribution/{lottery_type} - Апостериорное распределение

3. **frontend/src/components/analysis/BayesianAnalysis.tsx** - UI компонент
   - 4 вкладки: Генерация, Анализ вероятностей, Горячие/Холодные, Симуляция
   - Визуализация апостериорных распределений
   - Доверительные интервалы и тепловые карты
   - Метрики сходимости и производительности

### Ключевые возможности CDM модели:
- **Распределение Дирихле** для моделирования вероятностей
- **Мультиномиальное распределение** для наблюдений
- **Байесовское обновление** параметров альфа
- **Адаптивная концентрация** для автоподстройки
- **Инкрементальное обучение** на новых данных
- **Доверительные интервалы** для всех оценок
- **Кросс-валидация** для оценки качества
- **Симуляция производительности** с ROI метриками

### Математические основы:
- Априорное: `p ~ Dir(α)`
- Правдоподобие: `x | p ~ Multinomial(n, p)`
- Апостериорное: `p | x ~ Dir(α + counts)`
- Предсказание: `P(x_new) = ∫ P(x_new|p)P(p|data)dp`

### Статус: ✅ Фаза 5 завершена

## Реализованные фазы проекта:
1. ✅ **XGBoost с SHAP интерпретируемостью**
2. ✅ **Walk-forward валидация**
3. ✅ **Генетические алгоритмы**
4. ✅ **Reinforcement Learning (Q-Learning + DQN)**
5. ✅ **Временные ряды (ARIMA/SARIMA)**
6. ✅ **Байесовские методы (CDM модель)**

## Архитектурные особенности:
- Модульная структура с независимыми компонентами
- Единый LotteryContext для управления типами лотерей
- Кэширование моделей в глобальных менеджерах
- Инкрементальное обучение без потери состояния
- Полная интеграция frontend/backend
- Премиум-функции для продвинутых методов