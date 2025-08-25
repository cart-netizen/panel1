import React, { useState } from 'react';
import {
  ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  Cell
} from 'recharts';
import { useSelectedLottery } from '../../../store';
import { LOTTERY_CONFIGS } from '../../../constants';

interface PatternData {
  hot_cold: {
    field1: { hot: number[], cold: number[] },
    field2: { hot: number[], cold: number[] }
  };
  cycles_field1?: Array<{ number: number, last_seen_ago: number, avg_cycle: number, is_overdue: boolean }>;
  cycles_field2?: Array<{ number: number, last_seen_ago: number, avg_cycle: number, is_overdue: boolean }>;
}

interface ReadinessAnalysisProps {
  data?: PatternData;
}

interface BubbleDataPoint {
  number: number;
  avgInterval: number;
  currentInterval: number;
  frequency: number;
  isHot: boolean;
  isCold: boolean;
  isOverdue: boolean;
  readinessScore: number; // 0-100
  field: 'field1' | 'field2';
}

const ReadinessAnalysis: React.FC<ReadinessAnalysisProps> = ({ data }) => {
  const selectedLottery = useSelectedLottery();
  const config = LOTTERY_CONFIGS[selectedLottery];
  const [selectedField, setSelectedField] = useState<'field1' | 'field2'>('field1');

  // Генерируем данные для пузырькового графика
  const generateBubbleData = (): { field1: BubbleDataPoint[], field2: BubbleDataPoint[] } => {
    const field1Data: BubbleDataPoint[] = [];
    const field2Data: BubbleDataPoint[] = [];

    // Поле 1
    for (let i = 1; i <= config.field1_max; i++) {
      const isHot = data?.hot_cold.field1.hot.includes(i) || false;
      const isCold = data?.hot_cold.field1.cold.includes(i) || false;
      const cycleInfo = data?.cycles_field1?.find(c => c.number === i);

      const avgInterval = cycleInfo?.avg_cycle || (Math.random() * 10 + 3);
      const currentInterval = cycleInfo?.last_seen_ago || (Math.random() * 15 + 1);
      const isOverdue = cycleInfo?.is_overdue || currentInterval > avgInterval * 1.5;

      // Расчет частоты на основе статуса
      let frequency = 10; // базовая частота
      if (isHot) frequency += Math.random() * 15 + 5;
      if (isCold) frequency = Math.max(2, frequency - Math.random() * 8);
      if (isOverdue) frequency += 3; // бонус за просроченность

      // Расчет готовности (0-100)
      let readinessScore = 50; // базовый уровень

      // Чем больше текущий интервал относительно среднего, тем выше готовность
      const intervalRatio = currentInterval / avgInterval;
      readinessScore += Math.min(30, intervalRatio * 20);

      // Бонус за просроченность
      if (isOverdue) readinessScore += 20;

      // Штраф за "горячесть" (недавно выпадало)
      if (isHot && currentInterval < avgInterval * 0.5) readinessScore -= 15;

      // Ограничиваем в диапазоне 0-100
      readinessScore = Math.max(0, Math.min(100, readinessScore));

      field1Data.push({
        number: i,
        avgInterval,
        currentInterval,
        frequency,
        isHot,
        isCold,
        isOverdue,
        readinessScore,
        field: 'field1'
      });
    }

    // Поле 2
    for (let i = 1; i <= config.field2_max; i++) {
      const isHot = data?.hot_cold.field2.hot.includes(i) || false;
      const isCold = data?.hot_cold.field2.cold.includes(i) || false;
      const cycleInfo = data?.cycles_field2?.find(c => c.number === i);

      const avgInterval = cycleInfo?.avg_cycle || (Math.random() * 8 + 2);
      const currentInterval = cycleInfo?.last_seen_ago || (Math.random() * 12 + 1);
      const isOverdue = cycleInfo?.is_overdue || currentInterval > avgInterval * 1.5;

      let frequency = 15; // базовая частота для поля 2
      if (isHot) frequency += Math.random() * 20 + 10;
      if (isCold) frequency = Math.max(5, frequency - Math.random() * 10);
      if (isOverdue) frequency += 5;

      let readinessScore = 50;
      const intervalRatio = currentInterval / avgInterval;
      readinessScore += Math.min(35, intervalRatio * 25);
      if (isOverdue) readinessScore += 25;
      if (isHot && currentInterval < avgInterval * 0.5) readinessScore -= 20;
      readinessScore = Math.max(0, Math.min(100, readinessScore));

      field2Data.push({
        number: i,
        avgInterval,
        currentInterval,
        frequency,
        isHot,
        isCold,
        isOverdue,
        readinessScore,
        field: 'field2'
      });
    }

    return { field1: field1Data, field2: field2Data };
  };

  const bubbleData = generateBubbleData();
  const currentFieldData = bubbleData[selectedField];

  // Кастомная точка для пузырькового графика
  const CustomBubble = (props: any) => {
    const { cx, cy, payload } = props;
    const radius = Math.sqrt(payload.frequency) * 2;

    let color = '#10b981'; // зеленый по умолчанию
    if (payload.readinessScore >= 75) color = '#dc2626'; // красный - очень готов
    else if (payload.readinessScore >= 60) color = '#ea580c'; // оранжевый - готов
    else if (payload.isHot) color = '#f59e0b'; // желтый - горячий
    else if (payload.isCold) color = '#3b82f6'; // синий - холодный

    return (
      <circle
        cx={cx}
        cy={cy}
        r={radius}
        fill={color}
        fillOpacity={0.7}
        stroke={color}
        strokeWidth={2}
        className="transition-all duration-300 hover:stroke-width-4 cursor-pointer animate-pulse"
        style={{
          filter: 'drop-shadow(0 4px 8px rgba(0,0,0,0.2))',
          animationDuration: payload.readinessScore >= 75 ? '1s' : '2s'
        }}
      />
    );
  };

  // Кастомный тултип
  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-gray-800 text-white p-4 rounded-lg shadow-xl border border-gray-600 max-w-xs">
          <div className="font-bold text-lg mb-2">Число {data.number}</div>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span>Готовность:</span>
              <span className={`font-bold ${
                data.readinessScore >= 75 ? 'text-red-300' :
                data.readinessScore >= 60 ? 'text-orange-300' :
                data.readinessScore >= 40 ? 'text-yellow-300' :
                'text-green-300'
              }`}>
                {data.readinessScore.toFixed(0)}%
              </span>
            </div>
            <div className="flex justify-between">
              <span>Частота:</span>
              <span className="font-semibold">{Math.round(data.frequency)}</span>
            </div>
            <div className="flex justify-between">
              <span>Интервал:</span>
              <span>{Math.round(data.currentInterval * 10) / 10} тиражей</span>
            </div>
            <div className="flex justify-between">
              <span>Средний цикл:</span>
              <span>{Math.round(data.avgInterval * 10) / 10}</span>
            </div>
            {data.isOverdue && <div className="text-red-300 font-semibold">⏰ Просрочено!</div>}
            {data.isHot && <div className="text-orange-300">🔥 Горячее</div>}
            {data.isCold && <div className="text-blue-300">❄️ Холодное</div>}
          </div>
        </div>
      );
    }
    return null;
  };

  // Получаем самые готовые числа
  const getTopReadyNumbers = () => {
    return currentFieldData
      .filter(d => d.readinessScore >= 60)
      .sort((a, b) => b.readinessScore - a.readinessScore)
      .slice(0, 5);
  };

  const topReady = getTopReadyNumbers();

  return (
    <div className="p-6 space-y-6">
      {/* Заголовок */}
      <div className="text-center">
        <h3 className="text-xl font-bold bg-gradient-to-r from-purple-600 to-pink-600 bg-clip-text text-transparent">
          💫 Анализ готовности чисел к выходу
        </h3>
        <p className="text-gray-600 mt-2">
          X = средний интервал между появлениями, Y = текущий интервал с последнего появления.
          Размер пузыря = общая частота. Правый верхний угол = числа "готовые к выходу".
        </p>
      </div>

      {/* Переключатель полей */}
      <div className="flex justify-center space-x-2">
        <button
          onClick={() => setSelectedField('field1')}
          className={`px-6 py-3 rounded-xl font-medium transition-all duration-200 ${
            selectedField === 'field1'
              ? 'bg-gradient-to-r from-purple-500 to-pink-600 text-white shadow-lg'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          }`}
        >
          🎯 Поле 1 ({config.field1_max} чисел)
        </button>
        <button
          onClick={() => setSelectedField('field2')}
          className={`px-6 py-3 rounded-xl font-medium transition-all duration-200 ${
            selectedField === 'field2'
              ? 'bg-gradient-to-r from-purple-500 to-pink-600 text-white shadow-lg'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          }`}
        >
          🎲 Поле 2 ({config.field2_max} чисел)
        </button>
      </div>

      {/* Пузырьковый график */}
      <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-200">
        <div className="h-96">
          <ResponsiveContainer width="100%" height="100%">
            <ScatterChart data={currentFieldData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.1)" />
              <XAxis
                dataKey="avgInterval"
                name="Средний интервал"
                stroke="#6b7280"
                tick={{ fontSize: 12 }}
                label={{ value: 'Средний интервал (тиражи)', position: 'bottom' }}
              />
              <YAxis
                dataKey="currentInterval"
                name="Текущий интервал"
                stroke="#6b7280"
                tick={{ fontSize: 12 }}
                label={{ value: 'Текущий интервал (тиражи)', angle: -90, position: 'insideLeft' }}
              />
              <Tooltip content={<CustomTooltip />} cursor={{ strokeDasharray: '3 3' }} />
              <Scatter dataKey="frequency" shape={<CustomBubble />} />
            </ScatterChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Зоны готовности */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="text-center p-4 bg-red-50 rounded-xl border border-red-200">
          <div className="w-6 h-6 bg-red-500 rounded-full mx-auto mb-2"></div>
          <div className="font-semibold text-red-700">Очень готовы</div>
          <div className="text-sm text-red-600">Готовность ≥ 75%</div>
          <div className="text-xs text-gray-500 mt-1">
            {currentFieldData.filter(d => d.readinessScore >= 75).length} чисел
          </div>
        </div>
        <div className="text-center p-4 bg-orange-50 rounded-xl border border-orange-200">
          <div className="w-6 h-6 bg-orange-500 rounded-full mx-auto mb-2"></div>
          <div className="font-semibold text-orange-700">Готовы</div>
          <div className="text-sm text-orange-600">60-74%</div>
          <div className="text-xs text-gray-500 mt-1">
            {currentFieldData.filter(d => d.readinessScore >= 60 && d.readinessScore < 75).length} чисел
          </div>
        </div>
        <div className="text-center p-4 bg-green-50 rounded-xl border border-green-200">
          <div className="w-6 h-6 bg-green-500 rounded-full mx-auto mb-2"></div>
          <div className="font-semibold text-green-700">Нейтральные</div>
          <div className="text-sm text-green-600">40-59%</div>
          <div className="text-xs text-gray-500 mt-1">
            {currentFieldData.filter(d => d.readinessScore >= 40 && d.readinessScore < 60).length} чисел
          </div>
        </div>
        <div className="text-center p-4 bg-blue-50 rounded-xl border border-blue-200">
          <div className="w-6 h-6 bg-blue-500 rounded-full mx-auto mb-2"></div>
          <div className="font-semibold text-blue-700">Не готовы</div>
          <div className="text-sm text-blue-600">&lt; 40%</div>
          <div className="text-xs text-gray-500 mt-1">
            {currentFieldData.filter(d => d.readinessScore < 40).length} чисел
          </div>
        </div>
      </div>

      {/* Топ готовых чисел */}
      {topReady.length > 0 && (
        <div className="bg-gradient-to-br from-red-50 to-pink-50 rounded-xl p-6 border-l-4 border-red-500">
          <h4 className="text-lg font-semibold text-gray-800 mb-4">
            🎯 Топ готовых к выходу - Поле {selectedField === 'field1' ? '1' : '2'}
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {topReady.map((item, index) => (
              <div key={item.number} className="bg-white rounded-lg p-4 shadow-sm border border-red-200">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center">
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center text-white text-sm font-bold mr-2 ${
                      index === 0 ? 'bg-red-500' : index === 1 ? 'bg-orange-500' : 'bg-yellow-500'
                    }`}>
                      {item.number}
                    </div>
                    <div className="font-semibold">#{index + 1}</div>
                  </div>
                  <div className={`px-2 py-1 rounded-full text-xs font-bold text-white ${
                    item.readinessScore >= 85 ? 'bg-red-500' :
                    item.readinessScore >= 75 ? 'bg-orange-500' : 'bg-yellow-500'
                  }`}>
                    {item.readinessScore.toFixed(0)}%
                  </div>
                </div>
                <div className="text-sm text-gray-600 space-y-1">
                  <div>Интервал: {item.currentInterval.toFixed(1)} / {item.avgInterval.toFixed(1)}</div>
                  <div>Частота: {item.frequency.toFixed(0)}</div>
                  {item.isOverdue && <div className="text-red-600 font-semibold">⏰ Просрочено</div>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Руководство по интерпретации */}
      <div className="bg-gray-50 rounded-xl p-6">
        <h4 className="text-lg font-semibold text-gray-800 mb-4">📖 Как читать график</h4>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-sm text-gray-700">
          <div className="space-y-3">
            <div>
              <strong>Оси графика:</strong>
              <ul className="ml-4 mt-1 space-y-1">
                <li>• X (горизонт): средний интервал между появлениями</li>
                <li>• Y (вертикаль): интервал с последнего появления</li>
              </ul>
            </div>
            <div>
              <strong>Размер пузыря:</strong> общая частота появления числа
            </div>
          </div>
          <div className="space-y-3">
            <div>
              <strong>Зоны готовности:</strong>
              <ul className="ml-4 mt-1 space-y-1">
                <li>• Правый верх: числа готовы к выходу</li>
                <li>• Левый низ: недавно выпадавшие числа</li>
                <li>• Центр: нейтральные числа</li>
              </ul>
            </div>
            <div>
              <strong>Цвета:</strong> красный = очень готов, оранжевый = готов, зеленый = нейтрально
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ReadinessAnalysis;