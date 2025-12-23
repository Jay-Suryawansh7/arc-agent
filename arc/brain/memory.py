"""
ARC Memory System - Phase 3
Handles simple JSON-based persistence for Episodic and Long-Term memory.
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import TypedDict, List, Optional, Dict, Any

from arc.config import get_config

logger = logging.getLogger(__name__)

# --- Configurations ---
MEMORY_DIR = Path("C:/arc-agent/memory")
EPISODIC_FILE = MEMORY_DIR / "episodic.json"
LONG_TERM_FILE = MEMORY_DIR / "user_profile.json"

# --- Types ---
class EpisodicEntry(TypedDict):
    timestamp: str
    intent: str
    tool: str
    args: Dict[str, Any]
    outcome: str # "success" or "failure"
    result_summary: str

class UserProfile(TypedDict):
    facts: List[str]
    preferences: Dict[str, Any]

# --- Memory Manager ---
class MemoryManager:
    def __init__(self):
        self._ensure_storage()

    def _ensure_storage(self):
        """Create memory directory and files if missing."""
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        
        if not EPISODIC_FILE.exists():
            EPISODIC_FILE.write_text("[]", encoding="utf-8")
            
        if not LONG_TERM_FILE.exists():
            default_profile = {"facts": [], "preferences": {}}
            LONG_TERM_FILE.write_text(json.dumps(default_profile, indent=2), encoding="utf-8")

    def log_episodic(self, intent: str, tool: str, args: dict, outcome: str, result_summary: str):
        """Append a record to episodic memory."""
        try:
            entry = EpisodicEntry(
                timestamp=datetime.now().isoformat(),
                intent=intent,
                tool=tool,
                args=args,
                outcome=outcome,
                result_summary=str(result_summary)[:200]
            )
            
            data = json.loads(EPISODIC_FILE.read_text(encoding="utf-8"))
            data.append(entry)
            EPISODIC_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
            logger.info(f"🧪 Episodic Logged: {tool}")
            
        except Exception as e:
            logger.error(f"Failed to log episodic: {e}")

    def update_profile(self, new_facts: List[str]):
        """
        Update user profile with new facts (Phase 5: +Metadata).
        Lazy Decay happens here.
        """
        if not new_facts:
            return
            
        try:
            data = json.loads(LONG_TERM_FILE.read_text(encoding="utf-8"))
            
            # --- Schema Migration (String -> Dict) ---
            raw_facts = data.get("facts", [])
            structured_facts = []
            for f in raw_facts:
                if isinstance(f, str):
                    structured_facts.append({
                        "text": f,
                        "last_used": datetime.now().isoformat(),
                        "strength": 1
                    })
                else:
                    structured_facts.append(f)
            
            # --- Update / Add ---
            now_str = datetime.now().isoformat()
            
            for new_f in new_facts:
                found = False
                for existing in structured_facts:
                    if existing["text"].lower() == new_f.lower():
                        existing["last_used"] = now_str
                        existing["strength"] = min(existing.get("strength", 1) + 1, 5) # Cap at 5
                        found = True
                        break
                
                if not found:
                    structured_facts.append({
                        "text": new_f,
                        "last_used": now_str,
                        "strength": 1
                    })
                    logger.info(f"📒 Learned: {new_f}")

            # --- Lazy Decay ---
            self._apply_decay(structured_facts)
            
            data["facts"] = structured_facts
            LONG_TERM_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
                
        except Exception as e:
            logger.error(f"Failed to update profile: {e}")

    def _apply_decay(self, facts: List[Dict]):
        """
        Remove weak/old facts.
        Rule: If not used in 30 days -> Remove.
        """
        decayed_indices = []
        now = datetime.now()
        
        for i, fact in enumerate(facts):
            last_used = datetime.fromisoformat(fact["last_used"])
            days_inactive = (now - last_used).days
            
            if days_inactive > 30:
                decayed_indices.append(i)
        
        # Remove in reverse to preserve indices
        for i in sorted(decayed_indices, reverse=True):
            removed = facts.pop(i)
            logger.info(f"🍂 Forgot: {removed['text']} (Decay)")

    def get_profile(self) -> List[str]:
        """Read user facts (simplified for consumption)."""
        try:
            if not LONG_TERM_FILE.exists():
                return []
            data = json.loads(LONG_TERM_FILE.read_text(encoding="utf-8"))
            
            # Extract text from dicts
            return [f["text"] if isinstance(f, dict) else f for f in data.get("facts", [])]
        except Exception as e:
            logger.error(f"Failed to read profile: {e}")
            return []

    def get_recent_episodic(self, limit: int = 3) -> List[EpisodicEntry]:
        """Read recent episodic memory."""
        try:
            if not EPISODIC_FILE.exists():
                return []
            data = json.loads(EPISODIC_FILE.read_text(encoding="utf-8"))
            return data[-limit:] if data else []
        except Exception as e:
            logger.error(f"Failed to read episodic: {e}")
            return []
            
    def delete_last_episodic(self):
        """Phase 5 Control: Forget last action."""
        try:
            if not EPISODIC_FILE.exists(): return
            data = json.loads(EPISODIC_FILE.read_text(encoding="utf-8"))
            if data:
                removed = data.pop()
                EPISODIC_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
                logger.info("🗑️ Deleted last episodic memory.")
        except Exception as e:
            logger.error(f"Delete failed: {e}")

    def clear_profile(self):
        """Phase 5 Control: Wipe facts."""
        try:
            default_profile = {"facts": [], "preferences": {}}
            LONG_TERM_FILE.write_text(json.dumps(default_profile, indent=2), encoding="utf-8")
            logger.info("🧹 Wiped user profile.")
        except Exception as e:
            logger.error(f"Clear failed: {e}")

# Singleton
_memory_manager = None
def get_memory_manager():
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager()
    return _memory_manager
