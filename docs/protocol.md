# RT97L Serial Protocol

Reverse-engineered from RT97L.exe binary analysis (state machine at VA 0x40BD40).

## Serial Parameters

- Baud: 9600
- Data bits: 8
- Parity: None
- Stop bits: 1
- Timeout: 1000ms

## Protocol Overview

The protocol uses a state machine driven by received bytes. Each received
byte triggers a WM_USER+7 (0x407) message to the dialog window, which
dispatches to the state machine handler at VA 0x40BD40.

Total configuration data: **256 bytes** (8 read blocks x 32 bytes, or 16 write blocks x 16 bytes).

## Handshake Sequence

```
State 0 — Initial
  HOST opens serial port (DTR/RTS raised)
  DEVICE → HOST: 0x06 (ACK, 1 byte)
  HOST → DEVICE: 0x02 (STX, 1 byte)
  → State 1

State 1 — Wait for device identifier
  DEVICE → HOST: 8 bytes: [0x50 0x33 ... ... ... ... ... 0xFF]
                            'P'   '3'   (model info)       0xFF
  Validation: byte[0]==0x50('P'), byte[1]==0x33('3'), byte[7]==0xFF
  HOST → DEVICE: 0x06 (ACK, 1 byte)
  → State 2

State 2 — Wait for ACK
  DEVICE → HOST: 0x06 (ACK, 1 byte)
  → State 3
```

## Read Sequence (State 3, read flag == 0)

```
State 3 — Data transfer (READ)
  Address counter starts at 0, increments by 0x20 (32) per block.
  Loop while address < 0x100 (256):

    HOST → DEVICE: 4 bytes
      [0] = 0x52 ('R')          — Read command
      [1] = addr >> 8           — Address high byte
      [2] = addr & 0xFF         — Address low byte
      [3] = 0x20                — Block size (32 bytes)
    → State 0x1F (first iteration uses State 0x20)

  State 0x1F / 0x20 — Wait for read response
    DEVICE → HOST: 36 bytes
      [0]    = 0x57 ('W')       — Response marker (Write-back)
      [1]    = addr >> 8        — Address high byte (echo)
      [2]    = addr & 0xFF      — Address low byte (echo)
      [3]    = 0x20             — Block size (echo)
      [4:36] = 32 bytes of data — Configuration data

    After receiving:
      HOST → DEVICE: 0x06 (ACK, 1 byte)
      → State 2 (wait for ACK) → State 3 (next block)

  When address reaches 0x100 (all 8 blocks read):
    HOST → DEVICE: 0x45 ('E', 1 byte) — End command
    Done. (1000ms delay, then close)
```

Total: 8 read blocks × 32 bytes = **256 bytes** of configuration.

## Write Sequence (State 3, write flag != 0)

The write process first reads the initial block (for password verification),
then writes data in 16-byte blocks.

```
State 3 — Data transfer (WRITE)
  Step 1: Read initial block for password check
    HOST → DEVICE: R 00 00 20 (4 bytes)
    DEVICE → HOST: W 00 00 20 [32 bytes] (36 bytes)
    Password extracted from response bytes 17-19 and 33-35.

  Step 2: Write data blocks
    Address counter starts at 0, increments by 0x10 (16) per block.
    Loop while address < 0x100 (256):

      HOST → DEVICE: 20 bytes
        [0]    = 0x57 ('W')     — Write command
        [1]    = addr >> 8      — Address high byte
        [2]    = addr & 0xFF    — Address low byte
        [3]    = 0x10           — Block size (16 bytes)
        [4:20] = 16 bytes data  — Configuration data

      DEVICE → HOST: 0x06 (ACK, 1 byte)
      → State 2 → State 3 (next block)

    When address reaches 0x100 (all 16 blocks written):
      HOST → DEVICE: 0x45 ('E', 1 byte) — End command
      Done.
```

Total: 16 write blocks × 16 bytes = **256 bytes** of configuration.

## Command Summary

| Command | Bytes | Direction | Description |
|---------|-------|-----------|-------------|
| ACK | `06` | Both | Acknowledgment |
| STX | `02` | Host→Dev | Start of transmission |
| Read | `52 HH LL 20` | Host→Dev | Read 32 bytes at address HH:LL |
| Write | `57 HH LL 10 [16B]` | Host→Dev | Write 16 bytes at address HH:LL |
| End | `45` | Host→Dev | End session |

## Memory Map (256 bytes)

Total config is 256 bytes at addresses 0x0000–0x00FF.

With 16 GMRS channels, this is **16 bytes per channel** (addresses 0x00–0xFF).

Exact field offsets TBD — to be determined via serial capture or Ghidra
decompilation of the data model code. Password bytes are at specific offsets
within the first block (bytes 17-19 and 33-35 of the read response).

## Key Addresses in Binary

| Description | VA | File Offset |
|-------------|------|-------------|
| State machine handler | 0x40BD40 | 0xBD40 |
| Prepare read command | 0x40BD10 | 0xBD10 |
| Serial write wrapper | 0x407280 | 0x7280 |
| Send buffer | 0x45F138 | (BSS) |
| Receive buffer | 0x45F338 | (BSS) |
| State variable | 0x45F378 | (BSS) |
| Byte counter | 0x45F3C2 | (BSS) |
| Address counter | 0x45F374 | (BSS) |
| Block counter | 0x45B134 | (BSS) |
| Channel data base | 0x45B138 | (BSS) |
| Write flag | 0x45F3BA | (BSS) |
| Password check fn | 0x408440 | 0x8440 |
