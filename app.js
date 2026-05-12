let allRows = [];
let filteredRows = [];
let currentPage = 1;
let rowsPerPage = 10;

let charts = {};

async function loadFloorsheet() {
  const response = await fetch("./Data/latest.json");
  const data = await response.json();

  allRows = Array.isArray(data)
    ? data
    : data.rows || data.data || data.floorsheet || [];

  filteredRows = allRows;

  document.getElementById("updated").textContent =
    `Loaded ${allRows.length} floorsheet records`;

  renderDashboard();
  renderTable();
  renderTopTrades();
  renderSymbolSummary();
}

function value(row, keys) {
  for (const key of keys) {
    if (row[key] !== undefined && row[key] !== null) return row[key];
  }
  return "";
}

function num(v) {
  return Number(String(v || 0).replaceAll(",", "")) || 0;
}

function fmt(n) {
  return Number(n || 0).toLocaleString("en-IN", {
    maximumFractionDigits: 2
  });
}

function getSymbol(row) {
  return value(row, ["symbol", "stockSymbol", "securitySymbol"]);
}

function getBuyer(row) {
  return value(row, ["buyer", "buyerBroker", "buyerMemberId"]);
}

function getSeller(row) {
  return value(row, ["seller", "sellerBroker", "sellerMemberId"]);
}

function getQuantity(row) {
  return num(value(row, ["quantity", "contractQuantity"]));
}

function getRate(row) {
  return num(value(row, ["rate", "contractRate", "price"]));
}

function getAmount(row) {
  const amount = num(value(row, ["amount", "contractAmount"]));
  if (amount) return amount;
  return getQuantity(row) * getRate(row);
}

function renderDashboard() {
  const totalTrades = allRows.length;
  const totalQuantity = allRows.reduce((sum, r) => sum + getQuantity(r), 0);
  const totalTurnover = allRows.reduce((sum, r) => sum + getAmount(r), 0);
  const uniqueStocks = new Set(allRows.map(getSymbol).filter(Boolean)).size;
  const avgTrade = totalTrades ? totalTurnover / totalTrades : 0;

  document.getElementById("total-trades").textContent = fmt(totalTrades);
  document.getElementById("total-turnover").textContent = fmt(totalTurnover);
  document.getElementById("total-quantity").textContent = fmt(totalQuantity);
  document.getElementById("unique-stocks").textContent = fmt(uniqueStocks);
  document.getElementById("avg-trade").textContent = fmt(avgTrade);

  const symbolSummary = buildSymbolSummary();
  const buyerSummary = buildBrokerSummary("buyer");
  const sellerSummary = buildBrokerSummary("seller");

  drawBarChart(
    "turnoverChart",
    "Turnover",
    symbolSummary.slice(0, 10).map(x => x.symbol),
    symbolSummary.slice(0, 10).map(x => x.turnover)
  );

  drawBarChart(
    "volumeChart",
    "Volume",
    [...symbolSummary].sort((a, b) => b.quantity - a.quantity).slice(0, 10).map(x => x.symbol),
    [...symbolSummary].sort((a, b) => b.quantity - a.quantity).slice(0, 10).map(x => x.quantity)
  );

  drawBarChart(
    "buyerChart",
    "Buyer Turnover",
    buyerSummary.slice(0, 10).map(x => x.broker),
    buyerSummary.slice(0, 10).map(x => x.turnover)
  );

  drawBarChart(
    "sellerChart",
    "Seller Turnover",
    sellerSummary.slice(0, 10).map(x => x.broker),
    sellerSummary.slice(0, 10).map(x => x.turnover)
  );
}

function buildSymbolSummary() {
  const map = {};

  allRows.forEach(row => {
    const symbol = getSymbol(row);
    if (!symbol) return;

    const quantity = getQuantity(row);
    const rate = getRate(row);
    const amount = getAmount(row);

    if (!map[symbol]) {
      map[symbol] = {
        symbol,
        trades: 0,
        quantity: 0,
        turnover: 0,
        high: rate,
        low: rate
      };
    }

    map[symbol].trades += 1;
    map[symbol].quantity += quantity;
    map[symbol].turnover += amount;
    map[symbol].high = Math.max(map[symbol].high, rate);
    map[symbol].low = Math.min(map[symbol].low, rate);
  });

  return Object.values(map)
    .map(x => ({
      ...x,
      vwap: x.quantity ? x.turnover / x.quantity : 0
    }))
    .sort((a, b) => b.turnover - a.turnover);
}

function buildBrokerSummary(type) {
  const map = {};

  allRows.forEach(row => {
    const broker = type === "buyer" ? getBuyer(row) : getSeller(row);
    if (!broker) return;

    const amount = getAmount(row);

    if (!map[broker]) {
      map[broker] = {
        broker,
        trades: 0,
        turnover: 0
      };
    }

    map[broker].trades += 1;
    map[broker].turnover += amount;
  });

  return Object.values(map).sort((a, b) => b.turnover - a.turnover);
}

function drawBarChart(canvasId, label, labels, data) {
  if (charts[canvasId]) {
    charts[canvasId].destroy();
  }

  charts[canvasId] = new Chart(document.getElementById(canvasId), {
    type: "bar",
    data: {
      labels,
      datasets: [{
        label,
        data
      }]
    },
    options: {
      responsive: true,
      plugins: {
        legend: {
          display: false
        }
      }
    }
  });
}

function renderTable() {
  const tbody = document.getElementById("floorsheet-body");
  tbody.innerHTML = "";

  const start = (currentPage - 1) * rowsPerPage;
  const end = start + rowsPerPage;
  const pageRows = filteredRows.slice(start, end);

  pageRows.forEach(row => {
    tbody.appendChild(makeTradeRow(row));
  });

  const totalPages = Math.max(1, Math.ceil(filteredRows.length / rowsPerPage));

  document.getElementById("summary").textContent =
    `Showing ${filteredRows.length ? start + 1 : 0}-${Math.min(end, filteredRows.length)} of ${filteredRows.length} transactions | Page ${currentPage} of ${totalPages}`;
}

function makeTradeRow(row) {
  const tr = document.createElement("tr");

  tr.innerHTML = `
    <td>${value(row, ["contract_no", "contractNo", "contractId", "id"])}</td>
    <td>${getSymbol(row)}</td>
    <td>${getBuyer(row)}</td>
    <td>${getSeller(row)}</td>
    <td>${fmt(getQuantity(row))}</td>
    <td>${fmt(getRate(row))}</td>
    <td>${fmt(getAmount(row))}</td>
  `;

  return tr;
}

function renderTopTrades() {
  const tbody = document.getElementById("top-trades-body");
  tbody.innerHTML = "";

  const topTrades = [...allRows]
    .sort((a, b) => getAmount(b) - getAmount(a))
    .slice(0, 10);

  topTrades.forEach(row => {
    tbody.appendChild(makeTradeRow(row));
  });
}

function renderSymbolSummary() {
  const tbody = document.getElementById("symbol-summary-body");
  tbody.innerHTML = "";

  const summary = buildSymbolSummary().slice(0, 25);

  summary.forEach(item => {
    const tr = document.createElement("tr");

    tr.innerHTML = `
      <td>${item.symbol}</td>
      <td>${fmt(item.trades)}</td>
      <td>${fmt(item.quantity)}</td>
      <td>${fmt(item.turnover)}</td>
      <td>${fmt(item.vwap)}</td>
      <td>${fmt(item.high)}</td>
      <td>${fmt(item.low)}</td>
    `;

    tbody.appendChild(tr);
  });
}

document.getElementById("search").addEventListener("input", function () {
  const keyword = this.value.toLowerCase();

  filteredRows = allRows.filter(row =>
    JSON.stringify(row).toLowerCase().includes(keyword)
  );

  currentPage = 1;
  renderTable();
});

document.getElementById("rows-per-page").addEventListener("change", function () {
  rowsPerPage = Number(this.value);
  currentPage = 1;
  renderTable();
});

function nextPage() {
  const totalPages = Math.ceil(filteredRows.length / rowsPerPage);

  if (currentPage < totalPages) {
    currentPage++;
    renderTable();
  }
}

function prevPage() {
  if (currentPage > 1) {
    currentPage--;
    renderTable();
  }
}

loadFloorsheet();