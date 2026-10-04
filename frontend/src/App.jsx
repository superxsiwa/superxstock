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
import { useAppStore } from './store'
import './App.css'

ChartJS.register(CategoryScale, Filler, LinearScale, LineElement, PointElement, Tooltip)

const money = new Intl.NumberFormat('th-TH', {
  style: 'currency',
  currency: 'THB',
  maximumFractionDigits: 2,
})

function App() {
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
        setAuthMessage('Account created. Sign in to continue.')
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
      setTradeMessage(result.message)
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
        <a className="brand" href="#overview" aria-label="SuperX Stock overview">
          <span className="brand-mark">SX</span>
          <span><strong>SuperX</strong><small>MARKET DESK</small></span>
        </a>
        <nav className="nav-list" aria-label="Main navigation">
          <a className="nav-item active" href="#overview">Overview</a>
          <a className="nav-item" href="#opportunities">Opportunities</a>
          <a className="nav-item" href="#portfolio">Portfolio</a>
        </nav>
          <div className="sidebar-status"><span className="status-dot" /><span>Thai equities</span><strong>DAILY</strong></div>
        <div className="sidebar-bottom"><span className="eyebrow">Session</span><strong>{accessToken ? 'Authenticated' : 'Guest access'}</strong></div>
      </aside>

      <main className="main-panel" id="overview">
        <header className="topbar">
          <div><p className="eyebrow">Market overview / Thailand</p><h1>Opportunity desk</h1></div>
          <div className="topbar-actions">
            <span className="market-date">SET | END OF DAY</span>
            {accessToken ? (
              <button className="button button-quiet" onClick={logout} type="button">Sign out</button>
            ) : (
              <button className="button button-quiet" onClick={() => setAuthOpen(true)} type="button">Sign in</button>
            )}
            <button className="button button-primary" disabled={busy} onClick={refreshScan} type="button">{busy ? 'Refreshing...' : 'Refresh scan'}</button>
          </div>
        </header>

        {error && <div className="notice notice-error" role="alert">{error}</div>}

        <section className="metrics" aria-label="Market summary">
          <div className="metric"><span>BUY SETUPS</span><strong>{buyCount}</strong><small>Across tracked symbols</small></div>
          <div className="metric"><span>WATCHLIST</span><strong>{stocks.length}</strong><small>Thai equities scanned</small></div>
          <div className="metric" id="portfolio"><span>PORTFOLIO VALUE</span><strong>{portfolio ? money.format(portfolio.total_value) : '-'}</strong><small>{portfolio ? 'Account value' : 'Sign in to view'}</small></div>
          <div className="metric"><span>AVAILABLE CASH</span><strong>{portfolio ? money.format(portfolio.cash) : '-'}</strong><small>{portfolio ? 'Paper trading balance' : 'Account balance'}</small></div>
        </section>

        <section className="work-grid">
          <article className="panel chart-panel">
            <div className="panel-heading"><div><p className="eyebrow">Price history</p><h2>{selectedSymbol || 'Select a symbol'}</h2></div><span className={`signal-tag ${selectedStock?.recommendation?.toLowerCase() || 'watch'}`}>{selectedStock?.recommendation || 'WATCH'}</span></div>
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
            ) : <div className="chart-empty">Select a scanned symbol to view its price history.</div>}
            <div className="chart-footer"><span>90 trading days</span><span>{candles.length ? `Latest close ${money.format(candles.at(-1).close)}` : 'No price data'}</span></div>
          </article>

          <article className="panel trade-panel">
            <div className="panel-heading"><div><p className="eyebrow">Simulation</p><h2>Paper trade</h2></div></div>
            <form className="trade-form" onSubmit={submitTrade}>
              <label>Symbol<input maxLength="10" onChange={(event) => setTradeSymbol(event.target.value)} value={tradeSymbol} required /></label>
              <div className="form-split">
                <label>Quantity<input min="1" onChange={(event) => setQuantity(event.target.value)} type="number" value={quantity} required /></label>
                <label>Side<select onChange={(event) => setAction(event.target.value)} value={action}><option value="BUY">Buy</option><option value="SELL">Sell</option></select></label>
              </div>
              <button className="button button-primary trade-submit" disabled={!accessToken || busy} type="submit">{accessToken ? 'Submit order' : 'Sign in to trade'}</button>
              <p className="form-message" role="status">{tradeMessage}</p>
            </form>
          </article>
        </section>

        <section className="panel table-panel" id="opportunities">
          <div className="panel-heading table-heading"><div><p className="eyebrow">Daily scan</p><h2>Top opportunities</h2></div><span className="table-count">{stocks.length} SYMBOLS</span></div>
          <div className="table-scroll"><table>
            <thead><tr><th>Symbol</th><th>Price</th><th>RSI</th><th>MACD</th><th>EMA 50</th><th>EMA 90</th><th>Volume</th><th>Zone</th><th>Score</th><th>Signal</th></tr></thead>
            <tbody>{stocks.map((stock) => (
              <tr className={stock.symbol === selectedSymbol ? 'selected-row' : ''} key={stock.symbol} onClick={() => setSelectedSymbol(stock.symbol)}>
                <td><strong>{stock.symbol}</strong></td><td>{Number(stock.price).toFixed(2)}</td><td>{Number(stock.rsi).toFixed(1)}</td><td>{Number(stock.macd).toFixed(2)}</td><td>{Number(stock.ema50).toFixed(2)}</td><td>{Number(stock.ema90).toFixed(2)}</td><td>{Number(stock.volume_ratio).toFixed(2)}x</td><td>{stock.action_zone}</td><td>{stock.score}</td><td><span className={`signal-tag ${stock.recommendation.toLowerCase()}`}>{stock.recommendation}</span></td>
              </tr>
            ))}</tbody>
          </table></div>
          {!stocks.length && <p className="table-empty">No scan results are available.</p>}
        </section>
      </main>

      {authOpen && (
        <div className="dialog-backdrop" role="presentation">
          <section aria-labelledby="auth-title" aria-modal="true" className="auth-dialog" role="dialog">
            <p className="eyebrow">SuperX account</p><h2 id="auth-title">{authMode === 'login' ? 'Sign in' : 'Create account'}</h2>
            <form className="auth-form" onSubmit={submitAuth}>
              <label>Email<input autoComplete="email" name="email" required type="email" /></label>
              <label>Password<input autoComplete={authMode === 'login' ? 'current-password' : 'new-password'} minLength="8" name="password" required type="password" /></label>
              <p className="form-message" role="status">{authMessage}</p>
              <button className="button button-primary" disabled={busy} type="submit">{authMode === 'login' ? 'Sign in' : 'Register'}</button>
            </form>
            <div className="dialog-actions">
              <button className="text-button" onClick={() => { setAuthMode(authMode === 'login' ? 'register' : 'login'); setAuthMessage('') }} type="button">{authMode === 'login' ? 'Create an account' : 'Back to sign in'}</button>
              <button className="text-button" onClick={() => setAuthOpen(false)} type="button">Close</button>
            </div>
          </section>
        </div>
      )}
    </div>
  )
}

export default App
