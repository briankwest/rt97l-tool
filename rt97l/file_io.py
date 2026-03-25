"""Save/load RepeaterConfig to JSON and text formats.

JSON is the native format for this tool.  The text format is designed
for compatibility with the Windows RT97L.exe "Save As" / "Open" .txt files
(format will be refined once Ghidra reveals the exact layout).
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

from rt97l.constants import ChannelMode, Compand, Language, ModelType, SquelchLevel, TxPower
from rt97l.data_model import ChannelConfig, GlobalConfig, RepeaterConfig


# ---------------------------------------------------------------------------
# JSON format
# ---------------------------------------------------------------------------


class _DecimalEncoder(json.JSONEncoder):
    """Encode Decimal as string to preserve precision."""

    def default(self, o: Any) -> Any:
        if isinstance(o, Decimal):
            return str(o)
        return super().default(o)


def _channel_to_dict(ch: ChannelConfig) -> dict[str, Any]:
    return {
        "channel_number": ch.channel_number,
        "rx_freq": str(ch.rx_freq),
        "tx_freq": str(ch.tx_freq),
        "ctcss_enc": ch.ctcss_enc,
        "ctcss_dec": ch.ctcss_dec,
        "channel_mode": ch.channel_mode.value,
        "tx_power": ch.tx_power.value,
        "squelch_level": ch.squelch_level.value,
        "scan_add": ch.scan_add,
        "channel_lock": ch.channel_lock,
        "compand": ch.compand.value,
    }


def _channel_from_dict(d: dict[str, Any]) -> ChannelConfig:
    return ChannelConfig(
        channel_number=d["channel_number"],
        rx_freq=Decimal(d["rx_freq"]),
        tx_freq=Decimal(d["tx_freq"]),
        ctcss_enc=d.get("ctcss_enc"),
        ctcss_dec=d.get("ctcss_dec"),
        channel_mode=ChannelMode(d.get("channel_mode", "Frequency")),
        tx_power=TxPower(d.get("tx_power", "High")),
        squelch_level=SquelchLevel(d.get("squelch_level", "4")),
        scan_add=d.get("scan_add", True),
        channel_lock=d.get("channel_lock", False),
        compand=Compand(d.get("compand", "Wide")),
    )


def _globals_to_dict(g: GlobalConfig) -> dict[str, Any]:
    return {
        "audio_output": g.audio_output,
        "volume": g.volume,
        "beep": g.beep,
        "backlight": g.backlight,
        "low_temperature": g.low_temperature,
        "battery_save": g.battery_save,
        "voice_prompts": g.voice_prompts,
        "vox_function": g.vox_function,
        "vox_level": g.vox_level,
        "vox_delay": g.vox_delay,
        "vox_set": g.vox_set,
        "relay": g.relay,
        "relay_delay": g.relay_delay,
        "squelch_tail_elim": g.squelch_tail_elim,
        "mic_gain": g.mic_gain,
        "timeout_sec": g.timeout_sec,
        "scan_ch": g.scan_ch,
        "special_dqt": g.special_dqt,
        "language": g.language.value,
        "frequency_band": g.frequency_band,
        "model_type": g.model_type.value,
    }


def _globals_from_dict(d: dict[str, Any]) -> GlobalConfig:
    return GlobalConfig(
        audio_output=d.get("audio_output", True),
        volume=d.get("volume", 5),
        beep=d.get("beep", True),
        backlight=d.get("backlight", True),
        low_temperature=d.get("low_temperature", False),
        battery_save=d.get("battery_save", True),
        voice_prompts=d.get("voice_prompts", True),
        vox_function=d.get("vox_function", False),
        vox_level=d.get("vox_level", 1),
        vox_delay=d.get("vox_delay", 1.0),
        vox_set=d.get("vox_set", False),
        relay=d.get("relay", True),
        relay_delay=d.get("relay_delay", 0.5),
        squelch_tail_elim=d.get("squelch_tail_elim", False),
        mic_gain=d.get("mic_gain", 0),
        timeout_sec=d.get("timeout_sec", 0),
        scan_ch=d.get("scan_ch", 1),
        special_dqt=d.get("special_dqt"),
        language=Language(d.get("language", "English")),
        frequency_band=d.get("frequency_band", 2),
        model_type=ModelType(d.get("model_type", "RT97L")),
    )


def save_json(config: RepeaterConfig, path: Path) -> None:
    """Save repeater configuration to a JSON file."""
    data = {
        "version": "1.0",
        "channels": [_channel_to_dict(ch) for ch in config.channels],
        "globals": _globals_to_dict(config.globals),
        "password": config.password,
        "machine_info": config.machine_info,
    }
    with open(path, "w") as f:
        json.dump(data, f, cls=_DecimalEncoder, indent=2)
        f.write("\n")


def load_json(path: Path) -> RepeaterConfig:
    """Load repeater configuration from a JSON file."""
    with open(path) as f:
        data = json.load(f)

    channels = [_channel_from_dict(d) for d in data["channels"]]
    globals_ = _globals_from_dict(data.get("globals", {}))

    return RepeaterConfig(
        channels=channels,
        globals=globals_,
        password=data.get("password"),
        machine_info=data.get("machine_info", ""),
    )


# ---------------------------------------------------------------------------
# Text format (tab-separated, Windows RT97L.exe compatible)
# Header + 16 rows of channel data + global settings block.
# Exact format TBD after Ghidra analysis; this is a best-effort layout.
# ---------------------------------------------------------------------------

_TXT_HEADER = (
    "Channel\tRx Freq\tTx Freq\tCT/DCS Enc\tCT/DCS Dec\t"
    "Channel Mode\tTx Power\tSquelch Level\tScan Add\t"
    "Channel Lock\tCompand"
)


def save_txt(config: RepeaterConfig, path: Path) -> None:
    """Save repeater configuration to a tab-separated text file."""
    lines = [_TXT_HEADER]
    for ch in config.channels:
        lines.append(
            f"{ch.channel_number}\t{ch.rx_freq}\t{ch.tx_freq}\t"
            f"{ch.tone_enc_display}\t{ch.tone_dec_display}\t"
            f"{ch.channel_mode.value}\t{ch.tx_power.value}\t"
            f"{ch.squelch_level.value}\t{'Yes' if ch.scan_add else 'No'}\t"
            f"{'Yes' if ch.channel_lock else 'No'}\t{ch.compand.value}"
        )

    # Global settings block (matches binary label order)
    g = config.globals
    lines.append("")
    lines.append(f"Low Temperature\t{'ON' if g.low_temperature else 'OFF'}")
    lines.append(f"Back Light\t{'ON' if g.backlight else 'OFF'}")
    lines.append(f"Relay\t{'ON' if g.relay else 'OFF'}")
    lines.append(f"Relay Delay\t{g.relay_delay}")
    lines.append(f"STE\t{'ON' if g.squelch_tail_elim else 'OFF'}")
    lines.append(f"Scan CH\t{g.scan_ch}")
    lines.append(f"Mic Gain\t{g.mic_gain}")
    lines.append(f"Audio Output\t{'ON' if g.audio_output else 'OFF'}")
    lines.append(f"Volume\t{g.volume}")
    lines.append(f"Vox Delay Time(sec)\t{g.vox_delay}")
    lines.append(f"Vox Level\t{g.vox_level}")
    lines.append(f"Vox Function\t{'ON' if g.vox_function else 'OFF'}")
    lines.append(f"Vox Set\t{'ON' if g.vox_set else 'OFF'}")
    lines.append(f"Beep\t{'ON' if g.beep else 'OFF'}")
    lines.append(f"Battery Save\t{'ON' if g.battery_save else 'OFF'}")
    lines.append(f"Voice Prompts\t{'ON' if g.voice_prompts else 'OFF'}")
    lines.append(f"Timeout(sec)\t{g.timeout_sec if g.timeout_sec else 'OFF'}")
    lines.append(f"Language\t{g.language.value}")
    lines.append(f"Frequency Band\t{g.frequency_band}")
    lines.append(f"Model Type\t{g.model_type.value}")

    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")


def load_txt(path: Path) -> RepeaterConfig:
    """Load repeater configuration from a tab-separated text file."""
    with open(path) as f:
        raw_lines = f.read().splitlines()

    # Skip header, parse channel lines
    channels: list[ChannelConfig] = []
    globals_dict: dict[str, str] = {}
    parsing_channels = False
    parsing_globals = False

    for line in raw_lines:
        line = line.strip()
        if not line:
            parsing_channels = False
            parsing_globals = True
            continue

        if line.startswith("Channel\t"):
            parsing_channels = True
            continue

        if parsing_channels:
            parts = line.split("\t")
            if len(parts) >= 11:
                channels.append(ChannelConfig(
                    channel_number=int(parts[0]),
                    rx_freq=Decimal(parts[1]),
                    tx_freq=Decimal(parts[2]),
                    ctcss_enc=None if parts[3] == "OFF" else parts[3],
                    ctcss_dec=None if parts[4] == "OFF" else parts[4],
                    channel_mode=ChannelMode(parts[5]),
                    tx_power=TxPower(parts[6]),
                    squelch_level=SquelchLevel(parts[7]),
                    scan_add=parts[8] == "Yes",
                    channel_lock=parts[9] == "Yes",
                    compand=Compand(parts[10]),
                ))
        elif parsing_globals:
            parts = line.split("\t", 1)
            if len(parts) == 2:
                globals_dict[parts[0]] = parts[1]

    # Build GlobalConfig from parsed key-value pairs
    def _bool(val: str) -> bool:
        return val.upper() == "ON"

    g = GlobalConfig()
    if "Low Temperature" in globals_dict:
        g.low_temperature = _bool(globals_dict["Low Temperature"])
    if "Back Light" in globals_dict:
        g.backlight = _bool(globals_dict["Back Light"])
    if "Relay" in globals_dict:
        g.relay = _bool(globals_dict["Relay"])
    if "Relay Delay" in globals_dict:
        g.relay_delay = float(globals_dict["Relay Delay"])
    if "STE" in globals_dict:
        g.squelch_tail_elim = _bool(globals_dict["STE"])
    if "Scan CH" in globals_dict:
        g.scan_ch = int(globals_dict["Scan CH"])
    if "Mic Gain" in globals_dict:
        g.mic_gain = int(globals_dict["Mic Gain"])
    if "Audio Output" in globals_dict:
        g.audio_output = _bool(globals_dict["Audio Output"])
    if "Volume" in globals_dict:
        g.volume = int(globals_dict["Volume"])
    if "Vox Delay Time(sec)" in globals_dict:
        g.vox_delay = float(globals_dict["Vox Delay Time(sec)"])
    if "Vox Level" in globals_dict:
        g.vox_level = int(globals_dict["Vox Level"])
    if "Vox Function" in globals_dict:
        g.vox_function = _bool(globals_dict["Vox Function"])
    if "Vox Set" in globals_dict:
        g.vox_set = _bool(globals_dict["Vox Set"])
    if "Beep" in globals_dict:
        g.beep = _bool(globals_dict["Beep"])
    if "Battery Save" in globals_dict:
        g.battery_save = _bool(globals_dict["Battery Save"])
    if "Voice Prompts" in globals_dict:
        g.voice_prompts = _bool(globals_dict["Voice Prompts"])
    if "Timeout(sec)" in globals_dict:
        val = globals_dict["Timeout(sec)"]
        g.timeout_sec = 0 if val == "OFF" else int(val)
    if "Language" in globals_dict:
        g.language = Language(globals_dict["Language"])
    if "Frequency Band" in globals_dict:
        g.frequency_band = int(globals_dict["Frequency Band"])
    if "Model Type" in globals_dict:
        g.model_type = ModelType(globals_dict["Model Type"])

    return RepeaterConfig(channels=channels, globals=g)
