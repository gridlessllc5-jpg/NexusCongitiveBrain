import React, { useState, useEffect, useRef } from "react";
import axios from "axios";
import "./App.css";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "http://localhost:8001";
const API = `${BACKEND_URL}/api`;

function App() {
  const [activeTab, setActiveTab] = useState("chat");
  const [selectedNPC, setSelectedNPC] = useState("vera");
  const [npcInitialized, setNpcInitialized] = useState(false);
  const [npcStatus, setNpcStatus] = useState(null);
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState("");
  const [loading, setLoading] = useState(false);
  const [activeNPCs, setActiveNPCs] = useState([]);
  const [allNPCs, setAllNPCs] = useState([]);
  const [quests, setQuests] = useState([]);
  const [territories, setTerritories] = useState(null);
  const [factions, setFactions] = useState(null);
  const messagesEndRef = useRef(null);

  // Player state
  const [playerId, setPlayerId] = useState("player_001");
  const [playerName, setPlayerName] = useState("Traveler");
  const [playerInfo, setPlayerInfo] = useState(null);
  const [allPlayers, setAllPlayers] = useState([]);
  const [currentReputation, setCurrentReputation] = useState(0);

  // NPC relationships and memories
  const [npcRelationships, setNpcRelationships] = useState([]);
  const [npcMemories, setNpcMemories] = useState([]);
  const [topicsExtracted, setTopicsExtracted] = useState(0);

  // World Simulation state
  const [worldStatus, setWorldStatus] = useState(null);
  const [worldEvents, setWorldEvents] = useState([]);
  const [timeScale, setTimeScale] = useState(24);
  const [simulationRunning, setSimulationRunning] = useState(false);

  // Faction & Territory state
  const [factionDetails, setFactionDetails] = useState(null);
  const [territoryControl, setTerritoryControl] = useState(null);
  const [factionEvents, setFactionEvents] = useState([]);
  const [battleHistory, setBattleHistory] = useState([]);
  const [tradeRoutes, setTradeRoutes] = useState([]);

  // Random NPC Generation
  const [randomNPCRole, setRandomNPCRole] = useState("merchant");
  const [customNPCData, setCustomNPCData] = useState({
    name: "",
    role: "",
    location: "",
    backstory: "",
    dialogue_style: "",
    faction: "citizens",
    curiosity: 0.5,
    empathy: 0.5,
    risk_tolerance: 0.5,
    aggression: 0.5,
    discipline: 0.5,
    romanticism: 0.5,
    opportunism: 0.5,
    paranoia: 0.5
  });

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    if (activeTab === "npcs") {
      fetchAllNPCs();
    } else if (activeTab === "quests") {
      fetchQuests();
    } else if (activeTab === "territory") {
      fetchTerritories();
      fetchFactions();
      fetchFactionDetails();
      fetchTerritoryControl();
      fetchFactionEvents();
      fetchBattleHistory();
      fetchTradeRoutes();
    } else if (activeTab === "players") {
      fetchAllPlayers();
      fetchPlayerInfo();
    } else if (activeTab === "world") {
      fetchWorldStatus();
      fetchWorldEvents();
    }
  }, [activeTab]);

  // Fetch player info when npc is initialized
  useEffect(() => {
    if (npcInitialized && playerId) {
      fetchPlayerInfo();
    }
  }, [npcInitialized, playerId]);

  // Auto-refresh world status when simulation is running
  useEffect(() => {
    let interval;
    if (activeTab === "world" && simulationRunning) {
      interval = setInterval(() => {
        fetchWorldStatus();
        fetchWorldEvents();
      }, 5000); // Refresh every 5 seconds
    }
    return () => clearInterval(interval);
  }, [activeTab, simulationRunning]);

  const initializeNPC = async () => {
    try {
      setLoading(true);
      const response = await axios.post(`${API}/npc/init`, {
        npc_id: selectedNPC,
      });

      if (response.data.status === "initialized" || response.data.status === "already_exists") {
        setNpcInitialized(true);
        await fetchNPCStatus();
        await fetchAllNPCs();
        
        setMessages([
          {
            type: "system",
            content: `${selectedNPC.toUpperCase()} initialized. ${response.data.role} at ${response.data.location}`,
          },
        ]);
      }
    } catch (error) {
      console.error("Error initializing NPC:", error);
      setMessages([
        {
          type: "error",
          content: `Failed to initialize ${selectedNPC}: ${error.response?.data?.detail || error.message}`,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const fetchNPCStatus = async () => {
    try {
      const response = await axios.get(`${API}/npc/status/${selectedNPC}`);
      setNpcStatus(response.data);
    } catch (error) {
      console.error("Error fetching NPC status:", error);
    }
  };

  const fetchAllNPCs = async () => {
    try {
      const response = await axios.get(`${API}/npc/list`);
      setActiveNPCs(response.data.npcs || []);
    } catch (error) {
      console.error("Error fetching NPCs:", error);
    }
  };

  const fetchPlayerInfo = async () => {
    try {
      const response = await axios.get(`${API}/player/${playerId}`);
      setPlayerInfo(response.data);
      // Update current reputation for selected NPC
      if (response.data.npc_reputations && response.data.npc_reputations[selectedNPC]) {
        setCurrentReputation(response.data.npc_reputations[selectedNPC]);
      } else {
        setCurrentReputation(0);
      }
    } catch (error) {
      console.error("Error fetching player info:", error);
    }
  };

  const fetchAllPlayers = async () => {
    try {
      const response = await axios.get(`${API}/players`);
      setAllPlayers(response.data.players || []);
    } catch (error) {
      console.error("Error fetching players:", error);
    }
  };

  const fetchNPCRelationships = async (npcId) => {
    try {
      const response = await axios.get(`${API}/npc/relationships/${npcId}`);
      setNpcRelationships(response.data.relationships || []);
    } catch (error) {
      console.error("Error fetching NPC relationships:", error);
    }
  };

  const fetchNPCMemories = async () => {
    try {
      const response = await axios.get(`${API}/npc/memories/${selectedNPC}/${playerId}`);
      setNpcMemories(response.data.memories || []);
    } catch (error) {
      console.error("Error fetching NPC memories:", error);
    }
  };

  // World Simulation Functions
  const fetchWorldStatus = async () => {
    try {
      const response = await axios.get(`${API}/world/status`);
      setWorldStatus(response.data);
      setSimulationRunning(response.data.is_running);
    } catch (error) {
      console.error("Error fetching world status:", error);
    }
  };

  const fetchWorldEvents = async () => {
    try {
      const response = await axios.get(`${API}/world/events?limit=20`);
      setWorldEvents(response.data.events || []);
    } catch (error) {
      console.error("Error fetching world events:", error);
    }
  };

  const startSimulation = async () => {
    try {
      setLoading(true);
      const response = await axios.post(`${API}/world/start?time_scale=${timeScale}&tick_interval=30`);
      setWorldStatus(response.data);
      setSimulationRunning(true);
    } catch (error) {
      console.error("Error starting simulation:", error);
    } finally {
      setLoading(false);
    }
  };

  const stopSimulation = async () => {
    try {
      setLoading(true);
      const response = await axios.post(`${API}/world/stop`);
      setWorldStatus(prev => ({ ...prev, ...response.data, is_running: false }));
      setSimulationRunning(false);
    } catch (error) {
      console.error("Error stopping simulation:", error);
    } finally {
      setLoading(false);
    }
  };

  const manualTick = async () => {
    try {
      setLoading(true);
      await axios.post(`${API}/world/tick`);
      await fetchWorldStatus();
      await fetchWorldEvents();
    } catch (error) {
      console.error("Error executing tick:", error);
    } finally {
      setLoading(false);
    }
  };

  const sendAction = async () => {
    if (!inputValue.trim()) return;

    try {
      setLoading(true);
      const userMessage = {
        type: "player",
        content: inputValue,
      };
      setMessages((prev) => [...prev, userMessage]);
      setInputValue("");

      const response = await axios.post(`${API}/npc/action`, {
        npc_id: selectedNPC,
        action: inputValue,
        player_id: playerId,
        player_name: playerName,
      });

      const { cognitive_frame, limbic_state, reputation, topics_extracted, topics_remembered, heard_from_others } = response.data;

      // Update reputation
      if (reputation !== undefined) {
        setCurrentReputation(reputation);
      }

      // Update topics extracted count
      if (topics_extracted > 0) {
        setTopicsExtracted(prev => prev + topics_extracted);
      }

      const reputationChange = cognitive_frame.trust_mod || 0;
      const reputationIndicator = reputationChange > 0 ? `📈 +${reputationChange.toFixed(2)}` : 
                                   reputationChange < 0 ? `📉 ${reputationChange.toFixed(2)}` : '';
      
      // Add memory indicator if topics were remembered
      const memoryIndicator = topics_remembered > 0 ? `🧠 ${topics_remembered}` : '';
      
      // Add gossip indicator if NPC heard about player from others
      const gossipIndicator = heard_from_others > 0 ? `👂 ${heard_from_others}` : '';

      setMessages((prev) => [
        ...prev,
        {
          type: "npc_thought",
          content: cognitive_frame.internal_reflection,
        },
        {
          type: "npc_dialogue",
          content: cognitive_frame.dialogue || "[Remains silent]",
          mood: cognitive_frame.emotional_state,
          intent: cognitive_frame.intent,
          reputationChange: reputationIndicator,
          memoryIndicator: memoryIndicator,
          gossipIndicator: gossipIndicator,
        },
      ]);

      await fetchNPCStatus();
      await fetchPlayerInfo();
      await fetchNPCMemories();
    } catch (error) {
      console.error("Error sending action:", error);
      setMessages((prev) => [
        ...prev,
        {
          type: "error",
          content: `Error: ${error.response?.data?.detail || error.message}`,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const generateRandomNPC = async () => {
    try {
      setLoading(true);
      const response = await axios.post(`${API}/npc/generate/random`, {
        role_type: randomNPCRole,
        auto_initialize: true
      });

      alert(`✅ Generated NPC: ${response.data.npc_id}\nRole: ${response.data.role}`);
      await fetchAllNPCs();
    } catch (error) {
      alert(`❌ Error: ${error.response?.data?.detail || error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const createCustomNPC = async () => {
    try {
      setLoading(true);
      const response = await axios.post(`${API}/npc/create/custom`, {
        name: customNPCData.name,
        role: customNPCData.role,
        location: customNPCData.location,
        backstory: customNPCData.backstory,
        dialogue_style: customNPCData.dialogue_style,
        faction: customNPCData.faction,
        personality: {
          curiosity: customNPCData.curiosity,
          empathy: customNPCData.empathy,
          risk_tolerance: customNPCData.risk_tolerance,
          aggression: customNPCData.aggression,
          discipline: customNPCData.discipline,
          romanticism: customNPCData.romanticism,
          opportunism: customNPCData.opportunism,
          paranoia: customNPCData.paranoia
        },
        auto_initialize: true
      });

      alert(`✅ Created NPC: ${response.data.npc_id}`);
      await fetchAllNPCs();
    } catch (error) {
      alert(`❌ Error: ${error.response?.data?.detail || error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const generateQuestForNPC = async (npcId) => {
    try {
      const response = await axios.post(`${API}/quest/generate/${npcId}`);
      alert(`✅ Quest Generated!\n\nTitle: ${response.data.title}\nType: ${response.data.quest_type}\nDifficulty: ${response.data.difficulty}`);
      await fetchQuests();
    } catch (error) {
      alert(`❌ Error: ${error.response?.data?.detail || error.message}`);
    }
  };

  const fetchQuests = async () => {
    try {
      const response = await axios.get(`${API}/quests/available`);
      setQuests(response.data.quests || []);
    } catch (error) {
      console.error("Error fetching quests:", error);
    }
  };

  const fetchTerritories = async () => {
    try {
      const response = await axios.get(`${API}/territory/overview`);
      setTerritories(response.data);
    } catch (error) {
      console.error("Error fetching territories:", error);
    }
  };

  const fetchFactions = async () => {
    try {
      const response = await axios.get(`${API}/factions`);
      setFactions(response.data);
    } catch (error) {
      console.error("Error fetching factions:", error);
    }
  };

  // New Faction & Territory Functions
  const fetchFactionDetails = async () => {
    try {
      const response = await axios.get(`${API}/factions`);
      setFactionDetails(response.data);
    } catch (error) {
      console.error("Error fetching faction details:", error);
    }
  };

  const fetchTerritoryControl = async () => {
    try {
      const response = await axios.get(`${API}/territory/control`);
      setTerritoryControl(response.data.territories || response.data);
    } catch (error) {
      console.error("Error fetching territory control:", error);
    }
  };

  const fetchFactionEvents = async () => {
    try {
      const response = await axios.get(`${API}/faction/events?limit=15`);
      setFactionEvents(response.data.events || []);
    } catch (error) {
      console.error("Error fetching faction events:", error);
    }
  };

  const fetchBattleHistory = async () => {
    try {
      const response = await axios.get(`${API}/battles?limit=10`);
      setBattleHistory(response.data.battles || []);
    } catch (error) {
      console.error("Error fetching battle history:", error);
    }
  };

  const fetchTradeRoutes = async () => {
    try {
      const response = await axios.get(`${API}/traderoutes`);
      setTradeRoutes(response.data.routes || []);
    } catch (error) {
      console.error("Error fetching trade routes:", error);
    }
  };

  const triggerFactionEvent = async (eventType) => {
    try {
      // Pick two random factions
      const factionIds = ["guards", "traders", "citizens", "outcasts"];
      const f1 = factionIds[Math.floor(Math.random() * factionIds.length)];
      let f2 = factionIds[Math.floor(Math.random() * factionIds.length)];
      while (f2 === f1) {
        f2 = factionIds[Math.floor(Math.random() * factionIds.length)];
      }
      
      await axios.post(`${API}/faction/event?event_type=${eventType}&faction1=${f1}&faction2=${f2}&description=${eventType} between ${f1} and ${f2}`);
      await fetchFactionEvents();
      await fetchFactionDetails();
    } catch (error) {
      console.error("Error triggering faction event:", error);
    }
  };

  const initiateBattle = async (territory) => {
    try {
      const attacker = prompt("Which faction attacks? (guards, traders, citizens, outcasts)");
      if (!attacker) return;
      
      const response = await axios.post(`${API}/territory/${territory}/battle?attacker_faction=${attacker}`);
      if (response.data.status === "battle_initiated") {
        alert(`Battle initiated for ${territory}!\nAttacker: ${response.data.battle.attacker}\nDefender: ${response.data.battle.defender}`);
        await fetchBattleHistory();
        await fetchTerritoryControl();
      }
    } catch (error) {
      alert(`Error: ${error.response?.data?.detail || error.message}`);
    }
  };

  const resolveBattle = async (battleId) => {
    try {
      const response = await axios.post(`${API}/battle/${battleId}/resolve`);
      if (response.data.winner) {
        alert(`Battle resolved!\nWinner: ${response.data.winner}\n${response.data.territory_changed_hands ? 'Territory changed hands!' : 'Defender held the line!'}`);
      }
      await fetchBattleHistory();
      await fetchTerritoryControl();
    } catch (error) {
      alert(`Error: ${error.response?.data?.detail || error.message}`);
    }
  };

  const establishNewRoute = async () => {
    try {
      if (activeNPCs.length < 2) {
        alert("Need at least 2 active NPCs to establish a trade route");
        return;
      }
      const fromNpc = activeNPCs[0]?.npc_id || "merchant";
      const toNpc = activeNPCs[1]?.npc_id || "vera";
      
      const response = await axios.post(`${API}/traderoute/establish?from_npc=${fromNpc}&to_npc=${toNpc}`);
      if (response.data.status === "route_established") {
        alert(`Trade route established!\n${response.data.route.from} → ${response.data.route.to}\nGoods: ${response.data.route.goods.join(", ")}`);
      }
      await fetchTradeRoutes();
    } catch (error) {
      alert(`Error: ${error.response?.data?.detail || error.message}`);
    }
  };

  const executeTrade = async (routeId) => {
    try {
      const response = await axios.post(`${API}/traderoute/${routeId}/execute`);
      if (response.data.success) {
        alert(`Trade successful! Earned ${response.data.gold_earned} gold`);
      } else {
        alert(`Trade failed: ${response.data.message || response.data.event}`);
      }
      await fetchTradeRoutes();
    } catch (error) {
      alert(`Error: ${error.response?.data?.detail || error.message}`);
    }
  };

  const disruptRoute = async (routeId) => {
    try {
      await axios.post(`${API}/traderoute/${routeId}/disrupt?reason=attack`);
      alert("Trade route disrupted!");
      await fetchTradeRoutes();
    } catch (error) {
      alert(`Error: ${error.response?.data?.detail || error.message}`);
    }
  };

  const restoreRoute = async (routeId) => {
    try {
      await axios.post(`${API}/traderoute/${routeId}/restore`);
      alert("Trade route restored!");
      await fetchTradeRoutes();
    } catch (error) {
      alert(`Error: ${error.response?.data?.detail || error.message}`);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendAction();
    }
  };

  const switchNPC = (npcId) => {
    setSelectedNPC(npcId);
    setNpcInitialized(false);
    setMessages([]);
    setNpcStatus(null);
  };

  return (
    <div className="app-container" data-testid="npc-system-app">
      <header className="header">
        <h1 data-testid="app-title">🧠 Fractured Survival - NPC Management Dashboard</h1>
        <p className="subtitle">Full Control Over Your AI NPCs</p>
      </header>

      {/* Tab Navigation */}
      <div className="tabs">
        <button 
          className={`tab ${activeTab === "chat" ? "active" : ""}`}
          onClick={() => setActiveTab("chat")}
          data-testid="chat-tab"
        >
          💬 Chat
        </button>
        <button 
          className={`tab ${activeTab === "generate" ? "active" : ""}`}
          onClick={() => setActiveTab("generate")}
          data-testid="generate-tab"
        >
          ✨ Generate NPCs
        </button>
        <button 
          className={`tab ${activeTab === "npcs" ? "active" : ""}`}
          onClick={() => setActiveTab("npcs")}
          data-testid="npcs-tab"
        >
          👥 All NPCs ({activeNPCs.length})
        </button>
        <button 
          className={`tab ${activeTab === "players" ? "active" : ""}`}
          onClick={() => setActiveTab("players")}
          data-testid="players-tab"
        >
          🎮 Players ({allPlayers.length})
        </button>
        <button 
          className={`tab ${activeTab === "quests" ? "active" : ""}`}
          onClick={() => setActiveTab("quests")}
          data-testid="quests-tab"
        >
          📜 Quests ({quests.length})
        </button>
        <button 
          className={`tab ${activeTab === "world" ? "active" : ""}`}
          onClick={() => setActiveTab("world")}
          data-testid="world-tab"
        >
          🌍 World {simulationRunning && <span className="running-indicator">●</span>}
        </button>
        <button 
          className={`tab ${activeTab === "territory" ? "active" : ""}`}
          onClick={() => setActiveTab("territory")}
          data-testid="territory-tab"
        >
          🗺️ Territory
        </button>
      </div>

      <div className="main-content">
        {/* CHAT TAB */}
        {activeTab === "chat" && (
          <>
            <aside className="sidebar">
              {/* Player Identity Section */}
              <div className="player-identity" data-testid="player-identity">
                <h3>🎮 Your Identity</h3>
                <div className="form-group-inline">
                  <label>ID:</label>
                  <input
                    type="text"
                    value={playerId}
                    onChange={(e) => setPlayerId(e.target.value)}
                    className="text-input-sm"
                    placeholder="player_001"
                  />
                </div>
                <div className="form-group-inline">
                  <label>Name:</label>
                  <input
                    type="text"
                    value={playerName}
                    onChange={(e) => setPlayerName(e.target.value)}
                    className="text-input-sm"
                    placeholder="Traveler"
                  />
                </div>
                {playerInfo && (
                  <div className="player-stats">
                    <div className="stat-row">
                      <span>Total Interactions:</span>
                      <strong>{playerInfo.total_interactions}</strong>
                    </div>
                    <div className="stat-row">
                      <span>Global Reputation:</span>
                      <strong className={playerInfo.global_reputation > 0 ? 'positive' : playerInfo.global_reputation < 0 ? 'negative' : ''}>
                        {(playerInfo.global_reputation * 100).toFixed(0)}%
                      </strong>
                    </div>
                  </div>
                )}
              </div>

              <div className="npc-selector">
                <h3>Select NPC</h3>
                <div className="npc-buttons">
                  <button
                    className={`npc-btn ${selectedNPC === "vera" ? "active" : ""}`}
                    onClick={() => switchNPC("vera")}
                  >
                    Vera (Gatekeeper)
                  </button>
                  <button
                    className={`npc-btn ${selectedNPC === "guard" ? "active" : ""}`}
                    onClick={() => switchNPC("guard")}
                  >
                    Guard (Protector)
                  </button>
                  <button
                    className={`npc-btn ${selectedNPC === "merchant" ? "active" : ""}`}
                    onClick={() => switchNPC("merchant")}
                  >
                    Merchant (Trader)
                  </button>
                </div>

                {!npcInitialized ? (
                  <button
                    className="init-btn"
                    onClick={initializeNPC}
                    disabled={loading}
                    data-testid="init-npc-btn"
                  >
                    {loading ? "Initializing..." : `Initialize ${selectedNPC.toUpperCase()}`}
                  </button>
                ) : (
                  <div className="npc-active-container">
                    <div className="npc-active">
                      <span className="status-indicator">●</span> Active
                    </div>
                    <div className="reputation-display" data-testid="reputation-display">
                      <span>Your Reputation:</span>
                      <strong className={currentReputation > 0 ? 'positive' : currentReputation < 0 ? 'negative' : ''}>
                        {(currentReputation * 100).toFixed(0)}%
                      </strong>
                    </div>
                  </div>
                )}
              </div>

              {npcStatus && (
                <div className="npc-status">
                  <h3>Status</h3>
                  <div className="status-item">
                    <strong>Mood:</strong> {npcStatus.emotional_state.mood}
                  </div>
                  <div className="status-item">
                    <strong>Arousal:</strong> {(npcStatus.emotional_state.arousal * 100).toFixed(0)}%
                  </div>
                  <div className="status-item">
                    <strong>Hunger:</strong> {(npcStatus.vitals.hunger * 100).toFixed(0)}%
                  </div>
                  <div className="status-item">
                    <strong>Fatigue:</strong> {(npcStatus.vitals.fatigue * 100).toFixed(0)}%
                  </div>

                  <h4 className="mt-4">Personality</h4>
                  {Object.entries(npcStatus.personality).map(([trait, value]) => (
                    <div key={trait} className="trait-bar">
                      <span className="trait-name">{trait}</span>
                      <div className="bar-container">
                        <div
                          className="bar-fill"
                          style={{ width: `${value * 100}%` }}
                        />
                      </div>
                      <span className="trait-value">{value.toFixed(2)}</span>
                    </div>
                  ))}
                </div>
              )}

              {/* Memory Log - What NPC remembers about you */}
              {npcInitialized && (
                <div className="memory-log" data-testid="memory-log">
                  <h3>🧠 Memory Log</h3>
                  <p className="memory-subtitle">What {selectedNPC} remembers about you</p>
                  
                  {npcMemories.length > 0 ? (
                    <div className="memory-list">
                      {npcMemories.map((memory, idx) => (
                        <div key={idx} className={`memory-item memory-${memory.category}`}>
                          <div className="memory-category">
                            {memory.category === 'family' && '👨‍👩‍👧'}
                            {memory.category === 'goal' && '🎯'}
                            {memory.category === 'fear' && '😰'}
                            {memory.category === 'event' && '📅'}
                            {memory.category === 'secret' && '🤫'}
                            {memory.category === 'preference' && '❤️'}
                            {memory.category === 'origin' && '🏠'}
                            {memory.category === 'profession' && '💼'}
                            <span className="category-label">{memory.category}</span>
                          </div>
                          <p className="memory-content">{memory.content}</p>
                          <div className="memory-meta">
                            <span className="emotional-weight">
                              Weight: {(memory.emotional_weight * 100).toFixed(0)}%
                            </span>
                            {memory.times_referenced > 0 && (
                              <span className="times-referenced">
                                Referenced {memory.times_referenced}x
                              </span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="no-memories">No memories yet. Share something personal!</p>
                  )}
                </div>
              )}
            </aside>

            <main className="chat-container">
              {!npcInitialized ? (
                <div className="welcome-screen">
                  <h2>Welcome to Porto Cobre Gates</h2>
                  <p>Select an NPC and initialize to begin interaction.</p>
                </div>
              ) : (
                <>
                  <div className="messages">
                    {messages.map((msg, idx) => (
                      <div key={idx} className={`message message-${msg.type}`}>
                        {msg.type === "system" && (
                          <div className="system-message">{msg.content}</div>
                        )}
                        {msg.type === "player" && (
                          <div className="player-message">
                            <strong>You:</strong> {msg.content}
                          </div>
                        )}
                        {msg.type === "npc_thought" && (
                          <div className="npc-thought">
                            <strong>🧠 Internal Thought:</strong>
                            <p>{msg.content}</p>
                          </div>
                        )}
                        {msg.type === "npc_dialogue" && (
                          <div className="npc-dialogue">
                            <strong>💬 {selectedNPC.toUpperCase()}:</strong>
                            <p>{msg.content}</p>
                            <div className="npc-meta">
                              <span>Mood: {msg.mood}</span>
                              <span>Intent: {msg.intent}</span>
                              {msg.reputationChange && (
                                <span className="reputation-change">{msg.reputationChange}</span>
                              )}
                              {msg.memoryIndicator && (
                                <span className="memory-indicator" title="Memories recalled">{msg.memoryIndicator}</span>
                              )}
                              {msg.gossipIndicator && (
                                <span className="gossip-indicator" title="Heard from other NPCs">{msg.gossipIndicator}</span>
                              )}
                            </div>
                          </div>
                        )}
                        {msg.type === "error" && (
                          <div className="error-message">{msg.content}</div>
                        )}
                      </div>
                    ))}
                    <div ref={messagesEndRef} />
                  </div>

                  <div className="input-area">
                    <textarea
                      className="action-input"
                      value={inputValue}
                      onChange={(e) => setInputValue(e.target.value)}
                      onKeyPress={handleKeyPress}
                      placeholder="Type your action..."
                      disabled={loading}
                      rows={2}
                    />
                    <button
                      className="send-btn"
                      onClick={sendAction}
                      disabled={loading || !inputValue.trim()}
                    >
                      {loading ? "Processing..." : "Send Action"}
                    </button>
                  </div>
                </>
              )}
            </main>
          </>
        )}

        {/* GENERATE NPCs TAB */}
        {activeTab === "generate" && (
          <div className="generate-container">
            <div className="generate-section">
              <h2>✨ Generate Random NPC</h2>
              <p>Create a unique NPC with auto-generated personality</p>
              
              <div className="form-group">
                <label>Role Type:</label>
                <select 
                  value={randomNPCRole} 
                  onChange={(e) => setRandomNPCRole(e.target.value)}
                  className="select-input"
                >
                  <option value="gatekeeper">Gatekeeper</option>
                  <option value="guard">Guard</option>
                  <option value="merchant">Merchant</option>
                  <option value="civilian">Civilian</option>
                  <option value="scholar">Scholar</option>
                  <option value="warrior">Warrior</option>
                </select>
              </div>

              <button 
                className="generate-btn"
                onClick={generateRandomNPC}
                disabled={loading}
              >
                {loading ? "Generating..." : "🎲 Generate Random NPC"}
              </button>
            </div>

            <div className="generate-section">
              <h2>🎨 Create Custom NPC</h2>
              <p>Full control over personality and attributes</p>

              <div className="form-grid">
                <div className="form-group">
                  <label>Name:</label>
                  <input
                    type="text"
                    value={customNPCData.name}
                    onChange={(e) => setCustomNPCData({...customNPCData, name: e.target.value})}
                    placeholder="Shadow"
                    className="text-input"
                  />
                </div>

                <div className="form-group">
                  <label>Role:</label>
                  <input
                    type="text"
                    value={customNPCData.role}
                    onChange={(e) => setCustomNPCData({...customNPCData, role: e.target.value})}
                    placeholder="Information Broker"
                    className="text-input"
                  />
                </div>

                <div className="form-group">
                  <label>Location:</label>
                  <input
                    type="text"
                    value={customNPCData.location}
                    onChange={(e) => setCustomNPCData({...customNPCData, location: e.target.value})}
                    placeholder="Dark Alley"
                    className="text-input"
                  />
                </div>

                <div className="form-group">
                  <label>Faction:</label>
                  <select
                    value={customNPCData.faction}
                    onChange={(e) => setCustomNPCData({...customNPCData, faction: e.target.value})}
                    className="select-input"
                  >
                    <option value="guards">Guards</option>
                    <option value="traders">Traders</option>
                    <option value="citizens">Citizens</option>
                    <option value="independents">Independents</option>
                  </select>
                </div>
              </div>

              <div className="form-group">
                <label>Backstory:</label>
                <textarea
                  value={customNPCData.backstory}
                  onChange={(e) => setCustomNPCData({...customNPCData, backstory: e.target.value})}
                  placeholder="A mysterious figure who deals in secrets..."
                  className="textarea-input"
                  rows={3}
                />
              </div>

              <div className="form-group">
                <label>Dialogue Style:</label>
                <input
                  type="text"
                  value={customNPCData.dialogue_style}
                  onChange={(e) => setCustomNPCData({...customNPCData, dialogue_style: e.target.value})}
                  placeholder="Cryptic, speaks in riddles"
                  className="text-input"
                />
              </div>

              <h3 className="personality-heading">Personality Traits</h3>
              <div className="sliders-grid">
                {["curiosity", "empathy", "risk_tolerance", "aggression", "discipline", "romanticism", "opportunism", "paranoia"].map(trait => (
                  <div key={trait} className="slider-group">
                    <label>{trait.charAt(0).toUpperCase() + trait.slice(1).replace("_", " ")}:</label>
                    <input
                      type="range"
                      min="0"
                      max="1"
                      step="0.01"
                      value={customNPCData[trait]}
                      onChange={(e) => setCustomNPCData({...customNPCData, [trait]: parseFloat(e.target.value)})}
                      className="slider"
                    />
                    <span className="slider-value">{customNPCData[trait].toFixed(2)}</span>
                  </div>
                ))}
              </div>

              <button 
                className="generate-btn"
                onClick={createCustomNPC}
                disabled={loading || !customNPCData.name || !customNPCData.role}
              >
                {loading ? "Creating..." : "🎨 Create Custom NPC"}
              </button>
            </div>
          </div>
        )}

        {/* ALL NPCs TAB */}
        {activeTab === "npcs" && (
          <div className="npcs-grid-container">
            <div className="npcs-header">
              <h2>👥 Active NPCs ({activeNPCs.length})</h2>
              <button className="refresh-btn" onClick={fetchAllNPCs}>
                🔄 Refresh
              </button>
            </div>

            <div className="npcs-grid">
              {activeNPCs.map((npc) => (
                <div key={npc.npc_id} className="npc-card">
                  <div className="npc-card-header">
                    <h3>{npc.npc_id}</h3>
                    <span className={`mood-badge mood-${npc.mood.toLowerCase()}`}>
                      {npc.mood}
                    </span>
                  </div>
                  <p className="npc-role">{npc.role}</p>
                  <p className="npc-location">📍 {npc.location}</p>
                  
                  <div className="npc-card-actions">
                    <button 
                      className="card-btn"
                      onClick={() => {
                        switchNPC(npc.npc_id);
                        setActiveTab("chat");
                      }}
                    >
                      💬 Chat
                    </button>
                    <button 
                      className="card-btn"
                      onClick={() => generateQuestForNPC(npc.npc_id)}
                    >
                      📜 Quest
                    </button>
                  </div>
                </div>
              ))}
              
              {activeNPCs.length === 0 && (
                <div className="empty-state">
                  <p>No NPCs active yet.</p>
                  <p>Go to &quot;Generate NPCs&quot; tab to create some!</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* QUESTS TAB */}
        {activeTab === "quests" && (
          <div className="quests-container">
            <div className="quests-header">
              <h2>📜 Available Quests ({quests.length})</h2>
              <button className="refresh-btn" onClick={fetchQuests}>
                🔄 Refresh
              </button>
            </div>

            <div className="quests-list">
              {quests.map((quest) => (
                <div key={quest.quest_id} className="quest-card">
                  <div className="quest-header">
                    <h3>{quest.title}</h3>
                    <span className={`difficulty-badge difficulty-${Math.floor(quest.difficulty * 3)}`}>
                      {quest.difficulty < 0.4 ? "Easy" : quest.difficulty < 0.7 ? "Medium" : "Hard"}
                    </span>
                  </div>
                  <p className="quest-giver">Quest Giver: <strong>{quest.quest_giver}</strong></p>
                  <p className="quest-type">Type: {quest.quest_type}</p>
                  <p className="quest-description">{quest.description}</p>
                  {quest.reward && (
                    <div className="quest-reward">
                      <strong>Reward:</strong> {quest.reward.type} (+{quest.reward.value})
                    </div>
                  )}
                </div>
              ))}

              {quests.length === 0 && (
                <div className="empty-state">
                  <p>No quests available.</p>
                  <p>Go to &quot;All NPCs&quot; tab and click &quot;Quest&quot; on any NPC to generate one!</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* WORLD SIMULATION TAB */}
        {activeTab === "world" && (
          <div className="world-container" data-testid="world-tab-content">
            <div className="world-header">
              <h2>🌍 World Simulation</h2>
              <div className={`simulation-status ${simulationRunning ? 'running' : 'stopped'}`}>
                {simulationRunning ? '● RUNNING' : '○ STOPPED'}
              </div>
            </div>

            <div className="world-grid">
              {/* Control Panel */}
              <div className="world-controls" data-testid="world-controls">
                <h3>⚙️ Simulation Controls</h3>
                
                {worldStatus && (
                  <div className="world-clock">
                    <span className="clock-label">World Time:</span>
                    <span className="clock-time">{worldStatus.world_time}</span>
                  </div>
                )}

                <div className="time-scale-control">
                  <label>Time Scale: {timeScale}x</label>
                  <input
                    type="range"
                    min="1"
                    max="100"
                    value={timeScale}
                    onChange={(e) => setTimeScale(parseInt(e.target.value))}
                    className="time-slider"
                    disabled={simulationRunning}
                  />
                  <div className="scale-labels">
                    <span>1x (Real-time)</span>
                    <span>100x (Fast)</span>
                  </div>
                </div>

                <div className="control-buttons">
                  {!simulationRunning ? (
                    <button 
                      className="control-btn start-btn"
                      onClick={startSimulation}
                      disabled={loading}
                      data-testid="start-simulation-btn"
                    >
                      ▶ Start Simulation
                    </button>
                  ) : (
                    <button 
                      className="control-btn stop-btn"
                      onClick={stopSimulation}
                      disabled={loading}
                      data-testid="stop-simulation-btn"
                    >
                      ⏹ Stop Simulation
                    </button>
                  )}
                  <button 
                    className="control-btn tick-btn"
                    onClick={manualTick}
                    disabled={loading}
                    data-testid="manual-tick-btn"
                  >
                    ⏭ Manual Tick
                  </button>
                  <button 
                    className="control-btn refresh-btn"
                    onClick={() => { fetchWorldStatus(); fetchWorldEvents(); }}
                  >
                    🔄 Refresh
                  </button>
                </div>
              </div>

              {/* Stats Panel */}
              <div className="world-stats" data-testid="world-stats">
                <h3>📊 Simulation Stats</h3>
                {worldStatus && worldStatus.stats ? (
                  <div className="stats-grid">
                    <div className="stat-box">
                      <span className="stat-value">{worldStatus.stats.total_ticks}</span>
                      <span className="stat-label">Total Ticks</span>
                    </div>
                    <div className="stat-box">
                      <span className="stat-value">{worldStatus.stats.memories_decayed}</span>
                      <span className="stat-label">Memories Faded</span>
                    </div>
                    <div className="stat-box">
                      <span className="stat-value">{worldStatus.stats.gossip_events}</span>
                      <span className="stat-label">Gossip Events</span>
                    </div>
                    <div className="stat-box">
                      <span className="stat-value">{worldStatus.stats.quests_generated}</span>
                      <span className="stat-label">Quests Created</span>
                    </div>
                    <div className="stat-box">
                      <span className="stat-value">{worldStatus.stats.quests_expired}</span>
                      <span className="stat-label">Quests Expired</span>
                    </div>
                  </div>
                ) : (
                  <p className="no-data">No simulation data yet</p>
                )}

                <h4>Active NPCs</h4>
                <div className="active-npcs-list">
                  {worldStatus && worldStatus.active_npcs && worldStatus.active_npcs.length > 0 ? (
                    worldStatus.active_npcs.map((npc) => (
                      <span key={npc} className="active-npc-badge">{npc}</span>
                    ))
                  ) : (
                    <p className="no-data">No NPCs in simulation</p>
                  )}
                </div>
              </div>

              {/* Event Feed */}
              <div className="world-events" data-testid="world-events">
                <h3>📜 Event Feed</h3>
                <div className="events-feed">
                  {worldEvents.length > 0 ? (
                    worldEvents.slice().reverse().map((event, idx) => (
                      <div key={idx} className="event-item">
                        <span className="event-time">[{event.time}]</span>
                        <span className="event-message">{event.message}</span>
                      </div>
                    ))
                  ) : (
                    <p className="no-data">No events yet. Start the simulation!</p>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TERRITORY & FACTIONS TAB */}
        {activeTab === "territory" && (
          <div className="factions-container" data-testid="factions-tab-content">
            <div className="factions-header">
              <h2>🏰 Factions & Territories</h2>
              <button className="refresh-btn" onClick={() => { fetchFactions(); fetchTerritories(); fetchTerritoryControl(); fetchFactionEvents(); fetchBattleHistory(); fetchTradeRoutes(); }}>
                🔄 Refresh All
              </button>
            </div>

            <div className="factions-grid">
              {/* Faction Cards */}
              <div className="faction-overview-section" data-testid="faction-overview">
                <h3>⚔️ Factions</h3>
                <div className="faction-cards">
                  {factionDetails ? Object.entries(factionDetails).map(([factionId, data]) => (
                    <div key={factionId} className={`faction-card-enhanced faction-${factionId}`} data-testid={`faction-card-${factionId}`}>
                      <div className="faction-card-header">
                        <span className="faction-icon">
                          {factionId === 'guards' && '🛡️'}
                          {factionId === 'traders' && '💰'}
                          {factionId === 'citizens' && '🏠'}
                          {factionId === 'outcasts' && '🗡️'}
                        </span>
                        <h4>{data.name || factionId.toUpperCase()}</h4>
                      </div>
                      <p className="faction-description">{data.description}</p>
                      {data.values && (
                        <div className="faction-values">
                          {data.values.map((v, i) => (
                            <span key={i} className="value-tag">{v}</span>
                          ))}
                        </div>
                      )}
                      {data.relations && (
                        <div className="faction-relations-mini">
                          <span className="relations-label">Relations:</span>
                          {Object.entries(data.relations).map(([otherId, rel]) => (
                            <span key={otherId} className={`relation-badge relation-${rel.type}`} title={`${rel.score.toFixed(2)}`}>
                              {otherId}: {rel.type}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  )) : (
                    <p className="no-data">Loading factions...</p>
                  )}
                </div>
              </div>

              {/* Territory Control */}
              <div className="territory-control-section" data-testid="territory-control">
                <h3>🗺️ Territory Control</h3>
                {territoryControl ? (
                  <div className="territory-grid">
                    {Object.entries(territoryControl).map(([territoryId, data]) => (
                      <div key={territoryId} className={`territory-card territory-${data.controlling_faction}`} data-testid={`territory-${territoryId}`}>
                        <div className="territory-header">
                          <span className="territory-name">{data.name || territoryId}</span>
                          <span className={`controller-badge controller-${data.controlling_faction}`}>
                            {data.controlling_faction}
                          </span>
                        </div>
                        <div className="territory-stats">
                          <div className="territory-stat">
                            <span>Control:</span>
                            <div className="control-bar">
                              <div className="control-fill" style={{ width: `${data.control_strength * 100}%` }} />
                            </div>
                            <span className="control-value">{(data.control_strength * 100).toFixed(0)}%</span>
                          </div>
                          <div className="territory-stat">
                            <span>Strategic Value:</span>
                            <strong className="strategic-value">{(data.strategic_value * 100).toFixed(0)}%</strong>
                          </div>
                        </div>
                        <button 
                          className="attack-btn"
                          onClick={() => initiateBattle(territoryId)}
                          title="Start territorial battle"
                        >
                          ⚔️ Attack
                        </button>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="no-data">Loading territories...</p>
                )}
              </div>

              {/* Trade Routes */}
              <div className="trade-routes-section" data-testid="trade-routes">
                <h3>🛒 Trade Routes</h3>
                <div className="trade-routes-controls">
                  <button className="control-btn" onClick={establishNewRoute} disabled={activeNPCs.length < 2}>
                    + New Route
                  </button>
                </div>
                {tradeRoutes && tradeRoutes.length > 0 ? (
                  <div className="trade-routes-list">
                    {tradeRoutes.map((route) => (
                      <div key={route.route_id} className={`trade-route-card route-${route.status}`}>
                        <div className="route-header">
                          <span className="route-path">{route.from_location} → {route.to_location}</span>
                          <span className={`route-status status-${route.status}`}>{route.status}</span>
                        </div>
                        <div className="route-details">
                          <span>NPCs: {route.from_npc} ↔ {route.to_npc}</span>
                          <span>Goods: {route.goods?.join(", ") || "Mixed"}</span>
                          <span>Profit: {(route.profit_margin * 100).toFixed(0)}%</span>
                          <span>Risk: {(route.risk_level * 100).toFixed(0)}%</span>
                          <span>Trades: {route.total_trades}</span>
                        </div>
                        <div className="route-actions">
                          {route.status === "active" && (
                            <>
                              <button className="route-btn execute" onClick={() => executeTrade(route.route_id)}>Execute Trade</button>
                              <button className="route-btn disrupt" onClick={() => disruptRoute(route.route_id)}>Disrupt</button>
                            </>
                          )}
                          {route.status === "disrupted" && (
                            <button className="route-btn restore" onClick={() => restoreRoute(route.route_id)}>Restore</button>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="no-data">No trade routes established. Create one!</p>
                )}
              </div>

              {/* Battle History */}
              <div className="battle-history-section" data-testid="battle-history">
                <h3>⚔️ Battle History</h3>
                {battleHistory && battleHistory.length > 0 ? (
                  <div className="battle-list">
                    {battleHistory.map((battle) => (
                      <div key={battle.battle_id} className={`battle-card battle-${battle.status}`}>
                        <div className="battle-header">
                          <span className="battle-territory">{battle.territory}</span>
                          <span className={`battle-status status-${battle.status}`}>
                            {battle.status === 'attacker_won' ? '🏆 Attacker Won' : 
                             battle.status === 'defender_won' ? '🛡️ Defender Won' : 
                             battle.status === 'in_progress' ? '⚔️ In Progress' : battle.status}
                          </span>
                        </div>
                        <div className="battle-factions">
                          <span className={`battle-faction attacker faction-${battle.attacker_faction}`}>
                            {battle.attacker_faction} ({(battle.attacker_strength * 100).toFixed(0)}%)
                          </span>
                          <span className="vs">vs</span>
                          <span className={`battle-faction defender faction-${battle.defender_faction}`}>
                            {battle.defender_faction} ({(battle.defender_strength * 100).toFixed(0)}%)
                          </span>
                        </div>
                        {battle.casualties && (
                          <div className="battle-casualties">
                            Casualties: Attacker {battle.casualties.attacker} | Defender {battle.casualties.defender}
                          </div>
                        )}
                        {battle.status === 'in_progress' && (
                          <button className="resolve-btn" onClick={() => resolveBattle(battle.battle_id)}>
                            Resolve Battle
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="no-data">No battles fought yet</p>
                )}
              </div>

              {/* Faction Events */}
              <div className="faction-events-section" data-testid="faction-events">
                <h3>📜 Faction Events</h3>
                <div className="event-controls">
                  <button className="trigger-event-btn" onClick={() => triggerFactionEvent("skirmish")}>
                    Trigger Skirmish
                  </button>
                  <button className="trigger-event-btn" onClick={() => triggerFactionEvent("trade_deal")}>
                    Trade Deal
                  </button>
                </div>
                {factionEvents && factionEvents.length > 0 ? (
                  <div className="faction-events-list">
                    {factionEvents.map((event, idx) => (
                      <div key={event.event_id || idx} className={`faction-event event-${event.event_type}`}>
                        <span className="event-icon">
                          {event.event_type === 'skirmish' && '⚔️'}
                          {event.event_type === 'trade_deal' && '🤝'}
                          {event.event_type === 'betrayal' && '🗡️'}
                          {event.event_type === 'alliance_formed' && '🤝'}
                        </span>
                        <div className="event-content">
                          <span className="event-type">{event.event_type?.replace('_', ' ').toUpperCase()}</span>
                          <span className="event-factions">
                            {event.factions_involved?.join(" vs ") || "Unknown factions"}
                          </span>
                          <span className="event-description">{event.description}</span>
                          {event.impact?.relation_change && (
                            <span className={`event-impact ${event.impact.relation_change > 0 ? 'positive' : 'negative'}`}>
                              Relations: {event.impact.relation_change > 0 ? '+' : ''}{event.impact.relation_change.toFixed(1)}
                            </span>
                          )}
                        </div>
                        <span className="event-time">{event.timestamp ? new Date(event.timestamp).toLocaleTimeString() : ''}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="no-data">No faction events yet</p>
                )}
              </div>
            </div>
          </div>
        )}

        {/* PLAYERS TAB */}
        {activeTab === "players" && (
          <div className="players-container" data-testid="players-tab-content">
            <div className="players-header">
              <h2>🎮 Player Tracking ({allPlayers.length})</h2>
              <button className="refresh-btn" onClick={fetchAllPlayers}>
                🔄 Refresh
              </button>
            </div>

            <div className="players-grid">
              {allPlayers.map((player) => (
                <div key={player.player_id} className="player-card" data-testid={`player-card-${player.player_id}`}>
                  <div className="player-card-header">
                    <h3>{player.player_name}</h3>
                    <span className={`reputation-badge ${player.global_reputation > 0.3 ? 'positive' : player.global_reputation < -0.3 ? 'negative' : 'neutral'}`}>
                      {player.global_reputation > 0.3 ? '😊 Trusted' : player.global_reputation < -0.3 ? '😠 Distrusted' : '😐 Neutral'}
                    </span>
                  </div>
                  <p className="player-id">ID: {player.player_id}</p>
                  <div className="player-stats-card">
                    <div className="stat-item">
                      <span>Interactions:</span>
                      <strong>{player.total_interactions}</strong>
                    </div>
                    <div className="stat-item">
                      <span>Global Rep:</span>
                      <strong className={player.global_reputation > 0 ? 'positive' : player.global_reputation < 0 ? 'negative' : ''}>
                        {(player.global_reputation * 100).toFixed(0)}%
                      </strong>
                    </div>
                  </div>
                  <button 
                    className="card-btn view-details-btn"
                    onClick={async () => {
                      setPlayerId(player.player_id);
                      setPlayerName(player.player_name);
                      await fetchPlayerInfo();
                      setActiveTab("chat");
                    }}
                  >
                    👤 Play as {player.player_name}
                  </button>
                </div>
              ))}

              {allPlayers.length === 0 && (
                <div className="empty-state">
                  <p>No players tracked yet.</p>
                  <p>Start chatting with NPCs to create player records!</p>
                </div>
              )}
            </div>

            {/* Current Player Details */}
            {playerInfo && (
              <div className="current-player-details" data-testid="current-player-details">
                <h3>📊 Your Player Details ({playerInfo.player_name})</h3>
                <div className="player-detail-grid">
                  <div className="detail-section">
                    <h4>NPC Reputations</h4>
                    {Object.entries(playerInfo.npc_reputations || {}).length > 0 ? (
                      Object.entries(playerInfo.npc_reputations).map(([npcId, rep]) => (
                        <div key={npcId} className="reputation-row">
                          <span className="npc-name">{npcId}</span>
                          <div className="rep-bar-container">
                            <div 
                              className={`rep-bar ${rep > 0 ? 'positive' : rep < 0 ? 'negative' : 'neutral'}`}
                              style={{ width: `${Math.abs(rep) * 100}%`, marginLeft: rep < 0 ? 'auto' : '50%' }}
                            />
                          </div>
                          <span className={`rep-value ${rep > 0 ? 'positive' : rep < 0 ? 'negative' : ''}`}>
                            {(rep * 100).toFixed(0)}%
                          </span>
                        </div>
                      ))
                    ) : (
                      <p className="no-data">No reputation data yet</p>
                    )}
                  </div>

                  <div className="detail-section">
                    <h4>Rumors About You</h4>
                    {playerInfo.rumors && playerInfo.rumors.length > 0 ? (
                      playerInfo.rumors.map((rumor, idx) => (
                        <div key={idx} className="rumor-item">
                          <p className="rumor-content">&quot;{rumor.content}&quot;</p>
                          <span className="rumor-source">— Spread by {rumor.created_by} ({rumor.spread_count} NPCs know)</span>
                        </div>
                      ))
                    ) : (
                      <p className="no-data">No rumors circulating about you</p>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
