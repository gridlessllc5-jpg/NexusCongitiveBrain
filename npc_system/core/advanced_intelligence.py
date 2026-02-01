"""
Advanced NPC Intelligence & Multiplayer Social System
- Long-term memory persistence
- NPC-to-NPC relationships
- Player session management
- Individual reputation per player
- Gossip & rumor system
"""
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
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
# Player Session Management
# ============================================================================

@dataclass
class PlayerSession:
    """Tracks individual player identity and state"""
    player_id: str
    player_name: str
    first_seen: str
    last_seen: str
    total_interactions: int
    global_reputation: float  # -1.0 to 1.0

class PlayerManager:
    """Manages player sessions and tracking"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or MEMORY_VAULT_DB
        self._initialize_player_tables()
    
    def _initialize_player_tables(self):
        """Create player-related tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Player sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS player_sessions (
                player_id TEXT PRIMARY KEY,
                player_name TEXT NOT NULL,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                total_interactions INTEGER DEFAULT 0,
                global_reputation REAL DEFAULT 0.0
            )
        """)
        
        # Player-NPC reputation table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS player_npc_reputation (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id TEXT NOT NULL,
                npc_id TEXT NOT NULL,
                reputation REAL DEFAULT 0.0,
                last_interaction TEXT,
                interaction_count INTEGER DEFAULT 0,
                UNIQUE(player_id, npc_id)
            )
        """)
        
        # Player action history
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS player_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id TEXT NOT NULL,
                npc_id TEXT NOT NULL,
                action TEXT NOT NULL,
                npc_response TEXT,
                reputation_change REAL DEFAULT 0.0,
                timestamp TEXT NOT NULL
            )
        """)
        
        conn.commit()
        conn.close()
        print("✓ Player management tables initialized")
    
    def get_or_create_player(self, player_id: str, player_name: str = None) -> PlayerSession:
        """Get existing player or create new session"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM player_sessions WHERE player_id = ?", (player_id,))
        row = cursor.fetchone()
        
        if row:
            # Update last seen
            cursor.execute(
                "UPDATE player_sessions SET last_seen = ? WHERE player_id = ?",
                (datetime.now().isoformat(), player_id)
            )
            conn.commit()
            player = PlayerSession(
                player_id=row[0],
                player_name=row[1],
                first_seen=row[2],
                last_seen=datetime.now().isoformat(),
                total_interactions=row[4],
                global_reputation=row[5]
            )
        else:
            # Create new player
            now = datetime.now().isoformat()
            name = player_name or f"Player_{player_id[:8]}"
            cursor.execute(
                """INSERT INTO player_sessions 
                   (player_id, player_name, first_seen, last_seen, total_interactions, global_reputation)
                   VALUES (?, ?, ?, ?, 0, 0.0)""",
                (player_id, name, now, now)
            )
            conn.commit()
            player = PlayerSession(
                player_id=player_id,
                player_name=name,
                first_seen=now,
                last_seen=now,
                total_interactions=0,
                global_reputation=0.0
            )
        
        conn.close()
        return player
    
    def get_player_reputation(self, player_id: str, npc_id: str) -> float:
        """Get player's reputation with specific NPC"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT reputation FROM player_npc_reputation WHERE player_id = ? AND npc_id = ?",
            (player_id, npc_id)
        )
        row = cursor.fetchone()
        conn.close()
        
        return row[0] if row else 0.0
    
    def update_reputation(self, player_id: str, npc_id: str, change: float):
        """Update player's reputation with NPC"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get current reputation
        cursor.execute(
            "SELECT reputation, interaction_count FROM player_npc_reputation WHERE player_id = ? AND npc_id = ?",
            (player_id, npc_id)
        )
        row = cursor.fetchone()
        
        if row:
            new_rep = max(-1.0, min(1.0, row[0] + change))
            cursor.execute(
                """UPDATE player_npc_reputation 
                   SET reputation = ?, last_interaction = ?, interaction_count = ?
                   WHERE player_id = ? AND npc_id = ?""",
                (new_rep, datetime.now().isoformat(), row[1] + 1, player_id, npc_id)
            )
        else:
            new_rep = max(-1.0, min(1.0, change))
            cursor.execute(
                """INSERT INTO player_npc_reputation 
                   (player_id, npc_id, reputation, last_interaction, interaction_count)
                   VALUES (?, ?, ?, ?, 1)""",
                (player_id, npc_id, new_rep, datetime.now().isoformat())
            )
        
        conn.commit()
        conn.close()
        
        # Update global reputation
        self._update_global_reputation(player_id)
    
    def _update_global_reputation(self, player_id: str):
        """Calculate and update global reputation (average across all NPCs)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT AVG(reputation) FROM player_npc_reputation WHERE player_id = ?",
            (player_id,)
        )
        avg_rep = cursor.fetchone()[0] or 0.0
        
        cursor.execute(
            "UPDATE player_sessions SET global_reputation = ? WHERE player_id = ?",
            (avg_rep, player_id)
        )
        
        conn.commit()
        conn.close()
    
    def log_action(self, player_id: str, npc_id: str, action: str, response: str, rep_change: float):
        """Log player action for history"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            """INSERT INTO player_actions 
               (player_id, npc_id, action, npc_response, reputation_change, timestamp)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (player_id, npc_id, action, response, rep_change, datetime.now().isoformat())
        )
        
        # Update total interactions
        cursor.execute(
            "UPDATE player_sessions SET total_interactions = total_interactions + 1 WHERE player_id = ?",
            (player_id,)
        )
        
        conn.commit()
        conn.close()


# ============================================================================
# NPC Relationship System
# ============================================================================

class NPCRelationshipGraph:
    """Tracks relationships between NPCs"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or MEMORY_VAULT_DB
        self._initialize_relationship_table()
    
    def _initialize_relationship_table(self):
        """Create relationship table"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS npc_relationships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                npc1_id TEXT NOT NULL,
                npc2_id TEXT NOT NULL,
                relationship_score REAL DEFAULT 0.5,
                relationship_type TEXT DEFAULT 'neutral',
                shared_experiences INTEGER DEFAULT 0,
                last_interaction TEXT,
                UNIQUE(npc1_id, npc2_id)
            )
        """)
        
        conn.commit()
        conn.close()
        print("✓ NPC relationship table initialized")
    
    def get_relationship(self, npc1: str, npc2: str) -> Tuple[float, str]:
        """Get relationship score and type between two NPCs"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Try both directions
        cursor.execute(
            "SELECT relationship_score, relationship_type FROM npc_relationships WHERE npc1_id = ? AND npc2_id = ?",
            (npc1, npc2)
        )
        row = cursor.fetchone()
        
        if not row:
            cursor.execute(
                "SELECT relationship_score, relationship_type FROM npc_relationships WHERE npc1_id = ? AND npc2_id = ?",
                (npc2, npc1)
            )
            row = cursor.fetchone()
        
        conn.close()
        
        if row:
            return row[0], row[1]
        return 0.5, "neutral"  # Default neutral relationship
    
    def update_relationship(self, npc1: str, npc2: str, change: float, interaction_type: str = None):
        """Update relationship between two NPCs"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if relationship exists
        cursor.execute(
            "SELECT relationship_score, shared_experiences FROM npc_relationships WHERE npc1_id = ? AND npc2_id = ?",
            (npc1, npc2)
        )
        row = cursor.fetchone()
        
        if row:
            new_score = max(0.0, min(1.0, row[0] + change))
            rel_type = self._determine_relationship_type(new_score)
            
            cursor.execute(
                """UPDATE npc_relationships 
                   SET relationship_score = ?, relationship_type = ?, shared_experiences = ?, last_interaction = ?
                   WHERE npc1_id = ? AND npc2_id = ?""",
                (new_score, rel_type, row[1] + 1, datetime.now().isoformat(), npc1, npc2)
            )
        else:
            new_score = max(0.0, min(1.0, 0.5 + change))
            rel_type = self._determine_relationship_type(new_score)
            
            cursor.execute(
                """INSERT INTO npc_relationships 
                   (npc1_id, npc2_id, relationship_score, relationship_type, shared_experiences, last_interaction)
                   VALUES (?, ?, ?, ?, 1, ?)""",
                (npc1, npc2, new_score, rel_type, datetime.now().isoformat())
            )
        
        conn.commit()
        conn.close()
    
    def _determine_relationship_type(self, score: float) -> str:
        """Determine relationship type from score"""
        if score < 0.2:
            return "hostile"
        elif score < 0.4:
            return "unfriendly"
        elif score < 0.6:
            return "neutral"
        elif score < 0.8:
            return "friendly"
        else:
            return "allied"
    
    def get_npc_social_circle(self, npc_id: str) -> List[Dict]:
        """Get all relationships for an NPC"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            """SELECT npc2_id, relationship_score, relationship_type, shared_experiences 
               FROM npc_relationships WHERE npc1_id = ?""",
            (npc_id,)
        )
        rows = cursor.fetchall()
        
        # Also check reverse
        cursor.execute(
            """SELECT npc1_id, relationship_score, relationship_type, shared_experiences 
               FROM npc_relationships WHERE npc2_id = ?""",
            (npc_id,)
        )
        rows += cursor.fetchall()
        
        conn.close()
        
        return [
            {
                "npc_id": row[0],
                "relationship_score": row[1],
                "relationship_type": row[2],
                "shared_experiences": row[3]
            }
            for row in rows
        ]


# ============================================================================
# Gossip & Rumor System
# ============================================================================

@dataclass
class Rumor:
    """A piece of gossip spreading among NPCs"""
    rumor_id: str
    about_player: str
    content: str
    truthfulness: float  # 0.0-1.0 (can be exaggerated)
    spread_count: int
    created_by: str
    timestamp: str

class GossipSystem:
    """NPCs share information and rumors about players"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or MEMORY_VAULT_DB
        self._initialize_gossip_table()
    
    def _initialize_gossip_table(self):
        """Create gossip tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rumors (
                rumor_id TEXT PRIMARY KEY,
                about_player TEXT NOT NULL,
                content TEXT NOT NULL,
                truthfulness REAL DEFAULT 1.0,
                spread_count INTEGER DEFAULT 0,
                created_by TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS npc_heard_rumors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                npc_id TEXT NOT NULL,
                rumor_id TEXT NOT NULL,
                heard_from TEXT,
                belief_level REAL DEFAULT 0.5,
                heard_at TEXT NOT NULL,
                UNIQUE(npc_id, rumor_id)
            )
        """)
        
        conn.commit()
        conn.close()
        print("✓ Gossip system initialized")
    
    def create_rumor(self, player_id: str, npc_id: str, action: str, outcome: str) -> Rumor:
        """NPC creates a rumor about player based on interaction"""
        import uuid
        
        # Generate rumor content based on outcome
        if "positive" in outcome.lower() or "help" in action.lower():
            templates = [
                f"{player_id} helped out at {npc_id}'s location. Seems trustworthy.",
                f"Heard {player_id} did something good. Maybe they're alright.",
                f"{player_id} showed respect. Not like the usual troublemakers."
            ]
        elif "negative" in outcome.lower() or "threat" in action.lower():
            templates = [
                f"{player_id} caused trouble near {npc_id}. Keep an eye on them.",
                f"Watch out for {player_id}. They're not to be trusted.",
                f"{player_id} acted suspiciously. Might be dangerous."
            ]
        else:
            templates = [
                f"{player_id} passed through. Nothing special.",
                f"Saw {player_id} around. Seemed ordinary enough."
            ]
        
        content = random.choice(templates)
        rumor_id = str(uuid.uuid4())[:8]
        
        rumor = Rumor(
            rumor_id=rumor_id,
            about_player=player_id,
            content=content,
            truthfulness=random.uniform(0.7, 1.0),  # Slightly exaggerated sometimes
            spread_count=0,
            created_by=npc_id,
            timestamp=datetime.now().isoformat()
        )
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            """INSERT INTO rumors 
               (rumor_id, about_player, content, truthfulness, spread_count, created_by, timestamp)
               VALUES (?, ?, ?, ?, 0, ?, ?)""",
            (rumor.rumor_id, rumor.about_player, rumor.content, rumor.truthfulness, 
             rumor.created_by, rumor.timestamp)
        )
        
        # Creator automatically knows the rumor
        cursor.execute(
            """INSERT INTO npc_heard_rumors (npc_id, rumor_id, heard_from, belief_level, heard_at)
               VALUES (?, ?, 'self', 1.0, ?)""",
            (npc_id, rumor_id, rumor.timestamp)
        )
        
        conn.commit()
        conn.close()
        
        return rumor
    
    def spread_rumor(self, from_npc: str, to_npc: str, rumor_id: str):
        """Spread rumor from one NPC to another"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if to_npc already heard it
        cursor.execute(
            "SELECT 1 FROM npc_heard_rumors WHERE npc_id = ? AND rumor_id = ?",
            (to_npc, rumor_id)
        )
        
        if not cursor.fetchone():
            # NPCs trust friends more
            # In real implementation, adjust belief based on relationship
            belief = random.uniform(0.5, 0.9)
            
            cursor.execute(
                """INSERT INTO npc_heard_rumors (npc_id, rumor_id, heard_from, belief_level, heard_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (to_npc, rumor_id, from_npc, belief, datetime.now().isoformat())
            )
            
            # Increment spread count
            cursor.execute(
                "UPDATE rumors SET spread_count = spread_count + 1 WHERE rumor_id = ?",
                (rumor_id,)
            )
            
            conn.commit()
        
        conn.close()
    
    def get_rumors_about_player(self, player_id: str, npc_id: str = None) -> List[Dict]:
        """Get rumors about a player, optionally filtered by what an NPC knows"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if npc_id:
            # Get only rumors this NPC has heard
            cursor.execute(
                """SELECT r.rumor_id, r.content, r.truthfulness, r.spread_count, r.created_by, 
                          nh.heard_from, nh.belief_level
                   FROM rumors r
                   JOIN npc_heard_rumors nh ON r.rumor_id = nh.rumor_id
                   WHERE r.about_player = ? AND nh.npc_id = ?
                   ORDER BY nh.heard_at DESC""",
                (player_id, npc_id)
            )
        else:
            # Get all rumors about player
            cursor.execute(
                """SELECT rumor_id, content, truthfulness, spread_count, created_by, NULL, NULL
                   FROM rumors WHERE about_player = ?
                   ORDER BY timestamp DESC""",
                (player_id,)
            )
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                "rumor_id": row[0],
                "content": row[1],
                "truthfulness": row[2],
                "spread_count": row[3],
                "created_by": row[4],
                "heard_from": row[5],
                "belief_level": row[6]
            }
            for row in rows
        ]
    
    def spread_all_rumors(self, from_npc: str, to_npc: str) -> int:
        """Share all rumors from_npc knows with to_npc"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get all rumors from_npc knows
        cursor.execute(
            """SELECT rumor_id FROM npc_heard_rumors WHERE npc_id = ?""",
            (from_npc,)
        )
        rumor_ids = [row[0] for row in cursor.fetchall()]
        
        # Also get rumors from_npc created
        cursor.execute(
            """SELECT rumor_id FROM rumors WHERE created_by = ?""",
            (from_npc,)
        )
        rumor_ids.extend([row[0] for row in cursor.fetchall()])
        
        conn.close()
        
        # Spread each rumor
        spread_count = 0
        for rumor_id in set(rumor_ids):
            self.spread_rumor(from_npc, to_npc, rumor_id)
            spread_count += 1
        
        return spread_count


# ============================================================================
# Topic Memory System - NPCs remember conversation topics
# ============================================================================

@dataclass
class ConversationTopic:
    """A memorable topic from a conversation"""
    topic_id: str
    player_id: str
    npc_id: str
    category: str  # family, goal, fear, event, preference, secret
    content: str
    emotional_weight: float  # 0.0-1.0 (higher = more impactful)
    keywords: List[str]
    timestamp: str
    times_referenced: int

class TopicMemorySystem:
    """NPCs remember and recall conversation topics"""
    
    # Keywords that indicate important topics
    TOPIC_INDICATORS = {
        "family": {
            "keywords": ["family", "father", "mother", "brother", "sister", "son", "daughter", "wife", "husband", "parents", "children", "killed", "died", "lost"],
            "emotional_weight": 0.9
        },
        "goal": {
            "keywords": ["want to", "need to", "looking for", "searching", "find", "seeking", "goal", "mission", "quest", "dream"],
            "emotional_weight": 0.7
        },
        "fear": {
            "keywords": ["afraid", "fear", "scared", "terrified", "nightmare", "dread", "worry", "anxious"],
            "emotional_weight": 0.8
        },
        "event": {
            "keywords": ["happened", "attacked", "survived", "escaped", "witnessed", "saw", "remember when", "last year", "last month", "yesterday"],
            "emotional_weight": 0.75
        },
        "preference": {
            "keywords": ["like", "love", "hate", "prefer", "favorite", "enjoy", "despise"],
            "emotional_weight": 0.5
        },
        "secret": {
            "keywords": ["secret", "don't tell", "between us", "confidential", "trust you", "never told anyone", "no one knows", "dark past", "hidden", "used to be", "changed my ways"],
            "emotional_weight": 0.95
        },
        "origin": {
            "keywords": ["from", "hometown", "village", "city", "born", "grew up", "raised", "northern", "southern", "eastern", "western"],
            "emotional_weight": 0.6
        },
        "profession": {
            "keywords": ["work", "job", "trade", "merchant", "soldier", "farmer", "hunter", "blacksmith", "healer", "bandit", "thief", "spy", "captain", "guard", "knight"],
            "emotional_weight": 0.5
        },
        "crime": {
            "keywords": ["robbed", "stole", "killed", "murdered", "crime", "criminal", "outlaw", "bandit", "thief", "guilty"],
            "emotional_weight": 0.9
        }
    }
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or MEMORY_VAULT_DB
        self._initialize_topic_tables()
    
    def _initialize_topic_tables(self):
        """Create topic memory tables with decay support"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversation_topics (
                topic_id TEXT PRIMARY KEY,
                player_id TEXT NOT NULL,
                npc_id TEXT NOT NULL,
                category TEXT NOT NULL,
                content TEXT NOT NULL,
                emotional_weight REAL DEFAULT 0.5,
                keywords TEXT,
                timestamp TEXT NOT NULL,
                times_referenced INTEGER DEFAULT 0,
                memory_strength REAL DEFAULT 1.0,
                last_reinforced TEXT,
                decay_rate REAL DEFAULT 0.05
            )
        """)
        
        # Add new columns if they don't exist (for existing databases)
        try:
            cursor.execute("ALTER TABLE conversation_topics ADD COLUMN memory_strength REAL DEFAULT 1.0")
        except:
            pass
        try:
            cursor.execute("ALTER TABLE conversation_topics ADD COLUMN last_reinforced TEXT")
        except:
            pass
        try:
            cursor.execute("ALTER TABLE conversation_topics ADD COLUMN decay_rate REAL DEFAULT 0.05")
        except:
            pass
        
        # Index for faster lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_topics_player_npc 
            ON conversation_topics(player_id, npc_id)
        """)
        
        # Shared memories table - what NPCs told each other
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS shared_memories (
                shared_id TEXT PRIMARY KEY,
                original_topic_id TEXT NOT NULL,
                from_npc TEXT NOT NULL,
                to_npc TEXT NOT NULL,
                player_id TEXT NOT NULL,
                category TEXT NOT NULL,
                content TEXT NOT NULL,
                emotional_weight REAL DEFAULT 0.5,
                trust_factor REAL DEFAULT 0.7,
                shared_at TEXT NOT NULL,
                memory_strength REAL DEFAULT 0.8
            )
        """)
        
        try:
            cursor.execute("ALTER TABLE shared_memories ADD COLUMN memory_strength REAL DEFAULT 0.8")
        except:
            pass
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_shared_to_npc_player
            ON shared_memories(to_npc, player_id)
        """)
        
        conn.commit()
        conn.close()
        print("✓ Topic memory system initialized (with decay support)")
    
    def extract_topics(self, player_id: str, npc_id: str, message: str) -> List[ConversationTopic]:
        """Extract memorable topics from player message"""
        import uuid
        
        extracted_topics = []
        message_lower = message.lower()
        
        for category, config in self.TOPIC_INDICATORS.items():
            # Check if any keywords match
            matched_keywords = [kw for kw in config["keywords"] if kw in message_lower]
            
            if matched_keywords:
                # Calculate emotional weight based on number of matches and base weight
                weight = min(1.0, config["emotional_weight"] + (len(matched_keywords) * 0.05))
                
                topic = ConversationTopic(
                    topic_id=str(uuid.uuid4())[:12],
                    player_id=player_id,
                    npc_id=npc_id,
                    category=category,
                    content=message,
                    emotional_weight=weight,
                    keywords=matched_keywords,
                    timestamp=datetime.now().isoformat(),
                    times_referenced=0
                )
                extracted_topics.append(topic)
        
        # Store extracted topics
        for topic in extracted_topics:
            self._store_topic(topic)
        
        return extracted_topics
    
    def _store_topic(self, topic: ConversationTopic):
        """Store a topic in the database with decay fields"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check for similar existing topic - if exists, reinforce instead
        cursor.execute("""
            SELECT topic_id FROM conversation_topics 
            WHERE player_id = ? AND npc_id = ? AND category = ?
            AND content = ?
        """, (topic.player_id, topic.npc_id, topic.category, topic.content))
        
        existing = cursor.fetchone()
        if existing:
            # Reinforce existing memory instead of creating duplicate
            cursor.execute("""
                UPDATE conversation_topics 
                SET memory_strength = 1.0, last_reinforced = ?, times_referenced = times_referenced + 1
                WHERE topic_id = ?
            """, (datetime.now().isoformat(), existing[0]))
            conn.commit()
            conn.close()
            return
        
        # Calculate decay rate based on emotional weight (important memories decay slower)
        decay_rate = max(0.02, 0.08 - (topic.emotional_weight * 0.05))
        
        cursor.execute("""
            INSERT INTO conversation_topics 
            (topic_id, player_id, npc_id, category, content, emotional_weight, keywords, timestamp, times_referenced, memory_strength, last_reinforced, decay_rate)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            topic.topic_id, topic.player_id, topic.npc_id, topic.category,
            topic.content, topic.emotional_weight, json.dumps(topic.keywords),
            topic.timestamp, topic.times_referenced, 1.0, topic.timestamp, decay_rate
        ))
        
        conn.commit()
        conn.close()
    
    def get_relevant_topics(self, player_id: str, npc_id: str, current_message: str = "", limit: int = 5) -> List[Dict]:
        """Get topics relevant to current conversation (filtered by memory strength)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get topics with sufficient memory strength, ordered by strength and emotional weight
        cursor.execute("""
            SELECT topic_id, category, content, emotional_weight, keywords, timestamp, times_referenced, memory_strength
            FROM conversation_topics
            WHERE player_id = ? AND npc_id = ? AND memory_strength > 0.2
            ORDER BY memory_strength DESC, emotional_weight DESC, timestamp DESC
            LIMIT ?
        """, (player_id, npc_id, limit * 2))  # Get more to filter
        
        rows = cursor.fetchall()
        conn.close()
        
        topics = []
        current_lower = current_message.lower()
        
        for row in rows:
            keywords = json.loads(row[4]) if row[4] else []
            memory_strength = row[7] if len(row) > 7 else 1.0
            
            # Calculate relevance to current message
            relevance = 0.0
            for kw in keywords:
                if kw in current_lower:
                    relevance += 0.3
            
            # High emotional weight topics are always somewhat relevant
            if row[3] >= 0.8:
                relevance += 0.4
            
            # Factor in memory strength
            effective_relevance = relevance * memory_strength
            
            # Determine memory clarity based on strength
            clarity = "vivid" if memory_strength > 0.8 else "clear" if memory_strength > 0.5 else "vague"
            
            topics.append({
                "topic_id": row[0],
                "category": row[1],
                "content": row[2],
                "emotional_weight": row[3],
                "keywords": keywords,
                "timestamp": row[5],
                "times_referenced": row[6],
                "memory_strength": memory_strength,
                "clarity": clarity,
                "relevance": min(1.0, effective_relevance + row[3] * 0.3)
            })
        
        # Sort by combined relevance, memory strength, and emotional weight
        topics.sort(key=lambda x: x["relevance"] + x["memory_strength"] * 0.5 + x["emotional_weight"] * 0.3, reverse=True)
        
        return topics[:limit]
    
    def get_all_topics_for_player(self, player_id: str, npc_id: str = None) -> List[Dict]:
        """Get all topics about a player (optionally filtered by NPC)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if npc_id:
            cursor.execute("""
                SELECT topic_id, npc_id, category, content, emotional_weight, keywords, timestamp, times_referenced, memory_strength
                FROM conversation_topics
                WHERE player_id = ?  AND npc_id = ?
                ORDER BY timestamp DESC
            """, (player_id, npc_id))
        else:
            cursor.execute("""
                SELECT topic_id, npc_id, category, content, emotional_weight, keywords, timestamp, times_referenced
                FROM conversation_topics
                WHERE player_id = ?
                ORDER BY timestamp DESC
            """, (player_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                "topic_id": row[0],
                "npc_id": row[1],
                "category": row[2],
                "content": row[3],
                "emotional_weight": row[4],
                "keywords": json.loads(row[5]) if row[5] else [],
                "timestamp": row[6],
                "times_referenced": row[7]
            }
            for row in rows
        ]
    
    def mark_topic_referenced(self, topic_id: str):
        """Increment the reference count and reinforce memory when NPC mentions a topic"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE conversation_topics 
            SET times_referenced = times_referenced + 1,
                memory_strength = 1.0,
                last_reinforced = ?
            WHERE topic_id = ?
        """, (datetime.now().isoformat(), topic_id))
        
        conn.commit()
        conn.close()
    
    def reinforce_memory(self, player_id: str, npc_id: str, keywords: List[str]) -> int:
        """Reinforce memories that match given keywords (called when player mentions related topics)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        reinforced_count = 0
        for keyword in keywords:
            cursor.execute("""
                UPDATE conversation_topics 
                SET memory_strength = 1.0,
                    last_reinforced = ?,
                    times_referenced = times_referenced + 1
                WHERE player_id = ? AND npc_id = ? 
                AND keywords LIKE ?
                AND memory_strength < 1.0
            """, (datetime.now().isoformat(), player_id, npc_id, f'%{keyword}%'))
            reinforced_count += cursor.rowcount
        
        conn.commit()
        conn.close()
        return reinforced_count
    
    def apply_memory_decay(self, hours_passed: float = 24.0) -> Dict:
        """Apply decay to all memories based on time passed. Call this periodically."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Decay formula: strength = strength * (1 - decay_rate * hours_factor)
        # Emotional weight affects decay: higher weight = slower decay
        hours_factor = hours_passed / 24.0  # Normalize to days
        
        # Update memory strength with decay
        cursor.execute("""
            UPDATE conversation_topics 
            SET memory_strength = MAX(0, memory_strength - (decay_rate * ? * (1.1 - emotional_weight)))
            WHERE memory_strength > 0
        """, (hours_factor,))
        
        decayed_count = cursor.rowcount
        
        # Also decay shared memories (faster decay for secondhand info)
        cursor.execute("""
            UPDATE shared_memories 
            SET memory_strength = MAX(0, memory_strength - (0.08 * ?))
            WHERE memory_strength > 0
        """, (hours_factor,))
        
        shared_decayed = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        return {"direct_memories_decayed": decayed_count, "shared_memories_decayed": shared_decayed}
    
    def cleanup_forgotten_memories(self, threshold: float = 0.1) -> Dict:
        """Remove memories that have decayed below threshold"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get count before deletion
        cursor.execute("SELECT COUNT(*) FROM conversation_topics WHERE memory_strength < ?", (threshold,))
        direct_forgotten = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM shared_memories WHERE memory_strength < ?", (threshold,))
        shared_forgotten = cursor.fetchone()[0]
        
        # Delete forgotten memories
        cursor.execute("DELETE FROM conversation_topics WHERE memory_strength < ?", (threshold,))
        cursor.execute("DELETE FROM shared_memories WHERE memory_strength < ?", (threshold,))
        
        conn.commit()
        conn.close()
        
        return {"direct_forgotten": direct_forgotten, "shared_forgotten": shared_forgotten}
    
    def get_memory_status(self, player_id: str = None, npc_id: str = None) -> Dict:
        """Get memory decay status for debugging/display"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = "SELECT topic_id, category, content, memory_strength, emotional_weight, last_reinforced FROM conversation_topics"
        params = []
        
        if player_id and npc_id:
            query += " WHERE player_id = ? AND npc_id = ?"
            params = [player_id, npc_id]
        elif player_id:
            query += " WHERE player_id = ?"
            params = [player_id]
        elif npc_id:
            query += " WHERE npc_id = ?"
            params = [npc_id]
        
        query += " ORDER BY memory_strength DESC"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        memories = []
        for row in rows:
            strength = row[3] or 1.0
            status = "vivid" if strength > 0.8 else "clear" if strength > 0.5 else "fading" if strength > 0.2 else "dim"
            memories.append({
                "topic_id": row[0],
                "category": row[1],
                "content": row[2][:50] + "..." if len(row[2]) > 50 else row[2],
                "strength": strength,
                "status": status,
                "emotional_weight": row[4],
                "last_reinforced": row[5]
            })
        
        return {"memories": memories, "total": len(memories)}
    
    def format_topics_for_context(self, topics: List[Dict]) -> str:
        """Format topics as context string for NPC, including memory clarity"""
        if not topics:
            return ""
        
        context_parts = ["You remember these things about this player:"]
        
        for topic in topics:
            category = topic["category"]
            content = topic["content"]
            clarity = topic.get("clarity", "clear")
            
            # Add memory clarity prefix
            clarity_prefix = ""
            if clarity == "vague":
                clarity_prefix = "(vaguely) "
            elif clarity == "vivid":
                clarity_prefix = "(vividly) "
            
            # Format based on category
            if category == "family":
                context_parts.append(f"- [IMPORTANT - Family matter] {clarity_prefix}They shared: \"{content}\"")
            elif category == "secret":
                context_parts.append(f"- [CONFIDENTIAL] {clarity_prefix}They trusted you with: \"{content}\"")
            elif category == "fear":
                context_parts.append(f"- [Their fear] They expressed: \"{content}\"")
            elif category == "goal":
                context_parts.append(f"- [Their goal] They mentioned: \"{content}\"")
            elif category == "event":
                context_parts.append(f"- [Past event] They told you: \"{content}\"")
            else:
                context_parts.append(f"- [{category}] \"{content}\"")
        
        context_parts.append("\nReference these memories naturally when relevant. Show you remember and care.")
        
        return "\n".join(context_parts)

    def share_memory_with_npc(self, from_npc: str, to_npc: str, topic_id: str) -> bool:
        """Share a memory about a player from one NPC to another"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get the original topic
        cursor.execute("""
            SELECT player_id, category, content, emotional_weight, keywords
            FROM conversation_topics WHERE topic_id = ?
        """, (topic_id,))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return False
        
        player_id, category, content, weight, keywords = row
        
        # Check if to_npc already knows this (prevent duplicates)
        cursor.execute("""
            SELECT 1 FROM shared_memories 
            WHERE to_npc = ? AND original_topic_id = ?
        """, (to_npc, topic_id))
        
        if cursor.fetchone():
            conn.close()
            return False  # Already shared
        
        # Create shared memory record
        import uuid
        shared_id = str(uuid.uuid4())[:12]
        
        cursor.execute("""
            INSERT INTO shared_memories 
            (shared_id, original_topic_id, from_npc, to_npc, player_id, category, content, 
             emotional_weight, trust_factor, shared_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            shared_id, topic_id, from_npc, to_npc, player_id, category, content,
            weight * 0.8,  # Slightly reduce weight for secondhand info
            0.7,  # Trust factor (how much to_npc believes from_npc)
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
        return True
    
    def get_shared_memories_about_player(self, npc_id: str, player_id: str) -> List[Dict]:
        """Get memories that other NPCs shared with this NPC about a player"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT shared_id, from_npc, category, content, emotional_weight, trust_factor, shared_at
            FROM shared_memories
            WHERE to_npc = ? AND player_id = ?
            ORDER BY shared_at DESC
        """, (npc_id, player_id))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                "shared_id": row[0],
                "told_by": row[1],
                "category": row[2],
                "content": row[3],
                "emotional_weight": row[4],
                "trust_factor": row[5],
                "shared_at": row[6]
            }
            for row in rows
        ]
    
    def format_shared_memories_for_context(self, shared_memories: List[Dict]) -> str:
        """Format shared memories as context for NPC"""
        if not shared_memories:
            return ""
        
        context_parts = ["\nYou've also heard about this player from others:"]
        
        for mem in shared_memories:
            told_by = mem["told_by"]
            content = mem["content"]
            trust = mem["trust_factor"]
            
            trust_qualifier = "reliably" if trust > 0.7 else "supposedly"
            context_parts.append(f"- {told_by} {trust_qualifier} told you: \"{content}\"")
        
        context_parts.append("Consider what you've heard, but form your own judgment.")
        
        return "\n".join(context_parts)
    
    def auto_share_memories(self, from_npc: str, to_npc: str, player_id: str = None) -> int:
        """Automatically share relevant memories between two NPCs during gossip"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get relationship strength between NPCs
        rel_score, rel_type = relationship_graph.get_relationship(from_npc, to_npc)
        
        # Only share if relationship is friendly
        if rel_score < 0.5:
            conn.close()
            return 0
        
        # Get high-importance topics from from_npc
        if player_id:
            cursor.execute("""
                SELECT topic_id FROM conversation_topics
                WHERE npc_id = ? AND player_id = ? AND emotional_weight >= 0.6
                ORDER BY emotional_weight DESC LIMIT 3
            """, (from_npc, player_id))
        else:
            cursor.execute("""
                SELECT topic_id FROM conversation_topics
                WHERE npc_id = ? AND emotional_weight >= 0.6
                ORDER BY emotional_weight DESC LIMIT 5
            """, (from_npc,))
        
        topic_ids = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        # Share topics based on relationship
        share_chance = rel_score * 0.8  # Better friends share more
        shared_count = 0
        
        import random
        for topic_id in topic_ids:
            if random.random() < share_chance:
                if self.share_memory_with_npc(from_npc, to_npc, topic_id):
                    shared_count += 1
        
        return shared_count


# ============================================================================
# Dynamic Quest Generation System
# ============================================================================

@dataclass
class Quest:
    """A dynamically generated quest"""
    quest_id: str
    npc_id: str  # NPC who generated the quest
    quest_type: str  # fetch, protect, investigate, revenge, trade, rescue
    title: str
    description: str
    target_player: str  # Player this quest is suited for (based on memories)
    objectives: List[str]
    rewards: Dict
    difficulty: str  # easy, medium, hard
    status: str  # available, active, completed, failed
    created_at: str
    expires_at: str  # Quests can expire
    context_memories: List[str]  # Memory IDs that inspired this quest


class QuestGenerator:
    """Generates quests based on NPC needs, memories, and relationships"""
    
    QUEST_TEMPLATES = {
        "fetch": {
            "titles": [
                "Retrieve Lost {item}",
                "Gather {item} from the {location}",
                "Find and Return {item}"
            ],
            "descriptions": [
                "I need someone to retrieve {item} from {location}. It's important to me.",
                "There's {item} out in {location} that I desperately need. Can you get it?",
                "I've lost my {item} somewhere near {location}. Please find it for me."
            ]
        },
        "protect": {
            "titles": [
                "Guard the {target}",
                "Escort to {location}",
                "Defend Against {threat}"
            ],
            "descriptions": [
                "I need protection while traveling to {location}. The roads aren't safe.",
                "{target} needs guarding. There have been threats lately.",
                "Something dangerous lurks near {location}. I need someone capable to handle it."
            ]
        },
        "investigate": {
            "titles": [
                "Uncover the Truth about {subject}",
                "Investigate {location}",
                "Find Information on {subject}"
            ],
            "descriptions": [
                "Strange things are happening at {location}. I need someone to look into it.",
                "I've heard rumors about {subject}. Can you find out what's really going on?",
                "There's something suspicious about {subject}. Investigate discreetly."
            ]
        },
        "revenge": {
            "titles": [
                "Justice for {victim}",
                "Hunt Down {target}",
                "Settle the Score"
            ],
            "descriptions": [
                "Someone wronged me, and I want justice. Find {target} and make them pay.",
                "{target} took something precious from me. I want it back—or them punished.",
                "I remember what {target} did. Help me get revenge."
            ]
        },
        "trade": {
            "titles": [
                "Deliver {item} to {recipient}",
                "Broker a Deal",
                "Secure Trade Route"
            ],
            "descriptions": [
                "I have {item} that needs to reach {recipient} safely. Interested?",
                "There's profit to be made if you can negotiate with {recipient} on my behalf.",
                "The trade routes have been disrupted. Clear them and there's coin in it for you."
            ]
        },
        "rescue": {
            "titles": [
                "Save {victim}",
                "Rescue Mission to {location}",
                "Free the Captive"
            ],
            "descriptions": [
                "{victim} has been taken. I need someone to bring them back.",
                "Someone I care about is trapped in {location}. Please help.",
                "They're holding {victim} somewhere. Find them before it's too late."
            ]
        }
    }
    
    ITEMS = ["supplies", "medicine", "weapons", "gold", "documents", "artifact", "tools", "food", "water"]
    LOCATIONS = ["the northern pass", "the old ruins", "the docks", "the forest edge", "the abandoned mine", "the merchant district"]
    THREATS = ["bandits", "wild beasts", "raiders", "unknown assailants", "rival faction"]
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or MEMORY_VAULT_DB
        self._initialize_quest_tables()
    
    def _initialize_quest_tables(self):
        """Create quest tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quests (
                quest_id TEXT PRIMARY KEY,
                npc_id TEXT NOT NULL,
                quest_type TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                target_player TEXT,
                objectives TEXT,
                rewards TEXT,
                difficulty TEXT DEFAULT 'medium',
                status TEXT DEFAULT 'available',
                created_at TEXT NOT NULL,
                expires_at TEXT,
                context_memories TEXT
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_quests_npc_status
            ON quests(npc_id, status)
        """)
        
        conn.commit()
        conn.close()
        print("✓ Quest system initialized")
    
    def generate_quest_from_memories(self, npc_id: str, player_id: str = None) -> Quest:
        """Generate a quest based on NPC's memories about a player"""
        import uuid
        import random
        
        # Get relevant memories
        memories = topic_memory.get_all_topics_for_player(player_id, npc_id) if player_id else []
        
        # Determine quest type based on memories
        quest_type = self._determine_quest_type(memories, npc_id)
        
        # Get template
        template = self.QUEST_TEMPLATES[quest_type]
        
        # Generate quest details
        item = random.choice(self.ITEMS)
        location = random.choice(self.LOCATIONS)
        threat = random.choice(self.THREATS)
        
        # Personalize based on memories
        personalization = self._personalize_quest(memories, player_id)
        
        title = random.choice(template["titles"]).format(
            item=item, location=location, target=threat, 
            subject=personalization.get("subject", "the mystery"),
            victim=personalization.get("victim", "the prisoner"),
            recipient=personalization.get("recipient", "my contact")
        )
        
        description = random.choice(template["descriptions"]).format(
            item=item, location=location, target=threat,
            subject=personalization.get("subject", "the situation"),
            victim=personalization.get("victim", "someone important"),
            recipient=personalization.get("recipient", "a trusted ally")
        )
        
        # Add memory-based context to description
        if memories and player_id:
            memory_context = self._add_memory_context(memories, description)
            description = memory_context
        
        # Calculate difficulty and rewards
        difficulty = random.choice(["easy", "medium", "hard"])
        rewards = self._calculate_rewards(difficulty, quest_type)
        
        # Create quest
        quest = Quest(
            quest_id=str(uuid.uuid4())[:12],
            npc_id=npc_id,
            quest_type=quest_type,
            title=title,
            description=description,
            target_player=player_id,
            objectives=self._generate_objectives(quest_type, item, location),
            rewards=rewards,
            difficulty=difficulty,
            status="available",
            created_at=datetime.now().isoformat(),
            expires_at=(datetime.now() + timedelta(days=7)).isoformat(),
            context_memories=[m.get("topic_id", "") for m in memories[:3]]
        )
        
        # Store quest
        self._store_quest(quest)
        
        return quest
    
    def _determine_quest_type(self, memories: List[Dict], npc_id: str) -> str:
        """Determine quest type based on memories and NPC state"""
        import random
        
        # Check memory categories
        categories = [m.get("category", "") for m in memories]
        
        if "crime" in categories or "secret" in categories:
            return random.choice(["investigate", "revenge"])
        elif "family" in categories:
            return random.choice(["rescue", "protect"])
        elif "goal" in categories:
            return random.choice(["fetch", "trade"])
        elif "fear" in categories:
            return random.choice(["protect", "investigate"])
        else:
            return random.choice(["fetch", "trade", "protect"])
    
    def _personalize_quest(self, memories: List[Dict], player_id: str) -> Dict:
        """Extract personalization details from memories"""
        personalization = {}
        
        for memory in memories:
            category = memory.get("category", "")
            content = memory.get("content", "").lower()
            
            if "bandit" in content or "thief" in content:
                personalization["subject"] = "the bandits"
            if "family" in content:
                personalization["victim"] = "a family member"
            if "merchant" in content or "trade" in content:
                personalization["recipient"] = "a merchant contact"
        
        return personalization
    
    def _add_memory_context(self, memories: List[Dict], base_description: str) -> str:
        """Add memory-based context to quest description"""
        if not memories:
            return base_description
        
        # Pick the most important memory
        top_memory = max(memories, key=lambda m: m.get("emotional_weight", 0))
        category = top_memory.get("category", "")
        
        context_additions = {
            "crime": " I know you have... experience with this sort of thing. That's why I'm asking you.",
            "secret": " You've trusted me before. Now I'm trusting you with this.",
            "family": " I remember what you told me about your family. This might be personal for you.",
            "goal": " This aligns with what you've been looking for, doesn't it?",
            "profession": " Your skills make you perfect for this task."
        }
        
        addition = context_additions.get(category, "")
        return base_description + addition
    
    def _generate_objectives(self, quest_type: str, item: str, location: str) -> List[str]:
        """Generate quest objectives"""
        objectives_map = {
            "fetch": [f"Travel to {location}", f"Find the {item}", "Return safely"],
            "protect": [f"Meet at {location}", "Ensure safe passage", "Report back when done"],
            "investigate": [f"Search {location}", "Gather evidence", "Report findings"],
            "revenge": ["Track down the target", "Confront them", "Return with proof"],
            "trade": [f"Collect the {item}", "Deliver to the recipient", "Secure payment"],
            "rescue": [f"Locate {location}", "Free the captive", "Escort to safety"]
        }
        return objectives_map.get(quest_type, ["Complete the task"])
    
    def _calculate_rewards(self, difficulty: str, quest_type: str) -> Dict:
        """Calculate quest rewards"""
        base_gold = {"easy": 50, "medium": 100, "hard": 200}
        base_rep = {"easy": 0.05, "medium": 0.1, "hard": 0.2}
        
        return {
            "gold": base_gold[difficulty],
            "reputation": base_rep[difficulty],
            "item": "random_item" if difficulty == "hard" else None
        }
    
    def _store_quest(self, quest: Quest):
        """Store quest in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO quests 
            (quest_id, npc_id, quest_type, title, description, target_player, objectives, rewards, difficulty, status, created_at, expires_at, context_memories)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            quest.quest_id, quest.npc_id, quest.quest_type, quest.title, quest.description,
            quest.target_player, json.dumps(quest.objectives), json.dumps(quest.rewards),
            quest.difficulty, quest.status, quest.created_at, quest.expires_at,
            json.dumps(quest.context_memories)
        ))
        
        conn.commit()
        conn.close()
    
    def get_available_quests(self, npc_id: str = None, player_id: str = None) -> List[Dict]:
        """Get available quests, optionally filtered by NPC or tailored for player"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = "SELECT * FROM quests WHERE status = 'available'"
        params = []
        
        if npc_id:
            query += " AND npc_id = ?"
            params.append(npc_id)
        
        if player_id:
            query += " AND (target_player = ? OR target_player IS NULL)"
            params.append(player_id)
        
        query += " ORDER BY created_at DESC"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        quests = []
        for row in rows:
            quests.append({
                "quest_id": row[0],
                "npc_id": row[1],
                "quest_type": row[2],
                "title": row[3],
                "description": row[4],
                "target_player": row[5],
                "objectives": json.loads(row[6]) if row[6] else [],
                "rewards": json.loads(row[7]) if row[7] else {},
                "difficulty": row[8],
                "status": row[9],
                "created_at": row[10],
                "expires_at": row[11]
            })
        
        return quests
    
    def accept_quest(self, quest_id: str, player_id: str) -> bool:
        """Player accepts a quest"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE quests SET status = 'active', target_player = ?
            WHERE quest_id = ? AND status = 'available'
        """, (player_id, quest_id))
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success
    
    def complete_quest(self, quest_id: str) -> Dict:
        """Mark quest as completed and return rewards"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT rewards, npc_id, target_player FROM quests WHERE quest_id = ?", (quest_id,))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return {"success": False, "error": "Quest not found"}
        
        rewards = json.loads(row[0]) if row[0] else {}
        npc_id = row[1]
        player_id = row[2]
        
        cursor.execute("UPDATE quests SET status = 'completed' WHERE quest_id = ?", (quest_id,))
        conn.commit()
        conn.close()
        
        # Apply reputation reward
        if player_id and npc_id and rewards.get("reputation"):
            player_manager.update_reputation(player_id, npc_id, rewards["reputation"])
        
        return {"success": True, "rewards": rewards}
    
    def expire_old_quests(self) -> int:
        """Mark expired quests as failed"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        cursor.execute("""
            UPDATE quests SET status = 'expired'
            WHERE status = 'available' AND expires_at < ?
        """, (now,))
        
        expired_count = cursor.rowcount
        conn.commit()
        conn.close()
        return expired_count


# ============================================================================
# World Simulation System - Living, Breathing World
# ============================================================================

class WorldSimulator:
    """
    Background world simulation that makes the game world feel alive.
    Automatically handles:
    - Memory decay over time
    - Quest expiration
    - NPC gossip and information spread
    - Dynamic quest generation
    - World events
    """
    
    def __init__(self):
        self.is_running = False
        self.world_time = datetime.now()  # Simulated world time
        self.time_scale = 1.0  # 1.0 = real time, 24.0 = 1 real hour = 1 game day
        self.tick_interval = 60  # Seconds between simulation ticks
        self.last_tick = None
        self.stats = {
            "total_ticks": 0,
            "memories_decayed": 0,
            "quests_expired": 0,
            "gossip_events": 0,
            "quests_generated": 0
        }
        self.active_npcs = set()  # Track NPCs in simulation
        self.event_log = []  # Recent world events
    
    def register_npc(self, npc_id: str):
        """Register an NPC to participate in world simulation"""
        self.active_npcs.add(npc_id)
    
    def unregister_npc(self, npc_id: str):
        """Remove NPC from world simulation"""
        self.active_npcs.discard(npc_id)
    
    def get_world_time(self) -> str:
        """Get current simulated world time"""
        return self.world_time.strftime("%Y-%m-%d %H:%M")
    
    def advance_time(self, real_seconds: float) -> float:
        """Advance world time based on real time and time scale"""
        game_seconds = real_seconds * self.time_scale
        self.world_time += timedelta(seconds=game_seconds)
        return game_seconds
    
    async def tick(self) -> Dict:
        """
        Execute one simulation tick.
        Returns summary of what happened.
        """
        tick_results = {
            "world_time": self.get_world_time(),
            "events": []
        }
        
        # Calculate time since last tick
        now = datetime.now()
        if self.last_tick:
            real_elapsed = (now - self.last_tick).total_seconds()
        else:
            real_elapsed = self.tick_interval
        
        game_hours = self.advance_time(real_elapsed) / 3600  # Convert to hours
        self.last_tick = now
        self.stats["total_ticks"] += 1
        
        # 1. Apply memory decay
        if game_hours > 0:
            decay_result = topic_memory.apply_memory_decay(game_hours)
            self.stats["memories_decayed"] += decay_result.get("direct_memories_decayed", 0)
            if decay_result.get("direct_memories_decayed", 0) > 0:
                tick_results["events"].append({
                    "type": "memory_decay",
                    "detail": f"Time fades {decay_result['direct_memories_decayed']} memories"
                })
        
        # 2. Clean up forgotten memories (below 10% strength)
        cleanup = topic_memory.cleanup_forgotten_memories(0.1)
        if cleanup.get("direct_forgotten", 0) > 0:
            tick_results["events"].append({
                "type": "memories_forgotten",
                "detail": f"{cleanup['direct_forgotten']} memories completely forgotten"
            })
        
        # 3. Expire old quests
        expired = quest_generator.expire_old_quests()
        self.stats["quests_expired"] += expired
        if expired > 0:
            tick_results["events"].append({
                "type": "quests_expired",
                "detail": f"{expired} quests expired"
            })
        
        # 4. Random NPC gossip (if multiple NPCs active)
        active_list = list(self.active_npcs)
        if len(active_list) >= 2 and random.random() < 0.3:  # 30% chance per tick
            npc1, npc2 = random.sample(active_list, 2)
            
            # NPCs share rumors
            gossip_system.spread_all_rumors(npc1, npc2)
            
            # NPCs share memories about players they both know
            shared = topic_memory.auto_share_memories(npc1, npc2)
            
            self.stats["gossip_events"] += 1
            if shared > 0:
                tick_results["events"].append({
                    "type": "npc_gossip",
                    "detail": f"{npc1} shared {shared} memories with {npc2}"
                })
                self._log_event(f"💬 {npc1} gossiped with {npc2}")
        
        # 5. Random quest generation (if NPCs are active)
        if len(active_list) > 0 and random.random() < 0.1:  # 10% chance per tick
            npc_id = random.choice(active_list)
            try:
                quest = quest_generator.generate_quest_from_memories(npc_id)
                self.stats["quests_generated"] += 1
                tick_results["events"].append({
                    "type": "quest_generated",
                    "detail": f"{npc_id} created quest: {quest.title}"
                })
                self._log_event(f"📜 {npc_id} posted: {quest.title}")
            except:
                pass  # Silently handle quest generation failures
        
        return tick_results
    
    def _log_event(self, message: str):
        """Log a world event"""
        self.event_log.append({
            "time": self.get_world_time(),
            "message": message
        })
        # Keep only last 50 events
        if len(self.event_log) > 50:
            self.event_log = self.event_log[-50:]
    
    def get_status(self) -> Dict:
        """Get current simulation status"""
        return {
            "is_running": self.is_running,
            "world_time": self.get_world_time(),
            "time_scale": self.time_scale,
            "tick_interval": self.tick_interval,
            "active_npcs": list(self.active_npcs),
            "stats": self.stats,
            "recent_events": self.event_log[-10:]
        }
    
    def configure(self, time_scale: float = None, tick_interval: int = None):
        """Configure simulation parameters"""
        if time_scale is not None:
            self.time_scale = max(0.1, min(100.0, time_scale))  # Clamp between 0.1x and 100x
        if tick_interval is not None:
            self.tick_interval = max(10, min(300, tick_interval))  # Between 10s and 5min
        
        return {
            "time_scale": self.time_scale,
            "tick_interval": self.tick_interval
        }
    
    def reset_stats(self):
        """Reset simulation statistics"""
        self.stats = {
            "total_ticks": 0,
            "memories_decayed": 0,
            "quests_expired": 0,
            "gossip_events": 0,
            "quests_generated": 0
        }
        self.event_log = []


# Global instances
player_manager = PlayerManager()
relationship_graph = NPCRelationshipGraph()
gossip_system = GossipSystem()
topic_memory = TopicMemorySystem()
quest_generator = QuestGenerator()
world_simulator = WorldSimulator()
