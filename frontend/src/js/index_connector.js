/* ═══════════════════════════════════════════════════════════════════
   Menu Maison — index_connector.js
   Miroir de ecole_connector.js du projet JPO
   Gère : recherche live, filtres sidebar, pagination, modal plat,
          constructeur de menu (drawer FAB)
   ═══════════════════════════════════════════════════════════════════ */

const API_FILTER = "http://127.0.0.1:5555/backend";
const API_DETAIL = "http://127.0.0.1:5556";

// ── État global ──────────────────────────────────────────────────────
let state = {
  query:     "",
  type:      "",
  categorie: "",
  pays:      "",
  tag:       "",
  stockOnly: false,
  page:      1,
};

let debounceTimer = null;

// Menu en cours de construction
let currentMenu = { entree: null, plat: null, dessert: null };

// ── Init ─────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  loadFilters();
  fetchData();

  // Recherche
  document.getElementById("searchInput").addEventListener("input", e => {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      state.query = e.target.value.trim();
      state.page = 1;
      fetchData();
    }, 350);
  });

  // Toggle stock header
  document.getElementById("stockToggleHeader").addEventListener("click", e => {
    e.currentTarget.classList.toggle("active");
    document.getElementById("stockOnly").checked = e.currentTarget.classList.contains("active");
    state.stockOnly = document.getElementById("stockOnly").checked;
    state.page = 1;
    fetchData();
  });

  // Toggle stock toolbar
  document.getElementById("stockOnly").addEventListener("change", e => {
    state.stockOnly = e.target.checked;
    state.page = 1;
    fetchData();
  });

  // Vues
  document.getElementById("viewGrid").addEventListener("click", () => {
    document.getElementById("cardsGrid").classList.remove("list-view");
    document.getElementById("viewGrid").classList.add("active");
    document.getElementById("viewList").classList.remove("active");
  });
  document.getElementById("viewList").addEventListener("click", () => {
    document.getElementById("cardsGrid").classList.add("list-view");
    document.getElementById("viewList").classList.add("active");
    document.getElementById("viewGrid").classList.remove("active");
  });

  // Clear filtres
  document.getElementById("clearFilters").addEventListener("click", clearAllFilters);

  // Modal
  document.getElementById("modalClose").addEventListener("click", closeModal);
  document.getElementById("modalOverlay").addEventListener("click", e => {
    if (e.target === document.getElementById("modalOverlay")) closeModal();
  });

  // FAB menu drawer
  document.getElementById("fabMenu").addEventListener("click", () => {
    document.getElementById("menuDrawer").classList.toggle("open");
  });
  document.getElementById("drawerClose").addEventListener("click", () => {
    document.getElementById("menuDrawer").classList.remove("open");
  });

  // Sauvegarder menu
  document.getElementById("saveMenu").addEventListener("click", saveMenu);
});

// ── Chargement des filtres ────────────────────────────────────────────
async function loadFilters() {
  try {
    const res = await fetch(`${API_DETAIL}/filters`);
    const data = await res.json();
    buildFilterGroup("filterType",      data.types,      "type");
    buildFilterGroup("filterCategorie", data.categories, "categorie");
    buildFilterGroup("filterPays",      data.pays,       "pays");
    buildFilterGroup("filterTag",       data.tags,       "tag");
  } catch (err) {
    console.warn("Filtres non chargés (backend démarré ?)", err.message);
  }
}

function buildFilterGroup(containerId, items, filterKey) {
  const wrap = document.getElementById(containerId);
  wrap.innerHTML = "";
  (items || []).forEach(item => {
    const btn = document.createElement("button");
    btn.className = "filter-chip";
    btn.textContent = item;
    btn.dataset.value = item;
    btn.dataset.key = filterKey;
    btn.addEventListener("click", () => toggleFilter(btn, filterKey, item));
    wrap.appendChild(btn);
  });
}

function toggleFilter(btn, key, value) {
  if (state[key] === value) {
    state[key] = "";
    btn.classList.remove("selected");
  } else {
    // Désélectionner l'ancien
    document.querySelectorAll(`.filter-chip[data-key="${key}"]`)
      .forEach(b => b.classList.remove("selected"));
    state[key] = value;
    btn.classList.add("selected");
  }
  state.page = 1;
  updateActiveChips();
  fetchData();
}

function clearAllFilters() {
  state.type = ""; state.categorie = ""; state.pays = ""; state.tag = "";
  document.querySelectorAll(".filter-chip").forEach(b => b.classList.remove("selected"));
  updateActiveChips();
  state.page = 1;
  fetchData();
}

function updateActiveChips() {
  const wrap = document.getElementById("activeFilters");
  wrap.innerHTML = "";
  const keys = ["type", "categorie", "pays", "tag"];
  const labels = { type:"Type", categorie:"Catégorie", pays:"Pays", tag:"Tag" };
  keys.forEach(k => {
    if (!state[k]) return;
    const chip = document.createElement("span");
    chip.className = "active-chip";
    chip.innerHTML = `<strong>${labels[k]}:</strong> ${state[k]}
      <button onclick="removeFilter('${k}')">✕</button>`;
    wrap.appendChild(chip);
  });
}

window.removeFilter = function(key) {
  state[key] = "";
  document.querySelectorAll(`.filter-chip[data-key="${key}"]`)
    .forEach(b => b.classList.remove("selected"));
  updateActiveChips();
  state.page = 1;
  fetchData();
};

// ── Fetch principal ───────────────────────────────────────────────────
async function fetchData() {
  const grid = document.getElementById("cardsGrid");
  grid.innerHTML = `<div class="state-loading">Chargement des plats…</div>`;

  const params = new URLSearchParams({ page: state.page });
  if (state.query)     params.set("query",     state.query);
  if (state.type)      params.set("type",      state.type);
  if (state.categorie) params.set("categorie", state.categorie);
  if (state.pays)      params.set("pays",      state.pays);
  if (state.tag)       params.set("tag",       state.tag);
  if (state.stockOnly) params.set("stock_only","1");

  try {
    const res = await fetch(`${API_FILTER}/backend?${params}`);
    if (!res.ok) throw new Error("HTTP " + res.status);
    const data = await res.json();

    document.getElementById("resultCount").textContent =
      `${data.total_results} résultat${data.total_results !== 1 ? "s" : ""}`;

    renderCards(data.data);
    renderPagination(data.current_page, data.total_pages);
  } catch (err) {
    grid.innerHTML = `<div class="state-empty">
      ⚠️ Impossible de joindre le backend.<br>
      <small>Démarrez <code>python backend_filtre.py</code> (port 5555).</small>
    </div>`;
    document.getElementById("resultCount").textContent = "—";
  }
}

// ── Rendu des cartes ──────────────────────────────────────────────────
function renderCards(items) {
  const grid = document.getElementById("cardsGrid");
  grid.innerHTML = "";

  if (!items || items.length === 0) {
    grid.innerHTML = `<div class="state-empty">Aucun résultat pour cette recherche.</div>`;
    return;
  }

  items.forEach(item => {
    const card = document.createElement("div");
    card.className = "meal-card";

    const typeBadgeClass = badgeClass(item.type_plat);
    const imgSrc = item.image_url || "https://via.placeholder.com/300x225/252930/5c6070?text=🍽";

    card.innerHTML = `
      <div class="card-img-wrap">
        <img class="card-img" src="${imgSrc}" alt="${escHtml(item.nom)}" loading="lazy">
        <span class="card-type-badge ${typeBadgeClass}">${item.type_plat || "Plat"}</span>
      </div>
      <div class="card-body">
        <div class="card-title">${escHtml(item.nom)}</div>
        <div class="card-meta">
          <span class="card-pays">${item.pays || ""}</span>
          ${item.categorie ? `<span class="dot">·</span><span>${escHtml(item.categorie)}</span>` : ""}
        </div>
      </div>
      <div class="card-actions">
        <button class="btn-add-menu" data-id="${item.id_plat}"
                data-nom="${escAttr(item.nom)}" data-type="${escAttr(item.type_plat || "Plat")}">
          + Menu
        </button>
      </div>`;

    // Clic sur la carte → modal
    card.addEventListener("click", e => {
      if (e.target.closest(".btn-add-menu")) return;
      openModal(item.id_plat);
    });

    // Bouton "Ajouter au menu"
    card.querySelector(".btn-add-menu").addEventListener("click", () => {
      addToMenu(item.id_plat, item.nom, item.type_plat || "Plat");
    });

    grid.appendChild(card);
  });
}

function badgeClass(type) {
  if (!type) return "badge-plat";
  if (type === "Entrée") return "badge-entree";
  if (type === "Dessert") return "badge-dessert";
  return "badge-plat";
}

// ── Pagination ────────────────────────────────────────────────────────
function renderPagination(current, total) {
  const wrap = document.getElementById("pagination");
  wrap.innerHTML = "";

  if (total <= 1) return;

  const prev = document.createElement("button");
  prev.className = "page-btn";
  prev.textContent = "‹ Précédent";
  prev.disabled = current <= 1;
  prev.onclick = () => { state.page = current - 1; fetchData(); window.scrollTo(0,0); };
  wrap.appendChild(prev);

  const start = Math.max(1, current - 2);
  const end   = Math.min(total, current + 2);
  for (let i = start; i <= end; i++) {
    const btn = document.createElement("button");
    btn.className = "page-btn" + (i === current ? " active" : "");
    btn.textContent = i;
    btn.onclick = () => { state.page = i; fetchData(); window.scrollTo(0,0); };
    wrap.appendChild(btn);
  }

  const next = document.createElement("button");
  next.className = "page-btn";
  next.textContent = "Suivant ›";
  next.disabled = current >= total;
  next.onclick = () => { state.page = current + 1; fetchData(); window.scrollTo(0,0); };
  wrap.appendChild(next);
}

// ── Modal ─────────────────────────────────────────────────────────────
async function openModal(id_plat) {
  const overlay = document.getElementById("modalOverlay");
  const body    = document.getElementById("modalBody");

  body.innerHTML = `<div class="detail-loading" style="padding:60px">Chargement…</div>`;
  overlay.removeAttribute("hidden");
  document.body.style.overflow = "hidden";

  try {
    const [platRes, recRes] = await Promise.all([
      fetch(`${API_DETAIL}/plat?id=${id_plat}`),
      fetch(`${API_DETAIL}/recette?id=${id_plat}`),
    ]);
    const plat    = platRes.ok    ? await platRes.json()    : null;
    const recette = recRes.ok     ? await recRes.json()     : null;

    if (!plat) { body.innerHTML = "<p style='padding:40px;color:var(--text-muted)'>Plat introuvable.</p>"; return; }

    renderModal(plat, recette);
  } catch (err) {
    body.innerHTML = `<p style='padding:40px;color:var(--accent-red)'>Erreur : ${err.message}</p>`;
  }
}

function renderModal(plat, recette) {
  const body = document.getElementById("modalBody");

  const tags = (plat.tags || []).map(t => `<span class="badge badge-tag">${escHtml(t)}</span>`).join("");
  const allergs = (plat.allergenes || []).map(a =>
    `<span class="badge badge-aller">⚠ ${escHtml(a.nom)}</span>`).join("");

  const videoId = plat.video_url ? youtubeId(plat.video_url) : null;

  body.innerHTML = `
    <div class="modal-plat-header">
      <img class="modal-plat-img"
           src="${plat.image_url || 'https://via.placeholder.com/200x150/252930/5c6070?text=🍽'}"
           alt="${escHtml(plat.nom)}">
      <div class="modal-plat-info">
        <div class="modal-plat-title">${escHtml(plat.nom)}</div>
        <div class="modal-badges">
          ${plat.type_plat  ? `<span class="badge badge-type">${escHtml(plat.type_plat)}</span>` : ""}
          ${plat.pays       ? `<span class="badge badge-pays">🌍 ${escHtml(plat.pays)}</span>` : ""}
          ${plat.categorie  ? `<span class="badge badge-tag">${escHtml(plat.categorie)}</span>` : ""}
          ${tags}
          ${allergs}
        </div>
        ${recette ? `
          <div style="font-size:12px;color:var(--text-muted);display:flex;gap:14px">
            ${recette.temps_preparation ? `🔪 ${recette.temps_preparation} min prép.` : ""}
            ${recette.temps_cuisson ? `🍳 ${recette.temps_cuisson} min cuisson` : ""}
            ${recette.nb_portions ? `🍽 ${recette.nb_portions} portions` : ""}
            ${recette.difficulte ? `· ${recette.difficulte}` : ""}
          </div>` : ""}
        ${videoId ? `<a class="detail-video-btn" href="https://youtu.be/${videoId}" target="_blank"
                       style="margin-top:10px;display:inline-flex">▶ Voir la vidéo</a>` : ""}
      </div>
    </div>

    <div class="modal-tabs">
      <button class="tab-btn active" data-tab="ingredients">Ingrédients</button>
      <button class="tab-btn" data-tab="recette">Recette</button>
      ${plat.nutrition ? `<button class="tab-btn" data-tab="nutrition">Nutrition</button>` : ""}
    </div>

    <div id="tab-ingredients" class="tab-content active">
      ${renderIngredients(recette)}
    </div>
    <div id="tab-recette" class="tab-content">
      <p class="instructions-text">${escHtml(recette?.instructions || "Recette non disponible.")}</p>
    </div>
    ${plat.nutrition ? `
    <div id="tab-nutrition" class="tab-content">
      ${renderNutrition(plat.nutrition)}
    </div>` : ""}
  `;

  // Tabs
  body.querySelectorAll(".tab-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      body.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
      body.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));
      btn.classList.add("active");
      body.querySelector(`#tab-${btn.dataset.tab}`).classList.add("active");
    });
  });
}

function renderIngredients(recette) {
  if (!recette || !recette.ingredients || recette.ingredients.length === 0)
    return `<p style="color:var(--text-muted)">Aucun ingrédient disponible.</p>`;

  const rows = recette.ingredients.map(ing => {
    const statusClass = ing.stock_status === "ok" ? "ing-ok"
                      : ing.stock_status === "insuffisant" ? "ing-warn" : "ing-absent";
    const qty = [ing.quantite ? +ing.quantite.toFixed(2) : "", ing.unite || ""].filter(Boolean).join(" ");
    return `
      <div class="ingredient-row">
        <span class="ing-status ${statusClass}"></span>
        <span class="ing-name">${escHtml(ing.nom)}</span>
        <span class="ing-qty">${escHtml(qty)}</span>
      </div>`;
  }).join("");

  return `<div class="ingredients-list">${rows}</div>`;
}

function renderNutrition(n) {
  const items = [
    { val: n.calories     ? Math.round(n.calories)    : "–", label: "Calories",  unit: "kcal" },
    { val: n.proteines_g  ? n.proteines_g.toFixed(1)  : "–", label: "Protéines", unit: "g" },
    { val: n.glucides_g   ? n.glucides_g.toFixed(1)   : "–", label: "Glucides",  unit: "g" },
    { val: n.lipides_g    ? n.lipides_g.toFixed(1)    : "–", label: "Lipides",   unit: "g" },
  ];
  return `<div class="nutrition-grid">
    ${items.map(i => `
      <div class="nutrition-item">
        <div class="nutrition-val">${i.val}<small style="font-size:11px;opacity:.5"> ${i.unit}</small></div>
        <div class="nutrition-label">${i.label}</div>
      </div>`).join("")}
  </div>`;
}

function closeModal() {
  document.getElementById("modalOverlay").setAttribute("hidden", "");
  document.body.style.overflow = "";
}

// ── Constructeur de menu ──────────────────────────────────────────────
function addToMenu(id, nom, type) {
  const pos = type === "Entrée" ? "entree" : type === "Dessert" ? "dessert" : "plat";
  currentMenu[pos] = { id_plat: id, nom, position: type };
  document.getElementById("slot" + pos.charAt(0).toUpperCase() + pos.slice(1)).textContent = nom;
  document.getElementById("menuDrawer").classList.add("open");
}

async function saveMenu() {
  const nom = document.getElementById("menuNom").value.trim() || "Menu du jour";
  const plats = Object.values(currentMenu).filter(Boolean);
  if (plats.length === 0) { alert("Ajoutez au moins un plat."); return; }

  try {
    const res = await fetch(`${API_DETAIL}/menu`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nom, plats }),
    });
    if (res.ok) {
      document.getElementById("menuDrawer").classList.remove("open");
      document.getElementById("menuNom").value = "";
      currentMenu = { entree: null, plat: null, dessert: null };
      ["Entree","Plat","Dessert"].forEach(p =>
        document.getElementById("slot"+p).innerHTML = "<em>Aucun</em>"
      );
      alert("✅ Menu sauvegardé !");
    }
  } catch (err) {
    alert("Erreur de sauvegarde : " + err.message);
  }
}

// ── Utilitaires ───────────────────────────────────────────────────────
function escHtml(s) {
  if (!s) return "";
  return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
}
function escAttr(s) { return escHtml(s); }

function youtubeId(url) {
  const m = url.match(/(?:v=|youtu\.be\/)([a-zA-Z0-9_-]{11})/);
  return m ? m[1] : null;
}
