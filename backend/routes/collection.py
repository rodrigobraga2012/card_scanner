# Rotas da colecao local (SQLite).
# Permite salvar cartas identificadas e gerenciar a colecao do usuario.

from flask import Blueprint, jsonify, request
import sqlite3
import os

collection_bp = Blueprint("collection", __name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "database", "collection.db")


def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS collection (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            set_name TEXT,
            number TEXT,
            rarity TEXT,
            language TEXT,
            image_url TEXT,
            condition TEXT DEFAULT 'NM',
            price_found REAL,
            price_source TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(collection)")}
    if "card_id" not in cols:
        conn.execute("ALTER TABLE collection ADD COLUMN card_id TEXT")
    conn.commit()
    conn.close()


# Inicializa banco na importacao
init_db()


@collection_bp.route("/collection", methods=["GET"])
def list_collection():
    """Lista todas as cartas salvas na colecao local."""
    conn = get_db()
    rows = conn.execute("SELECT * FROM collection ORDER BY created_at DESC").fetchall()
    conn.close()

    cards = [dict(row) for row in rows]
    total_value = sum((c.get("price_found") or 0) for c in cards)

    return jsonify({
        "total_cards": len(cards),
        "total_value": round(total_value, 2),
        "cards": cards
    })


@collection_bp.route("/collection", methods=["POST"])
def save_card():
    """Salva uma carta identificada na colecao local."""
    data = request.get_json(silent=True) or {}

    if not data.get("name"):
        return jsonify({"error": "Campo 'name' e obrigatorio"}), 400

    conn = get_db()
    cursor = conn.execute("""
        INSERT INTO collection (card_id, name, set_name, number, rarity, language, image_url, condition, price_found, price_source)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("card_id"),
        data.get("name"),
        data.get("set_name"),
        data.get("number"),
        data.get("rarity"),
        data.get("language"),
        data.get("image_url"),
        data.get("condition", "NM"),
        data.get("price_found"),
        data.get("price_source")
    ))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()

    return jsonify({"id": new_id, "message": "Carta salva na colecao"}), 201


@collection_bp.route("/collection/<int:card_id>", methods=["DELETE"])
def delete_card(card_id):
    """Remove uma carta da colecao."""
    conn = get_db()
    conn.execute("DELETE FROM collection WHERE id = ?", (card_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Carta removida da colecao"})


@collection_bp.route("/collection/search", methods=["GET"])
def search_collection():
    """Pesquisa cartas na colecao por nome."""
    query = request.args.get("q", "").strip()
    conn = get_db()
    if query:
        rows = conn.execute(
            "SELECT * FROM collection WHERE name LIKE ? ORDER BY created_at DESC",
            ("%" + query + "%",)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM collection ORDER BY created_at DESC").fetchall()
    conn.close()

    return jsonify({"cards": [dict(row) for row in rows]})
