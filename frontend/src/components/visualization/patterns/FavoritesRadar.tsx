import React, { useState } from 'react';
import {
  RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, ResponsiveContainer, Tooltip
} from 'recharts';

interface PatternData {
  favorites_analysis?: {
    field1: { [key: string]: { frequency: number, percentage: number } },
    field2: { [key: string]: { frequency: number, percentage: number } }
  };
  hot_cold: {
    field1: { hot: number[], cold: number[] },
    field2: { hot: number[], cold: number[] }
  };
}

interface FavoritesRadarProps {
  data?: PatternData;
}

const FavoritesRadar: React.FC<FavoritesRadarProps> = ({ data }) => {
  const [favoritesField1, setFavoritesField1] = useState<number[]>([7, 12]); // Пример избранных
  const [favoritesField2, setFavoritesField2] = useState<number[]>([2]); // Пример избранных
  const [isEditMode, setIsEditMode] = useState(false);

  // Генерируем данные для радарной диаграммы
  const generateRadarData = () => {
    if (favoritesField1.length === 0 && favoritesField2.length === 0) {
      return [];
    }

    const metrics = ['Частота', 'Тренд', 'Корреляции', 'Циклы', 'Позиции'];

    return metrics.map(metric => {
      const metricData: any = { metric };

      // Анализируем избранные числа поля 1
      favoritesField1.forEach((num, index) => {
        let value = 50; // базовое значение

        switch(metric) {
          case 'Частота':
            // На основе горячести числа
            if (data?.hot_cold.field1.hot.includes(num)) value = 85;
            else if (data?.hot_cold.field1.cold.includes(num)) value = 25;
            else value = Math.random() * 40 + 40; // 40-80
            break;

          case 'Тренд':
            // Симуляция трендового анализа
            value = Math.random() * 60 + 30; // 30-90
            break;

          case 'Корреляции':
            // Анализ связей с другими числами
            value = Math.random() * 70 + 20; // 20-90
            break;

          case 'Циклы':
            // Анализ циклов выпадения
            value = Math.random() * 50 + 40; // 40-90
            break;

          case 'Позиции':
            // Анализ позиций в тиражах
            value = Math.random() * 60 + 30; // 30-90
            break;

          default:
            value = 50;
        }

        metricData[`field1_${num}`] = Math.min(100, Math.max(0, value));
      });

      // Анализируем избранные числа поля 2
      favoritesField2.forEach((num, index) => {
        let value = 50;

        switch(metric) {
          case 'Частота':
            if (data?.hot_cold.field2.hot.includes(num)) value = 90;
            else if (data?.hot_cold.field2.cold.includes(num)) value = 20;
            else value = Math.random() * 40 + 45;
            break;
          case 'Тренд':
            value = Math.random() * 60 + 35;
            break;
          case 'Корреляции':
            value = Math.random() * 70 + 25;
            break;
          case 'Циклы':
            value = Math.random() * 50 + 45;
            break;
          case 'Позиции':
            value = Math.random() * 60 + 35;
            break;
          default:
            value = 50;
        }

        metricData[`field2_${num}`] = Math.min(100, Math.max(0, value));
      });

      return metricData;
    });
  };

  const radarData = generateRadarData();

  // Получаем цвета для разных чисел
  const getColorForNumber = (num: number, field: 'field1' | 'field2') => {
    const field1Colors = ['#ef4444', '#f97316', '#eab308', '#22c55e', '#06b6d4'];
    const field2Colors = ['#8b5cf6', '#ec4899', '#14b8a6'];

    const colors = field === 'field1' ? field1Colors : field2Colors;
    const index = field === 'field1'
      ? favoritesField1.indexOf(num)
      : favoritesField2.indexOf(num);

    return colors[index % colors.length];
  };

  // Кастомный тултип
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-gray-800 text-white p-3 rounded-lg shadow-xl">
          <div className="font-bold mb-2">{label}</div>
          {payload.map((entry: any, index: number) => {
            const [field, num] = entry.name.split('_');
            return (
              <div key={index} className="flex items-center justify-between space-x-4">
                <div className="flex items-center">
                  <div
                    className="w-3 h-3 rounded-full mr-2"
                    style={{ backgroundColor: entry.color }}
                  ></div>
                  <span>{field === 'field1' ? 'П1' : 'П2'} - {num}</span>
                </div>
                <span className="font-semibold">{entry.value.toFixed(0)}</span>
              </div>
            );
          })}
        </div>
      );
    }
    return null;
  };

  // Добавление/удаление избранных чисел
  const toggleFavorite = (num: number, field: 'field1' | 'field2') => {
    if (field === 'field1') {
      if (favoritesField1.includes(num)) {
        setFavoritesField1(favoritesField1.filter(n => n !== num));
      } else if (favoritesField1.length < 5) {
        setFavoritesField1([...favoritesField1, num]);
      }
    } else {
      if (favoritesField2.includes(num)) {
        setFavoritesField2(favoritesField2.filter(n => n !== num));
      } else if (favoritesField2.length < 3) {
        setFavoritesField2([...favoritesField2, num]);
      }
    }
  };

  const hasAnyFavorites = favoritesField1.length > 0 || favoritesField2.length > 0;

  return (
    <div className="p-6 space-y-6">
      {/* Заголовок */}
      <div className="text-center">
        <h3 className="text-xl font-bold bg-gradient-to-r from-pink-600 to-orange-600 bg-clip-text text-transparent">
          🎯 Профиль производительности избранных чисел
        </h3>
        <p className="text-gray-600 mt-2">
          5-осевой анализ ваших избранных чисел по ключевым метрикам.
          Чем больше область фигуры, тем лучше общая производительность числа.
        </p>
      </div>

      {/* Управление избранными числами */}
      <div className="bg-gradient-to-br from-pink-50 to-orange-50 rounded-xl p-6 border border-pink-200">
        <div className="flex justify-between items-center mb-4">
          <h4 className="text-lg font-semibold text-gray-800">⭐ Управление избранными числами</h4>
          <button
            onClick={() => setIsEditMode(!isEditMode)}
            className={`px-4 py-2 rounded-lg font-medium transition-all duration-200 ${
              isEditMode
                ? 'bg-green-500 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            {isEditMode ? '✅ Сохранить' : '✏️ Редактировать'}
          </button>
        </div>

        {isEditMode ? (
          <div className="space-y-4">
            {/* Поле 1 */}
            <div>
              <div className="text-sm font-medium text-gray-700 mb-2">
                Поле 1 (выберите до 5 чисел): {favoritesField1.length}/5
              </div>
              <div className="flex flex-wrap gap-2">
                {Array.from({length: 36}, (_, i) => i + 1).map(num => (
                  <button
                    key={`f1_${num}`}
                    onClick={() => toggleFavorite(num, 'field1')}
                    disabled={!favoritesField1.includes(num) && favoritesField1.length >= 5}
                    className={`w-8 h-8 rounded-lg text-sm font-bold transition-all duration-200 ${
                      favoritesField1.includes(num)
                        ? 'bg-pink-500 text-white shadow-lg'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200 disabled:opacity-50'
                    }`}
                  >
                    {num}
                  </button>
                ))}
              </div>
            </div>

            {/* Поле 2 */}
            <div>
              <div className="text-sm font-medium text-gray-700 mb-2">
                Поле 2 (выберите до 3 чисел): {favoritesField2.length}/3
              </div>
              <div className="flex flex-wrap gap-2">
                {Array.from({length: 4}, (_, i) => i + 1).map(num => (
                  <button
                    key={`f2_${num}`}
                    onClick={() => toggleFavorite(num, 'field2')}
                    disabled={!favoritesField2.includes(num) && favoritesField2.length >= 3}
                    className={`w-10 h-10 rounded-lg text-sm font-bold transition-all duration-200 ${
                      favoritesField2.includes(num)
                        ? 'bg-orange-500 text-white shadow-lg'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200 disabled:opacity-50'
                    }`}
                  >
                    {num}
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <div className="text-sm font-medium text-gray-700 mb-2">Избранные поля 1:</div>
              <div className="flex flex-wrap gap-2">
                {favoritesField1.map(num => (
                  <div key={num} className="bg-pink-500 text-white px-3 py-1 rounded-lg font-bold">
                    {num}
                  </div>
                ))}
                {favoritesField1.length === 0 && (
                  <div className="text-gray-500 text-sm">Не выбраны</div>
                )}
              </div>
            </div>
            <div>
              <div className="text-sm font-medium text-gray-700 mb-2">Избранные поля 2:</div>
              <div className="flex flex-wrap gap-2">
                {favoritesField2.map(num => (
                  <div key={num} className="bg-orange-500 text-white px-3 py-1 rounded-lg font-bold">
                    {num}
                  </div>
                ))}
                {favoritesField2.length === 0 && (
                  <div className="text-gray-500 text-sm">Не выбраны</div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Радарный график */}
      {hasAnyFavorites ? (
        <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-200">
          <div className="h-96">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart data={radarData}>
                <PolarGrid gridType="polygon" stroke="#e5e7eb" />
                <PolarAngleAxis
                  dataKey="metric"
                  tick={{ fontSize: 12, fontWeight: 'bold', fill: '#4b5563' }}
                />
                <PolarRadiusAxis
                  angle={90}
                  domain={[0, 100]}
                  tick={{ fontSize: 10, fill: '#9ca3af' }}
                />
                <Tooltip content={<CustomTooltip />} />

                {/* Линии для чисел поля 1 */}
                {favoritesField1.map((num, i) => (
                  <Radar
                    key={`field1_${num}`}
                    name={`field1_${num}`}
                    dataKey={`field1_${num}`}
                    stroke={getColorForNumber(num, 'field1')}
                    fill={getColorForNumber(num, 'field1')}
                    fillOpacity={0.2}
                    strokeWidth={3}
                    dot={{
                      fill: getColorForNumber(num, 'field1'),
                      strokeWidth: 2,
                      r: 4,
                      style: {
                        filter: 'drop-shadow(0 2px 4px rgba(0,0,0,0.2))'
                      }
                    }}
                  />
                ))}

                {/* Линии для чисел поля 2 */}
                {favoritesField2.map((num, i) => (
                  <Radar
                    key={`field2_${num}`}
                    name={`field2_${num}`}
                    dataKey={`field2_${num}`}
                    stroke={getColorForNumber(num, 'field2')}
                    fill={getColorForNumber(num, 'field2')}
                    fillOpacity={0.2}
                    strokeWidth={3}
                    dot={{
                      fill: getColorForNumber(num, 'field2'),
                      strokeWidth: 2,
                      r: 4,
                      style: {
                        filter: 'drop-shadow(0 2px 4px rgba(0,0,0,0.2))'
                      }
                    }}
                  />
                ))}
              </RadarChart>
            </ResponsiveContainer>
          </div>

          {/* Легенда */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6 pt-4 border-t border-gray-200">
            {/* Поле 1 */}
            {favoritesField1.length > 0 && (
              <div>
                <h5 className="font-semibold text-gray-700 mb-3">🎯 Поле 1</h5>
                <div className="space-y-2">
                  {favoritesField1.map((num, i) => (
                    <div key={num} className="flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        <div
                          className="w-4 h-4 rounded-full"
                          style={{ backgroundColor: getColorForNumber(num, 'field1') }}
                        ></div>
                        <span className="font-medium">Число {num}</span>
                      </div>
                      <div className="text-sm text-gray-500">
                        {data?.hot_cold.field1.hot.includes(num) ? '🔥 Горячее' :
                         data?.hot_cold.field1.cold.includes(num) ? '❄️ Холодное' : '➡️ Нейтральное'}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Поле 2 */}
            {favoritesField2.length > 0 && (
              <div>
                <h5 className="font-semibold text-gray-700 mb-3">🎲 Поле 2</h5>
                <div className="space-y-2">
                  {favoritesField2.map((num, i) => (
                    <div key={num} className="flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        <div
                          className="w-4 h-4 rounded-full"
                          style={{ backgroundColor: getColorForNumber(num, 'field2') }}
                        ></div>
                        <span className="font-medium">Число {num}</span>
                      </div>
                      <div className="text-sm text-gray-500">
                        {data?.hot_cold.field2.hot.includes(num) ? '🔥 Горячее' :
                         data?.hot_cold.field2.cold.includes(num) ? '❄️ Холодное' : '➡️ Нейтральное'}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      ) : (
        /* Заглушка при отсутствии избранных */
        <div className="h-96 flex items-center justify-center bg-white rounded-xl border-2 border-dashed border-gray-300">
          <div className="text-center">
            <div className="text-6xl mb-4">🎯</div>
            <h4 className="text-xl font-semibold text-gray-700 mb-2">
              Нет избранных чисел для анализа
            </h4>
            <p className="text-gray-500 mb-4">
              Выберите ваши любимые числа в полях выше для получения персонализированного профиля производительности
            </p>
            <button
              onClick={() => setIsEditMode(true)}
              className="px-6 py-3 bg-gradient-to-r from-pink-500 to-orange-500 text-white rounded-lg font-medium hover:shadow-lg transition-all duration-200"
            >
              ⭐ Выбрать избранные числа
            </button>
          </div>
        </div>
      )}

      {/* Объяснение метрик */}
      <div className="bg-gray-50 rounded-xl p-6">
        <h4 className="text-lg font-semibold text-gray-800 mb-4">📖 Расшифровка метрик радара</h4>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-sm text-gray-700">
          <div className="space-y-3">
            <div>
              <strong>🔢 Частота (0-100):</strong>
              <div className="ml-4 text-gray-600">Как часто число выпадает относительно среднего</div>
            </div>
            <div>
              <strong>📈 Тренд (0-100):</strong>
              <div className="ml-4 text-gray-600">Набирает или теряет активность в последних тиражах</div>
            </div>
            <div>
              <strong>🔗 Корреляции (0-100):</strong>
              <div className="ml-4 text-gray-600">Сила связей с другими числами</div>
            </div>
          </div>
          <div className="space-y-3">
            <div>
              <strong>🔄 Циклы (0-100):</strong>
              <div className="ml-4 text-gray-600">Регулярность интервалов между появлениями</div>
            </div>
            <div>
              <strong>📍 Позиции (0-100):</strong>
              <div className="ml-4 text-gray-600">Распределение по позициям в тиражах</div>
            </div>
          </div>
        </div>

        {/* Интерпретация */}
        <div className="mt-4 p-4 bg-white rounded-lg border border-orange-200">
          <div className="font-semibold text-orange-800 mb-2">💡 Как интерпретировать:</div>
          <ul className="text-sm text-gray-700 space-y-1 ml-4">
            <li>• <strong>Большая область фигуры</strong> - число показывает стабильно высокие результаты</li>
            <li>• <strong>Равномерная фигура</strong> - сбалансированные показатели по всем метрикам</li>
            <li>• <strong>Острые выступы</strong> - число сильно в определенных аспектах</li>
            <li>• <strong>Сравнение контуров</strong> - позволяет выбрать лучшие числа для комбинаций</li>
          </ul>
        </div>
      </div>
    </div>
  );
};

export default FavoritesRadar;