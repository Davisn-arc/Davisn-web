
import os
import logging
import secrets
from pathlib import Path

from flask import (
    Flask,
    request,
    jsonify,
    send_from_directory,
    session
)
from dotenv import load_dotenv

from server.ai import chat as ai_chat
from server.memory import (
    get_history,
    save_message,
    memory_count,
    build_memory_context,
    remember_from_message,
    clear_memory
)

# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
CLIENT_DIR = BASE_DIR / "client"
ASSETS_DIR = CLIENT_DIR / "assets"

load_dotenv(BASE_DIR / ".env")

app = Flask(__name__, static_folder=None)

app.secret_key = os.getenv("SECRET_KEY")

if not app.secret_key:
    raise RuntimeError("SECRET_KEY is missing from your .env file.")

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.getenv("COOKIE_SECURE", "false").lower() == "true",
    PERMANENT_SESSION_LIFETIME=60 * 60 * 24 * 30
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Davisn.Web")

MAX_MESSAGE_LENGTH = 10000


# --------------------------------------------------
# VISITOR SESSION
# --------------------------------------------------

def get_user_id():
    if "davisn_user_id" not in session:
        session["davisn_user_id"] = secrets.token_urlsafe(32)
        session.permanent = True

    return session["davisn_user_id"]


# --------------------------------------------------
# HOMEPAGE
# --------------------------------------------------

@app.route("/")
def index():
    return send_from_directory(str(ASSETS_DIR), "index.html")


# --------------------------------------------------
# FRONTEND ASSETS
# --------------------------------------------------

@app.route("/assets/<path:filename>")
def assets(filename):
    return send_from_directory(str(ASSETS_DIR), filename)


# --------------------------------------------------
# HEALTH CHECK
# --------------------------------------------------

@app.route("/api/health")
def health():
    return jsonify({
        "success": True,
        "message": "Davisn Web is online.",
        "mode": "cloud"
    })


# --------------------------------------------------
# CHAT
# --------------------------------------------------

@app.route("/api/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json(silent=True) or {}

        message = str(data.get("message", "")).strip()

        if not message:
            return jsonify({
                "success": False,
                "message": "Please enter a message."
            }), 400

        if len(message) > MAX_MESSAGE_LENGTH:
            return jsonify({
                "success": False,
                "message": "Your message is too long."
            }), 400

        user_id = get_user_id()

        history = get_history(user_id, limit=30)
        memory_context = build_memory_context(user_id, limit=50)

        result = ai_chat(
            message,
            history=history,
            memory_context=memory_context
        )

        if not isinstance(result, dict):
            result = {
                "success": True,
                "message": str(result)
            }

        if not result.get("success"):
            return jsonify(result), 502

        reply = str(result.get("message", "")).strip()

        if not reply:
            return jsonify({
                "success": False,
                "message": "Davisn received an empty AI response."
            }), 502

        save_message(user_id, "user", message)

        remembered = remember_from_message(user_id, message)

        save_message(user_id, "assistant", reply)

        return jsonify({
            "success": True,
            "message": reply,
            "mode": "cloud",
            "memory_saved": bool(remembered),
            "remembered": remembered
        })

    except Exception:
        logger.exception("Chat request failed")

        return jsonify({
            "success": False,
            "message": "Davisn encountered a server error. Please try again."
        }), 500


# --------------------------------------------------
# MEMORY STATUS
# --------------------------------------------------

@app.route("/api/memory")
def memory_status():
    try:
        user_id = get_user_id()
        result = memory_count(user_id)

        return jsonify({
            "success": True,
            "conversations": result["conversations"],
            "memories": result["memories"],
            "total": result["total"]
        })

    except Exception:
        logger.exception("Memory status failed")

        return jsonify({
            "success": False,
            "message": "Could not retrieve memory status."
        }), 500


# --------------------------------------------------
# CLEAR MEMORY
# --------------------------------------------------

@app.route("/api/memory/clear", methods=["POST"])
def clear_user_memory():
    try:
        user_id = get_user_id()
        clear_memory(user_id)

        return jsonify({
            "success": True,
            "message": "Your Davisn conversation history and memories have been cleared."
        })

    except Exception:
        logger.exception("Memory clearing failed")

        return jsonify({
            "success": False,
            "message": "Could not clear memory."
        }), 500


# --------------------------------------------------
# ERROR HANDLERS
# --------------------------------------------------

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "success": False,
        "message": "Davisn endpoint not found."
    }), 404


@app.errorhandler(500)
def server_error(error):
    logger.exception("Internal server error")

    return jsonify({
        "success": False,
        "message": "Davisn internal server error."
    }), 500


# --------------------------------------------------
# LOCAL DEVELOPMENT
# --------------------------------------------------

if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False
    )
