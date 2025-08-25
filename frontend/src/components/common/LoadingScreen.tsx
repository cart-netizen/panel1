import React from 'react';
import { cn } from '../../utils';

interface LoadingScreenProps {
  message?: string;
  size?: 'sm' | 'md' | 'lg';
  fullScreen?: boolean;
  showLogo?: boolean;
  className?: string;
}

export const LoadingScreen: React.FC<LoadingScreenProps> = ({
  message = 'Загрузка...',
  size = 'md',
  fullScreen = true,
  showLogo = true,
  className,
}) => {
  const sizeClasses = {
    sm: 'w-6 h-6',
    md: 'w-10 h-10',
    lg: 'w-16 h-16',
  };

  const containerClasses = cn(
    'flex flex-col items-center justify-center',
    fullScreen ? 'fixed inset-0 bg-white z-50' : 'p-8',
    className
  );

  return (
    <div className={containerClasses}>
      {/* Логотип */}
      {showLogo && (
        <div className="mb-6 text-center">
          <div className="text-6xl mb-2 animate-bounce-gentle">🎲</div>
          <h2 className="text-2xl font-bold text-gradient">
            Lottery Analysis
          </h2>
        </div>
      )}

      {/* Спиннер */}
      <div className="flex items-center space-x-3 mb-4">
        <div className={cn(
          sizeClasses[size],
          'border-4 border-gray-200 border-t-primary-600 rounded-full animate-spin'
        )} />
        <span className="text-gray-600 font-medium">{message}</span>
      </div>

      {/* Дополнительная информация */}
      {fullScreen && (
        <div className="text-center max-w-md">
          <p className="text-sm text-gray-500 mb-4">
            Инициализация системы анализа и машинного обучения...
          </p>

          {/* Прогресс-бар (анимированный) */}
          <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
            <div className="h-full bg-gradient-to-r from-primary-500 to-secondary-500 rounded-full animate-pulse"
                 style={{ width: '60%' }} />
          </div>
        </div>
      )}
    </div>
  );
};

// Компонент для inline загрузки
export const LoadingSpinner: React.FC<{
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}> = ({ size = 'sm', className }) => {
  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-6 h-6',
    lg: 'w-8 h-8',
  };

  return (
    <div className={cn(
      sizeClasses[size],
      'border-2 border-gray-300 border-t-primary-600 rounded-full animate-spin',
      className
    )} />
  );
};

// Скелетон для загрузки контента
export const LoadingSkeleton: React.FC<{
  lines?: number;
  className?: string;
}> = ({ lines = 3, className }) => {
  return (
    <div className={cn('space-y-3', className)}>
      {Array.from({ length: lines }, (_, i) => (
        <div
          key={i}
          className={cn(
            'h-4 bg-gray-200 rounded animate-pulse',
            i === lines - 1 ? 'w-3/4' : 'w-full'
          )}
        />
      ))}
    </div>
  );
};

// Карточка загрузки
export const LoadingCard: React.FC<{
  className?: string;
}> = ({ className }) => {
  return (
    <div className={cn('card p-6', className)}>
      <div className="space-y-4">
        {/* Заголовок */}
        <div className="h-6 bg-gray-200 rounded w-1/2 animate-pulse" />

        {/* Контент */}
        <div className="space-y-2">
          <div className="h-4 bg-gray-200 rounded animate-pulse" />
          <div className="h-4 bg-gray-200 rounded w-5/6 animate-pulse" />
          <div className="h-4 bg-gray-200 rounded w-4/6 animate-pulse" />
        </div>

        {/* Кнопки */}
        <div className="flex space-x-2 pt-4">
          <div className="h-10 bg-gray-200 rounded w-24 animate-pulse" />
          <div className="h-10 bg-gray-200 rounded w-20 animate-pulse" />
        </div>
      </div>
    </div>
  );
};