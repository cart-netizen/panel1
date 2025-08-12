import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useUser, useSelectedLottery } from '../../store';
import { ROUTES, LOTTERY_CONFIGS, QUERY_KEYS } from '../../constants';
import { StatsCard, StatsCardSkeleton } from '../../components/common/StatsCard';
import { Button } from '../../components/common/Button';
import { LoadingScreen } from '../../components/common/LoadingScreen';
import { apiClient } from '../../services/api';

export const DashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const user = useUser();
  const selectedLottery = useSelectedLottery();

  // Загружаем статистику dashboard
  const { data: stats, isLoading: statsLoading, error: statsError } = useQuery({
    queryKey: QUERY_KEYS.dashboard.stats,
    queryFn: async () => {
      const response = await apiClient.get('/dashboard/stats');
      return response.data;
    },
    staleTime: 2 * 60 * 1000, // 2 минуты
    retry: 2,
  });

  // Загружаем текущие тренды
  const { data: trends, isLoading: trendsLoading } = useQuery({
    queryKey: QUERY_KEYS.lottery.trends(selectedLottery),
    queryFn: async () => {
      const response = await apiClient.lotteryRequest(selectedLottery, '/trends');
      return response.data;
    },
    staleTime: 30 * 1000, // 30 секунд
  });

  const handleQuickGeneration = () => {
    navigate(ROUTES.GENERATION);
  };

  const handleViewTrends = () => {
    navigate(ROUTES.TRENDS);
  };

  const handleUpgradeSubscription = () => {
    navigate(ROUTES.SUBSCRIPTIONS);
  };

  if (statsLoading && !stats) {
    return <LoadingScreen message="Загрузка панели управления..." />;
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Заголовок с приветствием */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 mb-2">
                🎲 Панель управления
              </h1>
              <p className="text-gray-600">
                Добро пожаловать, {user?.full_name || 'Пользователь'}!
                Выбранная лотерея: <span className="font-medium">{LOTTERY_CONFIGS[selectedLottery].name}</span>
              </p>
            </div>

            {/* Статус подписки */}
            <div className="hidden sm:flex items-center space-x-4">
              <div className={cn(
                'px-4 py-2 rounded-full text-sm font-medium',
                user?.subscription_status === 'active'
                  ? 'bg-green-100 text-green-800'
                  : 'bg-gray-100 text-gray-800'
              )}>
                {user?.subscription_status === 'active'
                  ? `🌟 ${user.preferences?.subscription_plan || 'Premium'}`
                  : '🆓 Базовый план'
                }
              </div>

              {user?.subscription_status !== 'active' && (
                <Button
                  onClick={handleUpgradeSubscription}
                  size="sm"
                  variant="primary"
                >
                  💎 Улучшить план
                </Button>
              )}
            </div>
          </div>
        </div>

        {/* Основной контент */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Левый блок - статистика */}
          <div className="lg:col-span-2 space-y-8">
            {/* Карточки статистики */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {statsLoading ? (
                <>
                  <StatsCardSkeleton />
                  <StatsCardSkeleton />
                  <StatsCardSkeleton />
                  <StatsCardSkeleton />
                </>
              ) : (
                <>
                  <StatsCard
                    title="Генераций сегодня"
                    value={stats?.generations_today || 0}
                    icon="🚀"
                    color="blue"
                    description="Комбинаций создано"
                    onClick={() => navigate(ROUTES.GENERATION)}
                  />

                  <StatsCard
                    title="Анализов трендов"
                    value={stats?.trend_analyses || 0}
                    icon="📊"
                    color="green"
                    description="Обновлений за день"
                    onClick={() => navigate(ROUTES.TRENDS)}
                  />

                  <StatsCard
                    title="Точность прогнозов"
                    value={`${stats?.accuracy_percentage || 0}%`}
                    icon="🎯"
                    color="purple"
                    trend={{
                      value: 2.3,
                      direction: 'up',
                      label: '%'
                    }}
                    description="За последние 30 дней"
                  />

                  <StatsCard
                    title="Лучшая оценка RF"
                    value={stats?.best_score || 'N/A'}
                    icon="🏆"
                    color="yellow"
                    description="Максимальная оценка"
                  />
                </>
              )}
            </div>

            {/* Быстрые действия */}
            <div className="card">
              <div className="card-header">
                <h2 className="text-xl font-semibold text-gray-900">
                  ⚡ Быстрые действия
                </h2>
              </div>
              <div className="card-body">
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  <Button
                    onClick={handleQuickGeneration}
                    variant="primary"
                    size="lg"
                    fullWidth
                    icon="🎲"
                  >
                    Генерация
                  </Button>

                  <Button
                    onClick={handleViewTrends}
                    variant="secondary"
                    size="lg"
                    fullWidth
                    icon="📊"
                  >
                    Тренды
                  </Button>

                  <Button
                    onClick={() => navigate(ROUTES.HISTORY)}
                    variant="secondary"
                    size="lg"
                    fullWidth
                    icon="📚"
                  >
                    История
                  </Button>
                </div>
              </div>
            </div>

            {/* Текущие тренды - превью */}
            {trends && (
              <div className="card">
                <div className="card-header flex items-center justify-between">
                  <h2 className="text-xl font-semibold text-gray-900">
                    🔥 Текущие тренды
                  </h2>
                  <Button
                    onClick={handleViewTrends}
                    variant="ghost"
                    size="sm"
                  >
                    Подробнее →
                  </Button>
                </div>
                <div className="card-body">
                  <div className="space-y-4">
                    {/* Поле 1 */}
                    <div>
                      <h3 className="text-sm font-medium text-gray-700 mb-2">
                        Поле 1 - Горячие числа:
                      </h3>
                      <div className="flex flex-wrap gap-2">
                        {trends.trends?.field1?.hot_acceleration?.slice(0, 5).map((num: number) => (
                          <span
                            key={num}
                            className="lottery-number-hot"
                          >
                            {num}
                          </span>
                        )) || <span className="text-gray-500">Нет данных</span>}
                      </div>
                    </div>

                    {/* Поле 2 */}
                    <div>
                      <h3 className="text-sm font-medium text-gray-700 mb-2">
                        Поле 2 - Горячие числа:
                      </h3>
                      <div className="flex flex-wrap gap-2">
                        {trends.trends?.field2?.hot_acceleration?.slice(0, 5).map((num: number) => (
                          <span
                            key={num}
                            className="lottery-number-hot"
                          >
                            {num}
                          </span>
                        )) || <span className="text-gray-500">Нет данных</span>}
                      </div>
                    </div>

                    {/* Рекомендации */}
                    {trends.recommendations && trends.recommendations.length > 0 && (
                      <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                        <h4 className="text-sm font-semibold text-blue-800 mb-2">
                          💡 Рекомендации:
                        </h4>
                        <ul className="text-sm text-blue-700 space-y-1">
                          {trends.recommendations.slice(0, 3).map((rec: string, index: number) => (
                            <li key={index}>• {rec}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Правый блок - активность и информация */}
          <div className="space-y-6">
            {/* Недавняя активность */}
            <div className="card">
              <div className="card-header">
                <h2 className="text-lg font-semibold text-gray-900">
                  📋 Недавняя активность
                </h2>
              </div>
              <div className="card-body">
                {stats?.recent_activities?.length > 0 ? (
                  <div className="space-y-3">
                    {stats.recent_activities.slice(0, 5).map((activity: any, index: number) => (
                      <div key={index} className="flex items-center space-x-3 p-2 hover:bg-gray-50 rounded">
                        <span className="text-lg">
                          {activity.type === 'generation' ? '🎲' :
                           activity.type === 'analysis' ? '📊' : '🔍'}
                        </span>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-gray-900 truncate">
                            {activity.description}
                          </p>
                          <p className="text-xs text-gray-500">
                            {new Date(activity.timestamp).toLocaleTimeString('ru-RU')}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-6 text-gray-500">
                    <span className="text-3xl block mb-2">📊</span>
                    <p className="text-sm">Пока нет активности</p>
                    <p className="text-xs mt-1">Начните с генерации комбинаций</p>
                  </div>
                )}
              </div>
            </div>

            {/* Информация о системе */}
            <div className="card">
              <div className="card-header">
                <h2 className="text-lg font-semibold text-gray-900">
                  ⚡ Статус системы
                </h2>
              </div>
              <div className="card-body space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">RF модель</span>
                  <span className="text-sm font-medium text-green-600">✅ Готова</span>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">Анализ трендов</span>
                  <span className="text-sm font-medium text-green-600">
                    {trendsLoading ? '⏳ Обновление...' : '✅ Актуальны'}
                  </span>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">База данных</span>
                  <span className="text-sm font-medium text-green-600">✅ Онлайн</span>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">Тиражей загружено</span>
                  <span className="text-sm font-medium text-blue-600">
                    {trends?.analyzed_draws || 'N/A'}
                  </span>
                </div>
              </div>
            </div>

            {/* Подсказки для новых пользователей */}
            {(!stats?.total_generations || stats.total_generations < 5) && (
              <div className="card border-blue-200 bg-blue-50">
                <div className="card-body">
                  <h3 className="text-lg font-semibold text-blue-800 mb-3">
                    🎯 Начните с этого:
                  </h3>

                  <div className="space-y-3">
                    <div className="flex items-center space-x-3">
                      <span className="w-6 h-6 bg-blue-600 text-white rounded-full text-xs flex items-center justify-center">1</span>
                      <span className="text-sm text-blue-700">Изучите текущие тренды</span>
                    </div>

                    <div className="flex items-center space-x-3">
                      <span className="w-6 h-6 bg-blue-600 text-white rounded-full text-xs flex items-center justify-center">2</span>
                      <span className="text-sm text-blue-700">Сгенерируйте первые комбинации</span>
                    </div>

                    <div className="flex items-center space-x-3">
                      <span className="w-6 h-6 bg-blue-600 text-white rounded-full text-xs flex items-center justify-center">3</span>
                      <span className="text-sm text-blue-700">Оцените результаты</span>
                    </div>
                  </div>

                  <Button
                    onClick={handleQuickGeneration}
                    variant="primary"
                    size="sm"
                    fullWidth
                    className="mt-4"
                  >
                    🚀 Начать сейчас
                  </Button>
                </div>
              </div>
            )}

            {/* Реклама подписки для базовых пользователей */}
            {user?.subscription_status !== 'active' && (
              <div className="card border-purple-200 bg-gradient-to-br from-purple-50 to-pink-50">
                <div className="card-body text-center">
                  <div className="text-4xl mb-3">🌟</div>
                  <h3 className="text-lg font-semibold text-purple-800 mb-2">
                    Откройте все возможности
                  </h3>
                  <p className="text-sm text-purple-700 mb-4">
                    Премиум подписка даст доступ к расширенной аналитике, симуляциям и безлимитным генерациям
                  </p>

                  <div className="space-y-2 text-xs text-purple-600 mb-4">
                    <div>✅ 100+ генераций в день</div>
                    <div>✅ Кластерный анализ</div>
                    <div>✅ Симуляция стратегий</div>
                    <div>✅ Приоритетная поддержка</div>
                  </div>

                  <Button
                    onClick={handleUpgradeSubscription}
                    variant="primary"
                    size="sm"
                    fullWidth
                  >
                    💎 Улучшить до Premium
                  </Button>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Нижний блок - краткий обзор трендов */}
        {trends && (
          <div className="mt-8 card">
            <div className="card-header flex items-center justify-between">
              <h2 className="text-xl font-semibold text-gray-900">
                📈 Краткий обзор трендов
              </h2>
              <span className="text-sm text-gray-500">
                Обновлено: {new Date(trends.timestamp).toLocaleTimeString('ru-RU')}
              </span>
            </div>
            <div className="card-body">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Поле 1 */}
                <div>
                  <h3 className="text-lg font-medium text-gray-900 mb-3">
                    🎯 Поле 1
                  </h3>

                  <div className="space-y-3">
                    <div>
                      <p className="text-sm text-gray-600 mb-1">Горячие числа:</p>
                      <div className="flex flex-wrap gap-1">
                        {trends.trends?.field1?.hot_acceleration?.slice(0, 3).map((num: number) => (
                          <span key={num} className="lottery-number-hot text-xs">
                            {num}
                          </span>
                        ))}
                      </div>
                    </div>

                    <div>
                      <p className="text-sm text-gray-600 mb-1">Готовые к выходу:</p>
                      <div className="flex flex-wrap gap-1">
                        {trends.trends?.field1?.cold_reversal?.slice(0, 3).map((num: number) => (
                          <span key={num} className="lottery-number-cold text-xs">
                            {num}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Поле 2 */}
                <div>
                  <h3 className="text-lg font-medium text-gray-900 mb-3">
                    🎯 Поле 2
                  </h3>

                  <div className="space-y-3">
                    <div>
                      <p className="text-sm text-gray-600 mb-1">Горячие числа:</p>
                      <div className="flex flex-wrap gap-1">
                        {trends.trends?.field2?.hot_acceleration?.slice(0, 3).map((num: number) => (
                          <span key={num} className="lottery-number-hot text-xs">
                            {num}
                          </span>
                        ))}
                      </div>
                    </div>

                    <div>
                      <p className="text-sm text-gray-600 mb-1">Готовые к выходу:</p>
                      <div className="flex flex-wrap gap-1">
                        {trends.trends?.field2?.cold_reversal?.slice(0, 3).map((num: number) => (
                          <span key={num} className="lottery-number-cold text-xs">
                            {num}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Общая сводка */}
              {trends.summary && (
                <div className="mt-6 p-4 bg-gray-50 rounded-lg border border-gray-200">
                  <p className="text-sm text-gray-700">
                    <span className="font-medium">Сводка:</span> {trends.summary}
                  </p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};