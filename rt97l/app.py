"""RT97L Repeater Programmer — Textual TUI Application."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header

from rt97l.data_model import RepeaterConfig
from rt97l.screens.channel_table import ChannelTableScreen


class RT97LApp(App):
    """Main application for RT97L/CX-525 repeater programming."""

    TITLE = "RT97L Repeater Programmer"
    SUB_TITLE = "v0.1.0"

    CSS = """
    Screen {
        background: $surface;
    }
    Input {
        border: solid $surface-lighten-2;
    }
    Input:focus {
        border: solid $accent;
    }
    Select > SelectCurrent {
        border: solid $surface-lighten-2;
    }
    Select:focus > SelectCurrent {
        border: solid $accent;
    }
    SelectOverlay {
        border: solid $accent;
    }
    Button {
        border: solid $surface-lighten-2;
        height: 3;
        min-width: 16;
    }
    Button:hover {
        border: solid $accent;
    }
    Button.-primary {
        border: solid $primary;
    }
    Button.-primary:hover {
        border: solid $primary-lighten-1;
    }
    * {
        scrollbar-size-vertical: 1;
    }
    ScrollBar {
        background: $surface-lighten-1;
    }
    ScrollBar > .scrollbar--bar {
        color: $accent-darken-1;
    }
    ScrollBar > .scrollbar--bar-hover {
        color: $accent;
    }
    ScrollBar > .scrollbar--bar-active {
        color: $accent-lighten-1;
    }
    """

    BINDINGS = [
        Binding("ctrl+q", "request_quit", "Quit", priority=True),
        Binding("ctrl+r", "read_device", "Read", priority=True),
        Binding("ctrl+w", "write_device", "Write", priority=True),
        Binding("ctrl+s", "save_file", "Save", priority=True),
        Binding("ctrl+o", "open_file", "Open", priority=True),
        Binding("ctrl+g", "edit_globals", "Settings", priority=True),
        Binding("ctrl+p", "select_port", "Port", priority=True),
    ]

    def __init__(self):
        super().__init__()
        self.config: RepeaterConfig = RepeaterConfig.default()
        self.current_file: Optional[Path] = None
        self.port_path: Optional[str] = None
        self.dirty: bool = False
        self.transfer_in_progress: bool = False

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()

    def on_mount(self) -> None:
        self.push_screen(ChannelTableScreen())

    def mark_dirty(self) -> None:
        self.dirty = True
        self._update_subtitle()

    def mark_clean(self) -> None:
        self.dirty = False
        self._update_subtitle()

    def _update_subtitle(self) -> None:
        parts = []
        if self.current_file:
            parts.append(self.current_file.name)
        if self.dirty:
            parts.append("[modified]")
        if self.port_path:
            parts.append(self.port_path)
        self.sub_title = " | ".join(parts) if parts else "v0.1.0"

    # -- Actions --

    def action_request_quit(self) -> None:
        if self.transfer_in_progress:
            self.notify("Cannot quit during transfer!", severity="warning")
            return
        if self.dirty:
            from rt97l.screens.com_port import ConfirmDialog
            self.push_screen(
                ConfirmDialog("Unsaved changes will be lost. Quit anyway?"),
                callback=self._on_quit_confirm,
            )
        else:
            self.exit()

    def _on_quit_confirm(self, confirmed: bool) -> None:
        if confirmed:
            self.exit()

    def action_read_device(self) -> None:
        if self.transfer_in_progress:
            return
        if self.dirty:
            from rt97l.screens.com_port import ConfirmDialog
            self.push_screen(
                ConfirmDialog("Unsaved changes will be lost. Read from device?"),
                callback=self._on_read_confirm,
            )
        else:
            self._do_read()

    def _on_read_confirm(self, confirmed: bool) -> None:
        if confirmed:
            self._do_read()

    def _do_read(self) -> None:
        from rt97l.screens.com_port import ReadWriteScreen
        self.push_screen(ReadWriteScreen(mode="read"), callback=self._on_transfer_done)
        self.transfer_in_progress = True

    def action_write_device(self) -> None:
        if self.transfer_in_progress:
            return
        from rt97l.screens.com_port import ReadWriteScreen
        self.push_screen(ReadWriteScreen(mode="write"), callback=self._on_transfer_done)
        self.transfer_in_progress = True

    def _on_transfer_done(self, result: bool | None) -> None:
        self.transfer_in_progress = False
        # Refresh channel table if it's the current screen
        screen = self.screen
        if hasattr(screen, "_refresh_table"):
            screen._refresh_table()
            screen._update_status()

    def action_save_file(self) -> None:
        from rt97l.screens.com_port import SaveDialog
        self.push_screen(SaveDialog())

    def action_open_file(self) -> None:
        if self.dirty:
            from rt97l.screens.com_port import ConfirmDialog
            self.push_screen(
                ConfirmDialog("Unsaved changes will be lost. Open a file?"),
                callback=self._on_open_confirm,
            )
        else:
            self._do_open()

    def _on_open_confirm(self, confirmed: bool) -> None:
        if confirmed:
            self._do_open()

    def _do_open(self) -> None:
        from rt97l.screens.com_port import OpenDialog
        self.push_screen(OpenDialog(), callback=self._on_open_done)

    def _on_open_done(self, result: bool | None) -> None:
        screen = self.screen
        if hasattr(screen, "_refresh_table"):
            screen._refresh_table()
            screen._update_status()

    def action_edit_globals(self) -> None:
        from rt97l.screens.global_settings import GlobalSettingsScreen
        self.push_screen(GlobalSettingsScreen())

    def action_select_port(self) -> None:
        from rt97l.screens.com_port import PortSelectScreen
        self.push_screen(PortSelectScreen(), callback=self._on_port_selected)

    def _on_port_selected(self, result: str | None) -> None:
        screen = self.screen
        if hasattr(screen, "_update_status"):
            screen._update_status()
