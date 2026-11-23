"""
Rotas de preços em reais.
Usa os preços de mercado da TCGdex (Cardmarket/TCGplayer) convertidos pela
cotação do dia. Devolve também links para conferir no mercado brasileiro.
"""

from urllib.parse import quote_plus

import requests
from flask import Blueprint, jsonify, request

from services import pricing, tcgdex

prices_bp = Blueprint("prices", __name__)


def br_links(name):
    q = quote_plus(name or "")
    return {
        "liga": f"https://www.ligapokemon.com.br/?view=cards/search&card={q}",
        "mypcards": f"https://mypcards.com/pokemon?ProdutoSearch%5Bquery%5D={q}",
    }


@prices_bp.route("/prices/<card_id>", methods=["GET"])
def card_prices(card_id):
    variant = request.args.get("variant", "unknown")
    try:
        card = tcgdex.get_card(card_id)
    except requests.RequestException as exc:
        return jsonify({"error": f"Erro ao consultar TCGdex: {exc}"}), 502
    if not card:
        return jsonify({"error": "Carta não encontrada."}), 404

    result = pricing.build_prices(card, variant)
    result["card_id"] = card_id
    result["links"] = br_links(card.get("name"))
    return jsonify(result)
