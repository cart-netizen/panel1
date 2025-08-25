/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          800: '#1e40af',
          900: '#1e3a8a',
        },
        secondary: {
          50: '#fdf4ff',
          100: '#fae8ff',
          200: '#f5d0fe',
          300: '#f0abfc',
          400: '#e879f9',
          500: '#d946ef',
          600: '#c026d3',
          700: '#a21caf',
          800: '#86198f',
          900: '#701a75',
        },
        success: {
          50: '#f0fdf4',
          100: '#dcfce7',
          200: '#bbf7d0',
          300: '#86efac',
          400: '#4ade80',
          500: '#22c55e',
          600: '#16a34a',
          700: '#15803d',
          800: '#166534',
          900: '#14532d',
        },
        warning: {
          50: '#fffbeb',
          100: '#fef3c7',
          200: '#fde68a',
          300: '#fcd34d',
          400: '#fbbf24',
          500: '#f59e0b',
          600: '#d97706',
          700: '#b45309',
          800: '#92400e',
          900: '#78350f',
        },
        danger: {
          50: '#fef2f2',
          100: '#fee2e2',
          200: '#fecaca',
          300: '#fca5a5',
          400: '#f87171',
          500: '#ef4444',
          600: '#dc2626',
          700: '#b91c1c',
          800: '#991b1b',
          900: '#7f1d1d',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['Fira Code', 'monospace'],
      },
      boxShadow: {
        'soft': '0 2px 15px -3px rgba(0, 0, 0, 0.08), 0 10px 20px -2px rgba(0, 0, 0, 0.04)',
        'medium': '0 4px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
        'strong': '0 10px 40px -10px rgba(0, 0, 0, 0.15), 0 4px 25px -5px rgba(0, 0, 0, 0.1)',
      },
      animation: {
        'fade-in': 'fadeIn 0.5s ease-in-out',
        'slide-up': 'slideUp 0.3s ease-out',
        'bounce-gentle': 'bounceGentle 2s infinite',
        'pulse-soft': 'pulseSoft 2s infinite',
        'glow': 'glow 2s ease-in-out infinite alternate',
        'number-selected': 'numberSelected 0.2s ease-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { transform: 'translateY(10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        bounceGentle: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-5px)' },
        },
        pulseSoft: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.7' },
        },
        glow: {
          '0%': { boxShadow: '0 0 5px rgba(59, 130, 246, 0.3)' },
          '100%': { boxShadow: '0 0 20px rgba(59, 130, 246, 0.6)' },
        },
        numberSelected: {
          '0%': { transform: 'scale(1)' },
          '50%': { transform: 'scale(1.15)' },
          '100%': { transform: 'scale(1.1)' },
        },
      },
      spacing: {
        '18': '4.5rem',
        '88': '22rem',
        '128': '32rem',
      },
      borderRadius: {
        'xl': '0.75rem',
        '2xl': '1rem',
        '3xl': '1.5rem',
      },
      backdropBlur: {
        xs: '2px',
      },
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/typography'),
    function({ addComponents, theme }) {
      addComponents({
        // Компоненты для анализа
        '.cluster-item': {
          '@apply bg-gray-50 border border-gray-200 rounded-lg p-3 transition-all duration-200 hover:shadow-md hover:bg-gray-100': {},
        },
        '.cluster-item-active': {
          '@apply bg-primary-50 border-primary-200 shadow-md': {},
        },

        // Скоринг комбинаций
        '.score-excellent': {
          '@apply text-green-600 bg-green-50 border-green-200 border rounded-lg p-4': {},
        },
        '.score-good': {
          '@apply text-blue-600 bg-blue-50 border-blue-200 border rounded-lg p-4': {},
        },
        '.score-average': {
          '@apply text-warning-600 bg-warning-50 border-warning-200 border rounded-lg p-4': {},
        },
        '.score-poor': {
          '@apply text-danger-600 bg-danger-50 border-danger-200 border rounded-lg p-4': {},
        },

        // Числовые теги и индикаторы
        '.number-tag': {
          '@apply inline-flex items-center px-2 py-1 rounded text-sm font-medium transition-colors duration-200': {},
        },
        '.number-tag-hot': {
          '@apply bg-red-100 text-red-800 border border-red-200': {},
        },
        '.number-tag-cold': {
          '@apply bg-blue-100 text-blue-800 border border-blue-200': {},
        },
        '.number-tag-selected': {
          '@apply bg-primary-500 text-white shadow-md animate-number-selected': {},
        },
        '.number-tag-cluster-1': {
          '@apply bg-purple-100 text-purple-800 border border-purple-200': {},
        },
        '.number-tag-cluster-2': {
          '@apply bg-green-100 text-green-800 border border-green-200': {},
        },
        '.number-tag-cluster-3': {
          '@apply bg-yellow-100 text-yellow-800 border border-yellow-200': {},
        },
        '.number-tag-cluster-4': {
          '@apply bg-pink-100 text-pink-800 border border-pink-200': {},
        },
        '.number-tag-cluster-5': {
          '@apply bg-indigo-100 text-indigo-800 border border-indigo-200': {},
        },

        // Кнопки выбора чисел
        '.number-button': {
          '@apply w-8 h-8 text-sm rounded transition-all duration-200 font-medium border': {},
        },
        '.number-button-unselected': {
          '@apply bg-gray-100 hover:bg-gray-200 text-gray-700 border-gray-300 hover:border-gray-400': {},
        },
        '.number-button-selected': {
          '@apply bg-primary-500 text-white border-primary-600 shadow-md transform scale-110 animate-glow': {},
        },
        '.number-button-disabled': {
          '@apply bg-gray-50 text-gray-400 border-gray-200 cursor-not-allowed': {},
        },

        // Панели результатов
        '.analysis-panel': {
          '@apply bg-white border border-gray-200 rounded-lg shadow-soft p-6 transition-all duration-200': {},
        },
        '.analysis-panel-highlighted': {
          '@apply border-primary-200 shadow-medium': {},
        },

        // Статистические карточки
        '.stat-card': {
          '@apply bg-white border border-gray-200 rounded-lg p-4 text-center transition-all duration-200 hover:shadow-medium': {},
        },
        '.stat-card-primary': {
          '@apply border-primary-200 bg-primary-50': {},
        },
        '.stat-card-success': {
          '@apply border-success-200 bg-success-50': {},
        },
        '.stat-card-warning': {
          '@apply border-warning-200 bg-warning-50': {},
        },
        '.stat-card-danger': {
          '@apply border-danger-200 bg-danger-50': {},
        },

        // Прогресс бары и индикаторы
        '.progress-bar': {
          '@apply w-full bg-gray-200 rounded-full h-2 overflow-hidden': {},
        },
        '.progress-fill': {
          '@apply h-full bg-primary-500 rounded-full transition-all duration-500 ease-out': {},
        },
        '.progress-fill-success': {
          '@apply bg-success-500': {},
        },
        '.progress-fill-warning': {
          '@apply bg-warning-500': {},
        },
        '.progress-fill-danger': {
          '@apply bg-danger-500': {},
        },

        // Табы анализа
        '.analysis-tab': {
          '@apply py-4 px-1 border-b-2 font-medium text-sm transition-colors duration-200': {},
        },
        '.analysis-tab-active': {
          '@apply border-primary-500 text-primary-600': {},
        },
        '.analysis-tab-inactive': {
          '@apply border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300': {},
        },

        // Эффекты для результатов
        '.pattern-highlight': {
          '@apply bg-gradient-to-r from-primary-50 to-secondary-50 border border-primary-200 rounded-lg p-3': {},
        },
        '.correlation-item': {
          '@apply flex items-center justify-between p-2 bg-gray-50 rounded transition-colors duration-200 hover:bg-gray-100': {},
        },

        // Recommendation badges
        '.recommendation-badge': {
          '@apply inline-flex items-center px-3 py-1 rounded-full text-sm font-medium': {},
        },
        '.recommendation-excellent': {
          '@apply bg-green-100 text-green-800 border border-green-200': {},
        },
        '.recommendation-good': {
          '@apply bg-blue-100 text-blue-800 border border-blue-200': {},
        },
        '.recommendation-average': {
          '@apply bg-yellow-100 text-yellow-800 border border-yellow-200': {},
        },
        '.recommendation-poor': {
          '@apply bg-red-100 text-red-800 border border-red-200': {},
        },

        // Loading states для анализа
        '.analysis-loading': {
          '@apply animate-pulse bg-gray-200 rounded': {},
        },
        '.analysis-skeleton': {
          '@apply space-y-3': {},
        },
      })
    }
  ],
}