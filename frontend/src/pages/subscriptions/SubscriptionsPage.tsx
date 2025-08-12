import React from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { useUser, useAppActions, useNotificationActions } from '../../store';
import { subscriptionService } from '../../services/subscriptionService';
import { Button, SecondaryButton } from '../../components/common/Button';
import { LoadingScreen } from '../../components/common/LoadingScreen';
import { ApiErrorDisplay } from '../../components/common/ErrorBoundary';
import { formatCurrency, formatDate } from '../../utils';
import { cn } from '../../utils';

export const SubscriptionsPage: React.FC = () => {
  const user = useUser();
  const { updateUserSubscription } = useAppActions();
  const { showSuccess, showError } = useNotificationActions();

  // Загрузка планов подписки
  const {
    data: plansData,
    isLoading: plansLoading,
    error: plansError
  } = useQuery({
    queryKey: ['subscription-plans'],
    queryFn: () => subscriptionService.getPlans(),
    staleTime: 10 * 60 * 1000, // 10 минут
  });

  // Мутация для активации подписки (демо)
  const upgradeMutation = useMutation({
    mutationFn: ({ plan, duration }: { plan: string; duration: number }) =>
      subscriptionService.demoUpgrade(plan, duration),
    onSuccess: (data) => {
      updateUserSubscription('active', data.plan);
      showSuccess(
        'Подписка активирована!',
        `Добро пожаловать в ${data.plan} план. Все функции доступны.`
      );
    },
    onError: (error: any) => {
      const message = error.response?.data?.detail || 'Ошибка при активации подписки';
      showError('Ошибка активации', message);
    },
  });

  const handleUpgrade = (planId: string) => {
    if (window.confirm(`Активировать ${planId} подписку на 1 месяц?`)) {
      upgradeMutation.mutate({ plan: planId, duration: 1 });
    }
  };

  if (plansLoading) {
    return <LoadingScreen message="Загружаем планы подписки..." />;
  }

  if (plansError) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <ApiErrorDisplay error={plansError} onRetry={() => window.location.reload()} />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Заголовок */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            💎 Планы подписки
          </h1>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto">
            Выберите план, который подходит вашим потребностям.
            Все планы включают доступ к нашим AI моделям и анализу трендов.
          </p>
        </div>

        {/* Текущая подписка */}
        {user?.subscription_status === 'active' && (
          <div className="mb-12 card border-green-200 bg-green-50">
            <div className="card-body text-center">
              <div className="text-4xl mb-4">🌟</div>
              <h2 className="text-2xl font-bold text-green-800 mb-2">
                У вас активная подписка!
              </h2>
              <p className="text-green-700 mb-4">
                Текущий план: <strong>{user.preferences?.subscription_plan || 'Premium'}</strong>
              </p>
              <p className="text-green-600 text-sm">
                {user.subscription_expires_at
                  ? `Действует до: ${formatDate(user.subscription_expires_at)}`
                  : 'Бессрочная подписка'
                }
              </p>
            </div>
          </div>
        )}

        {/* Планы подписки */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-12">
          {plansData?.plans?.map((plan) => (
            <PlanCard
              key={plan.id}
              plan={plan}
              currentPlan={user?.preferences?.subscription_plan}
              isActive={user?.subscription_status === 'active'}
              onUpgrade={() => handleUpgrade(plan.id)}
              loading={upgradeMutation.isPending}
            />
          ))}
        </div>

        {/* FAQ */}
        <div className="card">
          <div className="card-header">
            <h2 className="text-2xl font-semibold text-gray-900">
              ❓ Часто задаваемые вопросы
            </h2>
          </div>
          <div className="card-body">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">
                  Можно ли изменить план?
                </h3>
                <p className="text-gray-600">
                  Да, вы можете повысить или понизить план в любое время.
                  Изменения вступают в силу немедленно.
                </p>
              </div>

              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">
                  Есть ли пробный период?
                </h3>
                <p className="text-gray-600">
                  Все планы включают 7-дневный пробный период.
                  Отменить можно в любое время без комиссии.
                </p>
              </div>

              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">
                  Как работает оплата?
                </h3>
                <p className="text-gray-600">
                  Оплата происходит автоматически каждый месяц или год.
                  Вы получите уведомление за 3 дня до списания.
                </p>
              </div>

              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">
                  Возврат средств?
                </h3>
                <p className="text-gray-600">
                  Мы предлагаем полный возврат в течение 14 дней
                  после оплаты, если вас не устроил сервис.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Поддержка */}
        <div className="mt-12 text-center">
          <p className="text-gray-600 mb-4">
            Нужна помощь с выбором плана?
          </p>
          <Button
            variant="secondary"
            icon="💬"
            onClick={() => {
              window.open(`mailto:${process.env.REACT_APP_SUPPORT_EMAIL}?subject=Помощь с выбором плана`, '_blank');
            }}
          >
            Связаться с поддержкой
          </Button>
        </div>
      </div>
    </div>
  );
};

// Компонент карточки плана
interface PlanCardProps {
  plan: any;
  currentPlan?: string;
  isActive: boolean;
  onUpgrade: () => void;
  loading: boolean;
}

const PlanCard: React.FC<PlanCardProps> = ({
  plan,
  currentPlan,
  isActive,
  onUpgrade,
  loading,
}) => {
  const isCurrent = isActive && currentPlan === plan.id;
  const canUpgrade = !isActive || (currentPlan && getPlanWeight(currentPlan) < getPlanWeight(plan.id));

  return (
    <div className={cn(
      'card relative overflow-hidden transition-all duration-200',
      plan.popular && 'ring-2 ring-primary-500 scale-105',
      isCurrent && 'border-green-300 bg-green-50'
    )}>
      {/* Популярный план */}
      {plan.popular && (
        <div className="absolute top-0 left-0 right-0 bg-primary-600 text-white text-center py-2 text-sm font-semibold">
          🌟 Популярный выбор
        </div>
      )}

      <div className={cn('card-body', plan.popular && 'pt-12')}>
        {/* Заголовок плана */}
        <div className="text-center mb-6">
          <div className="text-4xl mb-3">
            {plan.id === 'basic' && '📦'}
            {plan.id === 'premium' && '⭐'}
            {plan.id === 'pro' && '🚀'}
          </div>
          <h3 className="text-2xl font-bold text-gray-900 mb-2">
            {plan.name}
          </h3>
          <div className="mb-4">
            <span className="text-4xl font-bold text-gray-900">
              {formatCurrency(plan.price_monthly)}
            </span>
            <span className="text-gray-600">/мес</span>
          </div>
          {plan.price_yearly < plan.price_monthly * 12 && (
            <p className="text-sm text-green-600">
              💰 Экономия {formatCurrency(plan.price_monthly * 12 - plan.price_yearly)} при годовой оплате
            </p>
          )}
        </div>

        {/* Функции */}
        <div className="space-y-3 mb-6">
          {plan.features.map((feature: string, index: number) => (
            <div key={index} className="flex items-center space-x-2">
              <span className="text-green-500 font-bold">✓</span>
              <span className="text-sm text-gray-700">{feature}</span>
            </div>
          ))}
        </div>

        {/* Лимиты */}
        <div className="border-t border-gray-200 pt-4 mb-6">
          <h4 className="text-sm font-semibold text-gray-700 mb-2">📊 Лимиты:</h4>
          <div className="space-y-1 text-sm text-gray-600">
            <div>
              Генераций в день: {' '}
              <span className="font-medium">
                {plan.limits.generations_per_day === -1 ? 'Безлимит' : plan.limits.generations_per_day}
              </span>
            </div>
            <div>
              История: {' '}
              <span className="font-medium">
                {plan.limits.history_days === -1 ? 'Полная' : `${plan.limits.history_days} дней`}
              </span>
            </div>
            <div>
              Симуляций в день: {' '}
              <span className="font-medium">
                {plan.limits.simulations_per_day === -1 ? 'Безлимит' : plan.limits.simulations_per_day}
              </span>
            </div>
          </div>
        </div>

        {/* Кнопка */}
        <div className="text-center">
          {isCurrent ? (
            <div className="text-green-600 font-semibold py-2">
              ✅ Текущий план
            </div>
          ) : canUpgrade ? (
            <Button
              onClick={onUpgrade}
              loading={loading}
              fullWidth
              variant={plan.popular ? 'primary' : 'secondary'}
              size="lg"
            >
              {isActive ? 'Перейти на план' : 'Выбрать план'}
            </Button>
          ) : (
            <SecondaryButton
              fullWidth
              disabled
              size="lg"
            >
              Недоступно
            </SecondaryButton>
          )}
        </div>

        {/* Демо-активация */}
        {!isCurrent && (
          <div className="mt-3 text-center">
            <button
              onClick={onUpgrade}
              className="text-sm text-primary-600 hover:underline"
              disabled={loading}
            >
              🎯 Демо-активация (тест)
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

// Вспомогательная функция для сравнения планов
const getPlanWeight = (planId: string): number => {
  const weights: Record<string, number> = {
    basic: 1,
    premium: 2,
    pro: 3,
  };
  return weights[planId] || 0;
};