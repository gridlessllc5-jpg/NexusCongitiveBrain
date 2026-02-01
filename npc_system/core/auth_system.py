"""
Authentication System for Fractured Survival
Handles user registration, login, and session management
Works with both web frontend and Unreal Engine clients
"""
import sqlite3
import hashlib
import secrets
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple
from dataclasses import dataclass
import jwt

# Database path - use dynamic path
try:
    from core.paths import AUTH_DB
    AUTH_DB_PATH = AUTH_DB
except ImportError:
    try:
        from paths import AUTH_DB
        AUTH_DB_PATH = AUTH_DB
    except ImportError:
        AUTH_DB_PATH = "/app/npc_system/database/auth.db"

# JWT Configuration
JWT_SECRET = os.environ.get("JWT_SECRET", secrets.token_hex(32))
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24 * 7  # 1 week

@dataclass
class User:
    """User account data"""
    user_id: str
    username: str
    email: Optional[str]
    player_name: str
    created_at: str
    last_login: str
    is_active: bool
    auth_source: str  # "web" or "unreal"


class AuthSystem:
    """
    Handles user authentication for the NPC system.
    Supports both web-based registration and Unreal Engine account creation.
    """
    
    def __init__(self, db_path: str = AUTH_DB_PATH):
        self.db_path = db_path
        self._initialize_tables()
    
    def _initialize_tables(self):
        """Create authentication tables"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                player_name TEXT NOT NULL,
                created_at TEXT NOT NULL,
                last_login TEXT,
                is_active INTEGER DEFAULT 1,
                auth_source TEXT DEFAULT 'web'
            )
        """)
        
        # API Keys table (for Unreal Engine integration)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_keys (
                key_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                api_key TEXT UNIQUE NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT,
                is_active INTEGER DEFAULT 1,
                description TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # Sessions table (for tracking active sessions)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                token_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                ip_address TEXT,
                user_agent TEXT,
                is_active INTEGER DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        conn.commit()
        conn.close()
        print("✓ Authentication tables initialized")
    
    def _hash_password(self, password: str, salt: str = None) -> Tuple[str, str]:
        """Hash password with salt using SHA-256"""
        if salt is None:
            salt = secrets.token_hex(16)
        
        # Hash password with salt
        password_bytes = (password + salt).encode('utf-8')
        password_hash = hashlib.sha256(password_bytes).hexdigest()
        
        return password_hash, salt
    
    def _generate_user_id(self) -> str:
        """Generate unique user ID"""
        return f"user_{secrets.token_hex(8)}"
    
    def register(
        self,
        username: str,
        password: str,
        email: str = None,
        player_name: str = None,
        auth_source: str = "web"
    ) -> Dict:
        """
        Register a new user account.
        
        Args:
            username: Unique username
            password: Password (will be hashed)
            email: Optional email address
            player_name: Display name in game (defaults to username)
            auth_source: "web" or "unreal"
        
        Returns:
            Dict with user info and token on success
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Check if username exists
            cursor.execute("SELECT user_id FROM users WHERE username = ?", (username,))
            if cursor.fetchone():
                return {"success": False, "error": "Username already exists"}
            
            # Check if email exists (if provided)
            if email:
                cursor.execute("SELECT user_id FROM users WHERE email = ?", (email,))
                if cursor.fetchone():
                    return {"success": False, "error": "Email already registered"}
            
            # Create user
            user_id = self._generate_user_id()
            password_hash, salt = self._hash_password(password)
            now = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT INTO users (user_id, username, email, password_hash, salt, player_name, created_at, last_login, auth_source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                username,
                email,
                password_hash,
                salt,
                player_name or username,
                now,
                now,
                auth_source
            ))
            
            conn.commit()
            
            # Generate token
            token = self._generate_token(user_id, username)
            
            return {
                "success": True,
                "user_id": user_id,
                "username": username,
                "player_name": player_name or username,
                "token": token,
                "auth_source": auth_source
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            conn.close()
    
    def login(self, username: str, password: str) -> Dict:
        """
        Authenticate user and return token.
        
        Args:
            username: Username or email
            password: Password
        
        Returns:
            Dict with user info and token on success
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Find user by username or email
            cursor.execute("""
                SELECT user_id, username, email, password_hash, salt, player_name, is_active, auth_source
                FROM users 
                WHERE username = ? OR email = ?
            """, (username, username))
            
            row = cursor.fetchone()
            
            if not row:
                return {"success": False, "error": "Invalid username or password"}
            
            user_id, db_username, email, password_hash, salt, player_name, is_active, auth_source = row
            
            if not is_active:
                return {"success": False, "error": "Account is deactivated"}
            
            # Verify password
            check_hash, _ = self._hash_password(password, salt)
            
            if check_hash != password_hash:
                return {"success": False, "error": "Invalid username or password"}
            
            # Update last login
            cursor.execute(
                "UPDATE users SET last_login = ? WHERE user_id = ?",
                (datetime.now().isoformat(), user_id)
            )
            conn.commit()
            
            # Generate token
            token = self._generate_token(user_id, db_username)
            
            return {
                "success": True,
                "user_id": user_id,
                "username": db_username,
                "email": email,
                "player_name": player_name,
                "token": token,
                "auth_source": auth_source
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            conn.close()
    
    def _generate_token(self, user_id: str, username: str) -> str:
        """Generate JWT token for user"""
        payload = {
            "user_id": user_id,
            "username": username,
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
        }
        return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    
    def verify_token(self, token: str) -> Dict:
        """
        Verify JWT token and return user info.
        
        Returns:
            Dict with user info if valid, error if invalid
        """
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            
            # Check if user still exists and is active
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT user_id, username, player_name, is_active FROM users WHERE user_id = ?",
                (payload["user_id"],)
            )
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return {"valid": False, "error": "User not found"}
            
            if not row[3]:  # is_active
                return {"valid": False, "error": "Account deactivated"}
            
            return {
                "valid": True,
                "user_id": row[0],
                "username": row[1],
                "player_name": row[2]
            }
            
        except jwt.ExpiredSignatureError:
            return {"valid": False, "error": "Token expired"}
        except jwt.InvalidTokenError as e:
            return {"valid": False, "error": f"Invalid token: {str(e)}"}
    
    def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT user_id, username, email, player_name, created_at, last_login, is_active, auth_source
            FROM users WHERE user_id = ?
        """, (user_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return User(
                user_id=row[0],
                username=row[1],
                email=row[2],
                player_name=row[3],
                created_at=row[4],
                last_login=row[5],
                is_active=bool(row[6]),
                auth_source=row[7]
            )
        return None
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT user_id, username, email, player_name, created_at, last_login, is_active, auth_source
            FROM users WHERE username = ?
        """, (username,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return User(
                user_id=row[0],
                username=row[1],
                email=row[2],
                player_name=row[3],
                created_at=row[4],
                last_login=row[5],
                is_active=bool(row[6]),
                auth_source=row[7]
            )
        return None
    
    def update_player_name(self, user_id: str, new_player_name: str) -> bool:
        """Update user's player name"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "UPDATE users SET player_name = ? WHERE user_id = ?",
                (new_player_name, user_id)
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()
    
    def change_password(self, user_id: str, old_password: str, new_password: str) -> Dict:
        """Change user password"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Get current password info
            cursor.execute(
                "SELECT password_hash, salt FROM users WHERE user_id = ?",
                (user_id,)
            )
            row = cursor.fetchone()
            
            if not row:
                return {"success": False, "error": "User not found"}
            
            # Verify old password
            old_hash, old_salt = row
            check_hash, _ = self._hash_password(old_password, old_salt)
            
            if check_hash != old_hash:
                return {"success": False, "error": "Current password is incorrect"}
            
            # Set new password
            new_hash, new_salt = self._hash_password(new_password)
            
            cursor.execute(
                "UPDATE users SET password_hash = ?, salt = ? WHERE user_id = ?",
                (new_hash, new_salt, user_id)
            )
            conn.commit()
            
            return {"success": True, "message": "Password changed successfully"}
            
        finally:
            conn.close()
    
    def deactivate_user(self, user_id: str) -> bool:
        """Deactivate user account"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "UPDATE users SET is_active = 0 WHERE user_id = ?",
                (user_id,)
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()
    
    # ========================================================================
    # Unreal Engine Integration
    # ========================================================================
    
    def create_or_get_unreal_user(
        self,
        unreal_player_id: str,
        player_name: str = None,
        password: str = None
    ) -> Dict:
        """
        Create or retrieve a user account from Unreal Engine.
        Used when Unreal Engine sends a player ID.
        
        If the user doesn't exist, creates one with the Unreal ID as username.
        If password is not provided, generates a random one.
        
        Args:
            unreal_player_id: Player ID from Unreal Engine
            player_name: Display name (optional)
            password: Password (optional, will be generated if not provided)
        
        Returns:
            Dict with user info and token
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Check if user exists (using unreal ID as username)
            cursor.execute(
                "SELECT user_id, username, player_name FROM users WHERE username = ?",
                (unreal_player_id,)
            )
            row = cursor.fetchone()
            
            if row:
                # User exists, generate token
                user_id, username, db_player_name = row
                
                # Update last login
                cursor.execute(
                    "UPDATE users SET last_login = ? WHERE user_id = ?",
                    (datetime.now().isoformat(), user_id)
                )
                conn.commit()
                
                token = self._generate_token(user_id, username)
                
                return {
                    "success": True,
                    "is_new": False,
                    "user_id": user_id,
                    "username": username,
                    "player_name": db_player_name,
                    "token": token
                }
            
            # User doesn't exist, create new account
            generated_password = password or secrets.token_urlsafe(16)
            
            result = self.register(
                username=unreal_player_id,
                password=generated_password,
                player_name=player_name or f"Player_{unreal_player_id[:8]}",
                auth_source="unreal"
            )
            
            if result["success"]:
                result["is_new"] = True
                # Include generated password for Unreal to store if needed
                if not password:
                    result["generated_password"] = generated_password
            
            return result
            
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            conn.close()
    
    def validate_unreal_credentials(
        self,
        unreal_player_id: str,
        password: str
    ) -> Dict:
        """
        Validate credentials from Unreal Engine.
        Used for returning players who already have accounts.
        
        Args:
            unreal_player_id: Player ID from Unreal Engine (used as username)
            password: Password
        
        Returns:
            Dict with user info and token if valid
        """
        return self.login(unreal_player_id, password)
    
    # ========================================================================
    # API Key Management (for server-to-server auth)
    # ========================================================================
    
    def generate_api_key(self, user_id: str, description: str = None, expires_days: int = None) -> Dict:
        """Generate API key for a user (for Unreal Engine server auth)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Verify user exists
            cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
            if not cursor.fetchone():
                return {"success": False, "error": "User not found"}
            
            key_id = f"key_{secrets.token_hex(8)}"
            api_key = f"fsnpc_{secrets.token_urlsafe(32)}"
            now = datetime.now()
            expires_at = None
            if expires_days:
                expires_at = (now + timedelta(days=expires_days)).isoformat()
            
            cursor.execute("""
                INSERT INTO api_keys (key_id, user_id, api_key, created_at, expires_at, description)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (key_id, user_id, api_key, now.isoformat(), expires_at, description))
            
            conn.commit()
            
            return {
                "success": True,
                "key_id": key_id,
                "api_key": api_key,
                "expires_at": expires_at
            }
            
        finally:
            conn.close()
    
    def validate_api_key(self, api_key: str) -> Dict:
        """Validate API key and return associated user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT k.user_id, k.expires_at, k.is_active, u.username, u.player_name
                FROM api_keys k
                JOIN users u ON k.user_id = u.user_id
                WHERE k.api_key = ?
            """, (api_key,))
            
            row = cursor.fetchone()
            
            if not row:
                return {"valid": False, "error": "Invalid API key"}
            
            user_id, expires_at, is_active, username, player_name = row
            
            if not is_active:
                return {"valid": False, "error": "API key is deactivated"}
            
            if expires_at:
                if datetime.fromisoformat(expires_at) < datetime.now():
                    return {"valid": False, "error": "API key has expired"}
            
            return {
                "valid": True,
                "user_id": user_id,
                "username": username,
                "player_name": player_name
            }
            
        finally:
            conn.close()
    
    def revoke_api_key(self, key_id: str) -> bool:
        """Revoke an API key"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "UPDATE api_keys SET is_active = 0 WHERE key_id = ?",
                (key_id,)
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()
    
    def list_users(self, limit: int = 100, offset: int = 0) -> Dict:
        """List all users (admin function)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT COUNT(*) FROM users")
            total = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT user_id, username, email, player_name, created_at, last_login, is_active, auth_source
                FROM users
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """, (limit, offset))
            
            users = []
            for row in cursor.fetchall():
                users.append({
                    "user_id": row[0],
                    "username": row[1],
                    "email": row[2],
                    "player_name": row[3],
                    "created_at": row[4],
                    "last_login": row[5],
                    "is_active": bool(row[6]),
                    "auth_source": row[7]
                })
            
            return {
                "total": total,
                "users": users,
                "limit": limit,
                "offset": offset
            }
            
        finally:
            conn.close()


# ============================================================================
# Global Instance
# ============================================================================

auth_system = AuthSystem()
