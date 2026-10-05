import { create } from 'zustand'
import { createJSONStorage, persist } from 'zustand/middleware'

const storageKey = 'superx-session'
const previousSession = sessionStorage.getItem(storageKey)

if (!localStorage.getItem(storageKey) && previousSession) {
  localStorage.setItem(storageKey, previousSession)
}
sessionStorage.removeItem(storageKey)

export const useAppStore = create(persist((set) => ({
  accessToken: '',
  userRole: '',
  stocks: [],
  portfolio: null,
  selectedSymbol: 'AOT',
  authOpen: false,
  manageStocksOpen: false,
  error: '',
  setAccessToken: (accessToken) => set({ accessToken, userRole: '' }),
  setUserRole: (userRole) => set({ userRole }),
  setStocks: (stocks) => set({ stocks }),
  setPortfolio: (portfolio) => set({ portfolio }),
  setSelectedSymbol: (selectedSymbol) => set({ selectedSymbol }),
  setAuthOpen: (authOpen) => set({ authOpen }),
  setManageStocksOpen: (manageStocksOpen) => set({ manageStocksOpen }),
  setError: (error) => set({ error }),
  logout: () => set({ accessToken: '', userRole: '', portfolio: null }),
}), {
  name: storageKey,
  storage: createJSONStorage(() => localStorage),
  partialize: (state) => ({ accessToken: state.accessToken }),
}))