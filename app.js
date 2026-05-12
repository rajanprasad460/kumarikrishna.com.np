let allRows = [];
let filteredRows = [];
let currentPage = 1;
const rowsPerPage = 10;

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

function value(row, keys) {
  for (const key of keys) {
    if (row[key] !== undefined && row[key] !== null) return row[key];
  }
  return "";
}

function renderTable() {
  const tbody = document.getElementById("floorsheet-body");
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
      <td>${value(row, ["quantity", "contractQuantity"])}</td>
      <td>${value(row, ["rate", "contractRate", "price"])}</td>
      <td>${value(row, ["amount", "contractAmount"])}</td>
    `;
    tbody.appendChild(tr);
  });

  const totalPages = Math.ceil(filteredRows.length / rowsPerPage);

  document.getElementById("summary").textContent =
    `Showing ${start + 1}-${Math.min(end, filteredRows.length)} of ${filteredRows.length} transactions | Page ${currentPage} of ${totalPages}`;
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