import React from "react";

const PlayersTab = ({
  allPlayers,
  playerInfo,
  playerId,
  setPlayerId,
  playerName,
  setPlayerName,
  fetchAllPlayers,
  fetchPlayerInfo,
  switchPlayer
}) => {
  return (
    <div className="players-container" data-testid="players-tab-content">
      <div className="players-header">
        <h2>🎮 Player Tracking ({allPlayers.length})</h2>
        <button className="refresh-btn" onClick={fetchAllPlayers}>
          🔄 Refresh
        </button>
      </div>

      <div className="players-grid">
        {/* Current Player */}
        <div className="current-player-panel" data-testid="current-player-panel">
          <h3>👤 Current Player</h3>
          <div className="player-inputs">
            <div className="input-group">
              <label>Player ID:</label>
              <input
                type="text"
                value={playerId}
                onChange={(e) => setPlayerId(e.target.value)}
                placeholder="player_001"
                data-testid="player-id-input"
              />
            </div>
            <div className="input-group">
              <label>Display Name:</label>
              <input
                type="text"
                value={playerName}
                onChange={(e) => setPlayerName(e.target.value)}
                placeholder="Traveler"
                data-testid="player-name-input"
              />
            </div>
            <button 
              className="apply-btn" 
              onClick={fetchPlayerInfo}
              data-testid="apply-player-btn"
            >
              Apply
            </button>
          </div>
          
          {playerInfo && (
            <div className="player-details" data-testid="player-details">
              <div className="player-stat">
                <span>Total Interactions:</span>
                <strong>{playerInfo.total_interactions || 0}</strong>
              </div>
              <div className="player-stat">
                <span>NPCs Met:</span>
                <strong>{playerInfo.npcs_met?.length || 0}</strong>
              </div>
              <div className="player-stat">
                <span>Active Quests:</span>
                <strong>{playerInfo.active_quests || 0}</strong>
              </div>
            </div>
          )}
        </div>

        {/* Reputation Overview */}
        <div className="reputation-overview" data-testid="reputation-overview">
          <h3>⭐ NPC Reputations</h3>
          {playerInfo && playerInfo.npc_reputations ? (
            <div className="reputation-list">
              {Object.entries(playerInfo.npc_reputations).map(([npcId, rep]) => (
                <div key={npcId} className="reputation-item">
                  <span className="npc-name">{npcId}</span>
                  <div className="rep-bar-mini">
                    <div 
                      className="rep-fill-mini"
                      style={{
                        width: `${Math.abs(rep) * 50 + 50}%`,
                        backgroundColor: rep >= 0 ? '#4CAF50' : '#f44336'
                      }}
                    />
                  </div>
                  <span className={`rep-score ${rep >= 0 ? 'positive' : 'negative'}`}>
                    {rep.toFixed(2)}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p className="no-data">No reputation data yet</p>
          )}
        </div>

        {/* Faction Standing */}
        <div className="faction-standing" data-testid="faction-standing">
          <h3>⚔️ Faction Standing</h3>
          {playerInfo && playerInfo.faction_reputations ? (
            <div className="faction-rep-list">
              {Object.entries(playerInfo.faction_reputations).map(([factionId, rep]) => (
                <div key={factionId} className={`faction-rep-item faction-${factionId}`}>
                  <span className="faction-name">{factionId}</span>
                  <div className="faction-rep-bar">
                    <div 
                      className="faction-rep-fill"
                      style={{
                        width: `${Math.abs(rep) * 50 + 50}%`,
                        backgroundColor: rep >= 0 ? '#4CAF50' : '#f44336'
                      }}
                    />
                  </div>
                  <span className={`faction-rep-score ${rep >= 0 ? 'positive' : 'negative'}`}>
                    {rep.toFixed(2)}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p className="no-data">No faction standing yet</p>
          )}
        </div>

        {/* All Players List */}
        <div className="all-players-list" data-testid="all-players-list">
          <h3>📋 All Known Players</h3>
          {allPlayers && allPlayers.length > 0 ? (
            <div className="player-list">
              {allPlayers.map((player) => (
                <div 
                  key={player.player_id} 
                  className={`player-item ${player.player_id === playerId ? 'active' : ''}`}
                  onClick={() => switchPlayer(player.player_id)}
                >
                  <span className="player-id">{player.player_id}</span>
                  <span className="player-interactions">
                    {player.total_interactions || 0} interactions
                  </span>
                  <span className="player-last-seen">
                    {player.last_seen ? new Date(player.last_seen).toLocaleDateString() : 'Never'}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p className="no-data">No players tracked yet</p>
          )}
        </div>

        {/* Rumors About Player */}
        <div className="player-rumors" data-testid="player-rumors">
          <h3>👂 What NPCs Say About You</h3>
          {playerInfo && playerInfo.rumors && playerInfo.rumors.length > 0 ? (
            <div className="rumors-list">
              {playerInfo.rumors.map((rumor, idx) => (
                <div key={idx} className="rumor-item">
                  <span className="rumor-source">From: {rumor.source_npc}</span>
                  <span className="rumor-content">{rumor.content}</span>
                  <span className="rumor-spread">Spread to: {rumor.spread_to?.join(", ") || "No one yet"}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="no-data">No rumors circulating about you</p>
          )}
        </div>
      </div>
    </div>
  );
};

export default PlayersTab;
