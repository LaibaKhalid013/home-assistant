"""Wake word models."""
from dataclasses import dataclass


@dataclass(frozen=True)
class WakeWord:
    """Wake word model."""

    ww_id: str
    name: str


@dataclass
class DetectionResult:
    """Result of wake word detection."""

    ww_id: str
    """Id of detected wake word"""

    timestamp: int | None
    """Timestamp of audio chunk with detected wake word"""
