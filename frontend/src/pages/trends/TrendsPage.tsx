import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useSelectedLottery, useAppActions } from '../../store';
import { QUERY_KEYS, LOTTERY_CONFIGS, TREND_COLORS } from '../../constants';
import { lotteryService } from '../../services/lotteryService';
import { Button, SecondaryButton } from '../../components/common/Button';
import { LotteryNumbers } from '../../components/common/LotteryNumbers';
import { StatsCard } from '../../components/common/StatsCard';
import { LoadingScreen, LoadingSpinner } from '../../components/common/LoadingScreen';
import { ApiErrorDisplay } from '../../components/common/ErrorBoundary';
import { formatDateTime } from '../../utils';
import { cn } from '../../utils';

export const TrendsPage: React.FC = () => {
  const selectedLottery = useSelectedLottery();
  const { setSelectedLottery } = useAppActions();

  const [refreshKey, setRefreshKey] = useState(0);
  const [autoRefresh, setAutoRefresh] = useState(true);

  // Загрузка трендов
  const {
    data: trends,
    isLoading,
    error,
    refetch,
    dataUpdatedAt
  } = useQuery({
    queryKey: [...QUERY_KEYS.lottery.trends(selectedLottery), refreshKey],
    queryFn: () => lotteryService.getTrends(selectedLottery),
    staleTime: 30 * 1000, // 30 секунд
    refetchInterval: autoRefresh ? 60 * 1000 : false, // Автообновление каждую минуту
    retry: 3,
  });

  // Загрузка истории для дополнительного анализа
  const { data: history } = useQuery({
    queryKey: QUERY_KEYS.lottery.history(selectedLottery, 1, 50),
    queryFn: () => lotteryService.getDrawHistory(selectedLottery, { limit: 50 }),
    staleTime: 5 * 60 * 1000, // 5 минут
  });

  const handleRefresh = () => {
    setRefreshKey(prev => prev + 1);
    refetch();
  };

  const handleAutoRefreshToggle = () => {
    setAutoRefresh(!autoRefresh);
  };

  if (isLoading && !trends) {
    return <LoadingScreen message="Анализируем текущие тренды..." />;
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
                📊 Анализ трендов
              </h1>
              <p className="text-gray-600">
                Актуальные паттерны и тенденции для {LOTTERY_CONFIGS[selectedLottery].name}
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

              {/* Автообновление */}
              <label className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  checked={autoRefresh}
                  onChange={handleAutoRefreshToggle}
                  className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                />
                <span className="text-sm text-gray-700">Авто</span>
              </label>

              {/* Кнопка обновления */}
              <Button
                onClick={handleRefresh}
                variant="secondary"
                size="sm"
                loading={isLoading}
                icon={isLoading ? undefined : "🔄"}
              >
                Обновить
              </Button>
            </div>
          </div>

          {/* Время последнего обновления */}
          {dataUpdatedAt && (
            <div className="mt-4 text-sm text-gray-500">
              Последнее обновление: {formatDateTime(new Date(dataUpdatedAt))}
              {trends?.timestamp && (
                <span className="ml-4">
                  Данные сервера: {formatDateTime(trends.timestamp)}
                </span>
              )}
            </div>
          )}
        </div>

        {trends && (
          <div className="space-y-8">
            {/* Статистика трендов */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <StatsCard
                title="Проанализировано тиражей"
                value={trends.analyzed_draws}
                icon="📈"
                color="blue"
                description="Историческая база"
              />

              <StatsCard
                title="Сила тренда П1"
                value={`${(trends.trends?.field1?.trend_strength * 100 || 0).toFixed(1)}%`}
                icon="🔥"
                color="red"
                description={`Паттерн: ${trends.trends?.field1?.pattern_shift || 'stable'}`}
              />

              <StatsCard
                title="Сила тренда П2"
                value={`${(trends.trends?.field2?.trend_strength * 100 || 0).toFixed(1)}%`}
                icon="❄️"
                color="blue"
                description={`Паттерн: ${trends.trends?.field2?.pattern_shift || 'stable'}`}
              />
            </div>

            {/* Основной анализ трендов */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              {/* Поле 1 */}
              <TrendFieldAnalysis
                fieldName="Поле 1"
                fieldData={trends.trends?.field1}
                fieldNumber={1}
                maxNumber={LOTTERY_CONFIGS[selectedLottery].field1_max}
              />

              {/* Поле 2 */}
              <TrendFieldAnalysis
                fieldName="Поле 2"
                fieldData={trends.trends?.field2}
                fieldNumber={2}
                maxNumber={LOTTERY_CONFIGS[selectedLottery].field2_max}
              />
            </div>

            {/* Общие рекомендации */}
            {trends.recommendations && trends.recommendations.length > 0 && (
              <div className="card">
                <div className="card-header">
                  <h2 className="text-xl font-semibold text-gray-900">
                    💡 Рекомендации на основе трендов
                  </h2>
                </div>
                <div className="card-body">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {trends.recommendations.map((recommendation, index) => (
                      <div
                        key={index}
                        className="flex items-start space-x-3 p-3 bg-blue-50 border border-blue-200 rounded-lg"
                      >
                        <span className="text-blue-600 mt-0.5">💡</span>
                        <p className="text-sm text-blue-800">{recommendation}</p>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Сводка трендов */}
            {trends.summary && (
              <div className="card">
                <div className="card-header">
                  <h2 className="text-xl font-semibold text-gray-900">
                    📋 Сводка анализа
                  </h2>
                </div>
                <div className="card-body">
                  <div className="p-4 bg-gradient-to-r from-gray-50 to-blue-50 border border-gray-200 rounded-lg">
                    <p className="text-gray-700 leading-relaxed">
                      {trends.summary}
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

// Компонент анализа для отдельного поля
interface TrendFieldAnalysisProps {
  fieldName: string;
  fieldData: any;
  fieldNumber: number;
  maxNumber: number;
}

const TrendFieldAnalysis: React.FC<TrendFieldAnalysisProps> = ({
  fieldName,
  fieldData,
  fieldNumber,
  maxNumber,
}) => {
  if (!fieldData) {
    return (
      <div className="card">
        <div className="card-header">
          <h2 className="text-xl font-semibold text-gray-900">{fieldName}</h2>
        </div>
        <div className="card-body text-center py-8 text-gray-500">
          <span className="text-4xl block mb-2">📊</span>
          <p>Нет данных для анализа</p>
        </div>
      </div>
    );
  }

  return (
    <div className="card">
      <div className="card-header">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-gray-900">
            🎯 {fieldName}
          </h2>
          <div className="flex items-center space-x-2 text-sm">
            <span className="text-gray-600">Уверенность:</span>
            <span className={cn(
              'font-medium px-2 py-1 rounded',
              fieldData.confidence_score > 0.7 ? 'bg-green-100 text-green-700' :
              fieldData.confidence_score > 0.5 ? 'bg-yellow-100 text-yellow-700' :
              'bg-red-100 text-red-700'
            )}>
              {(fieldData.confidence_score * 100).toFixed(0)}%
            </span>
          </div>
        </div>
      </div>

      <div className="card-body space-y-6">
        {/* Горячие числа */}
        <div>
          <h3 className="text-lg font-medium text-gray-900 mb-3 flex items-center">
            🔥 Горячие числа
            <span className="ml-2 text-sm text-gray-500">
              (ускоряющиеся)
            </span>
          </h3>
          {fieldData.hot_acceleration?.length > 0 ? (
            <LotteryNumbers
              numbers={fieldData.hot_acceleration}
              variant="hot"
              size="md"
            />
          ) : (
            <p className="text-gray-500 text-sm">Нет выраженных горячих чисел</p>
          )}
        </div>

        {/* Холодные числа */}
        <div>
          <h3 className="text-lg font-medium text-gray-900 mb-3 flex items-center">
            ❄️ Готовые к выходу
            <span className="ml-2 text-sm text-gray-500">
              (холодные)
            </span>
          </h3>
          {fieldData.cold_reversal?.length > 0 ? (
            <LotteryNumbers
              numbers={fieldData.cold_reversal}
              variant="cold"
              size="md"
            />
          ) : (
            <p className="text-gray-500 text-sm">Нет выраженных холодных чисел</p>
          )}
        </div>

        {/* Числа с импульсом */}
        <div>
          <h3 className="text-lg font-medium text-gray-900 mb-3 flex items-center">
            ⚡ Импульсные числа
            <span className="ml-2 text-sm text-gray-500">
              (с ускорением)
            </span>
          </h3>
          {fieldData.momentum_numbers?.length > 0 ? (
            <LotteryNumbers
              numbers={fieldData.momentum_numbers}
              variant="neutral"
              size="md"
            />
          ) : (
            <p className="text-gray-500 text-sm">Нет чисел с выраженным импульсом</p>
          )}
        </div>

        {/* Метрики поля */}
        <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
          <h4 className="text-sm font-semibold text-gray-700 mb-3">
            📈 Метрики поля
          </h4>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <span className="text-xs text-gray-600">Сдвиг паттерна:</span>
              <div className={cn(
                'text-sm font-medium mt-1 px-2 py-1 rounded text-center',
                fieldData.pattern_shift === 'ascending' ? 'bg-green-100 text-green-700' :
                fieldData.pattern_shift === 'descending' ? 'bg-red-100 text-red-700' :
                'bg-gray-100 text-gray-700'
              )}>
                {fieldData.pattern_shift === 'ascending' && '📈 Восходящий'}
                {fieldData.pattern_shift === 'descending' && '📉 Нисходящий'}
                {fieldData.pattern_shift === 'stable' && '➡️ Стабильный'}
              </div>
            </div>

            <div>
              <span className="text-xs text-gray-600">Сила тренда:</span>
              <div className="mt-1">
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className={cn(
                      'h-2 rounded-full transition-all duration-500',
                      fieldData.trend_strength > 0.7 ? 'bg-red-500' :
                      fieldData.trend_strength > 0.5 ? 'bg-yellow-500' :
                      'bg-green-500'
                    )}
                    style={{ width: `${fieldData.trend_strength * 100}%` }}
                  />
                </div>
                <span className="text-xs text-gray-600 mt-1">
                  {(fieldData.trend_strength * 100).toFixed(1)}%
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// Компонент визуализации распределения чисел
const NumberDistributionChart: React.FC<{
  fieldData: any;
  maxNumber: number;
}> = ({ fieldData, maxNumber }) => {
  // Создаем карту частот для всех чисел
  const frequencyMap = new Map<number, number>();

  // Инициализируем все числа нулевой частотой
  for (let i = 1; i <= maxNumber; i++) {
    frequencyMap.set(i, 0);
  }

  // Устанавливаем частоты для горячих чисел
  fieldData.hot_acceleration?.forEach((num: number, index: number) => {
    frequencyMap.set(num, 100 - index * 10); // Убывающая частота
  });

  // Устанавливаем частоты для импульсных чисел
  fieldData.momentum_numbers?.forEach((num: number, index: number) => {
    const currentFreq = frequencyMap.get(num) || 0;
    frequencyMap.set(num, Math.max(currentFreq, 50 - index * 5));
  });

  return (
    <div className="mt-6">
      <h4 className="text-sm font-semibold text-gray-700 mb-3">
        📊 Распределение активности чисел
      </h4>

      <div className="grid grid-cols-5 sm:grid-cols-10 gap-1">
        {Array.from({ length: maxNumber }, (_, i) => i + 1).map(num => {
          const frequency = frequencyMap.get(num) || 0;
          const isHot = fieldData.hot_acceleration?.includes(num);
          const isCold = fieldData.cold_reversal?.includes(num);
          const hasMomentum = fieldData.momentum_numbers?.includes(num);

          return (
            <div
              key={num}
              className="relative group"
            >
              <div
                className={cn(
                  'w-8 h-12 rounded border-2 flex items-end justify-center text-xs font-medium transition-all duration-200',
                  isHot ? 'border-red-300 bg-red-100 text-red-800' :
                  isCold ? 'border-blue-300 bg-blue-100 text-blue-800' :
                  hasMomentum ? 'border-yellow-300 bg-yellow-100 text-yellow-800' :
                  'border-gray-300 bg-gray-100 text-gray-600'
                )}
              >
                {/* Полоска активности */}
                <div
                  className={cn(
                    'absolute bottom-0 left-0 right-0 rounded-b transition-all duration-500',
                    isHot ? 'bg-red-400' :
                    isCold ? 'bg-blue-400' :
                    hasMomentum ? 'bg-yellow-400' :
                    'bg-gray-300'
                  )}
                  style={{ height: `${Math.max(frequency, 5)}%` }}
                />

                {/* Число */}
                <span className="relative z-10 mb-1">{num}</span>
              </div>

              {/* Тултип */}
              <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-2 py-1 bg-gray-900 text-white text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-20">
                Число {num}
                {isHot && <div>🔥 Горячее</div>}
                {isCold && <div>❄️ Холодное</div>}
                {hasMomentum && <div>⚡ Импульс</div>}
              </div>
            </div>
          );
        })}
      </div>

      {/* Легенда */}
      <div className="flex items-center justify-center space-x-6 mt-4 text-xs">
        <div className="flex items-center space-x-1">
          <div className="w-3 h-3 bg-red-400 rounded" />
          <span className="text-gray-600">Горячие</span>
        </div>
        <div className="flex items-center space-x-1">
          <div className="w-3 h-3 bg-blue-400 rounded" />
          <span className="text-gray-600">Холодные</span>
        </div>
        <div className="flex items-center space-x-1">
          <div className="w-3 h-3 bg-yellow-400 rounded" />
          <span className="text-gray-600">Импульс</span>
        </div>
        <div className="flex items-center space-x-1">
          <div className="w-3 h-3 bg-gray-300 rounded" />
          <span className="text-gray-600">Нейтральные</span>
        </div>
      </div>
    </div>
  );
};