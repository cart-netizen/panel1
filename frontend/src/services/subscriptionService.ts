import { apiClient } from './api';
import { SubscriptionPlansResponse, User } from '../types';

class SubscriptionService {
  // Получение доступных планов
  async getPlans(): Promise<SubscriptionPlansResponse> {
    const response = await apiClient.get('/subscriptions/plans');
    return response.data;
  }

  // Получение текущей подписки
  async getCurrentSubscription(): Promise<User> {
    const response = await apiClient.get('/subscriptions/my-subscription');
    return response.data;
  }

  // Демо-активация подписки (для тестирования)
  async demoUpgrade(plan: string, durationMonths = 1): Promise<any> {
    const response = await apiClient.post('/subscriptions/upgrade', {
      plan,
      duration_months: durationMonths,
    });
    return response.data;
  }

  // Отмена подписки
  async cancelSubscription(reason?: string): Promise<any> {
    const response = await apiClient.post('/subscriptions/cancel', {
      reason,
    });
    return response.data;
  }

  // Возобновление подписки
  async renewSubscription(): Promise<any> {
    const response = await apiClient.post('/subscriptions/renew');
    return response.data;
  }

  // Получение истории платежей
  async getPaymentHistory(): Promise<any> {
    const response = await apiClient.get('/subscriptions/payments');
    return response.data;
  }

  // Получение лимитов для текущего плана
  async getCurrentLimits(): Promise<any> {
    const response = await apiClient.get('/subscriptions/limits');
    return response.data;
  }

  // Получение использования за сегодня
  async getTodayUsage(): Promise<any> {
    const response = await apiClient.get('/subscriptions/usage/today');
    return response.data;
  }

  // Создание промокода (админ функция)
  async createPromoCode(
    code: string,
    discount: number,
    validUntil: string,
    maxUses = 1
  ): Promise<any> {
    const response = await apiClient.post('/subscriptions/promo/create', {
      code,
      discount,
      valid_until: validUntil,
      max_uses: maxUses,
    });
    return response.data;
  }

  // Применение промокода
  async applyPromoCode(code: string): Promise<any> {
    const response = await apiClient.post('/subscriptions/promo/apply', {
      code,
    });
    return response.data;
  }

  // Получение статистики использования
  async getUsageStatistics(period: '7d' | '30d' | '90d' = '30d'): Promise<any> {
    const response = await apiClient.get('/subscriptions/usage/stats', {
      params: { period }
    });
    return response.data;
  }
}

export const subscriptionService = new SubscriptionService();