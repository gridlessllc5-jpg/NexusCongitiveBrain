"""
Phase 4: Dynamic Civilizations
- NPC Autonomous Goals
- Quest Chains
- Trade Routes
- Territorial Conflicts
- API-first design for Unreal Engine integration
"""
import json
import sqlite3
import uuid
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict

# Import path configuration for database locations
try:
    from core.paths import MEMORY_VAULT_DB
except ImportError:
    try:
        from paths import MEMORY_VAULT_DB
    except ImportError:
        MEMORY_VAULT_DB = "/app/npc_system/database/memory_vault.db"


# ============================================================================
# NPC Goals System - Autonomous NPC Objectives
# ============================================================================

@dataclass
class NPCGoal:
    """An autonomous goal that an NPC is working toward"""
    goal_id: str
    npc_id: str
    goal_type: str  # trade, hunt, protect, revenge, acquire, socialize, survive
    description: str
    target: Optional[str]  # Target NPC, player, location, or item
    priority: float  # 0.0-1.0
    progress: float  # 0.0-1.0
    status: str  # active, completed, failed, abandoned
    created_at: str
    deadline: Optional[str]
    reward_on_completion: Dict
    steps: List[Dict]


class NPCGoalSystem:
    """Manages autonomous NPC goals and objectives"""
    
    GOAL_TEMPLATES = {
        "trade": {
            "descriptions": [
                "Establish trade connection with {target}",
                "Negotiate better prices with {target}",
                "Find new customers for my goods"
            ],
            "suitable_for": ["traders", "citizens"],
            "base_priority": 0.6
        },
        "hunt": {
            "descriptions": [
                "Track down {target}",
                "Bring {target} to justice",
                "Eliminate the threat of {target}"
            ],
            "suitable_for": ["guards"],
            "base_priority": 0.8
        },
        "protect": {
            "descriptions": [
                "Keep {target} safe from harm",
                "Guard {target} against threats",
                "Ensure the security of {target}"
            ],
            "suitable_for": ["guards", "citizens"],
            "base_priority": 0.7
        },
        "revenge": {
            "descriptions": [
                "Get revenge on {target}",
                "Make {target} pay for what they did",
                "Settle the score with {target}"
            ],
            "suitable_for": ["outcasts", "citizens"],
            "base_priority": 0.9
        },
        "acquire": {
            "descriptions": [
                "Obtain {target}",
                "Secure {target} for myself",
                "Find a way to get {target}"
            ],
            "suitable_for": ["traders", "outcasts"],
            "base_priority": 0.5
        },
        "socialize": {
            "descriptions": [
                "Build friendship with {target}",
                "Gain the trust of {target}",
                "Form an alliance with {target}"
            ],
            "suitable_for": ["traders", "citizens"],
            "base_priority": 0.4
        },
        "survive": {
            "descriptions": [
                "Find food and shelter",
                "Avoid {target}",
                "Stay alive another day"
            ],
            "suitable_for": ["outcasts", "citizens"],
            "base_priority": 0.95
        },
        "territory": {
            "descriptions": [
                "Expand control to {target}",
                "Defend {target} from rivals",
                "Reclaim {target} for our faction"
            ],
            "suitable_for": ["guards", "outcasts"],
            "base_priority": 0.75
        }
    }
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or MEMORY_VAULT_DB
        self._initialize_tables()
    
    def _initialize_tables(self):
        """Create goal tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS npc_goals (
                goal_id TEXT PRIMARY KEY,
                npc_id TEXT NOT NULL,
                goal_type TEXT NOT NULL,
                description TEXT NOT NULL,
                target TEXT,
                priority REAL DEFAULT 0.5,
                progress REAL DEFAULT 0.0,
                status TEXT DEFAULT 'active',
                created_at TEXT NOT NULL,
                deadline TEXT,
                reward_on_completion TEXT,
                steps TEXT
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_goals_npc_status
            ON npc_goals(npc_id, status)
        """)
        
        conn.commit()
        conn.close()
        print("✓ NPC Goal system initialized")
    
    def generate_goal(self, npc_id: str, npc_faction: str, context: Dict = None) -> NPCGoal:
        """Generate an autonomous goal for an NPC based on their faction and context"""
        # Determine suitable goal types for this faction
        suitable_types = []
        for goal_type, template in self.GOAL_TEMPLATES.items():
            if npc_faction in template["suitable_for"]:
                suitable_types.append((goal_type, template["base_priority"]))
        
        if not suitable_types:
            suitable_types = [("survive", 0.5)]
        
        # Weight selection by priority
        total_weight = sum(p for _, p in suitable_types)
        r = random.random() * total_weight
        cumulative = 0
        selected_type = suitable_types[0][0]
        
        for goal_type, priority in suitable_types:
            cumulative += priority
            if r <= cumulative:
                selected_type = goal_type
                break
        
        template = self.GOAL_TEMPLATES[selected_type]
        
        # Generate target based on goal type
        target = self._generate_target(selected_type, npc_faction, context)
        
        # Create description
        description = random.choice(template["descriptions"]).format(target=target or "the objective")
        
        # Generate steps
        steps = self._generate_goal_steps(selected_type, target)
        
        goal = NPCGoal(
            goal_id=str(uuid.uuid4())[:12],
            npc_id=npc_id,
            goal_type=selected_type,
            description=description,
            target=target,
            priority=template["base_priority"] + random.uniform(-0.1, 0.1),
            progress=0.0,
            status="active",
            created_at=datetime.now().isoformat(),
            deadline=(datetime.now() + timedelta(days=random.randint(3, 14))).isoformat(),
            reward_on_completion={"reputation": 0.1, "gold": random.randint(20, 100)},
            steps=steps
        )
        
        self._store_goal(goal)
        return goal
    
    def _generate_target(self, goal_type: str, faction: str, context: Dict = None) -> str:
        """Generate appropriate target for goal type"""
        targets = {
            "trade": ["the merchant guild", "northern traders", "a new supplier", "the docks"],
            "hunt": ["the bandit leader", "a wanted criminal", "the outlaw", "smugglers"],
            "protect": ["the city gates", "the merchant quarter", "the citizens", "the trade route"],
            "revenge": ["those who wronged me", "the betrayer", "my enemy", "the one responsible"],
            "acquire": ["rare goods", "valuable information", "weapons", "resources"],
            "socialize": ["influential people", "potential allies", "the guild master", "newcomers"],
            "survive": ["the authorities", "my enemies", "starvation", "danger"],
            "territory": ["the northern district", "the market square", "the old quarter", "the docks"]
        }
        
        return random.choice(targets.get(goal_type, ["the objective"]))
    
    def _generate_goal_steps(self, goal_type: str, target: str) -> List[Dict]:
        """Generate steps to complete the goal"""
        steps_map = {
            "trade": [
                {"step": 1, "action": "identify_opportunity", "description": "Find potential trade partners", "completed": False},
                {"step": 2, "action": "negotiate", "description": "Negotiate terms", "completed": False},
                {"step": 3, "action": "finalize", "description": "Complete the deal", "completed": False}
            ],
            "hunt": [
                {"step": 1, "action": "gather_info", "description": "Gather information about target", "completed": False},
                {"step": 2, "action": "track", "description": "Track down the target", "completed": False},
                {"step": 3, "action": "confront", "description": "Confront and capture/eliminate", "completed": False}
            ],
            "protect": [
                {"step": 1, "action": "assess_threat", "description": "Assess potential threats", "completed": False},
                {"step": 2, "action": "fortify", "description": "Strengthen defenses", "completed": False},
                {"step": 3, "action": "patrol", "description": "Maintain vigilance", "completed": False}
            ],
            "revenge": [
                {"step": 1, "action": "plan", "description": "Plan the revenge", "completed": False},
                {"step": 2, "action": "prepare", "description": "Gather resources needed", "completed": False},
                {"step": 3, "action": "execute", "description": "Execute the plan", "completed": False}
            ],
            "territory": [
                {"step": 1, "action": "scout", "description": "Scout the territory", "completed": False},
                {"step": 2, "action": "mobilize", "description": "Mobilize forces", "completed": False},
                {"step": 3, "action": "claim", "description": "Claim or defend the territory", "completed": False}
            ]
        }
        
        return steps_map.get(goal_type, [
            {"step": 1, "action": "start", "description": "Begin working on goal", "completed": False},
            {"step": 2, "action": "progress", "description": "Make progress", "completed": False},
            {"step": 3, "action": "complete", "description": "Complete the goal", "completed": False}
        ])
    
    def _store_goal(self, goal: NPCGoal):
        """Store goal in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO npc_goals 
            (goal_id, npc_id, goal_type, description, target, priority, progress, status, created_at, deadline, reward_on_completion, steps)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            goal.goal_id, goal.npc_id, goal.goal_type, goal.description, goal.target,
            goal.priority, goal.progress, goal.status, goal.created_at, goal.deadline,
            json.dumps(goal.reward_on_completion), json.dumps(goal.steps)
        ))
        
        conn.commit()
        conn.close()
    
    def get_npc_goals(self, npc_id: str, status: str = None) -> List[Dict]:
        """Get all goals for an NPC"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if status:
            cursor.execute("""
                SELECT * FROM npc_goals WHERE npc_id = ? AND status = ?
                ORDER BY priority DESC
            """, (npc_id, status))
        else:
            cursor.execute("""
                SELECT * FROM npc_goals WHERE npc_id = ?
                ORDER BY priority DESC
            """, (npc_id,))
        
        goals = []
        for row in cursor.fetchall():
            goals.append({
                "goal_id": row[0],
                "npc_id": row[1],
                "goal_type": row[2],
                "description": row[3],
                "target": row[4],
                "priority": row[5],
                "progress": row[6],
                "status": row[7],
                "created_at": row[8],
                "deadline": row[9],
                "reward_on_completion": json.loads(row[10]) if row[10] else {},
                "steps": json.loads(row[11]) if row[11] else []
            })
        
        conn.close()
        return goals
    
    def update_goal_progress(self, goal_id: str, progress_delta: float = 0.1) -> Dict:
        """Update progress on a goal"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT progress, steps, status FROM npc_goals WHERE goal_id = ?", (goal_id,))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return {"error": "Goal not found"}
        
        current_progress, steps_json, status = row
        if status != "active":
            conn.close()
            return {"error": f"Goal is {status}", "status": status}
        
        new_progress = min(1.0, current_progress + progress_delta)
        
        # Update steps based on progress
        steps = json.loads(steps_json) if steps_json else []
        steps_completed = int(new_progress * len(steps))
        for i, step in enumerate(steps):
            step["completed"] = i < steps_completed
        
        # Check if goal is complete
        new_status = "completed" if new_progress >= 1.0 else "active"
        
        cursor.execute("""
            UPDATE npc_goals SET progress = ?, steps = ?, status = ?
            WHERE goal_id = ?
        """, (new_progress, json.dumps(steps), new_status, goal_id))
        
        conn.commit()
        conn.close()
        
        return {
            "goal_id": goal_id,
            "progress": new_progress,
            "status": new_status,
            "steps_completed": steps_completed
        }
    
    def abandon_goal(self, goal_id: str, reason: str = "abandoned") -> bool:
        """Mark a goal as abandoned"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("UPDATE npc_goals SET status = 'abandoned' WHERE goal_id = ?", (goal_id,))
        success = cursor.rowcount > 0
        
        conn.commit()
        conn.close()
        return success


# ============================================================================
# Quest Chain System - Multi-step storylines
# ============================================================================

@dataclass
class QuestChain:
    """A chain of connected quests forming a storyline"""
    chain_id: str
    name: str
    description: str
    quests: List[str]  # Quest IDs in order
    current_quest_index: int
    status: str  # available, in_progress, completed, failed
    player_id: Optional[str]
    created_by_npc: str
    rewards_on_completion: Dict
    created_at: str


class QuestChainSystem:
    """Manages quest chains and storylines"""
    
    CHAIN_TEMPLATES = {
        "merchant_opportunity": {
            "name": "The Trade Route",
            "description": "Help establish a profitable trade route",
            "quest_sequence": ["scout_route", "clear_dangers", "negotiate_terms", "first_delivery"],
            "faction": "traders"
        },
        "bandit_hunt": {
            "name": "Hunting the Outlaws",
            "description": "Track down and eliminate a bandit threat",
            "quest_sequence": ["gather_intel", "track_hideout", "assault_camp", "capture_leader"],
            "faction": "guards"
        },
        "rebellion": {
            "name": "Spark of Rebellion",
            "description": "Help the outcasts fight back against oppression",
            "quest_sequence": ["recruit_allies", "gather_supplies", "sabotage", "uprising"],
            "faction": "outcasts"
        },
        "mystery": {
            "name": "The Dark Secret",
            "description": "Uncover a conspiracy threatening the city",
            "quest_sequence": ["find_clues", "interrogate_witness", "infiltrate", "expose_truth"],
            "faction": "citizens"
        }
    }
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or MEMORY_VAULT_DB
        self._initialize_tables()
    
    def _initialize_tables(self):
        """Create quest chain tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quest_chains (
                chain_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                quests TEXT,
                current_quest_index INTEGER DEFAULT 0,
                status TEXT DEFAULT 'available',
                player_id TEXT,
                created_by_npc TEXT,
                rewards_on_completion TEXT,
                created_at TEXT
            )
        """)
        
        conn.commit()
        conn.close()
        print("✓ Quest Chain system initialized")
    
    def create_chain(self, npc_id: str, npc_faction: str, player_id: str = None) -> QuestChain:
        """Create a new quest chain based on NPC faction"""
        # Find suitable template
        suitable_templates = {k: v for k, v in self.CHAIN_TEMPLATES.items() 
                            if v["faction"] == npc_faction}
        
        if not suitable_templates:
            suitable_templates = self.CHAIN_TEMPLATES
        
        template_key = random.choice(list(suitable_templates.keys()))
        template = suitable_templates[template_key]
        
        chain = QuestChain(
            chain_id=str(uuid.uuid4())[:12],
            name=template["name"],
            description=template["description"],
            quests=template["quest_sequence"],
            current_quest_index=0,
            status="available",
            player_id=player_id,
            created_by_npc=npc_id,
            rewards_on_completion={
                "gold": random.randint(200, 500),
                "reputation": 0.3,
                "special_item": f"reward_{template_key}"
            },
            created_at=datetime.now().isoformat()
        )
        
        self._store_chain(chain)
        return chain
    
    def _store_chain(self, chain: QuestChain):
        """Store chain in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO quest_chains
            (chain_id, name, description, quests, current_quest_index, status, player_id, created_by_npc, rewards_on_completion, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            chain.chain_id, chain.name, chain.description, json.dumps(chain.quests),
            chain.current_quest_index, chain.status, chain.player_id, chain.created_by_npc,
            json.dumps(chain.rewards_on_completion), chain.created_at
        ))
        
        conn.commit()
        conn.close()
    
    def get_available_chains(self, player_id: str = None) -> List[Dict]:
        """Get available quest chains"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if player_id:
            cursor.execute("""
                SELECT * FROM quest_chains 
                WHERE status IN ('available', 'in_progress') AND (player_id IS NULL OR player_id = ?)
                ORDER BY created_at DESC
            """, (player_id,))
        else:
            cursor.execute("""
                SELECT * FROM quest_chains WHERE status = 'available'
                ORDER BY created_at DESC
            """)
        
        chains = []
        for row in cursor.fetchall():
            chains.append({
                "chain_id": row[0],
                "name": row[1],
                "description": row[2],
                "quests": json.loads(row[3]) if row[3] else [],
                "current_quest_index": row[4],
                "status": row[5],
                "player_id": row[6],
                "created_by_npc": row[7],
                "rewards_on_completion": json.loads(row[8]) if row[8] else {},
                "created_at": row[9]
            })
        
        conn.close()
        return chains
    
    def start_chain(self, chain_id: str, player_id: str) -> Dict:
        """Player starts a quest chain"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE quest_chains SET status = 'in_progress', player_id = ?
            WHERE chain_id = ? AND status = 'available'
        """, (player_id, chain_id))
        
        success = cursor.rowcount > 0
        conn.commit()
        
        if success:
            cursor.execute("SELECT quests FROM quest_chains WHERE chain_id = ?", (chain_id,))
            row = cursor.fetchone()
            quests = json.loads(row[0]) if row and row[0] else []
            current_quest = quests[0] if quests else None
        else:
            current_quest = None
        
        conn.close()
        return {
            "success": success,
            "chain_id": chain_id,
            "current_quest": current_quest
        }
    
    def advance_chain(self, chain_id: str) -> Dict:
        """Advance to next quest in chain"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT quests, current_quest_index, status FROM quest_chains WHERE chain_id = ?
        """, (chain_id,))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return {"error": "Chain not found"}
        
        quests = json.loads(row[0]) if row[0] else []
        current_index = row[1]
        status = row[2]
        
        if status != "in_progress":
            conn.close()
            return {"error": f"Chain is {status}"}
        
        new_index = current_index + 1
        
        if new_index >= len(quests):
            # Chain complete
            cursor.execute("""
                UPDATE quest_chains SET status = 'completed', current_quest_index = ?
                WHERE chain_id = ?
            """, (new_index, chain_id))
            conn.commit()
            conn.close()
            return {
                "chain_id": chain_id,
                "status": "completed",
                "message": "Quest chain completed!"
            }
        
        cursor.execute("""
            UPDATE quest_chains SET current_quest_index = ?
            WHERE chain_id = ?
        """, (new_index, chain_id))
        
        conn.commit()
        conn.close()
        
        return {
            "chain_id": chain_id,
            "status": "in_progress",
            "previous_quest": quests[current_index],
            "current_quest": quests[new_index],
            "progress": f"{new_index + 1}/{len(quests)}"
        }


# ============================================================================
# Trade Route System
# ============================================================================

@dataclass
class TradeRoute:
    """A trade connection between two locations/NPCs"""
    route_id: str
    from_location: str
    to_location: str
    from_npc: str
    to_npc: str
    goods: List[str]
    profit_margin: float
    risk_level: float  # 0.0-1.0
    status: str  # active, disrupted, destroyed
    established_at: str
    last_trade: Optional[str]
    total_trades: int


class TradeRouteSystem:
    """Manages trade routes between NPCs and locations"""
    
    GOODS = ["food", "weapons", "medicine", "tools", "luxury_goods", "raw_materials", "information"]
    LOCATIONS = ["porto_cobre_gates", "merchant_district", "docks", "northern_pass", "old_quarter", "market_square"]
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or MEMORY_VAULT_DB
        self._initialize_tables()
    
    def _initialize_tables(self):
        """Create trade route tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trade_routes (
                route_id TEXT PRIMARY KEY,
                from_location TEXT,
                to_location TEXT,
                from_npc TEXT,
                to_npc TEXT,
                goods TEXT,
                profit_margin REAL DEFAULT 0.1,
                risk_level REAL DEFAULT 0.2,
                status TEXT DEFAULT 'active',
                established_at TEXT,
                last_trade TEXT,
                total_trades INTEGER DEFAULT 0
            )
        """)
        
        conn.commit()
        conn.close()
        print("✓ Trade Route system initialized")
    
    def establish_route(self, from_npc: str, to_npc: str, from_loc: str = None, to_loc: str = None) -> TradeRoute:
        """Establish a new trade route"""
        from_location = from_loc or random.choice(self.LOCATIONS)
        to_location = to_loc or random.choice([l for l in self.LOCATIONS if l != from_location])
        
        route = TradeRoute(
            route_id=str(uuid.uuid4())[:12],
            from_location=from_location,
            to_location=to_location,
            from_npc=from_npc,
            to_npc=to_npc,
            goods=random.sample(self.GOODS, k=random.randint(1, 3)),
            profit_margin=random.uniform(0.05, 0.25),
            risk_level=random.uniform(0.1, 0.5),
            status="active",
            established_at=datetime.now().isoformat(),
            last_trade=None,
            total_trades=0
        )
        
        self._store_route(route)
        return route
    
    def _store_route(self, route: TradeRoute):
        """Store route in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO trade_routes
            (route_id, from_location, to_location, from_npc, to_npc, goods, profit_margin, risk_level, status, established_at, last_trade, total_trades)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            route.route_id, route.from_location, route.to_location, route.from_npc, route.to_npc,
            json.dumps(route.goods), route.profit_margin, route.risk_level, route.status,
            route.established_at, route.last_trade, route.total_trades
        ))
        
        conn.commit()
        conn.close()
    
    def get_all_routes(self, status: str = None) -> List[Dict]:
        """Get all trade routes"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if status:
            cursor.execute("SELECT * FROM trade_routes WHERE status = ?", (status,))
        else:
            cursor.execute("SELECT * FROM trade_routes")
        
        routes = []
        for row in cursor.fetchall():
            routes.append({
                "route_id": row[0],
                "from_location": row[1],
                "to_location": row[2],
                "from_npc": row[3],
                "to_npc": row[4],
                "goods": json.loads(row[5]) if row[5] else [],
                "profit_margin": row[6],
                "risk_level": row[7],
                "status": row[8],
                "established_at": row[9],
                "last_trade": row[10],
                "total_trades": row[11]
            })
        
        conn.close()
        return routes
    
    def execute_trade(self, route_id: str) -> Dict:
        """Execute a trade on a route"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM trade_routes WHERE route_id = ?", (route_id,))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return {"error": "Route not found"}
        
        status = row[8]
        if status != "active":
            conn.close()
            return {"error": f"Route is {status}"}
        
        risk_level = row[7]
        profit_margin = row[6]
        
        # Check if trade is disrupted by risk
        if random.random() < risk_level:
            # Trade disrupted!
            cursor.execute("""
                UPDATE trade_routes SET status = 'disrupted' WHERE route_id = ?
            """, (route_id,))
            conn.commit()
            conn.close()
            return {
                "route_id": route_id,
                "success": False,
                "event": "trade_disrupted",
                "message": "The trade was disrupted by bandits!"
            }
        
        # Successful trade
        cursor.execute("""
            UPDATE trade_routes 
            SET total_trades = total_trades + 1, last_trade = ?
            WHERE route_id = ?
        """, (datetime.now().isoformat(), route_id))
        
        conn.commit()
        conn.close()
        
        gold_earned = int(100 * (1 + profit_margin))
        
        return {
            "route_id": route_id,
            "success": True,
            "gold_earned": gold_earned,
            "message": "Trade completed successfully"
        }
    
    def disrupt_route(self, route_id: str, reason: str = "attack") -> bool:
        """Disrupt a trade route"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE trade_routes SET status = 'disrupted' WHERE route_id = ? AND status = 'active'
        """, (route_id,))
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success
    
    def restore_route(self, route_id: str) -> bool:
        """Restore a disrupted route"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE trade_routes SET status = 'active' WHERE route_id = ? AND status = 'disrupted'
        """, (route_id,))
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success


# ============================================================================
# Territorial Conflict System
# ============================================================================

@dataclass
class TerritorialBattle:
    """A battle for territory control"""
    battle_id: str
    territory: str
    attacker_faction: str
    defender_faction: str
    attacker_strength: float
    defender_strength: float
    status: str  # pending, in_progress, attacker_won, defender_won
    started_at: str
    ended_at: Optional[str]
    casualties: Dict


class TerritorialConflictSystem:
    """Manages territorial conflicts between factions"""
    
    TERRITORIES = {
        "gates": {"name": "City Gates", "default_owner": "guards", "strategic_value": 0.9},
        "market": {"name": "Market Square", "default_owner": "traders", "strategic_value": 0.8},
        "docks": {"name": "The Docks", "default_owner": "traders", "strategic_value": 0.7},
        "slums": {"name": "The Slums", "default_owner": "outcasts", "strategic_value": 0.4},
        "old_quarter": {"name": "Old Quarter", "default_owner": "citizens", "strategic_value": 0.5},
        "northern_pass": {"name": "Northern Pass", "default_owner": "guards", "strategic_value": 0.6}
    }
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or MEMORY_VAULT_DB
        self._initialize_tables()
        self.territory_control = {t: info["default_owner"] for t, info in self.TERRITORIES.items()}
    
    def _initialize_tables(self):
        """Create battle tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS territorial_battles (
                battle_id TEXT PRIMARY KEY,
                territory TEXT NOT NULL,
                attacker_faction TEXT NOT NULL,
                defender_faction TEXT NOT NULL,
                attacker_strength REAL,
                defender_strength REAL,
                status TEXT DEFAULT 'pending',
                started_at TEXT,
                ended_at TEXT,
                casualties TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS territory_control (
                territory TEXT PRIMARY KEY,
                controlling_faction TEXT NOT NULL,
                control_strength REAL DEFAULT 1.0,
                last_changed TEXT
            )
        """)
        
        # Initialize default control
        for territory, info in self.TERRITORIES.items():
            cursor.execute("""
                INSERT OR IGNORE INTO territory_control (territory, controlling_faction, control_strength, last_changed)
                VALUES (?, ?, 1.0, ?)
            """, (territory, info["default_owner"], datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        print("✓ Territorial Conflict system initialized")
    
    def get_territory_control(self) -> Dict:
        """Get current territory control status"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT territory, controlling_faction, control_strength FROM territory_control")
        
        control = {}
        for row in cursor.fetchall():
            territory = row[0]
            control[territory] = {
                "name": self.TERRITORIES.get(territory, {}).get("name", territory),
                "controlling_faction": row[1],
                "control_strength": row[2],
                "strategic_value": self.TERRITORIES.get(territory, {}).get("strategic_value", 0.5)
            }
        
        conn.close()
        return control
    
    def initiate_battle(self, territory: str, attacker_faction: str) -> TerritorialBattle:
        """Initiate a battle for territory"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get current controller
        cursor.execute("SELECT controlling_faction FROM territory_control WHERE territory = ?", (territory,))
        row = cursor.fetchone()
        defender_faction = row[0] if row else "citizens"
        
        if attacker_faction == defender_faction:
            conn.close()
            return None  # Can't attack own territory
        
        # Calculate strengths (simplified)
        attacker_strength = random.uniform(0.4, 0.8)
        defender_strength = random.uniform(0.5, 0.9)  # Defenders have slight advantage
        
        battle = TerritorialBattle(
            battle_id=str(uuid.uuid4())[:12],
            territory=territory,
            attacker_faction=attacker_faction,
            defender_faction=defender_faction,
            attacker_strength=attacker_strength,
            defender_strength=defender_strength,
            status="in_progress",
            started_at=datetime.now().isoformat(),
            ended_at=None,
            casualties={"attacker": 0, "defender": 0}
        )
        
        cursor.execute("""
            INSERT INTO territorial_battles
            (battle_id, territory, attacker_faction, defender_faction, attacker_strength, defender_strength, status, started_at, casualties)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            battle.battle_id, battle.territory, battle.attacker_faction, battle.defender_faction,
            battle.attacker_strength, battle.defender_strength, battle.status, battle.started_at,
            json.dumps(battle.casualties)
        ))
        
        conn.commit()
        conn.close()
        return battle
    
    def resolve_battle(self, battle_id: str) -> Dict:
        """Resolve a battle and determine winner"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM territorial_battles WHERE battle_id = ?", (battle_id,))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return {"error": "Battle not found"}
        
        territory = row[1]
        attacker = row[2]
        defender = row[3]
        attacker_str = row[4]
        defender_str = row[5]
        
        # Determine winner (weighted random based on strengths)
        attacker_roll = attacker_str * random.uniform(0.8, 1.2)
        defender_roll = defender_str * random.uniform(0.9, 1.1)  # Defender bonus
        
        attacker_won = attacker_roll > defender_roll
        
        casualties = {
            "attacker": int((1 - attacker_str) * 100 * random.uniform(0.5, 1.5)),
            "defender": int((1 - defender_str) * 100 * random.uniform(0.5, 1.5))
        }
        
        status = "attacker_won" if attacker_won else "defender_won"
        
        cursor.execute("""
            UPDATE territorial_battles 
            SET status = ?, ended_at = ?, casualties = ?
            WHERE battle_id = ?
        """, (status, datetime.now().isoformat(), json.dumps(casualties), battle_id))
        
        # Update territory control if attacker won
        if attacker_won:
            cursor.execute("""
                UPDATE territory_control 
                SET controlling_faction = ?, control_strength = 0.6, last_changed = ?
                WHERE territory = ?
            """, (attacker, datetime.now().isoformat(), territory))
        
        conn.commit()
        conn.close()
        
        return {
            "battle_id": battle_id,
            "territory": territory,
            "winner": attacker if attacker_won else defender,
            "status": status,
            "casualties": casualties,
            "territory_changed_hands": attacker_won
        }
    
    def get_battle_history(self, territory: str = None, limit: int = 10) -> List[Dict]:
        """Get battle history"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if territory:
            cursor.execute("""
                SELECT * FROM territorial_battles WHERE territory = ?
                ORDER BY started_at DESC LIMIT ?
            """, (territory, limit))
        else:
            cursor.execute("""
                SELECT * FROM territorial_battles
                ORDER BY started_at DESC LIMIT ?
            """, (limit,))
        
        battles = []
        for row in cursor.fetchall():
            battles.append({
                "battle_id": row[0],
                "territory": row[1],
                "attacker_faction": row[2],
                "defender_faction": row[3],
                "attacker_strength": row[4],
                "defender_strength": row[5],
                "status": row[6],
                "started_at": row[7],
                "ended_at": row[8],
                "casualties": json.loads(row[9]) if row[9] else {}
            })
        
        conn.close()
        return battles


# Global instances
npc_goal_system = NPCGoalSystem()
quest_chain_system = QuestChainSystem()
trade_route_system = TradeRouteSystem()
territorial_conflict_system = TerritorialConflictSystem()
