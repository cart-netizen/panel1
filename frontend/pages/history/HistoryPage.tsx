import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useSelectedLottery, useAppActions } from '../../store';
import { QUERY_KEYS, LOTTERY_CONFIGS } from '../../constants';
import { lotteryService } from '../../services/lotteryService';
import { Button, SecondaryButton } from '../../components/common/Button';
import { CombinationDisplay } from '../../components/common/LotteryNumbers';
import { LoadingScreen, LoadingSpinner } from '../../components/common/LoadingScreen';
import { ApiErrorDisplay } from '../../components/common/ErrorBoundary';
import { formatDate, formatDateTime } from '../../utils';
import { cn } from '../../utils';

export const HistoryPage: React.FC = () => {
  const selectedLottery = useSelectedLottery();
  const { setSelectedLottery } = useAppActions();

  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage] = useState(20);

  // Загрузка истории тиражей
  const {
    data: history,
    isLoading,
    error,
    refetch
  } = useQuery({
    queryKey: QUERY_KEYS.lottery.history(selectedLottery, currentPage, itemsPerPage),
    queryFn: () => lotteryService.getDrawHistory(selectedLottery, {
      page: currentPage,
      limit: itemsPerPage,
    }),
    staleTime: 5 * 60 * 1000, // 5 минут
  });

  const handleRefresh = () => {
    refetch();
  };

  if (isLoading && !history) {
    return <LoadingScreen message="Загружаем историю тиражей..." />;
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <ApiErrorDisplay error={error} onRetry={handleRefresh} />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Заголовок */}
        <div className="mb-8">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 mb-2">
                📚 История тиражей
              </h1>
              <p className="text-gray-600">
                Архив розыгрышей {LOTTERY_CONFIGS[selectedLottery].name}
              </p>
            </div>

            <div className="flex items-center space-x-4">
              {/* Селектор лотереи */}
              <select
                value={selectedLottery}
                onChange={(e) => setSelectedLottery(e.target.value as any)}
                className="input-field w-auto min-w-[200px]"
              >
                {Object.entries(LOTTERY_CONFIGS).map(([key, config]) => (
                  <option key={key} value={key}>
                    {config.name}
                  </option>
                ))}
              </select>

              {/* Кнопка обновления */}
              <Button
                onClick={handleRefresh}
                variant="secondary"
                size="sm"
                loading={isLoading}
                icon="🔄"
              >
                Обновить
              </Button>
            </div>
          </div>
        </div>

        {/* Статистика */}
        {history && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
            <div className="bg-white rounded-lg p-4 border border-gray-200">
              <div className="flex items-center space-x-3">
                <span className="text-2xl">📊</span>
                <div>
                  <p className="text-lg font-semibold text-gray-900">
                    {history.total_count || 0}
                  </p>
                  <p className="text-sm text-gray-600">Всего тиражей</p>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg p-4 border border-gray-200">
              <div className="flex items-center space-x-3">
                <span className="text-2xl">📅</span>
                <div>
                  <p className="text-lg font-semibold text-gray-900">
                    {currentPage}
                  </p>
                  <p className="text-sm text-gray-600">Текущая страница</p>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg p-4 border border-gray-200">
              <div className="flex items-center space-x-3">
                <span className="text-2xl">🔢</span>
                <div>
                  <p className="text-lg font-semibold text-gray-900">
                    {itemsPerPage}
                  </p>
                  <p className="text-sm text-gray-600">На странице</p>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg p-4 border border-gray-200">
              <div className="flex items-center space-x-3">
                <span className="text-2xl">📈</span>
                <div>
                  <p className="text-lg font-semibold text-gray-900">
                    {Math.ceil((history.total_count || 0) / itemsPerPage)}
                  </p>
                  <p className="text-sm text-gray-600">Всего страниц</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Таблица истории */}
        <div className="card">
          <div className="card-header">
            <h2 className="text-xl font-semibold text-gray-900">
              🎲 Список тиражей
            </h2>
          </div>

          <div className="card-body p-0">
            {history?.draws && history.draws.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50 border-b border-gray-200">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        № Тиража
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Дата розыгрыша
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Выигрышные числа
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Действия
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {history.draws.map((draw, index) => (
                      <tr key={draw.draw_number || index} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm font-medium text-gray-900">
                            #{draw.draw_number || 'N/A'}
                          </div>
                        </td>

                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm text-gray-900">
                            {formatDate(draw.draw_date)}
                          </div>
                          <div className="text-xs text-gray-500">
                            {new Date(draw.draw_date).toLocaleTimeString('ru-RU', {
                              hour: '2-digit',
                              minute: '2-digit'
                            })}
                          </div>
                        </td>

                        <td className="px-6 py-4">
                          <CombinationDisplay
                            field1={draw.field1_numbers}
                            field2={draw.field2_numbers}
                            size="sm"
                            showLabels={false}
                          />
                        </td>

                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                          <div className="flex items-center space-x-2">
                            <SecondaryButton
                              size="sm"
                              icon="📊"
                              onClick={() => console.log('Анализ тиража:', draw)}
                            >
                              Анализ
                            </SecondaryButton>

                            <SecondaryButton
                              size="sm"
                              icon="🔍"
                              onClick={() => console.log('Детали тиража:', draw)}
                            >
                              Детали
                            </SecondaryButton>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="text-center py-12">
                <div className="text-6xl mb-4">📚</div>
                <h3 className="text-lg font-medium text-gray-900 mb-2">
                  История тиражей пуста
                </h3>
                <p className="text-gray-600 mb-4">
                  Данные тиражей еще не загружены или отсутствуют
                </p>
                <Button
                  onClick={handleRefresh}
                  icon="🔄"
                >
                  Попробовать загрузить
                </Button>
              </div>
            )}
          </div>

          {/* Пагинация */}
          {history && history.total_count > itemsPerPage && (
            <div className="card-body border-t border-gray-200">
              <div className="flex items-center justify-between">
                <div className="text-sm text-gray-700">
                  Показано {((currentPage - 1) * itemsPerPage) + 1} - {Math.min(currentPage * itemsPerPage, history.total_count)} из {history.total_count} тиражей
                </div>

                <div className="flex items-center space-x-2">
                  <Button
                    onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                    disabled={currentPage === 1}
                    variant="secondary"
                    size="sm"
                  >
                    ← Назад
                  </Button>

                  <span className="text-sm text-gray-700 px-3">
                    Страница {currentPage} из {Math.ceil((history.total_count || 0) / itemsPerPage)}
                  </span>

                  <Button
                    onClick={() => setCurrentPage(prev => prev + 1)}
                    disabled={currentPage >= Math.ceil((history.total_count || 0) / itemsPerPage)}
                    variant="secondary"
                    size="sm"
                  >
                    Вперед →
                  </Button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};