"""Tests for INI config read/write."""

import tempfile
from pathlib import Path

from rt97l.config import AppConfig


def test_save_and_load_roundtrip():
    original = AppConfig(
        port_number=3,
        auto_detect_port=True,
        language_code=1,
        frequency_band=1,
        book_names=["Alpha", "Beta", "Charlie"],
    )
    with tempfile.NamedTemporaryFile(suffix=".ini", mode="w", delete=False) as f:
        path = Path(f.name)

    original.save(path)
    loaded = AppConfig.load(path)

    assert loaded.port_number == 3
    assert loaded.auto_detect_port is True
    assert loaded.language_code == 1
    assert loaded.frequency_band == 1
    assert loaded.book_names == ["Alpha", "Beta", "Charlie"]
    path.unlink()


def test_load_defaults_on_missing_sections():
    with tempfile.NamedTemporaryFile(suffix=".ini", mode="w", delete=False) as f:
        f.write("[comm]\ncom=5\n")
        path = Path(f.name)

    loaded = AppConfig.load(path)
    assert loaded.port_number == 5
    assert loaded.auto_detect_port is False  # default
    assert loaded.language_code == 2  # default
    assert loaded.book_names == ["A", "B", "C"]  # default
    path.unlink()


def test_load_original_config_ini():
    """Test loading the actual config.ini from the Windows tool."""
    path = Path("/Users/brian/Desktop/rt97l/config.ini")
    if not path.exists():
        return  # Skip if not available
    loaded = AppConfig.load(path)
    assert loaded.port_number == 1
    assert loaded.auto_detect_port is False
    assert loaded.language_code == 2
    assert loaded.frequency_band == 2
    assert loaded.book_names == ["A", "B", "C"]
