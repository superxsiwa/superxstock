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
  updatePortfolioPrices: (prices) => set((state) => {
    if (!state.portfolio || !Array.isArray(prices)) return {}

    const pricesBySymbol = new Map()
    prices.forEach((quote) => {
      if (
        typeof quote?.symbol !== 'string'
        || typeof quote.price !== 'number'
        || !Number.isFinite(quote.price)
        || quote.price <= 0
      ) return

      const symbol = quote.symbol.trim().toUpperCase()
      pricesBySymbol.set(symbol, quote.price)
      pricesBySymbol.set(symbol.replace(/\.BK$/, ''), quote.price)
    })
    if (!pricesBySymbol.size) return {}

    let marketValue = 0
    let unrealizedPnl = 0
    let hasUnpricedPosition = false
    const positions = state.portfolio.positions.map((position) => {
      const symbol = typeof position.symbol === 'string'
        ? position.symbol.trim().toUpperCase()
        : ''
      const price = pricesBySymbol.get(symbol) ?? pricesBySymbol.get(symbol.replace(/\.BK$/, ''))
      if (price === undefined) {
        if (
          !position.price_available
          || typeof position.market_value !== 'number'
          || typeof position.unrealized_pnl !== 'number'
        ) {
          hasUnpricedPosition = true
        } else {
          marketValue += position.market_value
          unrealizedPnl += position.unrealized_pnl
        }
        return position
      }

      const positionMarketValue = price * position.quantity
      const positionUnrealizedPnl = (price - position.avg_price) * position.quantity
      marketValue += positionMarketValue
      unrealizedPnl += positionUnrealizedPnl
      return {
        ...position,
        price: Number(price.toFixed(2)),
        market_value: Number(positionMarketValue.toFixed(2)),
        unrealized_pnl: Number(positionUnrealizedPnl.toFixed(2)),
        price_available: true,
      }
    })
    const cash = state.portfolio.cash
    const priceable = !hasUnpricedPosition && Number.isFinite(cash)

    return {
      portfolio: {
        ...state.portfolio,
        positions,
        total_value: priceable ? Number((cash + marketValue).toFixed(2)) : null,
        unrealized_pnl: priceable ? Number(unrealizedPnl.toFixed(2)) : null,
      },
    }
  }),
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