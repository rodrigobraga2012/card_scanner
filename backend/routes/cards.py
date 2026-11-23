"""
Rotas de cartas Pokémon.
- /api/identify: identifica a carta pela foto (Claude visão + catálogo TCGdex)
- /api/cards/search: busca manual por nome
- /api/cards/<id>: detalhe de uma carta
"""

import requests
from flask import Blueprint, jsonify, request

from services import identify, tcgdex

cards_bp = Blueprint("cards", __name__)

MAX_IMAGE_BYTES = 8 * 1024 * 1024
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}

LANGUAGE_MAP = {
    "en": "Inglês", "pt": "Português", "es": "Espanhol", "fr": "Francês",
    "de": "Alemão", "it": "Italiano", "ja": "Japonês", "ko": "Coreano",
    "zh": "Chinês", "other": "Outro",
}


@cards_bp.route("/identify", methods=["POST"])
def identify_route():
    """Recebe a foto (multipart 'image'), lê a carta e devolve os candidatos."""
    if not identify.is_configured():
        return jsonify({
            "error": "Identificação por foto não configurada. Adicione ANTHROPIC_API_KEY no backend/.env.",
            "configured": False,
        }), 503

    file = request.files.get("image")
    if not file:
        return jsonify({"error": "Nenhuma imagem enviada."}), 400

    media_type = (file.mimetype or "image/jpeg").lower()
    if media_type not in ALLOWED_TYPES:
        return jsonify({"error": f"Formato de imagem não suportado ({media_type})."}), 400

    data = file.read(MAX_IMAGE_BYTES + 1)
    if len(data) > MAX_IMAGE_BYTES:
        return jsonify({"error": "Imagem muito grande (máx. 8 MB)."}), 413

    try:
        info = identify.identify_card(data, media_type)
    except identify.IdentifyError as exc:
        return jsonify({"error": str(exc)}), 502

    if not info.get("is_pokemon_card"):
        return jsonify({
            "detected": info,
            "candidates": [],
            "message": "Não reconheci uma carta Pokémon nesta foto.",
        })

    try:
        candidates = tcgdex.match_card(info)
    except requests.RequestException as exc:
        return jsonify({"error": f"Erro ao consultar o catálogo TCGdex: {exc}"}), 502

    best = candidates[0] if candidates else None
    # Confiável = bateu nome + número (8) e está à frente do 2º colocado
    second = candidates[1]["score"] if len(candidates) > 1 else 0
    confident = bool(best and best["score"] >= 8 and best["score"] > second)

    info["language_label"] = LANGUAGE_MAP.get(info.get("language"), info.get("language"))
    return jsonify({
        "detected": info,
        "candidates": candidates,
        "confident": confident,
    })


@cards_bp.route("/cards/search", methods=["GET"])
def search_cards():
    """Busca cartas no catálogo por nome (em inglês ou português)."""
    query = request.args.get("q", "").strip()
    language = request.args.get("language", "en")
    if not query:
        return jsonify({"error": "Parâmetro 'q' é obrigatório"}), 400

    try:
        cards = tcgdex.search_by_name(query, language)
        if not cards and language != "pt":
            cards = tcgdex.search_by_name(query, "pt")
        sets = tcgdex.all_sets()
    except requests.RequestException as exc:
        return jsonify({"error": f"Erro ao consultar TCGdex: {exc}"}), 502

    results = []
    for c in cards[:40]:
        sid = tcgdex.set_id_of(c.get("id"))
        results.append({
            "id": c.get("id"),
            "name": c.get("name"),
            "number": c.get("localId"),
            "set_id": sid,
            "set_name": (sets.get(sid) or {}).get("name"),
            "image": tcgdex.image_url(c.get("image")),
        })
    return jsonify({"query": query, "total": len(cards), "cards": results})


@cards_bp.route("/cards/<card_id>", methods=["GET"])
def get_card_detail(card_id):
    """Detalhes completos de uma carta pelo ID da TCGdex."""
    try:
        card = tcgdex.get_card(card_id)
    except requests.RequestException as exc:
        return jsonify({"error": f"Erro ao buscar a carta: {exc}"}), 502
    if not card:
        return jsonify({"error": "Carta não encontrada."}), 404

    s = card.get("set") or {}
    return jsonify({
        "id": card.get("id"),
        "name": card.get("name"),
        "number": card.get("localId"),
        "set_id": s.get("id"),
        "set_name": s.get("name"),
        "set_total": (s.get("cardCount") or {}).get("official"),
        "rarity": card.get("rarity"),
        "category": card.get("category"),
        "hp": card.get("hp"),
        "types": card.get("types"),
        "illustrator": card.get("illustrator"),
        "variants": card.get("variants"),
        "image": tcgdex.image_url(card.get("image")),
    })
