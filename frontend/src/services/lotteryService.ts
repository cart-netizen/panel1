import { apiClient } from './api';
import {
  LotteryType,
  GenerationParams,
  GenerationResponse,
  TrendsResponse,
  CombinationEvaluation,
  HistoryResponse,
  DashboardStats
} from '../types';

class LotteryService {
  // Генерация комбинаций
  async generateCombinations(
    lotteryType: LotteryType,
    params: GenerationParams
  ): Promise<GenerationResponse> {
    const response = await apiClient.lotteryRequest(
      lotteryType,
      '/generate',
      'POST',
      params
    );
    return response.data;
  }

  // Асинхронная генерация комбинаций
  async generateCombinationsAsync(
    lotteryType: LotteryType,
    params: GenerationParams
  ): Promise<GenerationResponse> {
    const response = await apiClient.lotteryRequest(
      lotteryType,
      '/generate',
      'POST',
      params,
      { timeout: 60000 } // Увеличенный таймаут для сложных генераций
    );
    return response.data;
  }

  // Получение анализа трендов
  async getTrends(lotteryType: LotteryType): Promise<TrendsResponse> {
    const response = await apiClient.lotteryRequest(lotteryType, '/trends');
    return response.data;
  }

  // Оценка конкретной комбинации
  async evaluateCombination(
    lotteryType: LotteryType,
    field1: number[],
    field2: number[]
  ): Promise<CombinationEvaluation> {
    const response = await apiClient.lotteryRequest(
      lotteryType,
      '/evaluate-combination',
      'POST',
      null,
      {
        params: { field1, field2 }
      }
    );
    return response.data;
  }

  // Получение истории тиражей
  async getDrawHistory(
    lotteryType: LotteryType,
    options: {
      limit?: number;
      page?: number;
      dateFrom?: string;
      dateTo?: string;
    } = {}
  ): Promise<HistoryResponse> {
    const { limit = 100, page = 1, dateFrom, dateTo } = options;

    const response = await apiClient.lotteryRequest(
      lotteryType,
      '/history',
      'GET',
      null,
      {
        params: {
          limit,
          page,
          date_from: dateFrom,
          date_to: dateTo,
        }
      }
    );
    return response.data;
  }

  // Получение статистики для dashboard
  async getDashboardStats(): Promise<DashboardStats> {
    const response = await apiClient.get('/dashboard/stats');
    return response.data;
  }

  // Симуляция стратегий
  async simulateStrategy(
    lotteryType: LotteryType,
    params: {
      strategy: string;
      draw_count: number;
      investment_per_draw: number;
      target_combinations: number;
    }
  ): Promise<any> {
    const response = await apiClient.lotteryRequest(
      lotteryType,
      '/simulate',
      'POST',
      params,
      { timeout: 120000 } // 2 минуты для симуляций
    );
    return response.data;
  }

  // Получение паттернов
  async getPatterns(
    lotteryType: LotteryType,
    analysisType: 'frequency' | 'pairs' | 'clusters' | 'sequences' = 'frequency'
  ): Promise<any> {
    const response = await apiClient.lotteryRequest(
      lotteryType,
      `/patterns/${analysisType}`
    );
    return response.data;
  }

  // Проверка билета
  async verifyTicket(
    lotteryType: LotteryType,
    combinations: { field1: number[]; field2: number[] }[],
    drawNumber?: number
  ): Promise<any> {
    const response = await apiClient.lotteryRequest(
      lotteryType,
      '/verify',
      'POST',
      {
        combinations,
        draw_number: drawNumber,
      }
    );
    return response.data;
  }

  // Получение статуса обучения моделей
  async getTrainingStatus(lotteryType: LotteryType): Promise<any> {
    const response = await apiClient.lotteryRequest(lotteryType, '/training-status');
    return response.data;
  }

  // Принудительное обновление данных
  async forceDataUpdate(lotteryType: LotteryType): Promise<any> {
    const response = await apiClient.lotteryRequest(
      lotteryType,
      '/update-source',
      'POST',
      null,
      { timeout: 60000 }
    );
    return response.data;
  }

  // Импорт данных из CSV
  async importHistoryFromCSV(lotteryType: LotteryType, file: File): Promise<any> {
    const response = await apiClient.uploadFile(
      `/${lotteryType}/import-history`,
      file
    );
    return response.data;
  }

  // Экспорт данных
  async exportData(
    lotteryType: LotteryType,
    format: 'csv' | 'xlsx' | 'json',
    dataType: 'combinations' | 'history' | 'analysis',
    options: {
      dateFrom?: string;
      dateTo?: string;
      limit?: number;
    } = {}
  ): Promise<Blob> {
    const response = await apiClient.lotteryRequest(
      lotteryType,
      '/export',
      'POST',
      {
        format,
        data_type: dataType,
        ...options,
      },
      {
        responseType: 'blob'
      }
    );
    return response.data;
  }

  // Получение конфигурации лотереи
  async getLotteryConfig(lotteryType: LotteryType): Promise<any> {
    const response = await apiClient.lotteryRequest(lotteryType, '/config');
    return response.data;
  }

  // Получение топ комбинаций
  async getTopCombinations(
    lotteryType: LotteryType,
    period: '7d' | '30d' | '90d' = '30d',
    limit = 10
  ): Promise<any> {
    const response = await apiClient.lotteryRequest(
      lotteryType,
      '/top-combinations',
      'GET',
      null,
      {
        params: { period, limit }
      }
    );
    return response.data;
  }

  // Получение статистики по числам
  async getNumberStatistics(
    lotteryType: LotteryType,
    period: '7d' | '30d' | '90d' | 'all' = '30d'
  ): Promise<any> {
    const response = await apiClient.lotteryRequest(
      lotteryType,
      '/statistics/numbers',
      'GET',
      null,
      {
        params: { period }
      }
    );
    return response.data;
  }

  // Получение расписания тиражей
  async getDrawSchedule(lotteryType: LotteryType): Promise<any> {
    const response = await apiClient.lotteryRequest(lotteryType, '/schedule');
    return response.data;
  }

  // Подписка на уведомления о новых тиражах
  async subscribeToDrawNotifications(
    lotteryType: LotteryType,
    email: string,
    enabled: boolean
  ): Promise<any> {
    const response = await apiClient.lotteryRequest(
      lotteryType,
      '/notifications/subscribe',
      'POST',
      {
        email,
        enabled,
      }
    );
    return response.data;
  }

  // Демо генерация (без авторизации)
  async demoGeneration(lotteryType: LotteryType): Promise<any> {
    const response = await apiClient.lotteryRequest(
      lotteryType,
      '/demo/generate',
      'POST',
      null,
      { skipAuth: true }
    );
    return response.data;
  }
}

export const lotteryService = new LotteryService();