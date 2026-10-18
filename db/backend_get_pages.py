"""
Menu Maison — Backend détail plat, menu & stock
Miroir de backend_get_pages.py du projet JPO

Routes :
  GET  /plat?id=<int>                  → détail complet d'un plat
  GET  /recette?id=<int>               → recette + ingrédients
  GET  /menu                           → liste des menus sauvegardés
  POST /menu                           → créer un nouveau menu  { nom, date_menu, notes, plats: [{id, position}] }
  GET  /menu/<id>                      → détail d'un menu avec ses plats
  DELETE /menu/<id>                    → supprimer un menu
  GET  /stock                          → liste du stock
  PUT  /stock/<id_ingredient>          → mettre à jour le stock  { quantite, unite }
  GET  /filters                        → liste pays, types, catégories disponibles
"""

from flask import Flask, request, jsonify, abort
from flask_cors import CORS
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "menu_maison.sqlite"

app = Flask(__name__)
CORS(app)


# ─── Helpers ──────────────────────────────────────────────────────────────────
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ─── Plat : détail ────────────────────────────────────────────────────────────
@app.route("/plat")
def plat_detail():
    id_plat = request.args.get("id", type=int)
    if not id_plat:
        abort(400, "Paramètre 'id' manquant")

    with get_conn() as conn:
        plat = conn.execute("""
            SELECT p.*, tp.libelle AS type_plat, po.nom AS pays, po.code_iso,
                   c.nom AS categorie
            FROM PLAT p
            LEFT JOIN TYPE_PLAT    tp ON p.id_type      = tp.id_type
            LEFT JOIN PAYS_ORIGINE po ON p.id_pays      = po.id_pays
            LEFT JOIN CATEGORIE    c  ON p.id_categorie = c.id_categorie
            WHERE p.id_plat = ?
        """, (id_plat,)).fetchone()

        if not plat:
            abort(404, "Plat introuvable")

        plat = dict(plat)

        # Tags
        tags = conn.execute("""
            SELECT t.libelle FROM TAG t
            JOIN PLAT_TAG pt ON t.id_tag = pt.id_tag
            WHERE pt.id_plat = ?
        """, (id_plat,)).fetchall()
        plat["tags"] = [r["libelle"] for r in tags]

        # Allergènes
        allergs = conn.execute("""
            SELECT a.nom, a.niveau_risque FROM ALLERGENE a
            JOIN PLAT_ALLERGENE pa ON a.id_allergene = pa.id_allergene
            WHERE pa.id_plat = ?
        """, (id_plat,)).fetchall()
        plat["allergenes"] = [dict(r) for r in allergs]

        # Nutrition
        nutr = conn.execute("SELECT * FROM NUTRITION WHERE id_plat = ?",
                            (id_plat,)).fetchone()
        plat["nutrition"] = dict(nutr) if nutr else None

        return jsonify(plat)


# ─── Recette ──────────────────────────────────────────────────────────────────
@app.route("/recette")
def recette_detail():
    id_plat = request.args.get("id", type=int)
    if not id_plat:
        abort(400, "Paramètre 'id' manquant")

    with get_conn() as conn:
        recette = conn.execute(
            "SELECT * FROM RECETTE WHERE id_plat = ?", (id_plat,)
        ).fetchone()

        if not recette:
            abort(404, "Recette introuvable")

        recette = dict(recette)
        id_recette = recette["id_recette"]

        # Ingrédients + stock
        ingredients = conn.execute("""
            SELECT
                i.id_ingredient,
                i.nom,
                i.image_url,
                ri.quantite,
                ri.unite,
                COALESCE(s.quantite, 0) AS stock_qte,
                CASE
                    WHEN s.quantite IS NULL THEN 'absent'
                    WHEN s.quantite >= COALESCE(ri.quantite, 0) THEN 'ok'
                    ELSE 'insuffisant'
                END AS stock_status
            FROM RECETTE_INGREDIENT ri
            JOIN INGREDIENT i ON ri.id_ingredient = i.id_ingredient
            LEFT JOIN STOCK s ON s.id_ingredient = i.id_ingredient
            WHERE ri.id_recette = ?
            ORDER BY i.nom
        """, (id_recette,)).fetchall()

        recette["ingredients"] = [dict(r) for r in ingredients]
        return jsonify(recette)


# ─── Menus ────────────────────────────────────────────────────────────────────
@app.route("/menu", methods=["GET"])
def list_menus():
    with get_conn() as conn:
        menus = conn.execute(
            "SELECT * FROM MENU ORDER BY date_crea DESC"
        ).fetchall()
        return jsonify([dict(m) for m in menus])


@app.route("/menu", methods=["POST"])
def create_menu():
    body = request.get_json(force=True)
    nom       = body.get("nom", "Sans nom")
    date_menu = body.get("date_menu")
    notes     = body.get("notes")
    plats     = body.get("plats", [])   # [{ id_plat, position }]

    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO MENU (nom, date_menu, notes) VALUES (?,?,?)",
            (nom, date_menu, notes)
        )
        id_menu = cur.lastrowid

        for p in plats:
            cur.execute(
                "INSERT OR IGNORE INTO MENU_PLAT (id_menu, id_plat, position) VALUES (?,?,?)",
                (id_menu, p["id_plat"], p.get("position"))
            )
        conn.commit()

    return jsonify({"id_menu": id_menu, "message": "Menu créé"}), 201


@app.route("/menu/<int:id_menu>", methods=["GET"])
def get_menu(id_menu):
    with get_conn() as conn:
        menu = conn.execute(
            "SELECT * FROM MENU WHERE id_menu = ?", (id_menu,)
        ).fetchone()
        if not menu:
            abort(404)

        plats = conn.execute("""
            SELECT p.id_plat, p.nom, p.image_url, tp.libelle AS type_plat, mp.position
            FROM MENU_PLAT mp
            JOIN PLAT p ON mp.id_plat = p.id_plat
            LEFT JOIN TYPE_PLAT tp ON p.id_type = tp.id_type
            WHERE mp.id_menu = ?
            ORDER BY mp.position
        """, (id_menu,)).fetchall()

        result = dict(menu)
        result["plats"] = [dict(p) for p in plats]
        return jsonify(result)


@app.route("/menu/<int:id_menu>", methods=["DELETE"])
def delete_menu(id_menu):
    with get_conn() as conn:
        conn.execute("DELETE FROM MENU WHERE id_menu = ?", (id_menu,))
        conn.commit()
    return jsonify({"message": "Supprimé"}), 200


# ─── Stock ────────────────────────────────────────────────────────────────────
@app.route("/stock", methods=["GET"])
def list_stock():
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT i.id_ingredient, i.nom, i.image_url, i.unite_defaut,
                   COALESCE(s.quantite, 0) AS quantite,
                   s.unite, s.date_maj, s.date_peremption
            FROM INGREDIENT i
            LEFT JOIN STOCK s ON i.id_ingredient = s.id_ingredient
            ORDER BY i.nom
        """).fetchall()
        return jsonify([dict(r) for r in rows])


@app.route("/stock/<int:id_ingredient>", methods=["PUT"])
def update_stock(id_ingredient):
    body = request.get_json(force=True)
    quantite = body.get("quantite", 0)
    unite    = body.get("unite")
    date_per = body.get("date_peremption")

    with get_conn() as conn:
        existing = conn.execute(
            "SELECT 1 FROM STOCK WHERE id_ingredient = ?", (id_ingredient,)
        ).fetchone()

        if existing:
            conn.execute("""
                UPDATE STOCK
                SET quantite = ?, unite = ?, date_peremption = ?,
                    date_maj = DATETIME('now')
                WHERE id_ingredient = ?
            """, (quantite, unite, date_per, id_ingredient))
        else:
            conn.execute("""
                INSERT INTO STOCK (id_ingredient, quantite, unite, date_peremption)
                VALUES (?,?,?,?)
            """, (id_ingredient, quantite, unite, date_per))
        conn.commit()

    return jsonify({"message": "Stock mis à jour"})


# ─── Filtres disponibles ──────────────────────────────────────────────────────
@app.route("/filters", methods=["GET"])
def get_filters():
    with get_conn() as conn:
        types      = [r[0] for r in conn.execute("SELECT libelle FROM TYPE_PLAT ORDER BY libelle")]
        pays       = [r[0] for r in conn.execute("SELECT nom FROM PAYS_ORIGINE ORDER BY nom")]
        categories = [r[0] for r in conn.execute("SELECT nom FROM CATEGORIE ORDER BY nom")]
        tags       = [r[0] for r in conn.execute("SELECT libelle FROM TAG ORDER BY libelle")]

    return jsonify({
        "types":      types,
        "pays":       pays,
        "categories": categories,
        "tags":       tags,
    })


if __name__ == "__main__":
    app.run(debug=False, host="127.0.0.1", port=5556)

