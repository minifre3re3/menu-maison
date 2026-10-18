/* ═══════════════════════════════════════════════════════════════════
   Menu Maison — stock_connector.js
   Page stock.html : gestion du stock d'ingrédients
   ═══════════════════════════════════════════════════════════════════ */

const API = "http://127.0.0.1:5556";

let allIngredients = [];

document.addEventListener("DOMContentLoaded", () => {
  loadStock();

  document.getElementById("stockSearch").addEventListener("input", filterStock);
  document.getElementById("showOnlyAvailable").addEventListener("change", filterStock);
});

async function loadStock() {
  const grid = document.getElementById("stockGrid");
  try {
    const res  = await fetch(`${API}/stock`);
    allIngredients = await res.json();
    renderStock(allIngredients);
  } catch (err) {
    grid.innerHTML = `<p style="color:var(--accent-red)">Erreur : ${err.message}</p>`;
  }
}

function filterStock() {
  const q    = document.getElementById("stockSearch").value.toLowerCase();
  const only = document.getElementById("showOnlyAvailable").checked;
  const filtered = allIngredients.filter(i => {
    if (q && !i.nom.toLowerCase().includes(q)) return false;
    if (only && i.quantite <= 0) return false;
    return true;
  });
  renderStock(filtered);
}

function renderStock(items) {
  const grid = document.getElementById("stockGrid");
  grid.innerHTML = "";

  if (!items.length) {
    grid.innerHTML = `<p style="color:var(--text-muted)">Aucun ingrédient trouvé.</p>`;
    return;
  }

  items.forEach(ing => grid.appendChild(buildStockItem(ing)));
}

function buildStockItem(ing) {
  const inStock = ing.quantite > 0;
  const div = document.createElement("div");
  div.className = "stock-item" + (inStock ? " in-stock" : "");
  div.innerHTML = `
    <div style="display:flex;align-items:center;gap:8px">
      <span class="stock-status-dot"></span>
      <span class="stock-item-name">${esc(ing.nom)}</span>
    </div>
    <div class="stock-item-controls">
      <input class="stock-qty-input" type="number" min="0" step="0.1"
             value="${ing.quantite || 0}" id="qty-${ing.id_ingredient}">
      <input class="stock-unit-input" type="text" placeholder="unité"
             value="${esc(ing.unite || ing.unite_defaut || "")}" id="unit-${ing.id_ingredient}">
      <button class="stock-save-btn" onclick="saveStock(${ing.id_ingredient})">✓</button>
    </div>
    ${ing.date_peremption
      ? `<div style="font-size:10px;color:var(--text-muted)">⏱ Péremption : ${ing.date_peremption}</div>`
      : ""}`;
  return div;
}

window.saveStock = async function(id) {
  const qte   = parseFloat(document.getElementById(`qty-${id}`).value)  || 0;
  const unite = document.getElementById(`unit-${id}`).value.trim() || null;

  try {
    const res = await fetch(`${API}/stock/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ quantite: qte, unite }),
    });
    if (res.ok) {
      // Mettre à jour l'état local
      const ing = allIngredients.find(i => i.id_ingredient === id);
      if (ing) { ing.quantite = qte; ing.unite = unite; }

      // Rafraîchir la carte visuellement
      filterStock();
      showToast(`✓ ${unite || ""} mis à jour`);
    }
  } catch (err) {
    showToast("Erreur : " + err.message, true);
  }
};

function showToast(msg, isError = false) {
  const t = document.getElementById("toast");
  t.textContent = msg;
  t.style.borderColor = isError ? "var(--accent-red)" : "var(--accent-green)";
  t.style.color       = isError ? "var(--accent-red)" : "var(--text-primary)";
  t.classList.add("show");
  setTimeout(() => t.classList.remove("show"), 2200);
}

function esc(s) {
  if (!s) return "";
  return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
}
