"""Data model for RT97L / CX-525 repeater configuration.

Dataclasses representing per-channel settings, global settings, and the
complete repeater configuration.  Includes validation against the
constants defined in constants.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional

from rt97l.constants import (
    CTCSS_TONES,
    DCS_CODES_ALL,
    FREQ_MAX,
    FREQ_MIN,
    MIC_GAIN_MAX,
    MIC_GAIN_MIN,
    NUM_CHANNELS,
    RELAY_DELAY_OPTIONS,
    TIMEOUT_OPTIONS,
    VOX_DELAY_OPTIONS,
    VOX_LEVEL_MAX,
    VOX_LEVEL_MIN,
    VOLUME_MAX,
    VOLUME_MIN,
    ChannelMode,
    Compand,
    Language,
    ModelType,
    SquelchLevel,
    TxPower,
)


class ValidationError(Exception):
    """Raised when a configuration value is out of range or invalid."""


def _validate_frequency(freq: Decimal, label: str) -> None:
    if not (FREQ_MIN <= freq <= FREQ_MAX):
        raise ValidationError(
            f"{label} {freq} MHz out of range ({FREQ_MIN}–{FREQ_MAX})"
        )


def _validate_tone(tone: Optional[str], label: str) -> None:
    if tone is None or tone == "OFF":
        return
    if tone in CTCSS_TONES or tone in DCS_CODES_ALL:
        return
    raise ValidationError(f"{label} invalid tone/code: {tone!r}")


@dataclass
class ChannelConfig:
    """Configuration for a single repeater channel."""

    channel_number: int
    rx_freq: Decimal
    tx_freq: Decimal
    ctcss_enc: Optional[str] = None  # None or "OFF" = no tone
    ctcss_dec: Optional[str] = None
    channel_mode: ChannelMode = ChannelMode.FREQUENCY
    tx_power: TxPower = TxPower.HIGH
    squelch_level: SquelchLevel = SquelchLevel.L4
    scan_add: bool = True
    channel_lock: bool = False
    compand: Compand = Compand.WIDE

    def validate(self) -> None:
        """Raise ValidationError if any value is out of range."""
        if not (1 <= self.channel_number <= NUM_CHANNELS):
            raise ValidationError(
                f"Channel number {self.channel_number} out of range (1–{NUM_CHANNELS})"
            )
        _validate_frequency(self.rx_freq, f"CH{self.channel_number} RX")
        _validate_frequency(self.tx_freq, f"CH{self.channel_number} TX")
        _validate_tone(self.ctcss_enc, f"CH{self.channel_number} CT/DCS Enc")
        _validate_tone(self.ctcss_dec, f"CH{self.channel_number} CT/DCS Dec")

    @property
    def tone_enc_display(self) -> str:
        return self.ctcss_enc if self.ctcss_enc else "OFF"

    @property
    def tone_dec_display(self) -> str:
        return self.ctcss_dec if self.ctcss_dec else "OFF"


@dataclass
class GlobalConfig:
    """Global (non-per-channel) repeater settings."""

    # Audio
    audio_output: bool = True
    volume: int = 5
    beep: bool = True
    # Display
    backlight: bool = True
    low_temperature: bool = False
    # Power
    battery_save: bool = True
    # Voice
    voice_prompts: bool = True
    # VOX
    vox_function: bool = False
    vox_level: int = 1
    vox_delay: float = 1.0
    vox_set: bool = False  # VOX enable/disable (separate from vox_function)
    # Relay
    relay: bool = True  # Relay ON/OFF
    relay_delay: float = 0.5
    # Radio
    squelch_tail_elim: bool = False  # STE — Squelch Tail Elimination
    mic_gain: int = 0
    timeout_sec: int = 0  # 0 = OFF
    scan_ch: int = 1
    special_dqt: Optional[str] = None
    # System
    language: Language = Language.ENGLISH
    frequency_band: int = 2
    model_type: ModelType = ModelType.RT97L

    def validate(self) -> None:
        """Raise ValidationError if any value is out of range."""
        if not (VOLUME_MIN <= self.volume <= VOLUME_MAX):
            raise ValidationError(
                f"Volume {self.volume} out of range ({VOLUME_MIN}–{VOLUME_MAX})"
            )
        if not (MIC_GAIN_MIN <= self.mic_gain <= MIC_GAIN_MAX):
            raise ValidationError(
                f"Mic gain {self.mic_gain} out of range ({MIC_GAIN_MIN}–{MIC_GAIN_MAX})"
            )
        if not (VOX_LEVEL_MIN <= self.vox_level <= VOX_LEVEL_MAX):
            raise ValidationError(
                f"VOX level {self.vox_level} out of range ({VOX_LEVEL_MIN}–{VOX_LEVEL_MAX})"
            )
        if self.vox_delay not in VOX_DELAY_OPTIONS:
            raise ValidationError(
                f"VOX delay {self.vox_delay} not in {VOX_DELAY_OPTIONS}"
            )
        if self.relay_delay not in RELAY_DELAY_OPTIONS:
            raise ValidationError(
                f"Relay delay {self.relay_delay} not in {RELAY_DELAY_OPTIONS}"
            )
        if self.timeout_sec not in TIMEOUT_OPTIONS:
            raise ValidationError(
                f"Timeout {self.timeout_sec} not in valid options"
            )
        if not (1 <= self.scan_ch <= NUM_CHANNELS):
            raise ValidationError(
                f"Scan CH {self.scan_ch} out of range (1–{NUM_CHANNELS})"
            )


@dataclass
class RepeaterConfig:
    """Complete repeater configuration: channels + globals + metadata."""

    channels: list[ChannelConfig] = field(default_factory=list)
    globals: GlobalConfig = field(default_factory=GlobalConfig)
    password: Optional[str] = None
    machine_info: str = ""

    def validate(self) -> None:
        """Validate the entire configuration."""
        if len(self.channels) != NUM_CHANNELS:
            raise ValidationError(
                f"Expected {NUM_CHANNELS} channels, got {len(self.channels)}"
            )
        for ch in self.channels:
            ch.validate()
        self.globals.validate()

    @classmethod
    def default(cls) -> RepeaterConfig:
        """Create a default configuration with GMRS channel defaults."""
        from rt97l.constants import GMRS_RX_FREQS, GMRS_TX_FREQS

        channels = [
            ChannelConfig(
                channel_number=i + 1,
                rx_freq=GMRS_RX_FREQS[i],
                tx_freq=GMRS_TX_FREQS[i],
            )
            for i in range(NUM_CHANNELS)
        ]
        return cls(channels=channels)
