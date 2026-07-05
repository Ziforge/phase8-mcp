# phase8-mcp

MCP server for the **Korg Phase 8** acoustic synthesizer. Wraps the MIDI
implementation documented in the phase 8 owner's manual v1.00
(2025-11-20) so a Model Context Protocol client (Claude Code, Cursor,
Continue, etc.) can trigger resonators, drive per-resonator knobs, and
modulate globals over USB MIDI.

Written by Ziforge as part of the `superclean-collaboration` livecoding
rig at EMS Stockholm. Companion to the other Ziforge MCPs for
Eurorack + hardware synths — see [Related MCPs](#related-mcps) below.

## MIDI implementation covered

Direct from section 12.0 (MIDI Implementation Chart) of the phase 8
owner's manual:

| Feature | MIDI | Notes |
|---|---|---|
| 8 resonator triggers | Notes 36-43 (C2..G2) | one note per resonator, left→right |
| Per-resonator Velocity knob | CC 12-19 | resonator 1..8 |
| Per-resonator Envelope knob | CC 20-27 | resonator 1..8 |
| Mod Depth | CC 28 | 0..127 |
| Mod Rate | CC 29 | 0..127 |
| Air slider | CC 30 | 0..127 |
| Tempo (Internal) | CC 31 | 0..127 |
| Shift | CC 90 | 0..127 |
| Mod Type | CC 92 | 0 = Pitch Env, 1 = Vibrato |
| All Sound Off | CC 120 | silence all |
| Reset All Controllers | CC 121 | reset all CCs |
| Program Change | 0-7 | one of the 8 patches |
| SysEx | Korg exclusive + Inquiry | via `send_raw_sysex` |

Not implemented (Phase 8 doesn't respond to them):

- Aftertouch (Key's or Channel)
- Pitch Bend

## Tools

| Category | Tools |
|---|---|
| Connection | `list_midi_ports`, `connect_phase8(port_pattern, channel)`, `disconnect_phase8`, `set_channel(channel)` |
| Notes | `trigger_resonator(resonator, velocity, duration_ms)`, `release_resonator(resonator)`, `strum(from_res, to_res, velocity, step_ms)` |
| Per-resonator CCs | `set_velocity_knob(resonator, value)`, `set_envelope_knob(resonator, value)` |
| Global CCs | `set_mod_depth`, `set_mod_rate`, `set_air`, `set_tempo`, `set_shift`, `set_mod_type(mod_type='vibrato')` |
| Master | `all_sound_off`, `reset_all_controllers`, `program_change(program)` |
| Escape hatches | `send_raw_sysex(hex_bytes)`, `send_cc(controller, value)` |

## Install

From PyPI (once published) or directly from GitHub:

```bash
pip install git+https://github.com/Ziforge/phase8-mcp
```

Or in a checkout:

```bash
git clone https://github.com/Ziforge/phase8-mcp
cd phase8-mcp
pip install -e .
```

Auto-connects on startup to any MIDI port whose name contains
`phase8`. Override with `connect_phase8(port_pattern="...", channel=N)`.

### Wiring it into Claude Code

```json
{
  "mcpServers": {
    "phase8": {
      "command": "phase8-mcp"
    }
  }
}
```

## Example prompts (for the MCP client)

- "Play a slow strum across all 8 resonators, 100 ms per note"
- "Set resonator 5's envelope knob to 80 and its velocity to 60"
- "Change to patch 3, then trigger resonator 1 for 2 seconds"
- "Enable vibrato mod at depth 90, rate 40"

## Related MCPs

Ziforge maintains several MCP servers for the hardware in the same
livecoding rig — all follow the same shape (FastMCP + python-rtmidi,
auto-connect by port-name substring, typed helpers for the top of the
MIDI chart plus escape hatches for the rest):

| MCP | For |
|---|---|
| [`disting-nt-mcp`](https://github.com/Ziforge/disting-nt-mcp) | Expert Sleepers Disting NT |
| [`fh2-mcp`](https://github.com/Ziforge/fh2-mcp) | Expert Sleepers FH-2 MIDI-to-CV |
| [`es9-mcp`](https://github.com/Ziforge/es9-mcp) | Expert Sleepers ES-9 audio interface |
| [`erae-mcp`](https://github.com/Ziforge/erae-mcp) | Embodme ERAE Touch II |
| [`cirklon-mcp`](https://github.com/Ziforge/cirklon-mcp) | Sequentix Cirklon sequencer |
| [`elektron-mcp`](https://github.com/Ziforge/elektron-mcp) | fork of zerubeus/elektron-mcp — Digitone, Digitakt, etc. |

## Contributing

Pull requests welcome. Suggested workflow:

1. Fork + branch.
2. `pip install -e .[dev]` (once dev extras land) or just install the
   base deps and run against a physical Phase 8 or via a virtual
   MIDI port for smoke testing.
3. If you're adding a Korg SysEx opcode or an undocumented CC that
   the manual doesn't cover, cite the source (community wiki, forum
   thread, sniffed capture) so future maintainers can reproduce.
4. Keep the style consistent with the other Ziforge MCPs — one
   `server.py` with FastMCP tools, a `pyproject.toml`, a README with
   the MIDI table + tools table.

## Attribution

MIDI implementation chart transcribed from the *phase 8 owner's manual*
v1.00 (Korg, 2025-11-20), section 12.0. Manual PDF available from
[Korg's support page for the Phase 8](https://www.korg.com/us/support/download/product/1/945/).

## License

GPL v2. See [`LICENSE`](LICENSE).
