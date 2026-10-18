/* ═══════════════════════════════════════════════════════════════════
   Menu Maison — plat_connector.js
   Page détail d'un plat : plat.html?id=<int>
   ═══════════════════════════════════════════════════════════════════ */

const API_DETAIL = "http://127.0.0.1:5556";

document.addEventListener("DOMContentLoaded", async () => {
  const params = new URLSearchParams(location.search);
  const id = parseInt(params.get("id"));

  if (!id) {
    document.getElementById("detailLayout").innerHTML =
      `<div class="detail-loading">❌ Paramètre 'id' manquant dans l'URL.</div>`;
    return;
  }

  try {
    const [platRes, recRes] = await Promise.all([
      fetch(`${API_DETAIL}/plat?id=${id}`),
      fetch(`${API_DETAIL}/recette?id=${id}`),
    ]);
    const plat    = platRes.ok ? await platRes.json() : null;
    const recette = recRes.ok  ? await recRes.json()  : null;

    if (!plat) {
      document.getElementById("detailLayout").innerHTML =
        `<div class="detail-loading">Plat #${id} introuvable.</div>`;
      return;
    }

    document.title = plat.nom + " – Menu Maison";
    renderDetail(plat, recette);
  } catch (err) {
    document.getElementById("detailLayout").innerHTML =
      `<div class="detail-loading" style="color:var(--accent-red)">Erreur : ${err.message}</div>`;
  }
});

function renderDetail(plat, recette) {
  const layout = document.getElementById("detailLayout");

  const tags    = (plat.tags     || []).map(t => `<span class="badge badge-tag">${esc(t)}</span>`).join("");
  const allergs = (plat.allergenes || []).map(a =>
    `<span class="badge badge-aller">⚠ ${esc(a.nom)} <small>(${esc(a.niveau_risque)})</small></span>`
  ).join("");

  const videoId = plat.video_url ? (/(?:v=|youtu\.be\/)([a-zA-Z0-9_-]{11})/.exec(plat.video_url)||[])[1] : null;

  layout.innerHTML = `
    <!-- Breadcrumb -->
    <nav style="font-size:12px;color:var(--text-muted);margin-bottom:24px">
      <a href="index.html">← Retour à l'explorateur</a>
    </nav>

    <!-- Hero -->
    <div class="detail-hero">
      <img class="detail-img"
           src="${plat.image_url || 'https://via.placeholder.com/320x240/252930/5c6070?text=🍽'}"
           alt="${esc(plat.nom)}">
      <div class="detail-info">
        <h1 class="detail-title">${esc(plat.nom)}</h1>
        <div class="detail-meta-row">
          ${plat.type_plat ? `<span class="badge badge-type">${esc(plat.type_plat)}</span>` : ""}
          ${plat.pays      ? `<span class="badge badge-pays">🌍 ${esc(plat.pays)}</span>` : ""}
          ${plat.categorie ? `<span class="badge badge-tag">${esc(plat.categorie)}</span>` : ""}
          ${tags}
        </div>
        ${allergs ? `<div class="detail-meta-row">${allergs}</div>` : ""}

        ${recette ? `
          <div style="display:flex;gap:20px;margin:14px 0;font-size:13px;color:var(--text-secondary)">
            ${recette.temps_preparation ? `<span>🔪 ${recette.temps_preparation} min prép.</span>` : ""}
            ${recette.temps_cuisson     ? `<span>🍳 ${recette.temps_cuisson} min cuisson</span>`   : ""}
            ${recette.nb_portions       ? `<span>🍽 ${recette.nb_portions} portions</span>`        : ""}
            ${recette.difficulte        ? `<span>· ${esc(recette.difficulte)}</span>`               : ""}
          </div>` : ""}

        ${videoId ? `
          <a class="detail-video-btn" href="https://youtu.be/${videoId}" target="_blank">
            ▶ Voir la vidéo YouTube
          </a>` : ""}

        ${plat.nutrition ? renderNutritionInline(plat.nutrition) : ""}
      </div>
    </div>

    <!-- Tabs -->
    <div class="modal-tabs" style="margin-bottom:0">
      <button class="tab-btn active" data-tab="ingredients">Ingrédients</button>
      <button class="tab-btn" data-tab="recette">Recette</button>
      ${videoId ? `<button class="tab-btn" data-tab="video">Vidéo</button>` : ""}
    </div>

    <div id="tab-ingredients" class="tab-content active" style="background:var(--bg-surface);border:1px solid var(--border-subtle);border-top:none;border-radius:0 0 var(--radius-lg) var(--radius-lg)">
      ${renderIngredients(recette)}
    </div>
    <div id="tab-recette" class="tab-content" style="background:var(--bg-surface);border:1px solid var(--border-subtle);border-top:none;border-radius:0 0 var(--radius-lg) var(--radius-lg)">
      <p class="instructions-text">${esc(recette?.instructions || "Recette non disponible.")}</p>
    </div>
    ${videoId ? `
    <div id="tab-video" class="tab-content" style="background:var(--bg-surface);border:1px solid var(--border-subtle);border-top:none;border-radius:0 0 var(--radius-lg) var(--radius-lg)">
      <iframe class="video-embed"
              src="https://www.youtube.com/embed/${videoId}"
              allowfullscreen></iframe>
    </div>` : ""}
  `;

  // Tabs logic
  layout.querySelectorAll(".tab-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      layout.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
      layout.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));
      btn.classList.add("active");
      layout.querySelector(`#tab-${btn.dataset.tab}`).classList.add("active");
    });
  });
}

function renderIngredients(recette) {
  if (!recette?.ingredients?.length)
    return `<p style="color:var(--text-muted);padding:20px">Aucun ingrédient disponible.</p>`;

  const rows = recette.ingredients.map(ing => {
    const cls = ing.stock_status === "ok" ? "ing-ok"
              : ing.stock_status === "insuffisant" ? "ing-warn" : "ing-absent";
    const statusTip = ing.stock_status === "ok"          ? "En stock ✓"
                    : ing.stock_status === "insuffisant"  ? "Stock insuffisant"
                    : "Non en stock";
    const qty = [ing.quantite ? +ing.quantite.toFixed(2) : "", ing.unite || ""].filter(Boolean).join(" ");
    return `
      <div class="ingredient-row" title="${statusTip}">
        <span class="ing-status ${cls}"></span>
        <span class="ing-name">${esc(ing.nom)}</span>
        <span class="ing-qty">${esc(qty)}</span>
      </div>`;
  }).join("");

  const ok      = recette.ingredients.filter(i => i.stock_status === "ok").length;
  const total   = recette.ingredients.length;
  const pct     = Math.round(ok / total * 100);
  const barCol  = pct === 100 ? "var(--accent-green)" : pct > 50 ? "var(--accent-yellow)" : "var(--accent-red)";

  return `
    <div style="padding:4px 0 12px;display:flex;align-items:center;gap:12px">
      <div style="flex:1;background:var(--bg-raised);border-radius:4px;height:6px;overflow:hidden">
        <div style="width:${pct}%;height:100%;background:${barCol};border-radius:4px;transition:width .4s"></div>
      </div>
      <span style="font-family:var(--font-mono);font-size:11px;color:var(--text-muted);white-space:nowrap">
        ${ok}/${total} disponibles
      </span>
    </div>
    <div class="ingredients-list">${rows}</div>`;
}

function renderNutritionInline(n) {
  return `
    <div class="nutrition-grid" style="margin-top:16px">
      ${[
        { val: n.calories ? Math.round(n.calories) : "–",   label:"Calories",  unit:"kcal" },
        { val: n.proteines_g ? n.proteines_g.toFixed(1):"–",label:"Protéines", unit:"g" },
        { val: n.glucides_g  ? n.glucides_g.toFixed(1) :"–",label:"Glucides",  unit:"g" },
        { val: n.lipides_g   ? n.lipides_g.toFixed(1)  :"–",label:"Lipides",   unit:"g" },
      ].map(i => `
        <div class="nutrition-item">
          <div class="nutrition-val">${i.val}<small style="font-size:11px;opacity:.5"> ${i.unit}</small></div>
          <div class="nutrition-label">${i.label}</div>
        </div>`).join("")}
    </div>`;
}

function esc(s) {
  if (!s) return "";
  return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
}
