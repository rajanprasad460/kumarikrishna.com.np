let allRows = [];
let filteredRows = [];
let currentPage = 1;
const rowsPerPage = 10;
let sortDirection = 1; // for quantity sorting



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
   FLOOR SHEET TABLE
========================= */

async function loadFloorsheet() {
  try {
    const response = await fetch("./Data/latest.json");
    const data = await response.json();

    allRows = Array.isArray(data)
      ? data
      : data.rows || data.data || data.floorsheet || [];

    filteredRows = allRows;

    document.getElementById("updated").textContent = "Floorsheet loaded";
    renderTable();
  } catch (error) {
    document.getElementById("updated").textContent = "Could not load floorsheet";
    console.error(error);
  }
}

function renderTable() {
  const tbody = document.getElementById("floorsheet-body");
  if (!tbody) return;

  tbody.innerHTML = "";

  const start = (currentPage - 1) * rowsPerPage;
  const end = start + rowsPerPage;
  const pageRows = filteredRows.slice(start, end);

  pageRows.forEach(row => {
    const tr = document.createElement("tr");

    tr.innerHTML = `
      <td>${value(row, ["contract_no", "contractNo", "contractId", "id"])}</td>
      <td>${value(row, ["symbol", "stockSymbol", "securitySymbol"])}</td>
      <td>${value(row, ["buyer", "buyerBroker", "buyerMemberId"])}</td>
      <td>${value(row, ["seller", "sellerBroker", "sellerMemberId"])}</td>
      <td>${fmt(value(row, ["quantity", "contractQuantity"]))}</td>
      <td>${fmt(value(row, ["rate", "contractRate", "price"]))}</td>
      <td>${fmt(value(row, ["amount", "contractAmount"]))}</td>
    `;

    tbody.appendChild(tr);
  });

  const totalPages = Math.max(1, Math.ceil(filteredRows.length / rowsPerPage));

  document.getElementById("summary").textContent =
    `Showing ${filteredRows.length ? start + 1 : 0}-${Math.min(end, filteredRows.length)} of ${filteredRows.length} transactions | Page ${currentPage} of ${totalPages}`;
}

function sortByQuantity() {
  sortDirection *= -1;

  const header = document.getElementById("qty-header");
  if (header) {
    header.textContent = sortDirection === 1 ? "Quantity ↑" : "Quantity ↓";
  }

  filteredRows.sort((a, b) => {
    const q1 = Number(a.contractQuantity || a.quantity || 0);
    const q2 = Number(b.contractQuantity || b.quantity || 0);

    return (q1 - q2) * sortDirection;
  });

  currentPage = 1;
  renderTable();
}


const searchBox = document.getElementById("search");

if (searchBox) {
  searchBox.addEventListener("input", function () {
    const keyword = this.value.toLowerCase();

    filteredRows = allRows.filter(row =>
      JSON.stringify(row).toLowerCase().includes(keyword)
    );

    currentPage = 1;
    renderTable();
  });
}

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

/* =========================
   BROKER DAILY TOP COMPANIES
   File:
   Data/analysis/broker_daily_top/58.json
========================= */

async function loadBrokerDailyTop() {
  const brokerInput = document.getElementById("broker-input");
  const status = document.getElementById("analysis-status");
  const title = document.getElementById("broker-title");
  const container = document.getElementById("broker-analysis");

  const broker = brokerInput.value.trim();

  if (!broker) {
    alert("Enter broker ID");
    return;
  }

  status.textContent = "Loading broker analysis...";
  title.textContent = "";
  container.innerHTML = "";

  try {
    const response = await fetch(`./Data/analysis/broker_daily_top/${broker}.json`);

    if (!response.ok) {
      throw new Error(`No broker analysis found for broker ${broker}`);
    }

    const days = await response.json();

    title.textContent = `Broker ${broker}: Daily Top 10 Buy / Sell Companies`;

    days
      .sort((a, b) => String(b.date).localeCompare(String(a.date)))
      .forEach(day => {
        const section = document.createElement("section");

        section.innerHTML = `
          <h4>${day.date}</h4>

          <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(350px,1fr));gap:16px;">
            <div>
              <h5>Top 10 Bought Companies</h5>
              ${makeCompanyTable(day.top_buy)}
            </div>

            <div>
              <h5>Top 10 Sold Companies</h5>
              ${makeCompanyTable(day.top_sell)}
            </div>
          </div>
        `;

        container.appendChild(section);
      });

    status.textContent = `Loaded ${days.length} trading days for broker ${broker}`;
  } catch (error) {
    status.textContent = error.message;
    console.error(error);
  }
}

function makeCompanyTable(rows) {
  if (!rows || rows.length === 0) {
    return "<p>No data</p>";
  }

  let html = `
    <table>
      <thead>
        <tr>
          <th>Symbol</th>
          <th>Trades</th>
          <th>Quantity</th>
          <th>Amount</th>
          <th>Avg Rate</th>
        </tr>
      </thead>
      <tbody>
  `;

  rows.forEach(row => {
    html += `
      <tr>
        <td>${row.stockSymbol || ""}</td>
        <td>${fmt(row.trades)}</td>
        <td>${fmt(row.quantity)}</td>
        <td>${fmt(row.amount)}</td>
        <td>${fmt(row.avg_rate)}</td>
      </tr>
    `;
  });

  html += `
      </tbody>
    </table>
  `;

  return html;
}

/* =========================
   COMPANY PERIOD TOP BROKERS
   File:
   Data/analysis/company_period_top/NABIL.json
========================= */

async function loadCompanyPeriodTop() {
  const companyInput = document.getElementById("company-input");
  const status = document.getElementById("analysis-status");
  const title = document.getElementById("company-title");

  const symbol = companyInput.value.trim().toUpperCase();

  if (!symbol) {
    alert("Enter company symbol");
    return;
  }

  status.textContent = "Loading company analysis...";
  title.textContent = "";

  clearTable("company-buyers-body");
  clearTable("company-sellers-body");

  try {
    const response = await fetch(`./Data/analysis/company_period_top/${symbol}.json`);

    if (!response.ok) {
      throw new Error(`No company analysis found for ${symbol}`);
    }

    const data = await response.json();

    title.textContent = `${symbol}: Top 10 Buyer / Seller Brokers for Full Available Period`;

    renderBrokerRows("company-buyers-body", data.top_buyers || []);
    renderBrokerRows("company-sellers-body", data.top_sellers || []);

    status.textContent = `Loaded company analysis for ${symbol}`;
  } catch (error) {
    status.textContent = error.message;
    console.error(error);
  }
}

function renderBrokerRows(tbodyId, rows) {
  const tbody = document.getElementById(tbodyId);
  if (!tbody) return;

  tbody.innerHTML = "";

  rows.forEach(row => {
    const tr = document.createElement("tr");

    tr.innerHTML = `
      <td>${row.broker || ""}</td>
      <td>${fmt(row.trades)}</td>
      <td>${fmt(row.quantity)}</td>
      <td>${fmt(row.amount)}</td>
      <td>${fmt(row.avg_rate)}</td>
    `;

    tbody.appendChild(tr);
  });
}

function clearTable(tbodyId) {
  const tbody = document.getElementById(tbodyId);
  if (tbody) tbody.innerHTML = "";
}

/* =========================
   INIT
========================= */

loadFloorsheet();