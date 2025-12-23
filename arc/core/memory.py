"""
Memory management module.
Handles short-term (in-memory) and long-term (SQLite) memory with encryption.
"""
import logging
import sqlite3
import json
from typing import Optional, List, Any, Dict
from pathlib import Path
from cryptography.fernet import Fernet
from arc.config import get_config

logger = logging.getLogger(__name__)

class MemoryManager:
    def __init__(self):
        self.config = get_config()
        self.short_term_memory: List[Dict[str, Any]] = []
        
        # Setup Long-term DB
        self.db_path = self.config.system.models_dir / "memory.db"
        self._init_db()
        
        # Setup Encryption
        # In a real app, this key should be persistent and secure (e.g. Keychain)
        # For this prototype, we'll use a deterministically generated key or env var if available
        # simplified for now: generating a fresh key if not found in env (volatile for now)
        # TODO: Persist key properly
        self.key = Fernet.generate_key() 
        self.cipher = Fernet(self.key)

    def _init_db(self):
        """Initialize SQLite database for long-term memory."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS memories (
                        key TEXT PRIMARY KEY,
                        value TEXT,
                        type TEXT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        encrypted BOOLEAN DEFAULT 0
                    )
                """)
                # Enable vector search extension if available for semantic search in future
                # For now, simple keyword search
        except Exception as e:
            logger.error(f"Failed to init memory DB: {e}")

    def add_short_term(self, items: Dict[str, Any]):
        """Add item to short-term session memory."""
        self.short_term_memory.append(items)

    def get_short_term(self) -> List[Dict[str, Any]]:
        return self.short_term_memory

    def store_long_term(self, key: str, value: Any, encrypt: bool = False):
        """
        Store a value in long-term memory.
        """
        json_val = json.dumps(value)
        if encrypt:
            json_val = self.cipher.encrypt(json_val.encode()).decode()
            
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO memories (key, value, type, encrypted) VALUES (?, ?, ?, ?)",
                    (key, json_val, "general", encrypt)
                )
            logger.debug(f"Stored memory: {key}")
        except Exception as e:
            logger.error(f"Failed to store memory {key}: {e}")

    def retrieve_long_term(self, key: str) -> Any:
        """
        Retrieve a value from long-term memory.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT value, encrypted FROM memories WHERE key = ?", (key,))
                row = cursor.fetchone()
                
            if row:
                val, encrypted = row
                if encrypted:
                    try:
                        val = self.cipher.decrypt(val.encode()).decode()
                    except Exception as e:
                        logger.error(f"Decryption failed for {key}: {e}")
                        return None
                return json.loads(val)
            return None
        except Exception as e:
            logger.error(f"Failed to retrieve memory {key}: {e}")
            return None

    def search_memory(self, query: str) -> List[Dict[str, Any]]:
        """
        Simple keyword search in long-term memory keys.
        """
        results = []
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Naive LIKE search, unsafe if query not sanitized but parameterized query handles it
                cursor = conn.execute("SELECT key, value, encrypted FROM memories WHERE key LIKE ?", (f"%{query}%",))
                for key, val, encrypted in cursor.fetchall():
                    if encrypted:
                        try:
                            val = self.cipher.decrypt(val.encode()).decode()
                        except:
                            val = "<encrypted>" # Skip if fail
                    
                    try:
                        decoded_val = json.loads(val)
                    except:
                        decoded_val = val
                        
                    results.append({"key": key, "value": decoded_val})
        except Exception as e:
            logger.error(f"Memory search failed: {e}")
        return results

    def forget(self, key: str):
        """Remove a memory."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM memories WHERE key = ?", (key,))
        except Exception as e:
            logger.error(f"Failed to delete memory {key}: {e}")

# Singleton
_memory_manager: Optional[MemoryManager] = None

def get_memory_manager() -> MemoryManager:
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager()
    return _memory_manager
