"""Port selection, read/write progress, and file save/open dialogs."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, ProgressBar, Select, Static

from rt97l.file_io import load_json, load_txt, save_json, save_txt
from rt97l.serial_port import enumerate_ports

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Port Selection
# ---------------------------------------------------------------------------

class PortSelectScreen(ModalScreen[str | None]):
    """Dialog for selecting a serial port."""

    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    CSS = """
    PortSelectScreen { align: center middle; }
    #port-container {
        width: 55;
        height: auto;
        border: round $accent;
        background: $surface;
        padding: 1 3;
    }
    #port-title { text-align: center; text-style: bold; margin-bottom: 1; }
    .field-row { height: 3; }
    .field-label { width: 10; padding-top: 1; }
    .field-input { width: 1fr; }
    #button-row { height: 3; align: center middle; margin-top: 1; }
    #button-row Button { margin: 0 2; }
    """

    def compose(self) -> ComposeResult:
        ports = enumerate_ports()
        current = self.app.port_path or ""

        if not ports:
            port_options = [("(manual entry below)", "")]
        else:
            port_options = [(p, p) for p in ports]

        with Vertical(id="port-container"):
            yield Static("Select Serial Port", id="port-title")
            with Horizontal(classes="field-row"):
                yield Label("Port", classes="field-label")
                yield Select(
                    port_options,
                    value=current if current in [p[1] for p in port_options] else (port_options[0][1] if port_options else ""),
                    id="port-select",
                    classes="field-input",
                )
            with Horizontal(classes="field-row"):
                yield Label("Manual", classes="field-label")
                yield Input(current, placeholder="/dev/ttyUSB0", id="port-manual", classes="field-input")
            with Horizontal(id="button-row"):
                yield Button("OK", variant="primary", id="ok-btn")
                yield Button("Cancel", variant="default", id="cancel-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "ok-btn":
            manual = self.query_one("#port-manual", Input).value.strip()
            selected = self.query_one("#port-select", Select).value
            port = manual or selected
            if port:
                self.app.port_path = port
                self.app._update_subtitle()
            self.dismiss(port or None)
        else:
            self.dismiss(None)

    def action_cancel(self) -> None:
        self.dismiss(None)


# ---------------------------------------------------------------------------
# Read / Write Progress
# ---------------------------------------------------------------------------

class ReadWriteScreen(ModalScreen[bool]):
    """Dialog that performs a read or write with progress bar."""

    CSS = """
    ReadWriteScreen { align: center middle; }
    #rw-container {
        width: 55;
        height: auto;
        border: round $accent;
        background: $surface;
        padding: 1 3;
    }
    #rw-title { text-align: center; text-style: bold; margin-bottom: 1; }
    #rw-status { text-align: center; margin-bottom: 1; }
    .field-row { height: 3; }
    .field-label { width: 12; padding-top: 1; }
    .field-input { width: 1fr; }
    #button-row { height: 3; align: center middle; margin-top: 1; }
    #button-row Button { margin: 0 2; }
    ProgressBar { margin: 0 1; }
    """

    def __init__(self, mode: str = "read"):
        super().__init__()
        self.mode = mode
        self._busy = False

    def compose(self) -> ComposeResult:
        title = "Read from Repeater" if self.mode == "read" else "Write to Repeater"
        with Vertical(id="rw-container"):
            yield Static(title, id="rw-title")
            with Horizontal(classes="field-row"):
                yield Label("Password", classes="field-label")
                yield Input(
                    "288288",
                    placeholder="6-digit password (default: 288288)",
                    password=True,
                    id="password",
                    classes="field-input",
                )
            yield Static("", id="rw-status")
            yield ProgressBar(total=100, id="rw-progress")
            with Horizontal(id="button-row"):
                yield Button("Start", variant="primary", id="start-btn")
                yield Button("Cancel", variant="default", id="cancel-btn")

    async def on_mount(self) -> None:
        if not self.app.port_path:
            self.query_one("#rw-status", Static).update(
                "No port selected! Use Ctrl+P first."
            )
            self.query_one("#start-btn", Button).disabled = True

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "start-btn" and not self._busy:
            asyncio.ensure_future(self._run())
        elif event.button.id == "cancel-btn":
            if not self._busy:
                self.dismiss(False)

    def check_action(self, action: str, parameters: tuple) -> bool:
        """Block escape/cancel while busy."""
        if action == "cancel" and self._busy:
            return False
        return True

    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def action_cancel(self) -> None:
        if not self._busy:
            self.dismiss(False)

    async def _run(self) -> None:
        self._busy = True
        # Disable buttons during transfer
        self.query_one("#start-btn", Button).disabled = True
        self.query_one("#cancel-btn", Button).disabled = True
        self.query_one("#password", Input).disabled = True

        status = self.query_one("#rw-status", Static)
        progress = self.query_one("#rw-progress", ProgressBar)
        password = self.query_one("#password", Input).value.strip()

        try:
            from rt97l.memory_map import decode_config, encode_config
            from rt97l.protocol import RT97LProtocol
            from rt97l.serial_port import SerialPort

            status.update("Connecting...")
            port = SerialPort(self.app.port_path, debug_log=True)
            port.open()

            try:
                proto = RT97LProtocol(port)
                status.update("Handshaking...")
                progress.update(progress=10)
                device_id = await asyncio.to_thread(proto.enter_programming_mode)
                status.update(f"Connected (ID: {device_id.hex()})")
                progress.update(progress=20)

                if self.mode == "read":
                    status.update("Reading configuration...")
                    raw = await asyncio.to_thread(proto.read_config)
                    progress.update(progress=80)

                    status.update("Decoding...")
                    config = decode_config(raw)
                    config.password = password
                    self.app.config = config
                    self.app.mark_dirty()
                    progress.update(progress=100)
                    status.update("Read complete!")

                else:  # write
                    self.app.config.password = password
                    status.update("Encoding configuration...")
                    raw = encode_config(self.app.config)
                    progress.update(progress=30)

                    status.update("Writing configuration...")
                    await asyncio.to_thread(proto.write_config, raw)
                    progress.update(progress=90)
                    status.update("Write complete!")
                    progress.update(progress=100)

                await asyncio.to_thread(proto.exit_programming_mode)

            finally:
                port.close()

            status.update(
                f"{'Read' if self.mode == 'read' else 'Write'} complete!"
            )
            await asyncio.sleep(1.5)
            self._busy = False
            self.dismiss(True)

        except Exception as e:
            status.update(f"Error: {e}")
            log.exception("Read/Write failed")
            self._busy = False
            self.query_one("#cancel-btn", Button).disabled = False


# ---------------------------------------------------------------------------
# Unsaved Changes Confirmation
# ---------------------------------------------------------------------------

class ConfirmDialog(ModalScreen[bool]):
    """Simple yes/no confirmation dialog."""

    CSS = """
    ConfirmDialog { align: center middle; }
    #confirm-container {
        width: 50;
        height: auto;
        border: round $accent;
        background: $surface;
        padding: 1 3;
    }
    #confirm-msg { text-align: center; margin-bottom: 1; }
    #button-row { height: 3; align: center middle; }
    #button-row Button { margin: 0 2; }
    """

    def __init__(self, message: str):
        super().__init__()
        self._message = message

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-container"):
            yield Static(self._message, id="confirm-msg")
            with Horizontal(id="button-row"):
                yield Button("Yes", variant="primary", id="yes-btn")
                yield Button("No", variant="default", id="no-btn")

    BINDINGS = [Binding("escape", "no", "No")]

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "yes-btn")

    def action_no(self) -> None:
        self.dismiss(False)


# ---------------------------------------------------------------------------
# File Save / Open
# ---------------------------------------------------------------------------

class SaveDialog(ModalScreen[bool]):
    """Dialog for saving configuration to a file."""

    BINDINGS = [
        Binding("ctrl+s", "do_save", "Save", priority=True),
        Binding("escape", "cancel", "Cancel"),
    ]

    CSS = """
    SaveDialog { align: center middle; }
    #save-container {
        width: 60;
        height: auto;
        border: round $accent;
        background: $surface;
        padding: 1 3;
    }
    #save-title { text-align: center; text-style: bold; margin-bottom: 1; }
    .field-row { height: 3; }
    .field-label { width: 10; padding-top: 1; }
    .field-input { width: 1fr; }
    #status-msg { text-align: center; height: 1; }
    #button-row { height: 3; align: center middle; margin-top: 1; }
    #button-row Button { margin: 0 2; }
    """

    def compose(self) -> ComposeResult:
        default = str(self.app.current_file) if self.app.current_file else "config.json"
        with Vertical(id="save-container"):
            yield Static("Save Configuration", id="save-title")
            with Horizontal(classes="field-row"):
                yield Label("File", classes="field-label")
                yield Input(default, placeholder="config.json", id="file-path", classes="field-input")
            yield Static("Formats: .json (native), .txt (Windows compat)", id="status-msg")
            with Horizontal(id="button-row"):
                yield Button("Save", variant="primary", id="save-btn")
                yield Button("Cancel", variant="default", id="cancel-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save-btn":
            self._save()
        else:
            self.dismiss(False)

    def action_do_save(self) -> None:
        self._save()

    def action_cancel(self) -> None:
        self.dismiss(False)

    def _save(self) -> None:
        path = Path(self.query_one("#file-path", Input).value.strip())
        status = self.query_one("#status-msg", Static)
        try:
            if path.suffix == ".txt":
                save_txt(self.app.config, path)
            else:
                if path.suffix != ".json":
                    path = path.with_suffix(".json")
                save_json(self.app.config, path)
            self.app.current_file = path
            self.app.mark_clean()
            self.dismiss(True)
        except Exception as e:
            status.update(f"Error: {e}")


class OpenDialog(ModalScreen[bool]):
    """Dialog for opening a configuration file."""

    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    CSS = """
    OpenDialog { align: center middle; }
    #open-container {
        width: 60;
        height: auto;
        border: round $accent;
        background: $surface;
        padding: 1 3;
    }
    #open-title { text-align: center; text-style: bold; margin-bottom: 1; }
    .field-row { height: 3; }
    .field-label { width: 10; padding-top: 1; }
    .field-input { width: 1fr; }
    #status-msg { text-align: center; height: 1; color: $error; }
    #button-row { height: 3; align: center middle; margin-top: 1; }
    #button-row Button { margin: 0 2; }
    """

    def compose(self) -> ComposeResult:
        default = str(self.app.current_file) if self.app.current_file else ""
        with Vertical(id="open-container"):
            yield Static("Open Configuration", id="open-title")
            with Horizontal(classes="field-row"):
                yield Label("File", classes="field-label")
                yield Input(default, placeholder="config.json", id="file-path", classes="field-input")
            yield Static("", id="status-msg")
            with Horizontal(id="button-row"):
                yield Button("Open", variant="primary", id="open-btn")
                yield Button("Cancel", variant="default", id="cancel-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "open-btn":
            self._open()
        else:
            self.dismiss(False)

    def action_cancel(self) -> None:
        self.dismiss(False)

    def _open(self) -> None:
        path = Path(self.query_one("#file-path", Input).value.strip())
        status = self.query_one("#status-msg", Static)
        try:
            if not path.exists():
                status.update(f"File not found: {path}")
                return
            if path.suffix == ".txt":
                config = load_txt(path)
            else:
                config = load_json(path)
            config.validate()
            self.app.config = config
            self.app.current_file = path
            self.app.mark_clean()
            self.dismiss(True)
        except Exception as e:
            status.update(f"Error: {e}")
