import React, { Component, ErrorInfo, ReactNode } from 'react';
import { cn } from '../../utils';
interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

interface State {
  hasError: boolean;
  error?: Error;
  errorInfo?: ErrorInfo;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    // Обновляем состояние, чтобы показать fallback UI
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Логируем ошибку
    console.error('ErrorBoundary caught an error:', error, errorInfo);

    // Сохраняем информацию об ошибке в состоянии
    this.setState({ error, errorInfo });

    // Вызываем callback если он есть
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }

    // В продакшене отправляем ошибку в сервис мониторинга
    if (process.env.NODE_ENV === 'production') {
      // TODO: Интеграция с Sentry или другим сервисом
      console.error('Production Error:', error, errorInfo);
    }
  }

  handleReset = () => {
    this.setState({ hasError: false, error: undefined, errorInfo: undefined });
  };

  handleReload = () => {
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      // Если передан кастомный fallback, используем его
      if (this.props.fallback) {
        return this.props.fallback;
      }

      // Дефолтный UI ошибки
      return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
          <div className="max-w-md w-full bg-white rounded-xl shadow-soft p-8 text-center">
            {/* Иконка ошибки */}
            <div className="text-6xl mb-6">💥</div>

            {/* Заголовок */}
            <h1 className="text-2xl font-bold text-gray-900 mb-4">
              Что-то пошло не так
            </h1>

            {/* Описание */}
            <p className="text-gray-600 mb-6">
              Произошла неожиданная ошибка. Мы уже работаем над её исправлением.
            </p>

            {/* Детали ошибки (только в разработке) */}
            {process.env.NODE_ENV === 'development' && this.state.error && (
              <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-left">
                <h3 className="text-sm font-semibold text-red-800 mb-2">
                  Детали ошибки (dev):
                </h3>
                <pre className="text-xs text-red-700 overflow-x-auto">
                  {this.state.error.message}
                </pre>
                {this.state.errorInfo && (
                  <pre className="text-xs text-red-600 mt-2 overflow-x-auto">
                    {this.state.errorInfo.componentStack}
                  </pre>
                )}
              </div>
            )}

            {/* Действия */}
            <div className="flex flex-col sm:flex-row gap-3 justify-center">
              <button
                onClick={this.handleReset}
                className="btn-primary"
              >
                🔄 Попробовать снова
              </button>

              <button
                onClick={this.handleReload}
                className="btn-secondary"
              >
                🏠 Перезагрузить страницу
              </button>
            </div>

            {/* Ссылка на поддержку */}
            <p className="text-sm text-gray-500 mt-6">
              Если проблема повторяется, свяжитесь с{' '}
              <a
                href={`mailto:${process.env.REACT_APP_SUPPORT_EMAIL}`}
                className="text-primary-600 hover:underline"
              >
                службой поддержки
              </a>
            </p>
          </div>
        </div>
      );
    }

    // Если ошибки нет, рендерим дочерние компоненты
    return this.props.children;
  }
}

// Хук для обработки ошибок в функциональных компонентах
export const useErrorHandler = () => {
  const handleError = (error: Error, context?: string) => {
    console.error('Error handled:', error, context);

    // В продакшене отправляем в сервис мониторинга
    if (process.env.NODE_ENV === 'production') {
      // TODO: Sentry или другой сервис
    }
  };

  return { handleError };
};

// Компонент для отображения ошибок API
export const ApiErrorDisplay: React.FC<{
  error: any;
  onRetry?: () => void;
  className?: string;
}> = ({ error, onRetry, className }) => {
  const getErrorMessage = (): string => {
    if (error?.response?.data?.detail) {
      return error.response.data.detail;
    }
    if (error?.response?.data?.message) {
      return error.response.data.message;
    }
    if (error?.message) {
      return error.message;
    }
    return 'Произошла неизвестная ошибка';
  };

  const getErrorIcon = (): string => {
    if (error?.response?.status === 401) return '🔐';
    if (error?.response?.status === 403) return '🚫';
    if (error?.response?.status === 404) return '🔍';
    if (error?.response?.status >= 500) return '🔧';
    return '⚠️';
  };

  return (
    <div className={cn(
      'flex flex-col items-center justify-center p-8 text-center',
      className
    )}>
      <div className="text-4xl mb-4">{getErrorIcon()}</div>

      <h3 className="text-lg font-semibold text-gray-900 mb-2">
        Ошибка загрузки данных
      </h3>

      <p className="text-gray-600 mb-4 max-w-md">
        {getErrorMessage()}
      </p>

      {onRetry && (
        <button
          onClick={onRetry}
          className="btn-primary"
        >
          🔄 Повторить попытку
        </button>
      )}

      {/* Детали ошибки в разработке */}
      {process.env.NODE_ENV === 'development' && (
        <details className="mt-4 max-w-md">
          <summary className="text-sm text-gray-500 cursor-pointer">
            Детали ошибки (dev)
          </summary>
          <pre className="text-xs text-left bg-gray-100 p-2 rounded mt-2 overflow-x-auto">
            {JSON.stringify(error, null, 2)}
          </pre>
        </details>
      )}
    </div>
  );
};