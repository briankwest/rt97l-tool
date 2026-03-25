"""Global settings screen — editor for non-per-channel settings."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Select, Static

from rt97l.constants import (
    MIC_GAIN_MAX,
    MIC_GAIN_MIN,
    RELAY_DELAY_OPTIONS,
    TIMEOUT_OPTIONS,
    VOX_DELAY_OPTIONS,
    VOX_LEVEL_MAX,
    VOX_LEVEL_MIN,
    VOLUME_MAX,
    VOLUME_MIN,
    Language,
    ModelType,
)

ONOFF = [("ON", "ON"), ("OFF", "OFF")]
LANG_OPTIONS = [(l.value, l.value) for l in Language]
MODEL_OPTIONS = [(m.value, m.value) for m in ModelType]
MIC_GAIN_OPTIONS = [(str(g), str(g)) for g in range(MIC_GAIN_MIN, MIC_GAIN_MAX + 1)]
VOLUME_OPTIONS = [(str(v), str(v)) for v in range(VOLUME_MIN, VOLUME_MAX + 1)]
VOX_LEVEL_OPTIONS = [(str(v), str(v)) for v in range(VOX_LEVEL_MIN, VOX_LEVEL_MAX + 1)]
VOX_DELAY_OPT = [(f"{d:.1f}", str(d)) for d in VOX_DELAY_OPTIONS]
RELAY_DELAY_OPT = [(f"{d:.1f}", str(d)) for d in RELAY_DELAY_OPTIONS]
TIMEOUT_OPT = [("OFF", "0")] + [(f"{t}s", str(t)) for t in TIMEOUT_OPTIONS if t > 0]
BAND_OPTIONS = [("1", "1"), ("2", "2")]


class GlobalSettingsScreen(ModalScreen[bool]):
    """Modal form for editing global repeater settings."""

    BINDINGS = [
        Binding("ctrl+s", "save", "Save", priority=True),
        Binding("escape", "cancel", "Cancel"),
    ]

    CSS = """
    GlobalSettingsScreen {
        align: center middle;
    }
    #settings-container {
        width: 65;
        max-height: 40;
        border: round $accent;
        background: $surface;
        padding: 1 3;
    }
    VerticalScroll {
        margin-right: 1;
    }
    #settings-title {
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
    }
    .section-header {
        text-style: bold;
        color: $accent;
        margin-top: 1;
    }
    .field-row {
        height: 3;
    }
    .field-label {
        width: 20;
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
    """

    def compose(self) -> ComposeResult:
        g = self.app.config.globals
        with Vertical(id="settings-container"):
            yield Static("Global Settings", id="settings-title")
            with VerticalScroll():
                # -- System --
                yield Static("System", classes="section-header")
                with Horizontal(classes="field-row"):
                    yield Label("Model Type", classes="field-label")
                    yield Select(MODEL_OPTIONS, value=g.model_type.value, id="model-type", classes="field-input")
                with Horizontal(classes="field-row"):
                    yield Label("Frequency Band", classes="field-label")
                    yield Select(BAND_OPTIONS, value=str(g.frequency_band), id="freq-band", classes="field-input")
                with Horizontal(classes="field-row"):
                    yield Label("Language", classes="field-label")
                    yield Select(LANG_OPTIONS, value=g.language.value, id="language", classes="field-input")

                # -- Audio --
                yield Static("Audio", classes="section-header")
                with Horizontal(classes="field-row"):
                    yield Label("Audio Output", classes="field-label")
                    yield Select(ONOFF, value="ON" if g.audio_output else "OFF", id="audio-output", classes="field-input")
                with Horizontal(classes="field-row"):
                    yield Label("Volume", classes="field-label")
                    yield Select(VOLUME_OPTIONS, value=str(g.volume), id="volume", classes="field-input")
                with Horizontal(classes="field-row"):
                    yield Label("Beep", classes="field-label")
                    yield Select(ONOFF, value="ON" if g.beep else "OFF", id="beep", classes="field-input")
                with Horizontal(classes="field-row"):
                    yield Label("Voice Prompts", classes="field-label")
                    yield Select(ONOFF, value="ON" if g.voice_prompts else "OFF", id="voice-prompts", classes="field-input")
                with Horizontal(classes="field-row"):
                    yield Label("Mic Gain", classes="field-label")
                    yield Select(MIC_GAIN_OPTIONS, value=str(g.mic_gain), id="mic-gain", classes="field-input")

                # -- VOX --
                yield Static("VOX", classes="section-header")
                with Horizontal(classes="field-row"):
                    yield Label("VOX Set", classes="field-label")
                    yield Select(ONOFF, value="ON" if g.vox_set else "OFF", id="vox-set", classes="field-input")
                with Horizontal(classes="field-row"):
                    yield Label("VOX Function", classes="field-label")
                    yield Select(ONOFF, value="ON" if g.vox_function else "OFF", id="vox-function", classes="field-input")
                with Horizontal(classes="field-row"):
                    yield Label("VOX Level", classes="field-label")
                    yield Select(VOX_LEVEL_OPTIONS, value=str(g.vox_level), id="vox-level", classes="field-input")
                with Horizontal(classes="field-row"):
                    yield Label("VOX Delay (sec)", classes="field-label")
                    yield Select(VOX_DELAY_OPT, value=str(g.vox_delay), id="vox-delay", classes="field-input")

                # -- Relay --
                yield Static("Relay", classes="section-header")
                with Horizontal(classes="field-row"):
                    yield Label("Relay", classes="field-label")
                    yield Select(ONOFF, value="ON" if g.relay else "OFF", id="relay", classes="field-input")
                with Horizontal(classes="field-row"):
                    yield Label("Relay Delay (sec)", classes="field-label")
                    yield Select(RELAY_DELAY_OPT, value=str(g.relay_delay), id="relay-delay", classes="field-input")

                # -- Radio --
                yield Static("Radio", classes="section-header")
                with Horizontal(classes="field-row"):
                    yield Label("STE", classes="field-label")
                    yield Select(ONOFF, value="ON" if g.squelch_tail_elim else "OFF", id="ste", classes="field-input")
                with Horizontal(classes="field-row"):
                    yield Label("Timeout (sec)", classes="field-label")
                    yield Select(TIMEOUT_OPT, value=str(g.timeout_sec), id="timeout", classes="field-input")
                with Horizontal(classes="field-row"):
                    yield Label("Battery Save", classes="field-label")
                    yield Select(ONOFF, value="ON" if g.battery_save else "OFF", id="battery-save", classes="field-input")
                with Horizontal(classes="field-row"):
                    yield Label("Backlight", classes="field-label")
                    yield Select(ONOFF, value="ON" if g.backlight else "OFF", id="backlight", classes="field-input")
                with Horizontal(classes="field-row"):
                    yield Label("Low Temperature", classes="field-label")
                    yield Select(ONOFF, value="ON" if g.low_temperature else "OFF", id="low-temp", classes="field-input")

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
        g = self.app.config.globals
        # System
        g.model_type = ModelType(self.query_one("#model-type", Select).value)
        g.frequency_band = int(self.query_one("#freq-band", Select).value)
        g.language = Language(self.query_one("#language", Select).value)
        # Audio
        g.audio_output = self.query_one("#audio-output", Select).value == "ON"
        g.volume = int(self.query_one("#volume", Select).value)
        g.beep = self.query_one("#beep", Select).value == "ON"
        g.voice_prompts = self.query_one("#voice-prompts", Select).value == "ON"
        g.mic_gain = int(self.query_one("#mic-gain", Select).value)
        # VOX
        g.vox_set = self.query_one("#vox-set", Select).value == "ON"
        g.vox_function = self.query_one("#vox-function", Select).value == "ON"
        g.vox_level = int(self.query_one("#vox-level", Select).value)
        g.vox_delay = float(self.query_one("#vox-delay", Select).value)
        # Relay
        g.relay = self.query_one("#relay", Select).value == "ON"
        g.relay_delay = float(self.query_one("#relay-delay", Select).value)
        # Radio
        g.squelch_tail_elim = self.query_one("#ste", Select).value == "ON"
        g.timeout_sec = int(self.query_one("#timeout", Select).value)
        g.battery_save = self.query_one("#battery-save", Select).value == "ON"
        g.backlight = self.query_one("#backlight", Select).value == "ON"
        g.low_temperature = self.query_one("#low-temp", Select).value == "ON"

        self.app.mark_dirty()
        self.dismiss(True)
