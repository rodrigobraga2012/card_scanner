"""
Catálogo TCGdex: busca de cartas e casamento (match) dos dados lidos na foto
com a carta exata do catálogo.

Documentação: https://tcgdex.dev
O casamento é feito sempre no catálogo em inglês, que é o mais completo e o que
traz preços. Cartas em português usam os mesmos IDs (ex.: swsh3-136).
"""

import re
import time

import requests

BASE_URL = "https://api.tcgdex.net/v2"
TIMEOUT = 15

_session = requests.Session()
_sets_cache = {"data": None, "at": 0.0}
SETS_TTL = 24 * 3600


def _get(path, params=None):
    resp = _session.get(f"{BASE_URL}{path}", params=params, timeout=TIMEOUT)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.json()


def image_url(base, quality="high", ext="png"):
    """A TCGdex devolve a imagem sem extensão; monta a URL final."""
    if not base:
        return None
    return f"{base}/{quality}.{ext}"


def all_sets():
    """Lista de coleções (em cache por 24h)."""
    now = time.time()
    if _sets_cache["data"] is None or now - _sets_cache["at"] > SETS_TTL:
        data = _get("/en/sets") or []
        _sets_cache["data"] = {s["id"]: s for s in data}
        _sets_cache["at"] = now
    return _sets_cache["data"]


def set_id_of(card_id):
    return card_id.rsplit("-", 1)[0] if card_id and "-" in card_id else None


def get_card(card_id, language="en"):
    """Detalhe completo da carta (inclui 'pricing')."""
    card = _get(f"/{language}/cards/{card_id}")
    if card is None and language != "en":
        card = _get(f"/en/cards/{card_id}")
    return card


def search_by_name(name, language="en"):
    if not name:
        return []
    return _get(f"/{language}/cards", params={"name": name}) or []


def _norm_number(value):
    """'006' -> '6', 'TG05' -> 'tg5', 'SWSH050' -> 'swsh50'."""
    if not value:
        return ""
    value = str(value).strip().lower()
    return re.sub(r"(?<![0-9])0+(?=[0-9])", "", value)


def _norm_name(value):
    return re.sub(r"\s+", " ", (value or "").strip().lower())


def _number_variants(number):
    """Formatos possíveis do localId na TCGdex ('6', '06', '006')."""
    n = str(number).strip()
    out = [n]
    digits = re.fullmatch(r"([A-Za-z]*)(\d+)", n)
    if digits:
        prefix, num = digits.groups()
        for width in (1, 2, 3):
            out.append(f"{prefix}{int(num):0{width}d}")
    return list(dict.fromkeys(out))


def _summary(card, score=0, reasons=None):
    sets = all_sets()
    sid = set_id_of(card.get("id"))
    s = sets.get(sid, {})
    return {
        "id": card.get("id"),
        "name": card.get("name"),
        "number": card.get("localId"),
        "set_id": sid,
        "set_name": s.get("name"),
        "set_total": (s.get("cardCount") or {}).get("official"),
        "image": image_url(card.get("image")),
        "score": score,
        "reasons": reasons or [],
    }


def match_card(info, limit=5):
    """
    Recebe o que a IA leu na carta e devolve candidatos do catálogo,
    ordenados do mais provável para o menos provável.
    """
    name_en = (info.get("name_en") or info.get("name") or "").strip()
    number = info.get("number")
    total = info.get("set_total")
    set_guess = _norm_name(info.get("set_name_guess"))

    try:
        total_int = int(re.sub(r"\D", "", str(total))) if total else None
    except ValueError:
        total_int = None

    sets = all_sets()
    sets_with_total = [
        sid for sid, s in sets.items()
        if total_int and (s.get("cardCount") or {}).get("official") == total_int
    ]

    # 1) Candidatos pelo nome (o filtro da TCGdex é "contém")
    pool = {}
    for c in search_by_name(name_en):
        pool[c["id"]] = c
    if not pool and " " in name_en:
        # Ex.: "Charizard ex" -> "Charizard"
        for c in search_by_name(name_en.split(" ")[0]):
            pool[c["id"]] = c

    # 2) Busca direta: coleção com o mesmo total + número da carta
    if number and sets_with_total:
        for sid in sets_with_total[:6]:
            for n in _number_variants(number):
                cid = f"{sid}-{n}"
                if cid in pool:
                    break
                card = _get(f"/en/cards/{cid}")
                if card:
                    pool[cid] = card
                    break

    target_num = _norm_number(number)
    target_name = _norm_name(name_en)

    scored = []
    for c in pool.values():
        score, reasons = 0, []
        sid = set_id_of(c["id"])
        if target_num and _norm_number(c.get("localId")) == target_num:
            score += 4
            reasons.append("número")
        if sid in sets_with_total:
            score += 3
            reasons.append("total da coleção")
        cname = _norm_name(c.get("name"))
        if cname == target_name:
            score += 4
            reasons.append("nome")
        elif target_name and (target_name in cname or cname in target_name):
            score += 2
            reasons.append("nome parecido")
        elif target_name:
            score -= 2  # mesmo número/coleção, mas outra carta
        if set_guess and set_guess == _norm_name((sets.get(sid) or {}).get("name")):
            score += 1
            reasons.append("nome da coleção")
        scored.append((score, c, reasons))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [_summary(c, s, r) for s, c, r in scored[:limit]]
