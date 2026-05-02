import os
import logging
from datetime import datetime
from functools import wraps
import re

from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
from flask_cors import CORS

from dotenv import load_dotenv
load_dotenv()

# Core modules
from rag_engine import RAGEngine
from llm_handler import LLMHandler, analyze_sentiment, extract_topics
from user_manager import UserManager
from session_memory import SessionMemory

# ─────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# APP INIT
# ─────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "chatbot-secret")

CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# ─────────────────────────────────────────────
# INIT SYSTEMS
# ─────────────────────────────────────────────
logger.info("Initializing chatbot systems...")

rag = RAGEngine(db_path="./chroma_db")
llm = LLMHandler()
user_mgr = UserManager(db_path="./data/users.json")
session_mem = SessionMemory(max_history=20)

logger.info("All systems initialized.")

# ─────────────────────────────────────────────
# MEMORY EXTRACTION (IMPORTANT)
# ─────────────────────────────────────────────
def extract_user_memory(text):
    text = text.lower()

    if "my name is" in text:
        return text

    if "my favorite" in text:
        return text

    if "remember this" in text:
        return text

    return None

# ─────────────────────────────────────────────
# AUTH DECORATOR
# ─────────────────────────────────────────────
def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("Authorization", "").replace("Bearer ", "")

        if not token:
            return jsonify({"error": "No token"}), 401

        user = user_mgr.verify_token(token)

        if not user:
            return jsonify({"error": "Invalid token"}), 401

        request.current_user = user
        return f(*args, **kwargs)

    return decorated

# ─────────────────────────────────────────────
# PAGES
# ─────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

# ─────────────────────────────────────────────
# HEALTH CHECK
# ─────────────────────────────────────────────
@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "model": getattr(llm, "model", "none"),
        "groq_available": getattr(llm, "groq_available", False),
        "gemini_available": getattr(llm, "gemini_available", False),
        "hf_available": getattr(llm, "hf_available", False),
        "timestamp": datetime.now().isoformat()
    })

# ─────────────────────────────────────────────
# AUTH APIs
# ─────────────────────────────────────────────
@app.route("/api/auth/register", methods=["POST"])
def register():
    data = request.json or {}

    success, msg = user_mgr.create_user(
        data.get("username"),
        data.get("password"),
        data.get("email")
    )

    if success:
        return jsonify({"message": msg}), 201
    return jsonify({"error": msg}), 400


@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.json or {}

    success, token, user_info = user_mgr.authenticate(
        data.get("username"),
        data.get("password")
    )

    if success:
        session_id = session_mem.create_session(user_info["username"])

        return jsonify({
            "token": token,
            "user": user_info,
            "session_id": session_id
        })

    return jsonify({"error": token}), 401


@app.route("/api/auth/verify", methods=["GET"])
@require_auth
def verify():
    return jsonify({"user": request.current_user})


@app.route("/api/auth/logout", methods=["POST"])
@require_auth
def logout():
    username = request.current_user["username"]
    session_mem.end_session(username)
    return jsonify({"message": "Logged out"})


# ─────────────────────────────────────────────
# CHAT API (RAG + MEMORY FIXED)
# ─────────────────────────────────────────────
@app.route("/api/chat", methods=["POST"])
@require_auth
def chat():
    data = request.json or {}
    query = data.get("message", "").strip()
    session_id = data.get("session_id")

    if not query:
        return jsonify({"error": "Message cannot be empty"}), 400

    # ✅ GET USER FIRST (fixes your previous crash)
    user = request.current_user
    username = user["username"]

    # 🔥 STORE MEMORY (FIXED)
    memory = extract_user_memory(query)
    if memory:
        rag.store_user_memory(username, memory)

    # SESSION HANDLING
    if not session_id:
        session_id = session_mem.get_user_session(username)
        if not session_id:
            session_id = session_mem.create_session(username)

    # SAVE USER MESSAGE
    session_mem.add_message(session_id, "user", query)

    # 🔥 RAG RETRIEVAL
    context_docs = rag.retrieve_relevant(query, n_results=5)
    user_memories = rag.get_user_memories(username, query, n_results=3)
    history = session_mem.get_history(session_id, n_messages=8)

    # DEBUG (IMPORTANT FOR YOU)
    print("---- DEBUG RAG ----")
    print("Query:", query)
    print("User:", username)
    print("Memories:", user_memories)
    print("-------------------")

    # GENERATE RESPONSE
    result = llm.generate_response(
        query=query,
        context_docs=context_docs,
        user_memories=user_memories,
        session_history=history,
        user_profile=user
    )

    response_text = result["response"]

    # SAVE RESPONSE
    session_mem.add_message(session_id, "assistant", response_text)

    return jsonify({
        "response": response_text,
        "model": result.get("model", "none"),
        "topics": result.get("topics", []),
        "sentiment": result.get("sentiment", "neutral"),
        "session_id": session_id
    })


# ─────────────────────────────────────────────
# RUN SERVER
# ─────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"Starting chatbot on port {port}")
    socketio.run(app, host="0.0.0.0", port=port)