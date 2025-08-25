import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { immer } from 'zustand/middleware/immer';
import { User, LotteryType, NotificationItem, Combination } from '../types';
export * from './auth';
export * from './app';

// Интерфейс для состояния приложения
interface AppState {
  // Пользователь и авторизация
  user: User | null;
  isAuthenticated: boolean;

  // UI состояние
  theme: 'light' | 'dark';
  sidebarOpen: boolean;
  selectedLottery: LotteryType;

  // Уведомления
  notifications: NotificationItem[];

  // Генерация комбинаций
  recentCombinations: Combination[];
  favoriteCombinations: Combination[];

  generation: {
  isGenerating: boolean;
  results: any | null;
  error: any | null;
    };

  // Настройки
  settings: {
    autoRefresh: boolean;
    showAnimations: boolean;
    soundEnabled: boolean;
    defaultCombinationsCount: number;
    preferredStrategy: string;
  };
}

// Интерфейс для действий
interface AppActions {
  // Пользователь
  setUser: (user: User | null) => void;
  login: (user: User) => void;
  logout: () => void;
  updateUserSubscription: (status: string, plan?: string) => void;

  // UI
  setTheme: (theme: 'light' | 'dark') => void;
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;
  setSelectedLottery: (lottery: LotteryType) => void;

  // Уведомления
  addNotification: (notification: Omit<NotificationItem, 'id' | 'timestamp'>) => void;
  removeNotification: (id: string) => void;
  markNotificationAsRead: (id: string) => void;
  clearNotifications: () => void;

  // Комбинации
  addRecentCombination: (combination: Combination) => void;
  addFavoriteCombination: (combination: Combination) => void;
  removeFavoriteCombination: (index: number) => void;
  clearRecentCombinations: () => void;

  // Настройки
  updateSettings: (settings: Partial<AppState['settings']>) => void;
  resetSettings: () => void;

  // Генерация
  startGeneration: () => void;
  setGenerationSuccess: (results: any) => void;
  setGenerationError: (error: any) => void;
  resetGeneration: () => void;
}

// Состояние по умолчанию
const defaultState: AppState = {
  user: null,
  isAuthenticated: false,
  theme: 'light',
  sidebarOpen: true,
  selectedLottery: '4x20',
  notifications: [],
  recentCombinations: [],
  favoriteCombinations: [],
  settings: {
    autoRefresh: true,
    showAnimations: true,
    soundEnabled: false,
    defaultCombinationsCount: 3,
    preferredStrategy: 'rf_ranked',
  },
  generation: {
  isGenerating: false,
  results: null,
  error: null,
  },
};

// Создаем store
export const useAppStore = create<AppState & AppActions>()(
  persist(
    immer((set, get) => ({
      ...defaultState,

      // Действия пользователя
      setUser: (user) => set((state) => {
        state.user = user;
        state.isAuthenticated = !!user;
      }),

      login: (user) => set((state) => {
        state.user = user;
        state.isAuthenticated = true;
      }),

      logout: () => set((state) => {
        state.user = null;
        state.isAuthenticated = false;
        state.recentCombinations = [];
        state.notifications = [];
      }),

      updateUserSubscription: (status, plan) => set((state) => {
        if (state.user) {
          state.user.subscription_status = status as any;
          if (plan && state.user.preferences) {
            state.user.preferences.subscription_plan = plan as any;
          }
        }
      }),

      // UI действия
      setTheme: (theme) => set((state) => {
        state.theme = theme;
      }),

      toggleSidebar: () => set((state) => {
        state.sidebarOpen = !state.sidebarOpen;
      }),

      setSidebarOpen: (open) => set((state) => {
        state.sidebarOpen = open;
      }),

      setSelectedLottery: (lottery) => set((state) => {
        state.selectedLottery = lottery;
        // Сохраняем выбор в localStorage для других частей приложения
        localStorage.setItem('selectedLottery', lottery);
      }),

      // Уведомления
      addNotification: (notification) => set((state) => {
        const newNotification: NotificationItem = {
          ...notification,
          id: Date.now().toString() + Math.random().toString(36).substr(2, 9),
          timestamp: new Date().toISOString(),
          read: false,
        };
        state.notifications.unshift(newNotification);

        // Ограничиваем количество уведомлений
        if (state.notifications.length > 50) {
          state.notifications = state.notifications.slice(0, 50);
        }
      }),

      removeNotification: (id) => set((state) => {
        state.notifications = state.notifications.filter(n => n.id !== id);
      }),

      markNotificationAsRead: (id) => set((state) => {
        const notification = state.notifications.find(n => n.id === id);
        if (notification) {
          notification.read = true;
        }
      }),

      clearNotifications: () => set((state) => {
        state.notifications = [];
      }),

      // Комбинации
      addRecentCombination: (combination) => set((state) => {
        state.recentCombinations.unshift(combination);

        // Ограничиваем количество недавних комбинаций
        if (state.recentCombinations.length > 20) {
          state.recentCombinations = state.recentCombinations.slice(0, 20);
        }
      }),

      addFavoriteCombination: (combination) => set((state) => {
        // Проверяем, нет ли уже такой комбинации
        const exists = state.favoriteCombinations.some(fav =>
          JSON.stringify(fav.field1) === JSON.stringify(combination.field1) &&
          JSON.stringify(fav.field2) === JSON.stringify(combination.field2)
        );

        if (!exists) {
          state.favoriteCombinations.push(combination);

          // Ограничиваем количество избранных
          if (state.favoriteCombinations.length > 50) {
            state.favoriteCombinations = state.favoriteCombinations.slice(0, 50);
          }
        }
      }),

      removeFavoriteCombination: (index) => set((state) => {
        state.favoriteCombinations.splice(index, 1);
      }),

      clearRecentCombinations: () => set((state) => {
        state.recentCombinations = [];
      }),

      // Настройки
      updateSettings: (newSettings) => set((state) => {
        state.settings = { ...state.settings, ...newSettings };
      }),

      // Генерация
      startGeneration: () => set((state) => {
        state.generation.isGenerating = true;
        state.generation.results = null;
        state.generation.error = null;
      }),

      setGenerationSuccess: (results) => set((state) => {
        state.generation.isGenerating = false;
        state.generation.results = results;
        state.generation.error = null;
      }),

      setGenerationError: (error) => set((state) => {
        state.generation.isGenerating = false;
        state.generation.results = null;
        state.generation.error = error;
      }),

      resetGeneration: () => set((state) => {
        state.generation = defaultState.generation;
      }),

      resetSettings: () => set((state) => {
        state.settings = defaultState.settings;
      }),
    })),
    {
      name: 'lottery-app-storage',
      storage: createJSONStorage(() => localStorage),
      // Указываем какие части состояния сохранять
      partialize: (state) => ({
        user: state.user,
        isAuthenticated: state.isAuthenticated,
        theme: state.theme,
        selectedLottery: state.selectedLottery,
        favoriteCombinations: state.favoriteCombinations,
        settings: state.settings,
        // Не сохраняем уведомления и недавние комбинации
      }),
    }
  )
);

// Селекторы для удобного доступа к данным
export const useUser = () => useAppStore((state) => state.user);
export const useIsAuthenticated = () => useAppStore((state) => state.isAuthenticated);
export const useTheme = () => useAppStore((state) => state.theme);
export const useSidebarOpen = () => useAppStore((state) => state.sidebarOpen);
export const useSelectedLottery = () => useAppStore((state) => state.selectedLottery);
export const useNotifications = () => useAppStore((state) => state.notifications);
export const useUnreadNotificationsCount = () =>
  useAppStore((state) => state.notifications.filter(n => !n.read).length);
export const useRecentCombinations = () => useAppStore((state) => state.recentCombinations);
export const useFavoriteCombinations = () => useAppStore((state) => state.favoriteCombinations);
export const useSettings = () => useAppStore((state) => state.settings);

// Селекторы для генерации
export const useGenerationState = () => useAppStore((state) => state.generation);
export const useGenerationActions = () => useAppStore((state) => ({
  startGeneration: state.startGeneration,
  setGenerationSuccess: state.setGenerationSuccess,
  setGenerationError: state.setGenerationError,
  resetGeneration: state.resetGeneration,
}));

// Действия
export const useAppActions = () => useAppStore((state) => ({
  setUser: state.setUser,
  login: state.login,
  logout: state.logout,
  updateUserSubscription: state.updateUserSubscription,
  setTheme: state.setTheme,
  toggleSidebar: state.toggleSidebar,
  setSidebarOpen: state.setSidebarOpen,
  setSelectedLottery: state.setSelectedLottery,
  addNotification: state.addNotification,
  removeNotification: state.removeNotification,
  markNotificationAsRead: state.markNotificationAsRead,
  clearNotifications: state.clearNotifications,
  addRecentCombination: state.addRecentCombination,
  addFavoriteCombination: state.addFavoriteCombination,
  removeFavoriteCombination: state.removeFavoriteCombination,
  clearRecentCombinations: state.clearRecentCombinations,
  updateSettings: state.updateSettings,
  resetSettings: state.resetSettings,
}));

// Хук для работы с авторизацией
export const useAuth = () => {
  const user = useUser();
  const isAuthenticated = useIsAuthenticated();
  const { login, logout, setUser } = useAppActions();

  return {
    user,
    isAuthenticated,
    login,
    logout,
    setUser,
    hasSubscription: user?.subscription_status === 'active',
    subscriptionPlan: user?.preferences?.subscription_plan || 'basic',
  };
};

// Хук для работы с уведомлениями
export const useNotificationActions = () => {
  const { addNotification, removeNotification, markNotificationAsRead, clearNotifications } = useAppActions();

  return {
     showSuccess: (title: string, message: string) => {
      addNotification({ type: 'success', title, message, autoClose: true, read: false });
    },
    showError: (title: string, message: string) => {
      addNotification({ type: 'error', title, message, autoClose: false, read: false });
    },
    showWarning: (title: string, message: string) => {
      addNotification({ type: 'warning', title, message, autoClose: true, read: false });
    },
    showInfo: (title: string, message: string) => {
      addNotification({ type: 'info', title, message, autoClose: true, read: false });
    },
    removeNotification,
    markNotificationAsRead,
    clearNotifications,
  };
};
// Реэкспорт основных хуков для удобства
export { useAuthStore } from './auth';
