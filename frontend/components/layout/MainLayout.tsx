import React, { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useSidebarOpen, useUser, useAppActions, useSelectedLottery } from '../../store';
import { ROUTES, ROUTE_META, NAVIGATION_GROUPS, LOTTERY_CONFIGS } from '../../constants';
import { cn } from '../../utils';
// import type { LotteryType, NavigationGroupKey } from '../../constants';
type LotteryType = keyof typeof LOTTERY_CONFIGS;

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
  // const handleLogout = () => {
  //   logout();
  //
  //   navigate(ROUTES.LOGIN);
  // };
  const handleLogout = async () => {
  try {
    // Очищаем токены
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');

    // Вызываем logout из store
    logout();

    // Перенаправляем на страницу входа
    window.location.href = '/login';
  } catch (error) {
    console.error('Logout error:', error);
    // В любом случае очищаем и перенаправляем
    localStorage.clear();
    window.location.href = '/login';
  }
  };
  return (
    <div className="min-h-screen bg-gray-50 flex">
      {/* Боковая панель */}
      <div className={cn(
        'fixed inset-y-0 left-0 z-50 w-64 bg-white shadow-strong transition-transform duration-300 ease-in-out',
        sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
      )}>
        {/* Заголовок */}
        <div className="flex items-center justify-between h-16 px-6 border-b border-gray-200">
          <h1 className="text-xl font-bold text-gray-900">🎲 LotteryBot</h1>
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
            Тип лотереи
          </label>
          <select
            value={selectedLottery}
            onChange={(e) => setSelectedLottery(e.target.value as LotteryType)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            {Object.entries(LOTTERY_CONFIGS).map(([key, config]) => (
              <option key={key} value={key}>
                {config.name}
              </option>
            ))}
          </select>
        </div>

        {/* Навигация */}
        <nav className="flex-1 px-4 py-6 space-y-8">
          {Object.entries(NAVIGATION_GROUPS).map(([groupKey, group]) => (
            <div key={groupKey} className="mb-6">
              <h3 className="px-2 text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
                {group.title}
              </h3>
              <div className="space-y-1">
                {group.routes.map((route: string) => {
                  const meta = ROUTE_META[route as keyof typeof ROUTE_META];
                  if (!meta) return null;

                  return (
                    <button
                      key={route}
                      onClick={() => navigate(route)}
                      className={cn(
                        'w-full flex items-center px-2 py-2 text-sm font-medium rounded-md transition-colors',
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
                ? 'bg-green-50 text-green-700 border border-green-200'
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
      <div className="flex-1 lg:ml-64">
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

          {/* Правая часть - профиль */}
          <div className="flex items-center space-x-4">
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
                <span className="hidden md:block text-sm font-medium text-gray-700">
                  {user?.full_name || user?.email}
                </span>
              </button>

              {/* Выпадающее меню профиля */}
              {profileMenuOpen && (
                <div className="absolute right-0 mt-2 w-48 bg-white rounded-md shadow-lg py-1 z-50">
                  <button
                    onClick={() => {
                      navigate(ROUTES.PROFILE);
                      setProfileMenuOpen(false);
                    }}
                    className="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                  >
                    👤 Профиль
                  </button>
                  <button
                    onClick={() => {
                      handleLogout();
                      setProfileMenuOpen(false);
                    }}
                    className="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                  >
                    🚪 Выйти
                  </button>
                </div>
              )}
            </div>
          </div>
        </header>

        {/* Контент страницы */}
        <main className="flex-1">
          {children}
        </main>
      </div>

      {/* Оверлей для мобильных устройств */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 lg:hidden z-40"
          onClick={() => setSidebarOpen(false)}
        />
      )}
    </div>
  );
};