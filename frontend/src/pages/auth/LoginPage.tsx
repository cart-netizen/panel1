import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAppActions, useNotificationActions } from '../../store';
import { authService } from '../../services/authService';
import { Button } from '../../components/common/Button';
import { Input } from '../../components/common/Input';
import { ROUTES } from '../../constants';

export const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const { setUser } = useAppActions();
  const { showSuccess, showError } = useNotificationActions();

  // Состояние формы
  const [formData, setFormData] = useState({
    email: '',
    password: ''
  });

  const [isLoading, setIsLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);

  // Валидация формы
  const [errors, setErrors] = useState<{
    email?: string;
    password?: string;
  }>({});

  // Обработка изменений в форме
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));

    // Очищаем ошибку поля при изменении
    if (errors[name as keyof typeof errors]) {
      setErrors(prev => ({
        ...prev,
        [name]: undefined
      }));
    }
  };

  // Валидация формы
  const validateForm = (): boolean => {
    const newErrors: typeof errors = {};

    // Валидация email
    if (!formData.email) {
      newErrors.email = 'Email обязателен';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = 'Некорректный email';
    }

    // Валидация пароля
    if (!formData.password) {
      newErrors.password = 'Пароль обязателен';
    } else if (formData.password.length < 6) {
      newErrors.password = 'Пароль должен быть не менее 6 символов';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // Обработка отправки формы
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Валидация
    if (!validateForm()) {
      return;
    }

    setIsLoading(true);

    try {
      // Вход через authService
      const response = await authService.login({
        email: formData.email,
        password: formData.password
      });

      // Получаем данные пользователя
      const userData = await authService.getCurrentUser();

      // Сохраняем в store
      setUser(userData);

      // Сохраняем email если включен "Запомнить меня"
      if (rememberMe) {
        localStorage.setItem('remembered_email', formData.email);
      } else {
        localStorage.removeItem('remembered_email');
      }

      // Показываем уведомление об успехе
      showSuccess('Успешный вход', `Добро пожаловать, ${userData.full_name || userData.email}!`);

      // Перенаправляем на dashboard
      navigate(ROUTES.DASHBOARD);

    } catch (error: any) {
      console.error('Login error:', error);

      // Обработка ошибок
      let errorMessage = 'Ошибка входа в систему';

      if (error.response?.data?.detail) {
        // Если detail - это строка, используем её
        if (typeof error.response.data.detail === 'string') {
          errorMessage = error.response.data.detail;
        }
        // Если detail - это массив объектов валидации Pydantic
        else if (Array.isArray(error.response.data.detail)) {
          const validationErrors = error.response.data.detail
            .map((err: any) => `${err.loc?.join('.')}: ${err.msg}`)
            .join(', ');
          errorMessage = `Ошибка валидации: ${validationErrors}`;
        }
        // Если detail - это объект валидации
        else if (typeof error.response.data.detail === 'object' && error.response.data.detail.msg) {
          errorMessage = `Ошибка валидации: ${error.response.data.detail.msg}`;
        }
      } else if (error.message) {
        errorMessage = error.message;
      }

      showError('Ошибка входа', errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  // Демо вход для тестирования
  const handleDemoLogin = async () => {
    setFormData({
      email: 'demo@example.com',
      password: 'demo123'
    });

    // Автоматически отправляем форму
    setTimeout(() => {
      const form = document.getElementById('login-form') as HTMLFormElement;
      if (form) {
        form.requestSubmit();
      }
    }, 100);
  };

  // Загрузка сохраненного email при монтировании
  React.useEffect(() => {
    const savedEmail = localStorage.getItem('remembered_email');
    if (savedEmail) {
      setFormData(prev => ({ ...prev, email: savedEmail }));
      setRememberMe(true);
    }
  }, []);

  return (
    <div className="w-full">
      {/* Заголовок */}
      <div className="text-center mb-8">
        <h2 className="text-3xl font-bold text-gray-900 mb-2">
          Вход в систему
        </h2>
        <p className="text-gray-600">
          Введите свои учетные данные для доступа к аккаунту
        </p>
      </div>

      {/* Форма */}
      <form id="login-form" onSubmit={handleSubmit} className="space-y-6">
        {/* Email */}
        <div>
          <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-2">
            Email адрес
          </label>
          <Input
            id="email"
            name="email"
            type="email"
            value={formData.email}
            onChange={handleChange}
            placeholder="example@email.com"
            error={errors.email}
            disabled={isLoading}
            autoComplete="email"
            required
          />
        </div>

        {/* Пароль */}
        <div>
          <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-2">
            Пароль
          </label>
          <div className="relative">
            <Input
              id="password"
              name="password"
              type={showPassword ? 'text' : 'password'}
              value={formData.password}
              onChange={handleChange}
              placeholder="••••••••"
              error={errors.password}
              disabled={isLoading}
              autoComplete="current-password"
              required
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700"
              tabIndex={-1}
            >
              {showPassword ? '👁️' : '👁️‍🗨️'}
            </button>
          </div>
        </div>

        {/* Запомнить меня и Забыли пароль */}
        <div className="flex items-center justify-between">
          <div className="flex items-center">
            <input
              id="remember-me"
              type="checkbox"
              checked={rememberMe}
              onChange={(e) => setRememberMe(e.target.checked)}
              className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
              disabled={isLoading}
            />
            <label htmlFor="remember-me" className="ml-2 block text-sm text-gray-700">
              Запомнить меня
            </label>
          </div>

          <Link
            to="/forgot-password"
            className="text-sm text-primary-600 hover:text-primary-700 hover:underline"
          >
            Забыли пароль?
          </Link>
        </div>

        {/* Кнопка входа */}
        <Button
          type="submit"
          variant="primary"
          fullWidth
          loading={isLoading}
          disabled={isLoading}
        >
          {isLoading ? 'Вход...' : 'Войти'}
        </Button>

        {/* Демо вход */}
        {process.env.NODE_ENV === 'development' && (
          <Button
            type="button"
            variant="secondary"
            fullWidth
            onClick={handleDemoLogin}
            disabled={isLoading}
          >
            🎮 Демо вход
          </Button>
        )}

        {/* Разделитель */}
        <div className="relative">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-gray-300" />
          </div>
          <div className="relative flex justify-center text-sm">
            <span className="px-2 bg-white text-gray-500">Или</span>
          </div>
        </div>

        {/* Ссылка на регистрацию */}
        <div className="text-center">
          <span className="text-sm text-gray-600">
            Нет аккаунта?{' '}
            <Link
              to={ROUTES.REGISTER}
              className="font-medium text-primary-600 hover:text-primary-700 hover:underline"
            >
              Зарегистрироваться
            </Link>
          </span>
        </div>
      </form>

      {/* Информация о безопасности */}
      <div className="mt-8 text-center">
        <p className="text-xs text-gray-500">
          🔒 Защищенное соединение • Ваши данные в безопасности
        </p>
      </div>
    </div>
  );
};