# Servico de catalogo Pokemon - TCGdex.
# Fornece funcoes auxiliares para buscar cartas e colecoes.

import requests

BASE_URL = "https://api.tcgdex.net/v2"


def search_cards(query, language="pt"):
    """Busca cartas pelo nome na TCGdex."""
    try:
        resp = requests.get(f"{BASE_URL}/cards", params={"name": query, "language": language}, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        return {"error": str(exc)}


def get_card(card_id, language="pt"):
    """Busca detalhe de uma carta pelo ID."""
    try:
        resp = requests.get(f"{BASE_URL}/cards/{card_id}", params={"language": language}, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        return {"error": str(exc)}


def list_sets(language="pt"):
    """Lista colecoes disponiveis."""
    try:
        resp = requests.get(f"{BASE_URL}/sets", params={"language": language}, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        return {"error": str(exc)}
