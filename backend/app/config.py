"""
Application configuration management.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database
    database_url: str = "sqlite+aiosqlite:///./eldorado.db"
    
    # Server
    backend_host: str = "127.0.0.1"
    backend_port: int = 8000
    
    # Discord
    discord_webhook_url: Optional[str] = None
    
    # Security
    extension_secret_key: str = "change-this-to-a-random-secret-key"
    
    # Logging
    log_level: str = "INFO"
    
    # Application
    app_name: str = "Eldorado Boosting Assistant"
    app_version: str = "0.1.0"
    debug: bool = False
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    @property
    def is_discord_configured(self) -> bool:
        """Check if Discord webhook is configured."""
        return self.discord_webhook_url is not None and len(self.discord_webhook_url) > 0


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get the global settings instance."""
    return settings
