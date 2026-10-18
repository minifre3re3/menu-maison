/* ═══════════════════════════════════════════════════════════════════
   Menu Maison — menu_connector.js
   Page menu.html : liste et détail des menus sauvegardés
   ═══════════════════════════════════════════════════════════════════ */

const API = "http://127.0.0.1:5556";

document.addEventListener("DOMContentLoaded", () => {
  loadMenus();

  document.getElementById("modalClose").addEventListener("click", () => {
    document.getElementById("modalOverlay").setAttribute("hidden","");
  });
  document.getElementById("modalOverlay").addEventListener("click", e => {
    if (e.target === document.getElementById("modalOverlay"))
      document.getElementById("modalOverlay").setAttribute("hidden","");
  });
});

async function loadMenus() {
  const grid = document.getElementById("menusGrid");
  try {
    const res  = await fetch(`${API}/menu`);
    const data = await res.json();

    if (!data.length) {
      grid.innerHTML = `<p style="color:var(--text-muted)">
        Aucun menu sauvegardé. <a href="index.html">Explorer des plats →</a></p>`;
      return;
    }

    grid.innerHTML = "";
    data.forEach(m => grid.appendChild(buildMenuCard(m)));
  } catch (err) {
    grid.innerHTML = `<p style="color:var(--accent-red)">Erreur : ${err.message}</p>`;
  }
}

function buildMenuCard(menu) {
  const card = document.createElement("div");
  card.className = "menu-card";
  card.innerHTML = `
    <div class="menu-card-title">${esc(menu.nom)}</div>
    <div class="menu-card-date">${menu.date_menu || menu.date_crea || ""}</div>
    <div class="menu-plats-preview" id="preview-${menu.id_menu}">
      <span style="color:var(--text-muted);font-size:12px">Chargement…</span>
    </div>
    <div class="menu-card-actions">
      <button class="btn-primary" onclick="openMenuDetail(${menu.id_menu})">Voir</button>
      <button class="btn-danger"  onclick="deleteMenu(${menu.id_menu}, this)">Supprimer</button>
    </div>`;

  // Charger le détail en arrière-plan pour le preview
  fetch(`${API}/menu/${menu.id_menu}`)
    .then(r => r.json())
    .then(detail => {
      const prev = document.getElementById(`preview-${menu.id_menu}`);
      if (!prev) return;
      if (!detail.plats?.length) { prev.innerHTML = "<em style='color:var(--text-muted)'>Vide</em>"; return; }
      prev.innerHTML = detail.plats.map(p =>
        `<div class="menu-plat-row">
           <span class="menu-pos-label">${p.position||""}</span>
           <span>${esc(p.nom)}</span>
         </div>`
      ).join("");
    })
    .catch(() => {});

  return card;
}

window.openMenuDetail = async function(id) {
  const overlay = document.getElementById("modalOverlay");
  const body    = document.getElementById("modalBody");
  body.innerHTML = `<div class="detail-loading" style="padding:60px">Chargement…</div>`;
  overlay.removeAttribute("hidden");

  const res  = await fetch(`${API}/menu/${id}`);
  const data = await res.json();

  const platRows = (data.plats || []).map(p => `
    <a class="ingredient-row" href="plat.html?id=${p.id_plat}"
       style="text-decoration:none;display:flex;gap:10px;align-items:center;padding:10px 12px;
              background:var(--bg-raised);border-radius:var(--radius-sm);margin-bottom:6px">
      ${p.image_url ? `<img src="${p.image_url}" style="width:50px;height:38px;object-fit:cover;border-radius:4px">` : ""}
      <span style="font-size:11px;font-weight:600;text-transform:uppercase;color:var(--text-muted);width:55px;flex-shrink:0">
        ${p.position||""}
      </span>
      <span style="font-family:var(--font-display);font-size:15px">${esc(p.nom)}</span>
    </a>`).join("");

  body.innerHTML = `
    <div style="padding:24px">
      <h2 style="font-family:var(--font-display);font-size:26px;margin-bottom:4px">${esc(data.nom)}</h2>
      <p style="font-size:12px;color:var(--text-muted);margin-bottom:20px">${data.date_menu||data.date_crea||""}</p>
      ${data.notes ? `<p style="color:var(--text-secondary);margin-bottom:16px">${esc(data.notes)}</p>` : ""}
      ${platRows || "<p style='color:var(--text-muted)'>Aucun plat dans ce menu.</p>"}
    </div>`;
};

window.deleteMenu = async function(id, btn) {
  if (!confirm("Supprimer ce menu ?")) return;
  await fetch(`${API}/menu/${id}`, { method: "DELETE" });
  btn.closest(".menu-card").remove();
};

function esc(s) {
  if (!s) return "";
  return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
}
