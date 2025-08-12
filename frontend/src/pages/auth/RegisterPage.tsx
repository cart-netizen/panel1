import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { useAuth, useNotificationActions } from '../../store';
import { ROUTES } from '../../constants';
import { EmailInput, PasswordInput, Input } from '../../components/common/Input';
import { Button } from '../../components/common/Button';
import { FormErrorNotification } from '../../components/common/Notifications';
import { apiClient } from '../../services/api';

interface RegisterFormData {
  email: string;
  password: string;
  confirmPassword: string;
  fullName: string;
  acceptTerms: boolean;
}

export const RegisterPage: React.FC = () => {
  const navigate = useNavigate();
  const { login } = useAuth();
  const { showSuccess, showError } = useNotificationActions();

  const [loading, setLoading] = useState(false);
  const [apiError, setApiError] = useState<string>('');

  const {
    register,
    handleSubmit,
    formState: { errors },
    watch
  } = useForm<RegisterFormData>();

  const password = watch('password');

  const onSubmit = async (data: RegisterFormData) => {
    setLoading(true);
    setApiError('');

    try {
      // Отправляем запрос на регистрацию
      const registerResponse = await apiClient.post('/auth/register', {
        email: data.email,
        password: data.password,
        full_name: data.fullName,
      });

      // Автоматически входим в систему после регистрации
      const loginResponse = await apiClient.post('/auth/login', {
        email: data.email,
        password: data.password,
      });

      const { access_token } = loginResponse.data;
      localStorage.setItem('access_token', access_token);

      // Получаем данные пользователя
      const userResponse = await apiClient.get('/auth/me');
      const userData = userResponse.data;

      // Обновляем состояние
      login(userData);

      // Показываем приветствие
      showSuccess(
        'Добро пожаловать!',
        'Регистрация прошла успешно. Вы автоматически вошли в систему.'
      );

      // Перенаправляем на dashboard
      navigate(ROUTES.DASHBOARD, { replace: true });

    } catch (error: any) {
      console.error('Registration error:', error);

      let errorMessage = 'Произошла ошибка при регистрации';

      if (error.response?.status === 400) {
        errorMessage = error.response.data?.detail || 'Пользователь с таким email уже существует';
      } else if (error.response?.data?.detail) {
        errorMessage = error.response.data.detail;
      } else if (error.message) {
        errorMessage = error.message;
      }

      setApiError(errorMessage);
      showError('Ошибка регистрации', errorMessage);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full">
      {/* Заголовок */}
      <div className="text-center mb-8">
        <h2 className="text-3xl font-bold text-gray-900 mb-2">
          📝 Создать аккаунт
        </h2>
        <p className="text-gray-600">
          Присоединяйтесь к профессиональным игрокам
        </p>
      </div>

      {/* Ошибка API */}
      {apiError && (
        <FormErrorNotification
          error={apiError}
          onClose={() => setApiError('')}
          className="mb-6"
        />
      )}

      {/* Форма регистрации */}
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
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
          placeholder="Введите ваше имя"
          leftIcon="👤"
          error={errors.fullName?.message}
          autoComplete="name"
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
          autoComplete="email"
        />

        {/* Пароль */}
        <PasswordInput
          {...register('password', {
            required: 'Пароль обязателен',
            minLength: {
              value: 6,
              message: 'Пароль должен содержать минимум 6 символов',
            },
            pattern: {
              value: /^(?=.*[a-z])(?=.*[A-Z\d])/,
              message: 'Пароль должен содержать минимум одну строчную букву и одну заглавную букву или цифру',
            },
          })}
          label="Пароль"
          error={errors.password?.message}
          autoComplete="new-password"
        />

        {/* Подтверждение пароля */}
        <PasswordInput
          {...register('confirmPassword', {
            required: 'Подтвердите пароль',
            validate: (value) => {
              if (value !== password) {
                return 'Пароли не совпадают';
              }
            },
          })}
          label="Подтверждение пароля"
          placeholder="Повторите пароль"
          error={errors.confirmPassword?.message}
          autoComplete="new-password"
        />

        {/* Соглашение с условиями */}
        <div className="space-y-4">
          <label className="flex items-start space-x-3">
            <input
              {...register('acceptTerms', {
                required: 'Необходимо принять условия использования',
              })}
              type="checkbox"
              className="mt-1 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
            />
            <span className="text-sm text-gray-700 leading-relaxed">
              Я принимаю{' '}
              <Link
                to="/terms"
                className="text-primary-600 hover:underline"
                target="_blank"
              >
                условия использования
              </Link>
              {' '}и{' '}
              <Link
                to="/privacy"
                className="text-primary-600 hover:underline"
                target="_blank"
              >
                политику конфиденциальности
              </Link>
            </span>
          </label>

          {errors.acceptTerms && (
            <p className="text-sm text-red-600 flex items-center space-x-1">
              <span>⚠️</span>
              <span>{errors.acceptTerms.message}</span>
            </p>
          )}
        </div>

        {/* Кнопка регистрации */}
        <Button
          type="submit"
          loading={loading}
          fullWidth
          size="lg"
          disabled={!watch('acceptTerms')}
        >
          🎯 Создать аккаунт
        </Button>
      </form>

      {/* Ссылка на вход */}
      <div className="mt-8 text-center">
        <p className="text-sm text-gray-600">
          Уже есть аккаунт?{' '}
          <Link
            to={ROUTES.LOGIN}
            className="font-medium text-primary-600 hover:text-primary-500 hover:underline"
          >
            Войти
          </Link>
        </p>
      </div>

      {/* Преимущества регистрации */}
      <div className="mt-8 p-4 bg-gradient-to-r from-blue-50 to-purple-50 border border-blue-200 rounded-lg">
        <h3 className="text-sm font-semibold text-blue-800 mb-3">
          🌟 Преимущества регистрации:
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm text-blue-700">
          <div className="flex items-center space-x-2">
            <span>🚀</span>
            <span>20+ генераций в день</span>
          </div>
          <div className="flex items-center space-x-2">
            <span>📊</span>
            <span>Анализ трендов</span>
          </div>
          <div className="flex items-center space-x-2">
            <span>💾</span>
            <span>Сохранение истории</span>
          </div>
          <div className="flex items-center space-x-2">
            <span>🎯</span>
            <span>Персональная статистика</span>
          </div>
        </div>
      </div>

      {/* Безопасность */}
      <div className="mt-6 p-3 bg-green-50 border border-green-200 rounded-lg">
        <div className="flex items-center space-x-2">
          <span className="text-green-600">🔒</span>
          <span className="text-sm text-green-700 font-medium">
            Ваши данные защищены 256-битным шифрованием
          </span>
        </div>
      </div>
    </div>
  );
};