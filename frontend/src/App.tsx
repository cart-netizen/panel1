import React, { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';

// Store и утилиты
import { queryClient, setupAutoRefresh } from './services/queryClient';
import { useAuth, useAppActions } from './store';

// Компоненты макета
import { MainLayout } from './components/layout/MainLayout';
import { AuthLayout } from './components/layout/AuthLayout';

// Страницы
import { LoginPage } from './pages/auth/LoginPage';
import { RegisterPage } from './pages/auth/RegisterPage';
import { DashboardPage } from './pages/dashboard/DashboardPage';
import { GenerationPage } from './pages/generation/GenerationPage';
import { TrendsPage } from './pages/trends/TrendsPage';
import { HistoryPage } from './pages/history/HistoryPage';
import { ProfilePage } from './pages/profile/ProfilePage';
import { SubscriptionsPage } from './pages/subscriptions/SubscriptionsPage';
import { HelpPage } from './pages/help/HelpPage';
import { AnalysisPage } from './pages/analysis/AnalysisPage';
import { SimulationPage } from './pages/simulation/SimulationPage';

// Компоненты защиты маршрутов
import { PrivateRoute } from './components/common/PrivateRoute';
import { LoadingScreen } from './components/common/LoadingScreen';
import { ErrorBoundary } from './components/common/ErrorBoundary';
import { NotificationContainer } from './components/common/Notifications';

// Константы
import { ROUTES } from './constants';

// Глобальные стили
import './index.css';
// Временные заглушки для оставшихся страниц
// const AnalysisPage = () => <div className="p-8">🔍 Детальная аналитика - в разработке</div>;

const App: React.FC = () => {
  const { isAuthenticated, user } = useAuth();
  const { setUser } = useAppActions();

  // Инициализация приложения
  useEffect(() => {
    // Настройка автообновления данных
    const cleanup = setupAutoRefresh();

    // Проверка токена при загрузке
    const initializeAuth = async () => {
      const token = localStorage.getItem('access_token');
      if (token && !user) {
        try {
          // Загружаем данные пользователя из токена
          const response = await fetch(`${process.env.REACT_APP_API_URL}/auth/me`, {
            headers: {
              'Authorization': `Bearer ${token}`
            }
          });

          if (response.ok) {
            const userData = await response.json();
            setUser(userData);
          } else {
            // Токен недействителен
            localStorage.removeItem('access_token');
          }
        } catch (error) {
          console.error('Failed to initialize auth:', error);
          localStorage.removeItem('access_token');
        }
      }
    };

    initializeAuth();

    // Cleanup при размонтировании
    return cleanup;
  }, [user, setUser]);

  useEffect(() => {
  const refreshTokenInterval = setInterval(async () => {
    const token = localStorage.getItem('access_token');
    if (token) {
      try {
        const response = await fetch(`${process.env.REACT_APP_API_URL}/auth/refresh-token`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
          }
        });

        if (response.ok) {
          const data = await response.json();
          localStorage.setItem('access_token', data.access_token);
        }
      } catch (error) {
        console.error('Failed to refresh token:', error);
      }
    }
  }, 20 * 60 * 1000); // Обновляем каждые 20 минут

  return () => clearInterval(refreshTokenInterval);
}, []);


  // Компонент для защищенных маршрутов
  const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
    return (
      <PrivateRoute>
        <MainLayout>
          {children}
        </MainLayout>
      </PrivateRoute>
    );
  };

  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <Router>
          <div className="App min-h-screen bg-gray-50">
            {/* Контейнер уведомлений */}
            <NotificationContainer />

            <Routes>
              {/* Публичные маршруты */}
              <Route
                path={ROUTES.LOGIN}
                element={
                  isAuthenticated ? (
                    <Navigate to={ROUTES.DASHBOARD} replace />
                  ) : (
                    <AuthLayout>
                      <LoginPage />
                    </AuthLayout>
                  )
                }
              />

              <Route
                path={ROUTES.REGISTER}
                element={
                  isAuthenticated ? (
                    <Navigate to={ROUTES.DASHBOARD} replace />
                  ) : (
                    <AuthLayout>
                      <RegisterPage />
                    </AuthLayout>
                  )
                }
              />

              {/* Защищенные маршруты */}
              <Route
                path={ROUTES.DASHBOARD}
                element={
                  <ProtectedRoute>
                    <DashboardPage />
                  </ProtectedRoute>
                }
              />

              <Route
                path={ROUTES.GENERATION}
                element={
                  <ProtectedRoute>
                    <GenerationPage />
                  </ProtectedRoute>
                }
              />

              <Route
                path={ROUTES.TRENDS}
                element={
                  <ProtectedRoute>
                    <TrendsPage />
                  </ProtectedRoute>
                }
              />

              <Route
                path={ROUTES.ANALYSIS}
                element={
                  <ProtectedRoute>
                    <AnalysisPage />
                  </ProtectedRoute>
                }
              />

              <Route
                path={ROUTES.SIMULATION}
                element={
                  <ProtectedRoute>
                    <SimulationPage />
                  </ProtectedRoute>
                }
              />

              <Route
                path={ROUTES.HISTORY}
                element={
                  <ProtectedRoute>
                    <HistoryPage />
                  </ProtectedRoute>
                }
              />

              <Route
                path={ROUTES.PROFILE}
                element={
                  <ProtectedRoute>
                    <ProfilePage />
                  </ProtectedRoute>
                }
              />

              <Route
                path={ROUTES.SUBSCRIPTIONS}
                element={
                  <ProtectedRoute>
                    <SubscriptionsPage />
                  </ProtectedRoute>
                }
              />

              <Route
                path={ROUTES.HELP}
                element={
                  <MainLayout>
                    <HelpPage />
                  </MainLayout>
                }
              />

              {/* Главная страница */}
              <Route
                path={ROUTES.HOME}
                element={
                  isAuthenticated ? (
                    <Navigate to={ROUTES.DASHBOARD} replace />
                  ) : (
                    <Navigate to={ROUTES.LOGIN} replace />
                  )
                }
              />

              {/* 404 - Страница не найдена */}
              <Route
                path="*"
                element={
                  <MainLayout>
                    <div className="flex items-center justify-center min-h-[400px]">
                      <div className="text-center">
                        <div className="text-6xl mb-4">🔍</div>
                        <h1 className="text-2xl font-bold text-gray-900 mb-2">
                          Страница не найдена
                        </h1>
                        <p className="text-gray-600 mb-4">
                          Запрашиваемая страница не существует или была перемещена.
                        </p>
                        <button
                          onClick={() => window.history.back()}
                          className="btn-primary"
                        >
                          Вернуться назад
                        </button>
                      </div>
                    </div>
                  </MainLayout>
                }
              />
            </Routes>
          </div>

          {/* React Query DevTools (только в разработке) */}
          {process.env.NODE_ENV === 'development' &&
           process.env.REACT_APP_SHOW_DEV_TOOLS === 'true' && (
            <ReactQueryDevtools initialIsOpen={false} />
          )}
        </Router>
      </QueryClientProvider>
    </ErrorBoundary>
  );
};

export default App;