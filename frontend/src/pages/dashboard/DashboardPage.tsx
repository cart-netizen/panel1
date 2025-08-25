import React, {useEffect, useState} from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useUser, useSelectedLottery } from '../../store';
import { ROUTES, LOTTERY_CONFIGS, QUERY_KEYS } from '../../constants';
import { StatsCard, StatsCardSkeleton } from '../../components/common/StatsCard';
import { Button } from '../../components/common/Button';
import { LoadingScreen } from '../../components/common/LoadingScreen';
import { apiClient } from '../../services/api';
import { cn } from '../../utils';
import { CombinationDisplay } from '../../components/common/LotteryNumbers';
import { FrequencyChart } from '../../components/charts/FrequencyChart';
import { DrawsTable } from '../../components/tables/DrawsTable';
import { FavoriteNumbersModal } from '../../components/modals/FavoriteNumbersModal';
import { useNotificationActions } from '../../store';

// Интерфейс для статистики dashboard
// interface DashboardStats {
//   generations_today: number;
//   trend_analyses: number;
//   accuracy_percentage: {
//     value: number;
//     change: number;
//   };
//   best_score: number | string;
//   total_generations: number;
//   recent_activities: Array<{
//     type: string;
//     description: string;
//     timestamp: string;
//     lottery_type?: string;
//   }>;
// }

export const DashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const user = useUser();
  const selectedLottery = useSelectedLottery();

  // Загружаем статистику dashboard
  const { data: stats, isLoading: statsLoading, error: statsError } = useQuery({
    queryKey: QUERY_KEYS.dashboard.stats,
    queryFn: async () => {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${process.env.REACT_APP_API_URL}/dashboard/stats`, {
        headers: {
          'Authorization': token ? `Bearer ${token}` : '',
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      return response.json();
    },
    staleTime: 2 * 60 * 1000, // 2 минуты
    retry: 2,
  });

  // Загружаем текущие тренды
  const { data: trends, isLoading: trendsLoading } = useQuery({
    queryKey: QUERY_KEYS.lottery.trends(selectedLottery),
    queryFn: async () => {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${process.env.REACT_APP_API_URL}/dashboard/${selectedLottery}/trends`, {
        headers: {
          'Authorization': token ? `Bearer ${token}` : '',
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      return response.json();
    },
    staleTime: 30 * 1000, // 30 секунд
  });

  // Загружаем последний тираж
  const { data: latestDraw, isLoading: latestDrawLoading, error: latestDrawError } = useQuery({
    queryKey: QUERY_KEYS.lottery.latestDraw(selectedLottery),
    queryFn: async () => {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${process.env.REACT_APP_API_URL}/dashboard/${selectedLottery}/latest-draw`, {
        headers: {
          'Authorization': token ? `Bearer ${token}` : '',
          'Content-Type': 'application/json',
        },
      });

      const data = await response.json();

      // Обрабатываем случай, когда нет данных
      if (data.status === 'no_data' || !data.draw_number) {
        return null;
      }

      return data;
    },
    staleTime: 5 * 60 * 1000, // 5 минут
    retry: 1, // Только одна попытка
  });

  // Загружаем историю для графиков
  const { data: drawsHistory, isLoading: historyLoading } = useQuery({
    queryKey: ['draws-history', selectedLottery],
    queryFn: async () => {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${process.env.REACT_APP_API_URL}/${selectedLottery}/history?limit=300`, {
        headers: {
          'Authorization': token ? `Bearer ${token}` : '',
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        console.error('Failed to fetch history:', response.status);
        return [];
      }

      const data = await response.json();
      console.log('History data loaded:', data.length, 'draws');
      return data;
    },
    staleTime: 10 * 60 * 1000, // 10 минут
    retry: 1,
  });

  const safeStats = stats || {
  generations_today: 0,
  trend_analyses: 0,
  accuracy_percentage: { value: 0, change: 0 },
  best_score: 'N/A',
  total_generations: 0,
  recent_activities: []
  };


  const { showSuccess, showError } = useNotificationActions();
  const handleQuickGeneration = () => {
    navigate(ROUTES.GENERATION);
  };

  const handleViewTrends = () => {
    navigate(ROUTES.TRENDS);
  };

  const handleUpgradeSubscription = () => {
    navigate(ROUTES.SUBSCRIPTIONS);
  };

  const [showFavoriteNumbersModal, setShowFavoriteNumbersModal] = useState(false);
  const [favoriteNumbers, setFavoriteNumbers] = useState<{
    field1: number[];
    field2: number[];
  }>({
    field1: user?.preferences?.favorite_numbers?.field1 || [],
    field2: user?.preferences?.favorite_numbers?.field2 || []
  });


  useEffect(() => {
    const loadUserFavorites = async () => {
      try {
        const token = localStorage.getItem('access_token');
        const response = await fetch(`${process.env.REACT_APP_API_URL}/user/preferences?lottery_type=${selectedLottery}`, {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        });

        if (response.ok) {
          const data = await response.json();
          if (data.favorite_numbers) {
            setFavoriteNumbers(data.favorite_numbers);
          } else {
            setFavoriteNumbers({ field1: [], field2: [] });
          }
        }
      } catch (error) {
        console.error('Ошибка загрузки избранных чисел:', error);
        setFavoriteNumbers({ field1: [], field2: [] });
      }
    };

    if (user) {
      loadUserFavorites();
    }
  }, [user, selectedLottery]);

  // Функция подсчета общего количества избранных чисел
  const getTotalFavoriteNumbers = () => {
    const field1Count = favoriteNumbers.field1?.length || 0;
    const field2Count = favoriteNumbers.field2?.length || 0;
    return field1Count + field2Count;
  };

  // Обновляем функцию сохранения
  const handleSaveFavorites = async (numbers: { field1: number[], field2: number[] }) => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${process.env.REACT_APP_API_URL}/user/preferences`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          favorite_numbers: numbers,
          lottery_type: selectedLottery
        })
      });

      if (response.ok) {
        setFavoriteNumbers(numbers);
        showSuccess('Сохранено','Избранные числа сохранены');
        setShowFavoriteNumbersModal(false);
      } else {
        throw new Error('Ошибка сохранения');
      }
    } catch (error) {
      showError('Ошибка','Ошибка сохранения избранных чисел');
      console.error(error);
    }
  };

  // Обновляем функцию очистки
  const handleClearFavorites = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${process.env.REACT_APP_API_URL}/user/preferences/favorite-numbers?lottery_type=${selectedLottery}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
        }
      });

      if (response.ok) {
        setFavoriteNumbers({ field1: [], field2: [] });
        showSuccess('Очищено',`Избранные числа очищены для ${LOTTERY_CONFIGS[selectedLottery].name}`);
      }
    } catch (error) {
      console.error('Ошибка очистки избранных чисел:', error);
    }
  };

  const handleEvaluateCombination = () => {
  // Переход на страницу генерации с параметрами оценки
  navigate(ROUTES.GENERATION, {
    state: {
      mode: 'evaluate',
      favoriteNumbers: favoriteNumbers
    }
  });
};

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
                    value={safeStats.generations_today || 0}
                    icon="🚀"
                    color="blue"
                    description="Комбинаций создано"
                    onClick={() => navigate(ROUTES.GENERATION)}
                  />

                  <StatsCard
                    title="Избранные числа"
                    value={(user?.preferences?.favorite_numbers?.field1?.length || 0 ) +
                           (user?.preferences?.favorite_numbers?.field2?.length || getTotalFavoriteNumbers())}

                    icon="⭐"
                    color="green"
                    description="Числа для генерации"
                    onClick={() => setShowFavoriteNumbersModal(true)}
                    actionButton={
                      (favoriteNumbers.field1.length > 0 || favoriteNumbers.field2.length > 0) ? (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleClearFavorites();
                          }}
                          className="px-2 py-1 text-xs bg-gray-100 hover:bg-gray-200 text-gray-600 rounded transition-colors"
                        >
                          Очистить
                        </button>
                      ) : null
                    }
                  />
                  {/* График частоты выпадения чисел - занимает всю ширину */}
                  <div className="lg:col-span-2">
                    {historyLoading ? (
                      <div className="card">
                        <div className="card-body text-center">
                          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary-500"></div>
                          <p className="mt-2 text-gray-500">Загрузка данных...</p>
                        </div>
                      </div>
                    ) : drawsHistory && drawsHistory.length > 0 ? (
                      <>
                        <FrequencyChart
                          data={drawsHistory}
                          lotteryType={selectedLottery}
                          maxNumbers={{
                            field1: LOTTERY_CONFIGS[selectedLottery].field1_max,
                            field2: LOTTERY_CONFIGS[selectedLottery].field2_max
                          }}
                        />

                        {/* Таблица выпавших номеров под графиком */}
                        <div className="mt-6">
                          <DrawsTable
                            draws={drawsHistory}
                            maxNumbers={{
                              field1: LOTTERY_CONFIGS[selectedLottery].field1_max,
                              field2: LOTTERY_CONFIGS[selectedLottery].field2_max
                            }}
                          />
                        </div>
                      </>
                    ) : (
                      <div className="card">
                        <div className="card-body text-center text-gray-500">
                          <p>Нет данных истории тиражей</p>
                          <Button
                            // onClick={() => navigate(ROUTES.DATA_MANAGEMENT)}
                            variant="primary"
                            size="sm"
                            className="mt-4"
                          >
                            Загрузить данные
                          </Button>
                        </div>
                      </div>
                    )}
                  </div>



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
            {/* Подсказки для новых пользователей */}
            {(!safeStats.total_generations || safeStats.total_generations < 5) && (
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

            {/* Недавняя активность */}
            <div className="card">
              <div className="card-header">
                <h2 className="text-lg font-semibold text-gray-900">
                  📋 Недавняя активность
                </h2>
              </div>
              <div className="card-body">
                {safeStats.recent_activities && safeStats.recent_activities.length > 0 ? (
                    <div className="space-y-3">
                      {safeStats.recent_activities.slice(0, 5).map((activity: any, index: number) => (
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
                    <div className="text-center py-8 text-gray-500">
                      <span className="text-2xl block mb-2">📝</span>
                      <p>Пока нет активности</p>
                      <p className="text-sm">Начните с создания комбинаций</p>
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

                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-2">Последний тираж</h4>
                  {latestDrawLoading ? (
                      <div className="flex items-center space-x-2">
                        <div
                            className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
                        <span className="text-sm text-gray-500">Загрузка...</span>
                      </div>
                  ) : latestDraw && latestDraw.draw_number > 0 ? (
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="text-sm text-gray-600">Номер тиража</span>
                          <span className="text-sm font-medium text-gray-900">#{latestDraw.draw_number}</span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-sm text-gray-600">Дата</span>
                          <span className="text-sm font-medium text-gray-900">
            {new Date(latestDraw.draw_date).toLocaleDateString('ru-RU')}
          </span>
                        </div>
                      </div>
                  ) : (
                      <div className="space-y-2">
                        <div className="text-sm text-amber-600">
                          База данных пуста
                        </div>
                        <div className="text-xs text-gray-500">
                          Необходимо загрузить данные тиражей
                        </div>
                      </div>
                  )}
                </div>

                {/* Комбинация последнего тиража */}
                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-2">Комбинация последнего тиража</h4>
                  {latestDrawLoading ? (
                      <div className="flex items-center space-x-2">
                        <div
                            className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
                        <span className="text-sm text-gray-500">Загрузка...</span>
                      </div>
                  ) : latestDraw ? (
                      <div className="space-y-2">
                        <CombinationDisplay
                            field1={latestDraw.field1_numbers}
                            field2={latestDraw.field2_numbers}
                            size="sm"
                            showLabels={true}
                        />
                      </div>
                  ) : (
                      <div className="text-sm text-red-600">Нет данных</div>
                  )}
                </div>
              </div>
            </div>

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
      {/* Модальное окно избранных чисел */}
      {showFavoriteNumbersModal && (
        <FavoriteNumbersModal
          isOpen={showFavoriteNumbersModal}
          onClose={() => setShowFavoriteNumbersModal(false)}
          onSave={handleSaveFavorites}
          lotteryType={selectedLottery}
          initialNumbers={favoriteNumbers}
        />
      )}
    </div>
  );
};