"""Tests for file I/O (JSON and text formats)."""

import tempfile
from decimal import Decimal
from pathlib import Path

from rt97l.constants import ChannelMode, Compand, Language, ModelType, SquelchLevel, TxPower
from rt97l.data_model import ChannelConfig, GlobalConfig, RepeaterConfig
from rt97l.file_io import load_json, load_txt, save_json, save_txt


def _make_config() -> RepeaterConfig:
    """Build a non-default config to test round-tripping."""
    config = RepeaterConfig.default()

    # Customize a few channels
    config.channels[0].ctcss_enc = "100.0"
    config.channels[0].ctcss_dec = "D023N"
    config.channels[0].tx_power = TxPower.LOW
    config.channels[0].squelch_level = SquelchLevel.L7
    config.channels[0].scan_add = False

    config.channels[5].channel_mode = ChannelMode.CH_FREQUENCY
    config.channels[5].channel_lock = True
    config.channels[5].compand = Compand.NARROW

    # Customize globals
    config.globals.mic_gain = -2
    config.globals.vox_function = True
    config.globals.vox_level = 5
    config.globals.vox_delay = 2.0
    config.globals.language = Language.CHINESE
    config.globals.model_type = ModelType.CX525
    config.globals.relay_delay = 2.5
    config.globals.timeout_sec = 60
    config.globals.scan_ch = 8
    config.globals.backlight = False

    config.password = "123456"
    config.machine_info = "test unit"
    return config


class TestJsonRoundTrip:
    def test_save_and_load(self):
        original = _make_config()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = Path(f.name)

        save_json(original, path)
        loaded = load_json(path)

        assert len(loaded.channels) == 16
        assert loaded.channels[0].ctcss_enc == "100.0"
        assert loaded.channels[0].ctcss_dec == "D023N"
        assert loaded.channels[0].tx_power == TxPower.LOW
        assert loaded.channels[0].squelch_level == SquelchLevel.L7
        assert loaded.channels[0].scan_add is False

        assert loaded.channels[5].channel_mode == ChannelMode.CH_FREQUENCY
        assert loaded.channels[5].channel_lock is True
        assert loaded.channels[5].compand == Compand.NARROW

        assert loaded.globals.mic_gain == -2
        assert loaded.globals.vox_function is True
        assert loaded.globals.vox_level == 5
        assert loaded.globals.language == Language.CHINESE
        assert loaded.globals.model_type == ModelType.CX525
        assert loaded.globals.relay_delay == 2.5
        assert loaded.globals.timeout_sec == 60
        assert loaded.globals.backlight is False

        assert loaded.password == "123456"
        assert loaded.machine_info == "test unit"

        loaded.validate()
        path.unlink()

    def test_frequency_precision(self):
        original = RepeaterConfig.default()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = Path(f.name)

        save_json(original, path)
        loaded = load_json(path)

        for i in range(16):
            assert loaded.channels[i].rx_freq == original.channels[i].rx_freq
            assert loaded.channels[i].tx_freq == original.channels[i].tx_freq
        path.unlink()


class TestTxtRoundTrip:
    def test_save_and_load(self):
        original = _make_config()
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            path = Path(f.name)

        save_txt(original, path)
        loaded = load_txt(path)

        assert len(loaded.channels) == 16
        assert loaded.channels[0].ctcss_enc == "100.0"
        assert loaded.channels[0].ctcss_dec == "D023N"
        assert loaded.channels[0].tx_power == TxPower.LOW

        assert loaded.channels[5].channel_mode == ChannelMode.CH_FREQUENCY
        assert loaded.channels[5].channel_lock is True

        assert loaded.globals.mic_gain == -2
        assert loaded.globals.vox_function is True
        assert loaded.globals.language == Language.CHINESE
        assert loaded.globals.timeout_sec == 60

        loaded.validate()
        path.unlink()

    def test_default_config_roundtrip(self):
        original = RepeaterConfig.default()
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            path = Path(f.name)

        save_txt(original, path)
        loaded = load_txt(path)

        assert len(loaded.channels) == 16
        for i in range(16):
            assert loaded.channels[i].rx_freq == original.channels[i].rx_freq
            assert loaded.channels[i].tx_freq == original.channels[i].tx_freq

        loaded.validate()
        path.unlink()
