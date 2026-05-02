"""
Session Memory Manager - In-memory session tracking with persistence
"""
import json
import os
import time
from datetime import datetime
from typing import Dict, List, Optional
from collections import deque
import logging

logger = logging.getLogger(__name__)

class SessionMemory:
    def __init__(self, max_history: int = 20, persistence_path: str = "./data/sessions.json"):
        self.max_history = max_history
        self.persistence_path = persistence_path
        self.sessions: Dict[str, Dict] = {}  # session_id -> session data
        self.user_sessions: Dict[str, str] = {}  # username -> active session_id
        os.makedirs(os.path.dirname(persistence_path), exist_ok=True)

    def create_session(self, username: str) -> str:
        """Create new session for user"""
        session_id = f"sess_{username}_{int(time.time() * 1000)}"
        
        self.sessions[session_id] = {
            "session_id": session_id,
            "username": username,
            "created_at": datetime.now().isoformat(),
            "last_active": datetime.now().isoformat(),
            "history": [],
            "context": {},
            "message_count": 0
        }
        
        self.user_sessions[username] = session_id
        return session_id

    def get_session(self, session_id: str) -> Optional[Dict]:
        """Get session by ID"""
        return self.sessions.get(session_id)

    def get_user_session(self, username: str) -> Optional[str]:
        """Get active session ID for user"""
        return self.user_sessions.get(username)

    def add_message(self, session_id: str, role: str, content: str, 
                   metadata: Dict = None) -> bool:
        """Add message to session history"""
        if session_id not in self.sessions:
            return False
        
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        
        session = self.sessions[session_id]
        session["history"].append(message)
        session["last_active"] = datetime.now().isoformat()
        session["message_count"] += 1
        
        # Keep history bounded
        if len(session["history"]) > self.max_history * 2:
            session["history"] = session["history"][-self.max_history * 2:]
        
        return True

    def get_history(self, session_id: str, n_messages: int = 10) -> List[Dict]:
        """Get recent conversation history"""
        if session_id not in self.sessions:
            return []
        return self.sessions[session_id]["history"][-n_messages:]

    def update_context(self, session_id: str, key: str, value):
        """Update session context vchatbotble"""
        if session_id in self.sessions:
            self.sessions[session_id]["context"][key] = value
            self.sessions[session_id]["last_active"] = datetime.now().isoformat()

    def get_context(self, session_id: str, key: str, default=None):
        """Get session context vchatbotble"""
        if session_id not in self.sessions:
            return default
        return self.sessions[session_id]["context"].get(key, default)

    def clear_session(self, session_id: str):
        """Clear session history but keep session alive"""
        if session_id in self.sessions:
            self.sessions[session_id]["history"] = []
            self.sessions[session_id]["context"] = {}

    def end_session(self, username: str):
        """End user's active session"""
        if username in self.user_sessions:
            session_id = self.user_sessions[username]
            if session_id in self.sessions:
                del self.sessions[session_id]
            del self.user_sessions[username]

    def get_all_sessions_stats(self) -> Dict:
        """Get statistics about active sessions"""
        now = time.time()
        active_count = 0
        
        for session in self.sessions.values():
            last = datetime.fromisoformat(session["last_active"]).timestamp()
            if now - last < 1800:  # 30 min
                active_count += 1
        
        return {
            "total_sessions": len(self.sessions),
            "active_sessions": active_count,
            "total_messages": sum(s["message_count"] for s in self.sessions.values())
        }