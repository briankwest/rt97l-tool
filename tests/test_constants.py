"""Tests for constants completeness and correctness."""

from decimal import Decimal

from rt97l.constants import (
    CTCSS_TONES,
    DCS_CODES_ALL,
    DCS_CODES_BASE,
    DCS_CODES_INVERTED,
    DCS_CODES_NORMAL,
    GMRS_RX_FREQS,
    GMRS_TX_FREQS,
    NUM_CHANNELS,
    RELAY_DELAY_OPTIONS,
    TIMEOUT_OPTIONS,
    TONE_OPTIONS,
    VOX_DELAY_OPTIONS,
)


def test_ctcss_tone_count():
    assert len(CTCSS_TONES) == 50


def test_ctcss_tones_are_sorted():
    values = [float(t) for t in CTCSS_TONES]
    assert values == sorted(values)


def test_ctcss_tones_in_range():
    for tone in CTCSS_TONES:
        v = float(tone)
        assert 60.0 <= v <= 260.0, f"Tone {tone} out of expected range"


def test_dcs_base_code_count():
    assert len(DCS_CODES_BASE) == 105


def test_dcs_codes_normal_count():
    assert len(DCS_CODES_NORMAL) == 105


def test_dcs_codes_inverted_count():
    assert len(DCS_CODES_INVERTED) == 105


def test_dcs_codes_all_count():
    assert len(DCS_CODES_ALL) == 210


def test_dcs_codes_format():
    for code in DCS_CODES_NORMAL:
        assert code.startswith("D") and code.endswith("N")
        assert len(code) == 5
        assert code[1:4].isdigit()
    for code in DCS_CODES_INVERTED:
        assert code.startswith("D") and code.endswith("I")


def test_dcs_codes_no_duplicates():
    assert len(set(DCS_CODES_ALL)) == 210


def test_tone_options_starts_with_off():
    assert TONE_OPTIONS[0] == "OFF"
    assert len(TONE_OPTIONS) == 1 + 50 + 210


def test_gmrs_rx_freq_count():
    assert len(GMRS_RX_FREQS) == NUM_CHANNELS


def test_gmrs_tx_freq_count():
    assert len(GMRS_TX_FREQS) == NUM_CHANNELS


def test_gmrs_freqs_are_decimal():
    for f in GMRS_RX_FREQS + GMRS_TX_FREQS:
        assert isinstance(f, Decimal)


def test_gmrs_rx_freqs_in_462_band():
    for f in GMRS_RX_FREQS:
        assert Decimal("462.0") <= f <= Decimal("463.0")


def test_gmrs_tx_freqs_channels_1_8_simplex():
    for i in range(8):
        assert GMRS_TX_FREQS[i] == GMRS_RX_FREQS[i], f"CH{i+1} should be simplex"


def test_gmrs_tx_freqs_channels_9_16_offset():
    for i in range(8, 16):
        offset = GMRS_TX_FREQS[i] - GMRS_RX_FREQS[i]
        assert offset == Decimal("5.0000"), f"CH{i+1} offset should be +5 MHz"


def test_timeout_options_include_off():
    assert 0 in TIMEOUT_OPTIONS


def test_timeout_options_range():
    non_zero = [t for t in TIMEOUT_OPTIONS if t > 0]
    assert min(non_zero) == 15
    assert max(non_zero) == 600
    # Check 15s increments
    for t in non_zero:
        assert t % 15 == 0


def test_vox_delay_options():
    assert len(VOX_DELAY_OPTIONS) >= 3
    assert all(isinstance(d, float) for d in VOX_DELAY_OPTIONS)


def test_relay_delay_options():
    assert RELAY_DELAY_OPTIONS == (0.5, 1.5, 2.5)
