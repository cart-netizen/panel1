import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';

// Глобальные стили
import './index.css';

// Проверяем поддержку современных браузеров
const checkBrowserSupport = (): boolean => {
  // Проверяем поддержку необходимых API
  const required = [
    'fetch',
    'Promise',
    'localStorage',
    'sessionStorage',
    'addEventListener'
  ];

  return required.every(feature => feature in window);
};

// Инициализация приложения
const initializeApp = () => {
  const root = ReactDOM.createRoot(
    document.getElementById('root') as HTMLElement
  );

  // Проверяем поддержку браузера
  if (!checkBrowserSupport()) {
    root.render(
      <div className="min-h-screen flex items-center justify-center bg-gray-50 p-4">
        <div className="max-w-md text-center">
          <div className="text-6xl mb-4">⚠️</div>
          <h1 className="text-2xl font-bold text-gray-900 mb-4">
            Браузер не поддерживается
          </h1>
          <p className="text-gray-600 mb-6">
            Для работы приложения требуется современный браузер.
            Пожалуйста, обновите ваш браузер или используйте:
          </p>
          <div className="space-y-2 text-sm">
            <div>• Chrome 80+</div>
            <div>• Firefox 75+</div>
            <div>• Safari 13+</div>
            <div>• Edge 80+</div>
          </div>
        </div>
      </div>
    );
    return;
  }

  // Рендерим приложение
  root.render(
    <React.StrictMode>
      <App />
    </React.StrictMode>
  );
};

// Обработчик ошибок
window.addEventListener('error', (event) => {
  console.error('Global error:', event.error);

  // В продакшене отправляем ошибки в сервис мониторинга
  if (process.env.NODE_ENV === 'production') {
    // TODO: Интеграция с Sentry
  }
});

// Обработчик необработанных промисов
window.addEventListener('unhandledrejection', (event) => {
  console.error('Unhandled promise rejection:', event.reason);

  // В продакшене отправляем ошибки в сервис мониторинга
  if (process.env.NODE_ENV === 'production') {
    // TODO: Интеграция с Sentry
  }
});

// Инициализируем приложение
initializeApp();

// Вывод информации о версии в консоль
if (process.env.NODE_ENV === 'development') {
  console.log(`
🎲 Lottery Analysis Frontend
Version: ${process.env.REACT_APP_VERSION}
Environment: ${process.env.REACT_APP_ENVIRONMENT}
API URL: ${process.env.REACT_APP_API_URL}
Build Date: ${new Date().toISOString()}
  `);
}