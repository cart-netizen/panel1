// Основные типы для лотерейного приложения

// Пользователь и авторизация
export interface User {
  id: number;
  email: string;
  full_name?: string;
  is_active: boolean;
  subscription_status: 'active' | 'inactive' | 'expired';
  subscription_expires_at?: string;
  created_at: string;

  preferences?: {
    subscription_plan?: 'basic' | 'premium' | 'pro';
    theme?: 'light' | 'dark';
    notifications?: boolean;
    favorite_numbers?: {
      field1: number[];
      field2: number[];
    };
    language?: 'ru' | 'en';
  };
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterData {
  email: string;
  password: string;
  full_name?: string;
}

// Лотерейные типы
export type LotteryType = '4x20' | '5x36plus';

export interface Combination {
  field1: number[];
  field2: number[];
  description: string;
}

export interface GenerationParams {
  generator_type: 'rf_ranked' | 'multi_strategy' | 'ml_based_rf' | 'hot' | 'cold' | 'balanced';
  num_combinations: number;
}

export interface GenerationResponse {
  combinations: Combination[];
  rf_prediction?: Combination;
  lstm_prediction?: Combination;
}

// Анализ трендов
export interface TrendData {
  hot_acceleration: number[];
  cold_reversal: number[];
  momentum_numbers: number[];
  pattern_shift: 'stable' | 'ascending' | 'descending';
  confidence_score: number;
  trend_strength: number;
}

export interface TrendsResponse {
  status: string;
  lottery_type: string;
  analyzed_draws: number;
  summary: string;
  trends: {
    field1: TrendData;
    field2: TrendData;
  };
  recommendations: string[];
  timestamp: string;
}

// Оценка комбинаций
export interface CombinationEvaluation {
  combination: {
    field1: number[];
    field2: number[];
  };
  evaluation: {
    trend_alignment: number;
    momentum_score: number;
    pattern_resonance: number;
    risk_assessment: 'low' | 'medium' | 'high';
    expected_performance: number;
  };
  recommendation: string;
  timestamp: string;
}

// История тиражей
export interface DrawHistory {
  draw_number: number;
  draw_date: string;
  field1_numbers: number[];
  field2_numbers: number[];
  jackpot_amount?: number;
  winners_count?: number;
}

export interface HistoryResponse {
  draws: DrawHistory[];
  total_count: number;
  page: number;
  per_page: number;
}

// Статистика и аналитика
export interface DashboardStats {
  generations_today: number;
  trend_analyses: number;
  accuracy_percentage: {
    value: number;
    change: number;
  }| number;
  best_score: number | string;
  total_generations: number;
  recent_activities: Array<{
    activity_type: string; // Поле было переименовано с type на activity_type в schemas.py
    activity_description: string; // Поле было переименовано с description на activity_description
    created_at: string; // Поле было переименовано с timestamp на created_at
    lottery_type?: string;
  }>;
  user_stats: {
    total_generations: number;
    successful_predictions: number;
    favorite_strategy: string;
    registration_date: string;
  };
}

export interface ActivityItem {
  id: string;
  type: 'generation' | 'analysis' | 'evaluation';
  description: string;
  activity_description?: string;
  timestamp: string;
  created_at?: string;
  lottery_type: LotteryType;
  status: 'success' | 'error' | 'pending';
}

// Подписки
export interface SubscriptionPlan {
  id: string;
  name: string;
  price_monthly: number;
  price_yearly: number;
  currency: string;
  features: string[];
  limits: {
    generations_per_day: number;
    history_days: number;
    simulations_per_day: number;
  };
  popular?: boolean;
}

export interface SubscriptionPlansResponse {
  plans: SubscriptionPlan[];
}

// API ответы
export interface ApiResponse<T = any> {
  status: 'success' | 'error';
  data?: T;
  message?: string;
  errors?: Record<string, string[]>;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

// Формы
export interface FormField {
  name: string;
  label: string;
  type: 'text' | 'email' | 'password' | 'number' | 'select' | 'checkbox';
  placeholder?: string;
  required?: boolean;
  options?: { value: string; label: string; }[];
  validation?: {
    min?: number;
    max?: number;
    pattern?: string;
    message?: string;
  };
}

// UI состояния
export interface LoadingState {
  isLoading: boolean;
  error?: string;
  lastUpdated?: string;
}

export interface UIState {
  theme: 'light' | 'dark';
  sidebarOpen: boolean;
  notifications: NotificationItem[];
  selectedLottery: LotteryType;
}

export interface NotificationItem {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  title: string;
  message: string;
  timestamp: string;
  read: boolean;
  autoClose?: boolean;
}

// Конфигурация
export interface LotteryConfig {
  name: string;
  field1_size: number;
  field1_max: number;
  field2_size: number;
  field2_max: number;
  min_numbers: number;
  max_numbers: number;
  draw_times?: string[];
  api_endpoints: {
    history: string;
    generate: string;
    trends: string;
    evaluate: string;
  };
}

// Графики и визуализация
export interface ChartDataPoint {
  label: string;
  value: number;
  date?: string;
  category?: string;
  color?: string;
}

export interface TrendChartData {
  dates: string[];
  field1_trends: number[];
  field2_trends: number[];
  hot_numbers: { number: number; frequency: number; }[];
  cold_numbers: { number: number; frequency: number; }[];
}

// Симуляция стратегий
export interface SimulationParams {
  strategy: string;
  draw_count: number;
  investment_per_draw: number;
  target_combinations: number;
}

export interface SimulationResult {
  total_investment: number;
  total_winnings: number;
  net_profit: number;
  win_rate: number;
  best_win: number;
  worst_loss: number;
  drawdown_periods: number;
  roi_percentage: number;
  detailed_results: {
    draw_number: number;
    investment: number;
    winnings: number;
    profit: number;
    cumulative_profit: number;
  }[];
}

// Экспорт данных
export interface ExportParams {
  format: 'csv' | 'xlsx' | 'json';
  data_type: 'combinations' | 'history' | 'analysis';
  date_range?: {
    start: string;
    end: string;
  };
  filters?: Record<string, any>;
}

// Настройки приложения
export interface AppSettings {
  api_base_url: string;
  default_lottery: LotteryType;
  auto_refresh_interval: number;
  max_combinations_per_generation: number;
  cache_duration: number;
  theme_preference: 'light' | 'dark' | 'auto';
  language: 'ru' | 'en';
  timezone: string;
}