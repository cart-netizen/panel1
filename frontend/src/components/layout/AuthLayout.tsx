import React from 'react';
import { Link } from 'react-router-dom';
import { ROUTES } from '../../constants';

interface AuthLayoutProps {
  children: React.ReactNode;
}

export const AuthLayout: React.FC<AuthLayoutProps> = ({ children }) => {
  return (
    <div className="min-h-screen flex">
      {/* Левая панель - декоративная */}
      <div className="hidden lg:flex lg:w-1/2 bg-gradient-primary items-center justify-center p-12">
        <div className="max-w-md text-white text-center">
          {/* Логотип */}
          <div className="text-8xl mb-8 animate-bounce-gentle">🎲</div>

          {/* Заголовок */}
          <h1 className="text-4xl font-bold mb-6">
            Lottery Analysis Pro
          </h1>

          {/* Описание */}
          <p className="text-xl text-blue-100 mb-8 leading-relaxed">
            Профессиональная система анализа лотерей с использованием
            машинного обучения и анализа трендов
          </p>

          {/* Особенности */}
          <div className="grid grid-cols-1 gap-4 text-left">
            <div className="flex items-center space-x-3">
              <span className="text-2xl">🧠</span>
              <div>
                <h3 className="font-semibold">AI Анализ</h3>
                <p className="text-sm text-blue-100">Random Forest + LSTM модели</p>
              </div>
            </div>

            <div className="flex items-center space-x-3">
              <span className="text-2xl">📊</span>
              <div>
                <h3 className="font-semibold">Анализ трендов</h3>
                <p className="text-sm text-blue-100">Горячие и холодные числа</p>
              </div>
            </div>

            <div className="flex items-center space-x-3">
              <span className="text-2xl">⚡</span>
              <div>
                <h3 className="font-semibold">Быстрая генерация</h3>
                <p className="text-sm text-blue-100">Результат за 1-2 секунды</p>
              </div>
            </div>

            <div className="flex items-center space-x-3">
              <span className="text-2xl">🎯</span>
              <div>
                <h3 className="font-semibold">Высокая точность</h3>
                <p className="text-sm text-blue-100">Оценка комбинаций до 99.7%</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Правая панель - форма */}
      <div className="flex-1 flex items-center justify-center p-6 lg:p-12">
        <div className="w-full max-w-md">
          {/* Мобильный логотип */}
          <div className="lg:hidden text-center mb-8">
            <div className="text-6xl mb-4">🎲</div>
            <h1 className="text-2xl font-bold text-gray-900 mb-2">
              Lottery Analysis
            </h1>
            <p className="text-gray-600">
              Профессиональный анализ лотерей
            </p>
          </div>

          {/* Основной контент */}
          <div className="bg-white rounded-2xl shadow-strong p-8 lg:p-10">
            {children}
          </div>

          {/* Дополнительные ссылки */}
          <div className="mt-8 text-center space-y-4">
            <div className="flex items-center justify-center space-x-6 text-sm">
              <Link
                to={ROUTES.HELP}
                className="text-gray-600 hover:text-primary-600 transition-colors"
              >
                ❓ Справка
              </Link>
              <Link
                to="/privacy"
                className="text-gray-600 hover:text-primary-600 transition-colors"
              >
                🔒 Конфиденциальность
              </Link>
              <Link
                to="/terms"
                className="text-gray-600 hover:text-primary-600 transition-colors"
              >
                📄 Условия
              </Link>
            </div>

            {/* Контакты поддержки */}
            <div className="text-xs text-gray-500">
              Нужна помощь?{' '}
              <a
                href={`mailto:${process.env.REACT_APP_SUPPORT_EMAIL}`}
                className="text-primary-600 hover:underline"
              >
                Свяжитесь с поддержкой
              </a>
            </div>

            {/* Версия приложения */}
            {process.env.NODE_ENV === 'development' && (
              <div className="text-xs text-gray-400">
                v{process.env.REACT_APP_VERSION} • {process.env.REACT_APP_ENVIRONMENT}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};