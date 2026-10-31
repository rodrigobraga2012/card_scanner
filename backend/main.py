"""
Pokémon Card Scanner - Backend (Flask)
Projeto baseado na conversa com o ChatGPT sobre o scanner de cartas Pokémon.

Arquitetura:
- Flask como servidor web (leve, fácil de rodar no notebook)
- SQLite para histórico local da coleção
- Integração com TCGdex (catálogo público de cartas Pokémon)
- Integração preparada com MYP Cards (preços no Brasil)

Execução:
    pip install -r requirements.txt
    python main.py

O servidor escuta em 0.0.0.0:5000 para aceitar conexões do iPhone na mesma rede Wi-Fi.
"""

import os
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv

from routes.cards import cards_bp
from routes.prices import prices_bp
from routes.collection import collection_bp

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()

app = Flask(__name__, static_folder=None)

# Habilita CORS para permitir acesso do frontend (mesmo dispositivo ou rede local)
CORS(app)

# Registra blueprints de rotas
app.register_blueprint(cards_bp, url_prefix="/api")
app.register_blueprint(prices_bp, url_prefix="/api")
app.register_blueprint(collection_bp, url_prefix="/api")

# Caminho absoluto para o frontend
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "..", "frontend")


@app.route("/")
def index():
    """Serve a página principal do scanner."""
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/<path:filename>")
def static_files(filename):
    """Serve arquivos estáticos do frontend (CSS, JS, imagens, etc.)."""
    return send_from_directory(FRONTEND_DIR, filename)


@app.route("/health")
def health():
    """Endpoint de saúde para verificar se o servidor está online."""
    return jsonify({"status": "online", "service": "pokemon-card-scanner"})


if __name__ == "__main__":
    # Debug desativado em produção. Host 0.0.0.0 permite acesso pelo iPhone na rede Wi-Fi.
    app.run(host="0.0.0.0", port=5000, debug=True)
