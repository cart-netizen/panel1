// src/constants/queryKeys.ts
export const QUERY_KEYS = {
  dashboard: {
    stats: ['dashboard', 'stats'] as const,
    activities: ['dashboard', 'activities'] as const,
  },
  generation: {
    combinations: ['generation', 'combinations'] as const,
    history: ['generation', 'history'] as const,
  },
  trends: {
    data: ['trends', 'data'] as const,
    analysis: ['trends', 'analysis'] as const,
  },
  user: {
    profile: ['user', 'profile'] as const,
    subscriptions: ['user', 'subscriptions'] as const,
    favorites: ['user', 'favorites'] as const,
    recent: ['user', 'recent'] as const,
  },
  // Лотерейные данные
  lottery: {
    trends: (lotteryType: string) => ['lottery', 'trends', lotteryType] as const,
    trendsDetailed: (lotteryType: string) => ['lottery', 'trends', 'detailed', lotteryType] as const,
    history: (lotteryType: string, page?: number, limit?: number) =>
      ['lottery', 'history', lotteryType, { page, limit }] as const,
    generation: (lotteryType: string) => ['lottery', 'generation', lotteryType] as const,
    evaluate: (lotteryType: string) => ['lottery', 'evaluate', lotteryType] as const,
    modelStatus: (lotteryType: string) => ['lottery', 'model-status', lotteryType] as const,
  },
    // Пользователь и авторизация
  auth: {
    currentUser: ['auth', 'currentUser'] as const,
    profile: ['auth', 'profile'] as const,
    subscription: ['auth', 'subscription'] as const,
  },
} as const;