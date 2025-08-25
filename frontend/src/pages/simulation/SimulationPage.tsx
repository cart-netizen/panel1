import React, { useState } from 'react';
import { useSelectedLottery, useNotificationActions } from '../../store';
import { Button } from '../../components/common/Button';
import { LOTTERY_CONFIGS } from '../../constants';
import { useMutation } from '@tanstack/react-query';

type SimulationType = 'strategy' | 'roi' | 'comparison' | 'bankroll';

export const SimulationPage: React.FC = () => {
  const selectedLottery = useSelectedLottery();
  const { showError } = useNotificationActions(); // Убираем showSuccess
  const [simulationType, setSimulationType] = useState<SimulationType>('strategy');

  // Отдельное состояние для результатов каждого типа симуляции
  const [simulationResults, setSimulationResults] = useState<{
    strategy: any;
    roi: any;
    comparison: any;
    bankroll: any;
  }>({
    strategy: null,
    roi: null,
    comparison: null,
    bankroll: null
  });

  // Мутация для симуляции стратегии
  const strategyMutation = useMutation({
    mutationFn: async (params: any) => {
      console.log('🚀 Запуск симуляции стратегии с параметрами:', params);
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${process.env.REACT_APP_API_URL}/simulation/strategy`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          lottery_type: selectedLottery,
          strategy: params.strategy || 'mixed',
          num_draws: params.num_draws || 100,
          combinations_per_draw: params.combinations_per_draw || 1,
          initial_bankroll: params.initial_bankroll || 10000,
          bet_size: params.bet_size || 100
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        console.error('❌ Ошибка ответа сервера:', errorData);
        throw new Error(errorData.detail || 'Ошибка симуляции стратегии');
      }

      const data = await response.json();
      console.log('✅ Получены данные от сервера:', data);
      console.log('🔍 Ключи ответа:', Object.keys(data));

      return data;
    },
    onSuccess: (data) => {
      console.log('✅ Симуляция стратегии успешно завершена:', data);
      console.log('🔧 Сохраняем в simulationResults.strategy');

      setSimulationResults(prev => {
        const newState = { ...prev, strategy: data };
        console.log('🔧 Новое состояние simulationResults:', newState);
        return newState;
      });

      // Убираем уведомление - результат отображается на странице
    },
    onError: (error: any) => {
      console.error('❌ Ошибка симуляции стратегии:', error);
      showError('Ошибка симуляции стратегии', error.message || 'Не удалось выполнить симуляцию');
    }
  });

  // Мутация для ROI калькулятора
  const roiMutation = useMutation({
    mutationFn: async (params: any) => {
      console.log('💰 Запуск расчёта ROI с параметрами:', params);
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${process.env.REACT_APP_API_URL}/simulation/roi`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          lottery_type: selectedLottery,
          investment: params.investment || 1000,
          ticket_price: params.ticket_price || 100,
          duration_days: params.duration_days || 30,
          strategy: params.strategy || 'mixed'
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        console.error('❌ Ошибка ответа сервера ROI:', errorData);
        throw new Error(errorData.detail || 'Ошибка расчёта ROI');
      }
      return response.json();
    },
    onSuccess: (data) => {
      console.log('✅ Расчёт ROI успешно завершён:', data);
      setSimulationResults(prev => ({ ...prev, roi: data }));
      // Убираем уведомление - результат отображается на странице
    },
    onError: (error: any) => {
      console.error('❌ Ошибка расчёта ROI:', error);
      showError('Ошибка расчёта ROI', error.message || 'Не удалось рассчитать ROI');
    }
  });

  // Мутация для сравнения методов
  const comparisonMutation = useMutation({
    mutationFn: async () => {
      console.log('⚖️ Запуск сравнения методов');
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${process.env.REACT_APP_API_URL}/simulation/compare?lottery_type=${selectedLottery}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        }
      });

      if (!response.ok) {
        const errorData = await response.json();
        console.error('❌ Ошибка ответа сервера сравнения:', errorData);
        throw new Error(errorData.detail || 'Ошибка сравнения методов');
      }
      return response.json();
    },
    onSuccess: (data) => {
      console.log('✅ Сравнение методов успешно завершено:', data);
      setSimulationResults(prev => ({ ...prev, comparison: data }));
      // Убираем уведомление - результат отображается на странице
    },
    onError: (error: any) => {
      console.error('❌ Ошибка сравнения методов:', error);
      showError('Ошибка сравнения', error.message || 'Не удалось выполнить сравнение методов');
    }
  });

  // Мутация для банкролл менеджмента
  const bankrollMutation = useMutation({
    mutationFn: async (params: any) => {
      console.log('🏦 Запуск симуляции банкролла с параметрами:', params);
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${process.env.REACT_APP_API_URL}/simulation/bankroll`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          lottery_type: selectedLottery,
          initial_bankroll: params.initial_bankroll || 10000,
          strategy: params.strategy || 'kelly',
          num_simulations: params.num_simulations || 1000,
          num_draws: params.num_draws || 100,
          risk_level: params.risk_level || 0.02
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        console.error('❌ Ошибка ответа сервера банкролла:', errorData);
        throw new Error(errorData.detail || 'Ошибка симуляции банкролла');
      }
      return response.json();
    },
    onSuccess: (data) => {
      console.log('✅ Симуляция банкролла успешно завершена:', data);
      setSimulationResults(prev => ({ ...prev, bankroll: data }));
      // Убираем уведомление - результат отображается на странице
    },
    onError: (error: any) => {
      console.error('❌ Ошибка симуляции банкролла:', error);
      showError('Ошибка банкролла', error.message || 'Не удалось выполнить симуляцию банкролла');
    }
  });

  // Функция для рендера результатов стратегии
  const renderStrategyResults = (data: any) => {
    console.log('🎨 Рендерим результаты стратегии:', data);
    console.log('🔍 Ключи объекта:', Object.keys(data));

    return (
      <div className="space-y-6 mt-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-blue-50 p-4 rounded-lg">
            <div className="text-sm text-gray-600">ROI</div>
            <div className="text-2xl font-bold text-blue-600">
              {data.roi || data.roi_percentage || 'N/A'}%
            </div>
          </div>

          <div className="bg-green-50 p-4 rounded-lg">
            <div className="text-sm text-gray-600">Процент выигрышей</div>
            <div className="text-2xl font-bold text-green-600">
              {data.win_rate || data.winRate || 'N/A'}%
            </div>
          </div>

          <div className="bg-purple-50 p-4 rounded-lg">
            <div className="text-sm text-gray-600">Финальный банкролл</div>
            <div className="text-2xl font-bold text-purple-600">
              {data.final_bankroll?.toLocaleString('ru-RU') || 'N/A'} ₽
            </div>
          </div>
        </div>

        {/* Дополнительная информация */}
        <div className="bg-gray-50 p-4 rounded-lg">
          <h4 className="font-semibold mb-2">📊 Детали симуляции</h4>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <span className="text-gray-600">Стратегия: </span>
              <span className="font-semibold">{data.strategy || 'N/A'}</span>
            </div>
            <div>
              <span className="text-gray-600">Выигрышей: </span>
              <span className="font-semibold">{data.wins || 0}</span>
            </div>
            <div>
              <span className="text-gray-600">Тиражей: </span>
              <span className="font-semibold">{data.simulated_draws || 0}</span>
            </div>
            <div>
              <span className="text-gray-600">Потрачено: </span>
              <span className="font-semibold">{data.total_spent?.toLocaleString('ru-RU') || 0} ₽</span>
            </div>
          </div>
        </div>

        {data.recommendation && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <h4 className="font-semibold text-blue-800 mb-2">💡 Рекомендация</h4>
            <p className="text-blue-700">{data.recommendation}</p>
          </div>
        )}

        {/* Отладочная информация для разработки */}
        {process.env.NODE_ENV === 'development' && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
            <h4 className="font-semibold text-yellow-800 mb-2">🔧 Данные от сервера</h4>
            <pre className="text-xs overflow-auto max-h-40">
              {JSON.stringify(data, null, 2)}
            </pre>
          </div>
        )}
      </div>
    );
  };

  // Функция для рендера результатов ROI
  const renderROIResults = (data: any) => {
    console.log('💰 Рендерим результаты ROI:', data);
    console.log('🔍 Сценарии:', data.scenarios);

    return (
      <div className="space-y-6 mt-6">
        {data.scenarios && Object.entries(data.scenarios).map(([scenario, scenarioData]: [string, any]) => (
          <div key={scenario} className="border border-gray-200 rounded-lg p-4">
            <h4 className="font-medium capitalize mb-2">{scenario}</h4>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <span className="text-gray-600">ROI: </span>
                <span className="font-semibold">{scenarioData.roi_percentage}%</span>
              </div>
              <div>
                <span className="text-gray-600">Ожидаемый выигрыш: </span>
                <span className="font-semibold">{scenarioData.expected_wins}</span>
              </div>
              <div>
                <span className="text-gray-600">Возврат: </span>
                <span className="font-semibold">{scenarioData.expected_return} ₽</span>
              </div>
              <div>
                <span className="text-gray-600">Безубыток: </span>
                <span className={`font-semibold ${scenarioData.break_even ? 'text-green-600' : 'text-red-600'}`}>
                  {scenarioData.break_even ? '✅' : '❌'}
                </span>
              </div>
            </div>
          </div>
        ))}

        {data.parameters && (
          <div className="bg-gray-50 p-4 rounded-lg">
            <h4 className="font-semibold mb-2">📊 Параметры расчёта</h4>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-gray-600">Инвестиции: </span>
                <span className="font-semibold">{data.parameters.investment} ₽</span>
              </div>
              <div>
                <span className="text-gray-600">Билетов: </span>
                <span className="font-semibold">{data.parameters.num_tickets}</span>
              </div>
              <div>
                <span className="text-gray-600">Цена билета: </span>
                <span className="font-semibold">{data.parameters.ticket_price} ₽</span>
              </div>
              <div>
                <span className="text-gray-600">Период: </span>
                <span className="font-semibold">{data.parameters.duration_days} дней</span>
              </div>
            </div>
          </div>
        )}

        {data.recommendation && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <h4 className="font-semibold text-blue-800 mb-2">💡 Рекомендация</h4>
            <p className="text-blue-700">{data.recommendation}</p>
          </div>
        )}

        {/* Отладочная информация */}
        {process.env.NODE_ENV === 'development' && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
            <h4 className="font-semibold text-yellow-800 mb-2">🔧 Данные от сервера</h4>
            <pre className="text-xs overflow-auto max-h-40">
              {JSON.stringify(data, null, 2)}
            </pre>
          </div>
        )}
      </div>
    );
  };

  // Функция для рендера результатов сравнения
  const renderComparisonResults = (data: any) => {
    console.log('⚖️ Рендерим результаты сравнения:', data);

    return (
      <div className="space-y-6 mt-6">
        {data.comparison && Array.isArray(data.comparison) && (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Метод</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Средний скор</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Win Rate</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">ROI</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Сложность</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {data.comparison.map((method: any, index: number) => (
                  <tr key={index} className={index === 0 ? 'bg-green-50' : ''}>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      {method.method}
                      {index === 0 && <span className="ml-2 text-green-600">🏆</span>}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {method.avg_score}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {method.win_rate}%
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      <span className={method.roi > 0 ? 'text-green-600' : 'text-red-600'}>
                        {method.roi}%
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {method.complexity}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {data.best_overall && (
          <div className="bg-green-50 border border-green-200 rounded-lg p-4">
            <h4 className="font-semibold text-green-800 mb-2">🏆 Лучший метод</h4>
            <p className="text-green-700">
              Рекомендуем использовать метод: <strong>{data.best_overall}</strong>
            </p>
          </div>
        )}

        {data.summary && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <h4 className="font-semibold text-blue-800 mb-2">📋 Сводка</h4>
            <p className="text-blue-700">{data.summary}</p>
          </div>
        )}

        {/* Отладочная информация */}
        {process.env.NODE_ENV === 'development' && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
            <h4 className="font-semibold text-yellow-800 mb-2">🔧 Данные от сервера</h4>
            <pre className="text-xs overflow-auto max-h-40">
              {JSON.stringify(data, null, 2)}
            </pre>
          </div>
        )}
      </div>
    );
  };

  // Функция для рендера результатов банкролла
  const renderBankrollResults = (data: any) => {
    console.log('🏦 Рендерим результаты банкролла:', data);

    return (
      <div className="space-y-6 mt-6">
        {data.results && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-green-50 p-4 rounded-lg">
              <div className="text-sm text-gray-600">Выживаемость</div>
              <div className="text-2xl font-bold text-green-600">
                {data.results.survival_rate || 'N/A'}%
              </div>
            </div>

            <div className="bg-blue-50 p-4 rounded-lg">
              <div className="text-sm text-gray-600">Прибыльность</div>
              <div className="text-2xl font-bold text-blue-600">
                {data.results.profitability_rate || 'N/A'}%
              </div>
            </div>

            <div className="bg-purple-50 p-4 rounded-lg">
              <div className="text-sm text-gray-600">Средний банкролл</div>
              <div className="text-2xl font-bold text-purple-600">
                {data.results.avg_final_bankroll?.toLocaleString('ru-RU') || 'N/A'} ₽
              </div>
            </div>
          </div>
        )}

        {data.optimal_settings && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
            <h4 className="font-semibold text-yellow-800 mb-2">⚙️ Оптимальные настройки</h4>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-gray-600">Размер ставки: </span>
                <span className="font-semibold">{data.optimal_settings.suggested_bet_size} ₽</span>
              </div>
              <div>
                <span className="text-gray-600">Уровень риска: </span>
                <span className="font-semibold">{data.optimal_settings.suggested_risk_level}%</span>
              </div>
            </div>
          </div>
        )}

        {data.recommendation && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <h4 className="font-semibold text-blue-800 mb-2">💡 Рекомендация</h4>
            <p className="text-blue-700">{data.recommendation}</p>
          </div>
        )}

        {/* Отладочная информация */}
        {process.env.NODE_ENV === 'development' && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
            <h4 className="font-semibold text-yellow-800 mb-2">🔧 Данные от сервера</h4>
            <pre className="text-xs overflow-auto max-h-40">
              {JSON.stringify(data, null, 2)}
            </pre>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            🧪 Симуляция стратегий
          </h1>
          <p className="text-gray-600">
            Лотерея: {LOTTERY_CONFIGS[selectedLottery].name}
          </p>
        </div>

        {/* Табы для типов симуляции */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 mb-6">
          <div className="border-b border-gray-200">
            <nav className="flex space-x-8 px-6" aria-label="Tabs">
              <button
                onClick={() => setSimulationType('strategy')}
                className={`py-4 px-1 border-b-2 font-medium text-sm ${
                  simulationType === 'strategy'
                    ? 'border-primary-500 text-primary-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                📈 Тестирование стратегий
              </button>
              <button
                onClick={() => setSimulationType('roi')}
                className={`py-4 px-1 border-b-2 font-medium text-sm ${
                  simulationType === 'roi'
                    ? 'border-primary-500 text-primary-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                💰 ROI калькулятор
              </button>
              <button
                onClick={() => setSimulationType('comparison')}
                className={`py-4 px-1 border-b-2 font-medium text-sm ${
                  simulationType === 'comparison'
                    ? 'border-primary-500 text-primary-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                ⚖️ Сравнение методов
              </button>
              <button
                onClick={() => setSimulationType('bankroll')}
                className={`py-4 px-1 border-b-2 font-medium text-sm ${
                  simulationType === 'bankroll'
                    ? 'border-primary-500 text-primary-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                🏦 Управление банкроллом
              </button>
            </nav>
          </div>

          <div className="p-6">
            {/* Тестирование стратегий */}
            {simulationType === 'strategy' && (
              <div className="space-y-6">
                <h2 className="text-xl font-semibold">Тестирование стратегий на исторических данных</h2>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Стратегия
                    </label>
                    <select
                      id="strategy"
                      className="w-full px-3 py-2 border border-gray-300 rounded-md"
                    >
                      <option value="random">Случайная</option>
                      <option value="hot">Горячие числа</option>
                      <option value="cold">Холодные числа</option>
                      <option value="mixed">Смешанная</option>
                      <option value="ai">AI-генерация</option>
                      <option value="martingale">Мартингейл</option>
                      <option value="fibonacci">Фибоначчи</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Количество тиражей
                    </label>
                    <input
                      type="number"
                      id="num_draws"
                      defaultValue={100}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Начальный банкролл
                    </label>
                    <input
                      type="number"
                      id="initial_bankroll"
                      defaultValue={10000}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Размер ставки
                    </label>
                    <input
                      type="number"
                      id="bet_size"
                      defaultValue={100}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md"
                    />
                  </div>
                </div>

                <Button
                  onClick={() => {
                    const strategy = (document.getElementById('strategy') as HTMLSelectElement).value;
                    const num_draws = parseInt((document.getElementById('num_draws') as HTMLInputElement).value);
                    const initial_bankroll = parseFloat((document.getElementById('initial_bankroll') as HTMLInputElement).value);
                    const bet_size = parseFloat((document.getElementById('bet_size') as HTMLInputElement).value);

                    strategyMutation.mutate({ strategy, num_draws, initial_bankroll, bet_size });
                  }}
                  loading={strategyMutation.isPending}
                  variant="primary"
                  fullWidth
                >
                  🚀 Запустить симуляцию
                </Button>

                {/* Результаты симуляции стратегии */}
                {simulationResults.strategy && simulationType === 'strategy' && (
                  <div>
                    <div className="mb-2 text-sm text-green-600">
                      ✅ Результаты стратегии готовы к отображению
                    </div>
                    {renderStrategyResults(simulationResults.strategy)}
                  </div>
                )}

                {/* Если результаты есть, но не отображаются */}
                {strategyMutation.isSuccess && simulationType === 'strategy' && !simulationResults.strategy && (
                  <div className="p-4 bg-red-100 border border-red-300 rounded">
                    <h3 className="font-semibold text-red-800">⚠️ Проблема с отображением</h3>
                    <p className="text-sm text-red-600">
                      Симуляция стратегии выполнена успешно, но результаты не отображаются.
                      Проверьте консоль браузера для деталей.
                    </p>
                  </div>
                )}
              </div>
            )}

            {/* ROI калькулятор */}
            {simulationType === 'roi' && (
              <div className="space-y-6">
                <h2 className="text-xl font-semibold">Расчёт потенциального ROI</h2>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Инвестиции (руб)
                    </label>
                    <input
                      type="number"
                      id="investment"
                      defaultValue={1000}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Цена билета (руб)
                    </label>
                    <input
                      type="number"
                      id="ticket_price"
                      defaultValue={100}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Период (дней)
                    </label>
                    <input
                      type="number"
                      id="duration_days"
                      defaultValue={30}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Стратегия
                    </label>
                    <select
                      id="roi_strategy"
                      className="w-full px-3 py-2 border border-gray-300 rounded-md"
                    >
                      <option value="mixed">Смешанная</option>
                      <option value="conservative">Консервативная</option>
                      <option value="aggressive">Агрессивная</option>
                    </select>
                  </div>
                </div>

                <Button
                  onClick={() => {
                    const investment = parseFloat((document.getElementById('investment') as HTMLInputElement).value);
                    const ticket_price = parseFloat((document.getElementById('ticket_price') as HTMLInputElement).value);
                    const duration_days = parseInt((document.getElementById('duration_days') as HTMLInputElement).value);
                    const strategy = (document.getElementById('roi_strategy') as HTMLSelectElement).value;

                    roiMutation.mutate({ investment, ticket_price, duration_days, strategy });
                  }}
                  loading={roiMutation.isPending}
                  variant="primary"
                  fullWidth
                >
                  💰 Рассчитать ROI
                </Button>

                {/* Результаты ROI */}
                {simulationResults.roi && simulationType === 'roi' && (
                  <div>
                    <div className="mb-2 text-sm text-green-600">
                      ✅ Результаты ROI готовы к отображению
                    </div>
                    {renderROIResults(simulationResults.roi)}
                  </div>
                )}

                {roiMutation.isSuccess && simulationType === 'roi' && !simulationResults.roi && (
                  <div className="p-4 bg-red-100 border border-red-300 rounded">
                    <h3 className="font-semibold text-red-800">⚠️ Проблема с отображением</h3>
                    <p className="text-sm text-red-600">
                      Расчёт ROI выполнен успешно, но результаты не отображаются.
                      Проверьте консоль браузера для деталей.
                    </p>
                  </div>
                )}
              </div>
            )}

            {/* Сравнение методов */}
            {simulationType === 'comparison' && (
              <div className="space-y-6">
                <h2 className="text-xl font-semibold">Сравнение методов генерации</h2>
                <p className="text-gray-600">
                  Комплексное сравнение всех доступных методов генерации комбинаций
                </p>

                <Button
                  onClick={() => comparisonMutation.mutate()}
                  loading={comparisonMutation.isPending}
                  variant="primary"
                  fullWidth
                >
                  ⚖️ Сравнить методы
                </Button>

                {/* Результаты сравнения */}
                {simulationResults.comparison && simulationType === 'comparison' && (
                  <div>
                    <div className="mb-2 text-sm text-green-600">
                      ✅ Результаты сравнения готовы к отображению
                    </div>
                    {renderComparisonResults(simulationResults.comparison)}
                  </div>
                )}

                {comparisonMutation.isSuccess && simulationType === 'comparison' && !simulationResults.comparison && (
                  <div className="p-4 bg-red-100 border border-red-300 rounded">
                    <h3 className="font-semibold text-red-800">⚠️ Проблема с отображением</h3>
                    <p className="text-sm text-red-600">
                      Сравнение методов выполнено успешно, но результаты не отображаются.
                      Проверьте консоль браузера для деталей.
                    </p>
                  </div>
                )}
              </div>
            )}

            {/* Управление банкроллом */}
            {simulationType === 'bankroll' && (
              <div className="space-y-6">
                <h2 className="text-xl font-semibold">Симуляция управления банкроллом</h2>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Начальный банкролл
                    </label>
                    <input
                      type="number"
                      id="bankroll_initial"
                      defaultValue={10000}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Стратегия управления
                    </label>
                    <select
                      id="bankroll_strategy"
                      className="w-full px-3 py-2 border border-gray-300 rounded-md"
                    >
                      <option value="kelly">Критерий Келли</option>
                      <option value="fixed">Фиксированная ставка</option>
                      <option value="percentage">Процент от банкролла</option>
                      <option value="martingale">Мартингейл</option>
                      <option value="fibonacci">Фибоначчи</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Количество симуляций
                    </label>
                    <input
                      type="number"
                      id="num_simulations"
                      defaultValue={1000}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Уровень риска (%)
                    </label>
                    <input
                      type="number"
                      id="risk_level"
                      defaultValue={2}
                      step="0.5"
                      min="0.5"
                      max="10"
                      className="w-full px-3 py-2 border border-gray-300 rounded-md"
                    />
                  </div>
                </div>

                <Button
                  onClick={() => {
                    const initial_bankroll = parseFloat((document.getElementById('bankroll_initial') as HTMLInputElement).value);
                    const strategy = (document.getElementById('bankroll_strategy') as HTMLSelectElement).value;
                    const num_simulations = parseInt((document.getElementById('num_simulations') as HTMLInputElement).value);
                    const risk_level = parseFloat((document.getElementById('risk_level') as HTMLInputElement).value) / 100;

                    bankrollMutation.mutate({ initial_bankroll, strategy, num_simulations, risk_level });
                  }}
                  loading={bankrollMutation.isPending}
                  variant="primary"
                  fullWidth
                >
                  🏦 Запустить симуляцию
                </Button>

                {/* Результаты банкролла */}
                {simulationResults.bankroll && simulationType === 'bankroll' && (
                  <div>
                    <div className="mb-2 text-sm text-green-600">
                      ✅ Результаты банкролла готовы к отображению
                    </div>
                    {renderBankrollResults(simulationResults.bankroll)}
                  </div>
                )}

                {bankrollMutation.isSuccess && simulationType === 'bankroll' && !simulationResults.bankroll && (
                  <div className="p-4 bg-red-100 border border-red-300 rounded">
                    <h3 className="font-semibold text-red-800">⚠️ Проблема с отображением</h3>
                    <p className="text-sm text-red-600">
                      Симуляция банкролла выполнена успешно, но результаты не отображаются.
                      Проверьте консоль браузера для деталей.
                    </p>
                  </div>
                )}
              </div>
            )}

            {/* Отладочная информация для разработки */}
            {process.env.NODE_ENV === 'development' && (
              <div className="mt-8 p-4 bg-yellow-50 border border-yellow-200 rounded">
                <h4 className="font-semibold text-yellow-800 mb-2">🔧 Отладочная информация</h4>
                <div className="text-sm text-yellow-700 space-y-1">
                  <div>Текущий тип: {simulationType}</div>
                  <div>Результаты strategy: {simulationResults.strategy ? '✅ Есть' : '❌ Нет'}</div>
                  <div>Результаты roi: {simulationResults.roi ? '✅ Есть' : '❌ Нет'}</div>
                  <div>Результаты comparison: {simulationResults.comparison ? '✅ Есть' : '❌ Нет'}</div>
                  <div>Результаты bankroll: {simulationResults.bankroll ? '✅ Есть' : '❌ Нет'}</div>
                  <div>Статус загрузки strategy: {strategyMutation.isPending ? 'Загружается' : strategyMutation.isSuccess ? 'Успех' : strategyMutation.isError ? 'Ошибка' : 'Ожидание'}</div>
                  <div>Статус загрузки roi: {roiMutation.isPending ? 'Загружается' : roiMutation.isSuccess ? 'Успех' : roiMutation.isError ? 'Ошибка' : 'Ожидание'}</div>
                  <div>Статус загрузки comparison: {comparisonMutation.isPending ? 'Загружается' : comparisonMutation.isSuccess ? 'Успех' : comparisonMutation.isError ? 'Ошибка' : 'Ожидание'}</div>
                  <div>Статус загрузки bankroll: {bankrollMutation.isPending ? 'Загружается' : bankrollMutation.isSuccess ? 'Успех' : bankrollMutation.isError ? 'Ошибка' : 'Ожидание'}</div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};