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

  // Административные маршруты
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
    order: 0,
  },
  [ROUTES.LOGIN]: {
    title: 'Вход',
    description: 'Вход в систему',
    icon: '🔐',
    requireAuth: false,
    showInNav: false,
    order: 999,
  },
  [ROUTES.REGISTER]: {
    title: 'Регистрация',
    description: 'Создание аккаунта',
    icon: '📝',
    requireAuth: false,
    showInNav: false,
    order: 999,
  },
  [ROUTES.FORGOT_PASSWORD]: {
    title: 'Восстановление пароля',
    description: 'Восстановление доступа',
    icon: '🔑',
    requireAuth: false,
    showInNav: false,
    order: 999,
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
    order: 999,
  },
  [ROUTES.SETTINGS]: {
    title: 'Настройки',
    description: 'Настройки приложения',
    icon: '⚙️',
    requireAuth: true,
    showInNav: false,
    order: 999,
  },
  [ROUTES.SUBSCRIPTIONS]: {
    title: 'Подписки',
    description: 'Управление подпиской',
    icon: '💎',
    requireAuth: true,
    showInNav: false,
    order: 999,
  },
  [ROUTES.HELP]: {
    title: 'Справка',
    description: 'Помощь и документация',
    icon: '❓',
    requireAuth: false,
    showInNav: true,
    order: 7,
  },
  [ROUTES.ABOUT]: {
    title: 'О нас',
    description: 'Информация о проекте',
    icon: 'ℹ️',
    requireAuth: false,
    showInNav: false,
    order: 999,
  },
  [ROUTES.PRIVACY]: {
    title: 'Конфиденциальность',
    description: 'Политика конфиденциальности',
    icon: '🔒',
    requireAuth: false,
    showInNav: false,
    order: 999,
  },
  [ROUTES.TERMS]: {
    title: 'Условия использования',
    description: 'Пользовательское соглашение',
    icon: '📋',
    requireAuth: false,
    showInNav: false,
    order: 999,
  },
  [ROUTES.ADMIN]: {
    title: 'Админ панель',
    description: 'Административная панель',
    icon: '⚡',
    requireAuth: true,
    showInNav: false,
    order: 999,
  },
  [ROUTES.ADMIN_USERS]: {
    title: 'Пользователи',
    description: 'Управление пользователями',
    icon: '👥',
    requireAuth: true,
    showInNav: false,
    order: 999,
  },
  [ROUTES.ADMIN_ANALYTICS]: {
    title: 'Аналитика',
    description: 'Административная аналитика',
    icon: '📊',
    requireAuth: true,
    showInNav: false,
    order: 999,
  },
} as const;

// Группы навигации
export const NAVIGATION_GROUPS = {
  MAIN: {
    title: 'Основное',
    routes: [ROUTES.DASHBOARD, ROUTES.GENERATION, ROUTES.TRENDS, ROUTES.HISTORY],
  },
  TOOLS: {
    title: 'Инструменты',
    routes: [ROUTES.ANALYSIS, ROUTES.SIMULATION],
  },
  HELP: {
    title: 'Поддержка',
    routes: [ROUTES.HELP],
  },
} as const;

// Утилиты для работы с маршрутами
export const getRouteTitle = (path: string): string => {
  const route = Object.values(ROUTES).find(r => r === path);
  if (!route) return 'Неизвестная страница';

  const routeKey = route as keyof typeof ROUTE_META;
  return ROUTE_META[routeKey]?.title || 'Неизвестная страница';
};

export const getRouteIcon = (path: string): string => {
  const route = Object.values(ROUTES).find(r => r === path);
  if (!route) return '📄';

  const routeKey = route as keyof typeof ROUTE_META;
  return ROUTE_META[routeKey]?.icon || '📄';
};

export const isPublicRoute = (path: string): boolean => {
  const route = Object.values(ROUTES).find(r => r === path);
  if (!route) return false;

  const routeKey = route as keyof typeof ROUTE_META;
  return !ROUTE_META[routeKey]?.requireAuth;
};

export const isProtectedRoute = (path: string): boolean => {
  return !isPublicRoute(path);
};

export const isPremiumRoute = (path: string): boolean => {
  const premiumRoutes = [ROUTES.ANALYSIS, ROUTES.SIMULATION];
  return premiumRoutes.includes(path as any);
};

export const getNavigationRoutes = () => {
  return Object.entries(ROUTE_META)
    .filter(([_, meta]) => meta.showInNav)
    .sort((a, b) => (a[1].order || 999) - (b[1].order || 999))
    .map(([route, meta]) => ({
      path: route,
      title: meta.title,
      icon: meta.icon,
      requireAuth: meta.requireAuth,
    }));
};

export type RouteKey = keyof typeof ROUTES;
export type RoutePath = typeof ROUTES[RouteKey];
export type RouteMetaData = typeof ROUTE_META[RoutePath];