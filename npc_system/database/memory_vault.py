"""Memory Vault - Foundation (Step 1)"""
import sqlite3
import asyncio
from datetime import datetime
from typing import List
from dataclasses import dataclass
import threading
import math
import os
from pathlib import Path

# Get database path dynamically
def get_default_db_path():
    """Get the default database path based on environment"""
    if os.path.exists("/app/npc_system"):
        return "/app/npc_system/database/memory_vault.db"
    # Local development - use relative path
    db_dir = Path(__file__).parent
    db_dir.mkdir(parents=True, exist_ok=True)
    return str(db_dir / "memory_vault.db")

@dataclass
class Memory:
    id: str
    npc_id: str
    memory_type: str
    content: str
    strength: float
    timestamp: str

@dataclass
class TraitChange:
    trait_id: str
    npc_id: str
    delta: float
    reason: str
    timestamp: str
    current_value: float

class MemoryVault:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or get_default_db_path()
        self.write_queue = asyncio.Queue()
        self.lock = threading.Lock()
        self._initialize_db()
    
    def _initialize_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""CREATE TABLE IF NOT EXISTS memories (
            id TEXT PRIMARY KEY, npc_id TEXT, memory_type TEXT,
            content TEXT, strength REAL, timestamp TEXT)""")
        cursor.execute("""CREATE TABLE IF NOT EXISTS personality_evolution (
            id INTEGER PRIMARY KEY AUTOINCREMENT, npc_id TEXT, trait_id TEXT,
            current_value REAL, delta REAL, reason TEXT, timestamp TEXT)""")
        cursor.execute("""CREATE TABLE IF NOT EXISTS summary_beliefs (
            id INTEGER PRIMARY KEY AUTOINCREMENT, npc_id TEXT,
            belief TEXT, strength REAL, timestamp TEXT)""")
        conn.commit()
        conn.close()
        print("✓ Database initialized")
    
    def _sigmoid_clamp(self, value: float) -> float:
        x = (value - 0.5) * 10
        sigmoid = 1 / (1 + math.exp(-x))
        return 0.05 + 0.9 * sigmoid
    
    async def write_trait_change_async(self, trait_change: TraitChange):
        await self.write_queue.put(("trait", trait_change))
    
    async def process_write_queue(self):
        while True:
            try:
                item = await asyncio.wait_for(self.write_queue.get(), timeout=0.1)
                write_type, data = item
                if write_type == "trait":
                    self._write_trait_sync(data)
            except asyncio.TimeoutError:
                await asyncio.sleep(0.1)
    
    def _write_trait_sync(self, trait_change: TraitChange):
        with self.lock:
            clamped = self._sigmoid_clamp(trait_change.current_value)
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""INSERT INTO personality_evolution 
                (npc_id, trait_id, current_value, delta, reason, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (trait_change.npc_id, trait_change.trait_id, clamped,
                 trait_change.delta, trait_change.reason, trait_change.timestamp))
            conn.commit()
            conn.close()
            print(f"✓ Delta-Log: {trait_change.trait_id} {trait_change.delta:+.3f} → {clamped:.3f}")
    
    def save_memory(self, memory: Memory):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""INSERT OR REPLACE INTO memories 
            (id, npc_id, memory_type, content, strength, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)""",
            (memory.id, memory.npc_id, memory.memory_type, 
             memory.content, memory.strength, memory.timestamp))
        conn.commit()
        conn.close()
    
    def get_recent_memories(self, npc_id: str, limit: int = 5) -> List[Memory]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""SELECT id, npc_id, memory_type, content, strength, timestamp
            FROM memories WHERE npc_id = ? ORDER BY timestamp DESC LIMIT ?""", 
            (npc_id, limit))
        rows = cursor.fetchall()
        conn.close()
        return [Memory(*row) for row in rows]
    
    def get_summary_beliefs(self, npc_id: str, limit: int = 5) -> List[str]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""SELECT belief FROM summary_beliefs
            WHERE npc_id = ? ORDER BY strength DESC LIMIT ?""", (npc_id, limit))
        beliefs = [row[0] for row in cursor.fetchall()]
        conn.close()
        return beliefs
    
    def save_summary_belief(self, npc_id: str, belief: str, strength: float):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""INSERT INTO summary_beliefs (npc_id, belief, strength, timestamp)
            VALUES (?, ?, ?, ?)""", (npc_id, belief, strength, datetime.now().isoformat()))
        conn.commit()
        conn.close()
    
    def get_trait_history(self, npc_id: str, trait_id: str, limit: int = 10):
        """Get personality evolution history for a trait"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""SELECT current_value, delta, reason, timestamp
            FROM personality_evolution WHERE npc_id = ? AND trait_id = ?
            ORDER BY timestamp DESC LIMIT ?""", (npc_id, trait_id, limit))
        rows = cursor.fetchall()
        conn.close()
        return [{"current_value": row[0], "delta": row[1], "reason": row[2], "timestamp": row[3]} for row in rows]
