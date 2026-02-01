import React, { useEffect, useRef, useCallback } from "react";
import SiriWave from "siriwave";
import "./VoiceVisualizer.css";

const VoiceVisualizer = ({ isPlaying, npcName }) => {
  const containerRef = useRef(null);
  const waveRef = useRef(null);

  // Initialize SiriWave
  useEffect(() => {
    if (containerRef.current && !waveRef.current) {
      waveRef.current = new SiriWave({
        container: containerRef.current,
        width: containerRef.current.offsetWidth,
        height: 120,
        style: "ios9",
        speed: 0.03,
        amplitude: 0.1,
        autostart: false,
        color: "#c4682b", // Rust orange
        cover: true,
      });
    }

    return () => {
      if (waveRef.current) {
        waveRef.current.dispose();
        waveRef.current = null;
      }
    };
  }, []);

  // Handle play/pause state
  useEffect(() => {
    if (waveRef.current) {
      if (isPlaying) {
        waveRef.current.setSpeed(0.12);
        waveRef.current.setAmplitude(1.5);
        waveRef.current.start();
      } else {
        // Smoothly reduce amplitude before stopping
        waveRef.current.setAmplitude(0.1);
        waveRef.current.setSpeed(0.03);
        setTimeout(() => {
          if (waveRef.current && !isPlaying) {
            waveRef.current.stop();
          }
        }, 500);
      }
    }
  }, [isPlaying]);

  // Handle window resize
  const handleResize = useCallback(() => {
    if (waveRef.current && containerRef.current) {
      // SiriWave doesn't have a resize method, so we need to recreate it
      const wasPlaying = isPlaying;
      waveRef.current.dispose();
      waveRef.current = new SiriWave({
        container: containerRef.current,
        width: containerRef.current.offsetWidth,
        height: 120,
        style: "ios9",
        speed: wasPlaying ? 0.12 : 0.03,
        amplitude: wasPlaying ? 1.5 : 0.1,
        autostart: wasPlaying,
        color: "#c4682b",
        cover: true,
      });
    }
  }, [isPlaying]);

  useEffect(() => {
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, [handleResize]);

  return (
    <div className={`voice-visualizer ${isPlaying ? "active" : ""}`}>
      <div className="visualizer-header">
        <div className="pulse-dot"></div>
        <span className="visualizer-label">
          {isPlaying ? `${npcName || "NPC"} is speaking...` : "Voice Ready"}
        </span>
      </div>
      <div className="wave-container" ref={containerRef}></div>
      <div className="visualizer-glow"></div>
    </div>
  );
};

export default VoiceVisualizer;
