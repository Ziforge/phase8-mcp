# phase8-mcp

MCP server for a **Korg Phase 8** acoustic synthesizer. Wraps the MIDI
implementation documented in the phase 8 owner's manual v1.00
(2025-11-20) so an MCP client can trigger resonators, drive per-resonator
knobs, and modulate globals over USB MIDI.

Part of the [`superclean-collaboration`](../README.md) monorepo — this
lets Daniel's SC session or Claude Code drive George's Phase 8 during
livecoded sets at EMS Stockholm.

## MIDI implementation covered

Direct from section 12.0 of the phase 8 manual:

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

```bash
cd phase8-mcp
pip install -e .
```

Auto-connects on startup to any MIDI port whose name contains
"phase8". Override with `connect_phase8(port_pattern="...", channel=N)`.

## Example prompts (for the MCP client)

- "Play a slow strum across all 8 resonators, 100 ms per note"
- "Set resonator 5's envelope knob to 80 and its velocity to 60"
- "Change to patch 3, then trigger resonator 1 for 2 seconds"
- "Enable vibrato mod at depth 90, rate 40"

## License

GPL v2, matching the rest of the monorepo. See [`../LICENSE`](../LICENSE).
