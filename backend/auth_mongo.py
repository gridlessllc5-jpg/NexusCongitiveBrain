"""
Authentication System for Fractured Survival - MongoDB Version
Handles user registration, login, and session management
Works with both web frontend and Unreal Engine clients
"""
import hashlib
import secrets
import os
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Tuple
from dataclasses import dataclass
import jwt
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

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


class AuthSystemMongo:
    """
    MongoDB-based authentication system for deployment.
    Handles user authentication for the NPC system.
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.users = db.users
        self.api_keys = db.api_keys
        self.sessions = db.sessions
    
    async def initialize(self):
        """Create indexes for collections and fix any data issues"""
        # Fix existing documents with email: null (sparse index requires field to be absent)
        await self.users.update_many(
            {"email": None},
            {"$unset": {"email": ""}}
        )
        
        # Drop and recreate email index to ensure it's sparse
        try:
            await self.users.drop_index("email_1")
        except Exception:
            pass  # Index might not exist
        
        # Create indexes
        await self.users.create_index("username", unique=True)
        await self.users.create_index("email", unique=True, sparse=True)
        await self.api_keys.create_index("api_key", unique=True)
        await self.api_keys.create_index("user_id")
    
    def _hash_password(self, password: str, salt: str = None) -> Tuple[str, str]:
        """Hash password with salt using SHA-256"""
        if salt is None:
            salt = secrets.token_hex(16)
        password_bytes = (password + salt).encode('utf-8')
        password_hash = hashlib.sha256(password_bytes).hexdigest()
        return password_hash, salt
    
    def _generate_user_id(self) -> str:
        """Generate unique user ID"""
        return f"user_{secrets.token_hex(8)}"
    
    async def register(
        self,
        username: str,
        password: str,
        email: str = None,
        player_name: str = None,
        auth_source: str = "web"
    ) -> Dict:
        """Register a new user account."""
        try:
            # Check if username exists
            existing = await self.users.find_one({"username": username})
            if existing:
                return {"success": False, "error": "Username already exists"}
            
            # Check if email exists
            if email:
                existing_email = await self.users.find_one({"email": email})
                if existing_email:
                    return {"success": False, "error": "Email already registered"}
            
            # Create user
            user_id = self._generate_user_id()
            password_hash, salt = self._hash_password(password)
            now = datetime.now(timezone.utc).isoformat()
            
            user_doc = {
                "user_id": user_id,
                "username": username,
                "password_hash": password_hash,
                "salt": salt,
                "player_name": player_name or username,
                "created_at": now,
                "last_login": now,
                "is_active": True,
                "auth_source": auth_source
            }
            # Only add email if provided (sparse index requires field to be absent, not null)
            if email:
                user_doc["email"] = email
            
            await self.users.insert_one(user_doc)
            
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
    
    async def login(self, username: str, password: str) -> Dict:
        """Authenticate user and return token."""
        try:
            # Find user by username or email
            user = await self.users.find_one({
                "$or": [{"username": username}, {"email": username}]
            })
            
            if not user:
                return {"success": False, "error": "Invalid username or password"}
            
            if not user.get("is_active", True):
                return {"success": False, "error": "Account is deactivated"}
            
            # Verify password
            check_hash, _ = self._hash_password(password, user["salt"])
            
            if check_hash != user["password_hash"]:
                return {"success": False, "error": "Invalid username or password"}
            
            # Update last login
            await self.users.update_one(
                {"user_id": user["user_id"]},
                {"$set": {"last_login": datetime.now(timezone.utc).isoformat()}}
            )
            
            # Generate token
            token = self._generate_token(user["user_id"], user["username"])
            
            return {
                "success": True,
                "user_id": user["user_id"],
                "username": user["username"],
                "email": user.get("email"),
                "player_name": user["player_name"],
                "token": token,
                "auth_source": user.get("auth_source", "web")
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
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
        """Verify JWT token and return user info."""
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            return {
                "valid": True,
                "user_id": payload["user_id"],
                "username": payload["username"]
            }
        except jwt.ExpiredSignatureError:
            return {"valid": False, "error": "Token expired"}
        except jwt.InvalidTokenError as e:
            return {"valid": False, "error": f"Invalid token: {str(e)}"}
    
    async def get_user(self, user_id: str) -> Optional[Dict]:
        """Get user by ID"""
        user = await self.users.find_one({"user_id": user_id}, {"password_hash": 0, "salt": 0, "_id": 0})
        return user
    
    async def update_player_name(self, user_id: str, new_player_name: str) -> bool:
        """Update user's player name"""
        result = await self.users.update_one(
            {"user_id": user_id},
            {"$set": {"player_name": new_player_name}}
        )
        return result.modified_count > 0
    
    async def change_password(self, user_id: str, old_password: str, new_password: str) -> Dict:
        """Change user password"""
        try:
            user = await self.users.find_one({"user_id": user_id})
            if not user:
                return {"success": False, "error": "User not found"}
            
            # Verify old password
            check_hash, _ = self._hash_password(old_password, user["salt"])
            if check_hash != user["password_hash"]:
                return {"success": False, "error": "Current password is incorrect"}
            
            # Set new password
            new_hash, new_salt = self._hash_password(new_password)
            await self.users.update_one(
                {"user_id": user_id},
                {"$set": {"password_hash": new_hash, "salt": new_salt}}
            )
            
            return {"success": True, "message": "Password changed successfully"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def create_or_get_unreal_user(
        self,
        unreal_player_id: str,
        player_name: str = None,
        password: str = None
    ) -> Dict:
        """Create or retrieve a user account from Unreal Engine."""
        try:
            # Check if user exists
            user = await self.users.find_one({"username": unreal_player_id})
            
            if user:
                # User exists, generate token
                await self.users.update_one(
                    {"user_id": user["user_id"]},
                    {"$set": {"last_login": datetime.now(timezone.utc).isoformat()}}
                )
                token = self._generate_token(user["user_id"], user["username"])
                return {
                    "success": True,
                    "is_new": False,
                    "user_id": user["user_id"],
                    "username": user["username"],
                    "player_name": user["player_name"],
                    "token": token
                }
            
            # Create new user
            generated_password = password or secrets.token_urlsafe(16)
            result = await self.register(
                username=unreal_player_id,
                password=generated_password,
                player_name=player_name or f"Player_{unreal_player_id[:8]}",
                auth_source="unreal"
            )
            
            if result["success"]:
                result["is_new"] = True
                if not password:
                    result["generated_password"] = generated_password
            
            return result
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def generate_api_key(self, user_id: str, description: str = None, expires_days: int = None) -> Dict:
        """Generate API key for a user"""
        try:
            user = await self.users.find_one({"user_id": user_id})
            if not user:
                return {"success": False, "error": "User not found"}
            
            key_id = f"key_{secrets.token_hex(8)}"
            api_key = f"fsnpc_{secrets.token_urlsafe(32)}"
            now = datetime.now(timezone.utc)
            expires_at = None
            if expires_days:
                expires_at = (now + timedelta(days=expires_days)).isoformat()
            
            key_doc = {
                "key_id": key_id,
                "user_id": user_id,
                "api_key": api_key,
                "created_at": now.isoformat(),
                "expires_at": expires_at,
                "is_active": True,
                "description": description
            }
            
            await self.api_keys.insert_one(key_doc)
            
            return {
                "success": True,
                "key_id": key_id,
                "api_key": api_key,
                "expires_at": expires_at
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def validate_api_key(self, api_key: str) -> Dict:
        """Validate API key and return associated user"""
        try:
            key_doc = await self.api_keys.find_one({"api_key": api_key})
            if not key_doc:
                return {"valid": False, "error": "Invalid API key"}
            
            if not key_doc.get("is_active", True):
                return {"valid": False, "error": "API key is deactivated"}
            
            if key_doc.get("expires_at"):
                if datetime.fromisoformat(key_doc["expires_at"]) < datetime.now(timezone.utc):
                    return {"valid": False, "error": "API key has expired"}
            
            user = await self.users.find_one({"user_id": key_doc["user_id"]})
            if not user:
                return {"valid": False, "error": "User not found"}
            
            return {
                "valid": True,
                "user_id": user["user_id"],
                "username": user["username"],
                "player_name": user["player_name"]
            }
        except Exception as e:
            return {"valid": False, "error": str(e)}
    
    async def list_users(self, limit: int = 100, offset: int = 0) -> Dict:
        """List all users"""
        try:
            total = await self.users.count_documents({})
            cursor = self.users.find(
                {},
                {"password_hash": 0, "salt": 0, "_id": 0}
            ).sort("created_at", -1).skip(offset).limit(limit)
            
            users = await cursor.to_list(length=limit)
            
            return {
                "total": total,
                "users": users,
                "limit": limit,
                "offset": offset
            }
        except Exception as e:
            return {"total": 0, "users": [], "error": str(e)}
