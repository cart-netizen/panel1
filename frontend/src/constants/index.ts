import { LotteryType, LotteryConfig } from '../types';

// Конфигурация лотерей
export const LOTTERY_CONFIGS: Record<LotteryType, LotteryConfig> = {
  '4x20': {
    name: 'Спортлото 4 из 20',
    field1_size: 4,
    field1_max: 20,
    field2_size: 4,
    field2_max: 20,
    min_numbers: 1,
    max_numbers: 20,
    draw_times: ['09:00', '12:00', '15:00', '18:00', '21:00', '00:00', '03:00'],
    api_endpoints: {
      history: '/history',
      generate: '/generate',
      trends: '/trends',
      evaluate: '/evaluate-combination',
    },
  },
  '5x36plus': {
    name: '5 из 36 плюс',
    field1_size: 5,
    field1_max: 36,
    field2_size: 1,
    field2_max: 4,
    min_numbers: 1,
    max_numbers: 36,
    draw_times: ['12:00', '21:00'],
    api_endpoints: {
      history: '/history',
      generate: '/generate',
      trends: '/trends',
      evaluate: '/evaluate-combination',
    },
  },
};

// Типы генераторов
export const GENERATOR_TYPES = {
  rf_ranked: {
    name: 'RF Ранжированные',
    description: 'Комбинации на основе Random Forest модели с анализом трендов',
    icon: '🧠',
    complexity: 'high',
    estimatedTime: '1-2 сек',
  },
  multi_strategy: {
    name: 'Мульти-стратегия',
    description: 'Комбинация различных алгоритмов для максимального покрытия',
    icon: '🎯',
    complexity: 'high',
    estimatedTime: '2-3 сек',
  },
  ml_based_rf: {
    name: 'ML Random Forest',
    description: 'Машинное обучение на основе Random Forest',
    icon: '🤖',
    complexity: 'medium',
    estimatedTime: '1-2 сек',
  },
  hot: {
    name: 'Горячие числа',
    description: 'Часто выпадающие числа из недавних тиражей',
    icon: '🔥',
    complexity: 'low',
    estimatedTime: '< 1 сек',
  },
  cold: {
    name: 'Холодные числа',
    description: 'Давно не выпадавшие числа, готовые к выходу',
    icon: '❄️',
    complexity: 'low',
    estimatedTime: '< 1 сек',
  },
  balanced: {
    name: 'Сбалансированные',
    description: 'Оптимальное сочетание горячих и холодных чисел',
    icon: '⚖️',
    complexity: 'medium',
    estimatedTime: '< 1 сек',
  },
} as const;

// Планы подписки
export const SUBSCRIPTION_PLANS = {
  basic: {
    name: 'Базовый',
    icon: '📦',
    color: 'blue',
    limits: {
      generations_per_day: 20,
      history_days: 180,
      simulations_per_day: 5,
    },
  },
  premium: {
    name: 'Премиум',
    icon: '⭐',
    color: 'purple',
    limits: {
      generations_per_day: 100,
      history_days: 365,
      simulations_per_day: 25,
    },
  },
  pro: {
    name: 'Профессиональный',
    icon: '🚀',
    color: 'gold',
    limits: {
      generations_per_day: -1,
      history_days: -1,
      simulations_per_day: -1,
    },
  },
} as const;

// Цвета для трендов
export const TREND_COLORS = {
  hot: '#ef4444', // red-500
  cold: '#3b82f6', // blue-500
  momentum: '#f59e0b', // amber-500
  stable: '#6b7280', // gray-500
  ascending: '#10b981', // emerald-500
  descending: '#f97316', // orange-500
} as const;

// Риски оценки
export const RISK_LEVELS = {
  low: {
    label: 'Низкий',
    color: 'green',
    icon: '✅',
  },
  medium: {
    label: 'Средний',
    color: 'yellow',
    icon: '⚠️',
  },
  high: {
    label: 'Высокий',
    color: 'red',
    icon: '⛔',
  },
} as const;

// Типы уведомлений
export const NOTIFICATION_TYPES = {
  success: {
    icon: '✅',
    color: 'green',
    duration: 5000,
  },
  error: {
    icon: '❌',
    color: 'red',
    duration: 0, // Не автозакрытие
  },
  warning: {
    icon: '⚠️',
    color: 'yellow',
    duration: 7000,
  },
  info: {
    icon: 'ℹ️',
    color: 'blue',
    duration: 5000,
  },
} as const;

// Навигационные маршруты
export const ROUTES = {
  home: '/',
  login: '/login',
  register: '/register',
  dashboard: '/dashboard',
  generation: '/generation',
  trends: '/trends',
  analysis: '/analysis',
  history: '/history',
  profile: '/profile',
  settings: '/settings',
  subscriptions: '/subscriptions',
  help: '/help',
} as const;

// Размеры экранов для адаптивности
export const BREAKPOINTS = {
  xs: '480px',
  sm: '640px',
  md: '768px',
  lg: '1024px',
  xl: '1280px',
  '2xl': '1536px',
} as const;

// Эмодзи для лотерейных чисел
export const NUMBER_EMOJIS = [
  '0️⃣', '1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣',
  '🔟', '1️⃣1️⃣', '1️⃣2️⃣', '1️⃣3️⃣', '1️⃣4️⃣', '1️⃣5️⃣', '1️⃣6️⃣', '1️⃣7️⃣', '1️⃣8️⃣', '1️⃣9️⃣',
  '2️⃣0️⃣', '2️⃣1️⃣', '2️⃣2️⃣', '2️⃣3️⃣', '2️⃣4️⃣', '2️⃣5️⃣', '2️⃣6️⃣', '2️⃣7️⃣', '2️⃣8️⃣', '2️⃣9️⃣',
  '3️⃣0️⃣', '3️⃣1️⃣', '3️⃣2️⃣', '3️⃣3️⃣', '3️⃣4️⃣', '3️⃣5️⃣', '3️⃣6️⃣'
] as const;

// Статусы загрузки
export const LOADING_STATES = {
  idle: 'idle',
  loading: 'loading',
  success: 'success',
  error: 'error',
} as const;

// Форматы дат
export const DATE_FORMATS = {
  short: 'dd.MM.yyyy',
  long: 'dd MMMM yyyy',
  withTime: 'dd.MM.yyyy HH:mm',
  time: 'HH:mm',
  iso: "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'",
} as const;

// Локализация
export const LOCALES = {
  ru: {
    name: 'Русский',
    code: 'ru-RU',
    flag: '🇷🇺',
  },
  en: {
    name: 'English',
    code: 'en-US',
    flag: '🇺🇸',
  },
} as const;

// Лимиты API
export const API_LIMITS = {
  maxCombinationsPerGeneration: 10,
  maxHistoryFetch: 1000,
  maxFileSize: 5 * 1024 * 1024, // 5MB
  requestTimeout: 30000, // 30 секунд
  retryAttempts: 3,
  retryDelay: 1000,
} as const;

// Кэширование
export const CACHE_KEYS = {
  trends: 'lottery_trends',
  history: 'lottery_history',
  userPreferences: 'user_preferences',
  recentCombinations: 'recent_combinations',
  favorites: 'favorite_combinations',
} as const;

export const CACHE_DURATIONS = {
  trends: 30 * 1000, // 30 секунд
  history: 5 * 60 * 1000, // 5 минут
  userProfile: 10 * 60 * 1000, // 10 минут
  staticData: 60 * 60 * 1000, // 1 час
} as const;

// Анимации
export const ANIMATIONS = {
  fadeIn: 'animate-fade-in',
  slideUp: 'animate-slide-up',
  bounce: 'animate-bounce-gentle',
  pulse: 'animate-pulse-soft',
  spin: 'animate-spin',
} as const;

// Валидация
export const VALIDATION_RULES = {
  email: {
    pattern: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
    message: 'Введите корректный email адрес',
  },
  password: {
    minLength: 6,
    message: 'Пароль должен содержать минимум 6 символов',
  },
  phone: {
    pattern: /^\+?[1-9]\d{1,14}$/,
    message: 'Введите корректный номер телефона',
  },
} as const;

// Клавиши для навигации
export const KEY_CODES = {
  ENTER: 'Enter',
  ESCAPE: 'Escape',
  ARROW_UP: 'ArrowUp',
  ARROW_DOWN: 'ArrowDown',
  ARROW_LEFT: 'ArrowLeft',
  ARROW_RIGHT: 'ArrowRight',
  TAB: 'Tab',
  SPACE: ' ',
} as const;

// Социальные сети (для будущего использования)
export const SOCIAL_LINKS = {
  telegram: 'https://t.me/lottery_bot',
  vk: 'https://vk.com/lottery_group',
  youtube: 'https://youtube.com/lottery_channel',
  email: 'support@lottery-app.ru',
} as const;

// Справочная информация
export const HELP_SECTIONS = {
  gettingStarted: {
    title: 'Начало работы',
    icon: '🚀',
    items: [
      'Регистрация и вход',
      'Выбор лотереи',
      'Первая генерация',
      'Понимание результатов',
    ],
  },
  generation: {
    title: 'Генерация комбинаций',
    icon: '🎲',
    items: [
      'Типы генераторов',
      'Настройка параметров',
      'Анализ результатов',
      'Сохранение избранных',
    ],
  },
  trends: {
    title: 'Анализ трендов',
    icon: '📊',
    items: [
      'Горячие и холодные числа',
      'Паттерны выпадения',
      'Импульс чисел',
      'Прогнозирование',
    ],
  },
  subscription: {
    title: 'Подписки и лимиты',
    icon: '💎',
    items: [
      'Планы подписки',
      'Лимиты и ограничения',
      'Оплата и активация',
      'Управление подпиской',
    ],
  },
} as const;

// Метрики производительности
export const PERFORMANCE_METRICS = {
  fastGeneration: 1000, // < 1 сек
  normalGeneration: 3000, // < 3 сек
  slowGeneration: 5000, // < 5 сек
  trendsRefresh: 30000, // 30 сек
  dashboardRefresh: 120000, // 2 мин
} as const;

// Экспорт всех констант
export * from './routes';
export * from './themes';

// Дополнительные утилиты
export const getGeneratorInfo = (type: keyof typeof GENERATOR_TYPES) => {
  return GENERATOR_TYPES[type];
};

export const getLotteryConfig = (type: LotteryType) => {
  return LOTTERY_CONFIGS[type];
};

export const getSubscriptionPlan = (plan: keyof typeof SUBSCRIPTION_PLANS) => {
  return SUBSCRIPTION_PLANS[plan];
};

export const getRiskLevel = (risk: keyof typeof RISK_LEVELS) => {
  return RISK_LEVELS[risk];
};

export const getNotificationType = (type: keyof typeof NOTIFICATION_TYPES) => {
  return NOTIFICATION_TYPES[type];
};