"""
Embedded Filesystem MCP Server for ARC.
Provides safe, sandboxed file operations.
"""
import os
import logging
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Union, Any

from arc.config import get_config

logger = logging.getLogger(__name__)

class FilesystemMCP:
    """
    Filesystem Tool Provider.
    Executes file operations within allowed roots.
    """
    def __init__(self):
        self.config = get_config()
        # Load roots from config or default to CWD
        self.allowed_roots = [Path(r).resolve() for r in getattr(self.config, "allowed_roots", [os.getcwd()])]
        
        # Security Warning
        if any(r == Path.cwd() for r in self.allowed_roots):
            logger.warning("⚠️  Filesystem MCP is using CWD as an allowed root. This is risky.")

    def _validate_path(self, path_str: str) -> Optional[Path]:
        """
        Resolve path and check if it's within allowed roots.
        Returns Path object if valid, None if invalid.
        """
        try:
            # Handle relative paths assumes relative to CWD, but must check if that resolves to inside a root
            # For simplicity, we treat inputs as relative to CWD if not absolute
            target = Path(path_str).resolve()
            
            for root in self.allowed_roots:
                # Check if target is inside root
                if root in target.parents or root == target:
                    return target
            
            logger.warning(f"🚫 Access Denied: {path_str} (Resolved: {target}) not in {self.allowed_roots}")
            return None
            
        except Exception as e:
            logger.error(f"Path validation error: {e}")
            return None

    def execute(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Dispatcher for filesystem tools.
        """
        try:
            if tool_name in ["list_directory", "list_files"]: # Alias
                return self.list_directory(args.get("path", "."))
            elif tool_name == "read_file":
                return self.read_file(args.get("path", ""))
            elif tool_name == "write_file":
                return self.write_file(args.get("path", ""), args.get("content", ""))
            elif tool_name == "create_file":
                return self.create_file(args.get("path", "")) # Empty file
            elif tool_name == "delete_file":
                return self.delete_file(args.get("path", ""))
            else:
                 return {"status": "error", "error": f"Unknown tool: {tool_name}", "data": None}
                 
        except Exception as e:
            logger.error(f"MCP Execute Error: {e}")
            return {"status": "error", "error": str(e), "data": None}

    def list_directory(self, path_str: str) -> Dict[str, Any]:
        target = self._validate_path(path_str)
        if not target:
            return {"status": "error", "error": "Access denied: Path outside allowed roots.", "data": None}
            
        if not target.exists() or not target.is_dir():
             return {"status": "error", "error": "Directory not found.", "data": None}
             
        try:
            items = []
            for item in target.iterdir():
                kind = "DIR" if item.is_dir() else "FILE"
                items.append(f"[{kind}] {item.name}")
            return {"status": "success", "data": "\n".join(items), "error": None}
        except Exception as e:
             return {"status": "error", "error": str(e), "data": None}

    def read_file(self, path_str: str) -> Dict[str, Any]:
        target = self._validate_path(path_str)
        if not target:
            return {"status": "error", "error": "Access denied.", "data": None}
            
        if not target.exists() or not target.is_file():
             return {"status": "error", "error": "File not found.", "data": None}
             
        try:
            content = target.read_text(encoding="utf-8")
            return {"status": "success", "data": content, "error": None}
        except Exception as e:
             return {"status": "error", "error": str(e), "data": None}

    def write_file(self, path_str: str, content: str) -> Dict[str, Any]:
        target = self._validate_path(path_str)
        if not target:
            return {"status": "error", "error": "Access denied.", "data": None}
             
        try:
            target.write_text(content, encoding="utf-8")
            return {"status": "success", "data": f"Written {len(content)} chars to {target.name}", "error": None}
        except Exception as e:
             return {"status": "error", "error": str(e), "data": None}

    def create_file(self, path_str: str) -> Dict[str, Any]:
        return self.write_file(path_str, "")

    def delete_file(self, path_str: str) -> Dict[str, Any]:
        target = self._validate_path(path_str)
        if not target:
            return {"status": "error", "error": "Access denied.", "data": None}
            
        if not target.exists():
             return {"status": "error", "error": "File not found.", "data": None}
             
        try:
            os.remove(target)
            return {"status": "success", "data": f"Deleted {target.name}", "error": None}
        except Exception as e:
             return {"status": "error", "error": str(e), "data": None}
