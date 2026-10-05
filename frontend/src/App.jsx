import { useEffect, useState } from 'react'
import { Line } from 'react-chartjs-2'
import {
  CategoryScale,
  Chart as ChartJS,
  Filler,
  LinearScale,
  LineElement,
  PointElement,
  Tooltip,
} from 'chart.js'
import { apiRequest } from './api'
import { useTranslation } from 'react-i18next'
import { useAppStore } from './store'
import './App.css'

ChartJS.register(CategoryScale, Filler, LinearScale, LineElement, PointElement, Tooltip)

function App() {
  const { t, i18n } = useTranslation()
  const money = new Intl.NumberFormat(i18n.language === 'th' ? 'th-TH' : 'en-US', {
    style: 'currency',
    currency: 'THB',
    maximumFractionDigits: 2,
  })
  const accessToken = useAppStore((state) => state.accessToken)
  const userRole = useAppStore((state) => state.userRole)
  const stocks = useAppStore((state) => state.stocks)
  const portfolio = useAppStore((state) => state.portfolio)
  const selectedSymbol = useAppStore((state) => state.selectedSymbol)
  const authOpen = useAppStore((state) => state.authOpen)
  const error = useAppStore((state) => state.error)
  const setStocks = useAppStore((state) => state.setStocks)
  const setPortfolio = useAppStore((state) => state.setPortfolio)
  const setSelectedSymbol = useAppStore((state) => state.setSelectedSymbol)
  const setAuthOpen = useAppStore((state) => state.setAuthOpen)
  const setManageStocksOpen = useAppStore((state) => state.setManageStocksOpen)
  const setError = useAppStore((state) => state.setError)
  const setAccessToken = useAppStore((state) => state.setAccessToken)
  const setUserRole = useAppStore((state) => state.setUserRole)
  const logout = useAppStore((state) => state.logout)
  const [candles, setCandles] = useState([])
  const [authMode, setAuthMode] = useState('login')
  const [authMessage, setAuthMessage] = useState('')
  const [tradeMessage, setTradeMessage] = useState('')
  const [busy, setBusy] = useState(false)
  const [quantity, setQuantity] = useState('50')
  const [action, setAction] = useState('BUY')
  const [tradeSymbol, setTradeSymbol] = useState('AOT')
  
  const manageStocksOpen = useAppStore((state) => state.manageStocksOpen)
  const isAdmin = userRole === 'admin'
  const [rawStocks, setRawStocks] = useState([])
  const [newStockSymbol, setNewStockSymbol] = useState('')
  const [stockMessage, setStockMessage] = useState('')
  const [configOpen, setConfigOpen] = useState(false)
  const [maxStocks, setMaxStocks] = useState('')
  const [configMessage, setConfigMessage] = useState('')
  const [configBusy, setConfigBusy] = useState(false)
  const [watchlistOpen, setWatchlistOpen] = useState(false)
  const [watchlistSymbols, setWatchlistSymbols] = useState([])
  const [watchlistInput, setWatchlistInput] = useState('')
  const [watchlistMessage, setWatchlistMessage] = useState('')
  const [watchlistBusy, setWatchlistBusy] = useState(false)
  const [alertsOpen, setAlertsOpen] = useState(false)
  const [lineUserId, setLineUserId] = useState('')
  const [lineChannelAccessToken, setLineChannelAccessToken] = useState('')
  const [lineConfigured, setLineConfigured] = useState(false)
  const [notificationMessage, setNotificationMessage] = useState('')
  const [notificationBusy, setNotificationBusy] = useState(false)
  const [signalAnalytics, setSignalAnalytics] = useState(null)
  const [signalAnalyticsError, setSignalAnalyticsError] = useState('')

  async function fetchRawStocks() {
    try {
      const res = await apiRequest('/api/stocks')
      setRawStocks(res)
    } catch (e) {
      setStockMessage(e.message)
    }
  }

  useEffect(() => {
    if (!manageStocksOpen) return undefined
    let active = true
    apiRequest('/api/stocks')
      .then((result) => {
        if (active) setRawStocks(result)
      })
      .catch((requestError) => {
        if (active) setStockMessage(requestError.message)
      })
    return () => { active = false }
  }, [manageStocksOpen])

  useEffect(() => {
    if (!configOpen) return undefined
    let active = true
    apiRequest('/api/config')
      .then((result) => {
        if (active) {
          setMaxStocks(String(result.MAX_STOCKS ?? ''))
          setConfigMessage('')
        }
      })
      .catch((requestError) => {
        if (active) setConfigMessage(requestError.message)
      })
    return () => { active = false }
  }, [configOpen])

  useEffect(() => {
    if (!watchlistOpen) return undefined
    let active = true
    apiRequest('/api/watchlist')
      .then((result) => {
        if (active) {
          setWatchlistSymbols(result)
          setWatchlistMessage('')
        }
      })
      .catch((requestError) => {
        if (active) setWatchlistMessage(requestError.message)
      })
    return () => { active = false }
  }, [watchlistOpen])

  useEffect(() => {
    if (!alertsOpen) return undefined
    let active = true
    apiRequest('/api/notifications/settings')
      .then((result) => {
        if (active) {
          setLineUserId(result.line_user_id || '')
          setLineConfigured(result.configured)
          setLineChannelAccessToken('')
          setNotificationMessage('')
        }
      })
      .catch((requestError) => {
        if (active) setNotificationMessage(requestError.message)
      })
    return () => { active = false }
  }, [alertsOpen])

  async function addWatchlistSymbol(event) {
    event.preventDefault()
    setWatchlistBusy(true)
    setWatchlistMessage('')
    try {
      const result = await apiRequest('/api/watchlist', {
        method: 'POST',
        body: JSON.stringify({ symbol: watchlistInput.trim().toUpperCase() }),
      })
      setWatchlistSymbols((current) => [...current, result.symbol].sort())
      setWatchlistInput('')
      setWatchlistMessage(t('watchlist.added'))
    } catch (requestError) {
      setWatchlistMessage(requestError.message)
    } finally {
      setWatchlistBusy(false)
    }
  }

  async function removeWatchlistSymbol(symbol) {
    setWatchlistBusy(true)
    setWatchlistMessage('')
    try {
      await apiRequest(`/api/watchlist/${encodeURIComponent(symbol)}`, { method: 'DELETE' })
      setWatchlistSymbols((current) => current.filter((item) => item !== symbol))
      setWatchlistMessage(t('watchlist.removed'))
    } catch (requestError) {
      setWatchlistMessage(requestError.message)
    } finally {
      setWatchlistBusy(false)
    }
  }

  async function saveNotificationSettings(event) {
    event.preventDefault()
    setNotificationBusy(true)
    setNotificationMessage('')
    try {
      const body = { line_user_id: lineUserId.trim() }
      if (lineChannelAccessToken.trim()) body.channel_access_token = lineChannelAccessToken.trim()
      const result = await apiRequest('/api/notifications/settings', {
        method: 'PUT',
        body: JSON.stringify(body),
      })
      setLineUserId(result.line_user_id)
      setLineConfigured(result.configured)
      setLineChannelAccessToken('')
      setNotificationMessage(t('notifications.saved'))
    } catch (requestError) {
      setNotificationMessage(requestError.message)
    } finally {
      setNotificationBusy(false)
    }
  }

  async function sendTestNotification() {
    setNotificationBusy(true)
    setNotificationMessage('')
    try {
      await apiRequest('/api/notifications/test', { method: 'POST' })
      setNotificationMessage(t('notifications.testSent'))
    } catch (requestError) {
      setNotificationMessage(requestError.message)
    } finally {
      setNotificationBusy(false)
    }
  }

  async function disconnectNotifications() {
    setNotificationBusy(true)
    setNotificationMessage('')
    try {
      await apiRequest('/api/notifications/settings', { method: 'DELETE' })
      setLineUserId('')
      setLineConfigured(false)
      setLineChannelAccessToken('')
      setNotificationMessage(t('notifications.disconnected'))
    } catch (requestError) {
      setNotificationMessage(requestError.message)
    } finally {
      setNotificationBusy(false)
    }
  }

  async function submitConfig(e) {
    e.preventDefault()
    setConfigBusy(true)
    setConfigMessage('')
    try {
      await apiRequest('/api/config', {
        method: 'PUT',
        body: JSON.stringify({ key: 'MAX_STOCKS', value: Number(maxStocks) }),
      })
      setConfigMessage(t('settings.saved'))
    } catch (requestError) {
      setConfigMessage(requestError.message)
    } finally {
      setConfigBusy(false)
    }
  }

  async function submitAddStock(e) {
    e.preventDefault()
    setBusy(true)
    setStockMessage('')
    try {
      await apiRequest('/api/stocks/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbol: newStockSymbol })
      })
      setNewStockSymbol('')
      await fetchRawStocks()
    } catch (err) {
      setStockMessage(err.message)
    } finally {
      setBusy(false)
    }
  }

  async function deleteStock(id) {
    if (!window.confirm("Are you sure?")) return
    setBusy(true)
    setStockMessage('')
    try {
      await apiRequest(`/api/stocks/${id}`, { method: 'DELETE' })
      await fetchRawStocks()
    } catch (err) {
      setStockMessage(err.message)
    } finally {
      setBusy(false)
    }
  }

  useEffect(() => {
    let active = true
    setError('')

    apiRequest('/api/scan')
      .then((result) => {
        if (active) {
          setStocks(result.stocks || [])
          if (result.stocks?.length && !result.stocks.some((item) => item.symbol === selectedSymbol)) {
            setSelectedSymbol(result.stocks[0].symbol)
          }
        }
      })
      .catch((requestError) => {
        if (active) setError(requestError.message)
      })

    if (accessToken) {
      apiRequest('/api/auth/me')
        .then((profile) => {
          if (active) setUserRole(profile.role)
        })
        .catch((requestError) => {
          if (active) setError(requestError.message)
        })
      apiRequest('/api/portfolio')
        .then((result) => {
          if (active) setPortfolio(result)
        })
        .catch((requestError) => {
          if (active) setError(requestError.message)
        })
    } else {
      setPortfolio(null)
      setAuthOpen(true)
    }

    return () => {
      active = false
    }
  }, [accessToken, selectedSymbol, setAuthOpen, setError, setPortfolio, setSelectedSymbol, setStocks, setUserRole])

  useEffect(() => {
    if (!accessToken) return undefined
    let active = true
    apiRequest('/api/analytics/signals')
      .then((result) => {
        if (active) {
          setSignalAnalytics(result)
          setSignalAnalyticsError('')
        }
      })
      .catch((requestError) => {
        if (active) setSignalAnalyticsError(requestError.message)
      })
    return () => { active = false }
  }, [accessToken])

  useEffect(() => {
    if (!selectedSymbol) return undefined
    let active = true
    apiRequest(`/api/charts/${encodeURIComponent(selectedSymbol)}`)
      .then((result) => {
        if (active) setCandles(result.candles || [])
      })
      .catch((requestError) => {
        if (active) setError(requestError.message)
      })
    return () => {
      active = false
    }
  }, [selectedSymbol, setError])

  async function refreshScan() {
    setBusy(true)
    setError('')
    try {
      const result = await apiRequest('/api/scan')
      setStocks(result.stocks || [])
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setBusy(false)
    }
  }

  async function submitAuth(event) {
    event.preventDefault()
    setBusy(true)
    setAuthMessage('')
    const form = new FormData(event.currentTarget)
    const email = String(form.get('email')).trim()
    const password = String(form.get('password'))

    try {
      if (authMode === 'register') {
        await apiRequest('/api/auth/register', {
          method: 'POST',
          body: JSON.stringify({ email, password }),
        })
        setAuthMode('login')
        setAuthMessage(t('auth.accountCreated'))
        return
      }

      const result = await apiRequest('/api/auth/token', {
        method: 'POST',
        body: new URLSearchParams({ username: email, password }),
      })
      setAccessToken(result.access_token)
      setAuthOpen(false)
      setAuthMessage('')
    } catch (requestError) {
      setAuthMessage(requestError.message)
    } finally {
      setBusy(false)
    }
  }

  async function submitTrade(event) {
    event.preventDefault()
    setTradeMessage('')
    try {
      const result = await apiRequest('/api/paper-trade', {
        method: 'POST',
        body: JSON.stringify({
          symbol: tradeSymbol.trim().toUpperCase(),
          action,
          quantity: Number(quantity),
        }),
      })
      const actionLabel = action === 'BUY' ? t('trade.buy') : t('trade.sell')
      setTradeMessage(t('trade.success', {
        action: actionLabel,
        quantity,
        symbol: tradeSymbol.trim().toUpperCase(),
      }))
      setPortfolio(result.portfolio)
      await refreshScan()
    } catch (requestError) {
      setTradeMessage(requestError.message)
    }
  }

  const selectedStock = stocks.find((stock) => stock.symbol === selectedSymbol)
  const buyCount = stocks.filter((stock) => stock.recommendation === 'BUY').length
  const chartData = {
    labels: candles.map((_, index) => index + 1),
    datasets: [{
      data: candles.map((candle) => candle.close),
      borderColor: '#1a9871',
      backgroundColor: 'rgba(26, 152, 113, 0.12)',
      borderWidth: 2,
      pointRadius: 0,
      pointHitRadius: 8,
      fill: true,
      tension: 0.18,
    }],
  }
  const analyticsSummary = signalAnalytics?.summary
  const analyticsChartData = {
    labels: signalAnalytics?.equity_curve.map((point) => point.date) || [],
    datasets: [{
      data: signalAnalytics?.equity_curve.map((point) => point.pnl_thb) || [],
      borderColor: '#55799a',
      backgroundColor: 'rgba(85, 121, 154, 0.12)',
      borderWidth: 2,
      pointRadius: 2,
      pointHitRadius: 8,
      fill: true,
      tension: 0.18,
    }],
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="#overview" aria-label={t('document.title')}>
          <span className="brand-mark">SX</span>
          <span><strong>SuperX</strong><small>{t('brand.tagline')}</small></span>
        </a>
        <nav className="nav-list" aria-label={t('navigation.label')}>
          <a className="nav-item active" href="#overview">{t('navigation.overview')}</a>
          <a className="nav-item" href="#opportunities">{t('navigation.opportunities')}</a>
          {accessToken && <a className="nav-item" href="#backtesting">{t('navigation.backtesting')}</a>}
          <a className="nav-item" href="#portfolio">{t('navigation.portfolio')}</a>
          {accessToken && (
            <>
              <button className="nav-item nav-action" onClick={() => setWatchlistOpen(true)} type="button">{t('actions.myWatchlist')}</button>
              <button className="nav-item nav-action" onClick={() => setAlertsOpen(true)} type="button">{t('actions.alertSettings')}</button>
            </>
          )}
          {isAdmin && (
            <>
              <button className="nav-item nav-action" onClick={() => setConfigOpen(true)} type="button">{t('actions.settings')}</button>
              <button className="nav-item nav-action" onClick={() => setManageStocksOpen(true)} type="button">{t('actions.manageStocks', { defaultValue: 'Manage Stocks' })}</button>
            </>
          )}
        </nav>
          <div className="sidebar-status"><span className="status-dot" /><span>{t('market.watchlistHint')}</span><strong>{t('market.daily')}</strong></div>
        <div className="sidebar-bottom"><span className="eyebrow">{t('session.label')}</span><strong>{accessToken ? t('session.authenticated') : t('session.guest')}</strong></div>
      </aside>

      <main className="main-panel" id="overview">
        <header className="topbar">
          <div><p className="eyebrow">{t('header.eyebrow')}</p><h1>{t('header.title')}</h1></div>
          <div className="topbar-actions">
            <span className="market-date">{t('header.marketClose')}</span>
            <div aria-label={t('language.label')} className="language-switch" role="group">
              <button aria-pressed={i18n.language === 'th'} className={i18n.language === 'th' ? 'language-button active' : 'language-button'} onClick={() => i18n.changeLanguage('th')} type="button">{t('language.thai')}</button>
              <button aria-pressed={i18n.language === 'en'} className={i18n.language === 'en' ? 'language-button active' : 'language-button'} onClick={() => i18n.changeLanguage('en')} type="button">{t('language.english')}</button>
            </div>
            {accessToken ? (
              <>
                {isAdmin && <>
                  <button className="button button-quiet" onClick={() => { setConfigOpen(false); setManageStocksOpen(true) }} type="button">{t('actions.manageStocks', { defaultValue: 'Manage Stocks' })}</button>
                  <button className="button button-quiet" onClick={() => { setManageStocksOpen(false); setConfigOpen(true) }} type="button">{t('actions.settings')}</button>
                </>}
                <button className="button button-quiet" onClick={logout} type="button">{t('actions.signOut')}</button>
              </>
            ) : (
              <button className="button button-quiet" onClick={() => setAuthOpen(true)} type="button">{t('actions.signIn')}</button>
            )}
            <button className="button button-primary" disabled={busy} onClick={refreshScan} type="button">{busy ? t('actions.refreshing') : t('actions.refresh')}</button>
          </div>
        </header>

        {error && <div className="notice notice-error" role="alert">{error}</div>}

        <section className="metrics" aria-label={t('market.summary')}>
          <div className="metric"><span>{t('market.buySetups')}</span><strong>{buyCount}</strong><small>{t('market.buySetupsHint')}</small></div>
          <div className="metric"><span>{t('market.watchlist')}</span><strong>{stocks.length}</strong><small>{t('market.watchlistHint')}</small></div>
          <div className="metric" id="portfolio"><span>{t('market.portfolioValue')}</span><strong>{portfolio ? money.format(portfolio.total_value) : '-'}</strong><small>{portfolio ? t('market.accountValue') : t('market.signInToView')}</small></div>
          <div className="metric"><span>{t('market.availableCash')}</span><strong>{portfolio ? money.format(portfolio.cash) : '-'}</strong><small>{portfolio ? t('market.paperBalance') : t('market.accountBalance')}</small></div>
        </section>

        <section className="work-grid">
          <article className="panel chart-panel">
            <div className="panel-heading"><div><p className="eyebrow">{t('chart.eyebrow')}</p><h2>{selectedSymbol || t('chart.selectSymbol')}</h2></div><span className={`signal-tag ${selectedStock?.recommendation?.toLowerCase() || 'watch'}`}>{t(`signals.${selectedStock?.recommendation || 'WATCH'}`)}</span></div>
            {candles.length ? (
              <div className="chart-wrap"><Line data={chartData} options={{
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false }, tooltip: { intersect: false, mode: 'index' } },
                scales: {
                  x: { display: false, grid: { display: false } },
                  y: { border: { display: false }, grid: { color: '#e7ece8' }, ticks: { color: '#77817b', maxTicksLimit: 5 } },
                },
              }} /></div>
            ) : <div className="chart-empty">{t('chart.empty')}</div>}
            <div className="chart-footer"><span>{t('chart.period')}</span><span>{candles.length ? t('chart.latestClose', { price: money.format(candles.at(-1).close) }) : t('chart.noData')}</span></div>
          </article>

          <article className="panel trade-panel">
            <div className="panel-heading"><div><p className="eyebrow">{t('trade.eyebrow')}</p><h2>{t('trade.title')}</h2></div></div>
            <form className="trade-form" onSubmit={submitTrade}>
              <label>{t('trade.symbol')}<input maxLength="10" onChange={(event) => setTradeSymbol(event.target.value)} value={tradeSymbol} required /></label>
              <div className="form-split">
                <label>{t('trade.quantity')}<input min="1" onChange={(event) => setQuantity(event.target.value)} type="number" value={quantity} required /></label>
                <label>{t('trade.side')}<select onChange={(event) => setAction(event.target.value)} value={action}><option value="BUY">{t('trade.buy')}</option><option value="SELL">{t('trade.sell')}</option></select></label>
              </div>
              <button className="button button-primary trade-submit" disabled={!accessToken || busy} type="submit">{accessToken ? t('trade.submit') : t('trade.signInToTrade')}</button>
              <p className="form-message" role="status">{tradeMessage}</p>
            </form>
          </article>
        </section>

        <section className="panel table-panel" id="opportunities">
          <div className="panel-heading table-heading"><div><p className="eyebrow">{t('opportunities.eyebrow')}</p><h2>{t('opportunities.title')}</h2></div><span className="table-count">{t('opportunities.count', { count: stocks.length })}</span></div>
          <div className="table-scroll"><table>
            <thead><tr><th>{t('table.symbol')}</th><th>{t('table.price')}</th><th>{t('table.rsi')}</th><th>{t('table.macd')}</th><th>{t('table.ema50')}</th><th>{t('table.ema90')}</th><th>{t('table.volume')}</th><th>{t('table.zone')}</th><th>{t('table.score')}</th><th>{t('table.signal')}</th></tr></thead>
            <tbody>{stocks.map((stock) => (
              <tr className={stock.symbol === selectedSymbol ? 'selected-row' : ''} key={stock.symbol} onClick={() => setSelectedSymbol(stock.symbol)}>
                <td><strong>{stock.symbol}</strong></td><td>{Number(stock.price).toFixed(2)}</td><td>{Number(stock.rsi).toFixed(1)}</td><td>{Number(stock.macd).toFixed(2)}</td><td>{Number(stock.ema50).toFixed(2)}</td><td>{Number(stock.ema90).toFixed(2)}</td><td>{Number(stock.volume_ratio).toFixed(2)}x</td><td>{t(`zones.${stock.action_zone}`, { defaultValue: stock.action_zone })}</td><td>{stock.score}</td><td><span className={`signal-tag ${stock.recommendation.toLowerCase()}`}>{t(`signals.${stock.recommendation}`, { defaultValue: stock.recommendation })}</span></td>
              </tr>
            ))}</tbody>
          </table></div>
          {!stocks.length && <p className="table-empty">{t('opportunities.empty')}</p>}
        </section>

        {accessToken && (
          <section aria-labelledby="backtest-title" className="panel backtest-panel" id="backtesting">
            <div className="panel-heading table-heading">
              <div><p className="eyebrow">{t('backtesting.eyebrow')}</p><h2 id="backtest-title">{t('backtesting.title')}</h2></div>
              <span className="table-count">{t('backtesting.signalCount', { count: analyticsSummary?.total_signals || 0 })}</span>
            </div>
            {signalAnalyticsError && <div className="notice notice-error" role="alert">{signalAnalyticsError}</div>}
            <div className="metrics backtest-metrics" aria-label={t('backtesting.summary')}>
              <div className="metric"><span>{t('backtesting.winRate')}</span><strong>{(analyticsSummary?.win_rate_pct || 0).toFixed(1)}%</strong><small>{t('backtesting.closedTrades', { count: analyticsSummary?.closed_trades || 0 })}</small></div>
              <div className="metric"><span>{t('backtesting.totalPnl')}</span><strong>{money.format(analyticsSummary?.total_pnl_thb || 0)}</strong><small>{t('backtesting.realizedPnl', { value: money.format(analyticsSummary?.realized_pnl_thb || 0) })}</small></div>
              <div className="metric"><span>{t('backtesting.unrealizedPnl')}</span><strong>{money.format(analyticsSummary?.unrealized_pnl_thb || 0)}</strong><small>{t('backtesting.openPositions', { count: analyticsSummary?.open_positions || 0 })}</small></div>
              <div className="metric"><span>{t('backtesting.maxDrawdown')}</span><strong>{money.format(analyticsSummary?.max_drawdown_thb || 0)}</strong><small>{t('backtesting.oneShareMethod')}</small></div>
            </div>
            {signalAnalytics?.equity_curve.length ? (
              <div className="backtest-chart">
                <Line data={analyticsChartData} options={{
                  responsive: true,
                  maintainAspectRatio: false,
                  plugins: { legend: { display: false }, tooltip: { intersect: false, mode: 'index' } },
                  scales: {
                    x: { border: { display: false }, grid: { display: false }, ticks: { maxTicksLimit: 8 } },
                    y: { border: { display: false }, grid: { color: '#e7ece8' }, ticks: { callback: (value) => money.format(value) } },
                  },
                }} />
              </div>
            ) : <p className="table-empty">{t('backtesting.empty')}</p>}
            <div className="backtest-tables">
              <div>
                <div className="panel-heading table-heading"><h3>{t('backtesting.closedTradesTitle')}</h3></div>
                <div className="table-scroll"><table>
                  <thead><tr><th>{t('table.symbol')}</th><th>{t('backtesting.buyDate')}</th><th>{t('backtesting.sellDate')}</th><th>{t('backtesting.return')}</th><th>{t('backtesting.pnl')}</th></tr></thead>
                  <tbody>{(signalAnalytics?.closed_trades || []).slice().reverse().map((trade) => (
                    <tr key={`${trade.symbol}-${trade.buy_date}-${trade.sell_date}`}>
                      <td><strong>{trade.symbol}</strong></td><td>{trade.buy_date}</td><td>{trade.sell_date}</td><td>{trade.return_pct.toFixed(2)}%</td><td>{money.format(trade.pnl_thb)}</td>
                    </tr>
                  ))}</tbody>
                </table></div>
              </div>
              <div>
                <div className="panel-heading table-heading"><h3>{t('backtesting.openPositionsTitle')}</h3></div>
                <div className="table-scroll"><table>
                  <thead><tr><th>{t('table.symbol')}</th><th>{t('backtesting.buyPrice')}</th><th>{t('backtesting.currentPrice')}</th><th>{t('backtesting.pnl')}</th></tr></thead>
                  <tbody>{(signalAnalytics?.open_trades || []).map((trade) => (
                    <tr key={`${trade.symbol}-${trade.buy_date}`}>
                      <td><strong>{trade.symbol}</strong></td><td>{money.format(trade.buy_price)}</td><td>{money.format(trade.current_price)}</td><td>{money.format(trade.pnl_thb)}</td>
                    </tr>
                  ))}</tbody>
                </table></div>
                {!signalAnalytics?.open_trades.length && <p className="table-empty">{t('backtesting.noOpenPositions')}</p>}
              </div>
            </div>
          </section>
        )}
      </main>

      {authOpen && (
        <div className="dialog-backdrop" role="presentation">
          <section aria-labelledby="auth-title" aria-modal="true" className="auth-dialog" role="dialog">
            <p className="eyebrow">{t('auth.eyebrow')}</p><h2 id="auth-title">{authMode === 'login' ? t('auth.signIn') : t('auth.createAccount')}</h2>
            <form className="auth-form" onSubmit={submitAuth}>
              <label>{t('auth.email')}<input autoComplete="email" name="email" required type="email" /></label>
              <label>{t('auth.password')}<input autoComplete={authMode === 'login' ? 'current-password' : 'new-password'} minLength="8" name="password" required type="password" /></label>
              <p className="form-message" role="status">{authMessage}</p>
              <button className="button button-primary" disabled={busy} type="submit">{authMode === 'login' ? t('auth.signIn') : t('auth.register')}</button>
            </form>
            <div className="dialog-actions">
              <button className="text-button" onClick={() => { setAuthMode(authMode === 'login' ? 'register' : 'login'); setAuthMessage('') }} type="button">{authMode === 'login' ? t('auth.createAccountAction') : t('auth.backToSignIn')}</button>
              <button className="text-button" onClick={() => setAuthOpen(false)} type="button">{t('actions.close')}</button>
            </div>
          </section>
        </div>
      )}

      {manageStocksOpen && (
        <div className="dialog-backdrop" role="presentation">
          <section aria-labelledby="manage-stocks-title" aria-modal="true" className="auth-dialog" role="dialog" style={{ maxWidth: '500px' }}>
            <p className="eyebrow">Settings</p><h2 id="manage-stocks-title">Manage Stocks</h2>
            <form className="trade-form" onSubmit={submitAddStock} style={{ display: 'flex', gap: '8px', marginBottom: '16px' }}>
              <input maxLength="15" onChange={(e) => setNewStockSymbol(e.target.value)} value={newStockSymbol} required placeholder="e.g. GULF.BK" style={{ flex: 1, padding: '8px', border: '1px solid #ccc', borderRadius: '4px' }} />
              <button className="button button-primary" disabled={busy} type="submit">Add</button>
            </form>
            <p className="form-message" role="status" style={{ color: stockMessage.includes('Cannot') ? 'red' : 'inherit' }}>{stockMessage}</p>
            <div className="table-scroll" style={{ maxHeight: '300px', overflowY: 'auto' }}>
              <table style={{ width: '100%', textAlign: 'left', borderCollapse: 'collapse' }}>
                <thead><tr><th style={{ paddingBottom: '8px', borderBottom: '1px solid #eee' }}>Symbol</th><th style={{ paddingBottom: '8px', borderBottom: '1px solid #eee', textAlign: 'right' }}>Action</th></tr></thead>
                <tbody>
                  {rawStocks.map(s => (
                    <tr key={s.id}>
                      <td style={{ padding: '8px 0', borderBottom: '1px solid #eee' }}><strong>{s.symbol}</strong></td>
                      <td style={{ padding: '8px 0', borderBottom: '1px solid #eee', textAlign: 'right' }}><button className="text-button" onClick={() => deleteStock(s.id)} type="button" style={{ color: 'red', cursor: 'pointer', background: 'none', border: 'none' }}>Delete</button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="dialog-actions" style={{ marginTop: '16px' }}>
              <button className="button button-quiet" onClick={() => setManageStocksOpen(false)} type="button">{t('actions.close')}</button>
            </div>
          </section>
        </div>
      )}

      {configOpen && (
        <div className="dialog-backdrop" role="presentation">
          <section aria-labelledby="config-title" aria-modal="true" className="auth-dialog config-dialog" role="dialog">
            <p className="eyebrow">{t('settings.eyebrow')}</p>
            <h2 id="config-title">{t('settings.title')}</h2>
            <form className="trade-form config-form" onSubmit={submitConfig}>
              <label htmlFor="max-stocks">{t('settings.maximumStocks')}
                <input id="max-stocks" min="1" onChange={(event) => setMaxStocks(event.target.value)} required step="1" type="number" value={maxStocks} />
              </label>
              <p className="form-message" role="status">{configMessage}</p>
              <div className="settings-actions">
                <button className="button button-quiet" onClick={() => setConfigOpen(false)} type="button">{t('actions.close')}</button>
                <button className="button button-primary" disabled={configBusy || !maxStocks} type="submit">{configBusy ? t('settings.saving') : t('settings.save')}</button>
              </div>
            </form>
          </section>
        </div>
      )}

      {watchlistOpen && (
        <div className="dialog-backdrop" role="presentation">
          <section aria-labelledby="watchlist-title" aria-modal="true" className="auth-dialog feature-dialog" role="dialog">
            <p className="eyebrow">{t('watchlist.eyebrow')}</p>
            <h2 id="watchlist-title">{t('watchlist.title')}</h2>
            <form className="feature-form watchlist-form" onSubmit={addWatchlistSymbol}>
              <label htmlFor="watchlist-symbol">{t('watchlist.symbol')}
                <input autoCapitalize="characters" id="watchlist-symbol" maxLength="20" onChange={(event) => setWatchlistInput(event.target.value)} required value={watchlistInput} />
              </label>
              <button className="button button-primary" disabled={watchlistBusy} type="submit">{t('watchlist.add')}</button>
            </form>
            <p className="form-message" role="status">{watchlistMessage}</p>
            <div className="table-scroll feature-table">
              <table>
                <thead><tr><th>{t('table.symbol')}</th><th>{t('table.price')}</th><th>{t('table.signal')}</th><th>{t('watchlist.action')}</th></tr></thead>
                <tbody>
                  {watchlistSymbols.map((symbol) => {
                    const stock = stocks.find((item) => item.symbol === symbol)
                    return (
                      <tr key={symbol}>
                        <td><strong>{symbol}</strong></td>
                        <td>{stock ? Number(stock.price).toFixed(2) : '-'}</td>
                        <td>{stock ? t(`signals.${stock.recommendation}`, { defaultValue: stock.recommendation }) : '-'}</td>
                        <td><button className="text-button" disabled={watchlistBusy} onClick={() => removeWatchlistSymbol(symbol)} type="button">{t('watchlist.remove')}</button></td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
            {!watchlistSymbols.length && <p className="table-empty">{t('watchlist.empty')}</p>}
            <div className="settings-actions">
              <button className="button button-quiet" onClick={() => setWatchlistOpen(false)} type="button">{t('actions.close')}</button>
            </div>
          </section>
        </div>
      )}

      {alertsOpen && (
        <div className="dialog-backdrop" role="presentation">
          <section aria-labelledby="alerts-title" aria-modal="true" className="auth-dialog feature-dialog" role="dialog">
            <p className="eyebrow">{t('notifications.eyebrow')}</p>
            <h2 id="alerts-title">{t('notifications.title')}</h2>
            <form className="feature-form alert-form" onSubmit={saveNotificationSettings}>
              <label htmlFor="line-user-id">{t('notifications.lineUserId')}
                <input autoComplete="off" id="line-user-id" pattern="U[0-9a-fA-F]{32}" required value={lineUserId} onChange={(event) => setLineUserId(event.target.value)} />
              </label>
              <label htmlFor="line-access-token">{t('notifications.channelAccessToken')}
                <input autoComplete="new-password" id="line-access-token" placeholder={lineConfigured ? t('notifications.tokenSaved') : ''} required={!lineConfigured} type="password" value={lineChannelAccessToken} onChange={(event) => setLineChannelAccessToken(event.target.value)} />
              </label>
              <div className="settings-actions">
                {lineConfigured && <button className="text-button" disabled={notificationBusy} onClick={disconnectNotifications} type="button">{t('notifications.disconnect')}</button>}
                <button className="button button-quiet" disabled={notificationBusy || !lineConfigured} onClick={sendTestNotification} type="button">{notificationBusy ? t('notifications.testing') : t('notifications.test')}</button>
                <button className="button button-primary" disabled={notificationBusy} type="submit">{notificationBusy ? t('notifications.saving') : t('notifications.save')}</button>
              </div>
            </form>
            <p className="form-message" role="status">{notificationMessage}</p>
            <div className="settings-actions">
              <button className="button button-quiet" onClick={() => setAlertsOpen(false)} type="button">{t('actions.close')}</button>
            </div>
          </section>
        </div>
      )}
    </div>
  )
}

export default App
