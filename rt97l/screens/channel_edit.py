"""Channel edit screen — form for editing a single channel."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Select, Static

from rt97l.constants import (
    CTCSS_TONES,
    DCS_CODES_ALL,
    FREQ_MAX,
    FREQ_MIN,
    ChannelMode,
    Compand,
    SquelchLevel,
    TxPower,
)


def _tone_options() -> list[tuple[str, str]]:
    """Build list of (display, value) for tone selector."""
    opts: list[tuple[str, str]] = [("OFF", "OFF")]
    for t in CTCSS_TONES:
        opts.append((f"{t} Hz", t))
    for d in DCS_CODES_ALL:
        opts.append((d, d))
    return opts


TONE_OPTIONS = _tone_options()
POWER_OPTIONS = [(p.value, p.value) for p in TxPower]
SQUELCH_OPTIONS = [(s.value, s.value) for s in SquelchLevel]
MODE_OPTIONS = [(m.value, m.value) for m in ChannelMode]
COMPAND_OPTIONS = [(c.value, c.value) for c in Compand]
BOOL_OPTIONS = [("Yes", "Yes"), ("No", "No")]


class ChannelEditScreen(ModalScreen[bool]):
    """Modal form for editing one channel's settings."""

    BINDINGS = [
        Binding("ctrl+s", "save", "Save", priority=True),
        Binding("escape", "cancel", "Cancel"),
    ]

    CSS = """
    ChannelEditScreen {
        align: center middle;
    }
    #edit-container {
        width: 70;
        max-height: 90%;
        border: round $accent;
        background: $surface;
        padding: 1 3;
    }
    VerticalScroll {
        margin-right: 1;
    }
    #edit-title {
        text-align: center;
        text-style: bold;
        height: 1;
        margin-bottom: 1;
    }
    .field-row {
        height: 3;
    }
    .field-label {
        width: 16;
        padding-top: 1;
    }
    .field-input {
        width: 1fr;
    }
    #button-row {
        height: 3;
        align: center middle;
        margin-top: 1;
    }
    #button-row Button {
        margin: 0 2;
    }
    #error-msg {
        color: $error;
        height: 1;
        text-align: center;
    }
    """

    def __init__(self, channel_index: int):
        super().__init__()
        self.channel_index = channel_index

    @property
    def channel(self):
        return self.app.config.channels[self.channel_index]

    def compose(self) -> ComposeResult:
        ch = self.channel
        with Vertical(id="edit-container"):
            yield Static(f"Edit Channel {ch.channel_number}", id="edit-title")

            with VerticalScroll():
                with Horizontal(classes="field-row"):
                    yield Label("Rx Freq (MHz)", classes="field-label")
                    yield Input(str(ch.rx_freq), id="rx-freq", classes="field-input")
                with Horizontal(classes="field-row"):
                    yield Label("Tx Freq (MHz)", classes="field-label")
                    yield Input(str(ch.tx_freq), id="tx-freq", classes="field-input")
                with Horizontal(classes="field-row"):
                    yield Label("CT/DCS Enc", classes="field-label")
                    yield Select(TONE_OPTIONS, value=ch.ctcss_enc or "OFF", id="tone-enc", classes="field-input")
                with Horizontal(classes="field-row"):
                    yield Label("CT/DCS Dec", classes="field-label")
                    yield Select(TONE_OPTIONS, value=ch.ctcss_dec or "OFF", id="tone-dec", classes="field-input")
                with Horizontal(classes="field-row"):
                    yield Label("Tx Power", classes="field-label")
                    yield Select(POWER_OPTIONS, value=ch.tx_power.value, id="tx-power", classes="field-input")
                with Horizontal(classes="field-row"):
                    yield Label("Squelch", classes="field-label")
                    yield Select(SQUELCH_OPTIONS, value=ch.squelch_level.value, id="squelch", classes="field-input")
                with Horizontal(classes="field-row"):
                    yield Label("Mode", classes="field-label")
                    yield Select(MODE_OPTIONS, value=ch.channel_mode.value, id="mode", classes="field-input")
                with Horizontal(classes="field-row"):
                    yield Label("Compand", classes="field-label")
                    yield Select(COMPAND_OPTIONS, value=ch.compand.value, id="compand", classes="field-input")
                with Horizontal(classes="field-row"):
                    yield Label("Scan Add", classes="field-label")
                    yield Select(BOOL_OPTIONS, value="Yes" if ch.scan_add else "No", id="scan-add", classes="field-input")
                with Horizontal(classes="field-row"):
                    yield Label("Channel Lock", classes="field-label")
                    yield Select(BOOL_OPTIONS, value="Yes" if ch.channel_lock else "No", id="channel-lock", classes="field-input")

            yield Static("", id="error-msg")
            with Horizontal(id="button-row"):
                yield Button("Save", variant="primary", id="save-btn")
                yield Button("Cancel", variant="default", id="cancel-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save-btn":
            self._save()
        elif event.button.id == "cancel-btn":
            self.dismiss(False)

    def action_save(self) -> None:
        self._save()

    def action_cancel(self) -> None:
        self.dismiss(False)

    def _save(self) -> None:
        error_widget = self.query_one("#error-msg", Static)
        ch = self.channel

        # Validate frequencies
        try:
            rx = Decimal(self.query_one("#rx-freq", Input).value.strip())
        except InvalidOperation:
            error_widget.update("Invalid Rx frequency")
            return
        try:
            tx = Decimal(self.query_one("#tx-freq", Input).value.strip())
        except InvalidOperation:
            error_widget.update("Invalid Tx frequency")
            return

        if not (FREQ_MIN <= rx <= FREQ_MAX):
            error_widget.update(f"Rx freq out of range ({FREQ_MIN}-{FREQ_MAX})")
            return
        if not (FREQ_MIN <= tx <= FREQ_MAX):
            error_widget.update(f"Tx freq out of range ({FREQ_MIN}-{FREQ_MAX})")
            return

        # Read selects
        tone_enc = self.query_one("#tone-enc", Select).value
        tone_dec = self.query_one("#tone-dec", Select).value
        power = self.query_one("#tx-power", Select).value
        squelch = self.query_one("#squelch", Select).value
        mode = self.query_one("#mode", Select).value
        compand = self.query_one("#compand", Select).value
        scan = self.query_one("#scan-add", Select).value
        lock = self.query_one("#channel-lock", Select).value

        # Apply
        ch.rx_freq = rx
        ch.tx_freq = tx
        ch.ctcss_enc = None if tone_enc == "OFF" else tone_enc
        ch.ctcss_dec = None if tone_dec == "OFF" else tone_dec
        ch.tx_power = TxPower(power)
        ch.squelch_level = SquelchLevel(squelch)
        ch.channel_mode = ChannelMode(mode)
        ch.compand = Compand(compand)
        ch.scan_add = scan == "Yes"
        ch.channel_lock = lock == "Yes"

        self.app.mark_dirty()
        self.dismiss(True)
