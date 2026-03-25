"""RT97L serial protocol implementation.

Implements the handshake, read, and write sequences reverse-engineered
from the RT97L.exe state machine (see docs/protocol.md).

Protocol summary:
  Handshake: ACK(06) → STX(02) → DeviceID(8B) → ACK(06) → ACK(06)
  Read:  R HH LL 20 → W HH LL 20 [32B] → ACK(06), repeat 8 times
  Write: W HH LL 10 [16B] → ACK(06), repeat 16 times
  End:   E(45)
"""

from __future__ import annotations

import logging
import time
from typing import Callable, Optional

from rt97l.serial_port import SerialPort

log = logging.getLogger(__name__)

# Protocol constants
ACK = 0x06
STX = 0x02
CMD_READ = 0x52   # 'R'
CMD_WRITE = 0x57  # 'W'
CMD_END = 0x45    # 'E'

CONFIG_SIZE = 256         # Total configuration size in bytes
READ_BLOCK_SIZE = 32      # Bytes per read request
WRITE_BLOCK_SIZE = 16     # Bytes per write request
READ_BLOCKS = CONFIG_SIZE // READ_BLOCK_SIZE    # 8
WRITE_BLOCKS = CONFIG_SIZE // WRITE_BLOCK_SIZE  # 16

DEVICE_ID_LEN = 8         # Length of device identifier response
HANDSHAKE_TIMEOUT = 3.0    # Seconds to wait for initial ACK
END_DELAY = 1.0            # Delay after sending End command

ProgressCallback = Optional[Callable[[int, int], None]]


class ProtocolError(Exception):
    """Raised when the protocol encounters an unexpected response."""


class RT97LProtocol:
    """Serial protocol handler for RT97L/CX-525 repeaters."""

    def __init__(self, port: SerialPort):
        self.port = port
        self.device_id: bytes = b""

    def enter_programming_mode(self) -> bytes:
        """Perform handshake and return the 8-byte device identifier.

        Sequence:
          1. Wait for device ACK (0x06) — device sends this when ready
          2. Send STX (0x02)
          3. Receive 8-byte device ID (starts with 'P3', ends with 0xFF)
          4. Send ACK (0x06)
          5. Receive ACK (0x06)

        If the device doesn't send the initial ACK within the timeout,
        we try sending STX first (some devices need a nudge).
        """
        log.info("Entering programming mode...")

        # Wait for device ACK
        data = self.port.read(1)

        if not data or data[0] != ACK:
            # Try sending STX to wake the device
            log.debug("No initial ACK, sending STX to wake device")
            self.port.write(bytes([STX]))
            time.sleep(0.1)
            data = self.port.read(1)
            if not data or data[0] != ACK:
                raise ProtocolError(
                    f"Device did not ACK. Got: {data.hex(' ') if data else 'timeout'}"
                )

        # Send STX
        self.port.write(bytes([STX]))

        # Read device identifier (8 bytes)
        device_id = self.port.read(DEVICE_ID_LEN)
        if len(device_id) != DEVICE_ID_LEN:
            raise ProtocolError(
                f"Incomplete device ID: expected {DEVICE_ID_LEN} bytes, "
                f"got {len(device_id)}"
            )
        if device_id[0] != 0x50 or device_id[1] != 0x33:  # 'P' '3'
            raise ProtocolError(
                f"Unexpected device ID: {device_id.hex(' ')} "
                f"(expected 'P3...')"
            )
        if device_id[7] != 0xFF:
            log.warning(
                "Device ID byte 7 = 0x%02x (expected 0xFF)", device_id[7]
            )

        self.device_id = device_id
        log.info("Device ID: %s", device_id.hex(" "))

        # Send ACK
        self.port.write(bytes([ACK]))

        # Wait for ACK
        ack = self.port.read(1)
        if not ack or ack[0] != ACK:
            raise ProtocolError(
                f"No ACK after device ID. Got: {ack.hex(' ') if ack else 'timeout'}"
            )

        log.info("Programming mode entered successfully")
        return device_id

    def read_config(self, progress: ProgressCallback = None) -> bytes:
        """Read the full 256-byte configuration from the repeater.

        Sends 8 read commands of 32 bytes each at addresses
        0x0000, 0x0020, 0x0040, ..., 0x00E0.

        Returns the complete 256-byte configuration data.
        """
        log.info("Reading configuration...")
        config = bytearray(CONFIG_SIZE)
        addr = 0

        for block in range(READ_BLOCKS):
            # Send: R addr_hi addr_lo 0x20
            cmd = bytes([
                CMD_READ,
                (addr >> 8) & 0xFF,
                addr & 0xFF,
                READ_BLOCK_SIZE,
            ])
            self.port.write(cmd)
            log.debug("TX: R %04x %02x", addr, READ_BLOCK_SIZE)

            # Receive: W addr_hi addr_lo 0x20 [32 bytes data]
            resp = self.port.read(4 + READ_BLOCK_SIZE)
            expected_len = 4 + READ_BLOCK_SIZE
            if len(resp) != expected_len:
                raise ProtocolError(
                    f"Read block {block}: expected {expected_len} bytes, "
                    f"got {len(resp)}"
                )
            if resp[0] != CMD_WRITE:
                raise ProtocolError(
                    f"Read block {block}: expected 'W' (0x57), got 0x{resp[0]:02x}"
                )

            # Store data
            config[addr:addr + READ_BLOCK_SIZE] = resp[4:]

            # Send ACK
            self.port.write(bytes([ACK]))

            # Wait for ACK (device confirms)
            ack = self.port.read(1)
            if not ack or ack[0] != ACK:
                log.warning(
                    "Block %d: expected ACK, got %s",
                    block,
                    ack.hex(" ") if ack else "timeout",
                )

            addr += READ_BLOCK_SIZE

            if progress:
                progress(block + 1, READ_BLOCKS)

        log.info("Read complete: %d bytes", CONFIG_SIZE)
        return bytes(config)

    def write_config(
        self, data: bytes, progress: ProgressCallback = None
    ) -> None:
        """Write the full 256-byte configuration to the repeater.

        Sends 16 write commands of 16 bytes each at addresses
        0x0000, 0x0010, 0x0020, ..., 0x00F0.
        """
        if len(data) != CONFIG_SIZE:
            raise ValueError(
                f"Expected {CONFIG_SIZE} bytes, got {len(data)}"
            )

        log.info("Writing configuration...")
        addr = 0

        for block in range(WRITE_BLOCKS):
            # Build: W addr_hi addr_lo 0x10 [16 bytes]
            block_data = data[addr:addr + WRITE_BLOCK_SIZE]
            cmd = bytes([
                CMD_WRITE,
                (addr >> 8) & 0xFF,
                addr & 0xFF,
                WRITE_BLOCK_SIZE,
            ]) + block_data
            self.port.write(cmd)
            log.debug("TX: W %04x [%s]", addr, block_data.hex(" "))

            # Wait for ACK
            ack = self.port.read(1)
            if not ack or ack[0] != ACK:
                raise ProtocolError(
                    f"Write block {block} at 0x{addr:04x}: "
                    f"no ACK. Got: {ack.hex(' ') if ack else 'timeout'}"
                )

            # Wait for second ACK (state 2 → state 3 transition)
            ack2 = self.port.read(1)
            if ack2 and ack2[0] != ACK:
                log.warning(
                    "Block %d: unexpected byte after ACK: 0x%02x",
                    block, ack2[0],
                )

            addr += WRITE_BLOCK_SIZE

            if progress:
                progress(block + 1, WRITE_BLOCKS)

        log.info("Write complete: %d bytes", CONFIG_SIZE)

    def exit_programming_mode(self) -> None:
        """Send End command and close the session."""
        log.info("Exiting programming mode...")
        self.port.write(bytes([CMD_END]))
        time.sleep(END_DELAY)
        log.info("Session ended")
