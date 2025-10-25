"""Client for interacting with the ViettelAI Text-to-Speech service."""
from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import List, Optional, Sequence

import requests

from .config import ApiSettings


class ViettelAIError(RuntimeError):
    """Raised when the ViettelAI service returns an error."""

    def __init__(self, message: str, *, status_code: Optional[int] = None) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass
class Voice:
    """Represents a voice returned from the ViettelAI service."""

    code: str
    name: str
    gender: Optional[str] = None
    language: Optional[str] = None
    description: Optional[str] = None


@dataclass
class SynthesisRequest:
    """Encapsulates the parameters required for a synthesis request."""

    text: str
    voice: str
    audio_format: str
    sample_rate: int
    speed: float
    volume: float
    pitch: float


@dataclass
class SynthesisResult:
    """Represents an audio asset returned from ViettelAI."""

    audio_bytes: bytes
    audio_format: str
    request: SynthesisRequest

    @property
    def suggested_filename(self) -> str:
        safe_voice = self.request.voice.replace("/", "-")
        return f"viettelai_{safe_voice}.{self.audio_format}"


class ViettelAITextToSpeechClient:
    """High-level helper around the ViettelAI REST API."""

    def __init__(self, settings: ApiSettings, session: Optional[requests.Session] = None) -> None:
        self._settings = settings
        self._session = session or requests.Session()

    @property
    def settings(self) -> ApiSettings:
        return self._settings

    def list_voices(self) -> Sequence[Voice]:
        """Return the list of voices available on the ViettelAI service."""
        response = self._session.get(
            self._settings.voices_url,
            headers=self._settings.headers(),
            timeout=self._settings.timeout,
        )
        if response.status_code >= 400:
            raise ViettelAIError(
                f"ViettelAI voice list failed with status {response.status_code}",
                status_code=response.status_code,
            )
        try:
            data = response.json()
        except ValueError as exc:  # pragma: no cover - defensive
            raise ViettelAIError("Could not decode voice list response as JSON") from exc

        voices_data: List[Voice] = []
        items = data.get("voices") or data.get("data") or data
        if isinstance(items, dict):
            items = items.get("voices") or items.get("items") or []
        if not isinstance(items, list):
            raise ViettelAIError("Unexpected voice list schema returned by ViettelAI")
        for item in items:
            if not isinstance(item, dict):  # pragma: no cover - defensive
                continue
            voices_data.append(
                Voice(
                    code=item.get("code") or item.get("id") or item.get("name", ""),
                    name=item.get("name") or item.get("description") or item.get("code", ""),
                    gender=item.get("gender"),
                    language=item.get("language"),
                    description=item.get("description"),
                )
            )
        return voices_data

    def synthesize(self, request: SynthesisRequest) -> SynthesisResult:
        """Perform a synthesis request and return the audio bytes."""
        payload = {
            "text": request.text,
            "voice": request.voice,
            "format": request.audio_format,
            "sample_rate": request.sample_rate,
            "speed": request.speed,
            "volume": request.volume,
            "pitch": request.pitch,
        }

        response = self._session.post(
            self._settings.synthesize_url,
            headers=self._settings.headers(),
            json=payload,
            timeout=self._settings.timeout,
        )
        if response.status_code >= 400:
            message = self._extract_error_message(response)
            raise ViettelAIError(message, status_code=response.status_code)

        content_type = response.headers.get("Content-Type", "")
        if "application/json" in content_type:
            data = response.json()
            audio_bytes = self._parse_audio_from_json(data)
            if not audio_bytes:
                raise ViettelAIError("ViettelAI did not return audio data for the request")
        else:
            audio_bytes = response.content
            if not audio_bytes:
                raise ViettelAIError("Received empty audio payload from ViettelAI")

        return SynthesisResult(audio_bytes=audio_bytes, audio_format=request.audio_format, request=request)

    @staticmethod
    def _extract_error_message(response: requests.Response) -> str:
        try:
            data = response.json()
        except ValueError:
            return f"ViettelAI request failed with status {response.status_code}"
        if isinstance(data, dict):
            for key in ("error", "message", "detail", "msg"):
                value = data.get(key)
                if isinstance(value, str):
                    return value
        return f"ViettelAI request failed with status {response.status_code}"

    @staticmethod
    def _parse_audio_from_json(data: object) -> bytes:
        if not isinstance(data, dict):
            return b""
        audio_b64 = (
            data.get("data")
            or data.get("audio")
            or data.get("audioData")
            or data.get("audio_base64")
            or data.get("audioBase64")
        )
        if isinstance(audio_b64, str):
            try:
                return base64.b64decode(audio_b64)
            except (ValueError, base64.binascii.Error):
                return b""
        return b""
