"""RT97L Repeater Programmer — Textual TUI Application."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Header

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
        Binding("ctrl+q", "request_quit", "Quit"),
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
