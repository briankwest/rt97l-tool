"""Channel table screen — main view showing all 16 channels."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import DataTable, Static


class ChannelTableScreen(Screen):
    """Main screen displaying the 16-channel configuration grid."""

    BINDINGS = [
        Binding("e", "edit_channel", "Edit Channel"),
        Binding("escape", "app.pop_screen", "Back", show=False),
    ]

    CSS = """
    ChannelTableScreen {
        layout: vertical;
    }
    #status-bar {
        dock: bottom;
        height: 1;
        background: $accent;
        color: $text;
        padding: 0 1;
    }
    DataTable {
        height: 1fr;
    }
    """

    def compose(self) -> ComposeResult:
        yield DataTable(id="channel-table")
        yield Static("", id="status-bar")

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.cursor_type = "row"
        table.zebra_stripes = True

        table.add_columns(
            "CH", "Rx Freq", "Tx Freq", "CT/DCS Enc", "CT/DCS Dec",
            "Mode", "Power", "Squelch", "Scan", "Lock", "Compand",
        )
        self._refresh_table()
        self._update_status()

    def _refresh_table(self) -> None:
        table = self.query_one(DataTable)
        table.clear()
        config = self.app.config

        for ch in config.channels:
            table.add_row(
                str(ch.channel_number),
                str(ch.rx_freq),
                str(ch.tx_freq),
                ch.tone_enc_display,
                ch.tone_dec_display,
                ch.channel_mode.value,
                ch.tx_power.value,
                ch.squelch_level.value,
                "Yes" if ch.scan_add else "No",
                "Yes" if ch.channel_lock else "No",
                ch.compand.value,
                key=str(ch.channel_number),
            )

    def _update_status(self) -> None:
        app = self.app
        parts = []
        if app.port_path:
            parts.append(f"Port: {app.port_path}")
        else:
            parts.append("No port selected")
        if app.current_file:
            parts.append(str(app.current_file.name))
        if app.dirty:
            parts.append("[modified]")
        parts.append("Enter/e:Edit  ^R:Read  ^W:Write  ^S:Save  ^O:Open  ^G:Settings  ^P:Port")
        self.query_one("#status-bar", Static).update(" | ".join(parts))

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle Enter/double-click on a row."""
        self._open_edit(event.cursor_row)

    def action_edit_channel(self) -> None:
        """Handle 'e' key to edit the selected channel."""
        table = self.query_one(DataTable)
        self._open_edit(table.cursor_row)

    def _open_edit(self, row_index: int) -> None:
        if row_index is not None and 0 <= row_index < len(self.app.config.channels):
            from rt97l.screens.channel_edit import ChannelEditScreen
            self.app.push_screen(
                ChannelEditScreen(row_index),
                callback=self._on_edit_done,
            )

    def _on_edit_done(self, result: bool | None) -> None:
        if result:
            self._refresh_table()
            self._update_status()
