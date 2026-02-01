import React, { useState, useEffect, useRef } from "react";
import axios from "axios";
import "./App.css";

// Import Components
import ChatPanel from "./components/ChatPanel";
import WorldControls from "./components/WorldControls";
import FactionUI from "./components/FactionUI";
import PlayersTab from "./components/PlayersTab";
import NPCsTab from "./components/NPCsTab";
import AuthPanel from "./components/AuthPanel";
import LoginPage from "./components/LoginPage";
import GroupConversation from "./components/GroupConversation";

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

  // Authentication state
  const [currentUser, setCurrentUser] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);

  // Player state (now linked to auth)
  const [playerId, setPlayerId] = useState("guest_player");
  const [playerName, setPlayerName] = useState("Guest");
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

  // Check for existing auth on load
  useEffect(() => {
    const checkAuth = async () => {
      const token = localStorage.getItem("auth_token");
      const userData = localStorage.getItem("user_data");
      
      if (token && userData) {
        try {
          // Verify token is still valid
          const response = await axios.post(`${API}/auth/verify`, {}, {
            headers: { Authorization: `Bearer ${token}` }
          });
          
          if (response.data.valid) {
            const user = JSON.parse(userData);
            setCurrentUser(user);
            setPlayerId(user.user_id);
            setPlayerName(user.player_name);
          } else {
            // Token invalid, clear storage
            localStorage.removeItem("auth_token");
            localStorage.removeItem("user_data");
          }
        } catch (err) {
          console.error("Auth check failed:", err);
        }
      }
      setAuthLoading(false);
    };
    
    checkAuth();
  }, []);

  // Handle login
  const handleLogin = (userData) => {
    setCurrentUser({
      user_id: userData.user_id,
      username: userData.username,
      player_name: userData.player_name
    });
    setPlayerId(userData.user_id);
    setPlayerName(userData.player_name);
    
    // Add welcome message
    setMessages(prev => [...prev, {
      type: "system",
      text: `Welcome, ${userData.player_name}! You are now logged in.`
    }]);
  };

  // Handle logout
  const handleLogout = () => {
    // Clear auth data from localStorage
    localStorage.removeItem("auth_token");
    localStorage.removeItem("user_data");
    
    setCurrentUser(null);
    setPlayerId("guest_player");
    setPlayerName("Guest");
    
    setMessages(prev => [...prev, {
      type: "system",
      text: "You have been logged out. Playing as Guest."
    }]);
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

  useEffect(() => {
    if (activeTab === "world" && simulationRunning) {
      const interval = setInterval(() => {
        fetchWorldStatus();
        fetchWorldEvents();
      }, 5000);
      return () => clearInterval(interval);
    }
  }, [activeTab, simulationRunning]);

  // Initialize NPC when selected
  const initializeNPC = async (npcId = selectedNPC) => {
    try {
      setLoading(true);
      const response = await axios.post(`${API}/npc/init`, {
        npc_id: npcId,
      });

      if (response.data.status === "initialized" || response.data.status === "already_exists") {
        if (npcId === selectedNPC) {
          setNpcInitialized(true);
          await fetchNPCStatus();
          
          // Handle both new init and already exists cases
          const role = response.data.role || "NPC";
          const location = response.data.location || "Porto Cobre";
          const statusText = response.data.status === "initialized" 
            ? `${npcId.toUpperCase()} initialized. ${role} at ${location}`
            : `${npcId.toUpperCase()} reconnected. Ready to interact.`;
          
          setMessages([{
            type: "system",
            content: statusText,
          }]);
        }
        await fetchAllNPCs();
      }
    } catch (error) {
      console.error("Error initializing NPC:", error);
      setMessages([{
        type: "error",
        content: `Failed to initialize ${npcId}: ${error.response?.data?.detail || error.message}`,
      }]);
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
      const userMessage = { type: "player", content: inputValue };
      setMessages((prev) => [...prev, userMessage]);
      setInputValue("");

      const response = await axios.post(`${API}/npc/action`, {
        npc_id: selectedNPC,
        action: inputValue,
        player_id: playerId,
        player_name: playerName,
      });

      const { cognitive_frame, limbic_state, reputation, topics_extracted, topics_remembered, heard_from_others } = response.data;

      if (reputation !== undefined) {
        setCurrentReputation(reputation);
      }

      if (topics_extracted > 0) {
        setTopicsExtracted(prev => prev + topics_extracted);
      }

      const reputationChange = cognitive_frame.trust_mod || 0;
      const reputationIndicator = reputationChange > 0 ? `📈 +${reputationChange.toFixed(2)}` : 
                                   reputationChange < 0 ? `📉 ${reputationChange.toFixed(2)}` : '';
      const memoryIndicator = topics_remembered > 0 ? `🧠 ${topics_remembered}` : '';
      const gossipIndicator = heard_from_others > 0;

      setMessages((prev) => [
        ...prev,
        {
          type: "npc",
          content: cognitive_frame.dialogue || "[Remains silent]",
          inner_thoughts: cognitive_frame.internal_reflection,
          emotional_shift: cognitive_frame.emotional_state,
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
        { type: "error", content: `Error: ${error.response?.data?.detail || error.message}` },
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

  const switchNPC = (npcId) => {
    setSelectedNPC(npcId);
    setNpcInitialized(false);
    setMessages([]);
    setNpcStatus(null);
  };

  const switchPlayer = (newPlayerId) => {
    setPlayerId(newPlayerId);
    fetchPlayerInfo();
  };

  const acceptQuest = async (questId) => {
    try {
      await axios.post(`${API}/quest/accept/${questId}`);
      alert("Quest accepted!");
      await fetchQuests();
    } catch (error) {
      alert(`Error: ${error.response?.data?.detail || error.message}`);
    }
  };

  // ========================================================================
  // SECURITY: Show login page if not authenticated
  // ========================================================================
  if (authLoading) {
    return (
      <div className="loading-screen">
        <div className="loading-spinner"></div>
        <p>Loading...</p>
      </div>
    );
  }

  if (!currentUser) {
    return <LoginPage API={API} onLogin={handleLogin} />;
  }

  // ========================================================================
  // AUTHENTICATED VIEW - Main Application
  // ========================================================================
  return (
    <div className="app-container" data-testid="npc-system-app">
      <header className="header">
        <div className="header-content">
          <img src="/assets/logo.jpg" alt="Fractured Survival" className="header-logo" />
          <div className="header-text">
            <h1 data-testid="app-title">NPC Intelligence Dashboard</h1>
            <p className="subtitle">Command Your AI Survivors</p>
          </div>
        </div>
        <div className="header-user">
          <span className="user-greeting">Welcome, <strong>{currentUser.player_name}</strong></span>
          <button className="logout-btn-header" onClick={handleLogout}>
            Logout
          </button>
        </div>
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
          className={`tab ${activeTab === "group" ? "active" : ""}`}
          onClick={() => setActiveTab("group")}
          data-testid="group-tab"
        >
          👥 Group Chat
        </button>
        <button 
          className={`tab ${activeTab === "generate" ? "active" : ""}`}
          onClick={() => setActiveTab("generate")}
          data-testid="generate-tab"
        >
          ✨ Generate NPC
        </button>
        <button 
          className={`tab ${activeTab === "npcs" ? "active" : ""}`}
          onClick={() => setActiveTab("npcs")}
          data-testid="npcs-tab"
        >
          👥 NPCs ({activeNPCs.length})
        </button>
        <button 
          className={`tab ${activeTab === "players" ? "active" : ""}`}
          onClick={() => setActiveTab("players")}
          data-testid="players-tab"
        >
          🎮 Players
        </button>
        <button 
          className={`tab ${activeTab === "quests" ? "active" : ""}`}
          onClick={() => setActiveTab("quests")}
          data-testid="quests-tab"
        >
          📜 Quests
        </button>
        <button 
          className={`tab ${activeTab === "world" ? "active" : ""}`}
          onClick={() => setActiveTab("world")}
          data-testid="world-tab"
        >
          🌍 World
        </button>
        <button 
          className={`tab ${activeTab === "territory" ? "active" : ""}`}
          onClick={() => setActiveTab("territory")}
          data-testid="territory-tab"
        >
          🏰 Factions
        </button>
        <button 
          className={`tab ${activeTab === "account" ? "active" : ""}`}
          onClick={() => setActiveTab("account")}
          data-testid="account-tab"
        >
          👤 {currentUser ? currentUser.player_name : "Account"}
        </button>
      </div>

      <main className="main-content">
        {/* CHAT TAB */}
        {activeTab === "chat" && (
          <ChatPanel
            selectedNPC={selectedNPC}
            npcStatus={npcStatus}
            messages={messages}
            inputValue={inputValue}
            setInputValue={setInputValue}
            loading={loading}
            sendAction={sendAction}
            currentReputation={currentReputation}
            topicsExtracted={topicsExtracted}
            npcMemories={npcMemories}
            messagesEndRef={messagesEndRef}
            playerId={playerId}
            playerName={playerName}
            API={API}
          />
        )}

        {/* GROUP CHAT TAB */}
        {activeTab === "group" && (
          <div className="group-chat-container" data-testid="group-chat-content" style={{ height: "calc(100vh - 180px)" }}>
            <GroupConversation
              activeNPCs={activeNPCs}
              playerId={playerId}
              playerName={playerName}
            />
          </div>
        )}

        {/* GENERATE TAB */}
        {activeTab === "generate" && (
          <div className="generate-container" data-testid="generate-tab-content">
            <h2>✨ NPC Generator</h2>
            
            {/* Random Generation */}
            <div className="generate-section">
              <h3>🎲 Random NPC</h3>
              <div className="random-gen-controls">
                <select 
                  value={randomNPCRole} 
                  onChange={(e) => setRandomNPCRole(e.target.value)}
                  data-testid="role-select"
                >
                  <option value="merchant">Merchant</option>
                  <option value="guard">Guard</option>
                  <option value="beggar">Beggar</option>
                  <option value="noble">Noble</option>
                  <option value="scholar">Scholar</option>
                  <option value="priest">Priest</option>
                </select>
                <button 
                  onClick={generateRandomNPC} 
                  disabled={loading}
                  data-testid="generate-random-btn"
                >
                  Generate Random
                </button>
              </div>
            </div>

            {/* Custom NPC Creation */}
            <div className="generate-section">
              <h3>🎨 Custom NPC</h3>
              <div className="custom-npc-form">
                <div className="form-row">
                  <input
                    type="text"
                    placeholder="Name"
                    value={customNPCData.name}
                    onChange={(e) => setCustomNPCData({...customNPCData, name: e.target.value})}
                    data-testid="custom-name-input"
                  />
                  <input
                    type="text"
                    placeholder="Role"
                    value={customNPCData.role}
                    onChange={(e) => setCustomNPCData({...customNPCData, role: e.target.value})}
                    data-testid="custom-role-input"
                  />
                </div>
                <div className="form-row">
                  <input
                    type="text"
                    placeholder="Location"
                    value={customNPCData.location}
                    onChange={(e) => setCustomNPCData({...customNPCData, location: e.target.value})}
                  />
                  <select 
                    value={customNPCData.faction}
                    onChange={(e) => setCustomNPCData({...customNPCData, faction: e.target.value})}
                    data-testid="custom-faction-select"
                  >
                    <option value="citizens">Citizens</option>
                    <option value="guards">Guards</option>
                    <option value="traders">Traders</option>
                    <option value="outcasts">Outcasts</option>
                  </select>
                </div>
                <textarea
                  placeholder="Backstory"
                  value={customNPCData.backstory}
                  onChange={(e) => setCustomNPCData({...customNPCData, backstory: e.target.value})}
                  data-testid="custom-backstory-input"
                />
                <input
                  type="text"
                  placeholder="Dialogue Style (e.g., formal, casual, cryptic)"
                  value={customNPCData.dialogue_style}
                  onChange={(e) => setCustomNPCData({...customNPCData, dialogue_style: e.target.value})}
                />
                
                <h4>Personality Traits</h4>
                <div className="traits-grid">
                  {['curiosity', 'empathy', 'risk_tolerance', 'aggression', 'discipline', 'romanticism', 'opportunism', 'paranoia'].map(trait => (
                    <div key={trait} className="trait-slider">
                      <label>{trait.replace('_', ' ')}: {customNPCData[trait].toFixed(1)}</label>
                      <input
                        type="range"
                        min="0"
                        max="1"
                        step="0.1"
                        value={customNPCData[trait]}
                        onChange={(e) => setCustomNPCData({...customNPCData, [trait]: parseFloat(e.target.value)})}
                      />
                    </div>
                  ))}
                </div>
                
                <button 
                  onClick={createCustomNPC} 
                  disabled={loading || !customNPCData.name || !customNPCData.role}
                  data-testid="create-custom-btn"
                >
                  Create Custom NPC
                </button>
              </div>
            </div>
          </div>
        )}

        {/* NPCS TAB */}
        {activeTab === "npcs" && (
          <NPCsTab
            allNPCs={allNPCs}
            activeNPCs={activeNPCs}
            selectedNPC={selectedNPC}
            loading={loading}
            fetchAllNPCs={fetchAllNPCs}
            initializeNPC={initializeNPC}
            switchNPC={switchNPC}
            setActiveTab={setActiveTab}
          />
        )}

        {/* QUESTS TAB */}
        {activeTab === "quests" && (
          <div className="quests-container" data-testid="quests-tab-content">
            <div className="quests-header">
              <h2>📜 Available Quests ({quests.length})</h2>
              <button className="refresh-btn" onClick={fetchQuests}>🔄 Refresh</button>
            </div>
            <div className="quests-list">
              {quests && quests.length > 0 ? (
                quests.map((quest) => (
                  <div key={quest.id} className={`quest-card quest-${quest.type}`} data-testid={`quest-${quest.id}`}>
                    <div className="quest-header">
                      <h3>{quest.title}</h3>
                      <span className={`quest-type type-${quest.type}`}>{quest.type}</span>
                    </div>
                    <p className="quest-description">{quest.description}</p>
                    <div className="quest-details">
                      <span>Difficulty: {quest.difficulty}</span>
                      <span>From: {quest.generated_by_npc || "System"}</span>
                      <span>Status: {quest.status}</span>
                    </div>
                    {quest.rewards && (
                      <div className="quest-rewards">
                        Rewards: {quest.rewards.gold && `${quest.rewards.gold} gold`} 
                        {quest.rewards.reputation && ` +${quest.rewards.reputation} rep`}
                      </div>
                    )}
                    {quest.status === "available" && (
                      <button className="accept-btn" onClick={() => acceptQuest(quest.id)}>Accept</button>
                    )}
                  </div>
                ))
              ) : (
                <p className="no-data">No quests available. Interact with NPCs to generate quests!</p>
              )}
            </div>
          </div>
        )}

        {/* WORLD TAB */}
        {activeTab === "world" && (
          <WorldControls
            worldStatus={worldStatus}
            worldEvents={worldEvents}
            timeScale={timeScale}
            setTimeScale={setTimeScale}
            simulationRunning={simulationRunning}
            loading={loading}
            startSimulation={startSimulation}
            stopSimulation={stopSimulation}
            manualTick={manualTick}
            fetchWorldStatus={fetchWorldStatus}
            fetchWorldEvents={fetchWorldEvents}
          />
        )}

        {/* TERRITORY/FACTIONS TAB */}
        {activeTab === "territory" && (
          <FactionUI
            factionDetails={factionDetails}
            territoryControl={territoryControl}
            tradeRoutes={tradeRoutes}
            battleHistory={battleHistory}
            factionEvents={factionEvents}
            activeNPCs={activeNPCs}
            fetchFactions={fetchFactions}
            fetchTerritories={fetchTerritories}
            fetchTerritoryControl={fetchTerritoryControl}
            fetchFactionEvents={fetchFactionEvents}
            fetchBattleHistory={fetchBattleHistory}
            fetchTradeRoutes={fetchTradeRoutes}
            triggerFactionEvent={triggerFactionEvent}
            initiateBattle={initiateBattle}
            resolveBattle={resolveBattle}
            establishNewRoute={establishNewRoute}
            executeTrade={executeTrade}
            disruptRoute={disruptRoute}
            restoreRoute={restoreRoute}
          />
        )}

        {/* PLAYERS TAB */}
        {activeTab === "players" && (
          <PlayersTab
            allPlayers={allPlayers}
            playerInfo={playerInfo}
            playerId={playerId}
            setPlayerId={setPlayerId}
            playerName={playerName}
            setPlayerName={setPlayerName}
            fetchAllPlayers={fetchAllPlayers}
            fetchPlayerInfo={fetchPlayerInfo}
            switchPlayer={switchPlayer}
          />
        )}

        {/* ACCOUNT TAB */}
        {activeTab === "account" && (
          <div className="account-tab-content" data-testid="account-tab-content">
            <h2>Account Management</h2>
            <p className="account-description">
              {currentUser 
                ? "Manage your account settings and view your player profile."
                : "Login or register to save your progress and interact with NPCs."}
            </p>
            <AuthPanel 
              API={API} 
              onLogin={handleLogin}
              onLogout={handleLogout}
              currentUser={currentUser}
            />
            
            {currentUser && (
              <div className="account-details" data-testid="account-details">
                <h3>Account Details</h3>
                <div className="detail-row">
                  <span className="detail-label">User ID:</span>
                  <span className="detail-value">{currentUser.user_id}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-label">Username:</span>
                  <span className="detail-value">@{currentUser.username}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-label">Player Name:</span>
                  <span className="detail-value">{currentUser.player_name}</span>
                </div>
                
                <div className="unreal-integration-info">
                  <h4>🎮 Unreal Engine Integration</h4>
                  <p>To connect from Unreal Engine, use the following credentials:</p>
                  <div className="code-block">
                    <code>Player ID: {currentUser.user_id}</code>
                  </div>
                  <p className="hint">
                    Call <code>/api/auth/unreal/connect</code> with your player ID 
                    to authenticate from your game client.
                  </p>
                </div>
              </div>
            )}
          </div>
        )}
      </main>

      {/* NPC Quick Select */}
      <div className="npc-quick-select" data-testid="npc-quick-select">
        <span>Quick Select:</span>
        {activeNPCs.slice(0, 5).map((npc) => (
          <button
            key={npc.npc_id}
            className={`quick-npc ${selectedNPC === npc.npc_id ? 'active' : ''}`}
            onClick={() => { switchNPC(npc.npc_id); setActiveTab("chat"); }}
          >
            {npc.name || npc.npc_id}
          </button>
        ))}
        {activeNPCs.length === 0 && (
          <button onClick={() => initializeNPC("vera")}>Initialize Vera</button>
        )}
      </div>
    </div>
  );
}

export default App;
