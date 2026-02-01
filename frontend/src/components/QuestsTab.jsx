import React from "react";

const QuestsTab = ({ quests, fetchQuests }) => {
  return (
    <div className="panel-content">
      <div className="quests-container">
        <div className="quests-header" style={{
            display: "flex", 
            justifyContent: "space-between", 
            alignItems: "center",
            borderBottom: "1px solid var(--scifi-border)",
            paddingBottom: "10px",
            marginBottom: "15px"
        }}>
          <h2 style={{color: "var(--scifi-primary)", margin: 0}}>📜 MISSION LOG ({quests.length})</h2>
          <button className="refresh-btn" onClick={fetchQuests}>
            🔄 SYNC
          </button>
        </div>

        <div className="quests-list" style={{display: "grid", gap: "15px"}}>
          {quests.map((quest) => (
            <div key={quest.quest_id} className="quest-card" style={{
                background: "rgba(0, 20, 20, 0.3)",
                border: "1px solid var(--scifi-border)",
                padding: "15px"
            }}>
              <div className="quest-header" style={{
                  display: "flex", 
                  justifyContent: "space-between", 
                  borderBottom: "1px solid rgba(0, 240, 255, 0.1)",
                  paddingBottom: "5px",
                  marginBottom: "5px"
              }}>
                <h3 style={{margin: 0, color: "var(--scifi-secondary)"}}>{quest.title}</h3>
                <span className={`difficulty-badge difficulty-${Math.floor(quest.difficulty * 3)}`}
                      style={{
                          fontSize: "0.8rem",
                          color: quest.difficulty < 0.4 ? "var(--scifi-success)" : quest.difficulty < 0.7 ? "var(--scifi-warning)" : "var(--scifi-alert)"
                      }}>
                  {quest.difficulty < 0.4 ? "LOW RISK" : quest.difficulty < 0.7 ? "MED RISK" : "HIGH RISK"}
                </span>
              </div>
              <p className="quest-giver" style={{margin: "5px 0", fontSize: "0.9rem", color: "var(--scifi-text-dim)"}}>
                  Source: <strong style={{color: "var(--scifi-primary)"}}>{quest.quest_giver}</strong>
              </p>
              <p className="quest-type" style={{margin: "5px 0", fontSize: "0.8rem"}}>
                  Type: {quest.quest_type.toUpperCase()}
              </p>
              <p className="quest-description" style={{margin: "10px 0", fontStyle: "italic"}}>
                  "{quest.description}"
              </p>
              {quest.reward && (
                <div className="quest-reward" style={{
                    marginTop: "10px", 
                    padding: "5px", 
                    background: "rgba(0, 255, 65, 0.1)", 
                    border: "1px dashed var(--scifi-success)",
                    color: "var(--scifi-success)",
                    fontSize: "0.9rem"
                }}>
                  <strong>BOUNTY:</strong> {quest.reward.type} (+{quest.reward.value})
                </div>
              )}
            </div>
          ))}

          {quests.length === 0 && (
            <div className="empty-state" style={{textAlign: "center", padding: "40px", color: "var(--scifi-text-dim)"}}>
              <p>NO ACTIVE MISSIONS.</p>
              <p>CONTACT AGENTS TO ACQUIRE OBJECTIVES.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default QuestsTab;