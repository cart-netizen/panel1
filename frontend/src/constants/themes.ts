// Темы оформления

export const LIGHT_THEME = {
  name: 'light',
  colors: {
    background: '#ffffff',
    surface: '#f8fafc',
    primary: '#3b82f6',
    secondary: '#8b5cf6',
    accent: '#10b981',
    text: {
      primary: '#1f2937',
      secondary: '#6b7280',
      disabled: '#9ca3af',
    },
    border: '#e5e7eb',
    shadow: 'rgba(0, 0, 0, 0.1)',
    overlay: 'rgba(0, 0, 0, 0.5)',
  },
  lottery: {
    field1: {
      background: '#dbeafe',
      text: '#1e40af',
      border: '#93c5fd',
    },
    field2: {
      background: '#dcfce7',
      text: '#166534',
      border: '#86efac',
    },
    hot: {
      background: '#fee2e2',
      text: '#991b1b',
      border: '#fca5a5',
    },
    cold: {
      background: '#dbeafe',
      text: '#1e40af',
      border: '#93c5fd',
    },
  },
} as const;

export const DARK_THEME = {
  name: 'dark',
  colors: {
    background: '#0f172a',
    surface: '#1e293b',
    primary: '#3b82f6',
    secondary: '#8b5cf6',
    accent: '#10b981',
    text: {
      primary: '#f1f5f9',
      secondary: '#cbd5e1',
      disabled: '#64748b',
    },
    border: '#334155',
    shadow: 'rgba(0, 0, 0, 0.3)',
    overlay: 'rgba(0, 0, 0, 0.7)',
  },
  lottery: {
    field1: {
      background: '#1e3a8a',
      text: '#93c5fd',
      border: '#3b82f6',
    },
    field2: {
      background: '#14532d',
      text: '#86efac',
      border: '#10b981',
    },
    hot: {
      background: '#991b1b',
      text: '#fca5a5',
      border: '#ef4444',
    },
    cold: {
      background: '#1e3a8a',
      text: '#93c5fd',
      border: '#3b82f6',
    },
  },
} as const;

export const THEME_CONFIG = {
  light: LIGHT_THEME,
  dark: DARK_THEME,
} as const;

export type ThemeType = keyof typeof THEME_CONFIG;