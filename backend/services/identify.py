"""
Identificação da carta pela foto usando visão do Claude.

O modelo lê o que está impresso na carta (nome, número "136/189", código da
coleção, idioma, variante) e devolve um JSON estruturado. O casamento com a
carta exata do catálogo é feito depois, em services/tcgdex.py.

Requer ANTHROPIC_API_KEY no .env.
"""

import base64
import json
import os

import anthropic

MODEL = os.getenv("CLAUDE_MODEL", "claude-opus-5-5")

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


def is_configured():
    return bool(os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN"))


def _nullable(t):
    return {"type": [t, "null"]}


CARD_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "is_pokemon_card", "name", "name_en", "number", "set_total",
        "set_code", "set_name_guess", "language", "variant_hint",
        "confidence", "notes",
    ],
    "properties": {
        "is_pokemon_card": {"type": "boolean"},
        "name": _nullable("string"),
        "name_en": _nullable("string"),
        "number": _nullable("string"),
        "set_total": _nullable("string"),
        "set_code": _nullable("string"),
        "set_name_guess": _nullable("string"),
        "language": {
            "type": "string",
            "enum": ["en", "pt", "es", "fr", "de", "it", "ja", "ko", "zh", "other"],
        },
        "variant_hint": {
            "type": "string",
            "enum": ["normal", "holo", "reverse", "first_edition", "unknown"],
        },
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        "notes": {"type": "string"},
    },
}

PROMPT = """Você está identificando uma carta do Pokémon Estampas Ilustradas (TCG) a partir de uma foto tirada com celular.

Leia o que está IMPRESSO na carta e preencha os campos:
- name: o nome exatamente como impresso no topo da carta, incluindo sufixos como "ex", "V", "VMAX", "VSTAR", "GX", "EX".
- name_en: o nome oficial em inglês da mesma carta (ex.: "Pikachu", "Charizard ex", "Professor's Research"). Se a carta estiver em português, traduza para o nome oficial em inglês.
- number: o número de colecionador, que fica no rodapé ANTES da barra (em "136/189" é "136"; em "TG05/TG30" é "TG05"; em promos "SWSH050" é "SWSH050"). Copie como impresso, com zeros à esquerda.
- set_total: o número DEPOIS da barra ("189"). null se não houver barra.
- set_code: a sigla da coleção impressa no rodapé, se existir (ex.: "PAL", "SVI", "DAA"). null se não houver.
- set_name_guess: o nome em inglês da coleção, se você souber com segurança pelo símbolo ou pela sigla. null caso contrário.
- language: idioma em que a carta foi impressa.
- variant_hint: "holo" se a ilustração for brilhante/holográfica, "reverse" se o brilho estiver no resto da carta e não na ilustração, "first_edition" se houver o selo de 1ª edição, "normal" se não houver brilho, "unknown" se não der para saber pela foto.
- confidence: "high" só se você leu nome E número com clareza.
- notes: uma frase curta em português sobre o que dificultou a leitura (reflexo, foco, corte), ou "" se nada.

Se a imagem não for uma carta Pokémon, use is_pokemon_card=false e deixe os demais campos null/"unknown".
Não invente números: se não estiver legível, use null."""


class IdentifyError(Exception):
    pass


def identify_card(image_bytes, media_type="image/jpeg"):
    """Envia a foto para o Claude e devolve o dicionário com os campos lidos."""
    image_b64 = base64.standard_b64encode(image_bytes).decode("utf-8")

    try:
        response = _get_client().beta.messages.create(
            model=MODEL,
            max_tokens=16000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            output_config={
                "effort": "low",
                "format": {"type": "json_schema", "schema": CARD_SCHEMA},
            },
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": media_type, "data": image_b64},
                    },
                    {"type": "text", "text": PROMPT},
                ],
            }],
        )
    except anthropic.AuthenticationError as exc:
        raise IdentifyError("Chave da API da Anthropic inválida.") from exc
    except anthropic.RateLimitError as exc:
        raise IdentifyError("Muitas requisições. Tente novamente em alguns segundos.") from exc
    except anthropic.BadRequestError as exc:
        raise IdentifyError(f"Requisição recusada pela API: {exc.message}") from exc
    except anthropic.APIStatusError as exc:
        raise IdentifyError(f"Erro na API da Anthropic ({exc.status_code}).") from exc
    except anthropic.APIConnectionError as exc:
        raise IdentifyError("Sem conexão com a API da Anthropic.") from exc

    if response.stop_reason == "refusal":
        raise IdentifyError("A análise da imagem foi recusada. Tente outra foto.")
    if response.stop_reason == "max_tokens":
        raise IdentifyError("Resposta incompleta da IA. Tente novamente.")

    text = "".join(b.text for b in response.content if b.type == "text")
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise IdentifyError("A IA devolveu uma resposta inválida.") from exc
