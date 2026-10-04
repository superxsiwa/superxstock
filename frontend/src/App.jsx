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
  const stocks = useAppStore((state) => state.stocks)
  const portfolio = useAppStore((state) => state.portfolio)
  const selectedSymbol = useAppStore((state) => state.selectedSymbol)
  const authOpen = useAppStore((state) => state.authOpen)
  const error = useAppStore((state) => state.error)
  const setStocks = useAppStore((state) => state.setStocks)
  const setPortfolio = useAppStore((state) => state.setPortfolio)
  const setSelectedSymbol = useAppStore((state) => state.setSelectedSymbol)
  const setAuthOpen = useAppStore((state) => state.setAuthOpen)
  const setError = useAppStore((state) => state.setError)
  const setAccessToken = useAppStore((state) => state.setAccessToken)
  const logout = useAppStore((state) => state.logout)
  const [candles, setCandles] = useState([])
  const [authMode, setAuthMode] = useState('login')
  const [authMessage, setAuthMessage] = useState('')
  const [tradeMessage, setTradeMessage] = useState('')
  const [busy, setBusy] = useState(false)
  const [quantity, setQuantity] = useState('50')
  const [action, setAction] = useState('BUY')
  const [tradeSymbol, setTradeSymbol] = useState('AOT')

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
  }, [accessToken, selectedSymbol, setAuthOpen, setError, setPortfolio, setSelectedSymbol, setStocks])

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
          <a className="nav-item" href="#portfolio">{t('navigation.portfolio')}</a>
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
              <button className="button button-quiet" onClick={logout} type="button">{t('actions.signOut')}</button>
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
    </div>
  )
}

export default App
