// Конфигурация маршрутов приложения

export const ROUTES = {
  // Публичные маршруты
  HOME: '/',
  LOGIN: '/login',
  REGISTER: '/register',
  FORGOT_PASSWORD: '/forgot-password',

  // Защищенные маршруты
  DASHBOARD: '/dashboard',
  GENERATION: '/generation',
  TRENDS: '/trends',
  ANALYSIS: '/analysis',
  HISTORY: '/history',
  SIMULATION: '/simulation',

  // Пользовательские маршруты
  PROFILE: '/profile',
  SETTINGS: '/settings',
  SUBSCRIPTIONS: '/subscriptions',

  // Справочные маршруты
  HELP: '/help',
  ABOUT: '/about',
  PRIVACY: '/privacy',
  TERMS: '/terms',

  // Административные маршруты (для будущего)
  ADMIN: '/admin',
  ADMIN_USERS: '/admin/users',
  ADMIN_ANALYTICS: '/admin/analytics',
} as const;

// Метаданные маршрутов
export const ROUTE_META = {
  [ROUTES.HOME]: {
    title: 'Главная',
    description: 'Профессиональный анализ лотерей',
    icon: '🏠',
    requireAuth: false,
    showInNav: true,
  },
  [ROUTES.LOGIN]: {
    title: 'Вход',
    description: 'Вход в систему',
    icon: '🔐',
    requireAuth: false,
    showInNav: false,
  },
  [ROUTES.REGISTER]: {
    title: 'Регистрация',
    description: 'Создание аккаунта',
    icon: '📝',
    requireAuth: false,
    showInNav: false,
  },
  [ROUTES.DASHBOARD]: {
    title: 'Панель управления',
    description: 'Обзор статистики и активности',
    icon: '📊',
    requireAuth: true,
    showInNav: true,
    order: 1,
  },
  [ROUTES.GENERATION]: {
    title: 'Генерация',
    description: 'Создание умных комбинаций',
    icon: '🎲',
    requireAuth: true,
    showInNav: true,
    order: 2,
  },
  [ROUTES.TRENDS]: {
    title: 'Тренды',
    description: 'Анализ текущих трендов',
    icon: '📈',
    requireAuth: true,
    showInNav: true,
    order: 3,
  },
  [ROUTES.ANALYSIS]: {
    title: 'Анализ',
    description: 'Детальная аналитика',
    icon: '🔍',
    requireAuth: true,
    showInNav: true,
    order: 4,
  },
  [ROUTES.HISTORY]: {
    title: 'История',
    description: 'Архив тиражей',
    icon: '📚',
    requireAuth: true,
    showInNav: true,
    order: 5,
  },
  [ROUTES.SIMULATION]: {
    title: 'Симуляция',
    description: 'Моделирование стратегий',
    icon: '🧪',
    requireAuth: true,
    showInNav: true,
    order: 6,
  },
  [ROUTES.PROFILE]: {
    title: 'Профиль',
    description: 'Настройки профиля',
    icon: '👤',
    requireAuth: true,
    showInNav: false,
  },
  [ROUTES.SETTINGS]: {
    title: 'Настройки',
    description: 'Настройки приложения',
    icon: '⚙️',
    requireAuth: true,
    showInNav: false,
  },
  [ROUTES.SUBSCRIPTIONS]: {
    title: 'Подписки',
    description: 'Управление подпиской',
    icon: '💎',
    requireAuth: true,
    showInNav: false,
  },
  [ROUTES.HELP]: {
    title: 'Справка',
    description: 'Помощь и документация',
    icon: '❓',
    requireAuth: false,
    showInNav: true,
    order: 10,
  },
} as const;

// Группы маршрутов для навигации
export const NAVIGATION_GROUPS = {
  main: {
    title: 'Основные',
    routes: [
      ROUTES.DASHBOARD,
      ROUTES.GENERATION,
      ROUTES.TRENDS,
      ROUTES.ANALYSIS,
    ],
  },
  tools: {
    title: 'Инструменты',
    routes: [
      ROUTES.HISTORY,
      ROUTES.SIMULATION,
    ],
  },
  support: {
    title: 'Поддержка',
    routes: [
      ROUTES.HELP,
    ],
  },
} as const;

// Публичные маршруты (не требуют авторизации)
export const PUBLIC_ROUTES = [
  ROUTES.HOME,
  ROUTES.LOGIN,
  ROUTES.REGISTER,
  ROUTES.FORGOT_PASSWORD,
  ROUTES.ABOUT,
  ROUTES.PRIVACY,
  ROUTES.TERMS,
  ROUTES.HELP,
] as const;

// Защищенные маршруты (требуют авторизации)
export const PROTECTED_ROUTES = [
  ROUTES.DASHBOARD,
  ROUTES.GENERATION,
  ROUTES.TRENDS,
  ROUTES.ANALYSIS,
  ROUTES.HISTORY,
  ROUTES.SIMULATION,
  ROUTES.PROFILE,
  ROUTES.SETTINGS,
  ROUTES.SUBSCRIPTIONS,
] as const;

// Премиум маршруты (требуют активную подписку)
export const PREMIUM_ROUTES = [
  ROUTES.SIMULATION,
  ROUTES.ANALYSIS,
] as const;

// Утилиты для работы с маршрутами
export const getRouteTitle = (path: string): string => {
  const route = Object.values(ROUTES).find(r => r === path);
  return route ? ROUTE_META[route]?.title || 'Неизвестная страница' : 'Неизвестная страница';
};

export const getRouteIcon = (path: string): string => {
  const route = Object.values(ROUTES).find(r => r === path);
  return route ? ROUTE_META[route]?.icon || '📄' : '📄';
};

export const isPublicRoute = (path: string): boolean => {
  return PUBLIC_ROUTES.includes(path as any);
};

export const isProtectedRoute = (path: string): boolean => {
  return PROTECTED_ROUTES.includes(path as any);
};

export const isPremiumRoute = (path: string): boolean => {
  return PREMIUM_ROUTES.includes(path as any);
};

export const getNavigationRoutes = () => {
  return Object.values(ROUTE_META)
    .filter(meta => meta.showInNav)
    .sort((a, b) => (a.order || 999) - (b.order || 999))
    .map(meta => {
      const route = Object.keys(ROUTE_META).find(
        key => ROUTE_META[key as keyof typeof ROUTE_META] === meta
      );
      return { path: route, ...meta };
    });
};