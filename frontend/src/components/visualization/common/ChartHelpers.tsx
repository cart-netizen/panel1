import React from 'react';

// Интерфейсы для данных паттернов (совместимы с API проекта)
export interface PatternData {
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
  cycles_field1?: Array<{ number: number, last_seen_ago: number, avg_cycle: number, is_overdue: boolean }>;
  cycles_field2?: Array<{ number: number, last_seen_ago: number, avg_cycle: number, is_overdue: boolean }>;
}

export interface PatternVisualizationProps {
  data?: PatternData;
}

// Утилитные функции для работы с цветами
export const getHeatmapColor = (frequency: number, maxFreq: number, minFreq: number, options?: {
  startColor?: { r: number, g: number, b: number };
  endColor?: { r: number, g: number, b: number };
}): string => {
  if (maxFreq === minFreq) return 'rgb(100, 100, 100)'; // Серый если нет разброса

  // Нормализуем частоту от 0 до 1
  const normalized = (frequency - minFreq) / (maxFreq - minFreq);

  // Цвета по умолчанию: темно-синий -> ярко-красный
  const startColor = options?.startColor || { r: 30, g: 58, b: 138 };
  const endColor = options?.endColor || { r: 220, g: 38, b: 38 };

  const r = Math.round(startColor.r + (endColor.r - startColor.r) * normalized);
  const g = Math.round(startColor.g + (endColor.g - startColor.g) * normalized);
  const b = Math.round(startColor.b + (endColor.b - startColor.b) * normalized);

  return `rgb(${r}, ${g}, ${b})`;
};

// Получение цвета для линий графика
export const getLineColor = (index: number): string => {
  const colors = [
    '#ef4444', // красный
    '#f97316', // оранжевый
    '#eab308', // желтый
    '#22c55e', // зеленый
    '#06b6d4', // голубой
    '#8b5cf6', // фиолетовый
    '#ec4899', // розовый
    '#14b8a6', // бирюзовый
  ];
  return colors[index % colors.length];
};

// Получение статуса числа
export const getNumberStatus = (num: number, data?: PatternData, field: 'field1' | 'field2' = 'field1'): {
  isHot: boolean;
  isCold: boolean;
  isOverdue: boolean;
  status: 'hot' | 'cold' | 'overdue' | 'neutral';
  statusText: string;
} => {
  const isHot = data?.hot_cold[field].hot.includes(num) || false;
  const isCold = data?.hot_cold[field].cold.includes(num) || false;
  const cycleField = field === 'field1' ? data?.cycles_field1 : data?.cycles_field2;
  const isOverdue = cycleField?.find(c => c.number === num)?.is_overdue || false;

  let status: 'hot' | 'cold' | 'overdue' | 'neutral' = 'neutral';
  let statusText = 'Нейтральное';

  if (isOverdue) {
    status = 'overdue';
    statusText = 'Просрочено';
  } else if (isHot) {
    status = 'hot';
    statusText = 'Горячее';
  } else if (isCold) {
    status = 'cold';
    statusText = 'Холодное';
  }

  return { isHot, isCold, isOverdue, status, statusText };
};

// Адаптер данных: преобразует ответ API в формат для графиков
export const adaptApiDataToPatterns = (apiResponse: any): PatternData => {
  return {
    hot_cold: {
      field1: {
        hot: apiResponse.hot_cold?.field1?.hot || [],
        cold: apiResponse.hot_cold?.field1?.cold || []
      },
      field2: {
        hot: apiResponse.hot_cold?.field2?.hot || [],
        cold: apiResponse.hot_cold?.field2?.cold || []
      }
    },
    correlations: {
      field1: apiResponse.correlations_field1 || [],
      field2: apiResponse.correlations_field2 || []
    },
    cycles_field1: apiResponse.cycles_field1 || [],
    cycles_field2: apiResponse.cycles_field2 || [],
    favorites_analysis: apiResponse.favorites_analysis
  };
};

// Генерация mock данных для тестирования
export const generateMockPatternData = (): PatternData => ({
  hot_cold: {
    field1: {
      hot: [7, 12, 19, 3, 15],
      cold: [1, 8, 20, 11, 16]
    },
    field2: {
      hot: [2, 4],
      cold: [1, 3]
    }
  },
  correlations: {
    field1: [
      { pair: "7-12", frequency_percent: 25.3, count: 12 },
      { pair: "19-3", frequency_percent: 18.7, count: 9 },
      { pair: "15-7", frequency_percent: 16.2, count: 8 }
    ],
    field2: [
      { pair: "2-4", frequency_percent: 32.1, count: 15 }
    ]
  },
  cycles_field1: [
    { number: 7, last_seen_ago: 5, avg_cycle: 8, is_overdue: false },
    { number: 12, last_seen_ago: 15, avg_cycle: 10, is_overdue: true }
  ],
  cycles_field2: [
    { number: 2, last_seen_ago: 3, avg_cycle: 6, is_overdue: false }
  ],
  favorites_analysis: {
    field1: {
      "7": { frequency: 15, percentage: 25.2 },
      "12": { frequency: 8, percentage: 13.4 }
    },
    field2: {
      "2": { frequency: 12, percentage: 20.1 }
    }
  }
});

// Компонент информационной подсказки
export const InfoTooltip: React.FC<{ text: string }> = ({ text }) => {
  const [isVisible, setIsVisible] = React.useState(false);

  return (
    <div className="relative inline-block ml-2">
      <span
        className="inline-flex items-center justify-center w-4 h-4 text-xs font-bold text-white bg-blue-500 rounded-full cursor-help hover:bg-blue-600 transition-all duration-200 hover:scale-110"
        onMouseEnter={() => setIsVisible(true)}
        onMouseLeave={() => setIsVisible(false)}
      >
        ?
      </span>
      {isVisible && (
        <div className="absolute bottom-6 left-1/2 transform -translate-x-1/2 w-64 p-3 text-sm text-white bg-gray-800 rounded-lg shadow-xl z-50 animate-fade-in">
          <div className="relative">
            {text}
            <div className="absolute top-full left-1/2 transform -translate-x-1/2 w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-gray-800"></div>
          </div>
        </div>
      )}
    </div>
  );
};

// Утилита для анимации появления элементов
export const useAnimationTrigger = () => {
  const [trigger, setTrigger] = React.useState(false);

  React.useEffect(() => {
    setTrigger(true);
  }, []);

  return trigger;
};

// CSS стили для анимаций (для включения в компоненты)
export const animationStyles = `
  @keyframes fadeInScale {
    from { opacity: 0; transform: scale(0.8); }
    to { opacity: 1; transform: scale(1); }
  }
  
  @keyframes bounceIn {
    0% { opacity: 0; transform: scale(0.3); }
    50% { transform: scale(1.1); }
    100% { opacity: 1; transform: scale(1); }
  }
  
  @keyframes animate-fade-in {
    from { opacity: 0; transform: translateY(-10px); }
    to { opacity: 1; transform: translateY(0); }
  }
  
  .animate-fade-in {
    animation: animate-fade-in 0.3s ease-out;
  }
  
  .animate-fade-in-scale {
    animation: fadeInScale 0.8s ease-out both;
  }
  
  .animate-bounce-in {
    animation: bounceIn 0.8s ease-out;
  }
  
  .gradient-bg {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  }
  
  .glass-effect {
    background: rgba(255, 255, 255, 0.1);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255, 255, 255, 0.2);
  }
`;

// Хук для работы с избранными числами
export const useFavoriteNumbers = () => {
  const [favorites, setFavorites] = React.useState<{
    field1: number[];
    field2: number[];
  }>({
    field1: [],
    field2: []
  });

  const addFavorite = (number: number, field: 'field1' | 'field2') => {
    setFavorites(prev => {
      const maxAllowed = field === 'field1' ? 5 : 3;
      const currentFavorites = prev[field];

      if (currentFavorites.includes(number) || currentFavorites.length >= maxAllowed) {
        return prev;
      }

      return {
        ...prev,
        [field]: [...currentFavorites, number]
      };
    });
  };

  const removeFavorite = (number: number, field: 'field1' | 'field2') => {
    setFavorites(prev => ({
      ...prev,
      [field]: prev[field].filter(n => n !== number)
    }));
  };

  const toggleFavorite = (number: number, field: 'field1' | 'field2') => {
    const currentFavorites = favorites[field];
    if (currentFavorites.includes(number)) {
      removeFavorite(number, field);
    } else {
      addFavorite(number, field);
    }
  };

  const isFavorite = (number: number, field: 'field1' | 'field2'): boolean => {
    return favorites[field].includes(number);
  };

  return {
    favorites,
    addFavorite,
    removeFavorite,
    toggleFavorite,
    isFavorite,
    setFavorites
  };
};