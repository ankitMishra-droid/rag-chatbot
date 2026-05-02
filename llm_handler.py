import json
import logging
import os
import requests
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

# ❌ Ollama disabled
OLLAMA_ENDPOINTS = []

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# ✅ Multiple working models (auto fallback)
GROQ_MODELS = [
    "llama3-8b-8192",
    "llama-3.1-8b-instant",
    "llama-3.3-70b-versatile"
]

# Gemini
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL   = "gemini-1.5-flash"
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

# HuggingFace
HF_API_KEY = os.environ.get("HF_API_KEY", "")
HF_MODEL   = "mistralai/Mistral-7B-Instruct-v0.3"
HF_API_URL = f"https://api-inference.huggingface.co/models/{HF_MODEL}"

# ─────────────────────────────────────────────

SYSTEM_PROMPT = """You are chakra (Adaptive Responsive Intelligent Assistant), a helpful AI assistant."""

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def analyze_sentiment(text: str) -> str:
    t = text.lower()
    pos = sum(t.count(w) for w in ["great","good","love"])
    neg = sum(t.count(w) for w in ["bad","hate"])
    return "positive" if pos > neg else ("negative" if neg > pos else "neutral")


def extract_topics(text: str) -> List[str]:
    return ["General"]


def _build_context_block(context_docs, user_memories, user_profile):
    parts = []
    if context_docs:
        parts.append("\n".join(d["text"] for d in context_docs[:3]))
    if user_memories:
        parts.append("\n".join(user_memories[:3]))
        memory_text = "\n".join(user_memories)
    return memory_text


def _build_openai_messages(query, context_docs, user_memories, session_history, user_profile):
    messages = [
        {
            "role": "system",
            "content": """You are an intelligent AI assistant with memory.

Use the provided user facts and conversation history to answer.
If user information is available, ALWAYS use it.
Never say you don't know if it's in memory."""
        }
    ]

    # 🔥 Inject user memory
    if user_memories:
        memory_text = "\n".join(user_memories)
        messages.append({
            "role": "system",
            "content": f"User facts:\n{memory_text}"
        })

    # 🔥 Inject chat history
    for msg in session_history[-6:]:
        messages.append({
            "role": msg["role"],
            "content": msg["content"]
        })

    # Current query
    messages.append({
        "role": "user",
        "content": query
    })

    return messages

# ─────────────────────────────────────────────
# MAIN CLASS
# ─────────────────────────────────────────────

class LLMHandler:
    def __init__(self):
        self.ollama_available = False

        self.groq_available   = bool(GROQ_API_KEY)
        self.gemini_available = bool(GEMINI_API_KEY)
        self.hf_available     = bool(HF_API_KEY)

        self.model = (
            f"groq/{GROQ_MODELS[0]}" if self.groq_available else
            f"gemini/{GEMINI_MODEL}" if self.gemini_available else
            f"hf/{HF_MODEL}" if self.hf_available else
            "none"
        )

        logger.info("=== LLM Backend Status ===")
        logger.info(f"Groq   : {'✓ ' + GROQ_MODELS[0] if self.groq_available else '✗'}")
        logger.info(f"Gemini : {'✓ ' + GEMINI_MODEL if self.gemini_available else '✗'}")
        logger.info(f"HF     : {'✓ ' + HF_MODEL if self.hf_available else '✗'}")

    # ─────────────────────────────────────────

    def generate_response(self, query, context_docs, user_memories, session_history, user_profile):
        sentiment = analyze_sentiment(query)
        topics = extract_topics(query)

        response, model_used = self._try_all_backends(
            query, context_docs, user_memories, session_history, user_profile
        )

        return {
            "response": response,
            "sentiment": sentiment,
            "topics": topics,
            "model": model_used,
            "prompt": ""
        }

    # ─────────────────────────────────────────

    def _try_all_backends(self, query, context_docs, user_memories, session_history, user_profile):

        if self.groq_available:
            r = self._call_groq(query, context_docs, user_memories, session_history, user_profile)
            if r:
                return r, f"groq/{GROQ_MODELS[0]}"

        if self.gemini_available:
            r = self._call_gemini(query)
            if r:
                return r, f"gemini/{GEMINI_MODEL}"

        if self.hf_available:
            r = self._call_hf(query)
            if r:
                return r, f"hf/{HF_MODEL}"

        return "❌ No backend working", "none"

    # ─────────────────────────────────────────
    # ✅ GROQ WITH FALLBACK
    # ─────────────────────────────────────────

    def _call_groq(self, query, context_docs, user_memories, session_history, user_profile):
        messages = _build_openai_messages(query, context_docs, user_memories, session_history, user_profile)

        for model in GROQ_MODELS:
            try:
                resp = requests.post(
                    GROQ_API_URL,
                    headers={
                        "Authorization": f"Bearer {GROQ_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model,
                        "messages": messages,
                        "temperature": 0.7
                    },
                    timeout=30,
                )

                print(f"GROQ TRYING: {model} → {resp.status_code}")

                if resp.status_code == 200:
                    return resp.json()["choices"][0]["message"]["content"]

                else:
                    print(f"GROQ FAILED ({model}):", resp.text)

            except Exception as e:
                print(f"GROQ ERROR ({model}):", e)

        return None

    # ─────────────────────────────────────────

    def _call_gemini(self, query):
        try:
            resp = requests.post(
                f"{GEMINI_API_URL}?key={GEMINI_API_KEY}",
                json={"contents":[{"parts":[{"text":query}]}]},
                timeout=30,
            )
            if resp.status_code == 200:
                return resp.json()["candidates"][0]["content"]["parts"][0]["text"]
        except:
            pass
        return None

    # ─────────────────────────────────────────

    def _call_hf(self, query):
        try:
            resp = requests.post(
                HF_API_URL,
                headers={"Authorization": f"Bearer {HF_API_KEY}"},
                json={"inputs": query},
                timeout=30,
            )
            if resp.status_code == 200:
                return resp.json()[0]["generated_text"]
        except:
            pass
        return None


# ─────────────────────────────────────────────
# 🔧 DUMMY FUNCTION (FOR app.py COMPATIBILITY)
# ─────────────────────────────────────────────

def check_ollama_available():
    return False, None, None