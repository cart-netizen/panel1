import React, { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useSidebarOpen, useUser, useAppActions, useSelectedLottery } from '../../store';
import { ROUTES, ROUTE_META, NAVIGATION_GROUPS, LOTTERY_CONFIGS } from '../../constants';
import { cn } from '../../utils';

interface MainLayoutProps {
  children: React.ReactNode;
}

export const MainLayout: React.FC<MainLayoutProps> = ({ children }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const user = useUser();
  const sidebarOpen = useSidebarOpen();
  const selectedLottery = useSelectedLottery();
  const { toggleSidebar, setSidebarOpen, setSelectedLottery, logout } = useAppActions();

  const [profileMenuOpen, setProfileMenuOpen] = useState(false);

  // Определяем активный маршрут
  const isActiveRoute = (path: string): boolean => {
    return location.pathname === path;
  };

  // Обработчик выхода
  const handleLogout = () => {
    logout();
    navigate(ROUTES.LOGIN);
  };

  return (
    <div className="min-h-screen bg-gray-50 flex">
      {/* Боковая панель */}
      <div className={cn(
        'fixed inset-y-0 left-0 z-50 w-64 bg-white shadow-strong transition-transform duration-300 ease-in-out',
        sidebarOpen ? 'translate-x-0' : '-translate-x-full',
        'lg:translate-x-0 lg:static lg:inset-0'
      )}>
        {/* Заголовок сайдбара */}
        <div className="flex items-center justify-between h-16 px-6 border-b border-gray-200">
          <div className="flex items-center space-x-3">
            <div className="text-2xl">🎲</div>
            <div>
              <h1 className="text-lg font-bold text-gray-900">
                Lottery Analysis
              </h1>
              <p className="text-xs text-gray-500">
                Профессиональный анализ
              </p>
            </div>
          </div>

          {/* Кнопка закрытия на мобильных */}
          <button
            onClick={() => setSidebarOpen(false)}
            className="lg:hidden p-1 rounded-md hover:bg-gray-100"
          >
            ✕
          </button>
        </div>

        {/* Селектор лотереи */}
        <div className="p-4 border-b border-gray-200">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Активная лотерея:
          </label>
          <select
            value={selectedLottery}
            onChange={(e) => setSelectedLottery(e.target.value as any)}
            className="w-full input-field text-sm"
          >
            {Object.entries(LOTTERY_CONFIGS).map(([key, config]) => (
              <option key={key} value={key}>
                {config.name}
              </option>
            ))}
          </select>
        </div>

        {/* Навигация */}
        <nav className="flex-1 px-4 py-4 space-y-1 overflow-y-auto">
          {Object.entries(NAVIGATION_GROUPS).map(([groupKey, group]) => (
            <div key={groupKey} className="mb-6">
              <h3 className="px-2 text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
                {group.title}
              </h3>
              <div className="space-y-1">
                {group.routes.map(route => {
                  const meta = ROUTE_META[route];
                  if (!meta) return null;

                  return (
                    <button
                      key={route}
                      onClick={() => navigate(route)}
                      className={cn(
                        'w-full flex items-center px-3 py-2 text-sm font-medium rounded-lg transition-colors duration-200',
                        isActiveRoute(route)
                          ? 'bg-primary-100 text-primary-700 border-r-2 border-primary-500'
                          : 'text-gray-700 hover:bg-gray-100 hover:text-gray-900'
                      )}
                    >
                      <span className="mr-3 text-lg">{meta.icon}</span>
                      {meta.title}
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
        </nav>

        {/* Информация о подписке */}
        {user && (
          <div className="p-4 border-t border-gray-200">
            <div className={cn(
              'px-3 py-2 rounded-lg text-sm',
              user.subscription_status === 'active'
                ? 'bg-success-50 text-success-700 border border-success-200'
                : 'bg-gray-50 text-gray-600 border border-gray-200'
            )}>
              <div className="flex items-center justify-between">
                <span className="font-medium">
                  {user.subscription_status === 'active' ? '⭐ Премиум' : '🆓 Базовый'}
                </span>
                <button
                  onClick={() => navigate(ROUTES.SUBSCRIPTIONS)}
                  className="text-xs text-primary-600 hover:underline"
                >
                  Управление
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Основной контент */}
      <div className="flex-1 lg:ml-0">
        {/* Верхняя панель */}
        <header className="bg-white shadow-sm border-b border-gray-200 h-16 flex items-center justify-between px-6">
          {/* Кнопка меню и breadcrumb */}
          <div className="flex items-center space-x-4">
            <button
              onClick={toggleSidebar}
              className="lg:hidden p-2 rounded-md hover:bg-gray-100"
            >
              ☰
            </button>

            {/* Breadcrumb */}
            <div className="hidden sm:flex items-center space-x-2 text-sm text-gray-600">
              <span>🏠</span>
              <span>/</span>
              <span className="font-medium text-gray-900">
                {ROUTE_META[location.pathname as keyof typeof ROUTE_META]?.title || 'Страница'}
              </span>
            </div>
          </div>

          {/* Правая часть - уведомления и профиль */}
          <div className="flex items-center space-x-4">
            {/* Уведомления */}
            <button className="p-2 rounded-md hover:bg-gray-100 relative">
              <span className="text-xl">🔔</span>
              {/* Индикатор новых уведомлений */}
              <span className="absolute -top-1 -right-1 w-3 h-3 bg-red-500 rounded-full"></span>
            </button>

            {/* Профиль пользователя */}
            <div className="relative">
              <button
                onClick={() => setProfileMenuOpen(!profileMenuOpen)}
                className="flex items-center space-x-3 p-2 rounded-md hover:bg-gray-100"
              >
                <div className="w-8 h-8 bg-primary-100 rounded-full flex items-center justify-center">
                  <span className="text-primary-700 font-semibold">
                    {user?.full_name?.charAt(0) || user?.email?.charAt(0) || '?'}
                  </span>
                </div>
                <div className="hidden sm:block text-left">
                  <p className="text-sm font-medium text-gray-900">
                    {user?.full_name || 'Пользователь'}
                  </p>
                  <p className="text-xs text-gray-500">
                    {user?.email}
                  </p>
                </div>
                <span className="text-gray-400">▼</span>
              </button>

              {/* Выпадающее меню профиля */}
              {profileMenuOpen && (
                <div className="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-strong border border-gray-200 py-2 z-10">
                  <button
                    onClick={() => {
                      navigate(ROUTES.PROFILE);
                      setProfileMenuOpen(false);
                    }}
                    className="w-full flex items-center px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                  >
                    👤 Профиль
                  </button>

                  <button
                    onClick={() => {
                      navigate(ROUTES.SETTINGS);
                      setProfileMenuOpen(false);
                    }}
                    className="w-full flex items-center px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                  >
                    ⚙️ Настройки
                  </button>

                  <button
                    onClick={() => {
                      navigate(ROUTES.SUBSCRIPTIONS);
                      setProfileMenuOpen(false);
                    }}
                    className="w-full flex items-center px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                  >
                    💎 Подписка
                  </button>

                  <hr className="my-2 border-gray-200" />

                  <button
                    onClick={() => {
                      handleLogout();
                      setProfileMenuOpen(false);
                    }}
                    className="w-full flex items-center px-4 py-2 text-sm text-red-600 hover:bg-red-50"
                  >
                    🚪 Выйти
                  </button>
                </div>
              )}
            </div>
          </div>
        </header>

        {/* Основной контент */}
        <main className="flex-1">
          {children}
        </main>
      </div>

      {/* Overlay для мобильных устройств */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-gray-600 bg-opacity-75 lg:hidden z-40"
          onClick={() => setSidebarOpen(false)}
        />
      )}
    </div>
  );
};