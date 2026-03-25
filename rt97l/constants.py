"""Constants extracted from RT97L.exe binary analysis.

All CTCSS tones, DCS codes, GMRS frequencies, and enumerated values
used by the RT97L / CX-525 GMRS repeaters.
"""

from decimal import Decimal
from enum import Enum

# ---------------------------------------------------------------------------
# CTCSS tones (50 standard tones, Hz) — extracted from binary strings
# ---------------------------------------------------------------------------
CTCSS_TONES: tuple[str, ...] = (
    "67.0", "69.3", "71.9", "74.4", "77.0", "79.7", "82.5", "85.4",
    "88.5", "91.5", "94.8", "97.4", "100.0", "103.5", "107.2", "110.9",
    "114.8", "118.8", "123.0", "127.3", "131.8", "136.5", "141.3", "146.2",
    "151.4", "156.7", "159.8", "162.2", "165.5", "167.9", "171.3", "173.8",
    "177.3", "179.9", "183.5", "186.2", "189.9", "192.8", "196.6", "199.5",
    "203.5", "206.5", "210.7", "218.1", "225.7", "229.1", "233.6", "241.8",
    "250.3", "254.1",
)

# ---------------------------------------------------------------------------
# DCS codes — 105 base codes, each with Normal (N) and Inverted (I) polarity
# Extracted from binary strings (D023N, D023I, ... D754N, D754I)
# ---------------------------------------------------------------------------
DCS_CODES_BASE: tuple[str, ...] = (
    "023", "025", "026", "031", "032", "036", "043", "047",
    "051", "053", "054", "065", "071", "072", "073", "074",
    "114", "115", "116", "122", "125", "131", "132", "134",
    "143", "145", "152", "155", "156", "162", "165", "172",
    "174", "205", "212", "223", "225", "226", "243", "244",
    "245", "246", "251", "252", "255", "261", "263", "265",
    "266", "271", "274", "306", "311", "315", "325", "331",
    "332", "343", "346", "351", "356", "364", "365", "371",
    "411", "412", "413", "423", "431", "432", "445", "446",
    "452", "454", "455", "462", "464", "465", "466", "503",
    "506", "516", "523", "526", "532", "546", "565", "606",
    "612", "624", "627", "631", "632", "645", "654", "662",
    "664", "703", "712", "723", "731", "732", "734", "743",
    "754",
)

DCS_CODES_NORMAL: tuple[str, ...] = tuple(f"D{c}N" for c in DCS_CODES_BASE)
DCS_CODES_INVERTED: tuple[str, ...] = tuple(f"D{c}I" for c in DCS_CODES_BASE)
DCS_CODES_ALL: tuple[str, ...] = DCS_CODES_NORMAL + DCS_CODES_INVERTED

# Combined tone/code list for CT/DCS selector: "OFF" + CTCSS tones + DCS codes
TONE_OPTIONS: tuple[str, ...] = ("OFF",) + CTCSS_TONES + DCS_CODES_ALL

# ---------------------------------------------------------------------------
# GMRS frequencies (MHz) — 16 channels extracted from binary
# Channels 1-8: simplex on 462.xxxx
# Channels 9-16: repeater pairs (RX on 462, TX on 467)
# ---------------------------------------------------------------------------
GMRS_RX_FREQS: tuple[Decimal, ...] = (
    Decimal("462.5500"), Decimal("462.5750"), Decimal("462.6000"), Decimal("462.6250"),
    Decimal("462.6500"), Decimal("462.6750"), Decimal("462.7000"), Decimal("462.7250"),
    Decimal("462.5500"), Decimal("462.5750"), Decimal("462.6000"), Decimal("462.6250"),
    Decimal("462.6500"), Decimal("462.6750"), Decimal("462.7000"), Decimal("462.7250"),
)

GMRS_TX_FREQS: tuple[Decimal, ...] = (
    Decimal("462.5500"), Decimal("462.5750"), Decimal("462.6000"), Decimal("462.6250"),
    Decimal("462.6500"), Decimal("462.6750"), Decimal("462.7000"), Decimal("462.7250"),
    Decimal("467.5500"), Decimal("467.5750"), Decimal("467.6000"), Decimal("467.6250"),
    Decimal("467.6500"), Decimal("467.6750"), Decimal("467.7000"), Decimal("467.7250"),
)

NUM_CHANNELS = 16

# Frequency band limits (MHz)
FREQ_MIN = Decimal("400.0000")
FREQ_MAX = Decimal("520.0000")

# ---------------------------------------------------------------------------
# Enumerated settings — extracted from binary string analysis
# ---------------------------------------------------------------------------


class TxPower(str, Enum):
    HIGH = "High"
    LOW = "Low"


class SquelchLevel(str, Enum):
    OFF = "OFF"
    L0 = "0"
    L1 = "1"
    L2 = "2"
    L3 = "3"
    L4 = "4"
    L5 = "5"
    L6 = "6"
    L7 = "7"
    L8 = "8"
    L9 = "9"


class ChannelMode(str, Enum):
    FREQUENCY = "Frequency"
    CH_FREQUENCY = "CH+Frequency"


class Compand(str, Enum):
    NARROW = "Narrow"
    WIDE = "Wide"


class Bandwidth(str, Enum):
    NARROW = "Narrow"
    WIDE = "Wide"


class Language(str, Enum):
    ENGLISH = "English"
    CHINESE = "Chinese"


class ModelType(str, Enum):
    RT97L = "RT97L"
    CX525 = "CX-525"


class OnOff(str, Enum):
    ON = "ON"
    OFF = "OFF"


# Volume level range (1-8, typical for Retevis)
VOLUME_MIN = 1
VOLUME_MAX = 8

# VOX delay options (seconds) — from binary
VOX_DELAY_OPTIONS: tuple[float, ...] = (0.5, 1.0, 1.5, 2.0, 2.5, 3.0)

# VOX level range
VOX_LEVEL_MIN = 1
VOX_LEVEL_MAX = 8

# Mic gain range (-3 to +3)
MIC_GAIN_MIN = -3
MIC_GAIN_MAX = 3

# Relay delay options (seconds) — from binary
RELAY_DELAY_OPTIONS: tuple[float, ...] = (0.5, 1.5, 2.5)

# Timeout options (seconds) — 15s increments from 15 to 600, plus OFF
TIMEOUT_OPTIONS: tuple[int, ...] = (0,) + tuple(range(15, 601, 15))

# Frequency band options
FREQ_BAND_OPTIONS: tuple[int, ...] = (1, 2)

# Default password (per Retevis documentation)
DEFAULT_PASSWORD = "288288"

# Serial communication defaults
DEFAULT_BAUD_RATE = 9600
DEFAULT_DATA_BITS = 8
DEFAULT_PARITY = "N"
DEFAULT_STOP_BITS = 1
DEFAULT_TIMEOUT_MS = 1000
