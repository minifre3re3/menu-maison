#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="python3"
if [[ -x "$APP_ROOT/.venv/bin/python" ]]; then
  PYTHON="$APP_ROOT/.venv/bin/python"
fi

if ! "$PYTHON" -c 'import flask, flask_cors, requests' >/dev/null 2>&1; then
  echo "Dépendances manquantes. Active l'environnement virtuel et lance :"
  echo "python -m pip install -r requirements.txt"
  exit 1
fi

if [[ ! -f "$APP_ROOT/db/menu_maison.sqlite" ]]; then
  "$PYTHON" "$APP_ROOT/db/creation_db/create_db.py"
fi

"$PYTHON" "$APP_ROOT/db/backend_filtre.py" &
PID_FILTER=$!
"$PYTHON" "$APP_ROOT/db/backend_get_pages.py" &
PID_DETAILS=$!

cleanup() {
  kill "$PID_FILTER" "$PID_DETAILS" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "API recherche : http://127.0.0.1:5555"
echo "API menus/stock : http://127.0.0.1:5556"
echo "Ouvre frontend/index.html dans ton navigateur."
wait
