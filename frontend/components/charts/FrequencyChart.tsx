// frontend/src/components/charts/FrequencyChart.tsx
//  Частота выпадения чисел
import React, { useMemo, useState } from 'react';
import { Bar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ChartOptions,
  TooltipItem,
} from 'chart.js';

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
);

interface FrequencyChartProps {
  data: Array<{
    draw_number?: number;
    Тираж?: number;
    field1_numbers?: number[];
    field2_numbers?: number[];
    Числа_Поле1_list?: number[];
    Числа_Поле2_list?: number[];
  }>;
  lotteryType: string;
  maxNumbers: {
    field1: number;
    field2: number;
  };
}

export const FrequencyChart: React.FC<FrequencyChartProps> = ({ data, lotteryType, maxNumbers }) => {
  const [drawsLimit, setDrawsLimit] = useState<number>(200);

  // Фильтруем данные по выбранному лимиту
  const filteredData = useMemo(() => {
    if (!data) return [];
    if (drawsLimit === -1) return data; // -1 означает "все тиражи"
    return data.slice(0, drawsLimit);
  }, [data, drawsLimit]);

  const { field1ChartData, field2ChartData, maxFreq } = useMemo(() => {
    if (!filteredData || filteredData.length === 0) {
      return { field1ChartData: null, field2ChartData: null, maxFreq: 0 };
    }

    const field1Freq: Record<number, number> = {};
    const field2Freq: Record<number, number> = {};

    // Инициализация
    for (let i = 1; i <= maxNumbers.field1; i++) field1Freq[i] = 0;
    for (let i = 1; i <= maxNumbers.field2; i++) field2Freq[i] = 0;

    // Подсчет частот
    filteredData.forEach(draw => {
      const f1Numbers = draw.field1_numbers || draw.Числа_Поле1_list || [];
      const f2Numbers = draw.field2_numbers || draw.Числа_Поле2_list || [];

      f1Numbers.forEach(num => {
        if (field1Freq[num] !== undefined) field1Freq[num]++;
      });

      f2Numbers.forEach(num => {
        if (field2Freq[num] !== undefined) field2Freq[num]++;
      });
    });

    const maxFrequency = Math.max(
      ...Object.values(field1Freq),
      ...Object.values(field2Freq)
    );

    // Вычисляем пороги для каждого поля отдельно
    const getFieldThresholds = (fieldFreq: Record<number, number>) => {
      const values = Object.values(fieldFreq);
      const avg = values.reduce((a, b) => a + b, 0) / values.length;
      const max = Math.max(...values);
      const min = Math.min(...values);

      return {
        hot: avg + (max - avg) * 0.5,  // Топ 50% от среднего к максимуму
        cold: avg - (avg - min) * 0.5  // Нижние 50% от минимума к среднему
      };
    };

    const field1Thresholds = getFieldThresholds(field1Freq);
    const field2Thresholds = getFieldThresholds(field2Freq);

    const createChartData = (
      frequencies: Record<number, number>,
      maxNum: number,
      fieldName: string,
      thresholds: { hot: number; cold: number }
    ) => {
      const labels = Array.from({ length: maxNum }, (_, i) => String(i + 1));
      const dataValues = labels.map(label => frequencies[Number(label)]);

      const backgroundColors = dataValues.map(value => {
        if (value > thresholds.hot) return 'rgba(239, 68, 68, 0.8)'; // Красный - горячие
        if (value < thresholds.cold) return 'rgba(156, 163, 175, 0.6)'; // Серый - холодные
        return 'rgba(59, 130, 246, 0.8)'; // Синий - обычные
      });

      const borderColors = dataValues.map(value => {
        if (value > thresholds.hot) return 'rgba(239, 68, 68, 1)';
        if (value < thresholds.cold) return 'rgba(156, 163, 175, 1)';
        return 'rgba(59, 130, 246, 1)';
      });

      return {
        labels,
        datasets: [{
          label: fieldName,
          data: dataValues,
          backgroundColor: backgroundColors,
          borderColor: borderColors,
          borderWidth: 1,
          borderRadius: 4,
        }],
      };
    };

    return {
      field1ChartData: createChartData(field1Freq, maxNumbers.field1, 'Поле 1', field1Thresholds),
      field2ChartData: maxNumbers.field2 > 0
        ? createChartData(field2Freq, maxNumbers.field2, 'Поле 2', field2Thresholds)
        : null,
      maxFreq: maxFrequency,
    };
  }, [filteredData, maxNumbers]);

  const chartOptions: ChartOptions<'bar'> = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        titleFont: { size: 12 },
        bodyFont: { size: 11 },
        callbacks: {
          title: (context: TooltipItem<'bar'>[]) => `Число: ${context[0].label}`,
          label: (context: TooltipItem<'bar'>) => `Выпало: ${context.raw} раз`,
        },
      },
    },
    scales: {
      y: {
        beginAtZero: true,
        max: maxFreq + 5,
        ticks: { stepSize: Math.ceil(maxFreq / 10) }
      },
      x: {
        grid: { display: false },
        ticks: {
          autoSkip: false,
          maxRotation: 45,
          minRotation: maxNumbers.field1 > 20 ? 45 : 0,
          font: { size: maxNumbers.field1 > 30 ? 8 : 10 }
        }
      },
    },
  };

  if (!field1ChartData) {
    return (
      <div className="card">
        <div className="card-body text-center text-gray-500">
          <p>Нет данных для отображения графика</p>
        </div>
      </div>
    );
  }

  // Рассчитываем пропорции для полей
  const field1Width = maxNumbers.field1;
  const field2Width = maxNumbers.field2 > 0 ? maxNumbers.field2 : 1;
  const totalWidth = field1Width + field2Width;
  const field1Percent = Math.round((field1Width / totalWidth) * 100);
  const field2Percent = 100 - field1Percent;

  return (
    <div className="card">
      <div className="card-header flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900">
          📊 Частота выпадения чисел
        </h2>
        <div className="flex items-center space-x-2">
          <span className="text-sm text-gray-600">Анализ за:</span>
          <select
            value={drawsLimit}
            onChange={(e) => setDrawsLimit(Number(e.target.value))}
            className="px-3 py-1 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <option value={100}>100 тиражей</option>
            <option value={200}>200 тиражей</option>
            <option value={-1}>Все тиражи ({data?.length || 0})</option>
          </select>
        </div>
      </div>
      <div className="card-body">
        <div className="flex gap-4">
          {/* График для поля 1 */}
          <div style={{ width: `${field1Percent}%` }}>
            <h3 className="text-sm font-medium text-gray-700 mb-3 text-center">
              Поле 1
            </h3>
            <div style={{ height: '250px' }}>
              <Bar options={chartOptions} data={field1ChartData} />
            </div>
          </div>

          {/* График для поля 2 (если есть) */}
          {field2ChartData && maxNumbers.field2 > 0 && (
            <div style={{ width: `${field2Percent}%` }}>
              <h3 className="text-sm font-medium text-gray-700 mb-3 text-center">
                Поле 2
              </h3>
              <div style={{ height: '250px' }}>
                <Bar
                  options={{
                    ...chartOptions,
                    scales: {
                      ...chartOptions.scales,
                      x: {
                        ...chartOptions.scales?.x,
                        ticks: {
                          autoSkip: false,
                          maxRotation: 0,
                          font: { size: 10 }
                        }
                      }
                    }
                  }}
                  data={field2ChartData}
                />
              </div>
            </div>
          )}
        </div>

        {/* Легенда */}
        <div className="mt-4 flex items-center justify-center space-x-6 text-sm">
          <div className="flex items-center space-x-2">
            <div className="w-4 h-4 bg-red-500 rounded"></div>
            <span>Горячие (часто)</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-4 h-4 bg-blue-500 rounded"></div>
            <span>Обычные (средне)</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-4 h-4 bg-gray-400 rounded"></div>
            <span>Холодные (редко)</span>
          </div>
        </div>

        <div className="mt-2 text-center text-xs text-gray-500">
          Анализируется {filteredData.length} тиражей
        </div>
      </div>
    </div>
  );
};