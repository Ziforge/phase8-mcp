"""phase8-mcp — MCP server for the Korg Phase 8 acoustic synthesizer.

MIDI implementation matches the phase 8 owner's manual v1.00 (2025-11-20):
  * Notes 36-43 (C2..G2) trigger the 8 resonators
  * CC 12-19 = per-resonator Velocity (1..8)
  * CC 20-27 = per-resonator Envelope (1..8)
  * CC 28 Mod Depth, 29 Mod Rate, 30 Air, 31 Tempo, 90 Shift, 92 Mod Type
  * CC 120 All Sound Off, 121 Reset All Controllers
  * Program Change 0-7 for the 8 patches
  * SysEx: Korg exclusive + Inquiry supported

Requires: mcp[cli], python-rtmidi.
"""

from __future__ import annotations

import time
from contextlib import asynccontextmanager
from typing import AsyncIterator

import rtmidi
from mcp.server.fastmcp import Context, FastMCP


# ---- Constants — mapped directly from the phase 8 manual chart ----------

# Note numbers, one per resonator (1 = leftmost, 8 = rightmost).
RESONATOR_NOTES = {
    1: 36,  # C2
    2: 37,  # C#2
    3: 38,  # D2
    4: 39,  # Eb2
    5: 40,  # E2
    6: 41,  # F2
    7: 42,  # F#2
    8: 43,  # G2
}

# CC map from section 12.0 of the manual.
CC_VELOCITY_BASE = 12   # CC 12..19  per-resonator velocity 1..8
CC_ENVELOPE_BASE = 20   # CC 20..27  per-resonator envelope 1..8
CC_MOD_DEPTH     = 28
CC_MOD_RATE      = 29
CC_AIR_SLIDER    = 30
CC_TEMPO         = 31
CC_SHIFT         = 90
CC_MOD_TYPE      = 92
CC_ALL_SOUND_OFF = 120
CC_RESET_ALL     = 121

MOD_TYPE_VALUES = {   # from Global Parameter Table
    "pitch_env": 0,
    "vibrato":   1,
}


class Phase8Engine:
    def __init__(self, port_pattern: str = "phase8", channel: int = 1):
        self.port_pattern = port_pattern
        self.channel = max(1, min(16, channel)) - 1   # 0-based on the wire
        self.midi_out: rtmidi.MidiOut | None = None
        self.connected = False

    def list_ports(self) -> list[str]:
        return rtmidi.MidiOut().get_ports()

    def connect(self, pattern: str | None = None, channel: int | None = None) -> str:
        if pattern:
            self.port_pattern = pattern
        if channel is not None:
            self.channel = max(1, min(16, channel)) - 1
        self.midi_out = rtmidi.MidiOut()
        ports = self.midi_out.get_ports()
        idx = next(
            (i for i, n in enumerate(ports) if self.port_pattern.lower() in n.lower()),
            None,
        )
        if idx is None:
            raise ValueError(
                f"No MIDI OUT port matching '{self.port_pattern}'. Available: {ports}"
            )
        self.midi_out.open_port(idx)
        self.connected = True
        return f"connected to '{ports[idx]}' on channel {self.channel + 1}"

    def disconnect(self):
        if self.midi_out is not None:
            try:
                self.midi_out.close_port()
            except Exception:
                pass
        self.connected = False

    def _require(self):
        if not self.connected:
            raise RuntimeError("Not connected. Call connect_phase8 first.")
        assert self.midi_out is not None
        return self.midi_out

    def note_on(self, note: int, velocity: int = 100):
        self._require().send_message([0x90 | self.channel, note & 0x7F, velocity & 0x7F])

    def note_off(self, note: int):
        self._require().send_message([0x80 | self.channel, note & 0x7F, 0])

    def cc(self, controller: int, value: int):
        self._require().send_message([0xB0 | self.channel, controller & 0x7F, value & 0x7F])

    def program_change(self, program: int):
        self._require().send_message([0xC0 | self.channel, program & 0x7F])

    def send_sysex(self, data: list[int]):
        self._require().send_message([0xF0] + list(data) + [0xF7])


# ---- MCP server --------------------------------------------------------


@asynccontextmanager
async def lifespan(_server: FastMCP) -> AsyncIterator[dict]:
    engine = Phase8Engine()
    try:
        engine.connect()
        print(f"[phase8-mcp] auto-connected on '{engine.port_pattern}'")
    except Exception as e:
        print(f"[phase8-mcp] auto-connect skipped: {e}")
    yield {"engine": engine}
    engine.disconnect()


mcp = FastMCP(
    "phase8",
    instructions=(
        "Control a Korg Phase 8 acoustic synthesizer over MIDI. Provides "
        "resonator note triggers, per-resonator velocity/envelope, mod depth/"
        "rate, air slider, tempo, shift, mod type, program change, and Korg "
        "SysEx passthrough."
    ),
    lifespan=lifespan,
)


def _eng(ctx: Context) -> Phase8Engine:
    return ctx.request_context.lifespan_context["engine"]


# ---- Connection -----------------------------------------------------


@mcp.tool()
async def list_midi_ports(ctx: Context) -> str:
    """List MIDI OUT ports on the host."""
    return str(_eng(ctx).list_ports())


@mcp.tool()
async def connect_phase8(ctx: Context, port_pattern: str = "phase8", channel: int = 1) -> str:
    """Connect to the Phase 8. `port_pattern` is a case-insensitive substring
    for the MIDI port name. `channel` is 1..16."""
    return _eng(ctx).connect(port_pattern, channel)


@mcp.tool()
async def disconnect_phase8(ctx: Context) -> str:
    """Close the MIDI port."""
    _eng(ctx).disconnect()
    return "disconnected"


@mcp.tool()
async def set_channel(ctx: Context, channel: int) -> str:
    """Change the MIDI channel used for future messages. 1..16."""
    eng = _eng(ctx)
    eng.channel = max(1, min(16, channel)) - 1
    return f"channel now {eng.channel + 1}"


# ---- Resonator triggers ----------------------------------------------


@mcp.tool()
async def trigger_resonator(
    ctx: Context, resonator: int, velocity: int = 100, duration_ms: int = 0
) -> str:
    """Fire a note that plays resonator N (1..8, left..right). If duration_ms
    is 0 the note is left hanging until release_resonator or all_sound_off.
    """
    r = max(1, min(8, int(resonator)))
    note = RESONATOR_NOTES[r]
    _eng(ctx).note_on(note, velocity)
    if duration_ms > 0:
        # Simple synchronous hold — MCP tools are async but the underlying
        # rtmidi call is instantaneous so this is fine.
        import asyncio
        await asyncio.sleep(duration_ms / 1000.0)
        _eng(ctx).note_off(note)
    return f"resonator {r} triggered (note {note}, vel {velocity})"


@mcp.tool()
async def release_resonator(ctx: Context, resonator: int) -> str:
    """Send Note Off to the specified resonator."""
    r = max(1, min(8, int(resonator)))
    _eng(ctx).note_off(RESONATOR_NOTES[r])
    return f"resonator {r} released"


@mcp.tool()
async def strum(
    ctx: Context, from_res: int = 1, to_res: int = 8,
    velocity: int = 100, step_ms: int = 30
) -> str:
    """Strum across a range of resonators, one after another."""
    import asyncio
    direction = 1 if to_res >= from_res else -1
    triggered = []
    for r in range(from_res, to_res + direction, direction):
        r = max(1, min(8, r))
        _eng(ctx).note_on(RESONATOR_NOTES[r], velocity)
        triggered.append(r)
        await asyncio.sleep(step_ms / 1000.0)
    # Leave notes ringing so the user hears the strum tail.
    return f"strummed resonators {triggered}"


# ---- Per-resonator parameter CCs -------------------------------------


@mcp.tool()
async def set_velocity_knob(ctx: Context, resonator: int, value: int) -> str:
    """CC 12..19: per-resonator Velocity knob (0..127)."""
    r = max(1, min(8, int(resonator)))
    _eng(ctx).cc(CC_VELOCITY_BASE + (r - 1), value)
    return f"resonator {r} velocity knob = {value}"


@mcp.tool()
async def set_envelope_knob(ctx: Context, resonator: int, value: int) -> str:
    """CC 20..27: per-resonator Envelope knob (0..127)."""
    r = max(1, min(8, int(resonator)))
    _eng(ctx).cc(CC_ENVELOPE_BASE + (r - 1), value)
    return f"resonator {r} envelope knob = {value}"


# ---- Global CCs -----------------------------------------------------


@mcp.tool()
async def set_mod_depth(ctx: Context, value: int) -> str:
    """CC 28: modulation depth (0..127)."""
    _eng(ctx).cc(CC_MOD_DEPTH, value)
    return f"mod depth = {value}"


@mcp.tool()
async def set_mod_rate(ctx: Context, value: int) -> str:
    """CC 29: modulation rate (0..127)."""
    _eng(ctx).cc(CC_MOD_RATE, value)
    return f"mod rate = {value}"


@mcp.tool()
async def set_air(ctx: Context, value: int) -> str:
    """CC 30: Air slider (0..127)."""
    _eng(ctx).cc(CC_AIR_SLIDER, value)
    return f"air = {value}"


@mcp.tool()
async def set_tempo(ctx: Context, value: int) -> str:
    """CC 31: internal tempo control (0..127)."""
    _eng(ctx).cc(CC_TEMPO, value)
    return f"tempo cc = {value}"


@mcp.tool()
async def set_shift(ctx: Context, value: int) -> str:
    """CC 90: Shift (0..127)."""
    _eng(ctx).cc(CC_SHIFT, value)
    return f"shift = {value}"


@mcp.tool()
async def set_mod_type(ctx: Context, mod_type: str = "vibrato") -> str:
    """CC 92: Mod Type. Options: 'pitch_env' (0), 'vibrato' (1)."""
    v = MOD_TYPE_VALUES.get(mod_type, MOD_TYPE_VALUES["vibrato"])
    _eng(ctx).cc(CC_MOD_TYPE, v)
    return f"mod type = {mod_type} ({v})"


@mcp.tool()
async def all_sound_off(ctx: Context) -> str:
    """CC 120: silence all resonators immediately."""
    _eng(ctx).cc(CC_ALL_SOUND_OFF, 0)
    return "all sound off"


@mcp.tool()
async def reset_all_controllers(ctx: Context) -> str:
    """CC 121: reset all controllers."""
    _eng(ctx).cc(CC_RESET_ALL, 0)
    return "reset all controllers"


@mcp.tool()
async def program_change(ctx: Context, program: int) -> str:
    """Send Program Change 0..7 to select one of the 8 patches."""
    p = max(0, min(7, int(program)))
    _eng(ctx).program_change(p)
    return f"program change {p}"


# ---- SysEx passthrough -----------------------------------------------


@mcp.tool()
async def send_raw_sysex(ctx: Context, hex_bytes: str) -> str:
    """Send a raw SysEx message. Provide the bytes as a hex string (no
    F0/F7 — those are added automatically). Example: '42 30 00 08' fires
    a Korg universal query."""
    data = [int(b, 16) for b in hex_bytes.split()]
    _eng(ctx).send_sysex(data)
    return f"sent {len(data)}-byte SysEx"


@mcp.tool()
async def send_cc(ctx: Context, controller: int, value: int) -> str:
    """Send any raw MIDI CC. Escape hatch for CCs not in the typed helpers."""
    _eng(ctx).cc(controller, value)
    return f"CC {controller} = {value}"


def main():
    mcp.run()


if __name__ == "__main__":
    main()
