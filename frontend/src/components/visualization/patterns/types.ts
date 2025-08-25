// Основные типы данных для визуализации паттернов

// Данные о горячих/холодных числах
export interface HotColdData {
  hot: number[];
  cold: number[];
}

// Данные корреляций между числами
export interface CorrelationPair {
  pair: string;
  frequency_percent: number;
  count: number;
}

// Информация о циклах чисел
export interface CycleInfo {
  number: number;
  last_seen_ago: number;
  avg_cycle: number;
  is_overdue: boolean;
}

// Анализ избранных чисел пользователя
export interface FavoritesAnalysis {
  [key: string]: {
    frequency: number;
    percentage: number;
  };
}

// Основной интерфейс данных паттернов
export interface PatternData {
  hot_cold: {
    field1: HotColdData;
    field2: HotColdData;
  };
  correlations: {
    field1: CorrelationPair[];
    field2: CorrelationPair[];
  };
  favorites_analysis?: {
    field1: FavoritesAnalysis;
    field2: FavoritesAnalysis;
  };
  cycles_field1?: CycleInfo[];
  cycles_field2?: CycleInfo[];
}

// Пропсы для компонентов визуализации
export interface PatternVisualizationProps {
  data?: PatternData;
}

// Данные для тепловой карты
export interface NumberFrequency {
  number: number;
  frequency: number;
  field: string;
  isHot: boolean;
  isCold: boolean;
  isOverdue: boolean;
}

// Данные для пузырькового анализа готовности
export interface BubbleDataPoint {
  number: number;
  avgInterval: number;
  currentInterval: number;
  frequency: number;
  isHot: boolean;
  isCold: boolean;
  isOverdue: boolean;
  readinessScore: number; // 0-100
  field: 'field1' | 'field2';
}

// Данные для трендового анализа
export interface TrendDataPoint {
  draw: number;
  [key: string]: number; // num7, num12, etc.
}

// Статистика активности чисел
export interface ActivityStat {
  number: number;
  activity: number; // 0-100
  trend: 'up' | 'down' | 'stable';
  change: number; // процентное изменение
}

// Данные для радарного анализа
export interface RadarDataPoint {
  metric: string;
  [key: string]: string | number; // field1_7, field2_2, etc.
}

// Типы графиков
export type ChartType = 'heatmap' | 'trends' | 'correlations' | 'readiness' | 'favorites';

// Статус числа
export interface NumberStatus {
  isHot: boolean;
  isCold: boolean;
  isOverdue: boolean;
  status: 'hot' | 'cold' | 'overdue' | 'neutral';
  statusText: string;
}

// Конфигурация цветов для графиков
export interface ColorConfig {
  primary: string;
  secondary: string;
  success: string;
  warning: string;
  danger: string;
  info: string;
  light: string;
  dark: string;
}

// Конфигурация анимации
export interface AnimationConfig {
  duration: number;
  delay: number;
  easing: 'ease' | 'ease-in' | 'ease-out' | 'ease-in-out';
}

// Настройки графиков
export interface ChartSettings {
  showGrid: boolean;
  showTooltip: boolean;
  showLegend: boolean;
  animationEnabled: boolean;
  colorScheme: 'default' | 'dark' | 'colorful';
  fontSize: 'small' | 'medium' | 'large';
}

// Фильтры для данных
export interface DataFilter {
  windowSize?: number; // размер окна анализа
  topN?: number; // количество топ элементов
  minFrequency?: number; // минимальная частота
  excludeCold?: boolean; // исключить холодные числа
  onlyFavorites?: boolean; // только избранные числа
}

// Экспорт данных
export interface ExportOptions {
  format: 'png' | 'svg' | 'pdf' | 'json' | 'csv';
  quality?: 'low' | 'medium' | 'high';
  includeData?: boolean;
  includeSettings?: boolean;
}

// Состояние компонента визуализации
export interface VisualizationState {
  activeChart: ChartType;
  loading: boolean;
  error: string | null;
  settings: ChartSettings;
  filter: DataFilter;
  lastUpdate: Date | null;
}

// События компонента
export interface VisualizationEvents {
  onChartChange: (chartType: ChartType) => void;
  onDataRefresh: () => void;
  onSettingsChange: (settings: ChartSettings) => void;
  onFilterChange: (filter: DataFilter) => void;
  onExport: (options: ExportOptions) => void;
  onNumberSelect: (number: number, field: 'field1' | 'field2') => void;
  onNumberHover: (number: number | null, field: 'field1' | 'field2') => void;
}

// Контекст для передачи данных между компонентами
export interface PatternVisualizationContext {
  data: PatternData | null;
  state: VisualizationState;
  events: VisualizationEvents;
  favorites: {
    field1: number[];
    field2: number[];
  };
  setFavorites: (favorites: { field1: number[]; field2: number[] }) => void;
}

// Результат API запроса
export interface PatternApiResponse {
  hot_cold: {
    field1: HotColdData;
    field2: HotColdData;
  };
  correlations_field1: CorrelationPair[];
  correlations_field2: CorrelationPair[];
  cycles_field1: CycleInfo[];
  cycles_field2: CycleInfo[];
  favorites_analysis?: {
    field1: FavoritesAnalysis;
    field2: FavoritesAnalysis;
  };
  metadata: {
    total_draws: number;
    analyzed_period_days: number;
    confidence_score: number;
    last_updated: string;
  };
}