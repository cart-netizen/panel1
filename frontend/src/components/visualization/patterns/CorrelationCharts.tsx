import React, { useState } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  Cell
} from 'recharts';

interface PatternData {
  correlations: {
    field1: Array<{ pair: string, frequency_percent: number, count: number }>,
    field2: Array<{ pair: string, frequency_percent: number, count: number }>
  };
}

interface CorrelationChartsProps {
  data?: PatternData;
}

const CorrelationCharts: React.FC<CorrelationChartsProps> = ({ data }) => {
  const [selectedField, setSelectedField] = useState<'field1' | 'field2'>('field1');

  // Генерируем моковые данные, если реальные данные недоступны
  const generateMockCorrelations = () => ({
    field1: [
      { pair: "7-12", frequency_percent: 25.3, count: 12 },
      { pair: "19-3", frequency_percent: 18.7, count: 9 },
      { pair: "15-7", frequency_percent: 16.2, count: 8 },
      { pair: "4-28", frequency_percent: 14.5, count: 7 },
      { pair: "11-22", frequency_percent: 12.8, count: 6 },
      { pair: "33-5", frequency_percent: 11.1, count: 5 },
      { pair: "2-17", frequency_percent: 9.4, count: 4 }
    ],
    field2: [
      { pair: "2-4", frequency_percent: 32.1, count: 15 },
      { pair: "1-3", frequency_percent: 28.4, count: 13 },
      { pair: "3-4", frequency_percent: 22.6, count: 10 },
      { pair: "1-2", frequency_percent: 19.8, count: 9 }
    ]
  });

  const correlationData = data?.correlations || generateMockCorrelations();
  const currentFieldData = correlationData[selectedField] || [];

  // Кастомный цвет для каждого столбца
  const getBarColor = (index: number, value: number) => {
    const colors = [
      '#8b5cf6', // фиолетовый
      '#3b82f6', // синий
      '#10b981', // зеленый
      '#f59e0b', // желтый
      '#ef4444', // красный
      '#ec4899', // розовый
      '#14b8a6'  // бирюзовый
    ];
    return colors[index % colors.length];
  };

  // Кастомный tooltip
    const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-gray-800 text-white p-3 rounded-lg shadow-xl border border-gray-600">
          <div className="font-bold text-lg mb-2">Пара: {label}</div>
          <div className="space-y-1">
            <div>📊 Частота: <span className="font-semibold">{data.frequency_percent}%</span></div>
            <div>🔢 Встреч: <span className="font-semibold">{data.count} раз</span></div>
            <div className="text-xs text-gray-300 mt-2">
              Числа этой пары появлялись вместе в {data.count} тиражах
            </div>
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
        <h3 className="text-xl font-bold bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">
          🕸️ Сеть связей между числами
        </h3>
        <p className="text-gray-600 mt-2">
          Показывает частоту совместного появления пар чисел. Высота столбца = частота появления пары.
        </p>
      </div>

      {/* Переключатель полей */}
      <div className="flex justify-center space-x-2">
        <button
          onClick={() => setSelectedField('field1')}
          className={`px-6 py-3 rounded-xl font-medium transition-all duration-200 ${
            selectedField === 'field1'
              ? 'bg-gradient-to-r from-indigo-500 to-purple-600 text-white shadow-lg'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          }`}
        >
          🎯 Поле 1 ({correlationData.field1.length} пар)
        </button>
        <button
          onClick={() => setSelectedField('field2')}
          className={`px-6 py-3 rounded-xl font-medium transition-all duration-200 ${
            selectedField === 'field2'
              ? 'bg-gradient-to-r from-indigo-500 to-purple-600 text-white shadow-lg'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          }`}
        >
          🎲 Поле 2 ({correlationData.field2.length} пар)
        </button>
      </div>

      {/* График корреляций */}
      <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-200">
        <div className="h-96">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={currentFieldData}
              margin={{ top: 20, right: 30, left: 20, bottom: 60 }}
            >
              <defs>
                <linearGradient id="correlationGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.9}/>
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.7}/>
                </linearGradient>
              </defs>

              <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.1)" />

              <XAxis
                dataKey="pair"
                stroke="#6b7280"
                tick={{ fontSize: 12, fontWeight: 'bold' }}
                angle={-45}
                textAnchor="end"
                height={80}
              />

              <YAxis
                stroke="#6b7280"
                tick={{ fontSize: 12 }}
                label={{ value: 'Частота (%)', angle: -90, position: 'insideLeft' }}
              />

              <Tooltip content={<CustomTooltip />} />

              <Bar
                dataKey="frequency_percent"
                radius={[8, 8, 0, 0]}
                style={{
                  filter: 'drop-shadow(0 4px 8px rgba(0,0,0,0.1))'
                }}
              >
                {currentFieldData.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={getBarColor(index, entry.frequency_percent)}
                    className="hover:brightness-110 transition-all duration-300"
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Детальная таблица */}
      <div className="bg-gradient-to-br from-gray-50 to-gray-100 rounded-xl p-6">
        <h4 className="text-lg font-semibold text-gray-800 mb-4">
          📋 Детальная статистика {selectedField === 'field1' ? 'поля 1' : 'поля 2'}
        </h4>

        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b-2 border-gray-300">
                <th className="text-left py-3 px-4 font-semibold text-gray-700">Ранг</th>
                <th className="text-left py-3 px-4 font-semibold text-gray-700">Пара чисел</th>
                <th className="text-center py-3 px-4 font-semibold text-gray-700">Частота</th>
                <th className="text-center py-3 px-4 font-semibold text-gray-700">Встреч</th>
                <th className="text-center py-3 px-4 font-semibold text-gray-700">Оценка</th>
              </tr>
            </thead>
            <tbody>
              {currentFieldData.map((item, index) => (
                <tr
                  key={item.pair}
                  className="border-b border-gray-200 hover:bg-white transition-colors duration-200"
                >
                  <td className="py-3 px-4">
                    <div className="flex items-center">
                      <div
                        className="w-6 h-6 rounded-full flex items-center justify-center text-white text-sm font-bold mr-2"
                        style={{ backgroundColor: getBarColor(index, item.frequency_percent) }}
                      >
                        {index + 1}
                      </div>
                    </div>
                  </td>
                  <td className="py-3 px-4">
                    <div className="font-medium text-lg">{item.pair}</div>
                  </td>
                  <td className="py-3 px-4 text-center">
                    <div className="inline-flex items-center justify-center px-3 py-1 rounded-full bg-blue-100 text-blue-800 font-semibold">
                      {item.frequency_percent}%
                    </div>
                  </td>
                  <td className="py-3 px-4 text-center">
                    <div className="text-gray-600 font-medium">{item.count}</div>
                  </td>
                  <td className="py-3 px-4 text-center">
                    <div className={`inline-flex items-center px-2 py-1 rounded-full text-sm font-medium ${
                      item.frequency_percent >= 20 ? 'bg-green-100 text-green-800' :
                      item.frequency_percent >= 15 ? 'bg-yellow-100 text-yellow-800' :
                      'bg-red-100 text-red-800'
                    }`}>
                      {item.frequency_percent >= 20 ? '🔥 Сильная' :
                       item.frequency_percent >= 15 ? '⚡ Умеренная' :
                       '❄️ Слабая'}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Рекомендации */}
      <div className="bg-gradient-to-r from-indigo-50 to-purple-50 rounded-xl p-6 border-l-4 border-indigo-500">
        <h4 className="text-lg font-semibold text-gray-800 mb-3">
          💡 Как использовать корреляции
        </h4>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm text-gray-700">
          <div className="space-y-2">
            <div>
              • <strong>Сильные пары (≥20%):</strong> Рассмотрите для сбалансированных комбинаций
            </div>
            <div>
              • <strong>Умеренные пары (15-19%):</strong> Хороший вариант для разнообразия
            </div>
          </div>
          <div className="space-y-2">
            <div>
              • <strong>Слабые пары (&lt;15%):</strong> Используйте осторожно или избегайте
            </div>
            <div>
              • <strong>Стратегия:</strong> Комбинируйте 1-2 сильные пары с одиночными числами
            </div>
          </div>
        </div>

        {/* Топ рекомендация */}
        {currentFieldData.length > 0 && (
          <div className="mt-4 p-3 bg-white rounded-lg border border-indigo-200">
            <div className="font-semibold text-indigo-800">
              🎯 Лучшая пара {selectedField === 'field1' ? 'поля 1' : 'поля 2'}: {currentFieldData[0].pair}
            </div>
            <div className="text-sm text-gray-600 mt-1">
              Появляется в {currentFieldData[0].frequency_percent}% случаев ({currentFieldData[0].count} встреч)
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default CorrelationCharts;