// src/store/auth.ts
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface User {
  id: string;
  email: string;
  full_name?: string;
  subscription_status: 'active' | 'inactive' | 'trial';
  subscription_plan?: 'basic' | 'premium' | 'pro';
  created_at: string;
}

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  hasSubscription: boolean;
  subscriptionPlan: string | null;
  loading: boolean;
}

interface AuthActions {
  setUser: (user: User | null) => void;
  login: (user: User) => void;
  logout: () => void;
  setLoading: (loading: boolean) => void;
}

type AuthStore = AuthState & AuthActions;

export const useAuthStore = create<AuthStore>()(
  persist(
    (set, get) => ({
      // Состояние
      user: null,
      isAuthenticated: false,
      hasSubscription: false,
      subscriptionPlan: null,
      loading: false,

      // Действия
      setUser: (user) => set((state) => ({
        user,
        isAuthenticated: !!user,
        hasSubscription: user?.subscription_status === 'active',
        subscriptionPlan: user?.subscription_plan || null,
      })),

      login: (user) => set({
        user,
        isAuthenticated: true,
        hasSubscription: user.subscription_status === 'active',
        subscriptionPlan: user.subscription_plan || null,
        loading: false,
      }),

      logout: () => {
        // Очищаем токены
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');

        set({
          user: null,
          isAuthenticated: false,
          hasSubscription: false,
          subscriptionPlan: null,
          loading: false,
        });
      },

      setLoading: (loading) => set({ loading }),
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        user: state.user,
        isAuthenticated: state.isAuthenticated,
        hasSubscription: state.hasSubscription,
        subscriptionPlan: state.subscriptionPlan,
      }),
    }
  )
);

// Хуки для удобного использования
export const useAuth = () => {
  const { user, isAuthenticated, hasSubscription, subscriptionPlan, loading } = useAuthStore();
  return { user, isAuthenticated, hasSubscription, subscriptionPlan, loading };
};

export const useUser = () => useAuthStore((state) => state.user);