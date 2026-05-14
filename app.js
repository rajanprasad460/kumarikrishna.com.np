let allRows = [];
let filteredRows = [];
let currentPage = 1;
const rowsPerPage = 10;

let sortDirection = 1;
let brokerCharts = [];

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

/* ========================= */

loadFloorsheet();