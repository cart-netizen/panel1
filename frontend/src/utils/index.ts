import { format, parseISO, isValid, differenceInDays, differenceInHours } from 'date-fns';
import { ru } from 'date-fns/locale';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

// Функция для объединения Tailwind классов
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// Форматирование дат
export const formatDate = (date: string | Date, formatStr = 'dd.MM.yyyy'): string => {
  try {
    const dateObj = typeof date === 'string' ? parseISO(date) : date;
    if (!isValid(dateObj)) return 'Неверная дата';
    return format(dateObj, formatStr, { locale: ru });
  } catch {
    return 'Неверная дата';
  }
};

export const formatDateTime = (date: string | Date): string => {
  return formatDate(date, 'dd.MM.yyyy HH:mm');
};

export const formatTime = (date: string | Date): string => {
  return formatDate(date, 'HH:mm');
};

export const getRelativeTime = (date: string | Date): string => {
  try {
    const dateObj = typeof date === 'string' ? parseISO(date) : date;
    if (!isValid(dateObj)) return 'Неверная дата';

    const now = new Date();
    const diffDays = differenceInDays(now, dateObj);
    const diffHours = differenceInHours(now, dateObj);

    if (diffDays > 0) {
      return `${diffDays} дн. назад`;
    } else if (diffHours > 0) {
      return `${diffHours} ч. назад`;
    } else {
      return 'Только что';
    }
  } catch {
    return 'Неверная дата';
  }
};

// Работа с числами
export const formatNumber = (num: number, decimals = 0): string => {
  return new Intl.NumberFormat('ru-RU', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(num);
};

export const formatCurrency = (amount: number, currency = 'RUB'): string => {
  return new Intl.NumberFormat('ru-RU', {
    style: 'currency',
    currency,
  }).format(amount);
};

export const formatPercentage = (value: number, decimals = 1): string => {
  return new Intl.NumberFormat('ru-RU', {
    style: 'percent',
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value);
};

// Работа с массивами
export const shuffleArray = <T>(array: T[]): T[] => {
  const shuffled = [...array];
  for (let i = shuffled.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
  }
  return shuffled;
};

export const getRandomElements = <T>(array: T[], count: number): T[] => {
  const shuffled = shuffleArray(array);
  return shuffled.slice(0, Math.min(count, array.length));
};

export const groupBy = <T, K extends keyof any>(
  array: T[],
  key: (item: T) => K
): Record<K, T[]> => {
  return array.reduce((groups, item) => {
    const group = key(item);
    groups[group] = groups[group] || [];
    groups[group].push(item);
    return groups;
  }, {} as Record<K, T[]>);
};

export const sortBy = <T>(array: T[], key: keyof T, direction: 'asc' | 'desc' = 'asc'): T[] => {
  return [...array].sort((a, b) => {
    const aVal = a[key];
    const bVal = b[key];

    if (aVal < bVal) return direction === 'asc' ? -1 : 1;
    if (aVal > bVal) return direction === 'asc' ? 1 : -1;
    return 0;
  });
};

// Валидация
export const isValidEmail = (email: string): boolean => {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
};

export const isValidPassword = (password: string): boolean => {
  return password.length >= 6;
};

export const isValidPhone = (phone: string): boolean => {
  const phoneRegex = /^\+?[1-9]\d{1,14}$/;
  return phoneRegex.test(phone.replace(/\s/g, ''));
};

// Работа со строками
export const capitalize = (str: string): string => {
  return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase();
};

export const truncate = (str: string, length: number, suffix = '...'): string => {
  if (str.length <= length) return str;
  return str.slice(0, length) + suffix;
};

export const slugify = (str: string): string => {
  return str
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/(^-|-$)/g, '');
};

// Работа с объектами
export const deepClone = <T>(obj: T): T => {
  return JSON.parse(JSON.stringify(obj));
};

export const omit = <T extends Record<string, any>, K extends keyof T>(
  obj: T,
  keys: K[]
): Omit<T, K> => {
  const result = { ...obj };
  keys.forEach(key => delete result[key]);
  return result;
};

export const pick = <T extends Record<string, any>, K extends keyof T>(
  obj: T,
  keys: K[]
): Pick<T, K> => {
  const result = {} as Pick<T, K>;
  keys.forEach(key => {
    if (key in obj) {
      result[key] = obj[key];
    }
  });
  return result;
};

// Работа с localStorage
export const storage = {
  set: (key: string, value: any): void => {
    try {
      localStorage.setItem(key, JSON.stringify(value));
    } catch (error) {
      console.error('Error saving to localStorage:', error);
    }
  },

  get: <T>(key: string, defaultValue?: T): T | null => {
    try {
      const item = localStorage.getItem(key);
      return item ? JSON.parse(item) : defaultValue || null;
    } catch (error) {
      console.error('Error reading from localStorage:', error);
      return defaultValue || null;
    }
  },

  remove: (key: string): void => {
    try {
      localStorage.removeItem(key);
    } catch (error) {
      console.error('Error removing from localStorage:', error);
    }
  },

  clear: (): void => {
    try {
      localStorage.clear();
    } catch (error) {
      console.error('Error clearing localStorage:', error);
    }
  },
};

// Дебаунсинг и троттлинг
export const debounce = <T extends (...args: any[]) => any>(
  func: T,
  wait: number
): ((...args: Parameters<T>) => void) => {
  let timeout: NodeJS.Timeout;

  return (...args: Parameters<T>) => {
    clearTimeout(timeout);
    timeout = setTimeout(() => func(...args), wait);
  };
};

export const throttle = <T extends (...args: any[]) => any>(
  func: T,
  limit: number
): ((...args: Parameters<T>) => void) => {
  let inThrottle: boolean;

  return (...args: Parameters<T>) => {
    if (!inThrottle) {
      func(...args);
      inThrottle = true;
      setTimeout(() => inThrottle = false, limit);
    }
  };
};

// Генерация случайных значений
export const generateId = (): string => {
  return Date.now().toString(36) + Math.random().toString(36).substr(2);
};

export const generateRandomNumber = (min: number, max: number): number => {
  return Math.floor(Math.random() * (max - min + 1)) + min;
};

export const generateRandomNumbers = (count: number, min: number, max: number): number[] => {
  const numbers = new Set<number>();

  while (numbers.size < count) {
    numbers.add(generateRandomNumber(min, max));
  }

  return Array.from(numbers).sort((a, b) => a - b);
};

// Цветовые утилиты
export const hexToRgb = (hex: string): { r: number; g: number; b: number } | null => {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return result ? {
    r: parseInt(result[1], 16),
    g: parseInt(result[2], 16),
    b: parseInt(result[3], 16)
  } : null;
};

export const rgbToHex = (r: number, g: number, b: number): string => {
  return "#" + ((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1);
};

export const getContrastColor = (hexColor: string): string => {
  const rgb = hexToRgb(hexColor);
  if (!rgb) return '#000000';

  const brightness = (rgb.r * 299 + rgb.g * 587 + rgb.b * 114) / 1000;
  return brightness > 128 ? '#000000' : '#ffffff';
};

// Работа с URL
export const getQueryParams = (): Record<string, string> => {
  const params = new URLSearchParams(window.location.search);
  const result: Record<string, string> = {};

  for (const [key, value] of params) {
    result[key] = value;
  }

  return result;
};

export const setQueryParams = (params: Record<string, string>): void => {
  const url = new URL(window.location.href);

  Object.entries(params).forEach(([key, value]) => {
    if (value) {
      url.searchParams.set(key, value);
    } else {
      url.searchParams.delete(key);
    }
  });

  window.history.replaceState({}, '', url.toString());
};

export const removeQueryParam = (key: string): void => {
  const url = new URL(window.location.href);
  url.searchParams.delete(key);
  window.history.replaceState({}, '', url.toString());
};

// Проверка устройства
export const isMobile = (): boolean => {
  return window.innerWidth < 768;
};

export const isTablet = (): boolean => {
  return window.innerWidth >= 768 && window.innerWidth < 1024;
};

export const isDesktop = (): boolean => {
  return window.innerWidth >= 1024;
};

export const getTouchDevice = (): boolean => {
  return 'ontouchstart' in window || navigator.maxTouchPoints > 0;
};

// Копирование в буфер обмена
export const copyToClipboard = async (text: string): Promise<boolean> => {
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text);
      return true;
    } else {
      // Fallback для старых браузеров
      const textArea = document.createElement('textarea');
      textArea.value = text;
      textArea.style.position = 'fixed';
      textArea.style.left = '-999999px';
      textArea.style.top = '-999999px';
      document.body.appendChild(textArea);
      textArea.focus();
      textArea.select();

      const success = document.execCommand('copy');
      document.body.removeChild(textArea);
      return success;
    }
  } catch (error) {
    console.error('Failed to copy to clipboard:', error);
    return false;
  }
};

// Скачивание файлов
export const downloadFile = (data: Blob | string, filename: string, type?: string): void => {
  const blob = data instanceof Blob ? data : new Blob([data], { type: type || 'text/plain' });
  const url = window.URL.createObjectURL(blob);

  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();

  document.body.removeChild(link);
  window.URL.revokeObjectURL(url);
};

export const downloadJSON = (data: any, filename: string): void => {
  const jsonString = JSON.stringify(data, null, 2);
  downloadFile(jsonString, filename, 'application/json');
};

export const downloadCSV = (data: any[], filename: string): void => {
  if (!data.length) return;

  const headers = Object.keys(data[0]);
  const csvContent = [
    headers.join(','),
    ...data.map(row => headers.map(field => `"${row[field] || ''}"`).join(','))
  ].join('\n');

  downloadFile(csvContent, filename, 'text/csv');
};

// Работа с изображениями
export const resizeImage = (
  file: File,
  maxWidth: number,
  maxHeight: number,
  quality = 0.8
): Promise<Blob> => {
  return new Promise((resolve, reject) => {
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    const img = new Image();

    img.onload = () => {
      const { width, height } = img;

      // Вычисляем новые размеры
      let newWidth = width;
      let newHeight = height;

      if (width > height) {
        if (width > maxWidth) {
          newHeight = (height * maxWidth) / width;
          newWidth = maxWidth;
        }
      } else {
        if (height > maxHeight) {
          newWidth = (width * maxHeight) / height;
          newHeight = maxHeight;
        }
      }

      canvas.width = newWidth;
      canvas.height = newHeight;

      ctx?.drawImage(img, 0, 0, newWidth, newHeight);

      canvas.toBlob(
        (blob) => {
          if (blob) {
            resolve(blob);
          } else {
            reject(new Error('Failed to resize image'));
          }
        },
        'image/jpeg',
        quality
      );
    };

    img.onerror = () => reject(new Error('Failed to load image'));
    img.src = URL.createObjectURL(file);
  });
};

// Лотерейные утилиты
export const generateLotteryCombination = (fieldSize: number, maxNumber: number): number[] => {
  return generateRandomNumbers(fieldSize, 1, maxNumber);
};

export const formatLotteryCombination = (numbers: number[]): string => {
  return numbers.sort((a, b) => a - b).join(', ');
};

export const validateLotteryCombination = (
  numbers: number[],
  fieldSize: number,
  maxNumber: number
): { isValid: boolean; errors: string[] } => {
  const errors: string[] = [];

  // Проверяем количество чисел
  if (numbers.length !== fieldSize) {
    errors.push(`Должно быть ${fieldSize} чисел`);
  }

  // Проверяем диапазон чисел
  numbers.forEach(num => {
    if (num < 1 || num > maxNumber) {
      errors.push(`Число ${num} вне диапазона 1-${maxNumber}`);
    }
  });

  // Проверяем уникальность
  const uniqueNumbers = new Set(numbers);
  if (uniqueNumbers.size !== numbers.length) {
    errors.push('Числа должны быть уникальными');
  }

  return {
    isValid: errors.length === 0,
    errors,
  };
};

export const calculateCombinationDifference = (combo1: number[], combo2: number[]): number => {
  const set1 = new Set(combo1);
  const set2 = new Set(combo2);
  const intersection = new Set([...set1].filter(x => set2.has(x)));
  return Math.max(combo1.length, combo2.length) - intersection.size;
};

// Статистические функции
export const calculateMean = (numbers: number[]): number => {
  return numbers.reduce((sum, num) => sum + num, 0) / numbers.length;
};

export const calculateMedian = (numbers: number[]): number => {
  const sorted = [...numbers].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 === 0
    ? (sorted[mid - 1] + sorted[mid]) / 2
    : sorted[mid];
};

export const calculateStandardDeviation = (numbers: number[]): number => {
  const mean = calculateMean(numbers);
  const squaredDiffs = numbers.map(num => Math.pow(num - mean, 2));
  const avgSquaredDiff = calculateMean(squaredDiffs);
  return Math.sqrt(avgSquaredDiff);
};

export const calculateFrequency = <T>(items: T[]): Map<T, number> => {
  const frequency = new Map<T, number>();

  items.forEach(item => {
    frequency.set(item, (frequency.get(item) || 0) + 1);
  });

  return frequency;
};

// Цветовые схемы для графиков
export const getChartColors = (count: number): string[] => {
  const baseColors = [
    '#3b82f6', // blue
    '#10b981', // emerald
    '#f59e0b', // amber
    '#ef4444', // red
    '#8b5cf6', // violet
    '#06b6d4', // cyan
    '#84cc16', // lime
    '#f97316', // orange
    '#ec4899', // pink
    '#6366f1', // indigo
  ];

  if (count <= baseColors.length) {
    return baseColors.slice(0, count);
  }

  // Генерируем дополнительные цвета
  const colors = [...baseColors];
  for (let i = baseColors.length; i < count; i++) {
    const hue = (i * 137.508) % 360; // Золотое сечение для равномерного распределения
    colors.push(`hsl(${hue}, 70%, 50%)`);
  }

  return colors;
};

// Производительность
export const measurePerformance = <T>(
  name: string,
  fn: () => T
): { result: T; duration: number } => {
  const start = performance.now();
  const result = fn();
  const duration = performance.now() - start;

  if (process.env.NODE_ENV === 'development') {
    console.log(`⏱️ ${name}: ${duration.toFixed(2)}ms`);
  }

  return { result, duration };
};

export const measureAsyncPerformance = async <T>(
  name: string,
  fn: () => Promise<T>
): Promise<{ result: T; duration: number }> => {
  const start = performance.now();
  const result = await fn();
  const duration = performance.now() - start;

  if (process.env.NODE_ENV === 'development') {
    console.log(`⏱️ ${name}: ${duration.toFixed(2)}ms`);
  }

  return { result, duration };
};

// Экспорт всех утилит
export * from './lottery-utils';
export * from './chart-utils';
export * from './form-utils';