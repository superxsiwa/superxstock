const state = {
  stocks: [],
  selectedSymbol: 'AOT',
  portfolio: { cash: 0, total_value: 0, positions: [] },
};

const el = {
  scanTableBody: document.getElementById('scanTableBody'),
  buyCount: document.getElementById('buyCount'),
  watchCount: document.getElementById('watchCount'),
  portfolioValue: document.getElementById('portfolioValue'),
  portfolioCash: document.getElementById('portfolioCash'),
  chartTitle: document.getElementById('chartTitle'),
  chartSignal: document.getElementById('chartSignal'),
  marketMood: document.getElementById('marketMood'),
  marketTrend: document.getElementById('marketTrend'),
  tradeBtn: document.getElementById('tradeBtn'),
  tradeMessage: document.getElementById('tradeMessage'),
  tradeSymbol: document.getElementById('tradeSymbol'),
  tradeAction: document.getElementById('tradeAction'),
  tradeQty: document.getElementById('tradeQty'),
  chartSvg: document.getElementById('chartSvg'),
  authButton: document.getElementById('authButton'),
  logoutButton: document.getElementById('logoutButton'),
  authDialog: document.getElementById('authDialog'),
  authForm: document.getElementById('authForm'),
  authEmail: document.getElementById('authEmail'),
  authPassword: document.getElementById('authPassword'),
  authTitle: document.getElementById('authTitle'),
  authMessage: document.getElementById('authMessage'),
  authSubmit: document.getElementById('authSubmit'),
  authModeButton: document.getElementById('authModeButton'),
  authCancelButton: document.getElementById('authCancelButton'),
};

let isRegisterMode = false;

function getAccessToken() {
  return sessionStorage.getItem('access_token');
}

function openAuthDialog(message = '') {
  el.authMessage.textContent = message;
  if (!el.authDialog.open) el.authDialog.showModal();
}

function updateAuthUI() {
  const isSignedIn = Boolean(getAccessToken());
  el.authButton.hidden = isSignedIn;
  el.logoutButton.hidden = !isSignedIn;
}

function logout(message = '') {
  sessionStorage.removeItem('access_token');
  updateAuthUI();
  openAuthDialog(message);
}

async function fetchJson(url, options = {}) {
  const headers = new Headers(options.headers || {});
  const token = getAccessToken();
  if (options.body instanceof URLSearchParams) {
    headers.set('Content-Type', 'application/x-www-form-urlencoded');
  } else if (options.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }
  if (token && !url.startsWith('/api/auth/')) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  const response = await fetch(url, { ...options, headers });
  const json = await response.json().catch(() => ({}));
  if (response.status === 401 && !url.startsWith('/api/auth/')) {
    logout('Your session expired. Please sign in again.');
  }
  if (!response.ok) {
    throw new Error(json.detail || 'Request failed');
  }
  return json;
}

function formatMoney(value) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 2 }).format(value);
}

function renderSignalClass(signal) {
  const normalized = String(signal).toUpperCase();
  if (normalized === 'BUY') return 'signal-buy';
  if (normalized === 'SELL') return 'signal-sell';
  return 'signal-watch';
}

function renderTable(rows) {
  el.scanTableBody.innerHTML = rows.map((stock) => `
    <tr data-symbol="${stock.symbol}">
      <td><strong>${stock.symbol}</strong></td>
      <td>${stock.price.toFixed(2)}</td>
      <td>${stock.rsi.toFixed(1)}</td>
      <td>${stock.macd.toFixed(2)}</td>
      <td>${stock.ema50.toFixed(2)}</td>
      <td>${stock.ema90.toFixed(2)}</td>
      <td>${stock.volume_ratio.toFixed(2)}x</td>
      <td>${stock.action_zone}</td>
      <td>${stock.score}</td>
      <td class="${renderSignalClass(stock.recommendation)}">${stock.recommendation}</td>
    </tr>
  `).join('');

  document.querySelectorAll('#scanTableBody tr').forEach((row) => {
    row.addEventListener('click', () => {
      const symbol = row.dataset.symbol;
      state.selectedSymbol = symbol;
      updateChart(symbol);
    });
  });
}

function renderChart(candles, symbol) {
  const width = 760;
  const height = 290;
  const padding = 28;
  const values = candles.map((c) => c.close);
  const min = Math.min(...values) * 0.98;
  const max = Math.max(...values) * 1.02;

  const points = candles.map((candle, index) => {
    const x = padding + (index / (candles.length - 1)) * (width - padding * 2);
    const y = height - padding - ((candle.close - min) / (max - min || 1)) * (height - padding * 2);
    return { x, y, candle };
  });

  const linePath = points.map((point, idx) => `${idx === 0 ? 'M' : 'L'} ${point.x} ${point.y}`).join(' ');

  const svg = `
    <defs>
      <linearGradient id="lineGradient" x1="0" x2="1">
        <stop offset="0%" stop-color="#62d0ff" />
        <stop offset="100%" stop-color="#2ecf9f" />
      </linearGradient>
    </defs>
    <path d="${linePath}" fill="none" stroke="url(#lineGradient)" stroke-width="2.5" stroke-linecap="round" />
    ${points.map((point) => `<circle cx="${point.x}" cy="${point.y}" r="1.6" fill="#62d0ff" />`).join('')}
  `;

  el.chartSvg.innerHTML = svg;
  el.chartTitle.textContent = `${symbol}`;
  const signal = state.stocks.find((s) => s.symbol === symbol);
  el.chartSignal.textContent = signal ? signal.recommendation : 'WATCH';
  el.chartSignal.className = `chip ${renderSignalClass(signal ? signal.recommendation : 'WATCH')}`;
}

async function updateChart(symbol) {
  const chartData = await fetchJson(`/api/charts/${symbol}`);
  renderChart(chartData.candles, symbol);
}

async function refreshScan() {
  const scan = await fetchJson('/api/scan');
  const stocks = scan.stocks;
  state.stocks = stocks;
  renderTable(stocks);

  const buySetups = stocks.filter((stock) => stock.recommendation === 'BUY').length;
  const watchSetups = stocks.filter((stock) => stock.recommendation === 'WATCH').length;
  el.buyCount.textContent = String(buySetups);
  el.watchCount.textContent = String(watchSetups);

  if (stocks.length > 0) {
    const top = stocks[0];
    el.marketMood.textContent = top.recommendation === 'BUY' ? 'Bullish' : top.recommendation === 'SELL' ? 'Cautious' : 'Balanced';
    el.marketTrend.textContent = top.action_zone;
  }

  if (state.selectedSymbol && !stocks.find((s) => s.symbol === state.selectedSymbol)) {
    state.selectedSymbol = stocks[0].symbol;
  }

  updateChart(state.selectedSymbol);
}

async function loadPortfolio() {
  const portfolio = await fetchJson('/api/portfolio');
  state.portfolio = portfolio;
  el.portfolioValue.textContent = formatMoney(portfolio.total_value);
  el.portfolioCash.textContent = formatMoney(portfolio.cash);
}

async function handleTrade() {
  const symbol = el.tradeSymbol.value.trim().toUpperCase();
  const action = el.tradeAction.value;
  const quantity = Number(el.tradeQty.value);

  try {
    const result = await fetchJson('/api/paper-trade', {
      method: 'POST',
      body: JSON.stringify({ symbol, action, quantity }),
    });

    el.tradeMessage.textContent = `✅ ${action} ${quantity} ${symbol} successful.`;
    el.tradeMessage.style.color = '#2ecf9f';
    await loadPortfolio();
    await refreshScan();
    el.tradeSymbol.value = symbol;
  } catch (err) {
    el.tradeMessage.textContent = `❌ ${err.message}`;
    el.tradeMessage.style.color = '#ff5d7a';
  }
}

async function handleAuthSubmit(event) {
  event.preventDefault();
  el.authMessage.textContent = '';
  el.authSubmit.disabled = true;

  const email = el.authEmail.value.trim();
  const password = el.authPassword.value;
  try {
    if (isRegisterMode) {
      await fetchJson('/api/auth/register', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      });
      isRegisterMode = false;
      el.authTitle.textContent = 'Sign in';
      el.authSubmit.textContent = 'Sign in';
      el.authModeButton.textContent = 'Create account';
      el.authPassword.autocomplete = 'current-password';
      el.authMessage.textContent = 'Account created. Sign in to continue.';
      el.authPassword.value = '';
      return;
    }

    const result = await fetchJson('/api/auth/token', {
      method: 'POST',
      body: new URLSearchParams({ username: email, password }),
    });
    sessionStorage.setItem('access_token', result.access_token);
    updateAuthUI();
    el.authDialog.close();
    await loadPortfolio();
  } catch (error) {
    el.authMessage.textContent = error.message;
  } finally {
    el.authSubmit.disabled = false;
  }
}

el.tradeBtn.addEventListener('click', handleTrade);
document.querySelector('.primary-btn').addEventListener('click', refreshScan);
el.authButton.addEventListener('click', () => {
  isRegisterMode = false;
  el.authTitle.textContent = 'Sign in';
  el.authSubmit.textContent = 'Sign in';
  el.authModeButton.textContent = 'Create account';
  el.authPassword.autocomplete = 'current-password';
  openAuthDialog();
});
el.logoutButton.addEventListener('click', () => logout('You have signed out.'));
el.authModeButton.addEventListener('click', () => {
  isRegisterMode = !isRegisterMode;
  el.authTitle.textContent = isRegisterMode ? 'Create account' : 'Sign in';
  el.authSubmit.textContent = isRegisterMode ? 'Register' : 'Sign in';
  el.authModeButton.textContent = isRegisterMode ? 'Back to sign in' : 'Create account';
  el.authPassword.autocomplete = isRegisterMode ? 'new-password' : 'current-password';
  el.authMessage.textContent = '';
});
el.authCancelButton.addEventListener('click', () => el.authDialog.close());
el.authForm.addEventListener('submit', handleAuthSubmit);

(async function init() {
  updateAuthUI();
  await refreshScan();
  if (getAccessToken()) {
    await loadPortfolio();
  } else {
    openAuthDialog('Sign in to view your portfolio and paper trade.');
  }
})();
