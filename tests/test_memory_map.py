"""Tests for memory map encode/decode."""

from decimal import Decimal

import pytest

from rt97l.constants import ChannelMode, Compand, SquelchLevel, TxPower
from rt97l.data_model import ChannelConfig, RepeaterConfig
from rt97l.memory_map import (
    CHANNEL_SIZE,
    decode_channel,
    decode_config,
    decode_freq_bcd,
    decode_tone,
    encode_channel,
    encode_config,
    encode_freq_bcd,
    encode_tone,
)


class TestFreqBCD:
    def test_encode_462_5500(self):
        result = encode_freq_bcd(Decimal("462.5500"))
        assert result == bytes([0x46, 0x25, 0x50, 0x00])

    def test_encode_467_7250(self):
        result = encode_freq_bcd(Decimal("467.7250"))
        assert result == bytes([0x46, 0x77, 0x25, 0x00])

    def test_decode_462_5500(self):
        result = decode_freq_bcd(bytes([0x46, 0x25, 0x50, 0x00]))
        assert result == Decimal("462.5500")

    def test_roundtrip(self):
        freqs = [
            Decimal("462.5500"), Decimal("462.5750"),
            Decimal("467.6250"), Decimal("467.7250"),
        ]
        for freq in freqs:
            assert decode_freq_bcd(encode_freq_bcd(freq)) == freq


class TestToneEncoding:
    def test_off(self):
        assert encode_tone(None) == 0
        assert encode_tone("OFF") == 0

    def test_decode_off(self):
        assert decode_tone(0) is None

    def test_ctcss_67_0(self):
        idx = encode_tone("67.0")
        assert idx == 1
        assert decode_tone(idx) == "67.0"

    def test_ctcss_254_1(self):
        idx = encode_tone("254.1")
        assert idx == 50
        assert decode_tone(idx) == "254.1"

    def test_dcs_d023n(self):
        idx = encode_tone("D023N")
        assert idx == 51
        assert decode_tone(idx) == "D023N"

    def test_dcs_d023i(self):
        idx = encode_tone("D023I")
        assert idx == 51 + 105  # First inverted code
        assert decode_tone(idx) == "D023I"

    def test_all_ctcss_roundtrip(self):
        from rt97l.constants import CTCSS_TONES
        for tone in CTCSS_TONES:
            assert decode_tone(encode_tone(tone)) == tone

    def test_all_dcs_roundtrip(self):
        from rt97l.constants import DCS_CODES_ALL
        for code in DCS_CODES_ALL:
            assert decode_tone(encode_tone(code)) == code


class TestChannelEncoding:
    def test_default_channel_roundtrip(self):
        original = ChannelConfig(
            channel_number=1,
            rx_freq=Decimal("462.5500"),
            tx_freq=Decimal("467.5500"),
        )
        raw = encode_channel(original)
        assert len(raw) == CHANNEL_SIZE
        decoded = decode_channel(raw, 1)
        assert decoded.rx_freq == original.rx_freq
        assert decoded.tx_freq == original.tx_freq
        assert decoded.tx_power == original.tx_power
        assert decoded.ctcss_enc is None
        assert decoded.scan_add is True

    def test_fully_configured_channel_roundtrip(self):
        original = ChannelConfig(
            channel_number=5,
            rx_freq=Decimal("462.6500"),
            tx_freq=Decimal("467.6500"),
            ctcss_enc="100.0",
            ctcss_dec="D023N",
            channel_mode=ChannelMode.CH_FREQUENCY,
            tx_power=TxPower.LOW,
            squelch_level=SquelchLevel.L7,
            scan_add=False,
            channel_lock=True,
            compand=Compand.NARROW,
        )
        raw = encode_channel(original)
        decoded = decode_channel(raw, 5)
        assert decoded.rx_freq == original.rx_freq
        assert decoded.tx_freq == original.tx_freq
        assert decoded.ctcss_enc == "100.0"
        assert decoded.ctcss_dec == "D023N"
        assert decoded.channel_mode == ChannelMode.CH_FREQUENCY
        assert decoded.tx_power == TxPower.LOW
        assert decoded.squelch_level == SquelchLevel.L7
        assert decoded.scan_add is False
        assert decoded.channel_lock is True
        assert decoded.compand == Compand.NARROW

    def test_squelch_off(self):
        ch = ChannelConfig(
            channel_number=1,
            rx_freq=Decimal("462.5500"),
            tx_freq=Decimal("462.5500"),
            squelch_level=SquelchLevel.OFF,
        )
        raw = encode_channel(ch)
        decoded = decode_channel(raw, 1)
        assert decoded.squelch_level == SquelchLevel.OFF


class TestConfigEncoding:
    def test_default_config_roundtrip(self):
        original = RepeaterConfig.default()
        raw = encode_config(original)
        assert len(raw) == 256

        decoded = decode_config(raw)
        assert len(decoded.channels) == 16

        for i in range(16):
            assert decoded.channels[i].rx_freq == original.channels[i].rx_freq
            assert decoded.channels[i].tx_freq == original.channels[i].tx_freq

    def test_config_size(self):
        raw = encode_config(RepeaterConfig.default())
        assert len(raw) == 256
