"""
Menu Maison — Script de scraping / population de la base de données
Sources :
  - TheMealDB  : https://www.themealdb.com/api.php  (gratuit, clé = 1)
  - Spoonacular: https://spoonacular.com/food-api   (clé API requise)
  - Edamam     : https://developer.edamam.com/      (clé API + app_id requis)

Usage :
  python scraper.py                    → scrape tout (TheMealDB en priorité)
  python scraper.py --source themealdb → TheMealDB seulement
  python scraper.py --enrich           → enrichit avec Spoonacular + Edamam
"""

import sqlite3
import requests
import json
import os
import time
import argparse
import re
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ─── Configuration ────────────────────────────────────────────────────────────
DB_PATH = Path(__file__).resolve().parent.parent / "menu_maison.sqlite"

SPOONACULAR_API_KEY = os.getenv("SPOONACULAR_API_KEY")
EDAMAM_APP_ID = os.getenv("EDAMAM_APP_ID")
EDAMAM_APP_KEY = os.getenv("EDAMAM_APP_KEY")

THEMEALDB_BASE = "https://www.themealdb.com/api/json/v1/1"

# ─── Connexion DB ─────────────────────────────────────────────────────────────
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ─── Helpers ──────────────────────────────────────────────────────────────────
def safe_get(url, params=None, retries=3, delay=1.0):
    for attempt in range(retries):
        try:
            r = requests.get(url, params=params, timeout=10)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            print(f"  [WARN] Tentative {attempt+1}/{retries} échouée : {e}")
            time.sleep(delay)
    return None


def upsert_pays(conn, nom, iso2=None):
    cur = conn.cursor()
    cur.execute("SELECT id_pays FROM PAYS_ORIGINE WHERE nom = ?", (nom,))
    row = cur.fetchone()
    if row:
        return row[0]
    cur.execute(
        "INSERT INTO PAYS_ORIGINE (nom, code_iso) VALUES (?, ?)",
        (nom, iso2 or "??")
    )
    conn.commit()
    return cur.lastrowid


def upsert_type_plat(conn, libelle):
    cur = conn.cursor()
    cur.execute("SELECT id_type FROM TYPE_PLAT WHERE libelle = ?", (libelle,))
    row = cur.fetchone()
    if row:
        return row[0]
    cur.execute("INSERT INTO TYPE_PLAT (libelle) VALUES (?)", (libelle,))
    conn.commit()
    return cur.lastrowid


def upsert_categorie(conn, nom):
    cur = conn.cursor()
    cur.execute("SELECT id_categorie FROM CATEGORIE WHERE nom = ?", (nom,))
    row = cur.fetchone()
    if row:
        return row[0]
    cur.execute("INSERT INTO CATEGORIE (nom) VALUES (?)", (nom,))
    conn.commit()
    return cur.lastrowid


def upsert_ingredient(conn, nom, unite=None):
    cur = conn.cursor()
    cur.execute("SELECT id_ingredient FROM INGREDIENT WHERE nom = ?", (nom,))
    row = cur.fetchone()
    if row:
        return row[0]
    cur.execute(
        "INSERT INTO INGREDIENT (nom, unite_defaut) VALUES (?, ?)",
        (nom, unite)
    )
    conn.commit()
    return cur.lastrowid


def upsert_tag(conn, libelle):
    cur = conn.cursor()
    cur.execute("SELECT id_tag FROM TAG WHERE libelle = ?", (libelle,))
    row = cur.fetchone()
    if row:
        return row[0]
    cur.execute("INSERT INTO TAG (libelle) VALUES (?)", (libelle,))
    conn.commit()
    return cur.lastrowid


# ─── TheMealDB ────────────────────────────────────────────────────────────────
def fetch_all_categories_mealdb():
    data = safe_get(f"{THEMEALDB_BASE}/categories.php")
    if not data:
        return []
    return data.get("categories", [])


def fetch_meals_by_category(category_name):
    data = safe_get(f"{THEMEALDB_BASE}/filter.php", {"c": category_name})
    if not data:
        return []
    return data.get("meals", []) or []


def fetch_meal_detail(meal_id):
    data = safe_get(f"{THEMEALDB_BASE}/lookup.php", {"i": meal_id})
    if not data:
        return None
    meals = data.get("meals")
    return meals[0] if meals else None


# Mapping catégories MealDB → type plat (approximation)
CATEGORY_TO_TYPE = {
    "Starter":   "Entrée",
    "Side":      "Entrée",
    "Breakfast": "Entrée",
    "Soup":      "Entrée",
    "Beef":      "Plat",
    "Chicken":   "Plat",
    "Lamb":      "Plat",
    "Pork":      "Plat",
    "Seafood":   "Plat",
    "Pasta":     "Plat",
    "Vegetarian":"Plat",
    "Vegan":     "Plat",
    "Miscellaneous": "Plat",
    "Dessert":   "Dessert",
    "Cake":      "Dessert",
    "Goat":      "Plat",
}

# Mapping areas MealDB → pays ISO2 (partiel)
AREA_TO_ISO = {
    "American": ("Américain", "US"),
    "British":  ("Britannique", "GB"),
    "Canadian": ("Canadien", "CA"),
    "Chinese":  ("Chinois", "CN"),
    "Croatian": ("Croate", "HR"),
    "Dutch":    ("Néerlandais", "NL"),
    "Egyptian": ("Égyptien", "EG"),
    "Filipino": ("Philippin", "PH"),
    "French":   ("Français", "FR"),
    "Greek":    ("Grec", "GR"),
    "Indian":   ("Indien", "IN"),
    "Irish":    ("Irlandais", "IE"),
    "Italian":  ("Italien", "IT"),
    "Jamaican": ("Jamaïcain", "JM"),
    "Japanese": ("Japonais", "JP"),
    "Kenyan":   ("Kenyan", "KE"),
    "Malaysian":("Malaisien", "MY"),
    "Mexican":  ("Mexicain", "MX"),
    "Moroccan": ("Marocain", "MA"),
    "Polish":   ("Polonais", "PL"),
    "Portuguese":("Portugais","PT"),
    "Russian":  ("Russe",    "RU"),
    "Spanish":  ("Espagnol", "ES"),
    "Thai":     ("Thaïlandais","TH"),
    "Tunisian": ("Tunisien", "TN"),
    "Turkish":  ("Turc",     "TR"),
    "Ukrainian":("Ukrainien","UA"),
    "Vietnamese":("Vietnamien","VN"),
    "Unknown":  ("Inconnu",  "??"),
}


def insert_meal_from_mealdb(conn, meal_raw, category_name):
    cur = conn.cursor()

    # ── Éviter les doublons ──────────────────────────────────────────────────
    cur.execute("SELECT id_plat FROM PLAT WHERE nom = ?", (meal_raw["strMeal"],))
    if cur.fetchone():
        return  # déjà en base

    # ── Pays ────────────────────────────────────────────────────────────────
    area = meal_raw.get("strArea", "Unknown")
    pays_nom, pays_iso = AREA_TO_ISO.get(area, (area, "??"))
    id_pays = upsert_pays(conn, pays_nom, pays_iso)

    # ── Type plat ───────────────────────────────────────────────────────────
    type_libelle = CATEGORY_TO_TYPE.get(category_name, "Plat")
    id_type = upsert_type_plat(conn, type_libelle)

    # ── Catégorie ────────────────────────────────────────────────────────────
    id_categorie = upsert_categorie(conn, category_name)

    # ── Plat ─────────────────────────────────────────────────────────────────
    cur.execute("""
        INSERT INTO PLAT
            (nom, description, image_url, video_url,
             id_type, id_pays, id_categorie,
             source_externe, id_externe)
        VALUES (?,?,?,?,?,?,?,?,?)
    """, (
        meal_raw["strMeal"],
        meal_raw.get("strInstructions", "")[:2000],
        meal_raw.get("strMealThumb"),
        meal_raw.get("strYoutube"),
        id_type,
        id_pays,
        id_categorie,
        "themealdb",
        meal_raw.get("idMeal"),
    ))
    id_plat = cur.lastrowid

    # ── Recette ──────────────────────────────────────────────────────────────
    cur.execute("""
        INSERT INTO RECETTE (id_plat, instructions, temps_preparation, temps_cuisson, nb_portions)
        VALUES (?, ?, ?, ?, ?)
    """, (id_plat, meal_raw.get("strInstructions", ""), None, None, 4))
    id_recette = cur.lastrowid

    # ── Ingrédients ──────────────────────────────────────────────────────────
    for i in range(1, 21):
        ing_name = meal_raw.get(f"strIngredient{i}", "")
        measure   = meal_raw.get(f"strMeasure{i}", "")
        if not ing_name or not ing_name.strip():
            break
        ing_name = ing_name.strip()
        measure  = measure.strip() if measure else None
        id_ing   = upsert_ingredient(conn, ing_name)

        # Parser la quantité et l'unité depuis la mesure libre
        qte, unite = parse_measure(measure)

        cur.execute("""
            INSERT INTO RECETTE_INGREDIENT (id_recette, id_ingredient, quantite, unite)
            VALUES (?, ?, ?, ?)
        """, (id_recette, id_ing, qte, unite))

    # ── Tags ─────────────────────────────────────────────────────────────────
    tags_raw = meal_raw.get("strTags") or ""
    for tag in tags_raw.split(","):
        tag = tag.strip()
        if tag:
            id_tag = upsert_tag(conn, tag)
            cur.execute(
                "INSERT OR IGNORE INTO PLAT_TAG (id_plat, id_tag) VALUES (?, ?)",
                (id_plat, id_tag)
            )

    conn.commit()
    print(f"  ✓ {meal_raw['strMeal']} ({category_name})")


def parse_measure(measure_str):
    """Tente d'extraire une quantité numérique et une unité d'une chaîne libre."""
    if not measure_str:
        return (None, None)
    m = re.match(r"^([\d./]+)\s*(.*)", measure_str.strip())
    if m:
        try:
            raw = m.group(1)
            if "/" in raw:
                parts = raw.split("/")
                qte = round(int(parts[0]) / int(parts[1]), 3)
            else:
                qte = float(raw)
        except Exception:
            qte = None
        unite = m.group(2).strip() or None
        return (qte, unite)
    return (None, measure_str[:50] if measure_str else None)


# ─── Scraping principal ───────────────────────────────────────────────────────
def scrape_themealdb(conn, max_per_category=None):
    print("\n── TheMealDB ──────────────────────────────────────────────────────")
    categories = fetch_all_categories_mealdb()
    print(f"  {len(categories)} catégories trouvées")

    for cat in categories:
        cat_name = cat["strCategory"]
        print(f"\n  Catégorie : {cat_name}")
        meals = fetch_meals_by_category(cat_name)
        if max_per_category:
            meals = meals[:max_per_category]

        for meal_summary in meals:
            meal_id = meal_summary["idMeal"]
            detail  = fetch_meal_detail(meal_id)
            if detail:
                insert_meal_from_mealdb(conn, detail, cat_name)
            time.sleep(0.3)  # respecter le rate-limit gratuit


def enrich_with_spoonacular(conn):
    """Enrichit les plats existants avec les données nutritionnelles Spoonacular."""
    print("\n── Spoonacular (enrichissement nutritionnel) ──────────────────────")
    if not SPOONACULAR_API_KEY:
        print("  [SKIP] Clé Spoonacular non configurée.")
        return

    cur = conn.cursor()
    cur.execute("SELECT id_plat, nom FROM PLAT WHERE source_externe = 'themealdb' LIMIT 50")
    plats = cur.fetchall()

    for plat in plats:
        data = safe_get(
            "https://api.spoonacular.com/recipes/complexSearch",
            {"query": plat["nom"], "number": 1, "apiKey": SPOONACULAR_API_KEY}
        )
        if not data or not data.get("results"):
            continue
        spoon_id = data["results"][0]["id"]

        # Infos nutritionnelles
        info = safe_get(
            f"https://api.spoonacular.com/recipes/{spoon_id}/nutritionWidget.json",
            {"apiKey": SPOONACULAR_API_KEY}
        )
        if not info:
            continue

        cur.execute("""
            INSERT OR REPLACE INTO NUTRITION
                (id_plat, calories, proteines_g, glucides_g, lipides_g, fibres_g)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            plat["id_plat"],
            _num(info.get("calories")),
            _num(info.get("protein")),
            _num(info.get("carbs")),
            _num(info.get("fat")),
            None,
        ))
        conn.commit()
        print(f"  ✓ Nutrition : {plat['nom']}")
        time.sleep(0.5)


def enrich_with_edamam(conn):
    """Enrichit avec les allergènes et labels nutritionnels Edamam."""
    print("\n── Edamam (allergènes / labels) ───────────────────────────────────")
    if not EDAMAM_APP_ID or not EDAMAM_APP_KEY:
        print("  [SKIP] Clés Edamam non configurées.")
        return

    cur = conn.cursor()
    cur.execute("SELECT id_plat, nom FROM PLAT LIMIT 30")
    plats = cur.fetchall()

    for plat in plats:
        data = safe_get(
            "https://api.edamam.com/search",
            {
                "q":      plat["nom"],
                "app_id": EDAMAM_APP_ID,
                "app_key":EDAMAM_APP_KEY,
                "to":     1,
            }
        )
        if not data or not data.get("hits"):
            continue

        recipe = data["hits"][0].get("recipe", {})
        # Allergènes
        for label in recipe.get("cautions", []):
            cur.execute("SELECT id_allergene FROM ALLERGENE WHERE nom = ?", (label,))
            row = cur.fetchone()
            if not row:
                cur.execute(
                    "INSERT INTO ALLERGENE (nom, code_eu, niveau_risque) VALUES (?,?,?)",
                    (label, "??", "Modéré")
                )
                conn.commit()
                all_id = cur.lastrowid
            else:
                all_id = row[0]
            cur.execute(
                "INSERT OR IGNORE INTO PLAT_ALLERGENE (id_plat, id_allergene) VALUES (?,?)",
                (plat["id_plat"], all_id)
            )
        conn.commit()
        print(f"  ✓ Edamam : {plat['nom']}")
        time.sleep(1.0)


def _num(val):
    if val is None:
        return None
    try:
        return float(str(val).replace("g", "").replace("kcal", "").strip())
    except Exception:
        return None


# ─── Entrypoint ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scraper Menu Maison")
    parser.add_argument("--source",  default="themealdb",
                        choices=["themealdb", "all"])
    parser.add_argument("--enrich",  action="store_true",
                        help="Enrich with Spoonacular + Edamam")
    parser.add_argument("--max",     type=int, default=None,
                        help="Max plats par catégorie (test)")
    args = parser.parse_args()

    conn = get_conn()

    if args.source in ("themealdb", "all"):
        scrape_themealdb(conn, max_per_category=args.max)

    if args.enrich:
        enrich_with_spoonacular(conn)
        enrich_with_edamam(conn)

    conn.close()
    print("\n✅ Scraping terminé.")

