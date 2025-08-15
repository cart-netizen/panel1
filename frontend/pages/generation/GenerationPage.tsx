import React, { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import {
  useSelectedLottery,
  useAppActions,
  useNotificationActions,
  // --- НОВЫЕ ХУКИ ИЗ ZUSTAND STORE ---
  useGenerationState,
  useGenerationActions
} from '../../store';
import { QUERY_KEYS, LOTTERY_CONFIGS, GENERATOR_TYPES } from '../../constants';
import { lotteryService } from '../../services/lotteryService';
import { Button, SecondaryButton } from '../../components/common/Button';
import { CombinationDisplay } from '../../components/common/LotteryNumbers';
import { LoadingSpinner } from '../../components/common/LoadingScreen';
import { ApiErrorDisplay } from '../../components/common/ErrorBoundary';
import { GenerationParams } from '../../types';
import { cn } from '../../utils';

export const GenerationPage: React.FC = () => {
  const selectedLottery = useSelectedLottery();
  const { setSelectedLottery, addRecentCombination, addFavoriteCombination } = useAppActions();
  const { showSuccess, showError } = useNotificationActions();

  // --- ПОЛУЧАЕМ СОСТОЯНИЕ И ДЕЙСТВИЯ ИЗ ГЛОБАЛЬНОГО СТОРА ZUSTAND ---
  const { isGenerating, results, error } = useGenerationState();
  const { startGeneration, setGenerationSuccess, setGenerationError } = useGenerationActions();

  const [generationParams, setGenerationParams] = useState<GenerationParams>({
    generator_type: 'rf_ranked',
    num_combinations: 3,
  });

  // Получение трендов для превью
  const {
    data: trends,
    isLoading: trendsLoading,
    refetch: refetchTrends
  } = useQuery({
    queryKey: QUERY_KEYS.lottery.trends(selectedLottery),
    queryFn: () => lotteryService.getTrends(selectedLottery),
    staleTime: 30 * 1000, // 30 секунд
    refetchInterval: 60 * 1000, // Автообновление каждую минуту
  });

  // Мутация теперь не хранит состояние, а только обновляет глобальный стор
  const generateMutation = useMutation({
    mutationFn: (params: GenerationParams) =>
      lotteryService.generateCombinations(selectedLottery, params),
    onMutate: () => {
      startGeneration(); // 1. Устанавливаем isGenerating = true в сторе
    },
    onSuccess: (data) => {
      setGenerationSuccess(data); // 2. Сохраняем успешный результат в стор

      showSuccess(
        'Генерация завершена!',
        `Создано ${data.combinations.length} комбинаций с использованием ${GENERATOR_TYPES[generationParams.generator_type].name}`
      );

      data.combinations.forEach(combo => {
        addRecentCombination(combo);
      });
    },
    onError: (error: any) => {
      setGenerationError(error); // 3. Сохраняем ошибку в стор
      const message = error.response?.data?.detail || 'Ошибка при генерации комбинаций';
      showError('Ошибка генерации', message);
    },
  });

  const handleGenerate = () => {
    generateMutation.mutate(generationParams);
  };

  // Остальные хендлеры без изменений
  const handleGeneratorChange = (type: keyof typeof GENERATOR_TYPES) => {
    setGenerationParams(prev => ({ ...prev, generator_type: type }));
  };

  const handleCombinationsCountChange = (count: number) => {
    setGenerationParams(prev => ({ ...prev, num_combinations: count }));
  };

  // Обработчик добавления в избранное
  const handleAddToFavorites = (combination: any) => {
    addFavoriteCombination(combination);
    showSuccess('Добавлено в избранное', 'Комбинация сохранена в ваших избранных');
  };

  // Обработчик копирования в буфер
  const handleCopyToClipboard = async (combination: any) => {
    try {
      const text = `Поле 1: ${combination.field1.join(', ')} | Поле 2: ${combination.field2.join(', ')}`;
      await navigator.clipboard.writeText(text);
      showSuccess('Скопировано', 'Комбинация скопирована в буфер обмена');
    } catch (error) {
      showError('Ошибка копирования', 'Не удалось скопировать комбинацию');
    }
  };

  const handleCheckModelStatus = async () => {
    try {
      const response = await fetch(`${process.env.REACT_APP_API_URL}/${selectedLottery}/model-status`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
      });

      if (response.ok) {
        const status = await response.json();
        console.log('=== СТАТУС МОДЕЛЕЙ ===', status);

        const message = `
  Лотерея: ${status.lottery_type}
  Данных: ${status.data_status.draws_count} (мин: ${status.data_status.min_required})
  RF модель: ${status.models_status.rf_trained ? '✅ Обучена' : '❌ Не обучена'}
  LSTM модель: ${status.models_status.lstm_trained ? '✅ Обучена' : '❌ Не обучена'}
        `;

        showSuccess('Статус моделей', message);
      } else {
        showError('Ошибка', 'Не удалось получить статус моделей');
      }
    } catch (error) {
      showError('Ошибка', 'Проблема с подключением к серверу');
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Заголовок */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 mb-2">
                🚀 Генерация комбинаций
              </h1>
              <p className="text-gray-600">
                Создавайте умные комбинации для {LOTTERY_CONFIGS[selectedLottery].name}
              </p>
            </div>

            {/* Селектор лотереи */}
            <div className="flex items-center space-x-4">
              <label className="text-sm font-medium text-gray-700">
                Лотерея:
              </label>
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
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
          {/* Левая панель - настройки генерации */}
          <div className="lg:col-span-1 space-y-6">
            {/* Форма настроек */}
            <div className="card">
              <div className="card-header">
                <h2 className="text-lg font-semibold text-gray-900">
                  ⚙️ Настройки генерации
                </h2>
              </div>
              <div className="card-body space-y-6">
                {/* Тип генератора */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-3">
                    Тип генератора:
                  </label>
                  <div className="space-y-2">
                    {Object.entries(GENERATOR_TYPES).map(([key, config]) => (
                      <label
                        key={key}
                        className={cn(
                          'flex items-center p-3 border rounded-lg cursor-pointer transition-colors',
                          generationParams.generator_type === key
                            ? 'border-primary-300 bg-primary-50'
                            : 'border-gray-200 hover:border-gray-300'
                        )}
                      >
                        <input
                          type="radio"
                          name="generator_type"
                          value={key}
                          checked={generationParams.generator_type === key}
                          onChange={() => handleGeneratorChange(key as any)}
                          className="sr-only"
                        />
                        <div className="flex-1">
                          <div className="flex items-center space-x-2 mb-1">
                            <span className="text-lg">{config.icon}</span>
                            <span className="text-sm font-medium">{config.name}</span>
                          </div>
                          <p className="text-xs text-gray-600">{config.description}</p>
                          <div className="flex items-center space-x-4 mt-1">
                            <span className={cn(
                              'text-xs px-2 py-1 rounded',
                              config.complexity === 'high' ? 'bg-red-100 text-red-700' :
                              config.complexity === 'medium' ? 'bg-yellow-100 text-yellow-700' :
                              'bg-green-100 text-green-700'
                            )}>
                              {config.complexity}
                            </span>
                            <span className="text-xs text-gray-500">
                              ⏱️ {config.estimatedTime}
                            </span>
                          </div>
                        </div>
                      </label>
                    ))}
                  </div>
                </div>

                {/* Количество комбинаций */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Количество комбинаций:
                  </label>
                  <div className="grid grid-cols-3 gap-2">
                    {[1, 2, 3, 5, 7, 10].map(count => (
                      <button
                        key={count}
                        onClick={() => handleCombinationsCountChange(count)}
                        className={cn(
                          'p-2 text-sm font-medium rounded border transition-colors',
                          generationParams.num_combinations === count
                            ? 'border-primary-300 bg-primary-50 text-primary-700'
                            : 'border-gray-200 hover:border-gray-300 text-gray-700'
                        )}
                      >
                        {count}
                      </button>
                    ))}
                  </div>

                  {/* Кастомное значение */}
                  <div className="mt-2">
                    <input
                      type="number"
                      min="1"
                      max="20"
                      value={generationParams.num_combinations}
                      onChange={(e) => handleCombinationsCountChange(parseInt(e.target.value) || 1)}
                      className="input-field text-sm"
                      placeholder="Или введите число"
                    />
                  </div>
                </div>

                {/* Кнопка генерации */}
                <Button
                  onClick={handleGenerate}
                  loading={isGenerating}
                  fullWidth
                  size="lg"
                  icon="🎲"
                >
                  {isGenerating
                    ? 'Генерация...'
                    : `Сгенерировать ${generationParams.num_combinations} комб.`
                  }
                </Button>

                {/* Диагностическая кнопка */}
                <SecondaryButton
                  onClick={handleCheckModelStatus}
                  fullWidth
                  size="sm"
                  icon="🔍"
                >
                  Проверить статус AI
                </SecondaryButton>

                {/* Время генерации */}
                {isGenerating && (
                  <div className="text-center">
                    <p className="text-sm text-gray-600">
                      Ожидаемое время: {GENERATOR_TYPES[generationParams.generator_type].estimatedTime}
                    </p>
                  </div>
                )}
              </div>
            </div>

            {/* Превью трендов */}
            <div className="card">
              <div className="card-header flex items-center justify-between">
                <h2 className="text-lg font-semibold text-gray-900">
                  🔥 Текущие тренды
                </h2>
                <button
                  onClick={() => refetchTrends()}
                  disabled={trendsLoading}
                  className="text-sm text-primary-600 hover:text-primary-700"
                >
                  {trendsLoading ? <LoadingSpinner size="sm" /> : '🔄'}
                </button>
              </div>
              <div className="card-body">
                {trendsLoading ? (
                  <div className="space-y-3">
                    <div className="h-4 bg-gray-200 rounded animate-pulse" />
                    <div className="h-4 bg-gray-200 rounded w-3/4 animate-pulse" />
                    <div className="h-4 bg-gray-200 rounded w-1/2 animate-pulse" />
                  </div>
                ) : trends ? (
                  <div className="space-y-4">
                    {/* Поле 1 */}
                    <div>
                      <h4 className="text-sm font-medium text-gray-700 mb-2">Поле 1:</h4>
                      <div className="space-y-2">
                        <div>
                          <span className="text-xs text-gray-500">🔥 Горячие:</span>
                          <div className="flex flex-wrap gap-1 mt-1">
                            {trends.trends?.field1?.hot_acceleration?.slice(0, 3).map((num: number) => (
                              <span key={num} className="lottery-number-hot text-xs">
                                {num}
                              </span>
                            ))}
                          </div>
                        </div>
                        <div>
                          <span className="text-xs text-gray-500">❄️ Готовые:</span>
                          <div className="flex flex-wrap gap-1 mt-1">
                            {trends.trends?.field1?.cold_reversal?.slice(0, 2).map((num: number) => (
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
                      <h4 className="text-sm font-medium text-gray-700 mb-2">Поле 2:</h4>
                      <div className="space-y-2">
                        <div>
                          <span className="text-xs text-gray-500">🔥 Горячие:</span>
                          <div className="flex flex-wrap gap-1 mt-1">
                            {trends.trends?.field2?.hot_acceleration?.slice(0, 3).map((num: number) => (
                              <span key={num} className="lottery-number-hot text-xs">
                                {num}
                              </span>
                            ))}
                          </div>
                        </div>
                        <div>
                          <span className="text-xs text-gray-500">❄️ Готовые:</span>
                          <div className="flex flex-wrap gap-1 mt-1">
                            {trends.trends?.field2?.cold_reversal?.slice(0, 2).map((num: number) => (
                              <span key={num} className="lottery-number-cold text-xs">
                                {num}
                              </span>
                            ))}
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Общая статистика */}
                    <div className="pt-3 border-t border-gray-200">
                      <div className="grid grid-cols-2 gap-2 text-xs">
                        <div>
                          <span className="text-gray-500">Сила тренда:</span>
                          <div className="font-medium">
                            П1: {trends.trends?.field1?.trend_strength?.toFixed(1) || 'N/A'}
                          </div>
                        </div>
                        <div>
                          <span className="text-gray-500">Уверенность:</span>
                          <div className="font-medium">
                            П2: {trends.trends?.field2?.confidence_score?.toFixed(1) || 'N/A'}
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-4 text-gray-500">
                    <span className="text-2xl block mb-2">📊</span>
                    <p className="text-sm">Нет данных трендов</p>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Основной блок - результаты генерации */}
          <div className="lg:col-span-3 space-y-6">
            <div className="card">
              <div className="card-header flex items-center justify-between">
                <h2 className="text-xl font-semibold text-gray-900">🎯 Результаты генерации</h2>

                {results && (
                  <div className="flex items-center space-x-2 text-sm text-gray-600">
                    <span>Сгенерировано:</span>
                    <span className="font-medium">{results.combinations.length} комб.</span>
                  </div>
                )}
              </div>

              <div className="card-body">
                {/* Состояние загрузки */}
                {isGenerating && (
                  <div className="text-center py-12">
                    <LoadingSpinner size="lg" className="mb-4" />
                    <h3 className="text-lg font-medium text-gray-900 mb-2">
                      Генерация комбинаций...
                    </h3>
                    <p className="text-gray-600 mb-4">
                      Анализируем тренды и обучаем модели
                    </p>
                    <div className="max-w-md mx-auto bg-gray-200 rounded-full h-2 overflow-hidden">
                      <div className="h-full bg-primary-600 rounded-full animate-pulse" style={{ width: '60%' }} />
                    </div>
                  </div>
                )}

                {/* Ошибка */}
                {!isGenerating && error && (
                  <ApiErrorDisplay error={error} onRetry={handleGenerate} />
                )}

                {/* Результаты */}
                {!isGenerating && results && (
                  <div className="space-y-6">
                    {/* RF предсказание */}
                    {results.rf_prediction && (
                      <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
                        <h3 className="text-lg font-semibold text-blue-800 mb-3">
                          🤖 RF Предсказание (приоритет)
                        </h3>
                        <CombinationDisplay
                          field1={results.rf_prediction.field1}
                          field2={results.rf_prediction.field2}
                          size="lg"
                        />
                        <p className="text-sm text-blue-700 mt-2">
                          {results.rf_prediction.description}
                        </p>
                      </div>
                    )}

                    {/* Сгенерированные комбинации */}
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900 mb-4">
                        🎲 Сгенерированные комбинации ({results.combinations.length})
                      </h3>

                      <div className="grid gap-4">
                        {results.combinations.map((combination: any, index: number) => (
                          <CombinationCard
                            key={index}
                            combination={combination}
                            index={index}
                            onAddToFavorites={() => handleAddToFavorites(combination)}
                            onCopyToClipboard={() => handleCopyToClipboard(combination)}
                          />
                        ))}
                      </div>
                    </div>
                  </div>
                )}

                {/* Начальное состояние */}
                {!isGenerating && !results && !error && (
                  <div className="text-center py-12">
                    <div className="text-6xl mb-4">🎲</div>
                    <h3 className="text-lg font-medium text-gray-900 mb-2">
                      Готовы к генерации
                    </h3>
                    <p className="text-gray-600 mb-6">
                      Выберите настройки и нажмите кнопку генерации
                    </p>
                    <Button onClick={handleGenerate} size="lg" icon="🚀">
                      Начать генерацию
                    </Button>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// Компонент для отображения комбинации
interface CombinationCardProps {
  combination: any;
  index: number;
  onAddToFavorites: () => void;
  onCopyToClipboard: () => void;
}

const CombinationCard: React.FC<CombinationCardProps> = ({
  combination,
  index,
  onAddToFavorites,
  onCopyToClipboard,
}) => {
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-sm font-medium text-gray-700 flex items-center space-x-2">
          <span>Комбинация #{index + 1}</span>
          {index === 0 && <span className="text-xl">🥇</span>}
          {index === 1 && <span className="text-xl">🥈</span>}
          {index === 2 && <span className="text-xl">🥉</span>}
        </h4>
        <div className="flex space-x-2">
          <SecondaryButton
            onClick={onAddToFavorites}
            size="sm"
            icon="⭐"
          >
            В избранное
          </SecondaryButton>
          <SecondaryButton
            onClick={onCopyToClipboard}
            size="sm"
            icon="📋"
          >
            Копировать
          </SecondaryButton>
        </div>
      </div>

      <div className="mb-3">
        <CombinationDisplay
          field1={combination.field1}
          field2={combination.field2}
          size="md"
          showLabels={true}
        />
      </div>

      {combination.description && (
        <div className="mt-3 p-3 bg-gray-50 rounded border border-gray-200">
          <p className="text-sm text-gray-700">{combination.description}</p>
        </div>
      )}
    </div>
  );
};