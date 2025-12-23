"""
Configuration management for ARC using Pydantic Settings.
"""
import os
from pathlib import Path
from typing import Optional, List, Literal
from pydantic import BaseModel, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# Define default paths
PROJECT_ROOT = Path(__file__).parent.parent
DEFAULT_MODELS_DIR = PROJECT_ROOT / "models"
DEFAULT_LOGS_DIR = PROJECT_ROOT / "logs"

class LLMConfig(BaseModel):
    backend: Literal["llamacpp", "ollama", "openai"] = Field("llamacpp", description="LLM backend to use")
    model_path: Optional[str] = Field(None, description="Path to the local LLM model file (for llamacpp)")
    model_name: Optional[str] = Field(None, description="Model name (for ollama/openai)")
    base_url: Optional[str] = Field(None, description="Base URL (for ollama/openai)")
    context_size: int = Field(2048, description="Context window size")
    gpu_layers: int = Field(0, description="Number of layers to offload to GPU")
    temperature: float = Field(0.7, description="Generation temperature")
    api_key: Optional[SecretStr] = Field(None, description="API Key for external LLM providers")

class MCPServerConfig(BaseModel):
    command: str
    args: List[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)
    enabled: bool = True

class MCPConfig(BaseModel):
    enabled: bool = True
    servers: dict[str, MCPServerConfig] = Field(default_factory=lambda: {
        "browser": MCPServerConfig(
            command="npx",
            args=["-y", "@browsermcp/server"],
        ),
        "git": MCPServerConfig(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-git"],
        ),
        "filesystem": MCPServerConfig(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem", "."],
        ),
        "python": MCPServerConfig( # Placeholder for python execution server
            command="python3",
            args=["-m", "mcp_server_python"], # Hypothetical or local module
            enabled=False # Disabled by default until configured
        ),
        "email": MCPServerConfig(
             command="npx",
             args=["-y", "mcp-server-email"], # Hypothetical
             enabled=False
        )
    })
    server_registry_path: Optional[str] = None
    trusted_servers: List[str] = Field(default_factory=list)

class VoiceConfig(BaseModel):
    wake_word: str = Field("jarvis", description="Wake word to listen for")
    porcupine_access_key: Optional[SecretStr] = Field(None, description="Access key for Porcupine")
    stt_model_size: Literal["tiny", "tiny.en", "base", "base.en", "small", "small.en", "medium", "medium.en", "large"] = "base"
    tts_voice: str = "en_US-lessac-medium"

class SystemConfig(BaseModel):
    project_root: Path = Field(default=PROJECT_ROOT)
    models_dir: Path = Field(default=DEFAULT_MODELS_DIR)
    logs_dir: Path = Field(default=DEFAULT_LOGS_DIR)
    debug: bool = False

class EmailConfig(BaseModel):
    user: Optional[str] = None
    password: Optional[SecretStr] = None
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587

class SafetyConfig(BaseModel):
    confirm_destructive_actions: bool = True
    allowed_shell_commands: List[str] = Field(default_factory=lambda: ["ls", "echo", "pwd"])

class Settings(BaseSettings):
    """
    Main settings class.
    Reads from environment variables with prefix 'ARC_'.
    Unprefixed variables are also checked for legacy/compatibility support if needed,
    but we prefer structured config.
    """
    
    # Nested configurations
    llm: LLMConfig = Field(default_factory=LLMConfig)
    mcp: MCPConfig = Field(default_factory=MCPConfig)
    voice: VoiceConfig = Field(default_factory=VoiceConfig)
    system: SystemConfig = Field(default_factory=SystemConfig)
    email: EmailConfig = Field(default_factory=EmailConfig)
    safety: SafetyConfig = Field(default_factory=SafetyConfig)
    
    # Top-level integration keys (legacy/convenience)
    github_token: Optional[SecretStr] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",  # Allows ARC_LLM__MODEL_PATH
        extra="ignore"
    )

# Singleton instance
_settings: Optional[Settings] = None

def get_config() -> Settings:
    """
    Returns the singleton configuration instance.
    """
    global _settings
    if _settings is None:
        # Create default directories if they don't exist
        start_up_settings = Settings()
        start_up_settings.system.models_dir.mkdir(parents=True, exist_ok=True)
        start_up_settings.system.logs_dir.mkdir(parents=True, exist_ok=True)
        _settings = start_up_settings
        
    return _settings

# For backwards compatibility if necessary, though we recommend using get_config()
def load_config():
    return get_config().model_dump()
