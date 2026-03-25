"""Serial port abstraction for RT97L / CX-525 communication.

Wraps pyserial with port enumeration, automatic configuration
(9600 8N1), timeout management, and optional hex logging for
protocol debugging.
"""

from __future__ import annotations

import glob
import logging
import sys
import time
from typing import Optional

import serial

from rt97l.constants import (
    DEFAULT_BAUD_RATE,
    DEFAULT_DATA_BITS,
    DEFAULT_PARITY,
    DEFAULT_STOP_BITS,
    DEFAULT_TIMEOUT_MS,
)

log = logging.getLogger(__name__)


def enumerate_ports() -> list[str]:
    """Return a sorted list of available serial port device paths."""
    patterns: list[str] = []
    if sys.platform == "linux":
        patterns = ["/dev/ttyUSB*", "/dev/ttyACM*"]
    elif sys.platform == "darwin":
        patterns = ["/dev/tty.usbserial*", "/dev/cu.usbserial*",
                     "/dev/tty.usbmodem*", "/dev/cu.usbmodem*",
                     "/dev/tty.PL*", "/dev/cu.PL*",
                     "/dev/tty.SLAB*", "/dev/cu.SLAB*"]
    else:
        # Windows-style names, though this tool targets Linux/macOS
        return [f"COM{i}" for i in range(1, 10)]

    ports: list[str] = []
    for pattern in patterns:
        ports.extend(glob.glob(pattern))
    return sorted(set(ports))


class SerialPort:
    """Managed serial connection to an RT97L/CX-525 repeater."""

    def __init__(
        self,
        port: str,
        baud_rate: int = DEFAULT_BAUD_RATE,
        timeout_ms: int = DEFAULT_TIMEOUT_MS,
        debug_log: bool = False,
    ):
        self.port_name = port
        self.baud_rate = baud_rate
        self.timeout_sec = timeout_ms / 1000.0
        self.debug_log = debug_log
        self._serial: Optional[serial.Serial] = None

    @property
    def is_open(self) -> bool:
        return self._serial is not None and self._serial.is_open

    def open(self) -> None:
        """Open the serial port with RT97L parameters (9600 8N1)."""
        if self.is_open:
            return
        log.info("Opening %s at %d baud", self.port_name, self.baud_rate)
        self._serial = serial.Serial(
            port=self.port_name,
            baudrate=self.baud_rate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=self.timeout_sec,
            write_timeout=self.timeout_sec,
        )
        # Flush any stale data
        self._serial.reset_input_buffer()
        self._serial.reset_output_buffer()

    def close(self) -> None:
        """Close the serial port."""
        if self._serial and self._serial.is_open:
            log.info("Closing %s", self.port_name)
            self._serial.close()
        self._serial = None

    def write(self, data: bytes) -> int:
        """Write bytes to the serial port. Returns number of bytes written."""
        if not self.is_open:
            raise ConnectionError("Serial port not open")
        if self.debug_log:
            log.debug("TX [%d]: %s", len(data), data.hex(" "))
        n = self._serial.write(data)
        self._serial.flush()
        return n

    def read(self, size: int) -> bytes:
        """Read exactly `size` bytes (or fewer on timeout)."""
        if not self.is_open:
            raise ConnectionError("Serial port not open")
        data = self._serial.read(size)
        if self.debug_log and data:
            log.debug("RX [%d/%d]: %s", len(data), size, data.hex(" "))
        return data

    def read_until(self, expected: bytes = b"\n", max_size: int = 4096) -> bytes:
        """Read until `expected` sequence or timeout."""
        if not self.is_open:
            raise ConnectionError("Serial port not open")
        data = self._serial.read_until(expected, max_size)
        if self.debug_log and data:
            log.debug("RX [%d]: %s", len(data), data.hex(" "))
        return data

    def read_all_available(self, delay: float = 0.05) -> bytes:
        """Read all currently available bytes from the input buffer."""
        if not self.is_open:
            raise ConnectionError("Serial port not open")
        time.sleep(delay)  # Brief pause to let data arrive
        n = self._serial.in_waiting
        if n == 0:
            return b""
        data = self._serial.read(n)
        if self.debug_log and data:
            log.debug("RX [%d avail]: %s", len(data), data.hex(" "))
        return data

    def flush_input(self) -> None:
        """Discard any unread input data."""
        if self.is_open:
            self._serial.reset_input_buffer()

    def flush_output(self) -> None:
        """Wait for all output data to be transmitted."""
        if self.is_open:
            self._serial.flush()

    def __enter__(self) -> SerialPort:
        self.open()
        return self

    def __exit__(self, *args) -> None:
        self.close()
