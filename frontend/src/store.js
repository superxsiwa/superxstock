import { create } from 'zustand'
import { createJSONStorage, persist } from 'zustand/middleware'

export const useAppStore = create(persist((set) => ({
  accessToken: '',
  stocks: [],
  portfolio: null,
  selectedSymbol: 'AOT',
  authOpen: false,
  error: '',
  setAccessToken: (accessToken) => set({ accessToken }),
  setStocks: (stocks) => set({ stocks }),
  setPortfolio: (portfolio) => set({ portfolio }),
  setSelectedSymbol: (selectedSymbol) => set({ selectedSymbol }),
  setAuthOpen: (authOpen) => set({ authOpen }),
  setError: (error) => set({ error }),
  logout: () => set({ accessToken: '', portfolio: null }),
}), {
  name: 'superx-session',
  storage: createJSONStorage(() => sessionStorage),
  partialize: (state) => ({ accessToken: state.accessToken }),
}))