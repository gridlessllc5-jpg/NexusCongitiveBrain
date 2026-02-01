"""
Path Configuration for NPC System
Handles database paths for both local development and container deployment
"""
import os
from pathlib import Path

def get_base_path() -> Path:
    """Get the base path for the NPC system"""
    # Check if we're in a container (Emergent/Docker)
    if os.path.exists("/app/npc_system"):
        return Path("/app/npc_system")
    
    # Local development - use the directory where this file is located
    return Path(__file__).parent.parent

def get_database_path() -> Path:
    """Get the database directory path"""
    db_path = get_base_path() / "database"
    db_path.mkdir(parents=True, exist_ok=True)
    return db_path

def get_memory_vault_db() -> str:
    """Get the memory vault database path"""
    return str(get_database_path() / "memory_vault.db")

def get_auth_db() -> str:
    """Get the auth database path"""
    return str(get_database_path() / "auth.db")

def get_voice_db() -> str:
    """Get the voice assignments database path"""
    return str(get_database_path() / "voice_assignments.db")

# Export commonly used paths
BASE_PATH = get_base_path()
DATABASE_PATH = get_database_path()
MEMORY_VAULT_DB = get_memory_vault_db()
AUTH_DB = get_auth_db()
VOICE_DB = get_voice_db()

print(f"✓ NPC System paths configured: {DATABASE_PATH}")
