# Menu Maison

Application web de gestion de menus et de stock alimentaire. Le projet permet de rechercher des recettes, de composer des menus et de suivre les ingrédients disponibles.

> Projet académique réalisé en équipe en 2026.

## Fonctionnalités

- Recherche de recettes avec filtres et pagination
- Consultation des recettes et de leurs ingrédients
- Création et gestion de menus
- Suivi du stock d’ingrédients
- API REST développées avec Flask et stockage SQLite
- Interface web en HTML, CSS et JavaScript

## Technologies

Python · Flask · SQLite · HTML · CSS · JavaScript

## Structure

```text
frontend/                 Pages et interface web
  src/css/                Styles
  src/js/                 Appels aux API

db/
  backend_filtre.py        API de recherche et de filtres
  backend_get_pages.py    API des plats, menus et stocks
  creation_db/
    create_db.py           Création du schéma SQLite
    scraper.py             Import de recettes depuis TheMealDB
```

La base `db/menu_maison.sqlite` est créée localement et n’est pas versionnée.

## Démarrage

Python 3.10 ou supérieur est recommandé.

```bash
python -m venv .venv
```

Active l’environnement virtuel, puis installe les dépendances :

```bash
# Windows PowerShell
.\.venv\Scripts\Activate.ps1

# Linux / macOS
source .venv/bin/activate
```

```bash
python -m pip install -r requirements.txt
python db/creation_db/create_db.py
python db/creation_db/scraper.py --max 5
```

L’import récupère des recettes depuis TheMealDB et nécessite une connexion Internet. Pour remplir davantage la base, relance le scraper sans `--max 5`.

Dans deux terminaux ouverts à la racine du projet, démarre les API :

```bash
python db/backend_filtre.py
python db/backend_get_pages.py
```

Les serveurs sont disponibles sur `http://127.0.0.1:5555` et `http://127.0.0.1:5556`. Ouvre ensuite `frontend/index.html` dans un navigateur.

Les scripts `start_backend.bat` (Windows) et `start_backend.sh` (Linux/macOS) démarrent les deux API après la création de la base.

## Enrichissement facultatif

Les données de TheMealDB sont suffisantes pour découvrir l’application. L’enrichissement nutritionnel et les informations d’allergènes utilisent Spoonacular et Edamam, qui demandent des identifiants API.

Copie `.env.example` vers `.env`, puis renseigne les clés fournies par ces services. Le fichier `.env` est ignoré par Git. Lance ensuite :

```bash
python db/creation_db/scraper.py --enrich
```

## API

| Service | Méthode et route | Rôle |
| --- | --- | --- |
| Recherche | `GET /backend` | Recherche paginée et filtres |
| Détail | `GET /plat?id=<id>` | Informations d’un plat |
| Recette | `GET /recette?id=<id>` | Instructions, ingrédients et stock |
| Menus | `GET/POST /menu` | Lister ou créer un menu |
| Menus | `GET/DELETE /menu/<id>` | Consulter ou supprimer un menu |
| Stock | `GET /stock` | Lister les ingrédients et quantités |
| Stock | `PUT /stock/<id>` | Modifier une quantité |
| Filtres | `GET /filters` | Valeurs disponibles pour les filtres |

## Limites

Les API Flask sont configurées pour un usage local de démonstration. Elles ne fournissent pas d’authentification et ne doivent pas être exposées directement sur Internet.
