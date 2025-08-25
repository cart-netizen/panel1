import React, { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../../services/api';
import { useSelectedLottery, useNotificationActions } from '../../../store';
import { Button } from '../../common/Button';
import { LoadingScreen } from '../../common/LoadingScreen';
import { cn } from '../../../utils';

// Компоненты графиков
import FrequencyHeatmap from './FrequencyHeatmap';
import TrendAnalysisCharts from './TrendAnalysisCharts';
import CorrelationCharts from './CorrelationCharts';
import ReadinessAnalysis from './ReadinessAnalysis';
import FavoritesRadar from './FavoritesRadar';

// Иконки
import { BarChart3, TrendingUp, Network, Zap, Target, RefreshCw } from 'lucide-react';

// Интерфейсы данных (адаптированы под API проекта)
interface PatternData {
  hot_cold: {
    field1: { hot: number[], cold: number[] },
    field2: { hot: number[], cold: number[] }
  };
  correlations: {
    field1: Array<{ pair: string, frequency_percent: number, count: number }>,
    field2: Array<{ pair: string, frequency_percent: number, count: number }>
  };
  favorites_analysis?: {
    field1: { [key: string]: { frequency: number, percentage: number } },
    field2: { [key: string]: { frequency: number, percentage: number } }
  };
  // Дополнительные данные из API
  cycles_field1?: Array<{ number: number, last_seen_ago: number, avg_cycle: number, is_overdue: boolean }>;
  cycles_field2?: Array<{ number: number, last_seen_ago: number, avg_cycle: number, is_overdue: boolean }>;
}

const PatternVisualizations: React.FC = () => {
  const selectedLottery = useSelectedLottery();
  const { showSuccess, showError } = useNotificationActions();
  const [activeChart, setActiveChart] = useState<string>('heatmap');

  // Загрузка данных паттернов из API
  const { data: patternData, isLoading, error, refetch } = useQuery({
    queryKey: ['patterns', selectedLottery],
    queryFn: async () => {
      const response = await apiClient.get(`/${selectedLottery}/patterns?window=30&top_n=10`);

      // ОТЛАДКА - показать исходные данные
      console.log('🔍 Исходные данные API:', {
        hot_cold: response.data.hot_cold,
        correlations_field1: response.data.correlations_field1,
        correlations_field2: response.data.correlations_field2,
        cycles_field1: response.data.cycles_field1?.slice(0, 3),
        cycles_field2: response.data.cycles_field2?.slice(0, 3)
      });

      // Адаптируем данные под интерфейс PatternData
      const adaptedData: PatternData = {
      hot_cold: {
        field1: {
          // Исправляем парсинг - данные могут приходить в разных форматах
          hot: (response.data.hot_cold?.field1?.hot || []).map((item: any) => {
            // Если это число - просто округляем
            if (typeof item === 'number') return Math.round(item);

            // Если это массив [число, частота] - берем первый элемент
            if (Array.isArray(item)) return Math.round(item[0]);

            // Если это строка "18,33.33333333333333" - берем часть до запятой
            if (typeof item === 'string') {
              const num = parseInt(item.split(',')[0]);
              return isNaN(num) ? 0 : num;
            }

            return 0;
          }).filter((num: number) => num > 0 && num <= 36), // Фильтруем валидные числа

          cold: (response.data.hot_cold?.field1?.cold || []).map((item: any) => {
            if (typeof item === 'number') return Math.round(item);
            if (Array.isArray(item)) return Math.round(item[0]);
            if (typeof item === 'string') {
              const num = parseInt(item.split(',')[0]);
              return isNaN(num) ? 0 : num;
            }
            return 0;
          }).filter((num: number) => num > 0 && num <= 36)
        },

        field2: {
          hot: (response.data.hot_cold?.field2?.hot || []).map((item: any) => {
            if (typeof item === 'number') return Math.round(item);
            if (Array.isArray(item)) return Math.round(item[0]);
            if (typeof item === 'string') {
              const num = parseInt(item.split(',')[0]);
              return isNaN(num) ? 0 : num;
            }
            return 0;
          }).filter((num: number) => num > 0 && num <= 12),

          cold: (response.data.hot_cold?.field2?.cold || []).map((item: any) => {
            if (typeof item === 'number') return Math.round(item);
            if (Array.isArray(item)) return Math.round(item[0]);
            if (typeof item === 'string') {
              const num = parseInt(item.split(',')[0]);
              return isNaN(num) ? 0 : num;
            }
            return 0;
          }).filter((num: number) => num > 0 && num <= 12)
        }
      },

      // Исправляем корреляции с округлением
      correlations: {
        field1: (response.data.correlations_field1 || []).map((item: any) => ({
          pair: item.pair || `${Math.round(Math.random() * 36)}-${Math.round(Math.random() * 36)}`,
          frequency_percent: Math.round((item.frequency_percent || 0) * 10) / 10,
          count: Math.round(item.count || 0)
        })),
        field2: (response.data.correlations_field2 || []).map((item: any) => ({
          pair: item.pair || `${Math.round(Math.random() * 12)}-${Math.round(Math.random() * 12)}`,
          frequency_percent: Math.round((item.frequency_percent || 0) * 10) / 10,
          count: Math.round(item.count || 0)
        }))
      },

      // Исправляем циклы с округлением
      cycles_field1: (response.data.cycles_field1 || []).map((item: any) => ({
        number: Math.round(item.number || 0),
        last_seen_ago: Math.round(item.last_seen_ago || 0),
        avg_cycle: Math.round((item.avg_cycle || 0) * 10) / 10,
        is_overdue: Boolean(item.is_overdue)
      })),

      cycles_field2: (response.data.cycles_field2 || []).map((item: any) => ({
        number: Math.round(item.number || 0),
        last_seen_ago: Math.round(item.last_seen_ago || 0),
        avg_cycle: Math.round((item.avg_cycle || 0) * 10) / 10,
        is_overdue: Boolean(item.is_overdue)
      })),

      favorites_analysis: response.data.favorites_analysis
    };

      return adaptedData;
    },
    staleTime: 5 * 60 * 1000, // 5 минут кэш
  });

  // Список доступных графиков
  const chartTypes = [
    {
      id: 'heatmap',
      label: 'Тепловая карта',
      icon: BarChart3,
      description: 'Частоты выпадения чисел',
      color: 'blue'
    },
    {
      id: 'trends',
      label: 'Динамика частот',
      icon: TrendingUp,
      description: 'Тренды во времени',
      color: 'green'
    },
    {
      id: 'correlations',
      label: 'Корреляции',
      icon: Network,
      description: 'Связи между числами',
      color: 'purple'
    },
    {
      id: 'readiness',
      label: 'Готовность',
      icon: Zap,
      description: 'Анализ готовности к выходу',
      color: 'orange'
    },
    {
      id: 'favorites',
      label: 'Избранные',
      icon: Target,
      description: 'Радар избранных чисел',
      color: 'pink'
    }
  ];

  const handleRefresh = () => {
    refetch();
    showSuccess('Обновление','Данные обновлены');
  };

  if (isLoading) {
    return <LoadingScreen message="Загрузка анализа паттернов..." />;
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <div className="text-red-500 mb-4">Ошибка загрузки данных</div>
        <Button onClick={handleRefresh} variant="secondary">
          <RefreshCw className="w-4 h-4 mr-2" />
          Повторить попытку
        </Button>
      </div>
    );
  }

  return (
    <div className="w-full space-y-6">
      {/* Заголовок и управление */}
      <div className="flex justify-between items-start">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">
            📊 Визуализация паттернов
          </h2>
          <p className="text-gray-600 mt-1">
            Интерактивные графики для анализа закономерностей в лотерее {selectedLottery}
          </p>
        </div>
        <Button onClick={handleRefresh} size="sm" variant="secondary">
          <RefreshCw className="w-4 h-4 mr-2" />
          Обновить
        </Button>
      </div>

      {/* Навигация по типам графиков */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
        {chartTypes.map((chart) => {
          const IconComponent = chart.icon;
          const isActive = activeChart === chart.id;

          return (
            <button
              key={chart.id}
              onClick={() => setActiveChart(chart.id)}
              className={cn(
                "p-4 rounded-xl border-2 transition-all duration-200 transform hover:scale-105",
                isActive
                  ? `border-${chart.color}-500 bg-${chart.color}-50 text-${chart.color}-700 shadow-md`
                  : "border-gray-200 hover:border-gray-300 bg-white hover:bg-gray-50"
              )}
            >
              <IconComponent className="w-6 h-6 mx-auto mb-2" />
              <div className="font-medium text-sm">{chart.label}</div>
              <div className="text-xs text-gray-500 mt-1">
                {chart.description}
              </div>
            </button>
          );
        })}
      </div>

      {/* Контент графиков */}
      <div className="bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden">
        {activeChart === 'heatmap' && (
          <FrequencyHeatmap data={patternData} />
        )}

        {activeChart === 'trends' && (
          <TrendAnalysisCharts data={patternData} />
        )}

        {activeChart === 'correlations' && (
          <CorrelationCharts data={patternData} />
        )}

        {activeChart === 'readiness' && (
          <ReadinessAnalysis data={patternData} />
        )}

        {activeChart === 'favorites' && (
          <FavoritesRadar data={patternData} />
        )}
      </div>

      {/* Общие рекомендации */}
      {patternData && (
        <div className="bg-gradient-to-r from-blue-50 to-purple-50 rounded-xl p-6 border-l-4 border-blue-500">
          <h3 className="text-lg font-semibold text-gray-800 mb-3">
            💡 Рекомендации на основе паттернов
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm text-gray-700">
            <div className="space-y-2">
              <div>
                • <strong>Горячие числа поля 1:</strong> {patternData.hot_cold.field1.hot.join(', ') || 'Не найдено'}
              </div>
              <div>
                • <strong>Холодные числа поля 1:</strong> {patternData.hot_cold.field1.cold.join(', ') || 'Не найдено'}
              </div>
            </div>
            <div className="space-y-2">
              <div>
                • <strong>Горячие числа поля 2:</strong> {patternData.hot_cold.field2.hot.join(', ') || 'Не найдено'}
              </div>
              <div>
                • <strong>Лучшие корреляции:</strong> {patternData.correlations.field1[0]?.pair || 'Не найдено'}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default PatternVisualizations;