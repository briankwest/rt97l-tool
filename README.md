# RT97L Repeater Programmer

A Linux/macOS terminal application for programming Retevis RT97L and CX-525 GMRS repeaters. Built as a full replacement for the Windows-only RT97L.exe software.

## Features

- **Terminal UI** — Textual-based TUI that runs in any terminal, over SSH, on headless servers, Raspberry Pi, etc.
- **Read/Write** — Read configuration from the repeater and write it back over USB-serial
- **16-channel editor** — Edit all per-channel settings: Rx/Tx frequency, CTCSS/DCS tones, power, squelch, scan, lock, compand
- **Global settings** — Full editor for all 21 global settings organized by category (System, Audio, VOX, Relay, Radio)
- **File save/load** — Save configurations as `.json` (native) or `.txt` (Windows-compatible tab-separated)
- **Password support** — Password field for device authentication during read/write
- **Safety** — Confirmation prompts for unsaved changes, quit blocked during transfers

## Supported Hardware

| Model | Status |
|-------|--------|
| Retevis RT97L | Primary target |
| CX-525 | Supported (same protocol) |

Requires a USB programming cable (Prolific PL2303 or FTDI chipset) with DB9 connector.

## Installation

```bash
# Clone or download
cd rt97l-tool

# Create virtual environment and install
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Requires Python 3.9+.

## Usage

### Launch the TUI

```bash
source .venv/bin/activate
python -m rt97l
```

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Enter` / `e` | Edit selected channel |
| `Ctrl+R` | Read configuration from repeater |
| `Ctrl+W` | Write configuration to repeater |
| `Ctrl+S` | Save configuration to file |
| `Ctrl+O` | Open configuration file |
| `Ctrl+G` | Edit global settings |
| `Ctrl+P` | Select serial port |
| `Ctrl+Q` | Quit (prompts if unsaved changes) |
| `Escape` | Close current dialog / cancel |

### Serial Capture Tool

A standalone tool for protocol debugging and validation:

```bash
# Probe — test handshake only
python tools/serial_capture.py /dev/ttyUSB0 --probe

# Read — dump full config and save raw bytes
python tools/serial_capture.py /dev/ttyUSB0 --read -o dump.bin

# Write — upload raw bytes to repeater
python tools/serial_capture.py /dev/ttyUSB0 --write dump.bin

# Passive capture — log all serial traffic
python tools/serial_capture.py /dev/ttyUSB0 --passive
```

### File Formats

**JSON** (`.json`) — Native format, human-readable, preserves all settings including globals and password.

**Text** (`.txt`) — Tab-separated format compatible with the Windows RT97L.exe "Save As" function. Useful for migrating existing configurations.

## Serial Protocol

The serial protocol was reverse-engineered from the RT97L.exe binary (MFC C++ application, ~610KB). Full documentation is in [`docs/protocol.md`](docs/protocol.md).

### Summary

- **Serial**: 9600 baud, 8N1, 1000ms timeout
- **Handshake**: ACK/STX exchange, 8-byte device ID starting with `P3`
- **Read**: 8 blocks of 32 bytes = 256 bytes total (`R addr_hi addr_lo 20`)
- **Write**: 16 blocks of 16 bytes = 256 bytes total (`W addr_hi addr_lo 10 [16B]`)
- **End**: Single `E` byte

## Per-Channel Settings

Each of the 16 channels supports:

| Setting | Values |
|---------|--------|
| Rx Frequency | 400.0000–520.0000 MHz |
| Tx Frequency | 400.0000–520.0000 MHz |
| CT/DCS Encode | OFF, 50 CTCSS tones (67.0–254.1 Hz), 210 DCS codes |
| CT/DCS Decode | Same as encode |
| Tx Power | High, Low |
| Squelch Level | OFF, 0–9 |
| Channel Mode | Frequency, CH+Frequency |
| Compand | Wide, Narrow |
| Scan Add | Yes, No |
| Channel Lock | Yes, No |

## Global Settings

| Category | Settings |
|----------|----------|
| System | Model Type (RT97L/CX-525), Frequency Band, Language |
| Audio | Audio Output, Volume (1–8), Beep, Voice Prompts, Mic Gain (-3 to +3) |
| VOX | VOX Set, VOX Function, VOX Level (1–8), VOX Delay (0.5–3.0s) |
| Relay | Relay (ON/OFF), Relay Delay (0.5/1.5/2.5s) |
| Radio | STE, Timeout (OFF/15–600s), Battery Save, Backlight, Low Temperature |

## Project Structure

```
rt97l-tool/
  rt97l/
    __main__.py         Entry point
    app.py              Textual application, keybindings, screen routing
    constants.py        CTCSS tones, DCS codes, GMRS frequencies, enums
    data_model.py       ChannelConfig, GlobalConfig, RepeaterConfig
    config.py           INI config reader/writer (Windows compat)
    file_io.py          JSON and text file save/load
    protocol.py         Serial protocol (handshake, read, write, end)
    serial_port.py      pyserial wrapper with port enumeration
    memory_map.py       Wire format encode/decode (BCD frequencies, tone indexes)
    screens/
      channel_table.py  Main 16-channel DataTable view
      channel_edit.py   Single-channel edit form
      global_settings.py Global settings editor
      com_port.py       Port select, read/write, save/open, confirm dialogs
  tools/
    serial_capture.py   Standalone serial capture/debug tool
  tests/                76 unit tests
  docs/
    protocol.md         Reverse-engineered protocol specification
```

## What Has Been Tested

- All 50 CTCSS tones and 210 DCS codes extracted and validated
- Data model validation (frequency ranges, tone validity, setting constraints)
- JSON and text file round-trip save/load
- BCD frequency encoding/decoding
- Tone index encoding/decoding (all 260 options)
- Channel config encode/decode round-trip
- Protocol command construction (read, write, handshake, end)
- Protocol error handling (bad device ID, timeout, short response, wrong size)
- TUI screen navigation (all screens open and close correctly)
- 76 automated tests, all passing

## What Still Needs Testing With Hardware

The following require the actual RT97L repeater and programming cable:

### Protocol Validation (Critical — Do First)

1. **Handshake sequence** — Confirm the device sends ACK first when the port opens, or if the host needs to send a trigger byte. Run:
   ```bash
   python tools/serial_capture.py /dev/ttyUSB0 --probe
   ```

2. **Read full configuration** — Verify all 8 read blocks complete successfully and capture the raw 256-byte dump:
   ```bash
   python tools/serial_capture.py /dev/ttyUSB0 --read -o dump.bin
   ```

3. **Compare with Windows tool** — Read the same repeater with RT97L.exe, save to `.txt`, then read with this tool and compare values to confirm the memory map is correct.

### Memory Map Validation (Critical)

4. **Frequency encoding** — The memory map assumes BCD encoding (e.g., 462.5500 MHz → `0x46255000`). This needs confirmation against the captured bytes. If the device uses a different encoding (binary scaled integer, etc.), `memory_map.py` will need adjustment.

5. **Tone index mapping** — Verify that tone index 1 = 67.0 Hz, index 51 = D023N, etc. Set a known CTCSS tone in the Windows tool, read with capture tool, check the byte value.

6. **Per-channel byte layout** — The 16-byte-per-channel structure with field offsets (freq at 0, tones at 8-9, flags at 10-12) is provisional. Need to set known values for each field in the Windows tool and verify the byte positions.

7. **Global settings location** — Global settings may be encoded in reserved bytes within channel records, or in a separate area within the 256 bytes. Currently globals are not encoded in the wire format (`memory_map.py` has a TODO for this).

### Write Validation (Do After Read Is Confirmed)

8. **Write round-trip** — Write a config from this tool, then read it back with both this tool and RT97L.exe to confirm data integrity.

9. **Password verification** — Test that the default password (288288) works, and test with a custom password.

10. **Write protection** — Verify that quit is blocked during write and that a failed write doesn't brick the repeater (the device should reject bad data).

### Platform Testing

11. **Linux x86_64** — Primary target, USB-serial with PL2303 driver
12. **Raspberry Pi (ARM)** — Common field deployment scenario
13. **macOS** — Development platform, verify serial port enumeration finds the cable

### Edge Cases

14. **Cable disconnect mid-transfer** — Verify error handling and that the app recovers gracefully
15. **Wrong baud rate** — Confirm timeout and error message
16. **Multiple repeaters** — Verify different device IDs are handled correctly

## Known Limitations

- **Memory map is provisional** — Per-channel byte offsets and global settings encoding need hardware validation before the tool can reliably write to a repeater. Reading and saving to file should work once the protocol handshake is confirmed.
- **No firmware update support** — This tool only handles configuration, not firmware.
- **No clone/copy between repeaters** — Not yet implemented, but the raw binary dump from the capture tool can be used manually.

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| pyserial | >=3.5 | Serial port communication |
| textual | >=0.80 | Terminal user interface |
| pytest | >=7.0 | Testing (dev only) |

## License

This project is an independent reverse-engineering effort. It is not affiliated with or endorsed by Retevis.

## Credits

Protocol reverse-engineered from RT97L.exe (version 0.1, dated 2019) through static binary analysis using objdump disassembly of the MFC application's serial communication state machine.

Related open-source projects that informed the protocol analysis:
- [CHIRP](https://github.com/kk7ds/chirp) — Open-source radio programming tool
- [OpenMicron](https://github.com/CircuitChaos/OpenMicron) — Retevis RT-95 Linux programmer
