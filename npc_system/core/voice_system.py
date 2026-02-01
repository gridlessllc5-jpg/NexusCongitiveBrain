"""
NPC Voice System - ElevenLabs Integration (Enhanced)
Provides unique, realistic voices for each NPC based on their personality and role
Includes voice cloning capability for custom NPC voices
"""
import os
import io
import base64
import hashlib
import json
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass, field
from elevenlabs import ElevenLabs, VoiceSettings
import asyncio
import sqlite3
from pathlib import Path

# ElevenLabs API Key
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")

# Database for voice assignments - use dynamic path
try:
    from core.paths import VOICE_DB
    VOICE_DB_PATH = VOICE_DB
except ImportError:
    try:
        from paths import VOICE_DB
        VOICE_DB_PATH = VOICE_DB
    except ImportError:
        VOICE_DB_PATH = "/app/npc_system/database/voice_assignments.db"

# ============================================================================
# Voice Profiles - Maps NPC characteristics to ElevenLabs voices
# ============================================================================

@dataclass
class VoiceProfile:
    """Voice configuration for an NPC"""
    voice_id: str
    voice_name: str
    description: str
    stability: float = 0.5  # 0-1, lower = more variable/emotional
    similarity_boost: float = 0.75  # 0-1, higher = more consistent
    style: float = 0.0  # 0-1, style exaggeration
    use_speaker_boost: bool = True
    is_cloned: bool = False  # True if this is a custom cloned voice

@dataclass
class NPCVoiceFingerprint:
    """Unique voice fingerprint for an NPC based on personality"""
    npc_id: str
    base_voice_key: str
    stability_mod: float = 0.0  # -0.3 to +0.3 modifier
    similarity_mod: float = 0.0
    style_mod: float = 0.0
    speed_mod: float = 1.0  # 0.5 to 2.0
    pitch_description: str = "normal"  # For reference
    
    def get_effective_settings(self, base_profile: VoiceProfile) -> Dict:
        """Calculate effective voice settings"""
        return {
            "stability": max(0.1, min(1.0, base_profile.stability + self.stability_mod)),
            "similarity_boost": max(0.1, min(1.0, base_profile.similarity_boost + self.similarity_mod)),
            "style": max(0.0, min(1.0, base_profile.style + self.style_mod)),
            "use_speaker_boost": base_profile.use_speaker_boost
        }

# ElevenLabs Pre-made Voices mapped to NPC archetypes
VOICE_LIBRARY = {
    # Male Voices - Deep/Authoritative
    "adam": VoiceProfile("pNInz6obpgDQGcFmaJgB", "Adam", "Deep, authoritative male - guards, warriors", 0.6, 0.8),
    "arnold": VoiceProfile("VR6AewLTigWG4xSOukaG", "Arnold", "Gruff, commanding male - military leaders", 0.7, 0.85),
    "clyde": VoiceProfile("2EiwWnXFnvU5JabPnv8n", "Clyde", "War veteran, grizzled male - old soldiers", 0.65, 0.75),
    
    # Male Voices - Friendly/Warm
    "antoni": VoiceProfile("ErXwobaYiN019PkySvjV", "Antoni", "Warm, friendly male - merchants, innkeepers", 0.5, 0.7),
    "josh": VoiceProfile("TxGEqnHWrfWFTfGW9XjX", "Josh", "Young, energetic male - apprentices", 0.4, 0.65),
    "ethan": VoiceProfile("g5CIjZEefAph4nQFvHAz", "Ethan", "Young American male - common folk", 0.45, 0.7),
    
    # Male Voices - Mysterious/Unique
    "sam": VoiceProfile("yoZ06aMxZJJ28mfd3POQ", "Sam", "Raspy, mysterious male - outcasts, rogues", 0.35, 0.6),
    "daniel": VoiceProfile("onwK4e9ZLuTAKqWW03F9", "Daniel", "British, refined male - nobles, scholars", 0.55, 0.8),
    "charlie": VoiceProfile("IKne3meq5aSn9XLyUdCD", "Charlie", "Casual Australian male - travelers", 0.45, 0.65),
    "harry": VoiceProfile("SOYHLrjzK2X1ezoPC6cr", "Harry", "Low, gravelly male - dwarves, blacksmiths", 0.6, 0.7),
    "james": VoiceProfile("ZQe5CZNOzWyzPSCn5a3c", "James", "Australian male - rugged travelers", 0.5, 0.7),
    
    # Female Voices - Calm/Professional
    "rachel": VoiceProfile("21m00Tcm4TlvDq8ikWAM", "Rachel", "Calm, professional female - healers, sages", 0.55, 0.8),
    "emily": VoiceProfile("LcfcDJNUP1GQjkzn1xUU", "Emily", "Calm American female - shopkeepers", 0.5, 0.75),
    
    # Female Voices - Strong/Confident
    "domi": VoiceProfile("AZnzlk1XvdvUeBnXmlld", "Domi", "Strong, confident female - female warriors", 0.6, 0.8),
    "charlotte": VoiceProfile("XB0fDUnXU5powFXDhCwa", "Charlotte", "Swedish, elegant female - nobles", 0.55, 0.85),
    
    # Female Voices - Soft/Gentle
    "bella": VoiceProfile("EXAVITQu4vr4xnSDxMaL", "Bella", "Soft, gentle female - kind NPCs", 0.45, 0.7),
    "elli": VoiceProfile("MF3mGyEYCl7XYWbV9V6O", "Elli", "Young, emotional female - young women", 0.35, 0.6),
    "grace": VoiceProfile("oWAxZDx7w5VEj9dCyTzz", "Grace", "Southern American female - innkeepers", 0.5, 0.7),
    "serena": VoiceProfile("pMsXgVXv3BLzUgSXRplE", "Serena", "Soft, pleasant female - merchants", 0.5, 0.75),
    
    # Female Voices - Unique/Character
    "glinda": VoiceProfile("z9fAnlkpzviPz146aGWa", "Glinda", "Witch-like, mystical female - fortune tellers", 0.4, 0.65),
    "mimi": VoiceProfile("zrHiDhphv9ZnVXBqCLjz", "Mimi", "Swedish female - foreign merchants", 0.45, 0.7),
}

# Role-to-Voice Mapping - Now split by gender
# Maps roles to preferred voice styles for each gender
ROLE_VOICE_MAP_MALE = {
    # Guards & Military
    "guard": "adam", "guard_captain": "arnold", "soldier": "clyde",
    "warrior": "arnold", "gatekeeper": "adam", "guarded_gatekeeper": "adam",
    "watchman": "adam", "knight": "arnold", "captain": "arnold", "sentry": "adam",
    
    # Merchants & Traders
    "merchant": "antoni", "trader": "antoni", "shopkeeper": "josh",
    "innkeeper": "antoni", "tavern_keeper": "antoni", "bartender": "antoni",
    "vendor": "josh", "peddler": "charlie", "settler": "ethan",
    
    # Scholars & Mystics
    "scholar": "daniel", "sage": "daniel", "priest": "daniel",
    "healer": "daniel", "fortune_teller": "sam", "mystic": "sam",
    "wizard": "daniel", "alchemist": "daniel",
    
    # Outcasts & Rogues
    "outcast": "sam", "thief": "sam", "beggar": "ethan",
    "rogue": "sam", "criminal": "sam", "smuggler": "sam",
    "assassin": "sam", "spy": "sam",
    
    # Nobles & Elite
    "noble": "daniel", "lord": "daniel", "aristocrat": "daniel",
    "prince": "daniel", "king": "arnold",
    
    # Common Folk
    "citizen": "ethan", "farmer": "josh", "craftsman": "harry",
    "blacksmith": "harry", "villager": "ethan", "peasant": "ethan",
    "miner": "harry", "fisherman": "charlie",
    
    # Special
    "elder": "clyde", "foreigner": "james",
}

ROLE_VOICE_MAP_FEMALE = {
    # Guards & Military
    "guard": "domi", "guard_captain": "domi", "soldier": "domi",
    "warrior": "domi", "gatekeeper": "domi", "guarded_gatekeeper": "domi",
    "watchman": "domi", "knight": "domi", "captain": "domi", "sentry": "domi",
    
    # Merchants & Traders
    "merchant": "serena", "trader": "serena", "shopkeeper": "emily",
    "innkeeper": "grace", "tavern_keeper": "grace", "bartender": "grace",
    "vendor": "emily", "peddler": "mimi", "settler": "bella",
    
    # Scholars & Mystics
    "scholar": "rachel", "sage": "rachel", "priest": "rachel",
    "healer": "rachel", "fortune_teller": "glinda", "mystic": "glinda",
    "wizard": "glinda", "witch": "glinda", "alchemist": "rachel",
    
    # Outcasts & Rogues
    "outcast": "elli", "thief": "elli", "beggar": "elli",
    "rogue": "elli", "criminal": "elli", "smuggler": "elli",
    "assassin": "elli", "spy": "elli",
    
    # Nobles & Elite
    "noble": "charlotte", "lady": "charlotte", "aristocrat": "charlotte",
    "princess": "charlotte", "queen": "charlotte",
    
    # Common Folk
    "citizen": "emily", "farmer": "bella", "craftsman": "emily",
    "villager": "bella", "peasant": "bella",
    
    # Special
    "child": "elli", "elder": "rachel", "foreigner": "mimi",
}

# ============================================================================
# Personality-Based Voice Modifiers
# These create unique "fingerprints" for each NPC
# ============================================================================

def calculate_voice_fingerprint(
    npc_id: str,
    personality: Dict[str, float],
    role: str,
    gender: str = "male"
) -> NPCVoiceFingerprint:
    """
    Calculate a unique voice fingerprint based on NPC personality traits.
    Uses gender-specific voice mappings to ensure correct voice assignment.
    
    Personality traits (0-1 scale):
    - curiosity: Higher = more varied intonation
    - empathy: Higher = softer, warmer voice
    - risk_tolerance: Higher = more confident, louder
    - aggression: Higher = harsher, less stable
    - discipline: Higher = more controlled, stable
    - romanticism: Higher = more expressive style
    - opportunism: Higher = smoother, persuasive
    - paranoia: Higher = more erratic, whisper-like
    """
    
    # Choose the correct role map based on gender
    gender_lower = gender.lower() if gender else "male"
    role_map = ROLE_VOICE_MAP_FEMALE if gender_lower == "female" else ROLE_VOICE_MAP_MALE
    
    # Get base voice from role
    role_lower = role.lower().replace(" ", "_")
    base_voice = role_map.get(role_lower)
    
    # Try partial matching
    if not base_voice:
        for role_key in role_map.keys():
            if role_key in role_lower or role_lower in role_key:
                base_voice = role_map[role_key]
                break
    
    # Default fallback based on gender
    if not base_voice:
        base_voice = "rachel" if gender_lower == "female" else "adam"
    
    # Extract personality traits with defaults
    curiosity = personality.get("curiosity", 0.5)
    empathy = personality.get("empathy", 0.5)
    risk_tolerance = personality.get("risk_tolerance", 0.5)
    aggression = personality.get("aggression", 0.5)
    discipline = personality.get("discipline", 0.5)
    romanticism = personality.get("romanticism", 0.5)
    opportunism = personality.get("opportunism", 0.5)
    paranoia = personality.get("paranoia", 0.5)
    
    # Calculate modifiers based on personality
    
    # Stability: discipline increases, aggression/paranoia decreases
    stability_mod = (discipline - 0.5) * 0.3 - (aggression - 0.5) * 0.2 - (paranoia - 0.5) * 0.25
    
    # Similarity: empathy and discipline increase consistency
    similarity_mod = (empathy - 0.5) * 0.15 + (discipline - 0.5) * 0.2
    
    # Style: romanticism and curiosity increase expressiveness
    style_mod = (romanticism - 0.5) * 0.3 + (curiosity - 0.5) * 0.2
    
    # Speed: risk_tolerance and aggression increase speed
    speed_mod = 1.0 + (risk_tolerance - 0.5) * 0.2 + (aggression - 0.5) * 0.15
    
    # Clamp values
    stability_mod = max(-0.3, min(0.3, stability_mod))
    similarity_mod = max(-0.2, min(0.2, similarity_mod))
    style_mod = max(-0.2, min(0.4, style_mod))
    speed_mod = max(0.7, min(1.3, speed_mod))
    
    # Generate pitch description
    if aggression > 0.7:
        pitch_desc = "harsh, aggressive"
    elif empathy > 0.7:
        pitch_desc = "warm, gentle"
    elif paranoia > 0.7:
        pitch_desc = "nervous, hushed"
    elif discipline > 0.7:
        pitch_desc = "controlled, precise"
    elif romanticism > 0.7:
        pitch_desc = "expressive, dramatic"
    else:
        pitch_desc = "normal"
    
    return NPCVoiceFingerprint(
        npc_id=npc_id,
        base_voice_key=base_voice,
        stability_mod=stability_mod,
        similarity_mod=similarity_mod,
        style_mod=style_mod,
        speed_mod=speed_mod,
        pitch_description=pitch_desc
    )

# Mood-based voice adjustments
MOOD_VOICE_SETTINGS = {
    "angry": {"stability": -0.2, "style": 0.3},
    "sad": {"stability": 0.1, "style": 0.15},
    "happy": {"stability": -0.1, "style": 0.25},
    "fearful": {"stability": -0.25, "style": 0.1},
    "neutral": {"stability": 0.0, "style": 0.0},
    "suspicious": {"stability": -0.1, "style": 0.05},
    "friendly": {"stability": 0.05, "style": 0.2},
    "threatening": {"stability": 0.1, "style": 0.15},
    "nervous": {"stability": -0.3, "style": 0.1},
    "confident": {"stability": 0.15, "style": 0.1},
}


class NPCVoiceSystem:
    """
    Enhanced voice management for NPCs using ElevenLabs.
    Creates unique voice fingerprints based on personality traits.
    Supports voice cloning for custom NPC voices.
    """
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or ELEVENLABS_API_KEY
        self.client = None
        self._voice_fingerprints: Dict[str, NPCVoiceFingerprint] = {}
        self._cloned_voices: Dict[str, VoiceProfile] = {}  # npc_id -> cloned voice
        self._voice_usage_count: Dict[str, int] = {}
        
        if self.api_key:
            self.client = ElevenLabs(api_key=self.api_key)
            print("✓ Enhanced NPC Voice System initialized with ElevenLabs")
        else:
            print("⚠ NPC Voice System: No API key - voice generation disabled")
        
        # Initialize database
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database for voice assignments"""
        Path(VOICE_DB_PATH).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(VOICE_DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS voice_fingerprints (
                npc_id TEXT PRIMARY KEY,
                base_voice_key TEXT,
                stability_mod REAL,
                similarity_mod REAL,
                style_mod REAL,
                speed_mod REAL,
                pitch_description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cloned_voices (
                npc_id TEXT PRIMARY KEY,
                voice_id TEXT,
                voice_name TEXT,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
    
    def assign_unique_voice(
        self,
        npc_id: str,
        role: str,
        gender: str = "male",
        faction: str = "citizens",
        personality: Dict[str, float] = None
    ) -> Tuple[VoiceProfile, NPCVoiceFingerprint]:
        """
        Assign a unique voice to an NPC based on their characteristics.
        Returns both the base voice profile and the unique fingerprint.
        ENSURES each NPC gets a unique base voice when possible.
        """
        # Check for existing cloned voice
        if npc_id in self._cloned_voices:
            cloned = self._cloned_voices[npc_id]
            fingerprint = NPCVoiceFingerprint(npc_id, "cloned", 0, 0, 0, 1.0, "custom")
            return cloned, fingerprint
        
        # Check for existing fingerprint
        if npc_id in self._voice_fingerprints:
            fingerprint = self._voice_fingerprints[npc_id]
            base_profile = VOICE_LIBRARY.get(fingerprint.base_voice_key, VOICE_LIBRARY["adam"])
            return base_profile, fingerprint
        
        # Create new fingerprint based on personality
        personality = personality or {}
        fingerprint = calculate_voice_fingerprint(npc_id, personality, role, gender)
        
        # Apply faction adjustments
        faction_mods = {
            "guards": {"stability_mod": 0.1, "similarity_mod": 0.05},
            "traders": {"stability_mod": -0.05, "style_mod": 0.1},
            "citizens": {"stability_mod": 0.0, "similarity_mod": 0.0},
            "outcasts": {"stability_mod": -0.15, "style_mod": 0.05},
        }
        
        if faction in faction_mods:
            mods = faction_mods[faction]
            fingerprint.stability_mod += mods.get("stability_mod", 0)
            fingerprint.similarity_mod += mods.get("similarity_mod", 0)
            fingerprint.style_mod += mods.get("style_mod", 0)
        
        # ALWAYS try to find a unique voice that hasn't been used yet
        base_voice = fingerprint.base_voice_key
        
        # Check if this voice is already used by another NPC
        voice_already_used = self._voice_usage_count.get(base_voice, 0) > 0
        
        if voice_already_used:
            # Find an unused voice of the same gender
            alternative = self._find_unique_voice(gender)
            if alternative:
                base_voice = alternative
                fingerprint.base_voice_key = alternative
        
        # Track voice usage
        self._voice_usage_count[base_voice] = self._voice_usage_count.get(base_voice, 0) + 1
        
        # Store fingerprint
        self._voice_fingerprints[npc_id] = fingerprint
        self._save_fingerprint(fingerprint)
        
        base_profile = VOICE_LIBRARY.get(fingerprint.base_voice_key, VOICE_LIBRARY["adam"])
        return base_profile, fingerprint
    
    def _find_unique_voice(self, gender: str) -> Optional[str]:
        """Find a voice of the given gender that hasn't been assigned to any NPC yet"""
        gender_voices = {
            "male": ["adam", "antoni", "arnold", "josh", "sam", "daniel", "charlie", "clyde", "ethan", "harry", "james"],
            "female": ["rachel", "domi", "bella", "elli", "emily", "grace", "charlotte", "serena", "glinda", "mimi"]
        }
        
        candidates = gender_voices.get(gender.lower(), gender_voices["male"])
        
        # First, try to find a completely unused voice
        for voice in candidates:
            if self._voice_usage_count.get(voice, 0) == 0:
                return voice
        
        # If all voices of this gender are used, find the least used one
        return self._find_alternative_voice(candidates[0], gender)
    
    def _find_alternative_voice(self, current: str, gender: str) -> str:
        """Find a less-used voice of the same gender"""
        gender_voices = {
            "male": ["adam", "antoni", "arnold", "josh", "sam", "daniel", "charlie", "clyde", "ethan", "harry", "james"],
            "female": ["rachel", "domi", "bella", "elli", "emily", "grace", "charlotte", "serena", "glinda", "mimi"]
        }
        
        candidates = gender_voices.get(gender.lower(), gender_voices["male"])
        min_usage = float('inf')
        best = current
        
        for voice in candidates:
            usage = self._voice_usage_count.get(voice, 0)
            if usage < min_usage:
                min_usage = usage
                best = voice
        
        return best
    
    def _save_fingerprint(self, fingerprint: NPCVoiceFingerprint):
        """Save fingerprint to database"""
        conn = sqlite3.connect(VOICE_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO voice_fingerprints 
            (npc_id, base_voice_key, stability_mod, similarity_mod, style_mod, speed_mod, pitch_description)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            fingerprint.npc_id, fingerprint.base_voice_key,
            fingerprint.stability_mod, fingerprint.similarity_mod,
            fingerprint.style_mod, fingerprint.speed_mod, fingerprint.pitch_description
        ))
        conn.commit()
        conn.close()
    
    def get_npc_voice_info(self, npc_id: str) -> Optional[Dict]:
        """Get complete voice information for an NPC"""
        if npc_id in self._cloned_voices:
            cloned = self._cloned_voices[npc_id]
            return {
                "npc_id": npc_id,
                "type": "cloned",
                "voice_id": cloned.voice_id,
                "voice_name": cloned.voice_name,
                "description": cloned.description,
                "settings": {
                    "stability": cloned.stability,
                    "similarity_boost": cloned.similarity_boost,
                    "style": cloned.style
                }
            }
        
        if npc_id in self._voice_fingerprints:
            fingerprint = self._voice_fingerprints[npc_id]
            base_profile = VOICE_LIBRARY.get(fingerprint.base_voice_key)
            if base_profile:
                effective = fingerprint.get_effective_settings(base_profile)
                return {
                    "npc_id": npc_id,
                    "type": "generated",
                    "base_voice": fingerprint.base_voice_key,
                    "voice_id": base_profile.voice_id,
                    "voice_name": base_profile.voice_name,
                    "pitch_description": fingerprint.pitch_description,
                    "speed_mod": fingerprint.speed_mod,
                    "settings": effective,
                    "modifiers": {
                        "stability_mod": fingerprint.stability_mod,
                        "similarity_mod": fingerprint.similarity_mod,
                        "style_mod": fingerprint.style_mod
                    }
                }
        
        return None
    
    def generate_speech(
        self,
        npc_id: str,
        text: str,
        mood: str = "neutral",
        role: str = "citizen",
        personality: Dict = None
    ) -> Optional[bytes]:
        """
        Generate speech with unique voice fingerprint and mood adjustments.
        """
        if not self.client:
            return None
        
        # Get or create voice info
        voice_info = self.get_npc_voice_info(npc_id)
        
        if not voice_info:
            # Auto-assign voice
            self.assign_unique_voice(npc_id, role, "male", "citizens", personality or {})
            voice_info = self.get_npc_voice_info(npc_id)
        
        if not voice_info:
            return None
        
        # Get mood adjustments
        mood_adj = MOOD_VOICE_SETTINGS.get(mood.lower(), MOOD_VOICE_SETTINGS["neutral"])
        
        # Calculate final settings
        base_stability = voice_info["settings"]["stability"]
        base_similarity = voice_info["settings"]["similarity_boost"]
        base_style = voice_info["settings"]["style"]
        
        final_stability = max(0.1, min(1.0, base_stability + mood_adj["stability"]))
        final_style = max(0.0, min(1.0, base_style + mood_adj["style"]))
        
        try:
            voice_settings = VoiceSettings(
                stability=final_stability,
                similarity_boost=base_similarity,
                style=final_style,
                use_speaker_boost=True
            )
            
            # Generate audio with Turbo model for faster response
            audio_generator = self.client.text_to_speech.convert(
                text=text,
                voice_id=voice_info["voice_id"],
                model_id="eleven_turbo_v2_5",  # ~2x faster than multilingual
                voice_settings=voice_settings
            )
            
            # Collect audio bytes
            audio_data = b""
            for chunk in audio_generator:
                audio_data += chunk
            
            return audio_data
            
        except Exception as e:
            print(f"Voice generation error for {npc_id}: {e}")
            return None
    
    async def generate_speech_async(
        self,
        npc_id: str,
        text: str,
        mood: str = "neutral",
        role: str = "citizen",
        personality: Dict = None
    ) -> Optional[bytes]:
        """Async version of speech generation"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self.generate_speech, npc_id, text, mood, role, personality
        )
    
    async def generate_voice_async(
        self,
        npc_id: str,
        text: str,
        mood: str = "neutral",
        output_format: str = "mp3"
    ) -> Optional[Dict]:
        """
        Generate voice audio for conversation system.
        Returns dict with audio base64, format, and metadata.
        """
        # Generate raw audio
        audio_bytes = await self.generate_speech_async(npc_id, text, mood)
        
        if not audio_bytes:
            return None
        
        # Convert to requested format if needed
        if output_format.lower() == "wav" and audio_bytes:
            try:
                from pydub import AudioSegment
                # ElevenLabs returns MP3
                audio_segment = AudioSegment.from_mp3(io.BytesIO(audio_bytes))
                wav_buffer = io.BytesIO()
                audio_segment.export(wav_buffer, format="wav")
                audio_bytes = wav_buffer.getvalue()
            except Exception as e:
                print(f"WAV conversion error: {e}")
                output_format = "mp3"  # Fall back to MP3
        
        # Get voice info for metadata
        voice_info = self.get_npc_voice_info(npc_id)
        
        return {
            "audio": base64.b64encode(audio_bytes).decode('utf-8'),
            "format": output_format,
            "voice_id": voice_info.get("voice_id", "") if voice_info else "",
            "voice_name": voice_info.get("voice_name", "") if voice_info else "",
            "npc_id": npc_id,
            "text": text,
            "mood": mood,
            "size_bytes": len(audio_bytes)
        }
    
    # ========================================================================
    # Voice Cloning
    # ========================================================================
    
    def clone_voice(
        self,
        npc_id: str,
        audio_files: List[bytes],
        voice_name: str,
        description: str = ""
    ) -> Optional[VoiceProfile]:
        """
        Clone a voice from audio samples for a specific NPC.
        Uses ElevenLabs Instant Voice Cloning (IVC).
        
        Args:
            npc_id: The NPC to assign this voice to
            audio_files: List of audio file bytes (MP3/WAV, 10-20 seconds each)
            voice_name: Name for the cloned voice
            description: Description of the voice
        
        Returns:
            VoiceProfile if successful, None otherwise
        """
        if not self.client:
            return None
        
        try:
            # Convert bytes to file-like objects
            files = [io.BytesIO(audio) for audio in audio_files]
            
            # Clone the voice
            voice = self.client.voices.ivc.create(
                name=f"NPC_{npc_id}_{voice_name}",
                files=files,
                description=description or f"Custom voice for NPC {npc_id}"
            )
            
            # Create profile
            profile = VoiceProfile(
                voice_id=voice.voice_id,
                voice_name=voice_name,
                description=description,
                stability=0.5,
                similarity_boost=0.75,
                style=0.0,
                use_speaker_boost=True,
                is_cloned=True
            )
            
            # Store
            self._cloned_voices[npc_id] = profile
            self._save_cloned_voice(npc_id, profile)
            
            print(f"✓ Voice cloned for NPC {npc_id}: {voice_name}")
            return profile
            
        except Exception as e:
            print(f"Voice cloning error: {e}")
            return None
    
    def _save_cloned_voice(self, npc_id: str, profile: VoiceProfile):
        """Save cloned voice to database"""
        conn = sqlite3.connect(VOICE_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO cloned_voices 
            (npc_id, voice_id, voice_name, description)
            VALUES (?, ?, ?, ?)
        """, (npc_id, profile.voice_id, profile.voice_name, profile.description))
        conn.commit()
        conn.close()
    
    def delete_cloned_voice(self, npc_id: str) -> bool:
        """Delete a cloned voice"""
        if npc_id not in self._cloned_voices:
            return False
        
        try:
            profile = self._cloned_voices[npc_id]
            # Delete from ElevenLabs
            self.client.voices.delete(profile.voice_id)
            
            # Remove from local storage
            del self._cloned_voices[npc_id]
            
            # Remove from database
            conn = sqlite3.connect(VOICE_DB_PATH)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM cloned_voices WHERE npc_id = ?", (npc_id,))
            conn.commit()
            conn.close()
            
            return True
        except Exception as e:
            print(f"Error deleting cloned voice: {e}")
            return False
    
    def get_available_voices(self) -> List[Dict]:
        """Get all available voices (library + cloned)"""
        voices = []
        
        # Library voices
        for key, profile in VOICE_LIBRARY.items():
            voices.append({
                "key": key,
                "voice_id": profile.voice_id,
                "name": profile.voice_name,
                "description": profile.description,
                "type": "library",
                "default_settings": {
                    "stability": profile.stability,
                    "similarity_boost": profile.similarity_boost,
                    "style": profile.style
                }
            })
        
        # Cloned voices
        for npc_id, profile in self._cloned_voices.items():
            voices.append({
                "key": f"cloned_{npc_id}",
                "voice_id": profile.voice_id,
                "name": profile.voice_name,
                "description": profile.description,
                "type": "cloned",
                "npc_id": npc_id
            })
        
        return voices
    
    def get_all_assignments(self) -> Dict[str, Dict]:
        """Get all NPC voice assignments with full details"""
        assignments = {}
        
        for npc_id in set(list(self._voice_fingerprints.keys()) + list(self._cloned_voices.keys())):
            info = self.get_npc_voice_info(npc_id)
            if info:
                assignments[npc_id] = info
        
        return assignments
    
    def get_stats(self) -> Dict:
        """Get voice system statistics"""
        return {
            "enabled": self.client is not None,
            "library_voices": len(VOICE_LIBRARY),
            "cloned_voices": len(self._cloned_voices),
            "assigned_npcs": len(self._voice_fingerprints) + len(self._cloned_voices),
            "voice_usage": dict(self._voice_usage_count),
            "unique_fingerprints": len(self._voice_fingerprints)
        }
    
    def preview_fingerprint(
        self,
        role: str,
        gender: str = "male",
        personality: Dict[str, float] = None
    ) -> Dict:
        """
        Preview what voice fingerprint would be generated for given parameters.
        Useful for testing without creating an assignment.
        """
        personality = personality or {}
        fingerprint = calculate_voice_fingerprint("preview", personality, role, gender)
        base_profile = VOICE_LIBRARY.get(fingerprint.base_voice_key, VOICE_LIBRARY["adam"])
        effective = fingerprint.get_effective_settings(base_profile)
        
        return {
            "base_voice": fingerprint.base_voice_key,
            "voice_name": base_profile.voice_name,
            "pitch_description": fingerprint.pitch_description,
            "speed_mod": fingerprint.speed_mod,
            "effective_settings": effective,
            "modifiers": {
                "stability_mod": round(fingerprint.stability_mod, 3),
                "similarity_mod": round(fingerprint.similarity_mod, 3),
                "style_mod": round(fingerprint.style_mod, 3)
            }
        }
    
    def reset_voice_assignment(self, npc_id: str) -> bool:
        """
        Remove an NPC's voice assignment so it can be reassigned.
        Returns True if the voice was removed.
        """
        if npc_id in self._voice_fingerprints:
            fingerprint = self._voice_fingerprints[npc_id]
            # Decrease usage count
            if fingerprint.base_voice_key in self._voice_usage_count:
                self._voice_usage_count[fingerprint.base_voice_key] -= 1
                if self._voice_usage_count[fingerprint.base_voice_key] <= 0:
                    del self._voice_usage_count[fingerprint.base_voice_key]
            
            # Remove from memory
            del self._voice_fingerprints[npc_id]
            
            # Remove from database
            try:
                conn = sqlite3.connect(VOICE_DB_PATH)
                cursor = conn.cursor()
                cursor.execute("DELETE FROM voice_fingerprints WHERE npc_id = ?", (npc_id,))
                conn.commit()
                conn.close()
            except Exception as e:
                print(f"Error removing voice from DB: {e}")
            
            return True
        return False
    
    def reset_all_voices(self) -> Dict:
        """
        Clear all voice assignments. Use to fix voice conflicts.
        Returns count of cleared assignments.
        """
        count = len(self._voice_fingerprints)
        self._voice_fingerprints.clear()
        self._voice_usage_count.clear()
        
        try:
            conn = sqlite3.connect(VOICE_DB_PATH)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM voice_fingerprints")
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error clearing voice DB: {e}")
        
        return {"cleared": count}


# ============================================================================
# Global Instance
# ============================================================================

# Create global enhanced voice system instance
npc_voice_system = NPCVoiceSystem()
