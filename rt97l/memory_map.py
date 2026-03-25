"""Memory map: convert between raw 256-byte config and RepeaterConfig.

The RT97L stores 256 bytes of configuration, organized as 16 channels
of 16 bytes each.

IMPORTANT: The exact byte layout below is based on binary analysis and
educated guesses from similar Retevis/TYT radios. It MUST be validated
against a real serial capture. Run the capture tool to dump the raw bytes
and correlate with known settings.

Expected layout per channel (16 bytes):
  [0:4]  RX frequency (32-bit, BCD or binary, TBD)
  [4:8]  TX frequency (32-bit, BCD or binary, TBD)
  [8]    CTCSS/DCS encode index
  [9]    CTCSS/DCS decode index
  [10]   Tx power / channel mode / bandwidth flags
  [11]   Squelch level
  [12]   Flags: scan_add, channel_lock, compand, etc.
  [13]   VOX / timeout / misc
  [14:16] Reserved / global settings in last channels

This module provides encode/decode with a pluggable layout so the exact
offsets can be refined after capture validation.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Optional

from rt97l.constants import (
    CTCSS_TONES,
    DCS_CODES_ALL,
    GMRS_RX_FREQS,
    GMRS_TX_FREQS,
    NUM_CHANNELS,
    ChannelMode,
    Compand,
    Language,
    ModelType,
    SquelchLevel,
    TxPower,
)
from rt97l.data_model import ChannelConfig, GlobalConfig, RepeaterConfig


# ---------------------------------------------------------------------------
# Frequency encoding — BCD format (common in Chinese radios)
# Example: 462.5500 MHz → 0x46255000 (each nibble is a digit)
# ---------------------------------------------------------------------------


def encode_freq_bcd(freq: Decimal) -> bytes:
    """Encode frequency (MHz) as 4-byte BCD."""
    # freq = 462.5500 → integer 4625500 (multiply by 10000, drop decimal)
    # But we need 8 BCD digits = 4 bytes
    # 462.5500 → "46255000" → bytes [0x46, 0x25, 0x50, 0x00]
    freq_str = f"{freq:.4f}".replace(".", "")  # "4625500" → need 8 digits
    freq_str = freq_str.ljust(8, "0")[:8]      # pad/truncate to 8 digits
    result = bytearray(4)
    for i in range(4):
        hi = int(freq_str[i * 2])
        lo = int(freq_str[i * 2 + 1])
        result[i] = (hi << 4) | lo
    return bytes(result)


def decode_freq_bcd(data: bytes) -> Decimal:
    """Decode 4-byte BCD to frequency (MHz)."""
    digits = ""
    for b in data:
        digits += f"{(b >> 4) & 0xF}{b & 0xF}"
    # digits = "46255000" → "462.5500"
    mhz = digits[:3] + "." + digits[3:]
    return Decimal(mhz)


# ---------------------------------------------------------------------------
# Tone encoding — index into the combined tone table
# Index 0 = OFF, 1-50 = CTCSS, 51-260 = DCS
# ---------------------------------------------------------------------------


def encode_tone(tone: Optional[str]) -> int:
    """Encode a tone/code string to a byte index."""
    if tone is None or tone == "OFF":
        return 0
    if tone in CTCSS_TONES:
        return CTCSS_TONES.index(tone) + 1
    if tone in DCS_CODES_ALL:
        return DCS_CODES_ALL.index(tone) + len(CTCSS_TONES) + 1
    return 0


def decode_tone(index: int) -> Optional[str]:
    """Decode a byte index to a tone/code string."""
    if index == 0:
        return None
    if 1 <= index <= len(CTCSS_TONES):
        return CTCSS_TONES[index - 1]
    offset = index - len(CTCSS_TONES) - 1
    if 0 <= offset < len(DCS_CODES_ALL):
        return DCS_CODES_ALL[offset]
    return None


# ---------------------------------------------------------------------------
# Channel encode/decode (16 bytes per channel)
#
# NOTE: These offsets are PROVISIONAL. They must be validated against
# captured serial data from real hardware.
# ---------------------------------------------------------------------------

# Byte offsets within a 16-byte channel record
OFF_RX_FREQ = 0      # 4 bytes, BCD
OFF_TX_FREQ = 4      # 4 bytes, BCD
OFF_TONE_ENC = 8     # 1 byte, tone index
OFF_TONE_DEC = 9     # 1 byte, tone index
OFF_FLAGS1 = 10      # 1 byte: [7:4]=reserved, [3]=compand, [2]=mode, [1:0]=power
OFF_SQUELCH = 11     # 1 byte: squelch level (0-9, 0xFF=OFF)
OFF_FLAGS2 = 12      # 1 byte: [7:2]=reserved, [1]=channel_lock, [0]=scan_add
OFF_MISC = 13        # 1 byte: reserved/VOX
OFF_RESERVED1 = 14   # 1 byte
OFF_RESERVED2 = 15   # 1 byte

CHANNEL_SIZE = 16


def encode_channel(ch: ChannelConfig) -> bytes:
    """Encode a ChannelConfig to 16 raw bytes."""
    data = bytearray(CHANNEL_SIZE)

    # Frequencies
    data[OFF_RX_FREQ:OFF_RX_FREQ + 4] = encode_freq_bcd(ch.rx_freq)
    data[OFF_TX_FREQ:OFF_TX_FREQ + 4] = encode_freq_bcd(ch.tx_freq)

    # Tones
    data[OFF_TONE_ENC] = encode_tone(ch.ctcss_enc)
    data[OFF_TONE_DEC] = encode_tone(ch.ctcss_dec)

    # Flags1: power (bit 0), mode (bit 2), compand (bit 3)
    flags1 = 0
    if ch.tx_power == TxPower.LOW:
        flags1 |= 0x01
    if ch.channel_mode == ChannelMode.CH_FREQUENCY:
        flags1 |= 0x04
    if ch.compand == Compand.NARROW:
        flags1 |= 0x08
    data[OFF_FLAGS1] = flags1

    # Squelch
    if ch.squelch_level == SquelchLevel.OFF:
        data[OFF_SQUELCH] = 0xFF
    else:
        data[OFF_SQUELCH] = int(ch.squelch_level.value)

    # Flags2: scan_add (bit 0), channel_lock (bit 1)
    flags2 = 0
    if ch.scan_add:
        flags2 |= 0x01
    if ch.channel_lock:
        flags2 |= 0x02
    data[OFF_FLAGS2] = flags2

    return bytes(data)


def decode_channel(data: bytes, channel_number: int) -> ChannelConfig:
    """Decode 16 raw bytes to a ChannelConfig."""
    rx_freq = decode_freq_bcd(data[OFF_RX_FREQ:OFF_RX_FREQ + 4])
    tx_freq = decode_freq_bcd(data[OFF_TX_FREQ:OFF_TX_FREQ + 4])

    tone_enc = decode_tone(data[OFF_TONE_ENC])
    tone_dec = decode_tone(data[OFF_TONE_DEC])

    flags1 = data[OFF_FLAGS1]
    tx_power = TxPower.LOW if (flags1 & 0x01) else TxPower.HIGH
    channel_mode = (
        ChannelMode.CH_FREQUENCY if (flags1 & 0x04) else ChannelMode.FREQUENCY
    )
    compand = Compand.NARROW if (flags1 & 0x08) else Compand.WIDE

    squelch_byte = data[OFF_SQUELCH]
    if squelch_byte == 0xFF or squelch_byte > 9:
        squelch = SquelchLevel.OFF
    else:
        squelch = SquelchLevel(str(squelch_byte))

    flags2 = data[OFF_FLAGS2]
    scan_add = bool(flags2 & 0x01)
    channel_lock = bool(flags2 & 0x02)

    return ChannelConfig(
        channel_number=channel_number,
        rx_freq=rx_freq,
        tx_freq=tx_freq,
        ctcss_enc=tone_enc,
        ctcss_dec=tone_dec,
        channel_mode=channel_mode,
        tx_power=tx_power,
        squelch_level=squelch,
        scan_add=scan_add,
        channel_lock=channel_lock,
        compand=compand,
    )


# ---------------------------------------------------------------------------
# Full config encode/decode (256 bytes)
# ---------------------------------------------------------------------------


def decode_config(raw: bytes) -> RepeaterConfig:
    """Decode 256 raw bytes into a RepeaterConfig.

    NOTE: Global settings location within the 256 bytes is not yet
    confirmed. For now, we decode 16 channels of 16 bytes each and
    use default global settings. Global settings may be encoded in
    reserved bytes within channel records or in a separate area.
    """
    if len(raw) != 256:
        raise ValueError(f"Expected 256 bytes, got {len(raw)}")

    channels = []
    for i in range(NUM_CHANNELS):
        offset = i * CHANNEL_SIZE
        ch_data = raw[offset:offset + CHANNEL_SIZE]
        channels.append(decode_channel(ch_data, i + 1))

    # TODO: Decode global settings from raw bytes once memory map is confirmed
    globals_ = GlobalConfig()

    return RepeaterConfig(channels=channels, globals=globals_)


def encode_config(config: RepeaterConfig) -> bytes:
    """Encode a RepeaterConfig into 256 raw bytes."""
    data = bytearray(256)

    for ch in config.channels:
        offset = (ch.channel_number - 1) * CHANNEL_SIZE
        data[offset:offset + CHANNEL_SIZE] = encode_channel(ch)

    # TODO: Encode global settings once memory map is confirmed

    return bytes(data)
