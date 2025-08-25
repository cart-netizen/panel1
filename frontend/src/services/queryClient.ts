import { QueryClient, DefaultOptions } from '@tanstack/react-query';
import { useMutation, useQuery } from '@tanstack/react-query';
// Конфигурация по умолчанию для React Query
const queryConfig: DefaultOptions = {
  queries: {
    // Время жизни кэша - 5 минут
    staleTime: 5 * 60 * 1000,
    // Время хранения неактивных данных - 10 минут (исправлено)
    gcTime: 10 * 60 * 1000,
    // Повторные попытки при ошибке
    retry: (failureCount, error: any) => {
      // Не повторяем для 401, 403, 404
      if (error?.response?.status === 401 ||
          error?.response?.status === 403 ||
          error?.response?.status === 404) {
        return false;
      }
      // Максимум 3 попытки для других ошибок
      return failureCount < 3;
    },
    // Задержка между попытками (экспоненциальная)
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
    // Обновление при фокусе окна (только для критических данных)
    refetchOnWindowFocus: false,
    // Обновление при восстановлении соединения
    refetchOnReconnect: true,
    // Показывать ошибки в консоли только в development (исправлено)
    throwOnError: false,
  },
  mutations: {
    // Повторные попытки для мутаций
    retry: 1,
    // Обработка ошибок мутаций (исправлено)
    throwOnError: false,
  },
};

// Создаем клиент React Query
export const queryClient = new QueryClient({
  defaultOptions: queryConfig,
});

// Ключи для кэширования запросов
export const QUERY_KEYS = {
  // Пользователь и авторизация
  auth: {
    currentUser: ['auth', 'currentUser'] as const,
    profile: ['auth', 'profile'] as const,
    subscription: ['auth', 'subscription'] as const,
  },

  // Лотерейные данные
  lottery: {
    // Тренды
    trends: (lotteryType: string) => ['lottery', 'trends', lotteryType] as const,
    trendsDetailed: (lotteryType: string) => ['lottery', 'trends', 'detailed', lotteryType] as const,

    // История тиражей
    history: (lotteryType: string, page?: number, limit?: number) =>
      ['lottery', 'history', lotteryType, page, limit] as const,

    // Генерация комбинаций
    generation: (lotteryType: string, params: any) =>
      ['lottery', 'generation', lotteryType, params] as const,

    // Оценка комбинаций
    evaluation: (lotteryType: string, field1: number[], field2: number[]) =>
      ['lottery', 'evaluation', lotteryType, field1, field2] as const,

    // Статистика
    stats: (lotteryType: string) => ['lottery', 'stats', lotteryType] as const,
  },

  // Dashboard
  dashboard: {
    stats: ['dashboard', 'stats'] as const,
    activity: ['dashboard', 'activity'] as const,
    overview: ['dashboard', 'overview'] as const,
  },

  // Подписки
  subscriptions: {
    plans: ['subscriptions', 'plans'] as const,
    current: ['subscriptions', 'current'] as const,
  },

  // Симуляции
  simulations: {
    results: (params: any) => ['simulations', 'results', params] as const,
    history: ['simulations', 'history'] as const,
  },
} as const;

// Утилиты для работы с кэшем
export const cacheUtils = {
  // Инвалидация всех данных пользователя
  invalidateUserData: () => {
    queryClient.invalidateQueries({ queryKey: QUERY_KEYS.auth.currentUser });
    queryClient.invalidateQueries({ queryKey: QUERY_KEYS.auth.profile });
    queryClient.invalidateQueries({ queryKey: QUERY_KEYS.dashboard.stats });
  },

  // Инвалидация данных лотереи
  invalidateLotteryData: (lotteryType: string) => {
    queryClient.invalidateQueries({
      queryKey: ['lottery', lotteryType],
      exact: false
    });
  },

  // Инвалидация трендов
  invalidateTrends: (lotteryType: string) => {
    queryClient.invalidateQueries({
      queryKey: QUERY_KEYS.lottery.trends(lotteryType)
    });
    queryClient.invalidateQueries({
      queryKey: QUERY_KEYS.lottery.trendsDetailed(lotteryType)
    });
  },

  // Очистка всего кэша
  clearAllCache: () => {
    queryClient.clear();
  },

  // Предварительная загрузка данных
  prefetchTrends: async (lotteryType: string) => {
    await queryClient.prefetchQuery({
      queryKey: QUERY_KEYS.lottery.trends(lotteryType),
      staleTime: 2 * 60 * 1000, // 2 минуты
    });
  },

  // Установка данных в кэш
  setQueryData: <T>(queryKey: any[], data: T) => {
    queryClient.setQueryData(queryKey, data);
  },

  // Получение данных из кэша
  getQueryData: <T>(queryKey: any[]): T | undefined => {
    return queryClient.getQueryData<T>(queryKey);
  },

  // Обновление данных в кэше
  updateQueryData: <T>(queryKey: any[], updater: (oldData: T | undefined) => T) => {
    queryClient.setQueryData<T>(queryKey, updater);
  },
};

// Настройка автоматического обновления данных
export const setupAutoRefresh = () => {
  // Обновляем тренды каждые 30 секунд для активной лотереи
  const refreshTrends = () => {
    const activeLottery = localStorage.getItem('selectedLottery') || '4x20';
    queryClient.invalidateQueries({
      queryKey: QUERY_KEYS.lottery.trends(activeLottery)
    });
  };

  // Обновляем статистику dashboard каждые 2 минуты
  const refreshDashboard = () => {
    queryClient.invalidateQueries({
      queryKey: QUERY_KEYS.dashboard.stats
    });
  };

  // Устанавливаем интервалы
  const trendsInterval = setInterval(refreshTrends, 30 * 1000); // 30 секунд
  const dashboardInterval = setInterval(refreshDashboard, 2 * 60 * 1000); // 2 минуты

  // Функция для очистки интервалов
  return () => {
    clearInterval(trendsInterval);
    clearInterval(dashboardInterval);
  };
};

// Хуки для работы с ошибками
export const errorHandlers = {
  // Глобальный обработчик ошибок запросов
  onError: (error: any) => {
    console.error('Query Error:', error);

    // Если 401 - разлогиниваем пользователя
    if (error?.response?.status === 401) {
      cacheUtils.clearAllCache();
      window.location.href = '/login';
      return;
    }

    // TODO: Показать уведомление об ошибке
    const message = error?.response?.data?.detail ||
                   error?.response?.data?.message ||
                   error?.message ||
                   'Произошла ошибка';

    console.error('Global Error:', message);
  },

  // Обработчик ошибок мутаций
  onMutationError: (error: any, variables: any, context: any) => {
    console.error('Mutation Error:', error, variables, context);

    // TODO: Показать уведомление об ошибке мутации
    const message = error?.response?.data?.detail ||
                   error?.response?.data?.message ||
                   'Ошибка при выполнении операции';

    console.error('Mutation Error:', message);
  },
};

// Настройка глобальных обработчиков
queryClient.setDefaultOptions({
  queries: {
  ...queryConfig.queries,
  // onError удален в новых версиях TanStack Query
},
mutations: {
  ...queryConfig.mutations,
  // onError удален в новых версиях TanStack Query
},
});

export default queryClient;



// Хук useQuery с обработкой ошибок
export const useQueryWithErrorHandling = (options: any) => {
  return useQuery({
    ...options,
    onError: (error: any) => {
      errorHandlers.onError(error);
    },
  });
};

// Хук useMutation с обработкой ошибок
export const useMutationWithErrorHandling = (options: any) => {
  return useMutation({
    ...options,
    onError: (error: any) => {
      errorHandlers.onError(error);
    },
  });
};