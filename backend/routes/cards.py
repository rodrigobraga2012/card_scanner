"""
Rotas de cartas Pokémon.
Integra com a API pública do TCGdex para buscar cartas por nome/coleção.
Documentação: https://docs.tcgdex.net/
"""

from flask import Blueprint, jsonify, request
import requests

cards_bp = Blueprint("cards", __name__)

TCGDEX_BASE_URL = "https://api.tcgdex.net/v2"

# Mapeamento de idiomas da TCGdex para português amigável
LANGUAGE_MAP = {
    "en": "Inglês",
    "fr": "Francês",
    "de": "Alemão",
    "es": "Espanhol",
    "it": "Italiano",
    "pt": "Português",
    "ja": "Japonês",
    "ko": "Coreano",
    "zh-hant": "Chinês Tradicional",
    "zh-hans": "Chinês Simplificado",
}


def normalize_language(code):
    return LANGUAGE_MAP.get(code, code)


@cards_bp.route("/cards/search", methods=["GET"])
def search_cards():
    """
    Busca cartas no catálogo TCGdex por nome.
    Query params:
      q - nome do Pokémon ou da carta (ex: "Pikachu", "Charizard")
      language - idioma opcional (default: pt)
    """
    query = request.args.get("q", "").strip()
    language = request.args.get("language", "en")

    if not query:
        return jsonify({"error": "Parâmetro 'q' é obrigatório"}), 400

    try:
        # Busca cartas pela TCGdex API
        # Formato correto: /v2/{language}/cards?name={query}
        url = f"{TCGDEX_BASE_URL}/{language}/cards"
        params = {"name": query}
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()

        # A TCGdex retorna um array direto, não envolto em {data: [...]}
        cards_list = data if isinstance(data, list) else data.get("data", [])

        results = []
        for card in cards_list:
            results.append({
                "id": card.get("id"),
                "name": card.get("name"),
                "localized_name": card.get("name"),
                "hp": card.get("hp"),
                "number": card.get("localId") or card.get("number"),
                "set_id": card.get("set", {}).get("id") if isinstance(card.get("set"), dict) else None,
                "set_name": None,
                "rarity": card.get("rarity"),
                "type": card.get("type"),
                "category": card.get("category"),
                "suite": card.get("suite"),
                "evolves_from": card.get("evolves_from"),
                "image": card.get("image"),
                "language": normalize_language(language),
            })

        return jsonify({
            "query": query,
            "language": language,
            "total": len(results),
            "cards": results,
            "source": "TCGdex"
        })

    except requests.exceptions.RequestException as exc:
        return jsonify({"error": f"Erro ao consultar TCGdex: {str(exc)}"}), 502


@cards_bp.route("/cards/<card_id>", methods=["GET"])
def get_card_detail(card_id):
    """
    Retorna detalhes completos de uma carta específica pelo ID da TCGdex.
    """
    language = request.args.get("language", "en")

    try:
        # Formato correto: /v2/{language}/cards/{id}
        url = f"{TCGDEX_BASE_URL}/{language}/cards/{card_id}"
        response = requests.get(url, timeout=15)
        if response.status_code == 404:
            url = f"{TCGDEX_BASE_URL}/en/cards/{card_id}"
            response = requests.get(url, timeout=15)
        response.raise_for_status()
        card = response.json()

        detail = {
            "id": card.get("id"),
            "name": card.get("name"),
            "localized_name": card.get("name"),
            "hp": card.get("hp"),
            "number": card.get("localId") or card.get("number"),
            "set_id": card.get("set", {}).get("id") if isinstance(card.get("set"), dict) else None,
            "set_name": None,
            "rarity": card.get("rarity"),
            "type": card.get("type"),
            "category": card.get("category"),
            "suite": card.get("suite"),
            "evolves_from": card.get("evolves_from"),
            "image": card.get("image"),
            "language": normalize_language(language),
            "attacks": card.get("attacks", []),
            "weaknesses": card.get("weaknesses", []),
            "resistances": card.get("resistances", []),
            "retreat_cost": card.get("retreat_cost"),
            "artist": card.get("artist"),
        }

        return jsonify(detail)

    except requests.exceptions.RequestException as exc:
        return jsonify({"error": f"Erro ao buscar detalhe da carta: {str(exc)}"}), 502


@cards_bp.route("/cards/sets", methods=["GET"])
def list_sets():
    """Lista coleções disponíveis na TCGdex."""
    language = request.args.get("language", "en")

    try:
        # Formato correto: /v2/{language}/sets
        url = f"{TCGDEX_BASE_URL}/{language}/sets"
        response = requests.get(url, timeout=15)
        if response.status_code == 404:
            url = f"{TCGDEX_BASE_URL}/en/sets"
            response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()

        # A TCGdex retorna um array direto para sets
        sets_list = data if isinstance(data, list) else data.get("data", [])

        sets = []
        for s in sets_list:
            sets.append({
                "id": s.get("id"),
                "name": s.get("name"),
                "release_date": s.get("release_date"),
                "symbol": s.get("symbol"),
                "card_count": s.get("cardCount", {}),
            })

        return jsonify({"sets": sets, "source": "TCGdex"})

    except requests.exceptions.RequestException as exc:
        return jsonify({"error": f"Erro ao listar coleções: {str(exc)}"}), 502
