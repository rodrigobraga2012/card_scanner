"""
Pokémon Card Scanner - Backend (Flask)

- Identificação da carta por foto: Claude (visão) + catálogo TCGdex
- Preço em R$: preços de mercado da TCGdex (Cardmarket/TCGplayer) + cotação do dia
- Coleção local em SQLite

Execução:
    pip install -r requirements.txt
    python main.py

Para abrir a câmera no celular é preciso HTTPS. Veja o README.md na raiz.
"""

import os

from dotenv import load_dotenv

# Carrega o .env ANTES de importar as rotas (elas leem variáveis na importação)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

from flask import Flask, jsonify, send_from_directory  # noqa: E402

from routes.cards import cards_bp  # noqa: E402
from routes.collection import collection_bp  # noqa: E402
from routes.prices import prices_bp  # noqa: E402
from services import identify  # noqa: E402

app = Flask(__name__, static_folder=None)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # uploads de até 10 MB

app.register_blueprint(cards_bp, url_prefix="/api")
app.register_blueprint(prices_bp, url_prefix="/api")
app.register_blueprint(collection_bp, url_prefix="/api")

FRONTEND_DIR = os.path.join(BASE_DIR, "..", "frontend")


@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/health")
def health():
    return jsonify({
        "status": "online",
        "service": "pokemon-card-scanner",
        "photo_identification": identify.is_configured(),
    })


@app.route("/<path:filename>")
def static_files(filename):
    return send_from_directory(FRONTEND_DIR, filename)


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "0") == "1"
    # HTTPS=1 gera um certificado autoassinado (útil para testar câmera no Android).
    ssl_context = "adhoc" if os.getenv("HTTPS", "0") == "1" else None
    app.run(host="0.0.0.0", port=port, debug=debug, ssl_context=ssl_context)
