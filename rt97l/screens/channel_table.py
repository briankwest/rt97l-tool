"""Channel table screen — main view showing all 16 channels."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header


class ChannelTableScreen(Screen):
    """Main screen displaying the 16-channel configuration grid."""

    BINDINGS = [
        Binding("e", "edit_channel", "Edit"),
        Binding("enter", "edit_channel", "Edit", show=False),
        Binding("ctrl+r", "read_device", "Read"),
        Binding("ctrl+w", "write_device", "Write"),
        Binding("ctrl+s", "save_file", "Save"),
        Binding("ctrl+o", "open_file", "Open"),
        Binding("ctrl+g", "edit_globals", "Settings"),
        Binding("ctrl+t", "select_port", "Port"),
    ]

    CSS = """
    ChannelTableScreen {
        layout: vertical;
    }
    DataTable {
        height: 1fr;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        yield DataTable(id="channel-table")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.cursor_type = "row"
        table.zebra_stripes = True

        table.add_columns(
            "CH", "Rx Freq", "Tx Freq", "CT/DCS Enc", "CT/DCS Dec",
            "Mode", "Power", "Squelch", "Scan", "Lock", "Compand",
        )
        self._refresh_table()
        self.app._update_subtitle()

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

    # -- Channel editing --

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        self._open_edit(event.cursor_row)

    def action_edit_channel(self) -> None:
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
            self.app._update_subtitle()

    # -- Read / Write (auto-redirect to port if needed) --

    def action_read_device(self) -> None:
        if self.app.transfer_in_progress:
            return
        if not self.app.port_path:
            self._select_port_then(self._start_read)
            return
        if self.app.dirty:
            from rt97l.screens.com_port import ConfirmDialog
            self.app.push_screen(
                ConfirmDialog("Unsaved changes will be lost. Read from device?"),
                callback=lambda ok: self._start_read() if ok else None,
            )
        else:
            self._start_read()

    def _start_read(self) -> None:
        from rt97l.screens.com_port import ReadWriteScreen
        self.app.transfer_in_progress = True
        self.app.push_screen(
            ReadWriteScreen(mode="read"), callback=self._on_transfer_done
        )

    def action_write_device(self) -> None:
        if self.app.transfer_in_progress:
            return
        if not self.app.port_path:
            self._select_port_then(self._start_write)
            return
        self._start_write()

    def _start_write(self) -> None:
        from rt97l.screens.com_port import ReadWriteScreen
        self.app.transfer_in_progress = True
        self.app.push_screen(
            ReadWriteScreen(mode="write"), callback=self._on_transfer_done
        )

    def _on_transfer_done(self, result: bool | None) -> None:
        self.app.transfer_in_progress = False
        self._refresh_table()
        self.app._update_subtitle()

    def _select_port_then(self, callback) -> None:
        """Open port selection, then call callback if a port was chosen."""
        from rt97l.screens.com_port import PortSelectScreen

        def on_port(result):
            self.app._update_subtitle()
            if self.app.port_path:
                callback()

        self.app.push_screen(PortSelectScreen(), callback=on_port)

    # -- File operations --

    def action_save_file(self) -> None:
        from rt97l.screens.com_port import SaveDialog
        self.app.push_screen(SaveDialog(), callback=self._on_file_done)

    def action_open_file(self) -> None:
        if self.app.dirty:
            from rt97l.screens.com_port import ConfirmDialog
            self.app.push_screen(
                ConfirmDialog("Unsaved changes will be lost. Open a file?"),
                callback=lambda ok: self._do_open() if ok else None,
            )
        else:
            self._do_open()

    def _do_open(self) -> None:
        from rt97l.screens.com_port import OpenDialog
        self.app.push_screen(OpenDialog(), callback=self._on_file_done)

    def _on_file_done(self, result: bool | None) -> None:
        self._refresh_table()
        self.app._update_subtitle()

    # -- Settings / Port --

    def action_edit_globals(self) -> None:
        from rt97l.screens.global_settings import GlobalSettingsScreen
        self.app.push_screen(GlobalSettingsScreen(), callback=self._on_file_done)

    def action_select_port(self) -> None:
        from rt97l.screens.com_port import PortSelectScreen
        self.app.push_screen(PortSelectScreen(), callback=lambda r: self.app._update_subtitle())
