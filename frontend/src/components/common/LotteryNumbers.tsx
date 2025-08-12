import React from 'react';
import { cn } from '../../utils';

interface LotteryNumbersProps {
  numbers: number[];
  variant?: 'field1' | 'field2' | 'hot' | 'cold' | 'neutral';
  size?: 'sm' | 'md' | 'lg';
  className?: string;
  label?: string;
  onClick?: (number: number) => void;
  selectedNumbers?: number[];
  maxSelect?: number;
}

export const LotteryNumbers: React.FC<LotteryNumbersProps> = ({
  numbers,
  variant = 'neutral',
  size = 'md',
  className,
  label,
  onClick,
  selectedNumbers = [],
  maxSelect,
}) => {
  const sizeClasses = {
    sm: 'w-8 h-8 text-xs',
    md: 'w-10 h-10 text-sm',
    lg: 'w-12 h-12 text-base',
  };

  const variantClasses = {
    field1: 'lottery-number-field1',
    field2: 'lottery-number-field2',
    hot: 'lottery-number-hot',
    cold: 'lottery-number-cold',
    neutral: 'bg-gray-100 text-gray-800 border-2 border-gray-300',
  };

  const handleNumberClick = (number: number) => {
    if (!onClick) return;

    // Проверяем лимит выбора
    if (maxSelect && selectedNumbers.length >= maxSelect && !selectedNumbers.includes(number)) {
      return;
    }

    onClick(number);
  };

  const isSelected = (number: number) => selectedNumbers.includes(number);

  return (
    <div className={cn('space-y-2', className)}>
      {/* Лейбл */}
      {label && (
        <div className="flex items-center justify-between">
          <label className="text-sm font-medium text-gray-700">
            {label}
          </label>
          {maxSelect && (
            <span className="text-xs text-gray-500">
              {selectedNumbers.length}/{maxSelect}
            </span>
          )}
        </div>
      )}

      {/* Числа */}
      <div className="flex flex-wrap gap-2">
        {numbers.map((number, index) => {
          const selected = isSelected(number);
          const clickable = !!onClick;

          return (
            <button
              key={`${number}-${index}`}
              onClick={() => handleNumberClick(number)}
              disabled={!clickable}
              className={cn(
                'lottery-number',
                sizeClasses[size],
                variantClasses[variant],
                clickable && 'hover:scale-105 active:scale-95 cursor-pointer',
                !clickable && 'cursor-default',
                selected && 'ring-2 ring-primary-500 ring-offset-2 bg-primary-600 text-white border-primary-600',
                // Затемнение если достигнут лимит выбора
                maxSelect && selectedNumbers.length >= maxSelect && !selected && 'opacity-50',
                'transition-all duration-200'
              )}
              title={`Число ${number}${selected ? ' (выбрано)' : ''}`}
            >
              {number}
            </button>
          );
        })}
      </div>

      {/* Дополнительная информация */}
      {numbers.length === 0 && (
        <div className="text-center py-4 text-gray-500">
          <span className="text-2xl mb-2 block">🎯</span>
          <p className="text-sm">Нет доступных чисел</p>
        </div>
      )}
    </div>
  );
};

// Компонент для отображения комбинации (два поля)
interface CombinationDisplayProps {
  field1: number[];
  field2: number[];
  size?: 'sm' | 'md' | 'lg';
  className?: string;
  showLabels?: boolean;
  vertical?: boolean;
}

export const CombinationDisplay: React.FC<CombinationDisplayProps> = ({
  field1,
  field2,
  size = 'md',
  className,
  showLabels = true,
  vertical = false,
}) => {
  return (
    <div className={cn(
      'space-y-3',
      !vertical && 'sm:space-y-0 sm:space-x-6 sm:flex sm:items-center',
      className
    )}>
      {/* Поле 1 */}
      <LotteryNumbers
        numbers={field1}
        variant="field1"
        size={size}
        label={showLabels ? 'Поле 1' : undefined}
      />

      {/* Разделитель */}
      {!vertical && (
        <div className="hidden sm:block text-gray-400 font-bold">|</div>
      )}

      {/* Поле 2 */}
      <LotteryNumbers
        numbers={field2}
        variant="field2"
        size={size}
        label={showLabels ? 'Поле 2' : undefined}
      />
    </div>
  );
};

// Компонент для выбора чисел
interface NumberSelectorProps {
  maxNumber: number;
  selectedNumbers: number[];
  onNumberToggle: (number: number) => void;
  maxSelect: number;
  label?: string;
  variant?: 'field1' | 'field2';
  size?: 'sm' | 'md' | 'lg';
}

export const NumberSelector: React.FC<NumberSelectorProps> = ({
  maxNumber,
  selectedNumbers,
  onNumberToggle,
  maxSelect,
  label,
  variant = 'field1',
  size = 'md',
}) => {
  const allNumbers = Array.from({ length: maxNumber }, (_, i) => i + 1);

  return (
    <LotteryNumbers
      numbers={allNumbers}
      variant={variant}
      size={size}
      label={label}
      onClick={onNumberToggle}
      selectedNumbers={selectedNumbers}
      maxSelect={maxSelect}
    />
  );
};