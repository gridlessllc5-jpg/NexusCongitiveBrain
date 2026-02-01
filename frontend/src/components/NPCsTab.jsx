import React from "react";

const NPCsTab = ({
  allNPCs,
  activeNPCs,
  selectedNPC,
  loading,
  fetchAllNPCs,
  initializeNPC,
  switchNPC,
  setActiveTab
}) => {
  return (
    <div className="npcs-container" data-testid="npcs-tab-content">
      <div className="npcs-header">
        <h2>👥 NPC Management ({activeNPCs.length} active)</h2>
        <button className="refresh-btn" onClick={fetchAllNPCs}>
          🔄 Refresh
        </button>
      </div>

      <div className="npcs-grid">
        {/* Active NPCs */}
        <div className="active-npcs-section" data-testid="active-npcs-section">
          <h3>🟢 Active NPCs</h3>
          {activeNPCs && activeNPCs.length > 0 ? (
            <div className="npc-cards">
              {activeNPCs.map((npc) => (
                <div 
                  key={npc.npc_id} 
                  className={`npc-card ${npc.npc_id === selectedNPC ? 'selected' : ''}`}
                  onClick={() => {
                    switchNPC(npc.npc_id);
                    setActiveTab("chat");
                  }}
                  data-testid={`active-npc-${npc.npc_id}`}
                >
                  <div className="npc-card-header">
                    <span className="npc-name">{npc.name || npc.npc_id}</span>
                    <span className="npc-role">{npc.role}</span>
                  </div>
                  <div className="npc-card-details">
                    <span className="npc-location">📍 {npc.location || "Unknown"}</span>
                    {npc.faction && (
                      <span className={`npc-faction faction-${npc.faction}`}>
                        ⚔️ {npc.faction}
                      </span>
                    )}
                  </div>
                  <div className="npc-card-stats">
                    <span>Energy: {((npc.vitals?.energy || 0.5) * 100).toFixed(0)}%</span>
                    <span>Mood: {npc.mood || "Neutral"}</span>
                  </div>
                  <button 
                    className="chat-btn"
                    onClick={(e) => {
                      e.stopPropagation();
                      switchNPC(npc.npc_id);
                      setActiveTab("chat");
                    }}
                  >
                    💬 Chat
                  </button>
                </div>
              ))}
            </div>
          ) : (
            <p className="no-data">No active NPCs. Initialize one below!</p>
          )}
        </div>

        {/* Available NPCs */}
        <div className="available-npcs-section" data-testid="available-npcs-section">
          <h3>📋 Available NPCs</h3>
          {allNPCs && allNPCs.length > 0 ? (
            <div className="available-npc-list">
              {allNPCs.map((npc) => {
                const isActive = activeNPCs.some(a => a.npc_id === npc.npc_id);
                return (
                  <div 
                    key={npc.npc_id} 
                    className={`available-npc-item ${isActive ? 'active' : ''}`}
                    data-testid={`available-npc-${npc.npc_id}`}
                  >
                    <div className="npc-info">
                      <span className="npc-id">{npc.npc_id}</span>
                      <span className="npc-name">{npc.name}</span>
                      <span className="npc-role">{npc.role}</span>
                    </div>
                    {!isActive ? (
                      <button 
                        className="init-btn"
                        onClick={() => initializeNPC(npc.npc_id)}
                        disabled={loading}
                      >
                        Initialize
                      </button>
                    ) : (
                      <span className="active-badge">✓ Active</span>
                    )}
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="no-data">No NPCs available</p>
          )}
        </div>

        {/* NPC Stats Summary */}
        <div className="npc-stats-summary" data-testid="npc-stats-summary">
          <h3>📊 Statistics</h3>
          <div className="stats-cards">
            <div className="stat-card">
              <span className="stat-value">{allNPCs?.length || 0}</span>
              <span className="stat-label">Total NPCs</span>
            </div>
            <div className="stat-card">
              <span className="stat-value">{activeNPCs?.length || 0}</span>
              <span className="stat-label">Active</span>
            </div>
            <div className="stat-card">
              <span className="stat-value">
                {activeNPCs?.filter(n => n.faction === 'guards').length || 0}
              </span>
              <span className="stat-label">Guards</span>
            </div>
            <div className="stat-card">
              <span className="stat-value">
                {activeNPCs?.filter(n => n.faction === 'traders').length || 0}
              </span>
              <span className="stat-label">Traders</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default NPCsTab;
