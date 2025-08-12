import React, { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { useAuth, useNotificationActions } from '../../store';
import { ROUTES } from '../../constants';
import { EmailInput, PasswordInput } from '../../components/common/Input';
import { Button } from '../../components/common/Button';
import { FormErrorNotification } from '../../components/common/Notifications';
import { apiClient } from '../../services/api';

interface LoginFormData {
  email: string;
  password: string;
  rememberMe?: boolean;
}

export const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { login } = useAuth();
  const { showSuccess, showError } = useNotificationActions();

  const [loading, setLoading] = useState(false);
  const [apiError, setApiError] = useState<string>('');

  const {
    register,
    handleSubmit,
    formState: { errors },
    watch
  } = useForm<LoginFormData>({
    defaultValues: {
      email: '',
      password: '',
      rememberMe: false,
    },
  });

  // Получаем путь, откуда пришел пользователь
  const from = (location.state as any)?.from || ROUTES.DASHBOARD;

  const onSubmit = async (data: LoginFormData) => {
    setLoading(true);
    setApiError('');

    try {
      // Отправляем запрос на авторизацию
      const response = await apiClient.post('/auth/login', {
        email: data.email,
        password: data.password,
      });

      const { access_token } = response.data;

      // Сохраняем токен
      localStorage.setItem('access_token', access_token);

      // Получаем данные пользователя
      const userResponse = await apiClient.get('/auth/me');
      const userData = userResponse.data;

      // Обновляем состояние
      login(userData);

      // Показываем успешное уведомление
      showSuccess(
        'Добро пожаловать!',
        `Вы успешно вошли в систему как ${userData.full_name || userData.email}`
      );

      // Перенаправляем пользователя
      navigate(from, { replace: true });

    } catch (error: any) {
      console.error('Login error:', error);

      let errorMessage = 'Произошла ошибка при входе';

      if (error.response?.status === 401) {
        errorMessage = 'Неверный email или пароль';
      } else if (error.response?.data?.detail) {
        errorMessage = error.response.data.detail;
      } else if (error.message) {
        errorMessage = error.message;
      }

      setApiError(errorMessage);
      showError('Ошибка входа', errorMessage);
    } finally {
      setLoading(false);
    }
  };

  // Демо-вход (для тестирования)
  const handleDemoLogin = async () => {
    setLoading(true);
    setApiError('');

    try {
      const demoCredentials = {
        email: 'final_test_1754893444@example.com',
        password: 'final123',
      };

      const response = await apiClient.post('/auth/login', demoCredentials);
      const { access_token } = response.data;

      localStorage.setItem('access_token', access_token);

      const userResponse = await apiClient.get('/auth/me');
      const userData = userResponse.data;

      login(userData);
      showSuccess('Демо-вход', 'Вы вошли под демо-аккаунтом');
      navigate(from, { replace: true });

    } catch (error: any) {
      console.error('Demo login error:', error);
      setApiError('Ошибка демо-входа. Возможно, сервер недоступен.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full">
      {/* Заголовок */}
      <div className="text-center mb-8">
        <h2 className="text-3xl font-bold text-gray-900 mb-2">
          🔐 Вход в систему
        </h2>
        <p className="text-gray-600">
          Введите свои данные для доступа к платформе
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

      {/* Форма входа */}
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
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
          })}
          label="Пароль"
          error={errors.password?.message}
          autoComplete="current-password"
        />

        {/* Запомнить меня */}
        <div className="flex items-center justify-between">
          <label className="flex items-center space-x-2">
            <input
              {...register('rememberMe')}
              type="checkbox"
              className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
            />
            <span className="text-sm text-gray-700">Запомнить меня</span>
          </label>

          <Link
            to={ROUTES.FORGOT_PASSWORD}
            className="text-sm text-primary-600 hover:text-primary-500 hover:underline"
          >
            Забыли пароль?
          </Link>
        </div>

        {/* Кнопка входа */}
        <Button
          type="submit"
          loading={loading}
          fullWidth
          size="lg"
        >
          🚀 Войти в систему
        </Button>
      </form>

      {/* Разделитель */}
      <div className="mt-8 mb-6">
        <div className="relative">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-gray-300" />
          </div>
          <div className="relative flex justify-center text-sm">
            <span className="bg-white px-2 text-gray-500">или</span>
          </div>
        </div>
      </div>

      {/* Демо-вход */}
      <Button
        onClick={handleDemoLogin}
        variant="secondary"
        fullWidth
        loading={loading}
        className="mb-6"
      >
        🎯 Демо-вход (тестирование)
      </Button>

      {/* Ссылка на регистрацию */}
      <div className="text-center">
        <p className="text-sm text-gray-600">
          Нет аккаунта?{' '}
          <Link
            to={ROUTES.REGISTER}
            className="font-medium text-primary-600 hover:text-primary-500 hover:underline"
          >
            Зарегистрироваться
          </Link>
        </p>
      </div>

      {/* Дополнительная информация */}
      <div className="mt-8 p-4 bg-blue-50 border border-blue-200 rounded-lg">
        <h3 className="text-sm font-semibold text-blue-800 mb-2">
          🎯 Что вас ждет:
        </h3>
        <ul className="text-sm text-blue-700 space-y-1">
          <li>• AI генерация комбинаций за 1-2 секунды</li>
          <li>• Анализ трендов в реальном времени</li>
          <li>• Точность прогнозов до 99.7%</li>
          <li>• Профессиональные инструменты анализа</li>
        </ul>
      </div>

      {/* Техническая информация для разработки */}
      {process.env.NODE_ENV === 'development' && (
        <div className="mt-6 p-3 bg-gray-100 rounded-lg border border-gray-300">
          <h4 className="text-xs font-semibold text-gray-700 mb-2">
            DEV: Тестовые данные
          </h4>
          <div className="text-xs text-gray-600 space-y-1">
            <div>Email: final_test_1754893444@example.com</div>
            <div>Password: final123</div>
            <div>API: {process.env.REACT_APP_API_URL}</div>
          </div>
        </div>
      )}
    </div>
  );
};