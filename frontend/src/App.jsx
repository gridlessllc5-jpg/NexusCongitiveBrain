import React, { useState, useEffect, useRef } from "react";
import axios from "axios";
import "./styles/ScifiTheme.css";
import { 
  Terminal, 
  Activity, 
  Map, 
  Users, 
  Cpu, 
  Radio, 
  ShieldAlert, 
  Database,
  ScrollText
} from "lucide-react";

import ChatPanel from "./components/ChatPanel";
import WorldControls from "./components/WorldControls";
import FactionUI from "./components/FactionUI";
import PlayersTab from "./components/PlayersTab";
import NPCsTab from "./components/NPCsTab";
import QuestsTab from "./components/QuestsTab";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "http://localhost:8001";
const API = `${BACKEND_URL}/api`;

const POTENTIAL_NPCS = [
  { npc_id: "vera", name: "Vera", role: "Chief Security Officer", location: "Command Center", faction: "guards" },
  { npc_id: "elena", name: "Elena", role: "Merchant", location: "Porto Cobre Market", faction: "traders" },
  { npc_id: "marcus", name: "Marcus", role: "Blacksmith", location: "Porto Cobre Market", faction: "citizens" },
  { npc_id: "silas_black", name: "Silas Black", role: "Cunning Broker", location: "Market District", faction: "traders" },
  { npc_id: "guard", name: "Unit 734", role: "Security Guard", location: "Perimeter", faction: "guards" },
  { npc_id: "merchant", name: "Local Trader", role: "Vendor", location: "Trade Hub", faction: "traders" },
  { npc_id: "kai", name: "Kai", role: "Tech Specialist", location: "Engineering", faction: "citizens" },
  { npc_id: "nora_north", name: "Nora North", role: "Scout", location: "Outpost 3", faction: "citizens" }
];

function App() {
  const [activeTab, setActiveTab] = useState("chat");
  const [selectedNPC, setSelectedNPC] = useState("vera");
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState("");
  const [loading, setLoading] = useState(false);
  const [activeNPCs, setActiveNPCs] = useState([]);
  
  const [worldStatus, setWorldStatus] = useState(null);
  const [worldEvents, setWorldEvents] = useState([]);
  const [timeScale, setTimeScale] = useState(24);
  const [simulationRunning, setSimulationRunning] = useState(false);

  const [factionDetails, setFactionDetails] = useState(null);
  const [territoryControl, setTerritoryControl] = useState(null);
  const [factionEvents, setFactionEvents] = useState([]);
  const [battleHistory, setBattleHistory] = useState([]);
  const [tradeRoutes, setTradeRoutes] = useState([]);

  const [quests, setQuests] = useState([]);

  const [currentUser] = useState({
    user_id: "guest_player",
    username: "guest",
    player_name: "Admin Commander"
  });
  const [playerId] = useState("guest_player");
  const [playerInfo, setPlayerInfo] = useState(null);
  const [allPlayers, setAllPlayers] = useState([]);
  const [currentReputation, setCurrentReputation] = useState(0);

  const [npcStatus, setNpcStatus] = useState(null);
  const [npcMemories, setNpcMemories] = useState([]);

  const messagesEndRef = useRef(null);

  useEffect(() => {
    fetchAllNPCs();
    fetchWorldStatus();
    fetchPlayerInfo();
  }, []);

  useEffect(() => {
    if (activeTab === "world" || activeTab === "territory") {
      const interval = setInterval(() => {
        if (activeTab === "world") fetchWorldEvents();
        if (activeTab === "territory") fetchFactionEvents();
      }, 5000);
      return () => clearInterval(interval);
    }
  }, [activeTab]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    if (activeTab === "territory") {
      fetchFactions();
      fetchTerritories();
      fetchTerritoryControl();
      fetchTradeRoutes();
    } else if (activeTab === "players") {
      fetchAllPlayers();
    } else if (activeTab === "missions") {
      fetchQuests();
    } else if (activeTab === "agents") {
      fetchAllNPCs();
    }
  }, [activeTab]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const fetchAllNPCs = async () => {
    try {
      const response = await axios.get(`${API}/npc/list`);
      setActiveNPCs(response.data.npcs || []);
    } catch (e) {
      console.error("NPC List Error", e);
    }
  };

  const initializeNPC = async (id) => {
    try {
      setLoading(true);
      // Construct the persona file name logic if needed, 
      // but the backend default map handles common ones.
      // For specific new ones, we might need to update backend or pass file param.
      let personaFile = null;
      if (id === "elena") personaFile = "elena_v1.json";
      if (id === "marcus") personaFile = "marcus_v1.json";
      if (id === "silas_black") personaFile = "silas_black_v1.json";
      if (id === "nora_north") personaFile = "nora_north_v1.json";

      const payload = { npc_id: id };
      if (personaFile) payload.persona_file = personaFile;

      await axios.post(`${API}/npc/init`, payload);
      await fetchAllNPCs();
    } catch (e) { 
      console.error("Init Error", e); 
      // Force refresh anyway to see if it worked
      fetchAllNPCs();
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

  const fetchPlayerInfo = async () => {
    try {
      const response = await axios.get(`${API}/player/${playerId}`);
      setPlayerInfo(response.data);
      if (response.data.npc_reputations?.[selectedNPC]) {
        setCurrentReputation(response.data.npc_reputations[selectedNPC]);
      }
    } catch (e) { console.error(e); }
  };

  const fetchWorldStatus = async () => {
    try {
      const response = await axios.get(`${API}/world/status`);
      setWorldStatus(response.data);
      setSimulationRunning(response.data.is_running);
    } catch (e) { console.error(e); }
  };

  const fetchWorldEvents = async () => {
    try { 
      const response = await axios.get(`${API}/world/events?limit=20`);
      setWorldEvents(response.data.events || []);
    } catch (e) { console.error(e); }
  };

  const fetchQuests = async () => {
      try {
          const res = await axios.get(`${API}/quests`);
          setQuests(res.data.quests || []);
      } catch (e) {
          console.error("Fetch Quests Error", e);
          setQuests([{quest_id: "q1", title: "Scan Sector 7", difficulty: 0.3, quest_giver: "Vera", quest_type: "scout", description: "Locate resource cache in sector 7 ruins.", reward: {type: "credits", value: 500}}]);
      }
  };

  const fetchFactions = async () => {
      try {
        const response = await axios.get(`${API}/factions/status`);
        setFactionDetails(response.data.factions || {});
      } catch (e) { console.error(e); }
  };
  const fetchTerritories = async () => setTerritories(null); 
  const fetchTerritoryControl = async () => {
      try {
          const res = await axios.get(`${API}/territory/control`);
          setTerritoryControl(res.data.territories);
      } catch (e) { console.error(e); }
  };
  const fetchFactionEvents = async () => {
      try {
          const res = await axios.get(`${API}/factions/events?limit=10`);
          setFactionEvents(res.data.events);
      } catch (e) { console.error(e); }
  };
  const fetchBattleHistory = async () => {
      try {
          const res = await axios.get(`${API}/territory/battles`);
          setBattleHistory(res.data.battles);
      } catch (e) { console.error(e); }
  };
  const fetchTradeRoutes = async () => {
      try {
          const res = await axios.get(`${API}/factions/trade/routes`);
          setTradeRoutes(res.data.routes);
      } catch (e) { console.error(e); }
  };
  const fetchAllPlayers = async () => {
      try {
          const res = await axios.get(`${API}/players`);
          setAllPlayers(res.data.players || []);
      } catch (e) { console.error(e); }
  };

  const handleSendMessage = async () => {
    if (!inputValue.trim()) return;
    setLoading(true);
    const userMsg = { type: "player", content: inputValue };
    setMessages(prev => [...prev, userMsg]);
    const currentInput = inputValue;
    setInputValue(""); 

    try {
      const response = await axios.post(`${API}/npc/action`, {
        npc_id: selectedNPC,
        action: currentInput,
        player_id: playerId,
        player_name: currentUser.player_name,
      });

      const { cognitive_frame } = response.data;
      const npcMsg = {
        type: "npc",
        content: cognitive_frame.dialogue || "...",
        inner_thoughts: cognitive_frame.internal_reflection,
        emotional_shift: cognitive_frame.emotional_state
      };
      setMessages(prev => [...prev, npcMsg]);
      
      fetchNPCStatus();
      fetchPlayerInfo();

    } catch (e) {
      setMessages(prev => [...prev, { type: "system", content: "LINK FAILURE: " + e.message }]);
    } finally {
      setLoading(false);
    }
  };

  const switchNPC = (id) => {
      setSelectedNPC(id);
      setMessages([]); 
      setNpcStatus(null);
  };

  const renderContent = () => {
    switch (activeTab) {
      case "chat":
        return (
          <div className="chat-interface panel-content">
             <ChatPanel 
                selectedNPC={selectedNPC}
                npcStatus={npcStatus}
                messages={messages}
                inputValue={inputValue}
                setInputValue={setInputValue}
                loading={loading}
                sendAction={handleSendMessage}
                currentReputation={currentReputation}
                topicsExtracted={[]} 
                npcMemories={npcMemories}
                messagesEndRef={messagesEndRef}
                playerId={playerId}
                playerName={currentUser.player_name}
                API={API}
             />
          </div>
        );
      case "world":
        return (
          <div className="panel-content">
             <WorldControls 
                worldStatus={worldStatus} 
                worldEvents={worldEvents}
                timeScale={timeScale}
                setTimeScale={setTimeScale}
                simulationRunning={simulationRunning}
                loading={loading}
                startSimulation={async () => {
                    await axios.post(`${API}/world/start?time_scale=${timeScale}`);
                    fetchWorldStatus();
                }}
                stopSimulation={async () => {
                    await axios.post(`${API}/world/stop`);
                    fetchWorldStatus();
                }}
                fetchWorldEvents={fetchWorldEvents}
             />
          </div>
        );
      case "territory":
        return (
            <div className="panel-content">
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
                />
            </div>
        );
      case "players":
        return (
            <div className="panel-content">
                <PlayersTab 
                   allPlayers={allPlayers}
                   playerInfo={playerInfo}
                   playerId={playerId}
                   fetchAllPlayers={fetchAllPlayers}
                   fetchPlayerInfo={fetchPlayerInfo}
                />
            </div>
        );
      case "agents":
        return (
            <div className="panel-content">
                <NPCsTab 
                    activeNPCs={activeNPCs}
                    allNPCs={POTENTIAL_NPCS}
                    fetchAllNPCs={fetchAllNPCs}
                    initializeNPC={initializeNPC}
                    selectedNPC={selectedNPC}
                    loading={loading}
                    setActiveTab={setActiveTab}
                    switchNPC={(id) => { switchNPC(id); setActiveTab("chat"); }}
                />
            </div>
        );
       case "missions":
        return (
            <div className="panel-content">
               <QuestsTab 
                  quests={quests}
                  fetchQuests={fetchQuests}
               />
            </div>
        );
      default: 
        return <div className="panel-content">MODULE UNREACHABLE</div>;
    }
  };

  return (
    <div className="scifi-container scanlines">
      <header className="scifi-header">
        <div className="scifi-logo">
          <span className="scifi-logo__text">NEXUS<span style={{color: "#fff"}}>BRAIN</span></span>
        </div>
        <div className="scifi-status-indicator">
          <div className="status-item">
            <span className={`status-dot ${worldStatus?.is_running ? "online" : ""}`}></span>
            WORLD_SIM
          </div>
          <div className="status-item">
            <span className="status-dot online"></span>
            NET_UPLINK
          </div>
          <div className="status-item">
            USER: {currentUser.player_name.toUpperCase()}
          </div>
        </div>
      </header>

      <main className="scifi-main">
        <nav className="scifi-nav scifi-panel">
          <div className="panel-header"><MenuIcon icon={Terminal} /> MODULES</div>
          <button className={`nav-btn ${activeTab === "chat" ? "active" : ""}`} onClick={() => setActiveTab("chat")}>
            <Radio size={16} style={{marginRight: 8, verticalAlign: "text-bottom"}} /> NEURAL LINK
          </button>
          <button className={`nav-btn ${activeTab === "world" ? "active" : ""}`} onClick={() => setActiveTab("world")}>
            <Activity size={16} /> WORLD SIM
          </button>
          <button className={`nav-btn ${activeTab === "territory" ? "active" : ""}`} onClick={() => setActiveTab("territory")}>
            <Map size={16} /> FACTION GRID
          </button>
          <button className={`nav-btn ${activeTab === "players" ? "active" : ""}`} onClick={() => setActiveTab("players")}>
            <Users size={16} /> SUBJECTS
          </button>
          <button className={`nav-btn ${activeTab === "agents" ? "active" : ""}`} onClick={() => setActiveTab("agents")}>
            <Database size={16} /> AGENTS DB
          </button>
          <button className={`nav-btn ${activeTab === "missions" ? "active" : ""}`} onClick={() => setActiveTab("missions")}>
             <ScrollText size={16} /> MISSIONS
          </button>

          <div className="panel-header" style={{marginTop: 20}}><MenuIcon icon={Cpu} /> QUICK LINK</div>
          {activeNPCs.map(npc => (
            <button 
                key={npc.npc_id} 
                className={`nav-btn ${selectedNPC === npc.npc_id ? "active" : ""}`}
                onClick={() => { switchNPC(npc.npc_id); setActiveTab("chat"); }}
                style={{fontSize: "0.8rem", padding: "10px 15px"}}
            >
                {npc.name} [{npc.role?.substring(0,3).toUpperCase()}]
            </button>
          ))}
          {activeNPCs.length === 0 && <div style={{padding: 15, color: "#555"}}>SCANNING...</div>}
        </nav>

        <div className="scifi-panel">
           <div className="panel-header">
              <span>ACTIVE MODULE // {activeTab.toUpperCase()}</span>
              {activeTab === "chat" && <span style={{color: "var(--scifi-primary)"}}>TARGET: {selectedNPC.toUpperCase()}</span>}
           </div>
           {renderContent()}
        </div>

        <aside className="scifi-panel info-panel">
           <div className="panel-header"><MenuIcon icon={ShieldAlert} /> DIAGNOSTICS</div>
           <div className="panel-content">
              {activeTab === "chat" && npcStatus ? (
                  <div style={{fontSize: "0.9rem"}}>
                      <DetailRow label="STATUS" value={npcStatus.status} />
                      <DetailRow label="HEALTH" value={npcStatus.vitals?.health + "%"} />
                      <DetailRow label="LOC" value={npcStatus.location} />
                      <DetailRow label="MOOD" value={npcStatus.emotional_state?.current_mood} />
                      <hr style={{borderColor: "rgba(0,240,255,0.2)", margin: "10px 0"}} />
                      <div style={{color: "var(--scifi-text-dim)", marginBottom: 5}}>REP WITH PLAYER:</div>
                      <div style={{fontSize: "1.2rem", color: currentReputation > 0 ? "var(--scifi-success)" : "var(--scifi-alert)"}}>
                          {currentReputation.toFixed(1)}
                      </div>
                  </div>
              ) : (
                  <div style={{textAlign: "center", marginTop: 50, color: "var(--scifi-text-dim)"}}>
                     NO DATA STREAM
                  </div>
              )}

              {activeTab === "world" && worldStatus && (
                  <div style={{fontSize: "0.9rem"}}>
                      <DetailRow label="TICKS" value={worldStatus.tick_count} />
                      <DetailRow label="TIME" value={worldStatus.world_time} />
                      <DetailRow label="SCALE" value={timeScale + "x"} />
                  </div>
              )}
           </div>
        </aside>

      </main>

      <footer style={{
         borderTop: "var(--scifi-border)", 
         background: "#020202", 
         display: "flex", 
         alignItems: "center", 
         padding: "0 20px", 
         fontSize: "0.7rem", 
         color: "var(--scifi-text-dim)"
      }}>
         <span>SYSTEM v2.4.9 // CONNECTION_SECURE</span>
         <span style={{flex: 1}}></span>
         <span>RENDER_NODE: OR-1</span>
      </footer>
    </div>
  );
}

const MenuIcon = ({icon: Icon}) => <Icon size={14} style={{marginRight: 8, display: "inline-block", verticalAlign: "middle"}} />;

const DetailRow = ({label, value}) => (
    <div style={{display: "flex", justifyContent: "space-between", marginBottom: 8}}>
        <span style={{color: "var(--scifi-text-dim)"}}>{label}:</span>
        <span style={{color: "var(--scifi-text)"}}>{value || "N/A"}</span>
    </div>
);

export default App;
