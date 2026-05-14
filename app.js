let allRows = [];
let filteredRows = [];
let currentPage = 1;
const rowsPerPage = 10;

let sortDirection = 1;
let brokerCharts = [];
let broker58FlowChart = null;

function fmt(n) {
  return Number(n || 0).toLocaleString("en-IN", {
    maximumFractionDigits: 2
  });
}

function value(row, keys) {
  for (const key of keys) {
    if (row[key] !== undefined && row[key] !== null) return row[key];
  }
  return "";
}

/* =========================
   FLOOR SHEET
========================= */

async function loadFloorsheet() {
  const response = await fetch("./Data/latest.json");
  const data = await response.json();

  allRows = Array.isArray(data)
    ? data
    : data.rows || data.data || data.floorsheet || [];

  filteredRows = allRows;

  document.getElementById("updated").textContent = "Floorsheet loaded";
  renderTable();
}

function renderTable() {
  const tbody = document.getElementById("floorsheet-body");
  tbody.innerHTML = "";

  const start = (currentPage - 1) * rowsPerPage;
  const end = start + rowsPerPage;

  filteredRows.slice(start, end).forEach(row => {
    const tr = document.createElement("tr");

    tr.innerHTML = `
      <td>${value(row, ["contractId"])}</td>
      <td>${value(row, ["stockSymbol"])}</td>
      <td>${value(row, ["buyerMemberId"])}</td>
      <td>${value(row, ["sellerMemberId"])}</td>
      <td>${fmt(value(row, ["contractQuantity"]))}</td>
      <td>${fmt(value(row, ["contractRate"]))}</td>
      <td>${fmt(value(row, ["contractAmount"]))}</td>
    `;

    tbody.appendChild(tr);
  });

  const totalPages = Math.max(1, Math.ceil(filteredRows.length / rowsPerPage));

  document.getElementById("summary").textContent =
    `Showing ${start + 1}-${Math.min(end, filteredRows.length)} of ${filteredRows.length} | Page ${currentPage}/${totalPages}`;
}

function sortByQuantity() {
  sortDirection *= -1;

  filteredRows.sort((a, b) => {
    return (a.contractQuantity - b.contractQuantity) * sortDirection;
  });

  currentPage = 1;
  renderTable();
}

document.getElementById("search").addEventListener("input", function () {
  const keyword = this.value.toLowerCase();

  filteredRows = allRows.filter(row =>
    JSON.stringify(row).toLowerCase().includes(keyword)
  );

  currentPage = 1;
  renderTable();
});

function nextPage() {
  currentPage++;
  renderTable();
}

function prevPage() {
  if (currentPage > 1) currentPage--;
  renderTable();
}

/* =========================
   BROKER ANALYSIS (TABLE + CHART)
========================= */

async function loadBrokerDailyTop() {
  const broker = document.getElementById("broker-input").value.trim();
  const mode = document.getElementById("broker-view-mode").value;
  const container = document.getElementById("broker-analysis");

  if (!broker) return alert("Enter broker ID");

  container.innerHTML = "";

  brokerCharts.forEach(c => c.destroy());
  brokerCharts = [];

  const res = await fetch(`./Data/analysis/broker_daily_top/${broker}.json`);
  const data = await res.json();

  data.reverse().forEach((day, i) => {
    if (mode === "table" || mode === "both") {
      renderBrokerTable(container, day);
    }

    if (mode === "chart" || mode === "both") {
      renderBrokerChart(container, day, i);
    }
  });
}

function renderBrokerTable(container, day) {
  const div = document.createElement("div");

  div.innerHTML = `
    <h4>${day.date}</h4>
    <b>Top Buy</b>
    ${makeCompanyTable(day.top_buy)}
    <b>Top Sell</b>
    ${makeCompanyTable(day.top_sell)}
  `;

  container.appendChild(div);
}









function renderBrokerChart(container, day) {
  const wrapper = document.createElement("div");

  wrapper.style.height = "350px";
  wrapper.style.display = "flex";
  wrapper.style.flexDirection = "column";
  wrapper.style.background = "white";
  wrapper.style.padding = "8px";
  wrapper.style.border = "1px solid #ddd";
  wrapper.style.borderRadius = "6px";

  const canvas = document.createElement("canvas");

  const chartContainer = document.createElement("div");
  chartContainer.style.flex = "1";
  chartContainer.style.position = "relative";

  chartContainer.appendChild(canvas);

  const buySorted = (day.top_buy || [])
    .sort((a, b) => b.amount - a.amount)
    .slice(0, 8);

  const sellSorted = (day.top_sell || [])
    .sort((a, b) => b.amount - a.amount)
    .slice(0, 8);

  const labels = [
    ...buySorted.map(x => x.stockSymbol),
    ...sellSorted.map(x => x.stockSymbol)
  ];

  const buyValues = [
    ...buySorted.map(x => x.amount),
    ...Array(sellSorted.length).fill(0)
  ];

  const sellValues = [
    ...Array(buySorted.length).fill(0),
    ...sellSorted.map(x => x.amount)
  ];

  wrapper.innerHTML = `<h4>${day.date}</h4>`;
  wrapper.appendChild(chartContainer);

  const chart = new Chart(canvas, {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          label: "Buy",
          data: buyValues,
          backgroundColor: "green",
          barThickness: 10
        },
        {
          label: "Sell",
          data: sellValues,
          backgroundColor: "red",
          barThickness: 10
        }
      ]
    },
    options: {
      indexAxis: "y",
      responsive: true,
      maintainAspectRatio: false,
      animation: false, // 🔥 KEY FIX
      plugins: {
        legend: { position: "bottom" }
      }
    }
  });

  brokerCharts.push(chart);
  container.appendChild(wrapper);
}












function makeCompanyTable(rows) {
  if (!rows || rows.length === 0) return "<p>No data</p>";

  let html = "<table><tr><th>Symbol</th><th>Qty</th><th>Amount</th></tr>";

  rows.forEach(r => {
    html += `<tr>
      <td>${r.stockSymbol}</td>
      <td>${fmt(r.quantity)}</td>
      <td>${fmt(r.amount)}</td>
    </tr>`;
  });

  html += "</table>";
  return html;
}

/* =========================
   COMPANY ANALYSIS
========================= */

async function loadCompanyPeriodTop() {
  const symbol = document.getElementById("company-input").value.trim().toUpperCase();

  if (!symbol) return alert("Enter company");

  const res = await fetch(`./Data/analysis/company_period_top/${symbol}.json`);
  const data = await res.json();

  renderBrokerRows("company-buyers-body", data.top_buyers);
  renderBrokerRows("company-sellers-body", data.top_sellers);
}

function renderBrokerRows(id, rows) {
  const tbody = document.getElementById(id);
  tbody.innerHTML = "";

  rows.forEach(r => {
    const tr = document.createElement("tr");

    tr.innerHTML = `
      <td>${r.broker}</td>
      <td>${fmt(r.trades)}</td>
      <td>${fmt(r.quantity)}</td>
      <td>${fmt(r.amount)}</td>
      <td>${fmt(r.avg_rate)}</td>
    `;

    tbody.appendChild(tr);
  });
}


async function loadBroker58CompanyFlow() {
  const symbol = document.getElementById("flow-company-input").value.trim().toUpperCase();
  const status = document.getElementById("flow-status");

  if (!symbol) {
    alert("Enter company symbol");
    return;
  }

  status.textContent = "Loading broker 58 flow...";

  try {
    const res = await fetch("./Data/analysis/broker_daily_company/58.json");

    if (!res.ok) {
      throw new Error("Could not load Data/analysis/broker_daily_company/58.json");
    }

    const allData = await res.json();

    let rows = allData
      .filter(r => String(r.symbol).toUpperCase() === symbol)
      .sort((a, b) => String(a.date).localeCompare(String(b.date)));

    if (rows.length === 0) {
      throw new Error(`No broker 58 data found for ${symbol}`);
    }

    let cumulativeQty = 0;
    let cumulativeAmount = 0;

    rows = rows.map(row => {
      const netQty = Number(row.net_quantity || 0);
      const netAmount = Number(row.net_amount || 0);

      cumulativeQty += netQty;
      cumulativeAmount += netAmount;

      let signal = "NEUTRAL";
      if (cumulativeQty > 0) signal = "ACCUMULATION";
      if (cumulativeQty < 0) signal = "DISTRIBUTION";

      return {
        ...row,
        cumulative_quantity: cumulativeQty,
        cumulative_amount: cumulativeAmount,
        signal
      };
    });

    renderBroker58FlowChart(symbol, rows);
    renderBroker58FlowTable(symbol, rows);

    status.textContent = `Loaded ${rows.length} days for Broker 58 - ${symbol}`;
  } catch (error) {
    status.textContent = error.message;
    console.error(error);
  }
}

function renderBroker58FlowChart(symbol, rows) {
  const canvas = document.getElementById("broker58-flow-chart");

  if (broker58FlowChart) {
    broker58FlowChart.destroy();
  }

  broker58FlowChart = new Chart(canvas, {
    data: {
      labels: rows.map(r => r.date),
      datasets: [
        {
          type: "bar",
          label: "Buy Qty",
          data: rows.map(r => Number(r.buy_quantity || 0)),
          backgroundColor: "rgba(0, 150, 80, 0.65)",
          yAxisID: "y"
        },
        {
          type: "bar",
          label: "Sell Qty",
          data: rows.map(r => Number(r.sell_quantity || 0)),
          backgroundColor: "rgba(220, 50, 50, 0.65)",
          yAxisID: "y"
        },
        {
          type: "line",
          label: "Cumulative Net Qty",
          data: rows.map(r => Number(r.cumulative_quantity || 0)),
          borderColor: "blue",
          backgroundColor: "blue",
          tension: 0.25,
          yAxisID: "y1"
        },
        {
          type: "line",
          label: "Avg Price",
          data: rows.map(r => Number(r.avg_price || 0)),
          borderColor: "orange",
          backgroundColor: "orange",
          borderDash: [5, 5],
          tension: 0.25,
          yAxisID: "y2"
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        mode: "index",
        intersect: false
      },
      plugins: {
        title: {
          display: true,
          text: `Broker 58 Flow + Avg Price: ${symbol}`
        },
        legend: {
          position: "bottom"
        }
      },
      scales: {
        y: {
          beginAtZero: true,
          position: "left",
          title: {
            display: true,
            text: "Daily Buy/Sell Quantity"
          }
        },
        y1: {
          position: "right",
          title: {
            display: true,
            text: "Cumulative Net Qty"
          },
          grid: {
            drawOnChartArea: false
          }
        },
        y2: {
          position: "right",
          title: {
            display: true,
            text: "Avg Price"
          },
          grid: {
            drawOnChartArea: false
          }
        }
      }
    }
  });
}

function renderBroker58FlowTable(symbol, rows) {
  document.getElementById("flow-title").textContent =
    `Broker 58 Accumulation / Distribution Table for ${symbol}`;

  const tbody = document.getElementById("broker58-flow-body");
  tbody.innerHTML = "";

  rows.forEach(row => {
    const tr = document.createElement("tr");

tr.innerHTML = `
  <td>${row.date}</td>
  <td>${fmt(row.buy_quantity)}</td>
  <td>${fmt(row.sell_quantity)}</td>
  <td>${fmt(row.net_quantity)}</td>
  <td>${fmt(row.cumulative_quantity)}</td>
  <td>${fmt(row.buy_amount)}</td>
  <td>${fmt(row.sell_amount)}</td>
  <td>${fmt(row.net_amount)}</td>
  <td>${fmt(row.buy_avg_price)}</td>
  <td>${fmt(row.sell_avg_price)}</td>
  <td>${fmt(row.avg_price)}</td>
  <td>${row.signal}</td>
`;
    tbody.appendChild(tr);
  });
}

async function loadBroker58AccumulationDashboard() {
  const days = Number(document.getElementById("accum-days").value);
  const status = document.getElementById("accum-status");

  status.textContent = "Loading accumulation dashboard...";

  try {
    const res = await fetch("./Data/analysis/broker_daily_company/58.json");

    if (!res.ok) {
      throw new Error("Could not load Broker 58 data");
    }

    const rows = await res.json();

    const dates = [...new Set(rows.map(r => r.date))]
      .sort((a, b) => String(a).localeCompare(String(b)));

    const selectedDates = dates.slice(Math.max(0, dates.length - days));
    const selectedSet = new Set(selectedDates);

    const filtered = rows.filter(r => selectedSet.has(r.date));

    const bySymbol = {};

    filtered.forEach(r => {
      const symbol = r.symbol;

      if (!bySymbol[symbol]) {
        bySymbol[symbol] = {
          symbol,
          buy_quantity: 0,
          sell_quantity: 0,
          net_quantity: 0,
          buy_amount: 0,
          sell_amount: 0,
          net_amount: 0
        };
      }

      bySymbol[symbol].buy_quantity += Number(r.buy_quantity || 0);
      bySymbol[symbol].sell_quantity += Number(r.sell_quantity || 0);
      bySymbol[symbol].net_quantity += Number(r.net_quantity || 0);

      bySymbol[symbol].buy_amount += Number(r.buy_amount || 0);
      bySymbol[symbol].sell_amount += Number(r.sell_amount || 0);
      bySymbol[symbol].net_amount += Number(r.net_amount || 0);
    });

    const summary = Object.values(bySymbol).map(r => {
      let signal = "NEUTRAL";

      if (r.net_quantity > 0) signal = "ACCUMULATION";
      if (r.net_quantity < 0) signal = "DISTRIBUTION";

      return { ...r, signal };
    });

    const accum = [...summary]
      .filter(r => r.net_quantity > 0)
      .sort((a, b) => b.net_quantity - a.net_quantity)
      .slice(0, 20);

    const dist = [...summary]
      .filter(r => r.net_quantity < 0)
      .sort((a, b) => a.net_quantity - b.net_quantity)
      .slice(0, 20);

    renderAccumulationTable("top-accum-body", accum);
    renderAccumulationTable("top-dist-body", dist);

    status.textContent =
      `Showing ${selectedDates.length} trading days: ${selectedDates[0]} to ${selectedDates[selectedDates.length - 1]}`;

  } catch (error) {
    status.textContent = error.message;
    console.error(error);
  }
}

function renderAccumulationTable(tbodyId, rows) {
  const tbody = document.getElementById(tbodyId);
  tbody.innerHTML = "";

  rows.forEach(r => {
    const tr = document.createElement("tr");

    tr.innerHTML = `
      <td>${r.symbol}</td>
      <td>${fmt(r.buy_quantity)}</td>
      <td>${fmt(r.sell_quantity)}</td>
      <td>${fmt(r.net_quantity)}</td>
      <td>${fmt(r.buy_amount)}</td>
      <td>${fmt(r.sell_amount)}</td>
      <td>${fmt(r.net_amount)}</td>
      <td>${r.signal}</td>
    `;

    tbody.appendChild(tr);
  });
}




/* ========================= */

loadFloorsheet();