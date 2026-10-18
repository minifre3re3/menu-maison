"""
Menu Maison — Backend recherche & filtres
Miroir de backend_filtre.py du projet JPO

Usage : python backend_filtre.py
        → http://127.0.0.1:5555/backend?query=chicken&type=Plat&pays=Français&page=1
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
from pathlib import Path
from dataclasses import dataclass, field

DB_PATH = Path(__file__).resolve().parent / "menu_maison.sqlite"


@dataclass
class SearchResult:
    results: list
    suggestions: dict
    total_results: int
    current_page: int
    total_pages: int


class MealSearchEngine:
    PAGE_SIZE = 20

    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path

    # ── Connexion ──────────────────────────────────────────────────────────
    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    # ── Recherche principale ───────────────────────────────────────────────
    def search(self, filters: dict, page: int = 1) -> SearchResult:
        conn = self._connect()
        try:
            base_query, params = self._build_query(filters)
            offset = (page - 1) * self.PAGE_SIZE

            paginated = f"{base_query} LIMIT ? OFFSET ?"
            rows = conn.execute(paginated, params + [self.PAGE_SIZE, offset]).fetchall()
            results = [dict(r) for r in rows]

            total = conn.execute(
                f"SELECT COUNT(*) FROM ({base_query})", params
            ).fetchone()[0]

            suggestions = self._get_suggestions(conn, filters)

            return SearchResult(
                results=results,
                suggestions=suggestions,
                total_results=total,
                current_page=page,
                total_pages=max(1, (total + self.PAGE_SIZE - 1) // self.PAGE_SIZE),
            )
        finally:
            conn.close()

    # ── Construction de la requête ─────────────────────────────────────────
    def _build_query(self, filters: dict):
        query = """
            SELECT DISTINCT
                p.id_plat,
                p.nom,
                p.description,
                p.image_url,
                p.video_url,
                tp.libelle  AS type_plat,
                po.nom      AS pays,
                po.code_iso AS pays_iso,
                c.nom       AS categorie,
                r.temps_preparation,
                r.temps_cuisson,
                r.difficulte,
                r.nb_portions,
                n.calories
            FROM PLAT p
            LEFT JOIN TYPE_PLAT    tp ON p.id_type      = tp.id_type
            LEFT JOIN PAYS_ORIGINE po ON p.id_pays      = po.id_pays
            LEFT JOIN CATEGORIE    c  ON p.id_categorie = c.id_categorie
            LEFT JOIN RECETTE      r  ON p.id_plat      = r.id_plat
            LEFT JOIN NUTRITION    n  ON p.id_plat      = n.id_plat
            WHERE 1=1
        """
        params = []

        # Recherche texte libre (nom du plat)
        if filters.get("query"):
            query += " AND p.nom LIKE ?"
            params.append(f"%{filters['query']}%")

        # Filtre type (Entrée / Plat / Dessert)
        if filters.get("type"):
            query += " AND tp.libelle = ?"
            params.append(filters["type"])

        # Filtre pays d'origine
        if filters.get("pays"):
            query += " AND po.nom LIKE ?"
            params.append(f"%{filters['pays']}%")

        # Filtre catégorie (Beef, Seafood, Dessert…)
        if filters.get("categorie"):
            query += " AND c.nom LIKE ?"
            params.append(f"%{filters['categorie']}%")

        # Filtre tag (ex: Healthy, Vegan…)
        if filters.get("tag"):
            query += """
                AND p.id_plat IN (
                    SELECT pt.id_plat FROM PLAT_TAG pt
                    JOIN TAG t ON pt.id_tag = t.id_tag
                    WHERE t.libelle LIKE ?
                )
            """
            params.append(f"%{filters['tag']}%")

        # Filtre stock uniquement (ingrédients disponibles)
        if filters.get("stock_only") == "1":
            query += """
                AND NOT EXISTS (
                    SELECT 1 FROM RECETTE_INGREDIENT ri
                    JOIN RECETTE rec ON ri.id_recette = rec.id_recette
                    WHERE rec.id_plat = p.id_plat
                      AND (
                          NOT EXISTS (
                              SELECT 1 FROM STOCK s
                              WHERE s.id_ingredient = ri.id_ingredient
                                AND s.quantite >= COALESCE(ri.quantite, 0)
                          )
                      )
                )
            """

        query += " ORDER BY p.nom"
        return query, params

    # ── Suggestions ────────────────────────────────────────────────────────
    def _get_suggestions(self, conn, filters: dict) -> dict:
        suggestions = {"plats": [], "pays": [], "categories": []}

        if filters.get("query"):
            rows = conn.execute(
                "SELECT DISTINCT nom FROM PLAT WHERE nom LIKE ? LIMIT 6",
                (f"%{filters['query']}%",)
            ).fetchall()
            suggestions["plats"] = [r[0] for r in rows]

        if filters.get("pays"):
            rows = conn.execute(
                "SELECT DISTINCT nom FROM PAYS_ORIGINE WHERE nom LIKE ? LIMIT 6",
                (f"%{filters['pays']}%",)
            ).fetchall()
            suggestions["pays"] = [r[0] for r in rows]

        return suggestions


app = Flask(__name__)
CORS(app)
engine = MealSearchEngine()


@app.route("/backend", methods=["GET"])
def backend():
    filters = {
        "query":      request.args.get("query",      "").strip(),
        "type":       request.args.get("type",        "").strip(),
        "pays":       request.args.get("pays",        "").strip(),
        "categorie":  request.args.get("categorie",   "").strip(),
        "tag":        request.args.get("tag",         "").strip(),
        "stock_only": request.args.get("stock_only",  "0").strip(),
    }
    # Nettoyer les filtres vides
    filters = {k: v for k, v in filters.items() if v}

    page = max(1, int(request.args.get("page", 1)))
    result = engine.search(filters, page)

    return jsonify({
        "data":          result.results,
        "current_page":  result.current_page,
        "total_pages":   result.total_pages,
        "total_results": result.total_results,
        "suggestions":   result.suggestions,
    })


if __name__ == "__main__":
    app.run(debug=False, host="127.0.0.1", port=5555)

