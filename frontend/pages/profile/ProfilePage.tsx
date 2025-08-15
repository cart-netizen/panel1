import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { useMutation, useQuery } from '@tanstack/react-query';
import { useUser, useAppActions, useNotificationActions } from '../../store';
import { authService } from '../../services/authService';
import { Input, EmailInput } from '../../components/common/Input';
import { Button, SecondaryButton } from '../../components/common/Button';
import { StatsCard } from '../../components/common/StatsCard';
import { formatDate } from '../../utils';
import { cn } from '../../utils';
interface ProfileFormData {
  fullName: string;
  email: string;
}

export const ProfilePage: React.FC = () => {
  const user = useUser();
  const { setUser } = useAppActions();
  const { showSuccess, showError } = useNotificationActions();

  const [activeTab, setActiveTab] = useState<'profile' | 'security' | 'preferences'>('profile');

  // Форма редактирования профиля
  const {
    register,
    handleSubmit,
    formState: { errors, isDirty },
    reset
  } = useForm<ProfileFormData>({
    defaultValues: {
      fullName: user?.full_name || '',
      email: user?.email || '',
    },
  });

  // Мутация обновления профиля
  const updateProfileMutation = useMutation({
    mutationFn: (data: ProfileFormData) => authService.updateProfile({
      full_name: data.fullName,
      email: data.email,
    }),
    onSuccess: (updatedUser) => {
      setUser(updatedUser);
      showSuccess('Профиль обновлен', 'Изменения успешно сохранены');
      reset({
        fullName: updatedUser.full_name || '',
        email: updatedUser.email || '',
      });
    },
    onError: (error: any) => {
      const message = error.response?.data?.detail || 'Ошибка при обновлении профиля';
      showError('Ошибка обновления', message);
    },
  });

  const handleProfileUpdate = (data: ProfileFormData) => {
    updateProfileMutation.mutate(data);
  };

  const handleResetForm = () => {
    reset({
      fullName: user?.full_name || '',
      email: user?.email || '',
    });
  };

  if (!user) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="text-6xl mb-4">👤</div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">
            Данные пользователя недоступны
          </h2>
          <p className="text-gray-600">
            Пожалуйста, перезайдите в систему
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Заголовок */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            👤 Профиль пользователя
          </h1>
          <p className="text-gray-600">
            Управляйте вашим аккаунтом и настройками
          </p>
        </div>

        {/* Информация о пользователе */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <StatsCard
            title="Статус аккаунта"
            value={user.is_active ? 'Активен' : 'Неактивен'}
            icon="✅"
            color={user.is_active ? 'green' : 'red'}
            description="Состояние аккаунта"
          />

          <StatsCard
            title="Подписка"
            value={user.subscription_status === 'active' ? 'Активна' : 'Неактивна'}
            icon="💎"
            color={user.subscription_status === 'active' ? 'purple' : 'gray'}
            description={user.preferences?.subscription_plan || 'Базовый план'}
          />

          <StatsCard
            title="Дата регистрации"
            value={formatDate(user.created_at)}
            icon="📅"
            color="blue"
            description="Участник с"
          />
        </div>

        {/* Табы */}
        <div className="card">
          <div className="card-header border-b-0">
            <div className="flex space-x-8">
              {[
                { key: 'profile', label: '👤 Профиль', icon: '👤' },
                { key: 'security', label: '🔒 Безопасность', icon: '🔒' },
                { key: 'preferences', label: '⚙️ Настройки', icon: '⚙️' },
              ].map(tab => (
                <button
                  key={tab.key}
                  onClick={() => setActiveTab(tab.key as any)}
                  className={cn(
                    'flex items-center space-x-2 pb-3 border-b-2 transition-colors',
                    activeTab === tab.key
                      ? 'border-primary-500 text-primary-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700'
                  )}
                >
                  <span>{tab.icon}</span>
                  <span className="font-medium">{tab.label}</span>
                </button>
              ))}
            </div>
          </div>

          <div className="card-body">
            {/* Вкладка профиля */}
            {activeTab === 'profile' && (
              <form onSubmit={handleSubmit(handleProfileUpdate)} className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Полное имя */}
                  <Input
                    {...register('fullName', {
                      required: 'Имя обязательно',
                      minLength: {
                        value: 2,
                        message: 'Имя должно содержать минимум 2 символа',
                      },
                    })}
                    label="Полное имя"
                    leftIcon="👤"
                    error={errors.fullName?.message}
                  />

                  {/* Email */}
                  <EmailInput
                    {...register('email', {
                      required: 'Email обязателен',
                      pattern: {
                        value: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
                        message: 'Введите корректный email',
                      },
                    })}
                    label="Email адрес"
                    error={errors.email?.message}
                  />
                </div>

                {/* Дополнительная информация */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      ID пользователя
                    </label>
                    <div className="input-field bg-gray-50 text-gray-500">
                      {user.id}
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Дата создания
                    </label>
                    <div className="input-field bg-gray-50 text-gray-500">
                      {formatDate(user.created_at)}
                    </div>
                  </div>
                </div>

                {/* Кнопки */}
                <div className="flex items-center space-x-4 pt-6 border-t border-gray-200">
                  <Button
                    type="submit"
                    loading={updateProfileMutation.isPending}
                    disabled={!isDirty}
                    icon="💾"
                  >
                    Сохранить изменения
                  </Button>

                  <SecondaryButton
                    type="button"
                    onClick={handleResetForm}
                    disabled={!isDirty}
                  >
                    Отменить
                  </SecondaryButton>
                </div>
              </form>
            )}

            {/* Вкладка безопасности */}
            {activeTab === 'security' && (
              <div className="space-y-6">
                <div className="text-center py-8">
                  <div className="text-6xl mb-4">🔒</div>
                  <h3 className="text-lg font-medium text-gray-900 mb-2">
                    Настройки безопасности
                  </h3>
                  <p className="text-gray-600 mb-6">
                    Управление паролем и безопасностью аккаунта
                  </p>

                  {/* Изменение пароля */}
                  <div className="max-w-md mx-auto space-y-4">
                    <Button
                      variant="secondary"
                      fullWidth
                      icon="🔑"
                      onClick={() => {
                        // TODO: Реализовать модальное окно смены пароля
                        console.log('Change password modal');
                      }}
                    >
                      Изменить пароль
                    </Button>

                    <Button
                      variant="secondary"
                      fullWidth
                      icon="📱"
                      onClick={() => {
                        // TODO: Реализовать 2FA
                        console.log('Setup 2FA');
                      }}
                    >
                      Настроить 2FA
                    </Button>
                  </div>
                </div>

                {/* История входов */}
                <div className="border-t border-gray-200 pt-6">
                  <h4 className="text-lg font-medium text-gray-900 mb-4">
                    📋 Последние входы
                  </h4>

                  <div className="bg-gray-50 rounded-lg p-4 text-center">
                    <p className="text-gray-600">
                      История входов будет доступна в следующих версиях
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Вкладка настроек */}
            {activeTab === 'preferences' && (
              <div className="space-y-6">
                <div className="text-center py-8">
                  <div className="text-6xl mb-4">⚙️</div>
                  <h3 className="text-lg font-medium text-gray-900 mb-2">
                    Настройки приложения
                  </h3>
                  <p className="text-gray-600 mb-6">
                    Персональные предпочтения и параметры
                  </p>

                  {/* Настройки */}
                  <div className="max-w-md mx-auto space-y-4 text-left">
                    {/* Тема */}
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Тема оформления
                      </label>
                      <select className="input-field">
                        <option value="light">🌞 Светлая</option>
                        <option value="dark">🌙 Темная</option>
                        <option value="auto">🔄 Автоматическая</option>
                      </select>
                    </div>

                    {/* Язык */}
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Язык интерфейса
                      </label>
                      <select className="input-field">
                        <option value="ru">🇷🇺 Русский</option>
                        <option value="en">🇺🇸 English</option>
                      </select>
                    </div>

                    {/* Уведомления */}
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Уведомления
                      </label>
                      <div className="space-y-2">
                        <label className="flex items-center space-x-2">
                          <input type="checkbox" className="rounded" defaultChecked />
                          <span className="text-sm">📧 Email уведомления</span>
                        </label>
                        <label className="flex items-center space-x-2">
                          <input type="checkbox" className="rounded" defaultChecked />
                          <span className="text-sm">🔔 Push уведомления</span>
                        </label>
                        <label className="flex items-center space-x-2">
                          <input type="checkbox" className="rounded" />
                          <span className="text-sm">🔊 Звуковые уведомления</span>
                        </label>
                      </div>
                    </div>

                    {/* Автообновление */}
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Автообновление данных
                      </label>
                      <select className="input-field">
                        <option value="30">Каждые 30 секунд</option>
                        <option value="60">Каждую минуту</option>
                        <option value="300">Каждые 5 минут</option>
                        <option value="0">Отключено</option>
                      </select>
                    </div>

                    {/* Кнопки */}
                    <div className="pt-4 space-y-2">
                      <Button
                        fullWidth
                        icon="💾"
                        onClick={() => {
                          showSuccess('Настройки сохранены', 'Изменения применены');
                        }}
                      >
                        Сохранить настройки
                      </Button>

                      <SecondaryButton
                        fullWidth
                        icon="🔄"
                        onClick={() => {
                          showSuccess('Настройки сброшены', 'Восстановлены значения по умолчанию');
                        }}
                      >
                        Сбросить к умолчанию
                      </SecondaryButton>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Статистика пользователя */}
        <div className="mt-8 card">
          <div className="card-header">
            <h2 className="text-xl font-semibold text-gray-900">
              📊 Ваша статистика
            </h2>
          </div>
          <div className="card-body">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
              <div className="text-center">
                <div className="text-3xl font-bold text-blue-600 mb-1">0</div>
                <p className="text-sm text-gray-600">Генераций всего</p>
              </div>

              <div className="text-center">
                <div className="text-3xl font-bold text-green-600 mb-1">0</div>
                <p className="text-sm text-gray-600">Успешных прогнозов</p>
              </div>

              <div className="text-center">
                <div className="text-3xl font-bold text-purple-600 mb-1">0</div>
                <p className="text-sm text-gray-600">Анализов трендов</p>
              </div>

              <div className="text-center">
                <div className="text-3xl font-bold text-yellow-600 mb-1">0</div>
                <p className="text-sm text-gray-600">Избранных комбинаций</p>
              </div>
            </div>

            <div className="mt-6 text-center text-gray-500">
              <p className="text-sm">
                📈 Подробная статистика будет доступна после начала использования платформы
              </p>
            </div>
          </div>
        </div>

        {/* Опасная зона */}
        <div className="mt-8 card border-red-200">
          <div className="card-header bg-red-50">
            <h2 className="text-xl font-semibold text-red-800">
              ⚠️ Опасная зона
            </h2>
          </div>
          <div className="card-body">
            <p className="text-gray-700 mb-4">
              Действия в этом разделе необратимы. Будьте осторожны.
            </p>

            <div className="space-y-4">
              <Button
                variant="danger"
                icon="🗑️"
                onClick={() => {
                  if (window.confirm('Вы уверены, что хотите удалить все данные? Это действие необратимо.')) {
                    showError('Удаление данных', 'Функция будет доступна в следующих версиях');
                  }
                }}
              >
                Удалить все данные
              </Button>

              <Button
                variant="danger"
                icon="❌"
                onClick={() => {
                  if (window.confirm('Вы уверены, что хотите удалить аккаунт? Это действие необратимо.')) {
                    showError('Удаление аккаунта', 'Функция будет доступна в следующих версиях');
                  }
                }}
              >
                Удалить аккаунт
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};