import React, { useState, useEffect } from 'react';
import { Modal } from '../common/Modal';
import { Button } from '../common/Button';
import { LOTTERY_CONFIGS } from '../../constants';
import { cn } from '../../utils';

interface FavoriteNumbersModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (numbers: { field1: number[], field2: number[] }) => void;
  lotteryType: string;
  initialNumbers?: { field1: number[], field2: number[] };
}

export const FavoriteNumbersModal: React.FC<FavoriteNumbersModalProps> = ({
  isOpen,
  onClose,
  onSave,
  lotteryType,
  initialNumbers = { field1: [], field2: [] }
}) => {
  const config = LOTTERY_CONFIGS[lotteryType as keyof typeof LOTTERY_CONFIGS];
  const [selectedNumbers, setSelectedNumbers] = useState(initialNumbers);

  useEffect(() => {
    setSelectedNumbers(initialNumbers);
  }, [initialNumbers]);

  const toggleNumber = (field: 'field1' | 'field2', num: number) => {
    setSelectedNumbers(prev => {
      const fieldNumbers = [...prev[field]];
      const index = fieldNumbers.indexOf(num);

      if (index > -1) {
        fieldNumbers.splice(index, 1);
      } else {
        // Проверяем лимит
        const maxSize = field === 'field1' ? config.field1_size * 2 : config.field2_size * 2;
        if (fieldNumbers.length < maxSize) {
          fieldNumbers.push(num);
        }
      }

      return { ...prev, [field]: fieldNumbers.sort((a, b) => a - b) };
    });
  };

  const handleSave = () => {
    onSave(selectedNumbers);
  };

  const renderNumberGrid = (field: 'field1' | 'field2') => {
    const maxNum = field === 'field1' ? config.field1_max : config.field2_max;
    const selected = selectedNumbers[field];

    return (
      <div className="grid grid-cols-10 gap-1">
        {Array.from({ length: maxNum }, (_, i) => i + 1).map(num => (
          <button
            key={num}
            onClick={() => toggleNumber(field, num)}
            className={cn(
              'w-8 h-8 text-sm rounded transition-all',
              selected.includes(num)
                ? 'bg-primary-500 text-white font-bold shadow-md transform scale-110'
                : 'bg-gray-100 hover:bg-gray-200 text-gray-700'
            )}
          >
            {num}
          </button>
        ))}
      </div>
    );
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="⭐ Избранные числа">
      <div className="space-y-6">
        {/* Описание */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
          <p className="text-sm text-blue-800">
            Выберите числа, которые будут использоваться при генерации комбинаций.
            Можно выбрать до {config.field1_size * 2} чисел для первого поля
            и до {config.field2_size * 2} для второго.
          </p>
        </div>

        {/* Поле 1 */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-medium text-gray-900">
              Поле 1 (выбрано: {selectedNumbers.field1.length})
            </h3>
            <button
              onClick={() => setSelectedNumbers(prev => ({ ...prev, field1: [] }))}
              className="text-sm text-gray-500 hover:text-gray-700"
            >
              Сбросить
            </button>
          </div>
          {renderNumberGrid('field1')}
        </div>

        {/* Поле 2 (если есть) */}
        {config.field2_max > 0 && (
          <div>
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-medium text-gray-900">
                Поле 2 (выбрано: {selectedNumbers.field2.length})
              </h3>
              <button
                onClick={() => setSelectedNumbers(prev => ({ ...prev, field2: [] }))}
                className="text-sm text-gray-500 hover:text-gray-700"
              >
                Сбросить
              </button>
            </div>
            {renderNumberGrid('field2')}
          </div>
        )}

        {/* Выбранные числа - превью */}
        {(selectedNumbers.field1.length > 0 || selectedNumbers.field2.length > 0) && (
          <div className="bg-gray-50 rounded-lg p-3">
            <h4 className="text-sm font-medium text-gray-700 mb-2">Выбранные числа:</h4>
            {selectedNumbers.field1.length > 0 && (
              <div className="mb-2">
                <span className="text-xs text-gray-500">Поле 1: </span>
                <span className="text-sm font-medium">{selectedNumbers.field1.join(', ')}</span>
              </div>
            )}
            {selectedNumbers.field2.length > 0 && (
              <div>
                <span className="text-xs text-gray-500">Поле 2: </span>
                <span className="text-sm font-medium">{selectedNumbers.field2.join(', ')}</span>
              </div>
            )}
          </div>
        )}

        {/* Кнопки действий */}
        <div className="flex space-x-3">
          <Button onClick={handleSave} variant="primary" fullWidth>
            💾 Сохранить
          </Button>
          <Button onClick={onClose} variant="secondary" fullWidth>
            Отмена
          </Button>
        </div>
      </div>
    </Modal>
  );
};