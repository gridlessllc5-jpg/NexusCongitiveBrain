import React, { useState, useEffect, useRef } from "react";
import axios from "axios";
import { Users, MessageCircle, Volume2, VolumeX, Send, Plus, X, MapPin, RefreshCw } from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "http://localhost:8001";
const API = `${BACKEND_URL}/api`;

const GroupConversation = ({ activeNPCs: propNPCs, playerId, playerName }) => {
  const [groupId, setGroupId] = useState(null);
  const [participants, setParticipants] = useState([]);
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState("");
  const [loading, setLoading] = useState(false);
  const [withVoice, setWithVoice] = useState(true);
  const [tensionLevel, setTensionLevel] = useState(0);
  const [selectedNPCs, setSelectedNPCs] = useState([]);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentSpeaker, setCurrentSpeaker] = useState(null);
  const [activeNPCs, setActiveNPCs] = useState([]);
  const [fetchingNPCs, setFetchingNPCs] = useState(false);
  const messagesEndRef = useRef(null);
  const audioRef = useRef(null);
  const audioQueueRef = useRef([]);

  // Fetch NPCs on mount and when propNPCs changes
  useEffect(() => {
    if (propNPCs && propNPCs.length > 0) {
      setActiveNPCs(propNPCs);
    } else {
      fetchNPCs();
    }
  }, [propNPCs]);

  const fetchNPCs = async () => {
    setFetchingNPCs(true);
    try {
      const response = await axios.get(`${API}/npc/list`);
      setActiveNPCs(response.data.npcs || []);
    } catch (error) {
      console.error("Failed to fetch NPCs:", error);
    }
    setFetchingNPCs(false);
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Toggle NPC selection
  const toggleNPCSelection = (npcId) => {
    setSelectedNPCs(prev => 
      prev.includes(npcId) 
        ? prev.filter(id => id !== npcId)
        : [...prev, npcId]
    );
  };

  // Start group conversation
  const startConversation = async () => {
    if (selectedNPCs.length < 1) {
      alert("Select at least 1 NPC to start a conversation");
      return;
    }

    setLoading(true);
    try {
      const response = await axios.post(`${API}/conversation/start`, {
        player_id: playerId,
        player_name: playerName,
        npc_ids: selectedNPCs,
        location: "tavern",
        auto_discover: false
      });

      setGroupId(response.data.group_id);
      setParticipants(response.data.participants || []);
      setMessages([{
        type: "system",
        content: `Group conversation started with ${response.data.participants?.map(p => p.name).join(", ")}`,
        timestamp: Date.now()
      }]);
      setTensionLevel(0);
    } catch (error) {
      console.error("Failed to start conversation:", error);
      alert("Failed to start conversation: " + (error.response?.data?.detail || error.message));
    }
    setLoading(false);
  };

  // End conversation
  const endConversation = async () => {
    if (!groupId) return;

    try {
      await axios.post(`${API}/conversation/${groupId}/end`);
      setMessages(prev => [...prev, {
        type: "system",
        content: "Conversation ended",
        timestamp: Date.now()
      }]);
      setGroupId(null);
      setParticipants([]);
    } catch (error) {
      console.error("Failed to end conversation:", error);
    }
  };

  // Play audio from base64
  const playAudio = (audioBase64, format = "wav") => {
    return new Promise((resolve, reject) => {
      try {
        const audio = new Audio(`data:audio/${format};base64,${audioBase64}`);
        audio.onended = resolve;
        audio.onerror = reject;
        audio.play();
        audioRef.current = audio;
      } catch (error) {
        reject(error);
      }
    });
  };

  // Process audio queue
  const processAudioQueue = async () => {
    if (isPlaying || audioQueueRef.current.length === 0) return;
    
    setIsPlaying(true);
    
    while (audioQueueRef.current.length > 0) {
      const item = audioQueueRef.current.shift();
      setCurrentSpeaker(item.npcName);
      
      try {
        await playAudio(item.audio, item.format);
      } catch (error) {
        console.error("Audio playback error:", error);
      }
    }
    
    setCurrentSpeaker(null);
    setIsPlaying(false);
  };

  // Send message
  const sendMessage = async () => {
    if (!inputValue.trim() || !groupId || loading) return;

    const userMessage = inputValue.trim();
    setInputValue("");
    setLoading(true);

    // Add player message to chat
    setMessages(prev => [...prev, {
      type: "player",
      speaker: playerName,
      content: userMessage,
      timestamp: Date.now()
    }]);

    try {
      const response = await axios.post(`${API}/conversation/${groupId}/message`, {
        message: userMessage,
        with_voice: withVoice,
        voice_format: "mp3"
      });

      // Update tension
      setTensionLevel(response.data.tension_level || 0);

      // Add NPC responses
      for (const resp of response.data.responses || []) {
        setMessages(prev => [...prev, {
          type: "npc",
          speaker: resp.npc_name,
          npcId: resp.npc_id,
          content: resp.dialogue,
          responseType: resp.response_type,
          mood: resp.mood,
          target: resp.target,
          timestamp: Date.now()
        }]);
      }

      // Queue voice responses
      if (withVoice && response.data.voice_responses) {
        for (const voice of response.data.voice_responses) {
          if (voice.audio_base64) {
            audioQueueRef.current.push({
              npcId: voice.npc_id,
              npcName: voice.npc_name,
              audio: voice.audio_base64,
              format: "mp3"
            });
          }
        }
        processAudioQueue();
      }

    } catch (error) {
      console.error("Failed to send message:", error);
      setMessages(prev => [...prev, {
        type: "error",
        content: "Failed to send message: " + (error.response?.data?.detail || error.message),
        timestamp: Date.now()
      }]);
    }

    setLoading(false);
  };

  const getResponseTypeColor = (type) => {
    switch (type) {
      case "agreement": return "text-green-400";
      case "disagreement": return "text-red-400";
      case "elaboration": return "text-blue-400";
      case "interruption": return "text-orange-400";
      case "redirect": return "text-purple-400";
      default: return "text-gray-400";
    }
  };

  const getResponseTypeLabel = (type) => {
    switch (type) {
      case "agreement": return "agrees";
      case "disagreement": return "disagrees";
      case "elaboration": return "adds";
      case "interruption": return "interrupts";
      case "redirect": return "redirects";
      default: return "";
    }
  };

  return (
    <div className="flex flex-col h-full bg-gray-900 rounded-lg overflow-hidden">
      {/* Header */}
      <div className="bg-gray-800 p-4 border-b border-gray-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Users className="text-amber-500" size={24} />
            <h2 className="text-xl font-bold text-amber-500">Group Conversation</h2>
          </div>
          
          {groupId && (
            <div className="flex items-center gap-4">
              <div className="text-sm">
                <span className="text-gray-400">Tension: </span>
                <span className={`font-bold ${
                  tensionLevel > 0.6 ? "text-red-400" : 
                  tensionLevel > 0.3 ? "text-yellow-400" : 
                  "text-green-400"
                }`}>
                  {(tensionLevel * 100).toFixed(0)}%
                </span>
              </div>
              <button
                onClick={() => setWithVoice(!withVoice)}
                className={`p-2 rounded ${withVoice ? "bg-amber-600" : "bg-gray-700"}`}
                title={withVoice ? "Voice On" : "Voice Off"}
              >
                {withVoice ? <Volume2 size={18} /> : <VolumeX size={18} />}
              </button>
              <button
                onClick={endConversation}
                className="px-3 py-1 bg-red-600 hover:bg-red-700 rounded text-sm"
              >
                End Chat
              </button>
            </div>
          )}
        </div>

        {/* Participants */}
        {groupId && participants.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-2">
            {participants.map(p => (
              <div 
                key={p.npc_id}
                className={`px-3 py-1 rounded-full text-sm flex items-center gap-1 ${
                  currentSpeaker === p.name 
                    ? "bg-amber-600 text-white animate-pulse" 
                    : "bg-gray-700 text-gray-300"
                }`}
              >
                <span>{p.name}</span>
                {currentSpeaker === p.name && <Volume2 size={14} />}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* NPC Selection (when no active conversation) */}
      {!groupId && (
        <div className="p-4 bg-gray-850 border-b border-gray-700">
          <h3 className="text-sm text-gray-400 mb-3">Select NPCs for conversation:</h3>
          <div className="flex flex-wrap gap-2 mb-4">
            {activeNPCs.map(npc => (
              <button
                key={npc.npc_id}
                onClick={() => toggleNPCSelection(npc.npc_id)}
                className={`px-3 py-2 rounded-lg text-sm flex items-center gap-2 transition-all ${
                  selectedNPCs.includes(npc.npc_id)
                    ? "bg-amber-600 text-white"
                    : "bg-gray-700 text-gray-300 hover:bg-gray-600"
                }`}
              >
                {selectedNPCs.includes(npc.npc_id) ? (
                  <X size={14} />
                ) : (
                  <Plus size={14} />
                )}
                <span>{npc.npc_id}</span>
                <span className="text-xs opacity-70">({npc.role})</span>
              </button>
            ))}
          </div>
          
          {activeNPCs.length === 0 && (
            <div className="text-center">
              <p className="text-gray-500 text-sm mb-3">No NPCs initialized yet.</p>
              <button
                onClick={fetchNPCs}
                disabled={fetchingNPCs}
                className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded text-sm flex items-center gap-2 mx-auto"
              >
                <RefreshCw size={14} className={fetchingNPCs ? "animate-spin" : ""} />
                {fetchingNPCs ? "Loading..." : "Refresh NPCs"}
              </button>
              <p className="text-gray-600 text-xs mt-2">Go to NPCs tab to initialize NPCs first</p>
            </div>
          )}
          
          <button
            onClick={startConversation}
            disabled={selectedNPCs.length < 1 || loading}
            className="w-full py-3 bg-amber-600 hover:bg-amber-700 disabled:bg-gray-700 disabled:cursor-not-allowed rounded-lg font-medium transition-colors"
          >
            {loading ? "Starting..." : `Start Group Chat (${selectedNPCs.length} NPCs)`}
          </button>
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg, idx) => (
          <div key={idx} className={`${
            msg.type === "system" ? "text-center" :
            msg.type === "player" ? "flex justify-end" :
            "flex justify-start"
          }`}>
            {msg.type === "system" ? (
              <span className="text-gray-500 text-sm italic">{msg.content}</span>
            ) : msg.type === "error" ? (
              <span className="text-red-400 text-sm">{msg.content}</span>
            ) : msg.type === "player" ? (
              <div className="max-w-[80%] bg-amber-600 rounded-lg px-4 py-3">
                <div className="text-xs text-amber-200 mb-1">{msg.speaker}</div>
                <div className="text-white">{msg.content}</div>
              </div>
            ) : (
              <div className="max-w-[80%] bg-gray-800 rounded-lg px-4 py-3 border border-gray-700">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-amber-400 font-medium">{msg.speaker}</span>
                  {msg.responseType && msg.responseType !== "direct_reply" && (
                    <span className={`text-xs ${getResponseTypeColor(msg.responseType)}`}>
                      ({getResponseTypeLabel(msg.responseType)}{msg.target && msg.target !== "player" ? ` ${msg.target}` : ""})
                    </span>
                  )}
                  {msg.mood && (
                    <span className="text-xs text-gray-500">• {msg.mood}</span>
                  )}
                </div>
                <div className="text-gray-200">{msg.content}</div>
              </div>
            )}
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      {groupId && (
        <div className="p-4 bg-gray-800 border-t border-gray-700">
          <div className="flex gap-2">
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyPress={(e) => e.key === "Enter" && sendMessage()}
              placeholder="Say something to the group..."
              className="flex-1 px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-amber-500"
              disabled={loading}
            />
            <button
              onClick={sendMessage}
              disabled={loading || !inputValue.trim()}
              className="px-6 py-3 bg-amber-600 hover:bg-amber-700 disabled:bg-gray-700 disabled:cursor-not-allowed rounded-lg transition-colors"
            >
              {loading ? (
                <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
              ) : (
                <Send size={20} />
              )}
            </button>
          </div>
          {isPlaying && (
            <div className="mt-2 text-sm text-amber-400 flex items-center gap-2">
              <Volume2 size={14} className="animate-pulse" />
              <span>{currentSpeaker} is speaking...</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default GroupConversation;
