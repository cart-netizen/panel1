import { apiClient } from './api';
import { User, LoginCredentials, RegisterData, AuthResponse } from '../types';

class AuthService {
  // Вход в систему
  async login(credentials: LoginCredentials): Promise<AuthResponse> {
    try {
      // Используем JSON endpoint
      const response = await apiClient.post('/auth/login-json', {
        email: credentials.email,
        password: credentials.password
      }, {
        skipAuth: true,
      });

      const { access_token, token_type } = response.data;

      // Сохраняем токен
      localStorage.setItem('access_token', access_token);

      // Получаем данные пользователя
      // try {
      //   const userResponse = await apiClient.get('/auth/me');
      //   localStorage.setItem('user', JSON.stringify(userResponse.data));
      // } catch (error) {
      //   console.warn('Failed to fetch user data:', error);
      // }

      return { access_token, token_type };
    } catch (error: any) {
      // Правильная обработка ошибок
      if (error.response?.data?.detail) {
        throw new Error(error.response.data.detail);
      }
      throw error;
    }
  }

  // Регистрация
  async register(userData: RegisterData): Promise<User> {
    const response = await apiClient.post('/auth/register', {
      email: userData.email,
      password: userData.password,
      full_name: userData.full_name,
    }, {
      skipAuth: true,
    });

    return response.data;
  }

  // Получение текущего пользователя
  async getCurrentUser(): Promise<User> {
    const response = await apiClient.get('/auth/me');
    return response.data;
  }

  // Обновление профиля
  async updateProfile(data: Partial<User>): Promise<User> {
    const response = await apiClient.patch('/auth/profile', data);
    return response.data;
  }

  // Обновление профиля из БД
  async refreshProfile(): Promise<User> {
    const response = await apiClient.get('/auth/refresh');
    return response.data;
  }

  // Выход из системы
  async logout(): Promise<void> {
    try {
      // Опционально: отправляем запрос на сервер для отзыва токена
      await apiClient.post('/auth/logout');
    } catch (error) {
      // Игнорируем ошибки выхода
      console.warn('Logout request failed:', error);
    } finally {
      // В любом случае очищаем локальные токены
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
    }
  }

  // Восстановление пароля
  async forgotPassword(email: string): Promise<void> {
    await apiClient.post('/auth/forgot-password', { email }, {
      skipAuth: true,
    });
  }

  // Сброс пароля
  async resetPassword(token: string, newPassword: string): Promise<void> {
    await apiClient.post('/auth/reset-password', {
      token,
      new_password: newPassword,
    }, {
      skipAuth: true,
    });
  }

  // Изменение пароля
  async changePassword(currentPassword: string, newPassword: string): Promise<void> {
    await apiClient.post('/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
    });
  }

  // Проверка доступности email
  async checkEmailAvailability(email: string): Promise<boolean> {
    try {
      const response = await apiClient.post('/auth/check-email', { email }, {
        skipAuth: true,
      });
      return response.data.available;
    } catch (error) {
      // Если эндпоинт не существует, возвращаем true
      return true;
    }
  }

  // Получение токена из localStorage
  getToken(): string | null {
    return localStorage.getItem('access_token');
  }

  // Проверка наличия токена
  hasValidToken(): boolean {
    const token = this.getToken();
    if (!token) return false;

    try {
      // Простая проверка формата JWT
      const payload = JSON.parse(atob(token.split('.')[1]));
      const currentTime = Date.now() / 1000;

      // Проверяем не истек ли токен
      return payload.exp > currentTime;
    } catch {
      return false;
    }
  }

  // Демо-вход (для тестирования)
  async demoLogin(): Promise<AuthResponse> {
    return this.login({
      email: 'final_test_1754893444@example.com',
      password: 'final123',
    });
  }
}

export const authService = new AuthService();
// export const authService = {
//   async login(email: string, password: string): Promise<LoginResponse> {
//     try {
//       // Используем JSON endpoint для frontend
//       const response = await apiClient.post('/auth/login-json', {
//         email,
//         password
//       }, {
//         skipAuth: true
//       });
//
//       const { access_token, user } = response.data;
//
//       // Сохраняем токен
//       localStorage.setItem('access_token', access_token);
//
//       // Если user не вернулся, получаем его отдельно
//       if (!user) {
//         const userResponse = await apiClient.get('/auth/me');
//         localStorage.setItem('user', JSON.stringify(userResponse.data));
//         return { access_token, user: userResponse.data };
//       }
//
//       localStorage.setItem('user', JSON.stringify(user));
//       return { access_token, user };
//     } catch (error) {
//       throw error;
//     }
//   },};