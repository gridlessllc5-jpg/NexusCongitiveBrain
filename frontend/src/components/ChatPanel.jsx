import React, { useState, useRef, useEffect, useCallback } from "react";
import axios from "axios";
import { Mic, MicOff, Loader2 } from "lucide-react";
import VoiceVisualizer from "./VoiceVisualizer";

const ChatPanel = ({
  selectedNPC,
  npcStatus,
  messages,
  inputValue,
  setInputValue,
  loading,
  sendAction,
  currentReputation,
  topicsExtracted,
  npcMemories,
  messagesEndRef,
  playerId,
  playerName,
  API
}) => {
  const [voiceEnabled, setVoiceEnabled] = useState(true);
  const [autoPlay, setAutoPlay] = useState(true);
  const [voiceLoading, setVoiceLoading] = useState(false);
  const [currentAudio, setCurrentAudio] = useState(null);
  const [voiceAssigned, setVoiceAssigned] = useState(false);
  const [lastPlayedIndex, setLastPlayedIndex] = useState(-1);
  const [isAudioPlaying, setIsAudioPlaying] = useState(false);
  const audioRef = useRef(null);
  
  // STT (Speech-to-Text) state
  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const [micError, setMicError] = useState(null);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const recordingTimerRef = useRef(null);

  const handleKeyPress = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendAction();
    }
  };

  // Auto-assign voice when NPC changes
  useEffect(() => {
    if (selectedNPC && voiceEnabled) {
      assignVoiceQuiet();
    }
  }, [selectedNPC]);

  // Auto-play new NPC messages
  useEffect(() => {
    if (!voiceEnabled || !autoPlay || messages.length === 0) return;
    
    const lastMessage = messages[messages.length - 1];
    const currentIndex = messages.length - 1;
    
    // Only play if it's a new NPC message we haven't played yet
    if (lastMessage.type === "npc" && currentIndex > lastPlayedIndex && !voiceLoading) {
      setLastPlayedIndex(currentIndex);
      playVoice(lastMessage.content, lastMessage.emotional_shift || "neutral");
    }
  }, [messages, voiceEnabled, autoPlay]);

  const assignVoiceQuiet = async () => {
    try {
      const response = await axios.post(`${API}/voice/assign/${selectedNPC}`);
      if (response.data.status === "assigned") {
        setVoiceAssigned(true);
        console.log(`Voice assigned: ${response.data.voice.voice_name}`);
      }
    } catch (error) {
      console.error("Error assigning voice:", error);
    }
  };

  const assignVoice = async () => {
    try {
      const response = await axios.post(`${API}/voice/assign/${selectedNPC}`);
      if (response.data.status === "assigned") {
        setVoiceAssigned(true);
        const fingerprint = response.data.fingerprint;
        alert(`✅ Voice assigned!\n\nVoice: ${response.data.voice.voice_name}\nPitch: ${fingerprint.pitch_description}\nSpeed: ${fingerprint.speed_mod}x`);
      }
    } catch (error) {
      console.error("Error assigning voice:", error);
    }
  };

  const playVoice = async (text, mood = "neutral") => {
    if (!voiceEnabled || !text || voiceLoading) return;
    
    setVoiceLoading(true);
    try {
      const response = await axios.post(`${API}/voice/generate/${selectedNPC}`, {
        text: text.substring(0, 500), // Limit text length
        mood: mood
      });
      
      if (response.data.audio_url) {
        setCurrentAudio(response.data.audio_url);
        if (audioRef.current) {
          audioRef.current.src = response.data.audio_url;
          setIsAudioPlaying(true);
          await audioRef.current.play();
        }
      }
    } catch (error) {
      console.error("Error generating voice:", error);
      setIsAudioPlaying(false);
    } finally {
      setVoiceLoading(false);
    }
  };

  const stopAudio = () => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
      setIsAudioPlaying(false);
    }
  };

  // Audio event handlers for visualizer
  useEffect(() => {
    const audio = audioRef.current;
    if (audio) {
      const handlePlay = () => setIsAudioPlaying(true);
      const handlePause = () => setIsAudioPlaying(false);
      const handleEnded = () => setIsAudioPlaying(false);
      
      audio.addEventListener('play', handlePlay);
      audio.addEventListener('pause', handlePause);
      audio.addEventListener('ended', handleEnded);
      
      return () => {
        audio.removeEventListener('play', handlePlay);
        audio.removeEventListener('pause', handlePause);
        audio.removeEventListener('ended', handleEnded);
      };
    }
  }, []);

  // ============================================================================
  // Speech-to-Text (STT) Functions
  // ============================================================================
  
  const startRecording = useCallback(async () => {
    setMicError(null);
    audioChunksRef.current = [];
    
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: { 
          echoCancellation: true,
          noiseSuppression: true,
          sampleRate: 44100
        } 
      });
      
      // Use webm format which is well supported
      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus') 
        ? 'audio/webm;codecs=opus' 
        : 'audio/webm';
      
      const mediaRecorder = new MediaRecorder(stream, { mimeType });
      mediaRecorderRef.current = mediaRecorder;
      
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };
      
      mediaRecorder.onstop = async () => {
        // Stop all tracks
        stream.getTracks().forEach(track => track.stop());
        
        // Create blob from chunks
        const audioBlob = new Blob(audioChunksRef.current, { type: mimeType });
        
        // Transcribe the audio
        await transcribeAudio(audioBlob);
      };
      
      // Start recording
      mediaRecorder.start(100); // Collect data every 100ms
      setIsRecording(true);
      setRecordingTime(0);
      
      // Start timer
      recordingTimerRef.current = setInterval(() => {
        setRecordingTime(prev => prev + 1);
      }, 1000);
      
    } catch (error) {
      console.error("Microphone access error:", error);
      if (error.name === 'NotAllowedError') {
        setMicError("Microphone access denied. Please allow microphone access in your browser settings.");
      } else if (error.name === 'NotFoundError') {
        setMicError("No microphone found. Please connect a microphone.");
      } else {
        setMicError(`Microphone error: ${error.message}`);
      }
    }
  }, []);
  
  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      
      // Clear timer
      if (recordingTimerRef.current) {
        clearInterval(recordingTimerRef.current);
        recordingTimerRef.current = null;
      }
    }
  }, [isRecording]);
  
  const transcribeAudio = async (audioBlob) => {
    setIsTranscribing(true);
    
    try {
      // Convert blob to base64
      const reader = new FileReader();
      const base64Promise = new Promise((resolve, reject) => {
        reader.onloadend = () => {
          const base64 = reader.result.split(',')[1]; // Remove data URL prefix
          resolve(base64);
        };
        reader.onerror = reject;
      });
      reader.readAsDataURL(audioBlob);
      
      const audioBase64 = await base64Promise;
      
      // Send to backend for transcription
      const response = await axios.post(`${API}/speech/transcribe`, {
        audio_base64: audioBase64,
        language: "en"
      });
      
      if (response.data.status === "success" && response.data.text) {
        // Set the transcribed text in the input
        setInputValue(prev => {
          const trimmedPrev = prev.trim();
          const newText = response.data.text.trim();
          return trimmedPrev ? `${trimmedPrev} ${newText}` : newText;
        });
      } else if (!response.data.text) {
        setMicError("No speech detected. Please try again.");
      }
      
    } catch (error) {
      console.error("Transcription error:", error);
      setMicError(`Transcription failed: ${error.response?.data?.error || error.message}`);
    } finally {
      setIsTranscribing(false);
    }
  };
  
  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (recordingTimerRef.current) {
        clearInterval(recordingTimerRef.current);
      }
      if (mediaRecorderRef.current && isRecording) {
        mediaRecorderRef.current.stop();
      }
    };
  }, [isRecording]);
  
  // Format recording time
  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="chat-container" data-testid="chat-container">
      {/* Hidden Audio Element */}
      <audio ref={audioRef} style={{ display: 'none' }} />
      
      {/* NPC Info Panel */}
      <div className="npc-info-panel" data-testid="npc-info-panel">
        {npcStatus ? (
          <>
            <div className="npc-header">
              <h2>{npcStatus.name}</h2>
              <span className="npc-role">{npcStatus.role}</span>
            </div>
            
            {/* Voice Controls */}
            <div className="voice-controls" data-testid="voice-controls">
              <label className="voice-toggle">
                <input 
                  type="checkbox" 
                  checked={voiceEnabled} 
                  onChange={(e) => setVoiceEnabled(e.target.checked)}
                />
                🔊 Voice {voiceEnabled ? 'ON' : 'OFF'}
              </label>
              
              {voiceEnabled && (
                <label className="voice-toggle auto-play-toggle">
                  <input 
                    type="checkbox" 
                    checked={autoPlay} 
                    onChange={(e) => setAutoPlay(e.target.checked)}
                  />
                  ▶️ Auto-play
                </label>
              )}
              
              {voiceEnabled && (
                <button 
                  className="assign-voice-btn" 
                  onClick={assignVoice}
                  title="View voice details"
                >
                  🎤 Voice Info
                </button>
              )}
              
              {voiceLoading && (
                <span className="voice-loading">
                  <span className="loading-spinner">🔄</span> Generating...
                </span>
              )}
              
              {voiceEnabled && currentAudio && !voiceLoading && (
                <button 
                  className="stop-audio-btn" 
                  onClick={stopAudio}
                  title="Stop audio"
                >
                  ⏹️ Stop
                </button>
              )}
            </div>
            
            <div className="player-badge">
              Playing as: <strong>{playerName}</strong> ({playerId})
            </div>
            <div className="reputation-display" data-testid="reputation-display">
              <span className="rep-label">Reputation:</span>
              <div className="rep-bar">
                <div 
                  className="rep-fill" 
                  style={{ 
                    width: `${Math.abs(currentReputation) * 50 + 50}%`,
                    backgroundColor: currentReputation >= 0 ? '#4CAF50' : '#f44336'
                  }}
                />
              </div>
              <span className="rep-value">{currentReputation.toFixed(2)}</span>
            </div>
            {topicsExtracted > 0 && (
              <div className="topics-indicator" data-testid="topics-indicator">
                📝 {topicsExtracted} topics remembered this session
              </div>
            )}
            <div className="npc-location">
              📍 {npcStatus.location || "Porto Cobre"}
            </div>
            {npcStatus.faction && (
              <div className="npc-faction">
                ⚔️ Faction: {npcStatus.faction}
              </div>
            )}
            <div className="emotional-state" data-testid="emotional-state">
              <h4>Emotional State</h4>
              <div className="emotion-grid">
                <span>Mood: {npcStatus.mood || "Neutral"}</span>
                <span>Energy: {((npcStatus.vitals?.energy || 0.5) * 100).toFixed(0)}%</span>
                <span>Stress: {((npcStatus.vitals?.stress || 0.3) * 100).toFixed(0)}%</span>
              </div>
            </div>
          </>
        ) : (
          <p>Loading NPC data...</p>
        )}
      </div>

      {/* Voice Visualizer - AI Speaking Animation */}
      {voiceEnabled && (
        <VoiceVisualizer 
          isPlaying={isAudioPlaying} 
          npcName={npcStatus?.name || selectedNPC}
        />
      )}

      {/* Messages */}
      <div className="messages-container" data-testid="messages-container">
        {messages.map((msg, idx) => (
          <div key={idx} className={`message ${msg.type}`}>
            {msg.type === "npc" && (
              <div className="message-header">
                <span className="npc-name">{npcStatus?.name || selectedNPC}</span>
                {voiceEnabled && (
                  <button 
                    className="play-voice-btn" 
                    onClick={() => playVoice(msg.content, msg.emotional_shift || "neutral")}
                    disabled={voiceLoading}
                    title="Play voice"
                  >
                    🔊
                  </button>
                )}
                {msg.gossipIndicator && (
                  <span className="gossip-badge" title="This NPC heard about you from others">
                    👂 Heard rumors
                  </span>
                )}
              </div>
            )}
            {msg.type === "player" && (
              <div className="message-header">
                <span className="player-name">{playerName}</span>
              </div>
            )}
            <div className="message-content">{msg.content}</div>
            {msg.inner_thoughts && (
              <div className="inner-thoughts">
                <span className="thoughts-label">💭 Inner thoughts:</span>
                <span className="thoughts-content">{msg.inner_thoughts}</span>
              </div>
            )}
            {msg.emotional_shift && (
              <div className="emotional-shift">
                Mood shifted: {msg.emotional_shift}
              </div>
            )}
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Memory Log */}
      {npcMemories && npcMemories.length > 0 && (
        <div className="memory-log" data-testid="memory-log">
          <h4>🧠 What {npcStatus?.name || selectedNPC} remembers about you:</h4>
          <div className="memory-list">
            {npcMemories.map((mem, idx) => (
              <div key={idx} className={`memory-item memory-${mem.category}`}>
                <span className="memory-category">{mem.category}</span>
                <span className="memory-content">{mem.content}</span>
                <span className="memory-strength" title="Memory strength">
                  {(mem.current_strength * 100).toFixed(0)}%
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Input */}
      <div className="input-container" data-testid="chat-input-container">
        {/* Microphone Error Message */}
        {micError && (
          <div className="mic-error" data-testid="mic-error">
            <span>⚠️ {micError}</span>
            <button onClick={() => setMicError(null)}>×</button>
          </div>
        )}
        
        <div className="input-row">
          {/* Microphone Button */}
          <button
            className={`mic-btn ${isRecording ? 'recording' : ''} ${isTranscribing ? 'transcribing' : ''}`}
            onClick={isRecording ? stopRecording : startRecording}
            disabled={loading || isTranscribing}
            data-testid="mic-btn"
            title={isRecording ? "Stop recording" : "Start recording"}
          >
            {isTranscribing ? (
              <Loader2 className="mic-icon spinning" size={20} />
            ) : isRecording ? (
              <>
                <MicOff className="mic-icon" size={20} />
                <span className="recording-time">{formatTime(recordingTime)}</span>
              </>
            ) : (
              <Mic className="mic-icon" size={20} />
            )}
          </button>
          
          <textarea
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder={isRecording ? "Recording... Click mic to stop" : "Say something to the NPC... (or click 🎤)"}
            disabled={loading || isRecording}
            data-testid="chat-input"
          />
          <button 
            onClick={sendAction} 
            disabled={loading || !inputValue.trim() || isRecording}
            data-testid="send-btn"
          >
            {loading ? "..." : "Send"}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ChatPanel;
