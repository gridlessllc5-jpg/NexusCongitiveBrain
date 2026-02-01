import React from "react";

const FactionUI = ({
  factionDetails,
  territoryControl,
  tradeRoutes,
  battleHistory,
  factionEvents,
  activeNPCs,
  fetchFactions,
  fetchTerritories,
  fetchTerritoryControl,
  fetchFactionEvents,
  fetchBattleHistory,
  fetchTradeRoutes,
  triggerFactionEvent,
  initiateBattle,
  resolveBattle,
  establishNewRoute,
  executeTrade,
  disruptRoute,
  restoreRoute
}) => {
  return (
    <div className="factions-container" data-testid="factions-tab-content">
      <div className="factions-header">
        <h2>🏰 Factions & Territories</h2>
        <button 
          className="refresh-btn" 
          onClick={() => { 
            fetchFactions(); 
            fetchTerritories(); 
            fetchTerritoryControl(); 
            fetchFactionEvents(); 
            fetchBattleHistory(); 
            fetchTradeRoutes(); 
          }}
        >
          🔄 Refresh All
        </button>
      </div>

      <div className="factions-grid">
        {/* Faction Cards */}
        <div className="faction-overview-section" data-testid="faction-overview">
          <h3>⚔️ Factions</h3>
          <div className="faction-cards">
            {factionDetails ? Object.entries(factionDetails).map(([factionId, data]) => (
              <div 
                key={factionId} 
                className={`faction-card-enhanced faction-${factionId}`} 
                data-testid={`faction-card-${factionId}`}
              >
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
                      <span 
                        key={otherId} 
                        className={`relation-badge relation-${rel.type}`} 
                        title={`${rel.score.toFixed(2)}`}
                      >
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
                <div 
                  key={territoryId} 
                  className={`territory-card territory-${data.controlling_faction}`} 
                  data-testid={`territory-${territoryId}`}
                >
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
                        <div 
                          className="control-fill" 
                          style={{ width: `${data.control_strength * 100}%` }} 
                        />
                      </div>
                      <span className="control-value">
                        {(data.control_strength * 100).toFixed(0)}%
                      </span>
                    </div>
                    <div className="territory-stat">
                      <span>Strategic Value:</span>
                      <strong className="strategic-value">
                        {(data.strategic_value * 100).toFixed(0)}%
                      </strong>
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
            <button 
              className="control-btn" 
              onClick={establishNewRoute} 
              disabled={activeNPCs.length < 2}
            >
              + New Route
            </button>
          </div>
          {tradeRoutes && tradeRoutes.length > 0 ? (
            <div className="trade-routes-list">
              {tradeRoutes.map((route) => (
                <div key={route.route_id} className={`trade-route-card route-${route.status}`}>
                  <div className="route-header">
                    <span className="route-path">
                      {route.from_location} → {route.to_location}
                    </span>
                    <span className={`route-status status-${route.status}`}>
                      {route.status}
                    </span>
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
                        <button 
                          className="route-btn execute" 
                          onClick={() => executeTrade(route.route_id)}
                        >
                          Execute Trade
                        </button>
                        <button 
                          className="route-btn disrupt" 
                          onClick={() => disruptRoute(route.route_id)}
                        >
                          Disrupt
                        </button>
                      </>
                    )}
                    {route.status === "disrupted" && (
                      <button 
                        className="route-btn restore" 
                        onClick={() => restoreRoute(route.route_id)}
                      >
                        Restore
                      </button>
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
                    <button 
                      className="resolve-btn" 
                      onClick={() => resolveBattle(battle.battle_id)}
                    >
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
            <button 
              className="trigger-event-btn" 
              onClick={() => triggerFactionEvent("skirmish")}
            >
              Trigger Skirmish
            </button>
            <button 
              className="trigger-event-btn" 
              onClick={() => triggerFactionEvent("trade_deal")}
            >
              Trade Deal
            </button>
          </div>
          {factionEvents && factionEvents.length > 0 ? (
            <div className="faction-events-list">
              {factionEvents.map((event, idx) => (
                <div 
                  key={event.event_id || idx} 
                  className={`faction-event event-${event.event_type}`}
                >
                  <span className="event-icon">
                    {event.event_type === 'skirmish' && '⚔️'}
                    {event.event_type === 'trade_deal' && '🤝'}
                    {event.event_type === 'betrayal' && '🗡️'}
                    {event.event_type === 'alliance_formed' && '🤝'}
                  </span>
                  <div className="event-content">
                    <span className="event-type">
                      {event.event_type?.replace('_', ' ').toUpperCase()}
                    </span>
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
                  <span className="event-time">
                    {event.timestamp ? new Date(event.timestamp).toLocaleTimeString() : ''}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p className="no-data">No faction events yet</p>
          )}
        </div>
      </div>
    </div>
  );
};

export default FactionUI;
