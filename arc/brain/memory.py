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
                result_summary=str(result_summary)[:200] # Truncate for sanity
            )
            
            # Load, append, save (inefficient but safe for Phase 3)
            data = json.loads(EPISODIC_FILE.read_text(encoding="utf-8"))
            data.append(entry)
            EPISODIC_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
            logger.info(f"🧪 Episodic Memory Logged: {tool} -> {outcome}")
            
        except Exception as e:
            logger.error(f"Failed to log episodic memory: {e}")

    def update_profile(self, new_facts: List[str]):
        """Update user profile with new facts."""
        if not new_facts:
            return
            
        try:
            data = json.loads(LONG_TERM_FILE.read_text(encoding="utf-8"))
            current_facts = set(data.get("facts", []))
            
            updated = False
            for fact in new_facts:
                if fact not in current_facts:
                    data["facts"].append(fact)
                    updated = True
                    logger.info(f"📒 Long-Term Memory Updated: {fact}")
            
            if updated:
                LONG_TERM_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
                
        except Exception as e:
            logger.error(f"Failed to update user profile: {e}")

    def get_profile(self) -> List[str]:
        """Read user facts from long-term memory."""
        try:
            if not LONG_TERM_FILE.exists():
                return []
            data = json.loads(LONG_TERM_FILE.read_text(encoding="utf-8"))
            return data.get("facts", [])
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
            logger.error(f"Failed to read episodic memory: {e}")
            return []

# Singleton
_memory_manager = None
def get_memory_manager():
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager()
    return _memory_manager
