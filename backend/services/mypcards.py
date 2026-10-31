# Servico de precos - MYP Cards.
# Preparado para integracao com a API oficial do MYP Cards.
# Documentacao: https://mypcards.com/acesso-api

import os
import requests

BASE_URL = os.getenv("MYPCARDS_API_BASE_URL", "https://api.mypcards.com")
TOKEN = os.getenv("MYPCARDS_API_TOKEN", "")


def headers():
    h = {"Accept": "application/json", "Content-Type": "application/json"}
    if TOKEN:
        h["X-Api-Token"] = TOKEN
    return h


def check_price(name, set_name=None, number=None):
    """
    Consulta preco de uma carta no MYP Cards.

    Retorna dicionario com 'configured', 'prices' e 'message'.
    """
    if not TOKEN:
        return {
            "configured": False,
            "message": "Token do MYP Cards nao configurado.",
            "prices": None,
        }

    # TODO: Implementar chamada real ao endpoint de precos do MYP Cards
    # Exemplo (ajustar conforme documentacao oficial):
    # resp = requests.post(f"{BASE_URL}/pokemon/prices", json={...}, headers=headers(), timeout=20)

    return {
        "configured": True,
        "message": "Endpoint de precos do MYP Cards pendente de implementacao.",
        "prices": None,
    }
