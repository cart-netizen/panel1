import React, { useState } from 'react';
import { useSelectedLottery, useNotificationActions } from '../../store';
import { Button } from '../../components/common/Button';
import { LoadingScreen } from '../../components/common/LoadingScreen';
import { LOTTERY_CONFIGS } from '../../constants';
import { useMutation, useQuery  } from '@tanstack/react-query';
import { useCallback, useEffect } from 'react';
import { cn } from '../../utils';
import XGBoostAnalysis from "../../components/analysis/XGBoostAnalysis";
import ValidationAnalysis from '../../components/analysis/ValidationAnalysis';
import GeneticAnalysis from '../../components/analysis/GeneticAnalysis';
import RLAnalysis from '../../components/analysis/RLAnalysis';
import TimeSeriesAnalysis from '../../components/analysis/TimeSeriesAnalysis';
import BayesianAnalysis from '../../components/analysis/BayesianAnalysis';
import { apiClient } from '../../services/api';
import {
  BarChart,
  TrendingUp,
  AlertCircle,
  RefreshCw,
  Download,
  Calendar,
  Brain,
  Activity,
  Cpu,
  TrendingDown,
  Calculator,
  Target
} from 'lucide-react';

interface CombinationEvaluationForm {
  field1: number[];
  field2: number[];
}

export const AnalysisPage: React.FC = () => {
  const selectedLottery = useSelectedLottery();
  const { showSuccess, showError } = useNotificationActions();
  const [analysisType, setAnalysisType] = useState<'patterns' | 'clusters' | 'evaluation' | 'xgboost' | 'validation' | 'genetic' | 'rl' | 'timeseries' | 'bayesian'>('patterns');
  // const [analysisResults, setAnalysisResults] = useState<{
  //   patterns: any;
  //   clusters: any;
  //   evaluation: any;
  // }>({
  //   patterns: null,
  //   clusters: null,
  //   evaluation: null
  // });
  const [analysisResults, setAnalysisResults] = useState<{
    patterns?: any;
    clusters?: any;
    evaluation?: any;
    xgboost?: any;
    validation?: any;
    genetic?: any;
    rl?: any;
    timeseries?: any;
    bayesian?: any;
  }>(() => {
    // Восстанавливаем результаты из localStorage при загрузке
    const savedResults = localStorage.getItem(`analysisResults_${selectedLottery}`);
    return savedResults ? JSON.parse(savedResults) : {};
  });

  // Сохраняем результаты в localStorage при изменении
  useEffect(() => {
    if (Object.keys(analysisResults).length > 0) {
      localStorage.setItem(`analysisResults_${selectedLottery}`, JSON.stringify(analysisResults));
    }
  }, [analysisResults, selectedLottery]);

  // Очистка результатов при смене лотереи
  useEffect(() => {
    const savedResults = localStorage.getItem(`analysisResults_${selectedLottery}`);
    setAnalysisResults(savedResults ? JSON.parse(savedResults) : {});
  }, [selectedLottery]);

  const [clusterMethod, setClusterMethod] = useState<'kmeans' | 'dbscan'>('kmeans');
  const [numClusters, setNumClusters] = useState(5);
  const [evaluationForm, setEvaluationForm] = useState<CombinationEvaluationForm>({
    field1: [],
    field2: []
  });

  const config = LOTTERY_CONFIGS[selectedLottery];

  // Мутация для анализа паттернов
  // const patternsMutation = useMutation({
  //   mutationFn: async () => {
  //     const response = await apiClient.get(`/${selectedLottery}/analyze-patterns`);
  //     return response.data;
  //   },
  //   onSuccess: (data) => {
  //     setAnalysisResults(prev => ({ ...prev, patterns: data }));
  //     showSuccess('Анализ завершен', 'Паттерны успешно проанализированы');
  //   },
  //   onError: (error: any) => {
  //     showError('Ошибка анализа', error.message || 'Не удалось выполнить анализ паттернов');
  //   },
  // });
  const patternsMutation = useMutation({
    mutationFn: async () => {
      const response = await apiClient.post(`/analysis/patterns`, {
        lottery_type: selectedLottery,
        depth: 100,
        include_favorites: true
      });
      return response.data;
    },
    onSuccess: (data) => {
      setAnalysisResults(prev => ({ ...prev, patterns: data }));
      // Убираем showSuccess - используем тихое обновление
    },
    onError: (error: any) => {
      console.error('Ошибка анализа паттернов:', error);
      // Показываем ошибку без всплывающего окна
      setAnalysisResults(prev => ({
        ...prev,
        patterns: {
          error: true,
          message: error.message || 'Не удалось выполнить анализ паттернов'
        }
      }));
    },
  });
  // Мутация для кластерного анализа
const clustersMutation = useMutation({
    mutationFn: async () => {
      const response = await apiClient.post(`/analysis/clusters`, {
        lottery_type: selectedLottery,
        method: clusterMethod,
        n_clusters: numClusters,
      });
      return response.data;
    },
    onSuccess: (data) => {
      setAnalysisResults(prev => ({ ...prev, clusters: data }));
      // Убираем showSuccess
    },
    onError: (error: any) => {
      console.error('Ошибка кластеризации:', error);
      setAnalysisResults(prev => ({
        ...prev,
        clusters: {
          error: true,
          message: error.message || 'Не удалось выполнить кластерный анализ'
        }
      }));
    },
  });

  // Мутация для оценки комбинации
  const evaluationMutation = useMutation({
    mutationFn: async (combination: CombinationEvaluationForm) => {
      const response = await apiClient.post(`/analysis/evaluate`, {
        lottery_type: selectedLottery,
        field1: combination.field1,
        field2: combination.field2,
        use_favorites: false
      });
      return response.data;
    },
    onSuccess: (data) => {
      setAnalysisResults(prev => ({ ...prev, evaluation: data }));
      // Убираем showSuccess
    },
    onError: (error: any) => {
      console.error('Ошибка оценки:', error);
      setAnalysisResults(prev => ({
        ...prev,
        evaluation: {
          error: true,
          message: error.message || 'Не удалось оценить комбинацию'
        }
      }));
    },
  });
  // ДОБАВИТЬ после мутаций:
  const clearResults = useCallback(() => {
    setAnalysisResults({});
    localStorage.removeItem(`analysisResults_${selectedLottery}`);
  }, [selectedLottery]);

  const handleRunAnalysis = () => {
    switch (analysisType) {
      case 'patterns':
        patternsMutation.mutate();
        break;
      case 'clusters':
        clustersMutation.mutate();
        break;
      case 'evaluation':
        if (evaluationForm.field1.length === 0 || evaluationForm.field2.length === 0) {
          showError('Ошибка', 'Пожалуйста, выберите числа для оценки');
          return;
        }
        evaluationMutation.mutate(evaluationForm);
        break;
    }
  };

  const renderPatternsResult = (data: any) => {
    if (!data) return null;

    // Обработка ошибок
    if (data.error) {
      return (
        <div className="p-4 bg-red-100 border border-red-300 rounded-lg">
          <h3 className="font-semibold text-red-800">⚠️ Ошибка анализа</h3>
          <p className="text-sm text-red-600">{data.message}</p>
          <button
            onClick={() => patternsMutation.mutate()}
            className="mt-2 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
          >
            Повторить попытку
          </button>
        </div>
      );
    }

    return (
      <div className="space-y-6">
        {/* Общая статистика */}
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <h3 className="font-semibold text-gray-800 mb-3">📊 Анализ паттернов</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-600">
                {data.analyzed_draws || 0}
              </div>
              <div className="text-sm text-gray-600">Проанализировано тиражей</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">
                {data.hot_numbers?.length || 0}
              </div>
              <div className="text-sm text-gray-600">Горячих чисел</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-red-600">
                {data.cold_numbers?.length || 0}
              </div>
              <div className="text-sm text-gray-600">Холодных чисел</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-purple-600">
                {data.anomalies_count || 0}
              </div>
              <div className="text-sm text-gray-600">Аномалий</div>
            </div>
          </div>
        </div>

        {/* Горячие числа */}
        {data.hot_cold_analysis && (
          <div className="bg-white border border-gray-200 rounded-lg p-4">
            <h4 className="font-semibold text-gray-800 mb-3">🔥 Горячие и холодные числа</h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Поле 1 */}
              <div>
                <h5 className="text-sm font-medium text-gray-700 mb-2">Поле 1:</h5>
                <div className="space-y-2">
                  <div>
                    <span className="text-sm font-medium text-red-600">Горячие:</span>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {(data.hot_cold_analysis.field1?.hot || []).map((num: number) => (
                        <span key={num} className="bg-red-100 text-red-800 px-2 py-1 rounded text-sm">
                          {num}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div>
                    <span className="text-sm font-medium text-blue-600">Холодные:</span>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {(data.hot_cold_analysis.field1?.cold || []).map((num: number) => (
                        <span key={num} className="bg-blue-100 text-blue-800 px-2 py-1 rounded text-sm">
                          {num}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              {/* Поле 2 */}
              <div>
                <h5 className="text-sm font-medium text-gray-700 mb-2">Поле 2:</h5>
                <div className="space-y-2">
                  <div>
                    <span className="text-sm font-medium text-red-600">Горячие:</span>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {(data.hot_cold_analysis.field2?.hot || []).map((num: number) => (
                        <span key={num} className="bg-red-100 text-red-800 px-2 py-1 rounded text-sm">
                          {num}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div>
                    <span className="text-sm font-medium text-blue-600">Холодные:</span>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {(data.hot_cold_analysis.field2?.cold || []).map((num: number) => (
                        <span key={num} className="bg-blue-100 text-blue-800 px-2 py-1 rounded text-sm">
                          {num}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Корреляции */}
        {data.correlations && (
          <div className="bg-white border border-gray-200 rounded-lg p-4">
            <h4 className="font-semibold text-gray-800 mb-3">🔗 Частые пары чисел</h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Поле 1 */}
              <div>
                <h5 className="text-sm font-medium text-gray-700 mb-2">Поле 1:</h5>
                <div className="space-y-1">
                  {(data.correlations.field1 || []).slice(0, 5).map((pair: any, idx: number) => (
                    <div key={idx} className="flex justify-between text-sm">
                      <span className="bg-green-100 text-green-800 px-2 py-1 rounded">
                        {pair.pair}
                      </span>
                      <span className="text-green-700">
                        {pair.frequency_percent}% ({pair.count} раз)
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Поле 2 */}
              <div>
                <h5 className="text-sm font-medium text-gray-700 mb-2">Поле 2:</h5>
                <div className="space-y-1">
                  {(data.correlations.field2 || []).slice(0, 5).map((pair: any, idx: number) => (
                    <div key={idx} className="flex justify-between text-sm">
                      <span className="bg-yellow-100 text-yellow-800 px-2 py-1 rounded">
                        {pair.pair}
                      </span>
                      <span className="text-yellow-700">
                        {pair.frequency_percent}% ({pair.count} раз)
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Аномалии */}
        {data.anomalies && (
          <div className="bg-white border border-gray-200 rounded-lg p-4">
            <h4 className="font-semibold text-gray-800 mb-3">⚠️ Статистические аномалии</h4>
            <div className="space-y-3">
              {Object.entries(data.anomalies).map(([type, anomaly]: [string, any]) => (
                <div key={type} className="bg-orange-50 p-3 rounded">
                  <div className="font-medium text-orange-800 mb-1">
                    {type === 'unusual_sums' ? 'Необычные суммы' :
                     type === 'unusual_spreads' ? 'Необычные размахи' :
                     type === 'consecutive_numbers' ? 'Последовательные числа' :
                     type === 'all_even_odd' ? 'Все четные/нечетные' : type}
                  </div>
                  <div className="text-sm text-orange-700">
                    Найдено случаев: {anomaly.count} ({anomaly.percentage?.toFixed(1)}% от всех тиражей)
                  </div>
                  {anomaly.examples && anomaly.examples.length > 0 && (
                    <div className="text-xs text-orange-600 mt-2">
                      Примеры: {anomaly.examples.slice(0, 3).map((ex: any) =>
                        `Тираж ${ex.draw}: ${ex.numbers}`
                      ).join(', ')}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Метаданные */}
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
          <h4 className="font-semibold text-gray-800 mb-3">📊 Метаданные анализа</h4>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
            <div>
              <span className="text-gray-600">Глубина анализа:</span>
              <div className="font-medium">{data.depth || 100} тиражей</div>
            </div>
            <div>
              <span className="text-gray-600">Статус:</span>
              <div className="font-medium">{data.status || 'completed'}</div>
            </div>
            <div>
              <span className="text-gray-600">Время анализа:</span>
              <div className="font-medium">
                {data.timestamp ? new Date(data.timestamp).toLocaleString() : 'N/A'}
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  };

  const renderClustersResult = (data: any) => {
    if (!data) return null;

    // Обработка ошибок
    if (data.error) {
      return (
        <div className="p-4 bg-red-100 border border-red-300 rounded-lg">
          <h3 className="font-semibold text-red-800">⚠️ Ошибка кластеризации</h3>
          <p className="text-sm text-red-600">{data.message}</p>
          <button
            onClick={() => clustersMutation.mutate()}
            className="mt-2 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
          >
            Повторить попытку
          </button>
        </div>
      );
    }

    // Обработка структуры данных от backend
    const getClustersInfo = () => {
      if (!data.clusters) return { field1Groups: {}, field2Groups: {}, totalClusters: 0 };

      // Группируем числа по кластерам для field1
      const field1Groups: { [key: number]: number[] } = {};
      if (data.clusters.field1) {
        Object.entries(data.clusters.field1).forEach(([num, clusterId]: [string, any]) => {
          const id = Number(clusterId);
          if (!field1Groups[id]) field1Groups[id] = [];
          field1Groups[id].push(Number(num));
        });
      }

      // Группируем числа по кластерам для field2
      const field2Groups: { [key: number]: number[] } = {};
      if (data.clusters.field2) {
        Object.entries(data.clusters.field2).forEach(([num, clusterId]: [string, any]) => {
          const id = Number(clusterId);
          if (!field2Groups[id]) field2Groups[id] = [];
          field2Groups[id].push(Number(num));
        });
      }

      const totalClusters = Math.max(
        Object.keys(field1Groups).length,
        Object.keys(field2Groups).length
      );

      return { field1Groups, field2Groups, totalClusters };
    };

    const { field1Groups, field2Groups, totalClusters } = getClustersInfo();

    return (
      <div className="space-y-6">
        {/* Общая статистика */}
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <h3 className="font-semibold text-gray-800 mb-3">🎯 Результаты кластеризации</h3>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-600">
                {data.n_clusters_found?.field1 || Object.keys(field1Groups).length}
              </div>
              <div className="text-sm text-gray-600">Кластеров поле 1</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-purple-600">
                {data.n_clusters_found?.field2 || Object.keys(field2Groups).length}
              </div>
              <div className="text-sm text-gray-600">Кластеров поле 2</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">{data.method || clusterMethod}</div>
              <div className="text-sm text-gray-600">Метод</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-orange-600">{totalClusters}</div>
              <div className="text-sm text-gray-600">Всего кластеров</div>
            </div>
          </div>
        </div>

        {/* Кластеры для поля 1 */}
        {Object.keys(field1Groups).length > 0 && (
          <div className="bg-white border border-gray-200 rounded-lg p-4">
            <h4 className="font-semibold text-gray-800 mb-3">🔵 Кластеры поля 1</h4>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {Object.entries(field1Groups).map(([clusterId, numbers]) => (
                <div key={`field1-${clusterId}`} className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                  <h5 className="font-medium text-blue-800 mb-2">
                    Кластер {Number(clusterId) === -1 ? 'Аномалии' : clusterId}
                  </h5>
                  <div className="flex flex-wrap gap-1">
                    {numbers.sort((a, b) => a - b).map(num => (
                      <span key={num} className="bg-blue-200 text-blue-800 px-2 py-1 rounded text-sm">
                        {num}
                      </span>
                    ))}
                  </div>
                  <div className="text-xs text-blue-600 mt-2">
                    {numbers.length} чисел
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Кластеры для поля 2 */}
        {Object.keys(field2Groups).length > 0 && (
          <div className="bg-white border border-gray-200 rounded-lg p-4">
            <h4 className="font-semibold text-gray-800 mb-3">🟣 Кластеры поля 2</h4>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {Object.entries(field2Groups).map(([clusterId, numbers]) => (
                <div key={`field2-${clusterId}`} className="bg-purple-50 border border-purple-200 rounded-lg p-3">
                  <h5 className="font-medium text-purple-800 mb-2">
                    Кластер {Number(clusterId) === -1 ? 'Аномалии' : clusterId}
                  </h5>
                  <div className="flex flex-wrap gap-1">
                    {numbers.sort((a, b) => a - b).map(num => (
                      <span key={num} className="bg-purple-200 text-purple-800 px-2 py-1 rounded text-sm">
                        {num}
                      </span>
                    ))}
                  </div>
                  <div className="text-xs text-purple-600 mt-2">
                    {numbers.length} чисел
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Интерпретация кластеров */}
        {data.interpretation && (
          <div className="bg-white border border-gray-200 rounded-lg p-4">
            <h4 className="font-semibold text-gray-800 mb-3">🧠 Интерпретация кластеров</h4>
            <div className="space-y-3">
              {Object.entries(data.interpretation).map(([key, info]: [string, any]) => (
                <div key={key} className="bg-gray-50 p-3 rounded">
                  <div className="font-medium text-gray-700 mb-1">
                    {key.includes('field1') ? '🔵 Поле 1: ' : '🟣 Поле 2: '}
                    {key.includes('outliers') ? 'Аномалии' : `Кластер ${key.split('_').pop()}`}
                  </div>
                  <div className="text-sm text-gray-600 mb-2">{info.description}</div>
                  {info.numbers && (
                    <div className="flex flex-wrap gap-1">
                      {info.numbers.map((num: number) => (
                        <span key={num} className="bg-gray-200 text-gray-700 px-2 py-1 rounded text-xs">
                          {num}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Метаданные */}
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
          <h4 className="font-semibold text-gray-800 mb-3">📊 Метаданные анализа</h4>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
            <div>
              <span className="text-gray-600">Метод:</span>
              <div className="font-medium">{data.method || clusterMethod}</div>
            </div>
            <div>
              <span className="text-gray-600">Запрошено кластеров:</span>
              <div className="font-medium">{numClusters}</div>
            </div>
            <div>
              <span className="text-gray-600">Время анализа:</span>
              <div className="font-medium">
                {data.timestamp ? new Date(data.timestamp).toLocaleString() : 'N/A'}
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  };

  const renderEvaluationResult = (data: any) => {
    if (!data) return null;

    // Обработка ошибок
    if (data.error) {
      return (
        <div className="p-4 bg-red-100 border border-red-300 rounded-lg">
          <h3 className="font-semibold text-red-800">⚠️ Ошибка оценки</h3>
          <p className="text-sm text-red-600">{data.message}</p>
          <button
            onClick={() => {
              if (evaluationForm.field1.length === 0 || evaluationForm.field2.length === 0) {
                return;
              }
              evaluationMutation.mutate(evaluationForm);
            }}
            className="mt-2 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
          >
            Повторить попытку
          </button>
        </div>
      );
    }

    return (
      <div className="space-y-6">
        {/* Общая оценка */}
        <div className="text-center py-8">
          <div className={cn(
            "text-6xl font-bold mb-4",
            data.total_score >= 80 ? "text-green-600" :
            data.total_score >= 60 ? "text-yellow-600" : "text-red-600"
          )}>
            {data.total_score || 0}/100
          </div>
          <div className="w-full bg-gray-200 rounded-full h-4 mb-4">
            <div
              className={cn(
                "h-full rounded-full transition-all duration-1000 ease-out",
                data.total_score >= 80 ? "bg-green-500" :
                data.total_score >= 60 ? "bg-yellow-500" : "bg-red-500"
              )}
              style={{ width: `${data.total_score || 0}%` }}
            />
          </div>
          <div className={cn(
            "text-lg font-medium px-4 py-2 rounded-full inline-block",
            data.total_score >= 80 ? "bg-green-100 text-green-800" :
            data.total_score >= 60 ? "bg-yellow-100 text-yellow-800" :
            "bg-red-100 text-red-800"
          )}>
            {data.total_score >= 80 ? "Отличная комбинация" :
             data.total_score >= 60 ? "Хорошая комбинация" :
             data.total_score >= 40 ? "Средняя комбинация" : "Слабая комбинация"}
          </div>
        </div>

        {/* Оцениваемая комбинация */}
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <h4 className="font-semibold text-gray-800 mb-3">🎯 Оцениваемая комбинация</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <span className="text-sm font-medium">Поле 1:</span>
              <div className="flex flex-wrap gap-1 mt-1">
                {(data.combination?.field1 || evaluationForm.field1).map((num: number) => (
                  <span key={num} className="bg-blue-100 text-blue-800 px-3 py-1 rounded text-lg font-medium">
                    {num}
                  </span>
                ))}
              </div>
            </div>
            <div>
              <span className="text-sm font-medium">Поле 2:</span>
              <div className="flex flex-wrap gap-1 mt-1">
                {(data.combination?.field2 || evaluationForm.field2).map((num: number) => (
                  <span key={num} className="bg-purple-100 text-purple-800 px-3 py-1 rounded text-lg font-medium">
                    {num}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Детальная оценка */}
        {data.analysis_factors && (
          <div className="bg-white border border-gray-200 rounded-lg p-4">
            <h4 className="font-semibold text-gray-800 mb-3">📋 Детальная оценка</h4>
            <div className="space-y-3">
              {data.analysis_factors.map((factor: any, idx: number) => (
                <div key={idx} className="flex justify-between items-center p-3 bg-gray-50 rounded">
                  <div>
                    <div className="font-medium text-gray-800">{factor.factor}</div>
                    <div className="text-sm text-gray-600">{factor.description}</div>
                  </div>
                  <div className="text-right">
                    <div className={cn(
                      "text-lg font-bold",
                      factor.score >= 8 ? "text-green-600" :
                      factor.score >= 6 ? "text-yellow-600" : "text-red-600"
                    )}>
                      {factor.score}/10
                    </div>
                    <div className="text-xs text-gray-500">
                      Вес: {factor.weight}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Рекомендации */}
        {data.suggestions && data.suggestions.length > 0 && (
          <div className="bg-white border border-gray-200 rounded-lg p-4">
            <h4 className="font-semibold text-gray-800 mb-3">💡 Рекомендации</h4>
            <div className="space-y-2">
              {data.suggestions.map((suggestion: string, idx: number) => (
                <div key={idx} className="flex items-start space-x-2">
                  <span className="text-blue-500 mt-1">•</span>
                  <span className="text-gray-700">{suggestion}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Метаданные */}
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
          <h4 className="font-semibold text-gray-800 mb-3">📊 Метаданные оценки</h4>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
            <div>
              <span className="text-gray-600">Алгоритм:</span>
              <div className="font-medium">{data.algorithm || 'AI-скоринг'}</div>
            </div>
            <div>
              <span className="text-gray-600">Версия модели:</span>
              <div className="font-medium">{data.model_version || 'v1.0'}</div>
            </div>
            <div>
              <span className="text-gray-600">Время оценки:</span>
              <div className="font-medium">
                {data.timestamp ? new Date(data.timestamp).toLocaleString() : 'N/A'}
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  };

  const isAnalysisRunning = patternsMutation.isPending || clustersMutation.isPending || evaluationMutation.isPending;

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="container mx-auto px-4 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">🔬 Детальная аналитика</h1>
          <p className="text-gray-600">
            Продвинутый анализ данных лотереи "{config.name}" с использованием ИИ и машинного обучения
          </p>
        </div>

        {/* Навигация по типам анализа */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-8">
          <h2 className="text-xl font-semibold mb-4">Выберите тип анализа</h2>

          <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
            <button
              onClick={() => setAnalysisType('patterns')}
              className={cn(
                "p-4 rounded-lg border-2 transition-all",
                analysisType === 'patterns'
                  ? "border-blue-500 bg-blue-50 text-blue-700"
                  : "border-gray-200 hover:border-gray-300"
              )}
            >
              <BarChart className="w-8 h-8 mx-auto mb-2" />
              <div className="font-medium">Анализ паттернов</div>
              <div className="text-sm text-gray-500">Горячие/холодные числа</div>
            </button>

            <button
              onClick={() => setAnalysisType('clusters')}
              className={cn(
                "p-4 rounded-lg border-2 transition-all",
                analysisType === 'clusters'
                  ? "border-green-500 bg-green-50 text-green-700"
                  : "border-gray-200 hover:border-gray-300"
              )}
            >
              <TrendingUp className="w-8 h-8 mx-auto mb-2" />
              <div className="font-medium">Кластеризация</div>
              <div className="text-sm text-gray-500">Группировка данных</div>
            </button>

            <button
              onClick={() => setAnalysisType('evaluation')}
              className={cn(
                "p-4 rounded-lg border-2 transition-all",
                analysisType === 'evaluation'
                  ? "border-purple-500 bg-purple-50 text-purple-700"
                  : "border-gray-200 hover:border-gray-300"
              )}
            >
              <AlertCircle className="w-8 h-8 mx-auto mb-2" />
              <div className="font-medium">Оценка комбинации</div>
              <div className="text-sm text-gray-500">Анализ ваших чисел</div>
            </button>

            <button
              onClick={() => setAnalysisType('xgboost')}
              className={cn(
                "p-4 rounded-lg border-2 transition-all",
                analysisType === 'xgboost'
                  ? "border-indigo-500 bg-indigo-50 text-indigo-700"
                  : "border-gray-200 hover:border-gray-300"
              )}
            >
              <Brain className="w-8 h-8 mx-auto mb-2" />
              <div className="font-medium">XGBoost</div>
              <div className="text-sm text-gray-500">SHAP объяснения</div>
            </button>

            <button
              onClick={() => setAnalysisType('validation')}
              className={cn(
                "p-4 rounded-lg border-2 transition-all",
                analysisType === 'validation'
                  ? "border-red-500 bg-red-50 text-red-700"
                  : "border-gray-200 hover:border-gray-300"
              )}
            >
              <Activity className="w-8 h-8 mx-auto mb-2" />
              <div className="font-medium">Валидация</div>
              <div className="text-sm text-gray-500">Walk-forward</div>
            </button>

            <button
              onClick={() => setAnalysisType('genetic')}
              className={cn(
                "p-4 rounded-lg border-2 transition-all",
                analysisType === 'genetic'
                  ? "border-pink-500 bg-pink-50 text-pink-700"
                  : "border-gray-200 hover:border-gray-300"
              )}
            >
              <Cpu className="w-8 h-8 mx-auto mb-2" />
              <div className="font-medium">Генетический</div>
              <div className="text-sm text-gray-500">Эволюция</div>
            </button>

            <button
              onClick={() => setAnalysisType('rl')}
              className={cn(
                "p-4 rounded-lg border-2 transition-all",
                analysisType === 'rl'
                  ? "border-orange-500 bg-orange-50 text-orange-700"
                  : "border-gray-200 hover:border-gray-300"
              )}
            >
              <Brain className="w-8 h-8 mx-auto mb-2" />
              <div className="font-medium">RL</div>
              <div className="text-sm text-gray-500">Q-Learning + DQN</div>
            </button>

            <button
              onClick={() => setAnalysisType('timeseries')}
              className={cn(
                "p-4 rounded-lg border-2 transition-all",
                analysisType === 'timeseries'
                  ? "border-teal-500 bg-teal-50 text-teal-700"
                  : "border-gray-200 hover:border-gray-300"
              )}
            >
              <TrendingDown className="w-8 h-8 mx-auto mb-2" />
              <div className="font-medium">Временные ряды</div>
              <div className="text-sm text-gray-500">ARIMA/SARIMA</div>
            </button>

            <button
              onClick={() => setAnalysisType('bayesian')}
              className={cn(
                "p-4 rounded-lg border-2 transition-all",
                analysisType === 'bayesian'
                  ? "border-violet-500 bg-violet-50 text-violet-700"
                  : "border-gray-200 hover:border-gray-300"
              )}
            >
              <Calculator className="w-8 h-8 mx-auto mb-2" />
              <div className="font-medium">Байесовский</div>
              <div className="text-sm text-gray-500">CDM модель</div>
            </button>
          </div>
                    {/* Кнопки управления */}
          <div className="flex justify-between items-center mt-4">
            <div className="text-sm text-gray-500">
              {Object.keys(analysisResults).length > 0 &&
                `Сохранено результатов: ${Object.keys(analysisResults).length}`
              }
            </div>
            <button
              onClick={clearResults}
              className="px-4 py-2 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              Очистить результаты
            </button>
          </div>
        </div>

        {/* Контент анализа */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200">
          {/* Классические типы анализа */}
          {(analysisType === 'patterns' || analysisType === 'clusters' || analysisType === 'evaluation') && (
            <div className="p-6">
              <div className="mb-6">
                <h2 className="text-xl font-semibold mb-4">
                  {analysisType === 'patterns' && '📊 Анализ паттернов'}
                  {analysisType === 'clusters' && '🎯 Кластерный анализ'}
                  {analysisType === 'evaluation' && '🔍 Оценка комбинации'}
                </h2>

                {/* Настройки для кластеризации */}
                {analysisType === 'clusters' && (
                  <div className="mb-4 p-4 bg-gray-50 rounded-lg">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium mb-2">Метод кластеризации:</label>
                        <select
                          value={clusterMethod}
                          onChange={(e) => setClusterMethod(e.target.value as 'kmeans' | 'dbscan')}
                          className="w-full p-2 border border-gray-300 rounded-md"
                        >
                          <option value="kmeans">K-Means</option>
                          <option value="dbscan">DBSCAN</option>
                        </select>
                      </div>
                      <div>
                        <label className="block text-sm font-medium mb-2">Количество кластеров:</label>
                        <input
                          type="number"
                          min="2"
                          max="10"
                          value={numClusters}
                          onChange={(e) => setNumClusters(parseInt(e.target.value))}
                          className="w-full p-2 border border-gray-300 rounded-md"
                        />
                      </div>
                    </div>
                  </div>
                )}

                {/* Форма для оценки комбинации */}
                {analysisType === 'evaluation' && (
                  <div className="mb-4 p-4 bg-gray-50 rounded-lg">
                    <h3 className="font-medium mb-3">Введите комбинацию для оценки:</h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium mb-2">
                          Поле 1 (выберите {config.field1_size} чисел из {config.field1_max}):
                        </label>
                        <div className="grid grid-cols-6 gap-1">
                          {Array.from({ length: config.field1_max }, (_, i) => i + 1).map(num => (
                            <button
                              key={num}
                              onClick={() => {
                                const newField1 = evaluationForm.field1.includes(num)
                                  ? evaluationForm.field1.filter(n => n !== num)
                                  : evaluationForm.field1.length < config.field1_size
                                    ? [...evaluationForm.field1, num]
                                    : evaluationForm.field1;
                                setEvaluationForm(prev => ({ ...prev, field1: newField1 }));
                              }}
                              className={cn(
                                "p-2 text-sm border rounded",
                                evaluationForm.field1.includes(num)
                                  ? "bg-blue-500 text-white border-blue-500"
                                  : "bg-white text-gray-700 border-gray-300 hover:border-gray-400"
                              )}
                            >
                              {num}
                            </button>
                          ))}
                        </div>
                        <div className="text-sm text-gray-600 mt-1">
                          Выбрано: {evaluationForm.field1.length}/{config.field1_size}
                        </div>
                      </div>
                      <div>
                        <label className="block text-sm font-medium mb-2">
                          Поле 2 (выберите {config.field2_size} чисел из {config.field2_max}):
                        </label>
                        <div className="grid grid-cols-6 gap-1">
                          {Array.from({ length: config.field2_max }, (_, i) => i + 1).map(num => (
                            <button
                              key={num}
                              onClick={() => {
                                const newField2 = evaluationForm.field2.includes(num)
                                  ? evaluationForm.field2.filter(n => n !== num)
                                  : evaluationForm.field2.length < config.field2_size
                                    ? [...evaluationForm.field2, num]
                                    : evaluationForm.field2;
                                setEvaluationForm(prev => ({ ...prev, field2: newField2 }));
                              }}
                              className={cn(
                                "p-2 text-sm border rounded",
                                evaluationForm.field2.includes(num)
                                  ? "bg-purple-500 text-white border-purple-500"
                                  : "bg-white text-gray-700 border-gray-300 hover:border-gray-400"
                              )}
                            >
                              {num}
                            </button>
                          ))}
                        </div>
                        <div className="text-sm text-gray-600 mt-1">
                          Выбрано: {evaluationForm.field2.length}/{config.field2_size}
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                <div className="text-center">
                  <Button
                    onClick={handleRunAnalysis}
                    disabled={isAnalysisRunning}
                    icon={isAnalysisRunning ? <RefreshCw className="animate-spin" /> : <Target />}
                    size="lg"
                  >
                    {isAnalysisRunning ?
                      'Анализируем...' : 'Запустить анализ паттернов'}
                  </Button>
                </div>

                {/* Результаты анализа паттернов */}
                {analysisResults.patterns && analysisType === 'patterns' && (
                  <div>
                    <div className="mb-2 text-sm text-green-600"></div>
                    {renderPatternsResult(analysisResults.patterns)}
                  </div>
                )}

                {/* Результаты кластеризации */}
                {analysisResults.clusters && analysisType === 'clusters' && (
                  <div>
                    <div className="mb-2 text-sm text-green-600"></div>
                    {renderClustersResult(analysisResults.clusters)}
                  </div>
                )}

                {/* Результаты оценки */}
                {analysisResults.evaluation && analysisType === 'evaluation' && (
                  <div>
                    <div className="mb-2 text-sm text-green-600"></div>
                    {renderEvaluationResult(analysisResults.evaluation)}
                  </div>
                )}

                {/* Если нет результатов после выполнения */}
                {patternsMutation.isSuccess && !analysisResults.patterns && (
                  <div className="p-4 bg-red-100 border border-red-300 rounded">
                    <h3 className="font-semibold text-red-800">⚠️ Проблема с отображением</h3>
                    <p className="text-sm text-red-600">
                      Анализ выполнен успешно, но результаты не отображаются.
                      Проверьте консоль браузера.
                    </p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Продвинутые модули анализа */}
          {analysisType === 'xgboost' && (
            <XGBoostAnalysis />
          )}

          {analysisType === 'validation' && (
            <ValidationAnalysis lotteryType={selectedLottery} />
          )}

          {analysisType === 'genetic' && (
            <GeneticAnalysis lotteryType={selectedLottery} />
          )}

          {analysisType === 'rl' && (
            <RLAnalysis lotteryType={selectedLottery} />
          )}

          {analysisType === 'timeseries' && (
            <TimeSeriesAnalysis lotteryType={selectedLottery} />
          )}

          {analysisType === 'bayesian' && (
            <BayesianAnalysis lotteryType={selectedLottery} />
          )}
        </div>
      </div>
    </div>
  );
};