"""
Menu Maison — Création du schéma SQLite
Exécuter AVANT le scraper.

Usage : python create_db.py
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "menu_maison.sqlite"


SCHEMA = """
PRAGMA foreign_keys = ON;

-- ─────────────────────────────────────────────────────────────────
--  Tables de référence
-- ─────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS TYPE_PLAT (
    id_type     INTEGER PRIMARY KEY AUTOINCREMENT,
    libelle     TEXT    NOT NULL UNIQUE
                        CHECK(libelle IN ('Entrée','Plat','Dessert','Boisson','Snack'))
);

CREATE TABLE IF NOT EXISTS PAYS_ORIGINE (
    id_pays     INTEGER PRIMARY KEY AUTOINCREMENT,
    nom         TEXT    NOT NULL UNIQUE,
    code_iso    TEXT    NOT NULL DEFAULT '??'
);

CREATE TABLE IF NOT EXISTS CATEGORIE (
    id_categorie INTEGER PRIMARY KEY AUTOINCREMENT,
    nom          TEXT    NOT NULL UNIQUE,
    description  TEXT
);

CREATE TABLE IF NOT EXISTS ALLERGENE (
    id_allergene  INTEGER PRIMARY KEY AUTOINCREMENT,
    nom           TEXT    NOT NULL UNIQUE,
    code_eu       TEXT    NOT NULL DEFAULT '??',
    niveau_risque TEXT    NOT NULL DEFAULT 'Modéré'
                          CHECK(niveau_risque IN ('Faible','Modéré','Élevé','Critique')),
    description   TEXT
);

CREATE TABLE IF NOT EXISTS TAG (
    id_tag  INTEGER PRIMARY KEY AUTOINCREMENT,
    libelle TEXT    NOT NULL UNIQUE
);

-- ─────────────────────────────────────────────────────────────────
--  Ingrédients
-- ─────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS INGREDIENT (
    id_ingredient  INTEGER PRIMARY KEY AUTOINCREMENT,
    nom            TEXT    NOT NULL UNIQUE,
    unite_defaut   TEXT,               -- 'g', 'ml', 'pcs', …
    image_url      TEXT,
    calories_100g  REAL,
    proteines_100g REAL,
    glucides_100g  REAL,
    lipides_100g   REAL
);

-- ─────────────────────────────────────────────────────────────────
--  Plats
-- ─────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS PLAT (
    id_plat        INTEGER PRIMARY KEY AUTOINCREMENT,
    nom            TEXT    NOT NULL,
    description    TEXT,
    image_url      TEXT,
    video_url      TEXT,
    id_type        INTEGER REFERENCES TYPE_PLAT(id_type),
    id_pays        INTEGER REFERENCES PAYS_ORIGINE(id_pays),
    id_categorie   INTEGER REFERENCES CATEGORIE(id_categorie),
    source_externe TEXT,               -- 'themealdb', 'spoonacular', …
    id_externe     TEXT,               -- ID dans la source
    date_ajout     TEXT    DEFAULT (DATE('now'))
);

CREATE TABLE IF NOT EXISTS PLAT_TAG (
    id_plat INTEGER REFERENCES PLAT(id_plat) ON DELETE CASCADE,
    id_tag  INTEGER REFERENCES TAG(id_tag)   ON DELETE CASCADE,
    PRIMARY KEY (id_plat, id_tag)
);

CREATE TABLE IF NOT EXISTS PLAT_ALLERGENE (
    id_plat      INTEGER REFERENCES PLAT(id_plat)           ON DELETE CASCADE,
    id_allergene INTEGER REFERENCES ALLERGENE(id_allergene) ON DELETE CASCADE,
    PRIMARY KEY (id_plat, id_allergene)
);

-- ─────────────────────────────────────────────────────────────────
--  Recettes
-- ─────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS RECETTE (
    id_recette       INTEGER PRIMARY KEY AUTOINCREMENT,
    id_plat          INTEGER NOT NULL UNIQUE
                             REFERENCES PLAT(id_plat) ON DELETE CASCADE,
    instructions     TEXT,
    temps_preparation INTEGER,   -- minutes
    temps_cuisson     INTEGER,   -- minutes
    nb_portions       INTEGER    DEFAULT 4,
    difficulte        TEXT       CHECK(difficulte IN ('Facile','Moyen','Difficile'))
);

CREATE TABLE IF NOT EXISTS RECETTE_INGREDIENT (
    id_recette    INTEGER REFERENCES RECETTE(id_recette)         ON DELETE CASCADE,
    id_ingredient INTEGER REFERENCES INGREDIENT(id_ingredient)   ON DELETE CASCADE,
    quantite      REAL,
    unite         TEXT,
    PRIMARY KEY (id_recette, id_ingredient)
);

-- ─────────────────────────────────────────────────────────────────
--  Nutrition (enrichissement optionnel)
-- ─────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS NUTRITION (
    id_plat      INTEGER PRIMARY KEY REFERENCES PLAT(id_plat) ON DELETE CASCADE,
    calories     REAL,
    proteines_g  REAL,
    glucides_g   REAL,
    lipides_g    REAL,
    fibres_g     REAL
);

-- ─────────────────────────────────────────────────────────────────
--  Menus
-- ─────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS MENU (
    id_menu    INTEGER PRIMARY KEY AUTOINCREMENT,
    nom        TEXT    NOT NULL,
    date_menu  TEXT,
    notes      TEXT,
    date_crea  TEXT    DEFAULT (DATE('now'))
);

CREATE TABLE IF NOT EXISTS MENU_PLAT (
    id_menu  INTEGER REFERENCES MENU(id_menu) ON DELETE CASCADE,
    id_plat  INTEGER REFERENCES PLAT(id_plat) ON DELETE CASCADE,
    position TEXT    CHECK(position IN ('Entrée','Plat','Dessert')),
    PRIMARY KEY (id_menu, id_plat)
);

-- ─────────────────────────────────────────────────────────────────
--  Stock d'ingrédients
-- ─────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS STOCK (
    id_stock      INTEGER PRIMARY KEY AUTOINCREMENT,
    id_ingredient INTEGER NOT NULL UNIQUE
                          REFERENCES INGREDIENT(id_ingredient) ON DELETE CASCADE,
    quantite      REAL    NOT NULL DEFAULT 0,
    unite         TEXT,
    date_maj      TEXT    DEFAULT (DATETIME('now')),
    date_peremption TEXT
);
"""


def create():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()
    print(f"✅ Base de données créée : {DB_PATH}")


if __name__ == "__main__":
    create()

