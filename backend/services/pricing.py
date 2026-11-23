"""
Preços de mercado convertidos para reais (R$).

Fontes:
- TCGdex 'pricing': Cardmarket (Europa, EUR) e TCGplayer (EUA, USD)
- AwesomeAPI: cotação do dia USD-BRL e EUR-BRL (cache de 1h)

Observação: são preços internacionais convertidos. O mercado brasileiro
(Liga Pokémon, MYP Cards) pode variar; o app mostra links para conferir.
"""

import time

import requests

FX_URL = "https://economia.awesomeapi.com.br/json/last/USD-BRL,EUR-BRL"
FX_TTL = 3600
_fx_cache = {"data": None, "at": 0.0}

# Variantes do TCGplayer em ordem de preferência por dica de variante
TCGP_VARIANTS = {
    "normal": ["normal", "holofoil", "reverse-holofoil", "1st-edition", "unlimited"],
    "holo": ["holofoil", "unlimited-holofoil", "normal", "reverse-holofoil"],
    "reverse": ["reverse-holofoil", "normal", "holofoil"],
    "first_edition": ["1st-edition-holofoil", "1st-edition", "1st-edition-normal", "holofoil"],
    "unknown": ["normal", "holofoil", "reverse-holofoil", "unlimited-holofoil", "1st-edition"],
}

VARIANT_LABELS = {
    "normal": "Normal",
    "holofoil": "Holo",
    "reverse-holofoil": "Reverse Holo",
    "1st-edition": "1ª Edição",
    "1st-edition-holofoil": "1ª Edição Holo",
    "1st-edition-normal": "1ª Edição",
    "unlimited": "Unlimited",
    "unlimited-holofoil": "Unlimited Holo",
}


def get_rates():
    """Retorna {'USD': x, 'EUR': y} em BRL, ou None se a cotação falhar."""
    now = time.time()
    if _fx_cache["data"] and now - _fx_cache["at"] < FX_TTL:
        return _fx_cache["data"]
    try:
        resp = requests.get(FX_URL, timeout=10)
        resp.raise_for_status()
        d = resp.json()
        rates = {
            "USD": float(d["USDBRL"]["bid"]),
            "EUR": float(d["EURBRL"]["bid"]),
            "updated": d["USDBRL"].get("create_date"),
        }
        _fx_cache.update(data=rates, at=now)
        return rates
    except (requests.RequestException, KeyError, ValueError):
        return _fx_cache["data"]  # usa a última cotação conhecida, se houver


def _brl(value, rate):
    if value is None or rate is None:
        return None
    try:
        return round(float(value) * rate, 2)
    except (TypeError, ValueError):
        return None


def build_prices(card, variant_hint="unknown"):
    """Monta o resumo de preços em R$ a partir do detalhe da carta da TCGdex."""
    pricing = (card or {}).get("pricing") or {}
    rates = get_rates()
    if not rates:
        return {"available": False, "message": "Não foi possível obter a cotação do dólar/euro."}

    result = {
        "available": False,
        "rates": rates,
        "tcgplayer": None,
        "cardmarket": None,
        "reference": None,
        "reference_source": None,
        "variant": None,
    }

    # TCGplayer (USD)
    tp = pricing.get("tcgplayer") or {}
    tp_variants = []
    for key, val in tp.items():
        if isinstance(val, dict) and ("marketPrice" in val or "midPrice" in val):
            tp_variants.append({
                "key": key,
                "label": VARIANT_LABELS.get(key, key),
                "low": _brl(val.get("lowPrice"), rates["USD"]),
                "market": _brl(val.get("marketPrice") or val.get("midPrice"), rates["USD"]),
                "high": _brl(val.get("highPrice"), rates["USD"]),
            })
    if tp_variants:
        result["tcgplayer"] = {"updated": tp.get("updated"), "variants": tp_variants}

    # Cardmarket (EUR). Campos "-holo" = versão reverse/holo.
    cm = pricing.get("cardmarket") or {}
    if cm:
        use_holo = variant_hint in ("holo", "reverse") and cm.get("trend-holo")
        sfx = "-holo" if use_holo else ""
        result["cardmarket"] = {
            "updated": cm.get("updated"),
            "variant": "Holo/Reverse" if use_holo else "Normal",
            "low": _brl(cm.get(f"low{sfx}"), rates["EUR"]),
            "trend": _brl(cm.get(f"trend{sfx}"), rates["EUR"]),
            "avg30": _brl(cm.get(f"avg30{sfx}"), rates["EUR"]),
        }

    # Preço de referência: TCGplayer da variante mais provável; senão Cardmarket
    by_key = {v["key"]: v for v in tp_variants}
    for key in TCGP_VARIANTS.get(variant_hint, TCGP_VARIANTS["unknown"]):
        v = by_key.get(key)
        if v and v["market"]:
            result["reference"] = v["market"]
            result["reference_source"] = "TCGplayer (mercado EUA)"
            result["variant"] = v["label"]
            break
    if result["reference"] is None and result["cardmarket"]:
        ref = result["cardmarket"]["trend"] or result["cardmarket"]["avg30"]
        if ref:
            result["reference"] = ref
            result["reference_source"] = "Cardmarket (tendência Europa)"
            result["variant"] = result["cardmarket"]["variant"]

    result["available"] = result["reference"] is not None
    if not result["available"]:
        result["message"] = "Esta carta ainda não tem preço de mercado registrado."
    return result
