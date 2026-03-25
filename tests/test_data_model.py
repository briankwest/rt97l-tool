"""Tests for data model validation."""

from decimal import Decimal

import pytest

from rt97l.constants import ChannelMode, Compand, Language, ModelType, SquelchLevel, TxPower
from rt97l.data_model import ChannelConfig, GlobalConfig, RepeaterConfig, ValidationError


def _make_channel(**kwargs) -> ChannelConfig:
    defaults = {
        "channel_number": 1,
        "rx_freq": Decimal("462.5500"),
        "tx_freq": Decimal("467.5500"),
    }
    defaults.update(kwargs)
    return ChannelConfig(**defaults)


class TestChannelConfig:
    def test_valid_channel(self):
        ch = _make_channel()
        ch.validate()  # Should not raise

    def test_channel_number_too_low(self):
        ch = _make_channel(channel_number=0)
        with pytest.raises(ValidationError, match="Channel number"):
            ch.validate()

    def test_channel_number_too_high(self):
        ch = _make_channel(channel_number=17)
        with pytest.raises(ValidationError, match="Channel number"):
            ch.validate()

    def test_rx_freq_out_of_range(self):
        ch = _make_channel(rx_freq=Decimal("100.0000"))
        with pytest.raises(ValidationError, match="RX"):
            ch.validate()

    def test_tx_freq_out_of_range(self):
        ch = _make_channel(tx_freq=Decimal("999.0000"))
        with pytest.raises(ValidationError, match="TX"):
            ch.validate()

    def test_valid_ctcss_tone(self):
        ch = _make_channel(ctcss_enc="100.0", ctcss_dec="D023N")
        ch.validate()

    def test_invalid_ctcss_tone(self):
        ch = _make_channel(ctcss_enc="999.9")
        with pytest.raises(ValidationError, match="CT/DCS Enc"):
            ch.validate()

    def test_off_tone_is_valid(self):
        ch = _make_channel(ctcss_enc="OFF", ctcss_dec=None)
        ch.validate()

    def test_tone_display_off(self):
        ch = _make_channel(ctcss_enc=None)
        assert ch.tone_enc_display == "OFF"

    def test_tone_display_value(self):
        ch = _make_channel(ctcss_enc="100.0")
        assert ch.tone_enc_display == "100.0"


class TestGlobalConfig:
    def test_valid_defaults(self):
        g = GlobalConfig()
        g.validate()

    def test_mic_gain_too_low(self):
        g = GlobalConfig(mic_gain=-4)
        with pytest.raises(ValidationError, match="Mic gain"):
            g.validate()

    def test_mic_gain_too_high(self):
        g = GlobalConfig(mic_gain=4)
        with pytest.raises(ValidationError, match="Mic gain"):
            g.validate()

    def test_vox_level_out_of_range(self):
        g = GlobalConfig(vox_level=0)
        with pytest.raises(ValidationError, match="VOX level"):
            g.validate()

    def test_invalid_vox_delay(self):
        g = GlobalConfig(vox_delay=7.7)
        with pytest.raises(ValidationError, match="VOX delay"):
            g.validate()

    def test_invalid_relay_delay(self):
        g = GlobalConfig(relay_delay=3.0)
        with pytest.raises(ValidationError, match="Relay delay"):
            g.validate()

    def test_invalid_timeout(self):
        g = GlobalConfig(timeout_sec=17)
        with pytest.raises(ValidationError, match="Timeout"):
            g.validate()

    def test_scan_ch_out_of_range(self):
        g = GlobalConfig(scan_ch=0)
        with pytest.raises(ValidationError, match="Scan CH"):
            g.validate()


class TestRepeaterConfig:
    def test_default_config_is_valid(self):
        config = RepeaterConfig.default()
        config.validate()

    def test_default_has_16_channels(self):
        config = RepeaterConfig.default()
        assert len(config.channels) == 16

    def test_wrong_channel_count(self):
        config = RepeaterConfig(channels=[])
        with pytest.raises(ValidationError, match="16 channels"):
            config.validate()

    def test_default_channel_freqs(self):
        config = RepeaterConfig.default()
        # Channel 1 should be simplex
        assert config.channels[0].rx_freq == Decimal("462.5500")
        assert config.channels[0].tx_freq == Decimal("462.5500")
        # Channel 9 should have +5 MHz offset
        assert config.channels[8].rx_freq == Decimal("462.5500")
        assert config.channels[8].tx_freq == Decimal("467.5500")
