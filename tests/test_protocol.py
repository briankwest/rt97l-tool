"""Tests for protocol command construction and parsing.

These tests verify the protocol logic without requiring real hardware
by using mock serial ports.
"""

from unittest.mock import MagicMock, call, patch

import pytest

from rt97l.protocol import (
    ACK,
    CMD_END,
    CMD_READ,
    CMD_WRITE,
    CONFIG_SIZE,
    READ_BLOCK_SIZE,
    READ_BLOCKS,
    STX,
    WRITE_BLOCK_SIZE,
    WRITE_BLOCKS,
    ProtocolError,
    RT97LProtocol,
)


def make_mock_port():
    """Create a mock SerialPort."""
    port = MagicMock()
    port.is_open = True
    return port


class TestHandshake:
    def test_successful_handshake(self):
        port = make_mock_port()
        # Simulate: ACK, device ID (P3...FF), ACK
        device_id = bytes([0x50, 0x33, 0x00, 0x00, 0x00, 0x00, 0x00, 0xFF])
        port.read.side_effect = [
            bytes([ACK]),      # Initial ACK
            device_id,         # Device ID
            bytes([ACK]),      # Final ACK
        ]
        proto = RT97LProtocol(port)
        result = proto.enter_programming_mode()
        assert result == device_id

        # Verify STX and ACK were sent
        calls = port.write.call_args_list
        assert calls[0] == call(bytes([STX]))
        assert calls[1] == call(bytes([ACK]))

    def test_handshake_retry_on_no_initial_ack(self):
        port = make_mock_port()
        device_id = bytes([0x50, 0x33, 0x00, 0x00, 0x00, 0x00, 0x00, 0xFF])
        port.read.side_effect = [
            b"",               # No initial response
            bytes([ACK]),      # ACK after STX nudge
            device_id,         # Device ID
            bytes([ACK]),      # Final ACK
        ]
        proto = RT97LProtocol(port)
        result = proto.enter_programming_mode()
        assert result == device_id

    def test_handshake_fails_on_bad_device_id(self):
        port = make_mock_port()
        port.read.side_effect = [
            bytes([ACK]),
            bytes([0x00] * 8),  # Bad device ID
        ]
        proto = RT97LProtocol(port)
        with pytest.raises(ProtocolError, match="Unexpected device ID"):
            proto.enter_programming_mode()

    def test_handshake_fails_on_timeout(self):
        port = make_mock_port()
        port.read.side_effect = [
            b"",  # No initial response
            b"",  # Still no response after STX
        ]
        proto = RT97LProtocol(port)
        with pytest.raises(ProtocolError, match="did not ACK"):
            proto.enter_programming_mode()


class TestRead:
    def test_read_sends_correct_commands(self):
        port = make_mock_port()

        # Build mock responses: 8 blocks of W + addr + 32 data bytes, then ACK
        responses = []
        for block in range(READ_BLOCKS):
            addr = block * READ_BLOCK_SIZE
            resp = bytes([CMD_WRITE, 0, addr, READ_BLOCK_SIZE]) + bytes(
                range(READ_BLOCK_SIZE)
            )
            responses.append(resp)    # W response
            responses.append(bytes([ACK]))  # ACK after our ACK

        port.read.side_effect = responses
        proto = RT97LProtocol(port)
        data = proto.read_config()
        assert len(data) == CONFIG_SIZE

        # Verify read commands sent
        write_calls = port.write.call_args_list
        for block in range(READ_BLOCKS):
            addr = block * READ_BLOCK_SIZE
            expected_cmd = bytes([CMD_READ, 0, addr, READ_BLOCK_SIZE])
            assert write_calls[block * 2] == call(expected_cmd)
            assert write_calls[block * 2 + 1] == call(bytes([ACK]))

    def test_read_fails_on_bad_response(self):
        port = make_mock_port()
        # Return wrong command byte
        port.read.side_effect = [
            bytes([0x00] * 36),  # Bad response (not 'W')
        ]
        proto = RT97LProtocol(port)
        with pytest.raises(ProtocolError, match="expected 'W'"):
            proto.read_config()

    def test_read_fails_on_short_response(self):
        port = make_mock_port()
        port.read.side_effect = [
            bytes([CMD_WRITE, 0, 0, READ_BLOCK_SIZE]),  # Only header, no data
        ]
        proto = RT97LProtocol(port)
        with pytest.raises(ProtocolError, match="expected 36 bytes"):
            proto.read_config()


class TestWrite:
    def test_write_sends_correct_commands(self):
        port = make_mock_port()
        # Each write block gets ACK + ACK
        port.read.side_effect = [bytes([ACK])] * (WRITE_BLOCKS * 2)

        proto = RT97LProtocol(port)
        data = bytes(range(CONFIG_SIZE))
        proto.write_config(data)

        write_calls = port.write.call_args_list
        for block in range(WRITE_BLOCKS):
            addr = block * WRITE_BLOCK_SIZE
            expected_data = data[addr:addr + WRITE_BLOCK_SIZE]
            expected_cmd = (
                bytes([CMD_WRITE, 0, addr, WRITE_BLOCK_SIZE]) + expected_data
            )
            assert write_calls[block] == call(expected_cmd)

    def test_write_rejects_wrong_size(self):
        port = make_mock_port()
        proto = RT97LProtocol(port)
        with pytest.raises(ValueError, match="Expected 256"):
            proto.write_config(bytes(100))


class TestEnd:
    def test_exit_sends_end(self):
        port = make_mock_port()
        proto = RT97LProtocol(port)
        proto.exit_programming_mode()
        port.write.assert_called_once_with(bytes([CMD_END]))
