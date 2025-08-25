import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse, InternalAxiosRequestConfig } from 'axios';
import { ApiResponse } from '../types';

// Конфигурация API
export const API_CONFIG = {
  BASE_URL: process.env.REACT_APP_API_URL || 'http://127.0.0.1:8002/api/v1',
  TIMEOUT: 30000,
  RETRY_ATTEMPTS: 3,
  RETRY_DELAY: 1000,
};

// Интерфейс для конфигурации запроса
interface RequestConfig extends AxiosRequestConfig {
  skipAuth?: boolean;
  skipErrorHandling?: boolean;
  retryAttempts?: number;
}

// Расширяем интерфейс для кастомного свойства skipAuth
declare module 'axios' {
  export interface AxiosRequestConfig {
    skipAuth?: boolean;
  }
  export interface InternalAxiosRequestConfig {
    skipAuth?: boolean;
  }
}

// Расширяем Window для showNotification
declare global {
  interface Window {
    showNotification?: (type: 'error' | 'success' | 'warning', title: string, message: string) => void;
  }
}

// Класс для работы с API
class ApiClient {
  private client: AxiosInstance;
  private refreshingToken = false;
  private failedQueue: Array<{
    resolve: (value: any) => void;
    reject: (reason: any) => void;
  }> = [];

  constructor() {
    this.client = axios.create({
      baseURL: API_CONFIG.BASE_URL,
      timeout: API_CONFIG.TIMEOUT,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    this.setupInterceptors();
  }

  private setupInterceptors() {
    // Интерцептор запросов - добавляем токен
    this.client.interceptors.request.use(
      (config: InternalAxiosRequestConfig) => {
        const token = this.getToken();
        if (token && !config.skipAuth) {
          config.headers = config.headers || {};
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // Интерцептор ответов - обработка ошибок и обновление токена
    this.client.interceptors.response.use(
      (response: AxiosResponse) => {
        // Логирование для разработки
        if (process.env.NODE_ENV === 'development') {
          console.log(`✅ API Response: ${response.config.method?.toUpperCase()} ${response.config.url} - ${response.status}`);
        }
        return response;
      },
      async (error: any) => {
        const originalRequest = error.config;

        // Проверка на истекший токен
        if (error.response?.status === 401) {
          const message = error.response.data?.detail || '';

          // Если токен истёк - очищаем и редиректим на логин
          if (message.includes('expired') || message.includes('Token has expired')) {
            this.clearTokens();
            localStorage.removeItem('user');

            // Показываем уведомление если функция доступна
            if (window.showNotification) {
              window.showNotification('error', 'Сессия истекла', 'Пожалуйста, войдите снова');
            } else {
              // Альтернативный способ показа уведомления
              console.warn('Сессия истекла. Пожалуйста, войдите снова');
              // Можно использовать alert для критических случаев
              // alert('Сессия истекла. Пожалуйста, войдите снова');
            }

            // Редирект на страницу логина
            window.location.href = '/login';
            return Promise.reject(error);
          }

          // Другие 401 ошибки
          if (!originalRequest._retry) {
            if (this.refreshingToken) {
              // Если токен уже обновляется, добавляем запрос в очередь
              return new Promise((resolve, reject) => {
                this.failedQueue.push({ resolve, reject });
              });
            }

            originalRequest._retry = true;
            this.refreshingToken = true;

            try {
              // Попытка обновить токен (если есть refresh token)
              const refreshToken = localStorage.getItem('refresh_token');
              if (refreshToken) {
                const response = await this.client.post('/auth/refresh', {
                  refresh_token: refreshToken
                }, { skipAuth: true });

                const { access_token } = response.data;
                this.setToken(access_token);

                // Выполняем все запросы из очереди
                this.processQueue(null, access_token);

                return this.client(originalRequest);
              } else {
                // Нет refresh токена - отправляем на логин
                this.handleAuthError();
                return Promise.reject(error);
              }
            } catch (refreshError) {
              this.processQueue(refreshError, null);
              this.handleAuthError();
              return Promise.reject(refreshError);
            } finally {
              this.refreshingToken = false;
            }
          }
        }

        // Обработка других ошибок
        if (!originalRequest?.skipErrorHandling) {
          this.handleApiError(error);
        }

        return Promise.reject(error);
      }
    );
  }

  private processQueue(error: any, token: string | null) {
    this.failedQueue.forEach(({ resolve, reject }) => {
      if (error) {
        reject(error);
      } else {
        resolve(token);
      }
    });

    this.failedQueue = [];
  }

  private handleAuthError() {
    this.clearTokens();
    localStorage.removeItem('user');
    // Перенаправляем на страницу входа
    window.location.href = '/login';
  }

  private handleApiError(error: any) {
    if (process.env.NODE_ENV === 'development') {
      console.error('❌ API Error:', error);
    }

    // Показываем уведомление об ошибке
    const message = error.response?.data?.detail ||
                   error.response?.data?.message ||
                   error.message ||
                   'Произошла ошибка при выполнении запроса';

    // Используем глобальную функцию уведомлений если она доступна
    if (window.showNotification) {
      window.showNotification('error', 'Ошибка', message);
    } else {
      console.error('API Error:', message);
    }
  }

  // Управление токенами
  private getToken(): string | null {
    return localStorage.getItem('access_token');
  }

  private setToken(token: string): void {
    localStorage.setItem('access_token', token);
  }

  private clearTokens(): void {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
  }

  // Основные методы HTTP
  public async get<T = any>(url: string, config?: RequestConfig): Promise<AxiosResponse<T>> {
    return this.client.get(url, config);
  }

  public async post<T = any>(url: string, data?: any, config?: RequestConfig): Promise<AxiosResponse<T>> {
    return this.client.post(url, data, config);
  }

  public async put<T = any>(url: string, data?: any, config?: RequestConfig): Promise<AxiosResponse<T>> {
    return this.client.put(url, data, config);
  }

  public async patch<T = any>(url: string, data?: any, config?: RequestConfig): Promise<AxiosResponse<T>> {
    return this.client.patch(url, data, config);
  }

  public async delete<T = any>(url: string, config?: RequestConfig): Promise<AxiosResponse<T>> {
    return this.client.delete(url, config);
  }

  // Специальные методы для работы с лотереей
  public async lotteryRequest<T = any>(
    lotteryType: string,
    endpoint: string,
    method: 'GET' | 'POST' | 'PUT' | 'DELETE' = 'GET',
    data?: any,
    config?: RequestConfig
  ): Promise<AxiosResponse<T>> {
    const url = `/${lotteryType}${endpoint}`;

    switch (method) {
      case 'GET':
        return this.get(url, config);
      case 'POST':
        return this.post(url, data, config);
      case 'PUT':
        return this.put(url, data, config);
      case 'DELETE':
        return this.delete(url, config);
      default:
        throw new Error(`Unsupported method: ${method}`);
    }
  }

  // Метод для загрузки файлов
  public async uploadFile<T = any>(url: string, file: File, config?: RequestConfig): Promise<AxiosResponse<T>> {
    const formData = new FormData();
    formData.append('file', file);

    return this.client.post(url, formData, {
      ...config,
      headers: {
        ...config?.headers,
        'Content-Type': 'multipart/form-data',
      },
    });
  }

  // Утилиты для работы с данными
  public handleApiResponse<T>(response: AxiosResponse<ApiResponse<T>>): T {
    if (response.data.status === 'error') {
      throw new Error(response.data.message || 'API Error');
    }
    return response.data.data as T;
  }

  // Метод для отмены запросов
  public createCancelToken() {
    return axios.CancelToken.source();
  }

  // Проверка статуса подключения
  public async healthCheck(): Promise<boolean> {
    try {
      await this.get('/health', {
        skipAuth: true,
        skipErrorHandling: true,
        timeout: 5000
      });
      return true;
    } catch (error) {
      return false;
    }
  }

  // Получение информации о текущем пользователе
  public async getCurrentUser() {
    const response = await this.get('/auth/me');
    return response.data;
  }

  // Метод для обновления токена
  public async refreshToken(): Promise<boolean> {
    try {
      const token = this.getToken();
      if (!token) return false;

      const response = await this.post('/auth/refresh-token', {}, {
        skipErrorHandling: true
      });

      if (response.data?.access_token) {
        this.setToken(response.data.access_token);
        return true;
      }
      return false;
    } catch (error) {
      return false;
    }
  }

  // Выход из системы
  public logout(): void {
    this.clearTokens();
    localStorage.removeItem('user');
    window.location.href = '/login';
  }
}

// Создаем глобальный экземпляр API клиента
export const apiClient = new ApiClient();

// Экспортируем типы для использования в других файлах
export type { RequestConfig };

// Вспомогательные функции
export const createApiUrl = (endpoint: string): string => {
  return `${API_CONFIG.BASE_URL}${endpoint}`;
};

export const isNetworkError = (error: any): boolean => {
  return !error.response && error.code === 'NETWORK_ERROR';
};

export const isTimeoutError = (error: any): boolean => {
  return error.code === 'ECONNABORTED';
};

export const getErrorMessage = (error: any): string => {
  if (error.response?.data?.detail) {
    return error.response.data.detail;
  }
  if (error.response?.data?.message) {
    return error.response.data.message;
  }
  if (error.message) {
    return error.message;
  }
  return 'Произошла неизвестная ошибка';
};