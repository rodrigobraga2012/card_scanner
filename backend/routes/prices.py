# Rotas de preços - Integracao com MYP Cards
# Preparado para consumir a API oficial do MYP Cards.
# Requer token de acesso (solicitar em https://mypcards.com/acesso-api).
#
# Limites:
# - Sem token: 10 requisicoes por minuto
# - Com token aprovado: 60 requisicoes por minuto

from flask import Blueprint, jsonify, request
import os
import requests

prices_bp = Blueprint("prices", __name__)

MYPCARDS_BASE_URL = os.getenv("MYPCARDS_API_BASE_URL", "https://api.mypcards.com")
MYPCARDS_TOKEN = os.getenv("MYPCARDS_API_TOKEN", "")


def build_headers():
    """Constrói cabecalhos de autenticacao para a API do MYP Cards."""
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    if MYPCARDS_TOKEN:
        headers["X-Api-Token"] = MYPCARDS_TOKEN
    return headers


@prices_bp.route("/prices/check", methods=["POST"])
def check_price():
    """
    Consulta preco de uma carta no MYP Cards.

    Corpo esperado (JSON):
    {
        "name": "Nome da carta",
        "set": "Nome da colecao",
        "number": "Numero da carta",
        "rarity": "Raridade",
        "language": "Portugues"
    }

    Retorna os precos encontrados ou indica que a API nao esta configurada.
    """
    data = request.get_json(silent=True) or {}

    name = data.get("name", "")
    set_name = data.get("set", "")
    number = data.get("number", "")

    if not name:
        return jsonify({"error": "Nome da carta e obrigatorio"}), 400

    # Se nao houver token configurado, retorna instrucao clara para o usuario
    if not MYPCARDS_TOKEN:
        return jsonify({
            "configured": False,
            "message": "API do MYP Cards nao configurada. Adicione MYPCARDS_API_TOKEN no .env",
            "instructions": "Solicite acesso em https://mypcards.com/acesso-api",
            "card": {
                "name": name,
                "set": set_name,
                "number": number,
            },
            "prices": None,
            "source": "MYP Cards (pendente de configuracao)"
        }), 200

    try:
        # TODO: Substituir pelo endpoint real da API do MYP Cards
        # Exemplo hipotetico (ajustar conforme documentacao oficial):
        # url = f"{MYPCARDS_BASE_URL}/pokemon/prices"
        # payload = {"name": name, "set": set_name, "number": number}
        # response = requests.post(url, json=payload, headers=build_headers(), timeout=20)

        return jsonify({
            "configured": True,
            "message": "Token configurado. Implemente o endpoint real de precos do MYP Cards aqui.",
            "card": {
                "name": name,
                "set": set_name,
                "number": number,
            },
            "prices": None,
            "source": "MYP Cards (pendente de implementacao do endpoint)"
        }), 200

    except requests.exceptions.RequestException as exc:
        return jsonify({
            "error": "Erro ao consultar MYP Cards: " + str(exc),
            "source": "MYP Cards"
        }), 502


@prices_bp.route("/prices/configured", methods=["GET"])
def is_configured():
    """Verifica se o token do MYP Cards esta configurado."""
    return jsonify({"configured": bool(MYPCARDS_TOKEN)})
