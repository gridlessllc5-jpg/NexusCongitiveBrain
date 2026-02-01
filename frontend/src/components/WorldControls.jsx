import React from "react";

const WorldControls = ({
  worldStatus,
  worldEvents,
  timeScale,
  setTimeScale,
  simulationRunning,
  loading,
  startSimulation,
  stopSimulation,
  manualTick,
  fetchWorldStatus,
  fetchWorldEvents
}) => {
  return (
    <div className="world-container" data-testid="world-tab-content">
      <div className="world-header">
        <h2>🌍 World Simulation</h2>
        <div className={`simulation-status ${simulationRunning ? 'running' : 'stopped'}`}>
          {simulationRunning ? '🟢 Running' : '🔴 Stopped'}
        </div>
      </div>

      <div className="world-grid">
        {/* Control Panel */}
        <div className="world-controls" data-testid="world-controls">
          <h3>⚙️ Simulation Controls</h3>
          <div className="time-scale-control">
            <label>Time Scale (hours per tick):</label>
            <input 
              type="range" 
              min="1" 
              max="168" 
              value={timeScale}
              onChange={(e) => setTimeScale(parseInt(e.target.value))}
              data-testid="time-scale-slider"
            />
            <span className="time-scale-value">{timeScale}h</span>
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
                <span className="stat-value">{worldStatus.stats.faction_events}</span>
                <span className="stat-label">Faction Events</span>
              </div>
            </div>
          ) : (
            <p className="no-data">No stats yet. Start simulation or run a tick.</p>
          )}
        </div>

        {/* World Clock */}
        <div className="world-clock" data-testid="world-clock">
          <h3>🕐 World Time</h3>
          {worldStatus && worldStatus.world_time ? (
            <div className="clock-display">
              <div className="clock-main">
                Day {worldStatus.world_time.day}, {String(worldStatus.world_time.hour).padStart(2, '0')}:{String(worldStatus.world_time.minute).padStart(2, '0')}
              </div>
              <div className="clock-total">
                Total: {worldStatus.world_time.total_hours?.toFixed(1) || 0} hours
              </div>
            </div>
          ) : (
            <p className="no-data">World time not initialized</p>
          )}
        </div>

        {/* Active NPCs */}
        <div className="active-npcs-panel" data-testid="active-npcs-panel">
          <h3>👥 Active NPCs</h3>
          {worldStatus && worldStatus.active_npcs && worldStatus.active_npcs.length > 0 ? (
            <div className="active-npc-list">
              {worldStatus.active_npcs.map((npc, idx) => (
                <span key={idx} className="active-npc-tag">{npc}</span>
              ))}
            </div>
          ) : (
            <p className="no-data">No active NPCs</p>
          )}
        </div>

        {/* Event Feed */}
        <div className="world-events" data-testid="world-events">
          <h3>📜 Event Feed</h3>
          {worldEvents && worldEvents.length > 0 ? (
            <div className="event-feed">
              {worldEvents.map((event, idx) => (
                <div key={idx} className={`event-item event-${event.type}`}>
                  <span className="event-icon">
                    {event.type === 'memory_decay' && '🧠'}
                    {event.type === 'gossip' && '👂'}
                    {event.type === 'faction' && '⚔️'}
                    {event.type === 'quest' && '📜'}
                    {event.type === 'trade' && '💰'}
                    {event.type === 'npc_gossip' && '🗣️'}
                    {event.type === 'goals_progressed' && '🎯'}
                    {event.type === 'memories_forgotten' && '💨'}
                    {event.type === 'quests_expired' && '⏰'}
                  </span>
                  <span className="event-type">{event.type}</span>
                  <span className="event-detail">{event.detail}</span>
                  {event.timestamp && (
                    <span className="event-time">
                      {new Date(event.timestamp).toLocaleTimeString()}
                    </span>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <p className="no-data">No events yet</p>
          )}
        </div>
      </div>
    </div>
  );
};

export default WorldControls;
