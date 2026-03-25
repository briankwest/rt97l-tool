"""Application configuration (INI file) and CLI argument handling.

Compatible with the Windows RT97L.exe config.ini format:

    [BookName]
    Name0=A
    Name1=B
    Name2=C
    [comm]
    com=1
    [auto_comm]
    auto_com=0
    [lan]
    type=2
    [FREQ_BAND]
    BAND=2
"""

from __future__ import annotations

import configparser
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class AppConfig:
    """Application-level configuration (not radio settings)."""

    port: Optional[str] = None  # e.g. "/dev/ttyUSB0" or "COM1"
    port_number: int = 1  # Legacy COM port number for Windows compat
    auto_detect_port: bool = False
    language_code: int = 2  # 1=Chinese, 2=English
    frequency_band: int = 2
    book_names: list[str] = field(default_factory=lambda: ["A", "B", "C"])

    def save(self, path: Path) -> None:
        """Write config to an INI file (Windows-compatible format)."""
        cfg = configparser.ConfigParser()
        cfg.optionxform = str  # preserve case

        cfg["BookName"] = {
            f"Name{i}": name for i, name in enumerate(self.book_names)
        }
        cfg["comm"] = {"com": str(self.port_number)}
        cfg["auto_comm"] = {"auto_com": str(int(self.auto_detect_port))}
        cfg["lan"] = {"type": str(self.language_code)}
        cfg["FREQ_BAND"] = {"BAND": str(self.frequency_band)}

        with open(path, "w") as f:
            cfg.write(f)

    @classmethod
    def load(cls, path: Path) -> AppConfig:
        """Read config from an INI file."""
        cfg = configparser.ConfigParser()
        cfg.optionxform = str
        cfg.read(path)

        book_names = []
        if cfg.has_section("BookName"):
            i = 0
            while cfg.has_option("BookName", f"Name{i}"):
                book_names.append(cfg.get("BookName", f"Name{i}"))
                i += 1
        if not book_names:
            book_names = ["A", "B", "C"]

        port_number = cfg.getint("comm", "com", fallback=1)
        auto_detect = cfg.getboolean("auto_comm", "auto_com", fallback=False)
        lang_code = cfg.getint("lan", "type", fallback=2)
        freq_band = cfg.getint("FREQ_BAND", "BAND", fallback=2)

        return cls(
            port_number=port_number,
            auto_detect_port=auto_detect,
            language_code=lang_code,
            frequency_band=freq_band,
            book_names=book_names,
        )
