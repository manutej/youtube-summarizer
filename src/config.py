"""Configuration management for YouTube Summarizer."""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Load environment variables
load_dotenv()


class Config(BaseModel):
    """Application configuration."""

    # API Configuration
    anthropic_api_key: str = Field(
        default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", "")
    )
    claude_model: str = Field(
        default_factory=lambda: os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")
    )

    # Output Configuration
    output_dir: Path = Field(
        default_factory=lambda: Path(os.getenv("OUTPUT_DIR", "summaries"))
    )
    docs_dir: Path = Field(default=Path("docs"))

    # Processing Configuration
    max_tokens: int = Field(
        default_factory=lambda: int(os.getenv("MAX_TOKENS", "4096"))
    )
    chunk_size: int = 1000  # tokens
    chunk_overlap: int = 200  # tokens

    # Transcript Configuration
    preferred_languages: list[str] = ["en", "en-US", "en-GB"]
    fallback_to_auto_generated: bool = True

    def validate_api_key(self) -> bool:
        """Validate that API key is set."""
        return bool(self.anthropic_api_key and self.anthropic_api_key != "")

    def ensure_directories(self) -> None:
        """Ensure output directories exist."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.docs_dir.mkdir(parents=True, exist_ok=True)


# Global configuration instance
config = Config()
