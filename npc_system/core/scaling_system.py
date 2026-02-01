"""
Phase 5: Global Scaling - Performance Optimization System
Handles 100+ NPCs efficiently with caching, batching, and connection pooling
"""
import sqlite3
import threading
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from contextlib import contextmanager
from collections import OrderedDict
import asyncio
import random

# Import path configuration for database locations
try:
    from core.paths import MEMORY_VAULT_DB
except ImportError:
    try:
        from paths import MEMORY_VAULT_DB
    except ImportError:
        MEMORY_VAULT_DB = "/app/npc_system/database/memory_vault.db"

# ============================================================================
# Connection Pool for SQLite
# ============================================================================

class ConnectionPool:
    """Thread-safe connection pool for SQLite"""
    
    def __init__(self, db_path: str, pool_size: int = 10):
        self.db_path = db_path
        self.pool_size = pool_size
        self._pool: List[sqlite3.Connection] = []
        self._lock = threading.Lock()
        self._in_use: Dict[int, sqlite3.Connection] = {}
        
        # Pre-create connections
        for _ in range(pool_size):
            conn = self._create_connection()
            self._pool.append(conn)
        
        print(f"✓ Connection pool initialized with {pool_size} connections")
    
    def _create_connection(self) -> sqlite3.Connection:
        """Create optimized SQLite connection"""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging for concurrency
        conn.execute("PRAGMA synchronous=NORMAL")  # Faster writes
        conn.execute("PRAGMA cache_size=-64000")  # 64MB cache
        conn.execute("PRAGMA temp_store=MEMORY")  # Temp tables in memory
        conn.row_factory = sqlite3.Row
        return conn
    
    @contextmanager
    def get_connection(self):
        """Get a connection from the pool"""
        conn = None
        thread_id = threading.get_ident()
        
        with self._lock:
            # Check if this thread already has a connection
            if thread_id in self._in_use:
                conn = self._in_use[thread_id]
            elif self._pool:
                conn = self._pool.pop()
                self._in_use[thread_id] = conn
            else:
                # Pool exhausted, create new connection
                conn = self._create_connection()
                self._in_use[thread_id] = conn
        
        try:
            yield conn
        finally:
            with self._lock:
                if thread_id in self._in_use:
                    returned_conn = self._in_use.pop(thread_id)
                    if len(self._pool) < self.pool_size:
                        self._pool.append(returned_conn)
                    else:
                        returned_conn.close()
    
    def close_all(self):
        """Close all connections"""
        with self._lock:
            for conn in self._pool:
                conn.close()
            for conn in self._in_use.values():
                conn.close()
            self._pool.clear()
            self._in_use.clear()


# ============================================================================
# LRU Cache with TTL
# ============================================================================

class TTLCache:
    """Thread-safe LRU cache with time-to-live expiration"""
    
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 300):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: OrderedDict = OrderedDict()
        self._timestamps: Dict[str, float] = {}
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        with self._lock:
            if key in self._cache:
                # Check TTL
                if time.time() - self._timestamps[key] < self.ttl_seconds:
                    # Move to end (most recently used)
                    self._cache.move_to_end(key)
                    self._hits += 1
                    return self._cache[key]
                else:
                    # Expired
                    del self._cache[key]
                    del self._timestamps[key]
            
            self._misses += 1
            return None
    
    def set(self, key: str, value: Any):
        """Set value in cache"""
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            else:
                if len(self._cache) >= self.max_size:
                    # Remove oldest item
                    oldest_key = next(iter(self._cache))
                    del self._cache[oldest_key]
                    del self._timestamps[oldest_key]
            
            self._cache[key] = value
            self._timestamps[key] = time.time()
    
    def invalidate(self, key: str):
        """Remove key from cache"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                del self._timestamps[key]
    
    def invalidate_prefix(self, prefix: str):
        """Remove all keys with given prefix"""
        with self._lock:
            keys_to_remove = [k for k in self._cache.keys() if k.startswith(prefix)]
            for key in keys_to_remove:
                del self._cache[key]
                del self._timestamps[key]
    
    def clear(self):
        """Clear entire cache"""
        with self._lock:
            self._cache.clear()
            self._timestamps.clear()
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": f"{hit_rate:.1f}%"
        }


# ============================================================================
# Tiered NPC Update System
# ============================================================================

@dataclass
class NPCActivityState:
    """Tracks NPC activity for tiered updates"""
    npc_id: str
    last_interaction: float = 0.0  # timestamp
    last_update: float = 0.0
    interaction_count_recent: int = 0  # last hour
    zone: str = "default"
    tier: str = "idle"  # active, nearby, idle, dormant


class TieredUpdateSystem:
    """
    Tiered update system for efficient NPC processing
    
    Tiers:
    - ACTIVE: Player is currently interacting (update every tick)
    - NEARBY: Player was here recently (update every 5 ticks)
    - IDLE: No recent activity (update every 20 ticks)
    - DORMANT: Long inactive (update every 100 ticks)
    """
    
    TIER_ACTIVE = "active"
    TIER_NEARBY = "nearby"
    TIER_IDLE = "idle"
    TIER_DORMANT = "dormant"
    
    # Update frequencies (in ticks)
    TIER_FREQUENCIES = {
        TIER_ACTIVE: 1,
        TIER_NEARBY: 5,
        TIER_IDLE: 20,
        TIER_DORMANT: 100
    }
    
    # Time thresholds (in seconds) for tier demotion
    TIER_THRESHOLDS = {
        TIER_ACTIVE: 60,      # Active for 1 minute after interaction
        TIER_NEARBY: 300,     # Nearby for 5 minutes
        TIER_IDLE: 3600,      # Idle for 1 hour
    }
    
    def __init__(self):
        self._npc_states: Dict[str, NPCActivityState] = {}
        self._lock = threading.Lock()
        self._current_tick = 0
        self._zones: Dict[str, List[str]] = {}  # zone -> list of npc_ids
    
    def register_npc(self, npc_id: str, zone: str = "default"):
        """Register an NPC in the system"""
        with self._lock:
            self._npc_states[npc_id] = NPCActivityState(
                npc_id=npc_id,
                last_update=time.time(),
                zone=zone,
                tier=self.TIER_IDLE
            )
            
            if zone not in self._zones:
                self._zones[zone] = []
            if npc_id not in self._zones[zone]:
                self._zones[zone].append(npc_id)
    
    def record_interaction(self, npc_id: str):
        """Record that an NPC was interacted with"""
        with self._lock:
            if npc_id in self._npc_states:
                state = self._npc_states[npc_id]
                state.last_interaction = time.time()
                state.interaction_count_recent += 1
                state.tier = self.TIER_ACTIVE
    
    def update_tiers(self):
        """Update all NPC tiers based on activity"""
        current_time = time.time()
        
        with self._lock:
            for npc_id, state in self._npc_states.items():
                time_since_interaction = current_time - state.last_interaction
                
                if time_since_interaction < self.TIER_THRESHOLDS[self.TIER_ACTIVE]:
                    state.tier = self.TIER_ACTIVE
                elif time_since_interaction < self.TIER_THRESHOLDS[self.TIER_NEARBY]:
                    state.tier = self.TIER_NEARBY
                elif time_since_interaction < self.TIER_THRESHOLDS[self.TIER_IDLE]:
                    state.tier = self.TIER_IDLE
                else:
                    state.tier = self.TIER_DORMANT
    
    def get_npcs_to_update(self) -> List[str]:
        """Get list of NPCs that should be updated this tick"""
        self._current_tick += 1
        npcs_to_update = []
        
        with self._lock:
            for npc_id, state in self._npc_states.items():
                frequency = self.TIER_FREQUENCIES[state.tier]
                if self._current_tick % frequency == 0:
                    npcs_to_update.append(npc_id)
                    state.last_update = time.time()
        
        return npcs_to_update
    
    def get_npcs_in_zone(self, zone: str) -> List[str]:
        """Get all NPCs in a specific zone"""
        with self._lock:
            return self._zones.get(zone, []).copy()
    
    def get_active_npcs(self) -> List[str]:
        """Get all NPCs in ACTIVE or NEARBY tier"""
        with self._lock:
            return [
                npc_id for npc_id, state in self._npc_states.items()
                if state.tier in (self.TIER_ACTIVE, self.TIER_NEARBY)
            ]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get system statistics"""
        with self._lock:
            tier_counts = {tier: 0 for tier in self.TIER_FREQUENCIES.keys()}
            for state in self._npc_states.values():
                tier_counts[state.tier] += 1
            
            return {
                "total_npcs": len(self._npc_states),
                "tier_distribution": tier_counts,
                "zones": len(self._zones),
                "current_tick": self._current_tick
            }


# ============================================================================
# Batch Operations Manager
# ============================================================================

class BatchOperationsManager:
    """Handles batch database operations for efficiency"""
    
    def __init__(self, connection_pool: ConnectionPool):
        self.pool = connection_pool
        self._pending_writes: List[Tuple[str, tuple]] = []
        self._lock = threading.Lock()
        self._batch_size = 100
    
    def queue_write(self, sql: str, params: tuple):
        """Queue a write operation for batch execution"""
        with self._lock:
            self._pending_writes.append((sql, params))
            
            if len(self._pending_writes) >= self._batch_size:
                self._flush_writes()
    
    def _flush_writes(self):
        """Execute all pending writes in a single transaction"""
        if not self._pending_writes:
            return
        
        writes = self._pending_writes.copy()
        self._pending_writes.clear()
        
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            try:
                for sql, params in writes:
                    cursor.execute(sql, params)
                conn.commit()
            except Exception as e:
                conn.rollback()
                print(f"Batch write error: {e}")
                raise
    
    def flush(self):
        """Force flush pending writes"""
        with self._lock:
            self._flush_writes()
    
    def batch_memory_decay(self, decay_rate: float, min_strength: float = 0.1) -> int:
        """Apply memory decay to all memories in a single batch operation"""
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            
            # Update all memories in single query (use conversation_topics table)
            try:
                cursor.execute("""
                    UPDATE conversation_topics 
                    SET current_strength = MAX(?, current_strength * (1 - ? * decay_rate))
                    WHERE current_strength > ?
                """, (min_strength, decay_rate, min_strength))
                
                affected = cursor.rowcount
                conn.commit()
                return affected
            except Exception:
                # Table might not exist or have different schema
                return 0
    
    def batch_cleanup_memories(self, threshold: float = 0.1) -> int:
        """Remove all memories below threshold in single operation"""
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute(
                    "DELETE FROM conversation_topics WHERE current_strength < ?",
                    (threshold,)
                )
                
                deleted = cursor.rowcount
                conn.commit()
                return deleted
            except Exception:
                # Table might not exist or have different schema
                return 0
    
    def batch_insert_memories(self, memories: List[Dict]) -> int:
        """Insert multiple memories in a batch"""
        if not memories:
            return 0
        
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                cursor.executemany("""
                    INSERT OR REPLACE INTO conversation_topics 
                    (id, player_id, npc_id, topic_category, content, emotional_weight, 
                     timestamp, last_accessed, decay_rate, current_strength)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, [
                    (m['id'], m['player_id'], m['npc_id'], m['topic_category'], 
                     m['content'], m['emotional_weight'], m['timestamp'],
                     m['last_accessed'], m['decay_rate'], m['current_strength'])
                    for m in memories
                ])
                
                conn.commit()
                return len(memories)
            except Exception:
                return 0
    
    def batch_get_npc_data(self, npc_ids: List[str]) -> Dict[str, Dict]:
        """Get data for multiple NPCs in single query"""
        if not npc_ids:
            return {}
        
        placeholders = ','.join(['?' for _ in npc_ids])
        
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get memories from conversation_topics table
            memory_stats = {}
            try:
                cursor.execute(f"""
                    SELECT npc_id, COUNT(*) as memory_count, 
                           AVG(current_strength) as avg_strength
                    FROM conversation_topics 
                    WHERE npc_id IN ({placeholders})
                    GROUP BY npc_id
                """, npc_ids)
                memory_stats = {row['npc_id']: dict(row) for row in cursor.fetchall()}
            except Exception:
                # Table might not exist or have different schema
                pass
            
            # Get relationship counts
            relationship_stats = {}
            try:
                cursor.execute(f"""
                    SELECT npc1_id as npc_id, COUNT(*) as relationship_count
                    FROM npc_relationships 
                    WHERE npc1_id IN ({placeholders})
                    GROUP BY npc1_id
                """, npc_ids)
                relationship_stats = {row['npc_id']: dict(row) for row in cursor.fetchall()}
            except Exception:
                pass
            
            # Combine results
            result = {}
            for npc_id in npc_ids:
                result[npc_id] = {
                    "npc_id": npc_id,
                    "memory_stats": memory_stats.get(npc_id, {}),
                    "relationship_stats": relationship_stats.get(npc_id, {})
                }
            
            return result


# ============================================================================
# Database Index Manager
# ============================================================================

class IndexManager:
    """Manages database indexes for performance"""
    
    INDEXES = [
        # Memory tables (conversation_topics is the actual table name)
        ("idx_conversation_topics_npc", "conversation_topics", "npc_id"),
        ("idx_conversation_topics_player", "conversation_topics", "player_id"),
        ("idx_conversation_topics_strength", "conversation_topics", "current_strength"),
        ("idx_conversation_topics_npc_player", "conversation_topics", "npc_id, player_id"),
        
        # Shared memories
        ("idx_shared_memories_target", "shared_memories", "target_npc_id"),
        ("idx_shared_memories_source", "shared_memories", "source_npc_id"),
        
        # Relationships
        ("idx_npc_relationships_npc1", "npc_relationships", "npc1_id"),
        ("idx_npc_relationships_npc2", "npc_relationships", "npc2_id"),
        
        # Player data
        ("idx_player_npc_reputation_player", "player_npc_reputation", "player_id"),
        ("idx_player_npc_reputation_npc", "player_npc_reputation", "npc_id"),
        ("idx_player_actions_player", "player_actions", "player_id"),
        ("idx_player_actions_timestamp", "player_actions", "timestamp"),
        
        # Rumors
        ("idx_rumors_player", "rumors", "about_player"),
        ("idx_npc_heard_rumors_npc", "npc_heard_rumors", "npc_id"),
        
        # Quests
        ("idx_quests_status", "quests", "status"),
        ("idx_quests_npc", "quests", "npc_id"),
        
        # Goals
        ("idx_npc_goals_npc", "npc_goals", "npc_id"),
        ("idx_npc_goals_status", "npc_goals", "status"),
        
        # Trade routes
        ("idx_trade_routes_status", "trade_routes", "status"),
        
        # Battles (territorial_battles is the actual table name)
        ("idx_battles_territory", "territorial_battles", "territory"),
        ("idx_battles_status", "territorial_battles", "status"),
    ]
    
    @classmethod
    def create_indexes(cls, connection_pool: ConnectionPool):
        """Create all performance indexes"""
        created = 0
        skipped = 0
        
        with connection_pool.get_connection() as conn:
            cursor = conn.cursor()
            
            for index_name, table, columns in cls.INDEXES:
                try:
                    cursor.execute(f"""
                        CREATE INDEX IF NOT EXISTS {index_name} 
                        ON {table} ({columns})
                    """)
                    created += 1
                except sqlite3.OperationalError as e:
                    # Table might not exist yet
                    skipped += 1
            
            conn.commit()
        
        print(f"✓ Indexes: {created} created, {skipped} skipped")
        return created, skipped
    
    @classmethod
    def analyze_tables(cls, connection_pool: ConnectionPool):
        """Run ANALYZE to update query planner statistics"""
        with connection_pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("ANALYZE")
            conn.commit()
        
        print("✓ Table statistics updated")


# ============================================================================
# Performance Monitor
# ============================================================================

class PerformanceMonitor:
    """Monitors system performance metrics"""
    
    def __init__(self):
        self._metrics: Dict[str, List[float]] = {}
        self._lock = threading.Lock()
        self._max_samples = 1000
    
    def record(self, metric_name: str, value: float):
        """Record a metric value"""
        with self._lock:
            if metric_name not in self._metrics:
                self._metrics[metric_name] = []
            
            self._metrics[metric_name].append(value)
            
            # Keep only recent samples
            if len(self._metrics[metric_name]) > self._max_samples:
                self._metrics[metric_name] = self._metrics[metric_name][-self._max_samples:]
    
    @contextmanager
    def measure(self, metric_name: str):
        """Context manager to measure execution time"""
        start = time.time()
        try:
            yield
        finally:
            duration = time.time() - start
            self.record(metric_name, duration)
    
    def get_stats(self, metric_name: str) -> Dict[str, float]:
        """Get statistics for a metric"""
        with self._lock:
            values = self._metrics.get(metric_name, [])
            
            if not values:
                return {"count": 0}
            
            sorted_values = sorted(values)
            n = len(values)
            
            return {
                "count": n,
                "avg": sum(values) / n,
                "min": min(values),
                "max": max(values),
                "p50": sorted_values[n // 2],
                "p95": sorted_values[int(n * 0.95)] if n > 20 else sorted_values[-1],
                "p99": sorted_values[int(n * 0.99)] if n > 100 else sorted_values[-1]
            }
    
    def get_all_stats(self) -> Dict[str, Dict[str, float]]:
        """Get statistics for all metrics"""
        with self._lock:
            return {name: self.get_stats(name) for name in self._metrics.keys()}


# ============================================================================
# Global Scaling Manager (Main Interface)
# ============================================================================

class GlobalScalingManager:
    """
    Main interface for the scaling system
    Coordinates all optimization components
    """
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or MEMORY_VAULT_DB
        
        # Initialize components
        self.connection_pool = ConnectionPool(self.db_path, pool_size=10)
        self.cache = TTLCache(max_size=5000, ttl_seconds=300)
        self.tiered_updates = TieredUpdateSystem()
        self.batch_ops = BatchOperationsManager(self.connection_pool)
        self.performance = PerformanceMonitor()
        
        # Create indexes
        IndexManager.create_indexes(self.connection_pool)
        
        print("✓ Global Scaling Manager initialized")
    
    def register_npc(self, npc_id: str, zone: str = "default"):
        """Register an NPC for tiered updates"""
        self.tiered_updates.register_npc(npc_id, zone)
    
    def record_interaction(self, npc_id: str):
        """Record an NPC interaction (promotes to active tier)"""
        self.tiered_updates.record_interaction(npc_id)
        self.cache.invalidate_prefix(f"npc:{npc_id}")
    
    def get_cached_or_fetch(self, key: str, fetch_fn, ttl: int = None) -> Any:
        """Get from cache or fetch using provided function"""
        cached = self.cache.get(key)
        if cached is not None:
            return cached
        
        with self.performance.measure(f"fetch:{key.split(':')[0]}"):
            result = fetch_fn()
        
        self.cache.set(key, result)
        return result
    
    def process_world_tick(self) -> Dict[str, Any]:
        """Process a world tick with optimized batching"""
        with self.performance.measure("world_tick"):
            # Update tiers
            self.tiered_updates.update_tiers()
            
            # Get NPCs to update this tick
            npcs_to_update = self.tiered_updates.get_npcs_to_update()
            
            # Batch memory decay
            decayed = self.batch_ops.batch_memory_decay(0.01)
            
            # Flush any pending writes
            self.batch_ops.flush()
            
            return {
                "npcs_updated": len(npcs_to_update),
                "memories_decayed": decayed,
                "tier_stats": self.tiered_updates.get_stats()
            }
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get comprehensive system statistics"""
        return {
            "cache": self.cache.stats(),
            "tiers": self.tiered_updates.get_stats(),
            "performance": self.performance.get_all_stats()
        }
    
    def cleanup(self):
        """Cleanup resources"""
        self.batch_ops.flush()
        self.connection_pool.close_all()


# ============================================================================
# Global Instance
# ============================================================================

# Create global scaling manager instance
scaling_manager = GlobalScalingManager()
