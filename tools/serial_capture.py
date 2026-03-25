#!/usr/bin/env python3
"""Serial capture tool for RT97L protocol analysis.

Captures all bytes exchanged between the host and an RT97L repeater,
with protocol-aware decoding.

Usage:
    python tools/serial_capture.py /dev/ttyUSB0
    python tools/serial_capture.py /dev/ttyUSB0 --raw    # hex dump only
    python tools/serial_capture.py /dev/ttyUSB0 --read    # perform a read
    python tools/serial_capture.py /dev/ttyUSB0 --write   # perform a write
"""

import argparse
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import serial


def hex_dump(data: bytes, prefix: str = "") -> str:
    """Format bytes as hex dump."""
    if not data:
        return f"{prefix}(empty)"
    hex_str = data.hex(" ")
    ascii_str = "".join(chr(b) if 32 <= b < 127 else "." for b in data)
    return f"{prefix}[{len(data):3d}] {hex_str}  |{ascii_str}|"


def decode_command(data: bytes, direction: str) -> str:
    """Decode a known protocol command."""
    if not data:
        return "empty"
    if len(data) == 1:
        b = data[0]
        if b == 0x06:
            return "ACK"
        if b == 0x02:
            return "STX (start handshake)"
        if b == 0x45:
            return "END (session end)"
        return f"byte: 0x{b:02x}"

    if data[0] == 0x52 and len(data) == 4:  # 'R'
        addr = (data[1] << 8) | data[2]
        size = data[3]
        return f"READ addr=0x{addr:04x} size={size}"

    if data[0] == 0x57 and len(data) >= 4:  # 'W'
        addr = (data[1] << 8) | data[2]
        size = data[3]
        if len(data) == 4 + size:
            return f"WRITE addr=0x{addr:04x} size={size} data=[{data[4:].hex(' ')}]"
        elif len(data) == 36 and size == 0x20:
            return f"READ-RESPONSE addr=0x{addr:04x} size={size} data=[{data[4:].hex(' ')}]"

    if data[0] == 0x50 and len(data) == 8:  # 'P'
        return f"DEVICE-ID: [{data.hex(' ')}] (model='{chr(data[0])}{chr(data[1])}')"

    return f"unknown ({len(data)} bytes)"


def perform_handshake(port: serial.Serial, verbose: bool = True) -> bool:
    """Perform the RT97L handshake sequence."""
    if verbose:
        print("\n=== Handshake ===")

    # Wait for device ACK (0x06)
    if verbose:
        print("Waiting for device ACK...")
    data = port.read(1)
    if verbose:
        print(f"  RX: {hex_dump(data)}")
    if not data or data[0] != 0x06:
        # Try sending STX first to trigger the device
        if verbose:
            print("  No ACK received, trying to send STX (0x02)...")
        port.write(b"\x02")
        data = port.read(1)
        if verbose:
            print(f"  RX: {hex_dump(data)}")
        if not data or data[0] != 0x06:
            print("ERROR: Device did not respond with ACK")
            return False

    # Send STX (0x02)
    if verbose:
        print("Sending STX (0x02)...")
    port.write(b"\x02")
    if verbose:
        print(f"  TX: {hex_dump(b'\\x02')}")

    # Read device identifier (8 bytes)
    data = port.read(8)
    if verbose:
        print(f"  RX: {hex_dump(data)} -> {decode_command(data, 'RX')}")
    if len(data) != 8 or data[0] != 0x50 or data[1] != 0x33:
        print(f"ERROR: Unexpected device ID: {data.hex(' ')}")
        return False

    # Send ACK
    port.write(b"\x06")
    if verbose:
        print(f"  TX: ACK (0x06)")

    # Wait for ACK
    data = port.read(1)
    if verbose:
        print(f"  RX: {hex_dump(data)}")
    if not data or data[0] != 0x06:
        print("ERROR: No ACK after handshake")
        return False

    if verbose:
        print("Handshake complete!\n")
    return True


def read_config(port: serial.Serial, verbose: bool = True) -> bytes:
    """Read 256 bytes of configuration from the repeater."""
    if verbose:
        print("=== Reading Configuration ===")

    config_data = bytearray(256)
    addr = 0

    while addr < 0x100:
        # Send read command: R addr_hi addr_lo 0x20
        cmd = bytes([0x52, (addr >> 8) & 0xFF, addr & 0xFF, 0x20])
        port.write(cmd)
        if verbose:
            print(f"  TX: {decode_command(cmd, 'TX')}")

        # Read response: W addr_hi addr_lo 0x20 [32 bytes]
        resp = port.read(36)
        if verbose:
            print(f"  RX: {decode_command(resp, 'RX')}")

        if len(resp) != 36:
            print(f"ERROR: Expected 36 bytes, got {len(resp)}")
            return bytes()
        if resp[0] != 0x57:
            print(f"ERROR: Expected 'W' (0x57), got 0x{resp[0]:02x}")
            return bytes()

        # Store data
        config_data[addr:addr + 32] = resp[4:36]

        # Send ACK
        port.write(b"\x06")

        # Wait for ACK
        ack = port.read(1)
        if not ack or ack[0] != 0x06:
            print(f"WARNING: Expected ACK, got {ack.hex(' ') if ack else 'timeout'}")

        addr += 0x20

    # Send End
    port.write(b"\x45")
    if verbose:
        print(f"  TX: END (0x45)")
        print(f"\nRead complete! {len(config_data)} bytes captured.\n")

    return bytes(config_data)


def write_config(port: serial.Serial, data: bytes, verbose: bool = True) -> bool:
    """Write 256 bytes of configuration to the repeater."""
    if len(data) != 256:
        print(f"ERROR: Expected 256 bytes, got {len(data)}")
        return False

    if verbose:
        print("=== Writing Configuration ===")

    addr = 0
    while addr < 0x100:
        # Build write command: W addr_hi addr_lo 0x10 [16 bytes]
        block = data[addr:addr + 16]
        cmd = bytes([0x57, (addr >> 8) & 0xFF, addr & 0xFF, 0x10]) + block
        port.write(cmd)
        if verbose:
            print(f"  TX: WRITE addr=0x{addr:04x} [{block.hex(' ')}]")

        # Wait for ACK
        ack = port.read(1)
        if not ack or ack[0] != 0x06:
            print(f"ERROR: No ACK after write at addr 0x{addr:04x}")
            return False
        if verbose:
            print(f"  RX: ACK")

        # Wait for second ACK (state 2 -> state 3)
        ack2 = port.read(1)
        if ack2 and ack2[0] == 0x06:
            if verbose:
                print(f"  RX: ACK")

        addr += 0x10

    # Send End
    port.write(b"\x45")
    if verbose:
        print(f"  TX: END (0x45)")
        print(f"\nWrite complete!\n")

    return True


def passive_capture(port: serial.Serial):
    """Passively capture and display all serial data."""
    print("=== Passive Capture Mode ===")
    print("Listening for serial data... (Ctrl+C to stop)\n")

    try:
        while True:
            data = port.read(1)
            if data:
                # Read any additional available bytes
                time.sleep(0.02)
                n = port.in_waiting
                if n > 0:
                    data += port.read(n)
                ts = time.strftime("%H:%M:%S")
                print(f"[{ts}] {hex_dump(data)} -> {decode_command(data, '??')}")
    except KeyboardInterrupt:
        print("\nCapture stopped.")


def main():
    parser = argparse.ArgumentParser(description="RT97L Serial Capture Tool")
    parser.add_argument("port", help="Serial port (e.g., /dev/ttyUSB0)")
    parser.add_argument("--baud", type=int, default=9600, help="Baud rate (default: 9600)")
    parser.add_argument("--read", action="store_true", help="Perform a full read")
    parser.add_argument("--write", metavar="FILE", help="Write config from raw binary file")
    parser.add_argument("--output", "-o", metavar="FILE", help="Save captured data to file")
    parser.add_argument("--passive", action="store_true", help="Passive capture mode")
    parser.add_argument("--probe", action="store_true",
                        help="Probe: try handshake only, don't read/write")
    args = parser.parse_args()

    print(f"Opening {args.port} at {args.baud} baud...")
    port = serial.Serial(
        port=args.port,
        baudrate=args.baud,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        timeout=2.0,
        write_timeout=2.0,
    )
    port.reset_input_buffer()
    port.reset_output_buffer()
    print(f"Port opened: {port.name}\n")

    try:
        if args.passive:
            passive_capture(port)
            return

        if args.probe:
            ok = perform_handshake(port)
            print(f"Handshake {'succeeded' if ok else 'FAILED'}")
            if ok:
                port.write(b"\x45")  # End
            return

        if args.read:
            ok = perform_handshake(port)
            if not ok:
                return
            data = read_config(port)
            if data:
                print("=== Configuration Hex Dump ===")
                for offset in range(0, len(data), 16):
                    chunk = data[offset:offset + 16]
                    hex_str = chunk.hex(" ")
                    ascii_str = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
                    print(f"  {offset:04x}: {hex_str:<48s} |{ascii_str}|")

                if args.output:
                    out_path = Path(args.output)
                    out_path.write_bytes(data)
                    print(f"\nSaved {len(data)} bytes to {out_path}")
            return

        if args.write:
            in_data = Path(args.write).read_bytes()
            ok = perform_handshake(port)
            if not ok:
                return
            write_config(port, in_data)
            return

        # Default: probe + read
        ok = perform_handshake(port)
        if ok:
            data = read_config(port)
            if data and args.output:
                Path(args.output).write_bytes(data)
                print(f"Saved to {args.output}")

    finally:
        port.close()
        print("Port closed.")


if __name__ == "__main__":
    main()
