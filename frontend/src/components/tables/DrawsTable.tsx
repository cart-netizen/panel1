// frontend/src/components/tables/DrawsTable.tsx
import React from 'react';
import { cn } from '../../utils';

interface DrawsTableProps {
  draws: Array<{
    draw_number?: number;
    Тираж?: number;
    draw_date?: string;
    Дата?: string;
    field1_numbers?: number[];
    field2_numbers?: number[];
    Числа_Поле1_list?: number[];
    Числа_Поле2_list?: number[];
  }>;
  maxNumbers: {
    field1: number;
    field2: number;
  };
}

export const DrawsTable: React.FC<DrawsTableProps> = ({ draws, maxNumbers }) => {
  if (!draws || draws.length === 0) {
    return (
      <div className="card">
        <div className="card-body text-center text-gray-500">
          <p>Нет данных для отображения таблицы</p>
        </div>
      </div>
    );
  }

  const getCellClass = (number: number, numbers: number[]): string => {
    if (numbers.includes(number)) {
      return 'bg-blue-500 text-white font-semibold';
    }
    return '';
  };

  // Рассчитываем размер ячеек в зависимости от количества чисел(масштаб)
  const cellSize = maxNumbers.field1 > 30 ? 'w-3 h-3 text-[8px]' :
                   maxNumbers.field1 > 20 ? 'w-2 h-2 text-[7px]' :
                   'w-3 h-3 text-[9px]';

  return (
    <div className="card">
      <div className="card-header">
        <h2 className="text-lg font-semibold text-gray-900">
          📋 Таблица выпавших номеров (последние 20 тиражей)
        </h2>
      </div>
      <div className="card-body p-2 sm:p-4">
        <div className="overflow-x-auto">
          <table className="w-full text-[9px] sm:text-xs">
            <thead>
              <tr className="border-b bg-gray-50">
                <th className="px-1 py-1 text-left font-medium text-gray-700 text-[10px]" rowSpan={2}>№</th>
                <th className="px-1 py-1 text-left font-medium text-gray-700 text-[10px]" rowSpan={2}>Дата</th>
                <th className="px-1 py-1 text-center font-medium text-gray-700 text-[10px]" colSpan={maxNumbers.field1}>
                  Поле 1
                </th>
                {maxNumbers.field2 > 0 && (
                  <th className="px-1 py-1 text-center font-medium text-gray-700 text-[10px] bg-gray-100" colSpan={maxNumbers.field2}>
                    Поле 2
                  </th>
                )}
              </tr>
              <tr className="border-b bg-gray-50">
                {/* Числа поля 1 */}
                {Array.from({ length: maxNumbers.field1 }, (_, i) => i + 1).map(num => (
                  <th key={`h1-${num}`} className="px-0.5 py-0.5 text-center text-gray-600 text-[9px]">
                    {num}
                  </th>
                ))}
                {/* Числа поля 2 */}
                {maxNumbers.field2 > 0 && Array.from({ length: maxNumbers.field2 }, (_, i) => i + 1).map(num => (
                  <th key={`h2-${num}`} className="px-0.5 py-0.5 text-center text-gray-600 text-[9px] bg-gray-100">
                    {num}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {draws.slice(0, 20).map((draw, idx) => {
                const drawNumber = draw.draw_number || draw.Тираж || 0;
                const drawDate = draw.draw_date || draw.Дата || '';
                const field1Numbers = draw.field1_numbers || draw.Числа_Поле1_list || [];
                const field2Numbers = draw.field2_numbers || draw.Числа_Поле2_list || [];

                return (
                  <tr key={`${drawNumber}-${idx}`} className={cn(
                    'border-b',
                    idx % 2 === 0 ? 'bg-white' : 'bg-gray-50/50'
                  )}>
                    <td className="px-1 py-0.5 font-medium text-[9px]">{drawNumber}</td>
                    <td className="px-1 py-0.5 text-gray-600 text-[9px]">
                      {new Date(drawDate).toLocaleDateString('ru-RU', {
                        day: '2-digit',
                        month: '2-digit'
                      })}
                    </td>

                    {/* Числа поля 1 */}
                    {Array.from({ length: maxNumbers.field1 }, (_, i) => i + 1).map(num => (
                      <td key={`c1-${num}`} className="px-0.5 py-0.5">
                        <div className={cn(
                          cellSize,
                          'rounded flex items-center justify-center',
                          getCellClass(num, field1Numbers),
                          !field1Numbers.includes(num) && 'text-gray-300'
                        )}>
                          {field1Numbers.includes(num) ? num : '·'}
                        </div>
                      </td>
                    ))}

                    {/* Числа поля 2 с серым фоном */}
                    {maxNumbers.field2 > 0 && Array.from({ length: maxNumbers.field2 }, (_, i) => i + 1).map(num => (
                      <td key={`c2-${num}`} className={cn(
                        "px-0.5 py-0.5",
                        idx % 2 === 0 ? 'bg-gray-100/70' : 'bg-gray-100'
                      )}>
                        <div className={cn(
                          cellSize,
                          'rounded flex items-center justify-center',
                          getCellClass(num, field2Numbers),
                          !field2Numbers.includes(num) && 'text-gray-400'
                        )}>
                          {field2Numbers.includes(num) ? num : '·'}
                        </div>
                      </td>
                    ))}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Легенда */}
        <div className="mt-3 flex items-center justify-center space-x-4 text-[10px] text-gray-600">
          <div className="flex items-center space-x-1">
            <div className="w-3 h-3 bg-blue-500 rounded"></div>
            <span>Выпавшее</span>
          </div>
          <div className="flex items-center space-x-1">
            <div className="w-3 h-3 bg-white border border-gray-300 rounded"></div>
            <span>Не выпало</span>
          </div>
          <div className="flex items-center space-x-1">
            <div className="w-3 h-3 bg-gray-100 rounded"></div>
            <span>Поле 2</span>
          </div>
        </div>
      </div>
    </div>
  );
};