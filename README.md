# 🤖 ARIA — Adaptive Responsive Intelligent Assistant

ARIA is a full-stack AI chatbot built from scratch using a custom **Retrieval-Augmented Generation (RAG)** architecture.

It combines:

* Vector search (ChromaDB)
* User memory persistence
* Session-based conversation tracking
* Multi-LLM backend (Groq, Gemini, HuggingFace)

to deliver **personalized, context-aware AI conversations**.

---

## 🚀 Features

### 🧠 RAG (Retrieval-Augmented Generation)

* Uses **ChromaDB vector database**
* Embeddings powered by **SentenceTransformers**
* Retrieves relevant knowledge + user memory before generating responses

### 👤 User Memory System

* Stores personal facts (e.g., name, preferences)
* Retrieves them across conversations
* Enables **personalized AI responses**

### 💬 Session-Based Chat

* Tracks conversation history
* Maintains context across messages
* Supports multi-session users

### 🔐 Authentication System

* JWT-based login & registration
* Role-based user system
* Secure session handling

### ⚡ Multi-LLM Support

* Groq (fastest, primary)
* Google Gemini (fallback)
* HuggingFace (fallback)

### 🧩 Modular Architecture

* Clean separation:

  * `rag_engine.py`
  * `llm_handler.py`
  * `session_memory.py`
  * `user_manager.py`

---

## 🏗️ Project Structure

```
chatbot_llm/
│
├── app.py                # Flask backend (API + routes)
├── rag_engine.py        # RAG system (ChromaDB + embeddings)
├── llm_handler.py       # LLM integration (Groq/Gemini/HF)
├── session_memory.py    # Chat history management
├── user_manager.py      # Auth & user profiles
│
├── chroma_db/           # Vector database (auto-generated)
├── data/                # User + session storage
├── templates/           # Frontend HTML
├── static/              # CSS / JS assets
│
├── requirements.txt
├── .env
└── README.md
```

---

## ⚙️ Tech Stack

* **Backend:** Flask, Flask-SocketIO
* **AI/ML:** SentenceTransformers, RAG
* **Vector DB:** ChromaDB
* **LLM APIs:** Groq, Gemini, HuggingFace
* **Auth:** JWT
* **Frontend:** HTML, CSS, JS

---

## 🧠 How RAG Works in This Project

1. User sends query
2. System retrieves:

   * Relevant knowledge from vector DB
   * User-specific memory
3. Context + history injected into LLM prompt
4. LLM generates personalized response

---

## 🔑 Environment Variables

Create a `.env` file:

```
GROQ_API_KEY=your_groq_key
GEMINI_API_KEY=your_gemini_key   # optional
HF_API_KEY=your_hf_key           # optional
SECRET_KEY=your_secret_key
```

---

## ▶️ Run Locally

```bash
# 1. Clone repo
git clone https://github.com/ankitMishra-droid/rag-chatbot.git

# 2. Go to project
cd rag-chatbot

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run server
python app.py
```

App runs on:

```
http://localhost:5000
```

---