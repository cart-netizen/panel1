// src/store/app.ts
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface AppState {
  sidebarOpen: boolean;
  selectedLottery: string;
  theme: 'light' | 'dark';
  notifications: Array<{
    id: string;
    type: 'success' | 'error' | 'warning' | 'info';
    message: string;
    timestamp: number;
  }>;
}

interface AppActions {
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;
  setSelectedLottery: (lottery: string) => void;
  setTheme: (theme: 'light' | 'dark') => void;
  addNotification: (notification: Omit<AppState['notifications'][0], 'id' | 'timestamp'>) => void;
  removeNotification: (id: string) => void;
  clearNotifications: () => void;
  // Действия из auth для совместимости
  setUser: (user: any) => void;
  logout: () => void;
}

type AppStore = AppState & AppActions;

export const useAppStore = create<AppStore>()(
  persist(
    (set, get) => ({
      // Состояние
      sidebarOpen: false,
      selectedLottery: '4x20',
      theme: 'light',
      notifications: [],

      // Действия
      toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),

      setSidebarOpen: (open) => set({ sidebarOpen: open }),

      setSelectedLottery: (lottery) => set({ selectedLottery: lottery }),

      setTheme: (theme) => set({ theme }),

      addNotification: (notification) => set((state) => ({
        notifications: [
          ...state.notifications,
          {
            ...notification,
            id: Math.random().toString(36).substr(2, 9),
            timestamp: Date.now(),
          }
        ]
      })),

      removeNotification: (id) => set((state) => ({
        notifications: state.notifications.filter(n => n.id !== id)
      })),

      clearNotifications: () => set({ notifications: [] }),

      // Импортируем действия из auth store для совместимости
      setUser: (user) => {
        const { setUser } = require('./auth').useAuthStore.getState();
        setUser(user);
      },

      logout: () => {
        const { logout } = require('./auth').useAuthStore.getState();
        logout();
      },
    }),
    {
      name: 'app-storage',
      partialize: (state) => ({
        selectedLottery: state.selectedLottery,
        theme: state.theme,
      }),
    }
  )
);

// Хуки для удобного использования
export const useSidebarOpen = () => useAppStore((state) => state.sidebarOpen);
export const useSelectedLottery = () => useAppStore((state) => state.selectedLottery);
export const useTheme = () => useAppStore((state) => state.theme);
export const useNotifications = () => useAppStore((state) => state.notifications);

export const useAppActions = () => {
  const {
    toggleSidebar,
    setSidebarOpen,
    setSelectedLottery,
    setTheme,
    addNotification,
    removeNotification,
    clearNotifications,
    setUser,
    logout,
  } = useAppStore();

  return {
    toggleSidebar,
    setSidebarOpen,
    setSelectedLottery,
    setTheme,
    addNotification,
    removeNotification,
    clearNotifications,
    setUser,
    logout,
  };
};