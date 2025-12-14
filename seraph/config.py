# ==============================================================================
# SERAPH CONFIGURATION
# ==============================================================================
import os
from dataclasses import dataclass, field
from typing import Optional, List

@dataclass
class SeraphConfig:
    """Seraph AI Configuration - Environment aware"""
    
    # API Settings
    api_key: Optional[str] = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY"))
    model: str = field(default_factory=lambda: os.getenv("SERAPH_MODEL", "claude-sonnet-4-5-20250929"))
    max_tokens: int = 1024
    temperature: float = 0.7
    
    # Memory Settings
    memory_enabled: bool = True
    memory_max_messages: int = 50
    memory_ttl_seconds: int = 3600 * 24  # 24 hours
    
    # Redis Settings (for memory)
    redis_host: str = field(default_factory=lambda: os.getenv("REDIS_HOST", "127.0.0.1"))
    redis_port: int = field(default_factory=lambda: int(os.getenv("REDIS_PORT", "16379")))
    redis_password: str = field(default_factory=lambda: os.getenv("REDIS_PASS", "voltran2024"))
    
    # Tool Settings
    tools_enabled: bool = True
    allowed_tools: List[str] = field(default_factory=lambda: [
        "get_market_data",
        "get_portfolio",
        "get_system_state",
        "get_dna_params",
        "get_voltran_signals"
    ])
    
    # Safety Settings
    max_actions_per_response: int = 5
    require_confirmation_for_trades: bool = True
    
    @classmethod
    def from_env(cls) -> "SeraphConfig":
        """Load config from environment variables"""
        return cls()
    
    def validate(self) -> bool:
        """Validate configuration"""
        if not self.api_key:
            return False
        if self.memory_max_messages < 1:
            return False
        return True

