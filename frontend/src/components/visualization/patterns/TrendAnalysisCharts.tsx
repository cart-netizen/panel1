import React, { useState } from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  AreaChart, Area
} from 'recharts';

interface PatternData {
  hot_cold: {
    field1: { hot: number[], cold: number[] },
    field2: { hot: number[], cold: number[] }
  };
}

interface TrendAnalysisChartsProps {
  data?: PatternData;
}

const TrendAnalysisCharts: React.FC<TrendAnalysisChartsProps> = ({ data }) => {
  const [chartType, setChartType] = useState<'lines' | 'area'>('lines');
  const [selectedField, setSelectedField] = useState<'field1' | 'field2'>('field1');

  // Генерируем данные для многолинейного графика
  const generateFrequencyData = () => {
    const draws = Array.from({length: 30}, (_, i) => i + 1);

    // Получаем горячие числа для выбранного поля
    const hotNumbers = selectedField === 'field1'
      ? (data?.hot_cold.field1.hot.slice(0, 5) || [7, 12, 19, 3, 15])
      : (data?.hot_cold.field2.hot.slice(0, 3) || [2, 4, 1]);

    return draws.map(draw => {
      const drawData: any = { draw };

      hotNumbers.forEach((num, index) => {
        // Симуляция трендов с разными паттернами
        let baseValue = 2;
        let trend = 0;

        // Разные типы трендов для разных чисел
        switch (index % 4) {
          case 0: // Восходящий тренд
            trend = Math.sin(draw * 0.2) * 2 + draw * 0.1;
            break;
          case 1: // Циклический
            trend = Math.sin(draw * 0.4) * 3;
            break;
          case 2: // Нисходящий с всплесками
            trend = -draw * 0.05 + Math.sin(draw * 0.6) * 4;
            break;
          case 3: // Случайные колебания
            trend = (Math.random() - 0.5) * 4;
            break;
        }

        const value = Math.max(0.1, baseValue + trend + (Math.random() - 0.5) * 1);
        drawData[`num${num}`] = value;
      });

      return drawData;
    });
  };

  // Генерируем статистику активности чисел
  const generateActivityStats = () => {
    const hotNumbers = selectedField === 'field1'
      ? (data?.hot_cold.field1.hot.slice(0, 8) || [7, 12, 19, 3, 15, 22, 8, 31])
      : (data?.hot_cold.field2.hot.slice(0, 4) || [2, 4, 1, 3]);

    return hotNumbers.map((num, index) => ({
      number: num,
      activity: Math.random() * 80 + 20, // 20-100%
      trend: index % 3 === 0 ? 'up' : index % 3 === 1 ? 'down' : 'stable',
      change: (Math.random() - 0.5) * 20 // -10 to +10
    }));
  };

  const frequencyData = generateFrequencyData();
  const activityStats = generateActivityStats();

  // Получаем горячие числа для легенды
  const hotNumbers = selectedField === 'field1'
  ? (data?.hot_cold.field1.hot.slice(0, 5) || [7, 12, 19, 3, 15])
    .map(num => Math.round(num))
    .filter(num => num > 0 && num <= 36)
  : (data?.hot_cold.field2.hot.slice(0, 3) || [2, 4, 1])
    .map(num => Math.round(num))
    .filter(num => num > 0 && num <= 20);
  // const hotNumbers = selectedField === 'field1'
  //   ? (data?.hot_cold.field1.hot.slice(0, 5) || [7, 12, 19, 3, 15])
  //   : (data?.hot_cold.field2.hot.slice(0, 3) || [2, 4, 1]);

  // Цвета для линий
  const getLineColor = (index: number): string => {
    const colors: string[] = ['#ef4444', '#f97316', '#eab308', '#22c55e', '#06b6d4', '#8b5cf6'];
    return colors[index % colors.length];
  };

  // Кастомный тултип
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-gray-800 text-white p-3 rounded-lg shadow-xl border border-gray-600">
          <div className="font-bold mb-2">Тираж #{label}</div>
          <div className="space-y-1">
            {payload.map((entry: any, index: number) => (
              <div key={index} className="flex items-center justify-between space-x-4">
                <div className="flex items-center">
                  <div
                    className="w-3 h-3 rounded-full mr-2"
                    style={{ backgroundColor: entry.color }}
                  ></div>
                  <span>Число {entry.name.replace('num', '')}</span>
                </div>
                <span className="font-semibold">{entry.value.toFixed(1)}</span>
              </div>
            ))}
          </div>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="p-6 space-y-6">
      {/* Заголовок */}
      <div className="text-center">
        <h3 className="text-xl font-bold bg-gradient-to-r from-green-600 to-blue-600 bg-clip-text text-transparent">
          📈 Динамика частот горячих чисел
        </h3>
        <p className="text-gray-600 mt-2">
          Показывает изменение активности топ чисел за последние тиражи.
          Пересечение линий = смена лидеров. Восходящий тренд = число набирает популярность.
        </p>
      </div>

      {/* Управление */}
      <div className="flex flex-wrap justify-between items-center gap-4">
        {/* Переключатель полей */}
        <div className="flex space-x-2">
          <button
            onClick={() => setSelectedField('field1')}
            className={`px-4 py-2 rounded-lg font-medium transition-all duration-200 ${
              selectedField === 'field1'
                ? 'bg-gradient-to-r from-green-500 to-blue-600 text-white shadow-lg'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            🎯 Поле 1
          </button>
          <button
            onClick={() => setSelectedField('field2')}
            className={`px-4 py-2 rounded-lg font-medium transition-all duration-200 ${
              selectedField === 'field2'
                ? 'bg-gradient-to-r from-green-500 to-blue-600 text-white shadow-lg'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            🎲 Поле 2
          </button>
        </div>

        {/* Переключатель типа графика */}
        <div className="flex space-x-2">
          <button
            onClick={() => setChartType('lines')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
              chartType === 'lines'
                ? 'bg-blue-500 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            📊 Линии
          </button>
          <button
            onClick={() => setChartType('area')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
              chartType === 'area'
                ? 'bg-blue-500 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            📈 Области
          </button>
        </div>
      </div>

      {/* График трендов */}
      <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-200">
        <div className="h-96">
          <ResponsiveContainer width="100%" height="100%">
            {chartType === 'lines' ? (
              <LineChart data={frequencyData}>
                <defs>
                  {hotNumbers.map((num, i) => (
                    <linearGradient key={num} id={`gradient${num}`} x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={getLineColor(i)} stopOpacity={0.8}/>
                      <stop offset="95%" stopColor={getLineColor(i)} stopOpacity={0.1}/>
                    </linearGradient>
                  ))}
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.1)" />
                <XAxis
                  dataKey="draw"
                  stroke="#6b7280"
                  tick={{ fontSize: 12 }}
                  label={{ value: 'Номер тиража', position: 'bottom' }}
                />
                <YAxis
                  stroke="#6b7280"
                  tick={{ fontSize: 12 }}
                  label={{ value: 'Активность', angle: -90, position: 'insideLeft' }}
                />
                <Tooltip content={<CustomTooltip />} />
                {hotNumbers.map((num, i) => (
                  <Line
                    key={num}
                    type="monotone"
                    dataKey={`num${num}`}
                    stroke={getLineColor(i)}
                    strokeWidth={3}
                    dot={{ fill: getLineColor(i), strokeWidth: 2, r: 4 }}
                    activeDot={{
                      r: 8,
                      style: {
                        filter: 'drop-shadow(0 0 6px rgba(0,0,0,0.3))'
                      }
                    }}
                    name={`${num}`}
                  />
                ))}
              </LineChart>
            ) : (
              <AreaChart data={frequencyData}>
                <defs>
                  {hotNumbers.map((num, i) => (
                    <linearGradient key={num} id={`areaGradient${num}`} x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={getLineColor(i)} stopOpacity={0.6}/>
                      <stop offset="95%" stopColor={getLineColor(i)} stopOpacity={0.1}/>
                    </linearGradient>
                  ))}
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.1)" />
                <XAxis
                  dataKey="draw"
                  stroke="#6b7280"
                  tick={{ fontSize: 12 }}
                />
                <YAxis
                  stroke="#6b7280"
                  tick={{ fontSize: 12 }}
                />
                <Tooltip content={<CustomTooltip />} />
                {hotNumbers.map((num, i) => (
                  <Area
                    key={num}
                    type="monotone"
                    dataKey={`num${num}`}
                    stackId="1"
                    stroke={getLineColor(i)}
                    fill={`url(#areaGradient${num})`}
                    strokeWidth={2}
                  />
                ))}
              </AreaChart>
            )}
          </ResponsiveContainer>
        </div>

        {/* Легенда с числами */}
        <div className="flex flex-wrap justify-center gap-4 mt-4 pt-4 border-t border-gray-200">
          {hotNumbers.map((num, i) => (
            <div key={num} className="flex items-center space-x-2">
              <div
                className="w-4 h-4 rounded-full"
                style={{ backgroundColor: getLineColor(i) }}
              ></div>
              <span className="font-medium">Число {num}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Статистика активности */}
      <div className="bg-gradient-to-br from-green-50 to-blue-50 rounded-xl p-6">
        <h4 className="text-lg font-semibold text-gray-800 mb-4">
          📊 Статистика активности - Поле {selectedField === 'field1' ? '1' : '2'}
        </h4>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {activityStats.map((stat, index) => (
            <div key={stat.number} className="bg-white rounded-lg p-4 shadow-sm border border-gray-200">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center">
                  <div
                    className="w-6 h-6 rounded-full flex items-center justify-center text-white text-sm font-bold mr-2"
                    style={{ backgroundColor: getLineColor(index) }}
                  >
                    {stat.number}
                  </div>
                </div>
                <div className={`text-sm font-semibold ${
                  stat.trend === 'up' ? 'text-green-600' :
                  stat.trend === 'down' ? 'text-red-600' : 'text-gray-600'
                }`}>
                  {stat.trend === 'up' ? '↗️' : stat.trend === 'down' ? '↘️' : '➡️'}
                </div>
              </div>

              <div className="text-sm text-gray-600 space-y-1">
                <div>Активность: <span className="font-semibold">{stat.activity.toFixed(1)}%</span></div>
                <div className={`text-xs ${
                  stat.change > 0 ? 'text-green-600' : stat.change < 0 ? 'text-red-600' : 'text-gray-500'
                }`}>
                  {stat.change > 0 ? '+' : ''}{stat.change.toFixed(1)}% за период
                </div>
              </div>

              {/* Мини-прогресс бар */}
              <div className="mt-2">
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="h-2 rounded-full transition-all duration-500"
                    style={{
                      width: `${Math.min(100, stat.activity)}%`,
                      backgroundColor: getLineColor(index)
                    }}
                  ></div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Интерпретация трендов */}
      <div className="bg-gray-50 rounded-xl p-6">
        <h4 className="text-lg font-semibold text-gray-800 mb-4">📖 Как читать тренды</h4>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-sm text-gray-700">
          <div className="space-y-3">
            <div>
              <strong>Восходящий тренд (↗️):</strong>
              <ul className="ml-4 mt-1 space-y-1">
                <li>• Число набирает активность</li>
                <li>• Может быть готово к серии выпадений</li>
                <li>• Рассмотрите для включения в комбинацию</li>
              </ul>
            </div>
            <div>
              <strong>Пересечения линий:</strong> Смена лидерства между числами
            </div>
          </div>
          <div className="space-y-3">
            <div>
              <strong>Нисходящий тренд (↘️):</strong>
              <ul className="ml-4 mt-1 space-y-1">
                <li>• Число теряет активность</li>
                <li>• Может уходить в "холодный" период</li>
                <li>• Используйте осторожно</li>
              </ul>
            </div>
            <div>
              <strong>Стабильные линии (➡️):</strong> Число в равновесии, предсказуемо
            </div>
          </div>
        </div>

        {/* Рекомендация */}
        <div className="mt-4 p-4 bg-white rounded-lg border border-blue-200">
          <div className="font-semibold text-blue-800 mb-2">💡 Стратегическая рекомендация:</div>
          <div className="text-sm text-gray-700">
            Комбинируйте числа с восходящими трендами (1-2 шт.) и стабильные числа (2-3 шт.)
            для сбалансированной стратегии. Избегайте чисел с резко падающими трендами.
          </div>
        </div>
      </div>
    </div>
  );
};

export default TrendAnalysisCharts;