import React from 'react';
import { cn } from '../../utils';

interface StatsCardProps {
  title: string;
  value: string | number;
  icon?: string | React.ReactNode;
  color?: 'blue' | 'green' | 'purple' | 'yellow' | 'red' | 'gray';
  trend?: {
    value: number;
    direction: 'up' | 'down' | 'neutral';
    label?: string;
  };
  description?: string;
  onClick?: () => void;
  loading?: boolean;
  className?: string;
  actionButton?: React.ReactNode;
}

export const StatsCard: React.FC<StatsCardProps> = ({
  title,
  value,
  icon,
  color = 'blue',
  trend,
  description,
  onClick,
  loading = false,
  className,
  actionButton,
}) => {
  const colorClasses = {
    blue: {
      icon: 'text-blue-600 bg-blue-100',
      trend: {
        up: 'text-blue-600 bg-blue-50',
        down: 'text-blue-600 bg-blue-50',
        neutral: 'text-blue-600 bg-blue-50',
      },
    },
    green: {
      icon: 'text-green-600 bg-green-100',
      trend: {
        up: 'text-green-600 bg-green-50',
        down: 'text-green-600 bg-green-50',
        neutral: 'text-green-600 bg-green-50',
      },
    },
    purple: {
      icon: 'text-purple-600 bg-purple-100',
      trend: {
        up: 'text-purple-600 bg-purple-50',
        down: 'text-purple-600 bg-purple-50',
        neutral: 'text-purple-600 bg-purple-50',
      },
    },
    yellow: {
      icon: 'text-yellow-600 bg-yellow-100',
      trend: {
        up: 'text-yellow-600 bg-yellow-50',
        down: 'text-yellow-600 bg-yellow-50',
        neutral: 'text-yellow-600 bg-yellow-50',
      },
    },
    red: {
      icon: 'text-red-600 bg-red-100',
      trend: {
        up: 'text-red-600 bg-red-50',
        down: 'text-red-600 bg-red-50',
        neutral: 'text-red-600 bg-red-50',
      },
    },
    gray: {
      icon: 'text-gray-600 bg-gray-100',
      trend: {
        up: 'text-gray-600 bg-gray-50',
        down: 'text-gray-600 bg-gray-50',
        neutral: 'text-gray-600 bg-gray-50',
      },
    },
  };

  const getTrendIcon = () => {
    if (!trend) return null;

    switch (trend.direction) {
      case 'up':
        return '📈';
      case 'down':
        return '📉';
      default:
        return '➡️';
    }
  };

  const getTrendColor = () => {
    if (!trend) return '';

    switch (trend.direction) {
      case 'up':
        return 'text-green-600';
      case 'down':
        return 'text-red-600';
      default:
        return 'text-gray-600';
    }
  };

  return (
    <div
      className={cn(
        'stats-card',
        onClick && 'cursor-pointer hover:shadow-medium',
        loading && 'animate-pulse',
        className
      )}
      onClick={onClick}
    >
      <div className="flex items-start justify-between">
        {/* Левая часть - контент */}
        <div className="flex-1">
          {/* Заголовок */}
          <p className="stats-label mb-1">{title}</p>

          {/* Значение */}
          <div className="flex items-baseline space-x-2">
            <p className={cn(
              'stats-value',
              loading && 'bg-gray-200 rounded w-20 h-8'
            )}>
              {loading ? '' : value}
            </p>

            {/* Тренд */}
            {trend && !loading && (
              <div className={cn(
                'flex items-center space-x-1 px-2 py-1 rounded-full text-xs font-medium',
                colorClasses[color].trend[trend.direction]
              )}>
                <span>{getTrendIcon()}</span>
                <span className={getTrendColor()}>
                  {trend.value > 0 ? '+' : ''}{trend.value}
                  {trend.label && `${trend.label}`}
                </span>
              </div>
            )}
          </div>

          {/* Описание */}
          {description && !loading && (
            <p className="text-xs text-gray-500 mt-1">{description}</p>
          )}

          {actionButton && (
            <div className="mt-3">
              {actionButton}
            </div>
          )}
        </div>

        {/* Правая часть - иконка */}
        {icon && (
          <div className={cn(
            'flex-shrink-0 w-12 h-12 rounded-lg flex items-center justify-center',
            colorClasses[color].icon,
            loading && 'animate-pulse'
          )}>
            {typeof icon === 'string' ? (
              <span className="text-2xl">{icon}</span>
            ) : (
              icon
            )}
          </div>
        )}
      </div>
    </div>
  );
};

// Компонент для мини-статистики
export const MiniStatsCard: React.FC<{
  label: string;
  value: string | number;
  icon?: string;
  color?: string;
  className?: string;
}> = ({ label, value, icon, color = 'text-gray-600', className }) => {
  return (
    <div className={cn(
      'flex items-center space-x-3 p-3 bg-white rounded-lg border border-gray-200',
      className
    )}>
      {icon && (
        <div className="flex-shrink-0">
          <span className="text-xl">{icon}</span>
        </div>
      )}
      <div className="flex-1 min-w-0">
        <p className="text-xs text-gray-500 truncate">{label}</p>
        <p className={cn('text-lg font-semibold', color)}>{value}</p>
      </div>
    </div>
  );
};

// Скелетон для статистических карточек
export const StatsCardSkeleton: React.FC<{ className?: string }> = ({ className }) => {
  return (
    <div className={cn('stats-card', className)}>
      <div className="flex items-start justify-between">
        <div className="flex-1 space-y-3">
          <div className="h-4 bg-gray-200 rounded w-3/4 animate-pulse" />
          <div className="h-8 bg-gray-200 rounded w-1/2 animate-pulse" />
          <div className="h-3 bg-gray-200 rounded w-2/3 animate-pulse" />
        </div>
        <div className="w-12 h-12 bg-gray-200 rounded-lg animate-pulse" />
      </div>
    </div>
  );
};