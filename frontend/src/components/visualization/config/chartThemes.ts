export const CHART_THEMES = {
  default: {
    primary: '#3b82f6',
    secondary: '#8b5cf6',
    success: '#10b981',
    warning: '#f59e0b',
    danger: '#ef4444',
    background: '#ffffff',
    grid: 'rgba(0,0,0,0.1)',
    text: '#374151',
  },
  dark: {
    primary: '#60a5fa',
    secondary: '#a78bfa',
    success: '#34d399',
    warning: '#fbbf24',
    danger: '#f87171',
    background: '#1f2937',
    grid: 'rgba(255,255,255,0.1)',
    text: '#f3f4f6',
  }
} as const;

export type ChartTheme = keyof typeof CHART_THEMES;