"""
User Management - JWT auth, rule-based permissions, profile management
"""
import json
import os
import time
import hashlib
import bcrypt
import jwt
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Tuple

logger = logging.getLogger(__name__)

SECRET_KEY = os.environ.get("SECRET_KEY", "chakra-super-secret-key-change-in-production-2024")
JWT_EXPIRY_HOURS = 24

# Rule-based permission system
ROLES = {
    "admin": {
        "permissions": ["read", "write", "delete", "analytics", "manage_users", 
                       "add_knowledge", "view_all_users", "system_config"],
        "description": "Full system access",
        "chat_limit": -1,  # unlimited
        "knowledge_upload": True
    },
    "power_user": {
        "permissions": ["read", "write", "analytics", "add_knowledge"],
        "description": "Enhanced user with knowledge upload",
        "chat_limit": 1000,
        "knowledge_upload": True
    },
    "user": {
        "permissions": ["read", "write"],
        "description": "Standard user",
        "chat_limit": 200,
        "knowledge_upload": False
    },
    "guest": {
        "permissions": ["read"],
        "description": "Limited guest access",
        "chat_limit": 20,
        "knowledge_upload": False
    }
}

class UserManager:
    def __init__(self, db_path: str = "./data/users.json"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.users = self._load_users()
        self._ensure_admin()

    def _load_users(self) -> Dict:
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {}

    def _save_users(self):
        with open(self.db_path, 'w') as f:
            json.dump(self.users, f, indent=2)

    def _ensure_admin(self):
        """Create default admin if none exists"""
        if not any(u.get("role") == "admin" for u in self.users.values()):
            self.create_user("admin", "admin123", "admin@chakra.ai", "admin")
            logger.info("Default admin created: admin / admin123")

    def create_user(self, username: str, password: str, email: str = "", 
                   role: str = "user") -> Tuple[bool, str]:
        """Create a new user"""
        if username in self.users:
            return False, "Username already exists"
        
        if len(password) < 6:
            return False, "Password must be at least 6 characters"
        
        if role not in ROLES:
            role = "user"
        
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        
        self.users[username] = {
            "username": username,
            "password_hash": hashed,
            "email": email,
            "role": role,
            "created_at": datetime.now().isoformat(),
            "last_login": None,
            "login_count": 0,
            "preferences": {
                "communication_style": "balanced",
                "response_length": "medium",
                "topics_of_interest": [],
                "language_complexity": "intermediate"
            },
            "stats": {
                "total_messages": 0,
                "total_sessions": 0,
                "favorite_topics": []
            },
            "active": True,
            "notifications": []
        }
        
        self._save_users()
        return True, "User created successfully"

    def authenticate(self, username: str, password: str) -> Tuple[bool, str, Optional[Dict]]:
        """Authenticate user and return JWT token"""
        if username not in self.users:
            return False, "Invalid credentials", None
        
        user = self.users[username]
        
        if not user.get("active", True):
            return False, "Account is deactivated", None
        
        if not bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
            return False, "Invalid credentials", None
        
        # Update login info
        self.users[username]["last_login"] = datetime.now().isoformat()
        self.users[username]["login_count"] = user.get("login_count", 0) + 1
        self.users[username]["stats"]["total_sessions"] = user["stats"].get("total_sessions", 0) + 1
        self._save_users()
        
        # Generate JWT
        payload = {
            "username": username,
            "role": user["role"],
            "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRY_HOURS),
            "iat": datetime.utcnow()
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
        
        user_info = {
            "username": username,
            "email": user.get("email", ""),
            "role": user["role"],
            "permissions": ROLES[user["role"]]["permissions"],
            "preferences": user.get("preferences", {}),
            "stats": user.get("stats", {})
        }
        
        return True, token, user_info

    def verify_token(self, token: str) -> Optional[Dict]:
        """Verify JWT token and return user info"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            username = payload["username"]
            
            if username not in self.users:
                return None
            
            user = self.users[username]
            if not user.get("active", True):
                return None
            
            return {
                "username": username,
                "role": user["role"],
                "permissions": ROLES[user["role"]]["permissions"],
                "preferences": user.get("preferences", {}),
                "stats": user.get("stats", {}),
                "chat_limit": ROLES[user["role"]]["chat_limit"],
                "notifications": user.get("notifications", [])
            }
        except jwt.ExpiredSignatureError:
            return None
        except Exception as e:
            logger.warning(f"Token verification error: {e}")
            return None

    def has_permission(self, username: str, permission: str) -> bool:
        """Check if user has a specific permission"""
        if username not in self.users:
            return False
        role = self.users[username]["role"]
        return permission in ROLES.get(role, {}).get("permissions", [])

    def update_preferences(self, username: str, preferences: Dict) -> bool:
        """Update user preferences"""
        if username not in self.users:
            return False
        self.users[username]["preferences"].update(preferences)
        self._save_users()
        return True

    def increment_message_count(self, username: str):
        """Track message count"""
        if username in self.users:
            self.users[username]["stats"]["total_messages"] = \
                self.users[username]["stats"].get("total_messages", 0) + 1
            self._save_users()

    def get_all_users(self) -> List[Dict]:
        """Get all users (admin only)"""
        result = []
        for username, data in self.users.items():
            result.append({
                "username": username,
                "email": data.get("email", ""),
                "role": data.get("role", "user"),
                "created_at": data.get("created_at", ""),
                "last_login": data.get("last_login", ""),
                "login_count": data.get("login_count", 0),
                "total_messages": data.get("stats", {}).get("total_messages", 0),
                "active": data.get("active", True)
            })
        return result

    def update_user_role(self, admin_username: str, target_username: str, new_role: str) -> Tuple[bool, str]:
        """Update user role (admin only)"""
        if not self.has_permission(admin_username, "manage_users"):
            return False, "Insufficient permissions"
        
        if target_username not in self.users:
            return False, "User not found"
        
        if new_role not in ROLES:
            return False, "Invalid role"
        
        if target_username == admin_username:
            return False, "Cannot change your own role"
        
        self.users[target_username]["role"] = new_role
        self._save_users()
        return True, f"Role updated to {new_role}"

    def toggle_user_active(self, admin_username: str, target_username: str) -> Tuple[bool, str]:
        """Enable/disable user"""
        if not self.has_permission(admin_username, "manage_users"):
            return False, "Insufficient permissions"
        
        if target_username not in self.users:
            return False, "User not found"
        
        if target_username == admin_username:
            return False, "Cannot deactivate yourself"
        
        current = self.users[target_username].get("active", True)
        self.users[target_username]["active"] = not current
        self._save_users()
        status = "activated" if not current else "deactivated"
        return True, f"User {status}"

    def add_notification(self, username: str, message: str, notif_type: str = "info"):
        """Add notification for user"""
        if username in self.users:
            notif = {
                "id": f"n_{int(time.time() * 1000)}",
                "message": message,
                "type": notif_type,
                "timestamp": datetime.now().isoformat(),
                "read": False
            }
            if "notifications" not in self.users[username]:
                self.users[username]["notifications"] = []
            self.users[username]["notifications"].append(notif)
            # Keep last 20 notifications
            self.users[username]["notifications"] = self.users[username]["notifications"][-20:]
            self._save_users()

    def mark_notifications_read(self, username: str):
        """Mark all notifications as read"""
        if username in self.users:
            for notif in self.users[username].get("notifications", []):
                notif["read"] = True
            self._save_users()

    def get_user_profile(self, username: str) -> Optional[Dict]:
        """Get full user profile"""
        if username not in self.users:
            return None
        user = self.users[username].copy()
        user.pop("password_hash", None)  # Never expose password hash
        return user
    