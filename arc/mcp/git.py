"""
Git operations module via MCP.
Provides high-level wrappers for Git and GitHub workflows.
"""
import logging
from typing import Optional, List, Any
from arc.mcp.client import get_mcp_manager

logger = logging.getLogger(__name__)

class GitClient:
    def __init__(self):
        self.manager = get_mcp_manager()
        self.server_name = "git"

    async def _call(self, tool_name: str, args: dict) -> Any:
        try:
            return await self.manager.call_tool(self.server_name, tool_name, args)
        except Exception as e:
            logger.error(f"Git tool execution failed ({tool_name}): {e}")
            raise

    async def status(self) -> str:
        """Get git status."""
        result = await self._call("git_status", {})
        return result.get("content", [{}])[0].get("text", "") if hasattr(result, "content") else str(result)

    async def smart_pull(self):
        """Pull changes, handling rebase if configured."""
        logger.info("Pulling changes...")
        return await self._call("git_pull", {})

    async def smart_push(self):
        """Push changes to remote."""
        logger.info("Pushing changes...")
        return await self._call("git_push", {})

    async def create_feature_branch(self, name: str):
        """Create and checkout a new feature branch."""
        logger.info(f"Creating branch: {name}")
        return await self._call("git_create_branch", {"name": name})

    # GitHub Operations (assuming git-mcp-server supports them or we have a github specific server)
    async def create_pr(self, title: str, body: str):
        """Create a Pull Request."""
        logger.info(f"Creating PR: {title}")
        # Note: tool names depend on the specific git server capabilities
        return await self._call("github_create_pr", {"title": title, "body": body})

    async def list_prs(self, state: str = "open"):
        """List Pull Requests."""
        return await self._call("github_list_prs", {"state": state})

def get_git_client() -> GitClient:
    return GitClient()
