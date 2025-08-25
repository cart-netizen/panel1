import React, { useEffect } from 'react';
import { useNotifications, useAppActions } from '../../store';
import { NOTIFICATION_TYPES } from '../../constants';
import { cn } from '../../utils';

export const NotificationContainer: React.FC = () => {
  const notifications = useNotifications();
  const { removeNotification } = useAppActions();

  return (
    <div className="fixed top-4 right-4 z-50 space-y-2 max-w-sm w-full">
      {notifications.map((notification) => (
        <NotificationItem
          key={notification.id}
          notification={notification}
          onClose={() => removeNotification(notification.id)}
        />
      ))}
    </div>
  );
};

interface NotificationItemProps {
  notification: {
    id: string;
    type: 'success' | 'error' | 'warning' | 'info';
    title: string;
    message: string;
    timestamp: string;
    read: boolean;
    autoClose?: boolean;
  };
  onClose: () => void;
}

const NotificationItem: React.FC<NotificationItemProps> = ({ notification, onClose }) => {
  const config = NOTIFICATION_TYPES[notification.type];

  // Автозакрытие уведомления
  useEffect(() => {
    if (notification.autoClose && config.duration > 0) {
      const timer = setTimeout(() => {
        onClose();
      }, config.duration);

      return () => clearTimeout(timer);
    }
  }, [notification.autoClose, config.duration, onClose]);

  const colorClasses = {
    success: 'bg-green-50 border-green-200 text-green-800',
    error: 'bg-red-50 border-red-200 text-red-800',
    warning: 'bg-yellow-50 border-yellow-200 text-yellow-800',
    info: 'bg-blue-50 border-blue-200 text-blue-800',
  };

  return (
    <div className={cn(
      'max-w-sm w-full bg-white shadow-strong rounded-lg border-l-4 p-4 animate-slide-up',
      colorClasses[notification.type]
    )}>
      <div className="flex items-start justify-between">
        <div className="flex items-start space-x-3 flex-1">
          {/* Иконка */}
          <div className="flex-shrink-0 text-xl">
            {config.icon}
          </div>

          {/* Контент */}
          <div className="flex-1 min-w-0">
            <h4 className="text-sm font-semibold mb-1">
              {notification.title}
            </h4>
            <p className="text-sm opacity-90">
              {notification.message}
            </p>
          </div>
        </div>

        {/* Кнопка закрытия */}
        <button
          onClick={onClose}
          className="flex-shrink-0 ml-2 text-gray-400 hover:text-gray-600 focus:outline-none"
        >
          ✕
        </button>
      </div>

      {/* Прогресс-бар для автозакрытия */}
      {notification.autoClose && config.duration > 0 && (
        <div className="mt-3 w-full bg-gray-200 rounded-full h-1 overflow-hidden">
          <div
            className={cn(
              'h-full rounded-full transition-all ease-linear',
              notification.type === 'success' && 'bg-green-500',
              notification.type === 'error' && 'bg-red-500',
              notification.type === 'warning' && 'bg-yellow-500',
              notification.type === 'info' && 'bg-blue-500'
            )}
            style={{
              animation: `shrink ${config.duration}ms linear`,
            }}
          />
        </div>
      )}
    </div>
  );
};

// Компонент для отображения ошибок в формах
export const FormErrorNotification: React.FC<{
  error: string;
  onClose?: () => void;
  className?: string;
}> = ({ error, onClose, className }) => {
  return (
    <div className={cn(
      'flex items-center justify-between p-3 bg-red-50 border border-red-200 rounded-lg',
      className
    )}>
      <div className="flex items-center space-x-2">
        <span className="text-red-500">⚠️</span>
        <span className="text-sm text-red-700">{error}</span>
      </div>

      {onClose && (
        <button
          onClick={onClose}
          className="text-red-400 hover:text-red-600 focus:outline-none"
        >
          ✕
        </button>
      )}
    </div>
  );
};

// Компонент для отображения успешных сообщений
export const SuccessNotification: React.FC<{
  message: string;
  onClose?: () => void;
  className?: string;
}> = ({ message, onClose, className }) => {
  return (
    <div className={cn(
      'flex items-center justify-between p-3 bg-green-50 border border-green-200 rounded-lg',
      className
    )}>
      <div className="flex items-center space-x-2">
        <span className="text-green-500">✅</span>
        <span className="text-sm text-green-700">{message}</span>
      </div>

      {onClose && (
        <button
          onClick={onClose}
          className="text-green-400 hover:text-green-600 focus:outline-none"
        >
          ✕
        </button>
      )}
    </div>
  );
};

// CSS для анимации прогресс-бара
const progressBarStyles = `
@keyframes shrink {
  from { width: 100%; }
  to { width: 0%; }
}
`;

// Вставляем стили в head
if (typeof document !== 'undefined') {
  const style = document.createElement('style');
  style.textContent = progressBarStyles;
  document.head.appendChild(style);
}