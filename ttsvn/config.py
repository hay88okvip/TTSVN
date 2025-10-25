"""Configuration management for the TTSVN application."""
from __future__ import annotations

from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any, Dict, Optional
import json

CONFIG_DIR = Path.home() / ".ttsvn"
CONFIG_PATH = CONFIG_DIR / "config.json"


@dataclass
class ApiSettings:
    """Holds ViettelAI API configuration."""

    token: str = ""
    synthesize_url: str = "https://viettelai.vn/tts/api/tts/v1"
    voices_url: str = "https://viettelai.vn/tts/api/tts/v1/voices"
    timeout: int = 60

    def headers(self) -> Dict[str, str]:
        """Return default headers for ViettelAI requests."""
        headers: Dict[str, str] = {
            "Content-Type": "application/json",
        }
        if self.token:
            # ViettelAI currently expects the token to be sent via the ``token`` header.
            headers["token"] = self.token
        return headers


@dataclass
class AudioDefaults:
    """Default synthesis values used when the user has not provided overrides."""

    voice: str = "hn_female_ngocanh_neural"
    format: str = "mp3"
    sample_rate: int = 22050
    speed: float = 1.0
    volume: float = 1.0
    pitch: float = 1.0


@dataclass
class AppConfig:
    """Represents the persisted configuration of the application."""

    api: ApiSettings = field(default_factory=ApiSettings)
    audio: AudioDefaults = field(default_factory=AudioDefaults)
    output_directory: str = str(Path.home() / "TTSVN")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AppConfig":
        api_data = data.get("api", {})
        audio_data = data.get("audio", {})
        return cls(
            api=ApiSettings(**api_data),
            audio=AudioDefaults(**audio_data),
            output_directory=data.get("output_directory", str(Path.home() / "TTSVN")),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "api": asdict(self.api),
            "audio": asdict(self.audio),
            "output_directory": self.output_directory,
        }

    def ensure_directories(self) -> None:
        Path(self.output_directory).expanduser().mkdir(parents=True, exist_ok=True)
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load_config(path: Optional[Path] = None) -> AppConfig:
    """Load an :class:`AppConfig` from disk, returning defaults if unavailable."""
    config_path = path or CONFIG_PATH
    if not config_path.exists():
        config = AppConfig()
        config.ensure_directories()
        save_config(config, config_path)
        return config

    try:
        with config_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (json.JSONDecodeError, OSError):
        data = AppConfig().to_dict()
    config = AppConfig.from_dict(data)
    config.ensure_directories()
    return config


def save_config(config: AppConfig, path: Optional[Path] = None) -> None:
    """Persist the provided configuration to disk."""
    config_path = path or CONFIG_PATH
    config.ensure_directories()
    with config_path.open("w", encoding="utf-8") as handle:
        json.dump(config.to_dict(), handle, indent=2, ensure_ascii=False)
