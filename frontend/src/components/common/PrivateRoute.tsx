import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../store';
import { LoadingScreen } from './LoadingScreen';
import { ROUTES } from '../../constants';

interface PrivateRouteProps {
  children: React.ReactNode;
  requireSubscription?: boolean;
  subscriptionLevel?: 'basic' | 'premium' | 'pro';
}

export const PrivateRoute: React.FC<PrivateRouteProps> = ({
  children,
  requireSubscription = false,
  subscriptionLevel = 'basic'
}) => {
  const { isAuthenticated, user, hasSubscription, subscriptionPlan } = useAuth();
  const location = useLocation();

  // Показываем загрузку пока проверяем авторизацию
  if (isAuthenticated === undefined) {
    return <LoadingScreen message="Проверка авторизации..." />;
  }

  // Если пользователь не авторизован
  if (!isAuthenticated || !user) {
    return (
      <Navigate
        to={ROUTES.LOGIN}
        state={{ from: location.pathname }}
        replace
      />
    );
  }

  // Если требуется подписка, но у пользователя ее нет
  if (requireSubscription && !hasSubscription) {
    return (
      <Navigate
        to={ROUTES.SUBSCRIPTIONS}
        state={{
          from: location.pathname,
          message: 'Для доступа к этой функции требуется активная подписка'
        }}
        replace
      />
    );
  }

  // Если требуется определенный уровень подписки
  if (requireSubscription && hasSubscription) {
    const planHierarchy = { basic: 1, premium: 2, pro: 3 };
    const requiredLevel = planHierarchy[subscriptionLevel];
    const userLevel = planHierarchy[subscriptionPlan as keyof typeof planHierarchy] || 0;

    if (userLevel < requiredLevel) {
      return (
        <Navigate
          to={ROUTES.SUBSCRIPTIONS}
          state={{
            from: location.pathname,
            message: `Для доступа требуется подписка уровня ${subscriptionLevel} или выше`
          }}
          replace
        />
      );
    }
  }

  // Если все проверки пройдены, показываем контент
  return <>{children}</>;
};

// Компонент для маршрутов, требующих только авторизации
export const AuthenticatedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return <PrivateRoute>{children}</PrivateRoute>;
};

// Компонент для премиум маршрутов
export const PremiumRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <PrivateRoute requireSubscription={true} subscriptionLevel="premium">
      {children}
    </PrivateRoute>
  );
};

// Компонент для про маршрутов
export const ProRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <PrivateRoute requireSubscription={true} subscriptionLevel="pro">
      {children}
    </PrivateRoute>
  );
};