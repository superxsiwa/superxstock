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
};

async function fetchJson(url, options = {}) {
  const response = await fetch(url, { headers: { 'Content-Type': 'application/json' }, ...options });
  const json = await response.json();
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

el.tradeBtn.addEventListener('click', handleTrade);
document.querySelector('.primary-btn').addEventListener('click', refreshScan);

(async function init() {
  await refreshScan();
  await loadPortfolio();
})();
