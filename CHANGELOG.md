# ME-OLE — Changelog

## v0.93

### Bug fixes
- **Preset button slots corrected — button N loads slot(N+1)** (`me1.py`):
  Device testing with a factory reset confirmed the exact slot behaviour:
  the boot/display preset is slot0, but pressing **button N loads slot(N+1)**.
  The correct layout is:

  - **slot0** = P1 boot/display copy (shown on initial load)
  - **slot2** = P1 button slot (device loads this when user presses button 1)
  - **slot3** = P2 button slot (device loads this when user presses button 2)
  - **slot4** = P3, **slot5** = P4 … **slot17** = P16

  `_preset_offset` updated: `i=0 → 0` (boot copy), `i≥1 → (i+2)*_SLOT` (button slots).
  `_encode` now writes P1 to **both** slot0 (boot display) and slot2 (button 1 slot),
  and P2 to slot3 (button 2 slot). Name table entries [1] and [2] always `0x01`.

---

## v0.92

### Bug fixes
- **Reverted to v0.90 layout — device boots from slot0, not slot2** (`me1.py`):
  v0.91 incorrectly assumed the device boots from slot2. Confirmed testing proved
  the device boots from **slot0** (Preset 1 is always shown first on load).
  The v0.91 change (P2→slot3) caused Preset 2 to appear blank because the device
  looks for P2 at slot2 (name table entry[1] → slot2).

  v0.92 restores the v0.90 layout exactly:
  - slot0 = P1, slot2 = P2, slot3 = P3 (or P1 copy when no P3)
  - Name table entries [1] and [2] always `flag=0x01`
  - Slot3 always has valid data (P3 data, or exact P1 copy fallback for 2-preset configs)

  The "boots on P2" behaviour reported in v0.89 testing was a device state issue
  (device retaining state from previous bad imports), not a file format problem.
  TEST65 (v0.89) is structurally identical to TEST60 (device-created) and both
  boot correctly on Preset 1.

---

## v0.91

### Bug fixes
- **Preset 1 is now the default/boot preset** (`me1.py`): The device reads from
  **slot2** on startup — not slot0. Slot0 is a saved backup that the device writes
  but does not boot from. For a ME-OLE-created config to boot on Preset 1, slot2
  must contain Preset 1's data.

  Previous versions wrote Preset 2 to slot2 (following the device export layout
  where slot2 = last-recalled preset). This caused the device to always boot on
  Preset 2. The corrected layout:

  - **slot0** = Preset 1 saved backup
  - **slot2** = Preset 1 live copy (device boots from here; P1 is always the startup preset)
  - **slot3** = Preset 2
  - **slot4** = Preset 3, **slot5** = Preset 4 … **slot17** = Preset 16

  `_preset_offset` updated: `i=0 → 0`, `i≥1 → (i+2)*_SLOT` (P2→slot3, P3→slot4…).
  `_encode` now always writes P1 to slot2 (with group-flag normalisation 0x30→0x20).

---

## v0.90

### Bug fixes
- **File layout definitively corrected** (`me1.py`): After extensive analysis comparing
  TEST60 (device-created, 2-preset), TEST65 (ME-OLE, 2-preset), and BASS.ME1 (device,
  14-preset), the correct slot layout is confirmed as:

  - **slot0** = Preset 1 (P1)
  - **slot1** = Name table
  - **slot2** = Preset 2 (P2) — also serves as active preset buffer at runtime
  - **slot3** = Preset 3 (P3)
  - **slot4..slot16** = Presets 4-16
  - **slot17** = Device working state (preserved for round-trip fidelity)

  The key evidence was BASS.ME1 (14 presets): its slot3 contains "1TO16" (P3 data), 
  not a copy of P1. The "slot3 = P1 copy" seen in TEST60 was the device's own behaviour
  when the P3 slot is empty — the device fills empty slots itself. ME-OLE should not
  write this copy.

  `_preset_offset` reverted to the original correct formula:
  `i=0 → 0`, `i≥1 → (i+1)*_SLOT`. The `_encode` slot3-P1copy write is removed.
  TEST65 now round-trips with **0 byte differences**.

- **Note on boot default**: The device always starts from slot2 (P2) as the active
  preset buffer. With a 2-preset config, the device will display P2 on first boot.
  Pressing the P1 button correctly loads P1. This is consistent with how the device
  exports its own configs (TEST60 boots on P2 because P2 was last recalled).

---

## v0.89

### Bug fixes
- **Both presets showing Preset 2 data on device** (`me1.py`): The v0.88 layout
  fix was still incorrect. Byte-for-byte comparison of TEST60 (device-created)
  confirmed the definitive file layout:

  - **slot0** = Preset 1 (saved)
  - **slot2** = Preset 2 (saved; also serves as active preset buffer at runtime)
  - **slot3** = Live copy of Preset 1 — exact byte copy of slot0, always required
  - **slot4** = Preset 3, **slot5** = Preset 4 … **slot17** = Preset 16

  ME-OLE v0.88 was writing P2 to slot3 and a live copy of P2 to slot2.
  The device reads slot3 as P1's live copy (not P2), so it saw P2 data everywhere.

  **Fix:** `_preset_offset` now returns slot2 for P2, slot4 for P3, slot5 for P4, …
  slot17 for P16. `_encode()` always writes an exact copy of slot0 to slot3.
  Name table entry[2] is always marked `flag=0x01` since slot3 always has data.
  Fresh ME-OLE configs now match TEST60 (device-created) byte-for-byte on all
  structural fields.

---

## v0.88

### Bug fixes
- **Tom showing Fred's buttons / Fred blank on device** (`me1.py`): This was a
  fundamental file layout bug. The device uses a 3-slot scheme for presets:
  - **slot0** = P1 saved data
  - **slot2** = Active preset buffer (device reads this on startup; updated at runtime
    when the user recalls any preset)
  - **slot3** = P2 saved home (device reads this when the user explicitly selects P2)
  - **slot4..slot17** = P3..P16 saved homes

  ME-OLE was writing P2 to slot2 only. The device boots from slot2 (showing P2/Fred as
  the default state), but when the user selects P1 it correctly loads slot0 (Tom), and
  when the user selects P2 it reads from slot3 — which was empty — resulting in a blank
  preset. This also meant the "default" view on boot showed P2 (Fred) instead of P1 (Tom).

  **Fix:** `_preset_offset(i)` now returns `(i+2)*_SLOT` for i≥1, placing P2 at slot3,
  P3 at slot4, ..., P16 at slot17. Slot2 is always written with P2's data (so the device
  boots with P2 as the active state, matching device behaviour), or a live copy of P1 if
  no P2 exists. Name table entry[2] is now marked `flag=0x01` when P2 has data, matching
  the device. Confirmed from byte-for-byte comparison with TEST60 (device-created file).

---

## v0.87

### Bug fixes
- **Group buttons not working on device — wrong preceding-button flag** (`me1.py`):
  `Preset._encode()` was writing `0x20` (`_FLAG_GROUP_ALT`) as the flag for the
  non-group button immediately preceding a group button. Device firmware (confirmed
  from TEST60, latest firmware) expects `0x30` (`_FLAG_GROUP_DEFAULT`) here. The same
  fix applies to `header[7]` (changed from `0x20` to `0x30` when button 1 is a group).
  Note: older firmware files (e.g. BASS.ME1) used `0x20` in these positions — the
  device accepts both values, but writing `0x30` matches current firmware behaviour.

- **Slot[40] sentinel incorrectly written for multi-channel groups** (`me1.py`):
  `assign_group()` was unconditionally writing the sentinel `03 80 01 25` at `slot[40]`
  for all group buttons. The device only writes this sentinel for single-channel groups;
  multi-channel groups leave `slot[40]` as the default `00 80 01 25`. The sentinel is
  now only written when the group has exactly one member channel. Single-channel group
  detection on load continues to work correctly via the sentinel.

---

## v0.86

### Bug fixes
- **Preset 2 data corrupted on save** (`me1.py`): `ME1Config._encode()` was applying
  the live-copy flag normalisation (stripping `0x30→0x20` group signals, mirroring
  `header[7]`) to slot 2 unconditionally — even when slot 2 contained real Preset 2 data.
  This overwrote P2's own group chain flags with P1's values, corrupting P2 on every save.
  The fix: slot 2 is now written as-is when Preset 2 has data. The live-copy normalisation
  (flag `0x30→0x20`, `header[7]` mirroring) is only applied when Preset 2 is empty, in
  which case a live copy of Preset 1 is written so the device starts correctly.

  This was the root cause of: "Preset Fred had the name but showed up as blank",
  "Recalling Preset 1 actually recalled Preset 2", and "Group names not coming through"
  — all three were consequences of P2's slot being overwritten with P1's adjusted data.

- **Round-trip fidelity improvement**: TEST59.ME1 (ME-OLE created) now round-trips with
  0 byte differences. TEST60.ME1 (device created) has 7 pre-existing structural
  differences (cpan recalculation, flag normalisation, `+204` bytes) which do not affect
  device functionality.

---

## v0.85

### Bug fixes
- **Preset 2 still showing blank / state not refreshing after rename** (`me1_editor.py`):
  The `update-preset-name` route now returns the full `config_to_dict()` response instead
  of `{"ok": True}`. The JS handler now replaces the entire `state` object from this
  response, ensuring `has_data`, button assignments, and all other preset state are
  immediately in sync after a rename — without needing to save a button first.

- **Group names not appearing in editor after save** (`me1_editor.py`):
  The `update-preset-name` JS handler previously only patched `state.presets[n].name`
  in place, leaving `has_data` and other fields stale. With the full state refresh above,
  the button grid and group labels now reflect the server state immediately.

- **Single-channel groups lost on reload** (`me1.py`): `assign_group()` was not writing
  the firmware sentinel at `slot[40]` (`03 80 01 25`). The device always writes this
  sentinel for all group buttons (single and multi-channel), and ME-OLE's group detection
  (added in v0.82) requires it to distinguish a genuine single-channel group from a stale
  `0x04` slot. Groups created by ME-OLE now write the sentinel, so single-channel groups
  survive a save/reload cycle correctly.

---

## v0.84

### Bug fixes
- **Preset 2 (and others) showing as blank after being named** (`me1_editor.py`): The
  `update-preset-name` route was not setting `has_data = True` when a name was applied to
  a previously-empty preset slot. This meant a user could name a preset and see the name
  appear in the list, but the preset's buttons would not be visible until a button was
  also saved. Naming a preset with a non-empty name now immediately marks it as having
  data so the button grid is active and ready to use.

- **Group button label not saving when created from an unassigned button** (`me1_editor.py`):
  When a user clicked an unassigned button and switched to the Group type pill, the
  `ed-default-name` checkbox and `ed-label` input retained their state from the previous
  `renderEditor` call. If a previous button had left the checkbox checked or the label
  field disabled, the label input would be silently suppressed on save, sending an empty
  string to `assign_group()`. The type pill click handler now explicitly resets the
  checkbox to unchecked and re-enables the label field whenever switching to the group
  type from a different type.

---

## v0.83

### Bug fixes
- **Button 14 (and similar) incorrectly shown as assigned** (`me1_editor.py`): The Bug B
  `single_no_ch` condition previously triggered when a button had a non-blank label,
  even if its level was `0x80` (sentinel/off). A label alone without an active level is a
  firmware ghost — the firmware carried the channel name across from the console but the
  button was never actually assigned. The condition is now stricter: a button is only
  classified as `single_no_ch` (assigned, channel unknown) when it has **both** a
  non-blank label **and** an active level. A blank label **or** a sentinel level now
  correctly resolves to `unassigned`.

---

## v0.82

### Bug fixes
- **Single-channel groups now correctly detected** (`me1.py`): Group detection previously
  required 2+ slots with marker `0x04`, so single-channel groups (one member channel) were
  missed and displayed as `single_no_ch`. The firmware always writes a sentinel value at
  `slot[40]` (`03 80 01 25`) for every group button. Detection now accepts 1+ marker slots
  when this sentinel is present, correctly identifying single-channel groups like a button
  assigned to only ch14 or ch27.

- **Single-channel buttons with `flag=0x20` now correctly detected** (`me1.py`): A
  single-channel button that physically precedes a group button gets `flag=0x20`
  (`_FLAG_GROUP_ALT`) written by the firmware as a signal to the device — not as a
  description of its own assignment type. The Bug A fix now covers both `flag=0x30` and
  `flag=0x20` when a valid channel byte is present and the key has no group slot data,
  promoting these to `_FLAG_MONO` so they display correctly as single-channel buttons.

---

## v0.81

### Bug fixes / improvements
- **Round-trip fidelity: slot 17 (device state block) now preserved** — The ME-1 firmware keeps a
  "current working state" copy of the active preset in the 18th slot of the config file
  (`0x11000`). Previously ME-OLE wrote zeros there on every save, producing 2508 byte
  differences against the original device-exported file. The block is now read on load and
  re-emitted unchanged on save, reducing round-trip diffs for BASS.ME1 from 2750 → 242.
  The remaining 242 diffs are pre-existing structural recalculations (console pan, group flag
  normalisation, channel field recalculation) that do not affect device functionality.

---

## v0.80

### Bug fixes
- **Firmware export bug fix (Bug A) — single-channel buttons showing as unassigned**: Buttons with `flag=0x30` on disk but a valid channel byte in the standard encoding position are now correctly identified as single-channel assigned buttons. Previously, `flag=0x30` (which doubles as both `_FLAG_UNASSIGNED` and `_FLAG_GROUP_DEFAULT`) caused these buttons to report `is_assigned()=False` and display as blank in the editor. Affected buttons now load correctly with their channel number and display as blue (single-channel) buttons. Fixed in `me1.py` — `Preset._decode()` now promotes these keys to `_FLAG_MONO` after the channel decode pass (guard: must have no group slot markers). Approximately 30 keys per file affected in typical device-exported configs.

- **Firmware export bug fix (Bug B) — channel number lost, button showing as unassigned**: Buttons where the firmware wrote `0xFF` in the channel byte but the button has a real label and/or active level are now shown as `single_no_ch` ("assigned, channel unknown") instead of `"unassigned"`. These buttons display with a red pip on the hardware panel (distinct from the normal blue pip) and show `"Label · CH?"` as their tooltip. Clicking such a button opens the single-channel editor with a red warning banner explaining that the channel was lost to a firmware export bug, and prompts the user to enter the correct channel number. Once a channel is entered and saved, the button becomes a normal single-channel button. Approximately 30 keys per file affected in typical device-exported configs.

---
## v0.4 — 2026-03-28

### Fixed
- **Button 1 misidentified as group** — flag byte `0x40` was incorrectly treated as
  a stereo/group encoding. Analysis of real device exports (Preset 3 in OLIVET with
  15 sequential channels all using `0x40`) confirms it is simply an alternate mono
  encoding, identical in behaviour to `0x00`. Renamed internally to `_FLAG_MONO_ALT`.
- **Pan defaulting to hard-left** — unset keys had sentinel pan value `0x01` displayed
  raw; UI now substitutes `128` (centre) for unset keys.

### Added
- **Level slider** — each button now has a level control (0 = Off → 255 ≈ +10 dB).
  Displays an approximate dB label; exact dB mapping is not yet confirmed from hardware.
- **Unity button** — one-click sets level to `0xF0` (240), the approximate unity gain
  value observed in real device exports.
- **Wider editor panel** — right sidebar widened from 286 px to 340 px for more
  comfortable editing.

### Research notes
- `0x40` confirmed = single mono channel (same as `0x00`). Observed in Allen & Heath
  console exports as an alternate encoding for individual input assignments.
- Level byte observed range in real files: `0xD2`–`0xF5` (210–245).
  `0xEF`–`0xF0` (239–240) appears to correspond to approximately 0 dB (unity).
  Exact dB scale needs hardware measurement to confirm.

---

## v0.3 — 2026-02-27

### Added
- **Docker container** — ships as a multi-platform Docker image.
  Builds for `linux/amd64`, `linux/arm64`, `linux/arm/v7` from a single Linux host.
- **Gunicorn** replaces Flask dev server — production WSGI server, bound to
  `0.0.0.0:5000` for remote access.
- **Hardware image UI** — buttons overlay the actual ME-1 photo.
  Assigned buttons show a status pip; hover shows label and channel tooltip.
- **Pan defaults to centre (128)** for new and unset keys.

---

## v0.2 — 2026-02-27

### Added
- **Group source type** — 40-cell channel grid for multi-channel assignment.
  Adjacent stereo pairs (e.g. ch 3+4) encode correctly; full multi-channel groups
  pending hardware sample.
- **Centre pan button** — snaps pan to 128.
- **Source type redesign** — Single / Group / Blank with contextual controls.
- **Label hints** — "optional, board sends name" for single; "required" for groups.

---

## v0.1 — 2026-02-27

### Initial release

**me1.py** — binary format library.
- `ME1Config.load()` / `.save()` — full 73728-byte config files
- `Preset.load()` / `.save()` — single 4096-byte preset files
- `Key.assign_mono()`, `.assign_stereo()`, `.assign_unassigned()`
- Round-trip fidelity: CLC.ME1 byte-perfect

**me1_editor.py** — Flask/Gunicorn web app.
- Open / save .ME1 files, edit all 16 buttons per preset

---

## Flag byte encoding (confirmed)

| Flag  | Meaning                                      |
|-------|----------------------------------------------|
| 0x00  | Mono single channel (ch 1–40)                |
| 0x40  | Mono single channel — alternate encoding     |
| 0x10  | Stereo linked pair (right = src_ch + 1)      |
| 0x01  | Special / personal mix bus                   |
| 0x30  | Unassigned (src_ch = 0xFF)                   |

## Group encoding (pending hardware sample)

Full multi-channel group encoding not yet confirmed. To unlock: export a .ME1
from a ME-1 with a group assigned to at least one button and share the file.

---

## v0.5 — 2026-03-28

### Fixed
- **Group encoding confirmed and implemented** — Groups were previously unsupported.
  Analysis of OLIVET.ME1 revealed the encoding: the button's on-disk flag stays `0x00`
  (same as mono); group membership is stored in the slot data where
  `slot[channel - 1] = [0x04, level, pan, 0x25]`. The library now reads and writes
  groups correctly with full per-member level and pan support.
- **Button 14 now correctly reads as unassigned** — `flag=0x00` combined with
  `src_ch=0xFF` is now treated as unassigned. Previously it was misread as a
  single-channel assignment to a non-existent channel.
- **Pan sentinel `0x01` now displays as centre** — The device stores `0x01` in the
  pan field to mean "not set / use default (centre)". This now correctly displays
  as `C` in the editor rather than hard-left for all keys, including assigned ones.
- **Group editor removes adjacent-pairs-only restriction** — Any combination of
  channels 1–40 can now be saved as a group.

### Research notes
- Group on-disk encoding: `flag=0x00`, `src_ch=primary_channel`,
  slots: `slot[ch-1] = [0x04, member_level, member_pan, 0x25]` for each member `ch`.
- Empty/unset slots remain `[0x00, 0x80, 0x01, 0x25]` (default).
- Round-trip key data: **0 differences** against OLIVET.ME1
  (9 trivial header-byte diffs in unused blank preset blocks are benign firmware garbage).

---

## v0.6 — 2026-03-28

### Fixed
- **Pan encoding was completely reversed** — the ME-1 stores pan as
  `0x00 = Hard Right`, `0x80 = Centre`, `0xFF = Hard Left`
  (low values = right, high values = left). Our constants `PAN_LEFT`/`PAN_RIGHT`
  and the slider display labels were backwards. Both the library constants and
  the UI display are now corrected.
- **Pan sentinel `0x01` display** — `0x01` is the device's "not set / use centre"
  value. Now correctly displays as `C` and maps to `128` for the slider. Previously
  it could show as slightly-right-of-hard-right on the corrected scale.
- **Button 13 wrongly shown as unassigned** — the v0.5 rule
  `flag=0x00 + src=0xFF → unassigned` was too broad. It now only applies when the
  key is *completely* blank (sentinel level, sentinel pan, and empty label).
  Button 13 has a label (`'coust'`, surviving portion of `'Accoust'`) so it
  correctly shows as assigned. The channel field is corrupted (`0xFF`) due to a
  known firmware export bug where long label characters overwrite adjacent fields —
  you can reassign it to the correct channel in the editor.
- **Sep byte preserved on round-trip** — the separator byte before each key's
  label can be non-`0x25` when a label's first character has been consumed by a
  firmware export quirk (e.g. button 1 sep = `0x4a` = `'J'`). This byte is now
  stored and re-emitted exactly on encode, giving zero key-data diffs on round-trip.

### Research notes
- Pan scale confirmed: `0x00` = Hard Right, `0x80` = Centre, `0xFF` = Hard Left.
  `0x01` = device sentinel for "not set / use centre".
- The firmware export quirk that corrupts label bytes: when the console sends
  a channel name, its first character can overflow into the separator position
  (and occasionally into pan/level), truncating the stored label by 1–2 chars.
  The affected key still works on the device; only the exported label is truncated.

---

## v0.7 — 2026-03-28

### Fixed
- **Critical: channel number written to wrong device position** — when saving a
  single-channel button, the editor always wrote flag `0x00` regardless of whether
  the original used `0x40`. The device treats these two flag values differently:
  with the wrong flag, the device reads the channel number from a different byte
  offset in the record (the default slot data `0x01`), causing it to see ch1 instead
  of the intended channel, and the actual channel value shifts into the *next*
  button's field (ch10 → ch1 on the edited button, ch10+1=ch11 on the next).
  The fix preserves the original on-disk flag (`_disk_flag`) through
  `assign_mono()` / `assign_stereo()`. New buttons (no prior disk flag) default
  to `0x40`, matching what the console writes when setting up channels initially.

### Research notes
- Flag byte `0x40` and `0x00` are NOT interchangeable on the device, even though
  both encode a single mono channel. The device uses the flag to determine which
  byte offset to read the channel number from within the key record.
- Round-trip key data: **0 differences** against OLIVET.ME1.

---

## v0.8 — 2026-03-29

### Fixed
- **`flag=0x40` is AUTO MODE, not "alternate mono"** — this was the root cause of all
  previous channel-write failures. When a button is in Auto Mode, the ME-1 device
  assigns its source channel automatically from the console's routing and completely
  ignores the `src_ch` byte. Every attempt to write a new channel to a flag=0x40
  button was silently discarded by the device. The fix: Auto Mode is now a distinct
  button type in the editor; switching to "Single" converts it to flag=0x00 so the
  channel is honoured by the device.
- **Pan slider was visually inverted** — dragging toward "left" in the UI sent
  `pan=0x00` (Hard Right) to the device, and vice versa. The slider is now corrected:
  left end = Hard Left (raw `0xFF`), right end = Hard Right (raw `0x00`), centre
  button writes `0x80`.
- **Level `0x80` labelled as "Off"** — `0x80` is the ME-1's fader-at-minimum value
  (what the device stores when volume is all the way down), not a sentinel. The level
  display and `LEVEL_OFF` constant are updated accordingly.

### Added
- **Auto Mode button type** — buttons with `flag=0x40` now show as "Auto" (blue pip
  on the hardware image, blue "Auto" pill in the editor). An info panel explains that
  the channel is assigned by the console. Users can switch an Auto button to Single to
  manually assign a specific channel.
- **`is_auto()` method** and **`assign_auto()`** on `Key`.
- **`LEVEL_FADER_OFF = 0x80`** alias alongside updated `LEVEL_OFF`.

### Research notes
- `flag=0x40` confirmed = AUTO MODE. The device uses `flag=0x00` for manually-assigned
  single channels. Confirmed by comparing OLIVET (Auto Mode on btn1/btn2) with NEWORIG
  (manually set to ch1/ch2 — flag changes from `0x40` to `0x00`).
- `src_ch` at offset `+204` is the correct channel field. All channels in OLIVET match
  NEWORIG exactly — channel encoding was always right for `flag=0x00` buttons.
- Level `0x80` = fader at minimum. Confirmed by buttons 9/10/11 set to "volume all the
  way down" in NEWORIG having `level=0x80`.
- Pan encoding confirmed: `0x00` = Hard Right, `0x80` = Centre, `0xFF` = Hard Left.
  The per-button "centre" values exported by the device vary because they encode the
  stereo balance relative to the source's console routing — not a fixed raw value.

---

## v0.9 — 2026-03-29

### Fixed
- **Critical: file header byte 7 was `0x40` instead of `0x00`** — this was causing the
  device to misread channels from all editor-written files. Every device-exported file
  (OLIVET, NEWORIG, NEWTEST) has `0x00` at header byte 7. Our `_HEADER` template had
  `0x40` there, which appears to signal a different format mode to the device firmware.
  With header `0x40`, the device ignores `src_ch` at `+204` and instead reads channels
  from default slot data (giving ch1 for every button), with the actual written channel
  value bleeding into the *next* button's position (producing the consistent `+1` pattern
  seen in all test failures).
- **Header bytes now preserved on save** — when a file is loaded and re-saved, the
  original 9-byte preset header is preserved verbatim rather than overwritten with the
  template. New presets created from scratch use the corrected `_HEADER` with `0x00` at
  byte 7.

### Research notes
- File header (9 bytes): `1d 1c 02 00 00 0c da [07] 00`
  - Byte 7: `0x00` = normal mode (device reads channel from `src_ch` at `+204`)
  - Byte 7: `0x40` = unknown alternate mode (device ignores `src_ch`, reads from
    slot default data, produces consistent channel `+1` bleed-through to next button)
- The `+1` bleed pattern: when header byte 7 = `0x40`, device reads button N's channel
  from the previous button's `src_ch` byte position, and adds `0x01` from the adjacent
  default slot byte `[00 80 01 25]`. This produced ch10+1=ch11, ch30+1=ch31 in tests.
- Button 12 and 13 sharing the same volume is a **device firmware behaviour**, not a
  file format issue. The ME-1 stores level/pan per source channel rather than per button,
  so two buttons on the same source channel share their fader state.

---

## v0.11 — 2026-03-29

### Fixed
- **Critical: button 1 channel stored at header byte 8, not key record +204** — this was
  the root cause of all channel-write failures for button 1 specifically. The device stores
  button 1's channel in the last byte of the 9-byte preset header (`block[8]`) as a
  0-indexed value (`channel − 1`). Buttons 2–16 use `key_record + 204` as before. Our
  editor was writing the channel only to `+204` for all buttons, which the device ignores
  for button 1. Now `_encode` writes `channel − 1` to `block[8]`, and `_decode` reads
  button 1's channel from `block[8]` (overriding the potentially stale `+204` value that
  the device leaves behind when it changes assignments).

- **CLEAR and uninitialized presets no longer show garbage button assignments** — preset
  blocks with header `byte2 = 0x01` (uninitialized flash) are now correctly treated as
  empty, showing all buttons as Unassigned. Previously the library decoded raw flash
  garbage as channel assignments.

### Research notes
- Confirmed by exact byte diff of two device-generated files (ORIG.ME1 with btn1=ch1 vs
  TEST4.ME1 with btn1=ch7): exactly 3 bytes differ — `block[8]` changed from `0x00` to
  `0x06` (= ch7 − 1), plus level/pan values that moved when the user touched the fader.
  The `+204` field for button 1 was **not updated** by the device, confirming it is not
  the authoritative channel field for button 1.
- Valid preset blocks have header `byte2 = 0x02`. Uninitialized blocks have `byte2 = 0x01`.
  Erased flash blocks are all `0xFF`.

---

## v0.11 — 2026-03-29

### Fixed
- **Critical: channel encoding is unified across all 16 buttons** — the channel for
  button N is stored at `block[8 + (N−1) × 205]` as `channel − 1` (0-indexed). For
  button 1 this is header byte 8; for buttons 2–16 it is the `+204` byte of the
  preceding key record. All 16 positions follow the same formula. Previous versions
  correctly handled button 1 (from v0.10) but still wrote buttons 2–16 to the wrong
  field (`key_record+204` of the current key rather than the previous key), causing
  channel writes for those buttons to be ignored by the device.

### Research notes
- Confirmed by exact byte diff of OLIORIG.ME1 vs TEST6.ME1 (both device-generated).
  User changed btn2→ch22, btn3→ch23, btn4→ch24, btn11→ch31. The device wrote
  `block[213]=0x15`, `block[418]=0x16`, `block[623]=0x17`, `block[2058]=0x1e`
  — each at `8 + (N−1) × 205`, each as `channel − 1`.
- Round-trip: 0 diffs across all 6 test files (OLIORIG, TEST6, OLIVET, ORIG,
  TEST4, NEWORIG).

---

## v0.12 — 2026-03-29

### Fixed
- **Group buttons now write 0xFF to the channel routing field** — a group button
  has no single source channel, so its routing position (`block[8 + (N-1)×205]`)
  must be 0xFF. Previously it was writing the group's first member channel (minus 1)
  there, which would confuse the device routing for that button slot.
- Round-trip: 0 diffs across all test files.

### Known unknowns (to resolve with device-generated files)
- Auto Mode channel field value (likely 0xFF like groups, but unconfirmed)
- 1kHz sine wave and Aux Input — flag values unknown; need device files to identify
- Pan and volume write verification end-to-end on device

---

## v0.13 — 2026-03-29

### Fixed
- **Unassigning a group button now fully clears the slot data** — previously `assign_unassigned()`
  only set the flag and src_ch but left the `b0=0x04` slot entries intact, so the device
  still detected the button as a group. All slot data is now reset to default
  `[00 80 01 25]` on unassign, and `_group_channels` is cleared.
- **Label field is hidden for Unassigned buttons** — the label input is irrelevant
  for blank buttons and is no longer shown in the editor panel.

---

## v0.14 — 2026-03-29

### Fixed
- **Group detection was broken after the channel encoding fix** — `Key._decode` checked
  for groups only when `flag ∈ {0x00, 0x40}` AND `src_ch ≠ 0xFF`. But `Preset._decode`
  overrides every button's `src_ch` from the channel routing table, which writes `0xFF`
  for groups. This meant the group-detection condition never fired — all group buttons
  decoded as Unassigned. Fixed: groups are now detected purely from slot data
  (`b0=0x04` entries), with no dependency on flag or src_ch value.

- **Header byte 7 now stores button 1's flag** — the device writes the on-disk flag
  for button 1 at header byte 7 (alongside button 1's channel at byte 8). For group
  buttons the device writes `0x20` there. `Preset._encode` now mirrors this correctly.

- **New flag `_FLAG_GROUP_ALT = 0x20`** — the device writes `0x20` as the on-disk flag
  for button 1 when it is a group. Added as a known constant. `Key._encode` now uses
  `_disk_flag` for all key types including groups, preserving the original flag for
  round-trips. New groups default to `_FLAG_MONO (0x00)`.

- **`assign_group()` now sets a correct `_disk_flag`** — previously left at the default
  `_FLAG_UNASSIGNED (0x30)`, causing new groups to write `0x30` as the on-disk flag.
  New groups now default to `_FLAG_MONO (0x00)`.

### Research notes
- Device-generated TEST10.ME1 confirmed: all three group buttons decode correctly
  (btn1 ch1,2,3 · btn2 ch4,5,6 · btn12 ch9,10,11). Round-trip: 0 diffs across all
  7 test files.
- Group detection relies solely on the presence of `b0=0x04` slot entries. Flag and
  src_ch values are unreliable indicators for group detection.

---

## v0.15 — 2026-03-29

### Fixed
- **Header byte 7 must be `0x20` when the preset contains group buttons** — the device
  uses this byte as a preset-type flag. When it is `0x00`, the device ignores all slot
  data and cannot detect group assignments, showing all buttons as Unassigned. When
  groups are present in the preset, `Preset._encode` now writes `0x20` at byte 7.
  Console-created groups that were already working with `0x00` will also receive `0x20`
  on re-save, which is harmless — the device accepts either value for those.

- **Unassigned buttons now write `flag=0x00` instead of `0x30`** — the device writes
  `0x00` for blank/never-assigned buttons. Our previous `0x30` value was causing the
  device to light up the Group indicator on those buttons, making them appear as
  undefined group assignments. `assign_unassigned()` now sets `_disk_flag=0x00`.

- **Group member slots now use sentinel level/pan `[04 80 01 25]`** — the device stores
  sentinel values (`0x80`/`0x01`) in group slot entries rather than the button's actual
  level/pan. The actual level and pan for the whole group button is stored at the key
  record's `+192`/`+193` fields as always. `assign_group()` updated accordingly.

### Research notes
- Confirmed from TEST12.ME1 (device-generated): both group buttons have `flag=0x00` in
  the key record; the group is identified purely from `b0=0x04` slot entries.
  Header `byte7=0x20` is the gate that enables group detection in device firmware.

---

## v0.16 — 2026-03-29

### Fixed
- **Groups for buttons 2–16 now load correctly on device** — the device requires the
  FLAG byte (`+203`) of the button immediately preceding a group button to be `0x20`.
  Without this, the device silently rejects the group assignment on file load, stripping
  the slot data and resetting the button to its default state. `Preset._encode` now
  writes `0x20` to the preceding button's flag field for every group button in the preset.
  For button 1 groups, the group button's own flag is set to `0x20` (no preceding button).
- **Group button `+193` field is now `0x00`** — groups have no overall pan; individual
  channel pans live in `slot[ch-1][2]` of the slot data. The byte at `+193` for group
  buttons is not a pan field — the device consistently writes `0x00` there. Fixed
  `assign_group()` default from `PAN_CENTRE (0x80)` to `0x00`.

### Research notes
- Confirmed from TEST10 (device, 3 groups), TEST15 (device, manually-set btn11 group):
  - Group at button N: button(N-1) flag = `0x20`
  - Group at button 1: btn1 own flag = `0x20`, header[7] = `0x20`
  - When consecutive buttons are groups: each group button's flag = `0x20` (it serves
    as the "preceding flag" for the next group)
- The `0x20` preceding-flag requirement applies only to ME-1-created groups loaded from
  file. Console-created groups (e.g. OLIVET btn16) appear to bypass this check.

---

## v0.17 — 2026-03-29

### Summary
Groups now work reliably for all button positions when loaded from file. This version
consolidates all group encoding fixes from v0.14 through v0.16 and is the first build
confirmed working end-to-end on the device for both btn1 and btn11 groups.

### Status
- ✓ Channel assignment (single) — all 16 buttons, device-verified
- ✓ Groups — btn1 and btn11 verified on device; encoding correct for all positions
- ✓ Unassigned buttons
- ✓ Labels / names
- ✓ CLEAR preset shows all Unassigned
- ✓ File round-trip clean across all test files
- ○ Pan changes — end-to-end device verification pending
- ○ Level changes — end-to-end device verification pending
- ○ 1kHz sine wave / Aux Input — flag values unknown; need device-generated files

---

## v0.18 — 2026-03-29

### Added
- **Aux Input support** — new button type for the 3.5mm jack on the rear of the unit.
  Encoded as channel field `0x28`, flag `0x20`. The device auto-labels the button "AuxIn".
  Available as "Aux In" in the editor's type selector.
- **1 kHz Sine Wave support** — new button type for the built-in test tone.
  Encoded as channel field `0x2F`, flag `0x00`. The device auto-labels the button "1kSine".
  Available as "1kHz Sine" in the editor's type selector.
- New library constants `SRC_AUXIN = 0x28` and `SRC_SINE = 0x2F`.
- New `Key` methods: `assign_auxin()`, `assign_sine()`, `is_auxin()`, `is_sine()`.

### Fixed
- Buttons with `flag=0x00` and `src_ch=SRC_NONE` (e.g. preceding-flag residuals) now
  correctly display as Unassigned rather than a channelless Single assignment.

### Research notes
- Confirmed from TEST20.ME1 (device-generated): AuxIn on btn8 has `ch_field=0x28`,
  `flag=0x20`; 1kSine on btn13 has `ch_field=0x2F`, `flag=0x00`. Both have sentinel
  level/pan and blank labels (device writes the label automatically from the type).
- Round-trip: 0 diffs on TEST20.ME1.

---

## v0.19 — 2026-03-29

### Fixed
- Buttons with `flag=0x00` and `src_ch=SRC_NONE` now correctly show as Unassigned
  in the editor, rather than as a channelless Single assignment (regression from v0.18).

### Known issue
- **AuxIn write encoding is not yet confirmed.** The `0x28` channel index written by
  the editor causes the device to light the Group indicator on that button but does not
  activate AuxIn. The device's own AuxIn encoding requires a device-generated baseline
  file to reverse-engineer correctly. AuxIn can be read/displayed from existing device
  files (e.g. TEST20.ME1) but setting it via the editor may not work until confirmed.
  To confirm: set AuxIn on a button via the device UI, export the file, and upload it.

### Status
- ✓ 1kHz Sine Wave — confirmed working on device (TEST21, btn14)
- ✓ Aux Input — reads correctly from device files; write encoding pending confirmation
- ✓ All other types — channels, groups, unassigned, auto, sine

---

## v0.20 — 2026-03-29

### Fixed
- **Aux Input write encoding confirmed and fixed** — the preceding button (N-1) must
  have `flag=0x01` (`_FLAG_SPECIAL`) for the device to accept AuxIn on button N.
  Previously the preceding flag was either unset or set to `0x20` (the group signal),
  which caused the device to light the Group indicator on the AuxIn button instead.
  The channel field `0x28` at the button's own channel position was already correct.
  Confirmed from device-generated TEST21.ME1 with working AuxIn on button 8:
  `btn7 flag=0x01`, `btn8 ch_field=0x28`, `btn8 flag=0x20`.

### Status
- ✓ Aux Input — confirmed working on device (TEST21, btn8)
- ✓ 1kHz Sine Wave — confirmed working on device (TEST21, btn14)
- ✓ Groups — confirmed working on device (all positions)
- ✓ Single channel — confirmed working (all 16 buttons)
- ✓ Unassigned, Auto Mode — working
- ○ Pan / level end-to-end device write — still to verify

---

## v0.21 — 2026-03-29

### Fixed
- **UI: Selecting Aux In or 1kHz Sine immediately reverted to Blank** — the
  `loadKeyIntoEditor` function only recognised `'single'` and `'group'` as valid
  types; anything else (including `'auxin'`, `'sine'`, `'auto'`) fell through to
  `'unassigned'`. The type is now passed through correctly for all known types.

---

## v0.22 — 2026-03-29

### Fixed
- **UI: Aux In and 1kHz Sine pills appeared unclickable** — clicking them gave no
  visual feedback because the `sel-auxin` and `sel-sine` CSS highlight classes were
  missing. Without the highlight, users couldn't tell the pill had been selected and
  didn't proceed to Apply. Both pills now highlight correctly when selected.
- **Auto pill was missing from the type selector** — it was accidentally dropped when
  Aux In and 1kHz Sine were added in v0.18. Restored.
- **Pill layout changed to flex-wrap** — with 6 pills (Single, Group, Blank, Auto,
  Aux In, 1kHz Sine) the row was too cramped. Pills now wrap to a second row when
  needed, keeping each pill a comfortable size.

---

## v0.23 — 2026-03-29

### Changed
- **Button status pips are now larger, centred, and colour-coded by type:**
  - 🔵 Light blue — Single channel
  - 🟢 Green — Group
  - 🟠 Amber — Auto Mode
  - 🟣 Purple — Aux Input
  - 🟡 Yellow — 1kHz Sine Wave
  - No pip — Unassigned (Blank)
- **Assigned buttons now dim slightly** so the coloured pip stands out against
  the hardware image background.
- **Tooltip labels extended** for all types: Auto shows the channel number,
  Aux In shows "Aux In", 1kHz Sine shows "1kHz Sine".

---

## v0.24 — 2026-03-29

### Fixed
- **Pip moved back to bottom-right corner** — centring it covered the button number.
  Pip is now 8×8px in the lower-right corner of each button.
- **Group buttons now show their pip** — old `.hw-btn.assigned-group` CSS rules
  were overriding the pip visibility with a conflicting background colour.
  Removed the stale single/group-only rules; all types now use a single unified
  dimming and pip rule set.

---

## v0.25 — 2026-03-30

### Fixed
- **Groups (and all types) now show their coloured pip and button dimming** —
  the previous CSS cleanup left behind stale conflicting rules and a malformed
  `; }` token that made the browser silently discard everything that followed,
  including the pip visibility rules. Full clean rewrite of the pip/assigned
  CSS block with no legacy fragments.
- **Tooltip labels were accidentally removed** in v0.24 during the CSS cleanup;
  restored.

---

## v0.26 — 2026-03-30

### Fixed
- **Aux Input button corrupted the channel assignment of the button after it** —
  `assign_auxin()` was setting `_disk_flag=0x20` on the AuxIn button itself.
  The device interprets flag=`0x20` as "the next button is a special/group type"
  and ignores that button's channel assignment. Fixed: the AuxIn button's on-disk
  flag is now `0x00`, matching what the device writes (confirmed from TEST24.ME1).
  The preceding button (N-1) still correctly gets `flag=0x01` as required.
- **AuxIn decode no longer overwrites `_disk_flag`** — `Preset._decode` was
  setting `_disk_flag=0x20` for AuxIn buttons, losing the original on-disk value
  (`0x00` or `0x20` depending on device). Now preserves the raw value from the file.

### Research notes
- Confirmed from TEST23 (editor, broken) vs TEST24 (device, working): only 1 critical
  diff — btn7 flag `0x20` (editor) vs `0x00` (device). Channel fields for btn6 (ch37),
  btn7 (AuxIn=0x28) and btn8 (ch38) were identical. Round-trip diffs on TEST24: 0.

---

## v0.27 — 2026-03-30

### Changed
- **Type pills coloured to match button pips:**
  Single = light blue, Group = green, Blank = grey, Aux In = purple, 1kHz Sine = yellow.
- **Pill layout redesigned:** two rows — Single + Group on top; Blank + Aux In + 1kHz Sine below.
- **Auto Mode removed from the type selector.** Existing Auto buttons loaded from device
  files still display correctly, but Auto cannot be assigned via the editor. Manual single
  or group assignments are clearer.
- **Click an already-selected button to deselect it.** The editor panel closes and
  "click a button to edit" is shown again.

### Added
- **Group channel validation:** channels already used in another group in the same preset
  are shown greyed-out in the channel picker and cannot be selected. Only channels assigned
  to individual single buttons (or unassigned) remain available to pick.

---

## v0.28 — 2026-03-30

### Fixed
- **Creating a config from scratch now works** — `assign_mono()` was not setting
  `_disk_flag`, so every button assigned from a new config inherited the default
  `_FLAG_UNASSIGNED (0x30)` on disk. The device treats `0x30` as "explicitly
  unassigned" and ignores the channel assignment. Fixed: `assign_mono()` now
  sets `_disk_flag = _FLAG_MONO (0x00)`, matching what the device writes for
  single-channel buttons.

### Roadmap (next items)
- Pan and level write verification end-to-end on device
- Per-channel pan and level for group buttons (slot[ch-1] bytes 1 and 2)
- Stereo pair type (flag=0x10) — seen in files, not yet implemented

---

## v0.30 — 2026-03-30

### Added
- **Editable filename in the topbar** — click the filename to rename it.
  Only letters and numbers are accepted; automatically converted to uppercase;
  maximum 8 characters for the base name; `.ME1` extension always appended.
  Press Enter or click away to confirm.

### Fixed
- **Server crash when editing a preset name before any config is loaded** —
  `/api/update-preset-name` now returns a clean 400 error instead of a 500
  traceback when `_config` is `None`.

---

## v0.31 — 2026-03-30

### Fixed
- **Software-generated configs caused all buttons to appear in Auto Mode on device** —
  two related encoding bugs:

  1. **`header[7]` was set to `0x20` whenever any group existed in the preset.**
     The correct rule (confirmed from all device-generated files) is: `header[7]=0x20`
     only when **button 1 itself is a group** (it has no preceding button to carry the
     flag). When groups are on buttons 2–16 only, `header[7]` must be `0x00`. The old
     code fell back to the value from the loaded file, which preserved a stale `0x20`
     from a previous group-containing config.

  2. **Block 2 (offset `0x2000`) was left as erased flash (`0xFF`) when only one preset
     existed.** The ME-1 always expects block 2 to hold a valid "live copy" of preset 1.
     Without it, the device falls back to a factory default state and shows all buttons
     as Auto Mode. Now, when preset 2 has no data, block 2 is written as an exact copy
     of preset 1.

### Research notes
- Confirmed from TEST27 (SW, broken) vs TEST28 (device, working): the two diffs above
  were the only structural differences causing the Auto Mode regression.
- TEST28 now round-trips with zero diffs.

---

## v0.32 — 2026-03-30

### Fixed
- **Software-generated configs still broken after v0.31** — a third encoding bug
  remained: unassigned buttons were written to disk with `flag=0x30`
  (`_FLAG_UNASSIGNED`) instead of `flag=0x00` (`_FLAG_MONO`). The device
  interprets `0x30` as an explicit "disabled" marker and ignores the entire
  button, causing it to fall back to Auto Mode behaviour.

  Root cause: `Key.__init__` initialised `_disk_flag` to `_FLAG_UNASSIGNED`
  (0x30). New buttons in a fresh config are never explicitly assigned, so
  `assign_unassigned()` was never called and `_disk_flag` never got corrected.
  Fixed: `Key.__init__` now defaults `_disk_flag` to `_FLAG_MONO` (0x00),
  matching what the device writes for all blank/unassigned buttons.

### Research notes
- Confirmed from TEST29 (SW v0.31, broken) vs TEST28 (device, working):
  the only remaining diff was `flag=0x30` on all unassigned buttons in SW
  vs `flag=0x00` in the device file.
- TEST28 and TEST29 both now round-trip with zero diffs.

---

## v0.33 — 2026-03-30

### Fixed
- **Software-generated configs still showing blank preset / Auto Mode after v0.32** —
  a fourth encoding bug found: the name table (block 1) was writing `flag=0x00` for
  the live-copy slot (preset index 1, block 2 / offset `0x2000`), causing the device
  to ignore that block entirely and fall back to factory Auto Mode defaults.

  Every device-generated file has `flag=0x01` in the name table for the live-copy
  slot. Our library used `flag = 0x01 if has_data else 0x00`, but newly created
  presets have `has_data=False` even though we now always write valid data to block 2.
  Fixed: the name table now always writes `flag=0x01` for preset index 1 (the
  live-copy slot), since block 2 always contains valid data.

### Research notes
- Confirmed from TEST30 (SW v0.32, broken) vs TEST28 (device, working):
  single remaining diff was name table byte 10: `0x00` (SW) vs `0x01` (device).
- TEST28 continues to round-trip with zero diffs.
- This is the fourth flag-related encoding bug in this area:
  v0.28 fixed `assign_mono` `_disk_flag`, v0.31 fixed `header[7]` and missing
  block 2, v0.32 fixed `Key.__init__` default `_disk_flag`, v0.33 fixes the
  name table live-copy flag.

---

## v0.34 — 2026-03-30

### Fixed
- **Software-generated presets still showing Auto Mode after loading (v0.33)** —
  a fifth encoding issue: every device-generated preset block contains an 807-byte
  trailing EQ/config data block starting with signature `5538 cf01 0000 002d`.
  Without this block (all zeros in its place), the device appears to ignore the
  preset's channel assignments and fall back to Auto Mode routing.

  New presets now always include this block with flat-EQ default values
  (matching the minimal version seen in TEST28). Previously `Preset._tail` was
  initialised to empty bytes `b''`, producing all zeros in the trailing area.

### Research notes
- Signature `5538cf01` is present in every single device-generated file examined
  (TEST21, TEST24, TEST28, OLIVET, OLIORIG, ORIG, TEST10, TEST12).
  The bytes following the signature appear to encode EQ band parameters.
  TEST28 (the confirmed-working reference) has the minimal version with flat EQ.
- TEST28 and TEST31 both round-trip with zero diffs after this fix.

---

## v0.35 — 2026-03-31

### Fixed
- **Software configs still showing Auto Mode on device (v0.34)** — the final
  encoding bug: the `+204` byte of the last key record (button 16) must be
  `0x22` in every preset block. Every single device-generated file has this
  value; our software was writing `0xFF` (the default for a new `Key`).

  This byte has no channel-routing purpose (button 17 doesn't exist), but the
  device appears to use it as a required terminator or validity marker. Without
  it the device ignores the preset assignments and falls back to Auto Mode.

  Fixed: `Key._raw_ch_field` now defaults to `0x22` instead of `0xFF`.

### Research notes
- Confirmed from TEST32 (SW v0.34, broken) vs TEST33 (device, working):
  the only structural difference was `btn16 +204 = 0xFF` (SW) vs `0x22` (device).
  `0x22` appears in **every** device-generated file examined without exception.
- TEST32, TEST33, and TEST28 all round-trip with zero diffs after this fix.

---

## v0.36 — 2026-04-01

### Changed
- **Level slider now displays dB values** confirmed from TEST34 device data:
  - `0x80` = Off (silent, below active range)
  - Active range: `0xCB` (−42 dB) to `0xFF` (+10 dB), linear
  - Unity gain (0 dB) = `0xF5` — now the default for new single-channel buttons
  - Slider shows values like "−17.0 dB", "+3.5 dB", "0 dB (Unity)", "Off"

### Added (library)
- `LEVEL_UNITY = 0xF5` — unity gain constant
- `level_to_db(raw)` — converts raw level byte to dB float (None = off)
- `db_to_level(db)` — converts dB to raw level byte (None = off)
- `assign_mono()` now defaults level to `LEVEL_UNITY` instead of `LEVEL_OFF`

### Research notes
- Level mapping confirmed from TEST34 (device-generated, 5 known positions):
  min=`0x80` (off), 25%=`0xD8`, 50%=`0xE4`, unity=`0xF5`, max=`0xFF`
  Scale is linear in dB: 52 raw steps span −42 to +10 dB (~1 step per dB)

---

## v0.37 — 2026-04-01

### Fixed
- **Level slider was writing values in the dead zone** — the slider ran from 128 to 255
  (`0x80`..`0xFF`) but the ME-1's active fader range only starts at `0xCB` (203, = −42 dB).
  Values from `0x81`..`0xCA` are below the physical fader minimum and are ignored by the
  device (or produce unexpected behaviour). A user dragging to "25%" of the slider was
  writing `0xA1` = 161, far below the active range; the device expects `0xD8` = 216.
  Fixed: slider now runs from `0xCB` (203, −42 dB) to `0xFF` (255, +10 dB), so
  25% of slider travel = `0xD8` = −29 dB, matching the device exactly.

- **Added "Off" button** next to Unity — sets the level to `0x80` (the sentinel/silent
  value that sits below the active slider range). Off is displayed when a loaded button
  has `level ≤ 0x80`.

### Research notes
- Confirmed from TEST35 (SW) vs TEST36 (device): slider at 25% wrote `0xA1`=161;
  device value for 25% fader is `0xD8`=216. Calibration now matches across all 5 points:
  25%=`0xD8` (−29 dB), max=`0xFF` (+10 dB), unity=`0xF6`/`0xF5` (~0 dB),
  just-under-unity=`0xF0` (−5 dB), +5 dB=`0xFA`.

---

## v0.38 — 2026-04-01

### Fixed
- **All levels saving as Off** — two bugs:
  1. `LEVEL_UNITY = 0xF0` was still present as a duplicate definition later in
     the library, overriding the correct `LEVEL_UNITY = 0xF5` added in v0.36.
     Python uses the last definition, so 0xF0 was being used everywhere.
  2. Two conflicting `input` event listeners were registered on the level slider.
     The `dataset.off` flag (used to distinguish "Off" from an active level) was
     only being cleared in the second handler, which was a duplicate that got
     removed. Now the single `input` handler clears `dataset.off` and updates
     the display label together.

---

## v0.39 — 2026-04-01

### Fixed
- **All levels saving as Off when not explicitly changing the slider** — when a button
  was first clicked (unassigned, level=`0x80`), `renderEditor` set the slider to
  `LEVEL_UNITY` (so it looked correct) but also set `dataset.off = 'true'`. If the
  user then set the type/channel and clicked Apply *without touching the slider*,
  the apply handler read `dataset.off === 'true'` and sent `0x80` (Off) instead of
  the slider's visible value. The slider looked right but the wrong value was saved.

  Fix: `renderEditor` never pre-sets `dataset.off = 'true'`. The Off state is only
  activated by clicking the explicit "Off" button. When loading a button with
  `level = 0x80`, the slider is placed at `LEVEL_UNITY` and `dataset.off` is left
  as `''` — so Apply saves unity unless the user explicitly clicks Off.

---

## v0.40 — 2026-04-01

### Fixed
- **All volumes loading as all-the-way-down on device** — root cause found.
  The device never writes `pan=0x80` for an assigned single-channel button across
  any device-generated file examined. When our software wrote `pan=0x80` (centre),
  the device interpreted it as a sentinel meaning "not configured by console" and
  reset the fader to minimum regardless of the stored level byte.

  The device uses `pan=0x01` as its sentinel for "use console pan" (no override).
  Fix: when pan is set to `0x80` (slider at centre), it is remapped to `0x01`
  before storing — both in the Python server and in the JS apply handler.
  Off-centre pan values are stored as-is. When loading a button with `pan=0x01`,
  the slider is displayed at centre.

  Also fixed: `assign_mono()` default pan changed from `PAN_CENTRE` (0x80) to
  `0x01` to match device behaviour for new buttons.

### Research notes
- Confirmed from device TEST39 and TEST36: no device file ever stores `pan=0x80`
  for an assigned single-channel button. Values like `0x8b`, `0x9f`, `0xc6` appear
  (actual console pan positions) but never exactly `0x80`.
- The pan at `+193` and level at `+192` positions are confirmed correct.
  The "all the way down" symptom was caused entirely by the `pan=0x80` sentinel
  triggering the device's "unconfigured channel" fallback.

---

## v0.41 — 2026-04-02

### Fixed (major — pan and level both corrected)
The per-key record layout was misunderstood. Confirmed from TEST40
(device-generated with 5 known pan positions):

**Correct layout:**
- `+192` = level  (unchanged)
- `+193` = console-sourced pan (physical pan from console; device stores/updates this; we write `0x00`)
- `+194` = ME-1 pan override (user-configurable; `0x25` = centre/passthrough)

**Previous (wrong) layout assumption:**
- `+192` = level
- `+193` = ME-1 pan override ← was writing `0x01` here (sentinel = "not active")
- `+194` = fixed separator `0x25`

Writing `0x01` at `+193` told the device the console had no signal on that
channel, causing the fader to go all the way down regardless of the level byte.

**ME-1 pan scale** (at `+194`): `0x00` = hard left, `0x25` = centre, `0x4A` = hard right.
The value `0x25` (37) was previously mistaken for a fixed separator byte.

**Pan slider** updated: range `0..74` (`0x00..0x4A`), default `37` (`0x25` = centre).

### Research notes
- Confirmed from TEST40: hard left=`0x00`, halfway left=`0x12`, centre=`0x25`,
  halfway right=`0x3b`, hard right=`0x4a`. Linear scale 0-74.
- All previous device files had `+194=0x25` because pan was always at centre.
  The "separator byte" was actually always-centre pan, not a constant.
- TEST40 round-trips with zero diffs after this fix.

---

## v0.42 — 2026-04-02

### Fixed
- **Volume still all the way down (v0.41)** — the `+193` byte (console pan) must be
  **non-zero** for the device to apply the stored level. We were writing `0x00`, and
  while `0x00` occasionally appears in device files, the confirmed pattern across all
  working device files is a non-zero console pan value (`0x9f`, `0x8b`, `0x62`, etc.).
  The device appears to use `0x00` as "hard left console pan" which it may treat as
  "no signal from console" and leave the fader at minimum.

  Fix: `_CONSOLE_PAN_DEFAULT` changed from `0x00` to `0x9F` — the most common value
  across confirmed-working device files (TEST28, TEST36, TEST39, TEST42). Unassigned
  buttons keep `0x01` (the device's inactive-channel sentinel).

### Research notes
- Confirmed from TEST42 (device, works) vs TEST43 (software, broken):
  the only structural differences were level values (different user settings) and
  `+193=0x62/0x9f/0x8b/0x9f` (device) vs `+193=0x00` (software).
- TEST42, TEST43, TEST28, TEST36, TEST39 all round-trip with zero diffs.

---

## v0.43 — 2026-04-02

### Fixed
- **Volume still failing for some buttons (v0.42)** — two related root causes found:

  1. **The ME-1 fader only produces 25 quantised level steps** (not a continuous
     0xCB–0xFF range). Writing any inter-step value (e.g. `0xf9` for +4 dB) causes
     the device to ignore the level entirely. Level bytes now snap to the nearest
     valid step before encoding.

  2. **Each valid level byte has a specific canonical `cpan` (+193) value** that the
     device expects — not arbitrary. For example, `level=0xd6` requires `cpan=0xda`;
     writing `cpan=0x9f` (our previous default) caused the device to ignore that
     button's level. A full lookup table derived from all device-generated files is
     now used to write the correct cpan for each level.

### Technical notes
Valid level bytes (25 steps, derived from device files):
`0xd2 0xd6 0xd8 0xde 0xe0 0xe1 0xe3–0xf2 0xf5 0xf6 0xff`

Notable gaps: `0xf3–0xf4`, `0xf7–0xfe` (between +1 dB and +10 dB — the device
jumps directly from 0xf6 (+1 dB) to 0xff (+10 dB) with no steps between).

---

## v0.44 — 2026-04-02

### Improved — level map expanded from TEST44
TEST44 provided a clean 16-button sweep from off to max, revealing 8 previously
unknown level steps and confirming the full fader range:

**New level steps added:** `0xcf` (−38 dB), `0xd7` (−30), `0xdd` (−24),
`0xf3` (−2), `0xf8` (+3), `0xfb` (+6), `0xfc` (+7), `0xfe` (+9)

**Level map:** now 33 confirmed steps from −38 dB to +10 dB. Notable gaps:
`−38 → −35 → −31 → −30 → −29` (sparse low end), `+1 → +3 → +6 → +7 → +9 → +10`
(no +2, +4, +5, +8 steps exist on the fader).

**Minimum level** updated from `0xCB` to `0xCF` (−38 dB); `0xCF` is the lowest
fader step the device produces. Values below this snap to `0xCF`.

**cpan lookup table** updated with TEST44 values for three conflicting entries
(`0xeb`, `0xef`, `0xf5`). TEST44 round-trips with zero diffs.

---

## v0.45 — 2026-04-02

### Improved — low-end level steps filled in
Second TEST44 sweep (buttons 1-8 at very low fader positions) revealed 5 more
level steps below the previous minimum:

`0xce` (−39 dB), `0xd1` (−36), `0xd3` (−34), `0xd5` (−32), `0xd9` (−28)

Level map now covers **38 steps** from −39 dB to +10 dB. `0xce` (206) is
confirmed as the lowest active fader step — `0x80` remains the off sentinel.
Minimum dB updated from −38 to −39. TEST44 round-trips with zero diffs.

---

## v0.46 — 2026-04-02

### Added
- **Per-channel level and pan for groups** — when a group button is selected, the
  editor now shows a per-channel panel below the channel grid with individual level
  and pan sliders for each member channel. These are written into the slot data
  (`[0x04, level, cpan, pan]` per channel) and round-trip correctly.

### Fixed
- **Group names not showing on device** — `assign_group()` was defaulting to
  `pan=0x00` (hard left) instead of `PAN_CENTRE` (`0x25`). Device group buttons
  always have `+194=0x25`. Fixed default to `PAN_CENTRE`.
- **Per-channel slot data was always written as sentinels** — `assign_group()` was
  ignoring the `per_channel` argument and always writing `[0x04, 0x80, 0x01, 0x25]`
  for every member channel slot. Now correctly writes snapped level, canonical cpan,
  and pan per channel.
- `key_to_dict` now returns `per_channel` data (decoded from slot bytes) so the
  editor can display existing per-channel settings when a saved group is loaded.
- `setGroupChannels` now accepts loaded per-channel data and passes it into the
  per-channel table on render.

### Changed
- **Type pill colour dots** — Single (blue), Group (green), Aux In (purple),
  1kHz Sine (yellow) pills now show a small colour dot matching their pip colour.

---

## v0.47 — 2026-04-02

### Changed
- **Level controls redesigned** — the slider now sits on its own full-width row
  (matching the pan slider layout). The dB value is shown inline in the "Level"
  label. The **Unity** and **Off** buttons are moved below the slider as fixed-width
  pills, styled like the Source Type buttons so they don't shift around when the
  label text changes.
- **Group has no overall pan** — the Pan slider is now hidden when a group button
  is selected. Individual channel pans are set via the per-channel table.
- **Per-channel level/pan rows** — each channel in a group now gets its own
  full-width level slider row and pan slider row (matching the single-channel layout),
  rather than cramped inline controls.
- **Removed the "Approximate" warning** from the level section — the dB mapping
  is now fully confirmed from hardware data.

---

## v0.48 — 2026-04-02

### Fixed
- **Unity/Off buttons were deselecting the Source Type and closing controls** —
  they used `class="type-pill"` which was caught by the source-type `forEach`
  click handler, resetting `editorType` to `undefined`. Renamed to `class="level-pill"`
  with identical visual styling but no type-switching behaviour.

### Added
- **Unity, Off, and Centre buttons per channel in groups** — each channel in a
  group's per-channel panel now has **Unity** and **Off** shortcut buttons below its
  level slider, and a **Centre** button below its pan slider. These use a delegated
  click handler on the table container so they work correctly for dynamically
  rendered rows.

---

## v0.49 — 2026-04-02

### Changed
- **Per-channel pan row matches single-channel layout** — the pan row in a group's
  per-channel panel now uses the same compact format as the single-channel pan:
  `[L] [slider] [R] [value] [Ctr]`, all on one line. The separate "Centre" button
  row is removed; Ctr sits inline on the right.
- **Bold section divider between per-channel panel and group label** — a 3px
  horizontal rule separates the individual-channel section from the Label and Apply
  controls below it, making the group editor visually cleaner. Thicker than the thin
  `1px` bars between each channel.

### Future work noted (not yet implemented)
- Persistent config storage / save slots
- Updated hardware image
- EQ and limiter controls (requires Master button testing)
- Group name display fix (on-device)
- Config name prominence
- App rename to "ME-OLE" (ME-Offline Editor)
- Multi-channel volume/pan interaction rules

---

## v0.50 — 2026-04-02

### Changed
- **Off/Unity button order swapped** — Off is now on the left, Unity on the right,
  for both the main level controls and per-channel group controls. Left-to-right
  reads low→high, matching the slider direction.
- **Removed "C" value display next to Ctr button** — both single-channel pan and
  per-channel group pan no longer show the redundant "C" label. The Ctr button
  is sufficient. (The hidden span is kept in the DOM for JS compatibility.)
- **Per-channel Ctr button now matches single-channel size** — uses `btn-center-pan`
  class directly rather than the wider `level-pill` override.

---

## v0.51 — 2026-04-02

### Fixed
- **Pressing Off then Apply reset level back to Unity** — `renderEditor` always
  cleared `dataset.off = ''` after an apply, so the Off state was lost on the
  next render. Now: if a saved button is assigned with `level = 0x80` (explicitly
  Off), `renderEditor` restores `dataset.off = 'true'` and shows "Off". Unassigned
  buttons (which also have `level = 0x80` as a default) still default to Unity so
  typing a channel number works naturally.

---

## v0.52 — 2026-04-02

### Fixed
- **"pan" error when saving a group** — `chPanLevel[ch]` is built incrementally
  in JS (one key at a time as sliders are moved), so a channel entry may have
  only `level` or only `pan` set. The dict comprehension used `v['level']` and
  `v['pan']` (hard key access), raising `KeyError: 'pan'` whenever a level slider
  was moved without touching the pan slider. Fixed to `v.get('level', LEVEL_UNITY)`
  and `v.get('pan', PAN_CENTRE)`.

---

## v0.53 — 2026-04-02

### Fixed
- **Per-channel Off resets to Unity on re-apply** — same class of bug as v0.51.
  `buildChPanLevelTable` was converting `level=0x80` to `LEVEL_UNITY` for display,
  so when the user applied again the slider was at Unity and that value was sent.
  Fix: the level slider now carries `data-off="true"` when built from an off state,
  the Off button sets it, the Unity button and slider drag both clear it, and the
  apply handler reads `data-off` from the DOM slider (not just `chPanLevel`) to
  decide whether to send `0x80` or the slider value.

---

## v0.54 — 2026-04-03

### Changed
- **New hardware image** — replaced the placeholder image with the ME-OLE branded
  image (1920×1080, 16:9). Button overlay positions recalculated from pixel
  measurements of the new image.
  - Row 1 (btns 1–8): y=55.6%
  - Row 2 (btns 9–16): y=75.3%
  - X centres: 25.26%, 31.98%, 38.70%, 45.47%, 52.40%, 59.38%, 66.35%, 73.33%
  - Button overlay size: 5.0% × 5.8%

### Added
- **Master button overlay** — invisible clickable overlay positioned over the
  Master button in the upper-right of the hardware image (x=69.74%, y=27.6%).
  Highlights amber on hover. Currently shows a "coming soon" toast. Will be
  wired to EQ and limiter controls in a future version.

---

## v0.55 — 2026-04-03

### Fixed
- **v0.54 broke the GUI** — the new `me1.png` file was copied to the docker
  folder but the image is embedded as a base64 data URI at build time, not
  served from disk at runtime. The old JPEG data URI was still in the Python
  source. Re-embedded the new PNG correctly.

---

## v0.56 — 2026-04-03

### Fixed
- **v0.55 — new image loaded but buttons and presets didn't render** — all edits
  in v0.54 (aspect-ratio, BTN_POSITIONS, Master button HTML, button overlay size)
  used slightly wrong source strings and failed silently, leaving the template
  unchanged. Root cause: the old BTN_POSITIONS had `20.55` not `20.53` for btn1 x,
  and the img alt text had a literal `&` not `&amp;`. Fixed by reading the exact
  template strings before replacing. All four changes now verified to be inside
  the HTML template.

---

## v0.57 — 2026-04-03

### Added — Saved Configs
- **"Saved Configs" button** in the topbar opens a modal showing all configs
  saved to persistent storage.
- **Save Current** — saves the active config to the volume under the current
  filename (or a custom name). Configs are written to `/data/configs` in the
  container, mounted as a named Docker volume `me1_configs`.
- **Open** — loads a saved config into the editor directly from the modal.
- **Download (↓)** — downloads a saved config as a `.ME1` file.
- **Delete (✕)** — removes a saved config with a confirmation prompt.
- Docker volume `me1_configs` added to both `docker-compose.yml` and
  `docker-compose.hub.yml`. The `Dockerfile` now declares `VOLUME ["/data/configs"]`.
  Configs survive container restarts and upgrades.

### Added — Master EQ & Limiter panel
- **Master button** on the hardware image now has a persistent amber pip and
  highlight (was fully invisible before). Clicking it opens the EQ & Limiter
  panel in place of the Button Editor.
- **Parametric EQ** with three bands:
  - **Lo** — fixed frequency, gain −12 to +12 dB in 1 dB steps
  - **Mid** — selectable frequency (200 Hz to 5k0 in 16 steps), same gain range
  - **Hi** — fixed frequency, same gain range
- **Live EQ graph** — canvas-drawn frequency response curve updates in real time
  as bands are adjusted. Includes log-scale frequency grid, zero line, and
  coloured band markers.
- **Limiter** — vertical slider 0–24. Fills left-to-right with a gradient
  (blue → green → amber → red).
- Panel closes via ✕ and restores the Button Editor.
- EQ values are UI-only for now — hardware byte mapping TBD. An info notice
  in the panel makes this clear.

---

## v0.58 — 2026-04-03

### Fixed
- **PermissionError on startup in Docker** — `appuser` (non-root) couldn't
  create `/app/configs`. Two fixes:
  1. `STORAGE_DIR` default reverted to `/data/configs` (the Docker volume mount
     path, not a subdirectory of `/app` which is owned by root).
  2. Dockerfile now creates `appuser` first, then `mkdir -p /data/configs &&
     chown -R appuser:appuser /data` — so the directory exists with correct
     ownership before the container starts.

---

## v0.59 — 2026-04-03

### Fixed
- **Master button was invisible and not clickable** — `buildHwButtons()` used
  `querySelectorAll('.hw-btn')` to clear old overlays, which removed the
  `#master-btn` element too (it also has class `hw-btn`). It was never
  re-added because it's static HTML, not part of the BTN_POSITIONS loop.
  Fixed selector to `.hw-btn:not(#master-btn)` so the master button is
  preserved on every render.

---

## v0.59a — 2026-04-03

### Changed
- **Docker volume changed from named to bind mount** — both compose files now
  use `./configs:/data/configs` (a `configs/` folder next to the compose file)
  instead of a Docker-managed named volume. This lets you see and control
  exactly where configs are stored on the host. To use a different path, just
  change the left side, e.g. `- /home/yourname/me1-configs:/data/configs`.
  The `volumes:` block at the bottom of both files has been removed.

---

## v0.60 — 2026-04-03

### Changed — App renamed to ME-OLE
- Page title: **ME-OLE — ME Offline Editor**
- Topbar logo: **ME-OLE** / Offline Editor
- Docker image labels updated to ME-OLE
- Startup console message updated

### Changed — UI close buttons
- **EQ/Master panel** close ✕ moved to the right side of the header
- **Button Editor** now has a ✕ close button on the right side of its header
  — clicking it deselects the active button (same as clicking it again on
  the hardware image)
- Both headers use `display:flex` with a spacer so the ✕ always sits flush right

### Changed — Master button toggles panel
- Clicking the **Master** button when the EQ panel is already open now closes
  it, rather than doing nothing. Click to open, click again to close.

---

## v0.61 — 2026-04-03

### Added
- **Config name displayed inside the device screen** — a static "Config:" label
  in the top-left of the black screen area, with the current config filename
  below it in large font. Both in yellow (`#ffd54f`). Updates whenever a file
  is opened, loaded from saved configs, created new, or renamed in the topbar.

### Changed
- **Docker service/image/container renamed** from `me1-editor` to `me-ole`
  in both compose files and `build.sh`
- **Default volume folder renamed** from `./configs` to `./me1-configs` in
  both compose files (rename your existing folder on the host to match, or
  update the path in the compose file)

---

## v0.62 — 2026-04-03

### Fixed
- **Config name overlay not scaling with the image** — font sizes were in `vw`
  (viewport width), which stays fixed as the hardware image container resizes.
  Switched to `cqw` (container query width) by adding `container-type: inline-size`
  to `.hw-img-container`. Font sizes are now `1.4cqw` (label) and `3.2cqw` (name),
  scaling proportionally with the image at any viewport size.

---

## v0.63 — 2026-04-03

### Fixed
- **v0.62 broke the layout** — `container-type: inline-size` on `.hw-img-container`
  disrupts how the element participates in flex layout, causing the image to
  collapse and only one button to appear. Removed entirely.
- **Config name overlay scaling** — switched from `cqw` units to a CSS custom
  property `--img-w` (set in pixels by a `ResizeObserver` on the container).
  Font sizes use `calc(var(--img-w) * 0.014)` / `calc(var(--img-w) * 0.032)`,
  so they scale proportionally with the actual rendered container width
  without needing container queries.

---

## v0.64 — 2026-04-03

### Changed
- **Config name moved from device screen overlay to topbar** — the on-image
  overlay is removed entirely. The config name now lives on the right side of
  the topbar as a prominent two-line block: a small "CONFIG" label above, and
  the filename in large yellow `Barlow Condensed` (18px, uppercase). A subtle
  yellow left border separates it from the rest of the topbar. Still editable
  by clicking. Scales correctly at any window size.

---

## v0.65 — 2026-04-03

### Added — Channel level/pan constraints
The ME-1 enforces that a channel's level and pan are global — if CH1 is on
two buttons (or in a group and a single), both must have the same values.

- **Auto-sync on Apply** — if you save a button using a channel that's already
  assigned elsewhere in the preset, the level and pan are automatically synced
  to the existing values. The sliders update in the UI and a toast explains
  what was synced.
- **Conflict hint** — when you type a channel number into the single-channel
  field that's already in use elsewhere, an amber notice appears: *"CH1 is used
  on another button — level & pan will stay in sync."*
- Same enforcement applies to individual channels within groups.
- Groups still block shared channels across multiple groups (existing behaviour).

---

## v0.66 — 2026-04-03

### Changed — Toast notifications redesigned
- **Position:** moved from bottom-centre to **top-centre**, just below the topbar
- **Size:** larger font (15px, semibold), more padding, minimum width 260px,
  drop shadow for contrast against the hardware image
- **Duration:** extended from 2.8s to **5 seconds**
- **Close button:** ✕ on the right side of each toast — click to dismiss immediately
- **Fade animation:** now fades in/out with opacity in addition to sliding,
  for a cleaner appearance
- Added `.toast.info` style (blue) for informational messages

---

## v0.67 — 2026-04-03

### Fixed — Group names now display on device

Root cause: the group button's own flag byte (+203) was always `0x20`, but
the device uses different values:

| Case | Correct flag | Was written |
|------|-------------|-------------|
| Custom name (e.g. "Band") | `0x00` | `0x20` ✗ |
| Default name (blank label) | `0x30` | `0x20` ✗ |

`0x20` belongs on the **preceding** button as a signal that the next button
is a group — not on the group button itself. Writing it on the group button
caused the device to misread or ignore the label.

Also fixed: blk2 (live copy slot) `header[7]` and group flags now mirror blk0
correctly (`0x30→0x20` in live copy, `header[7]` copied from blk0).

TEST51 round-trips with 0 non-cpan diffs. ✓

### Added — "Use device default name" option for groups
A **"Use device default (Grp1, Grp2…)"** checkbox appears in the Label section
when Group type is selected. Checking it clears and disables the label input and
sends a blank label, which causes the device to auto-assign its own sequential
name ("Grp1", "Grp2", etc.). The checkbox state is restored when loading a saved
group with a blank label.

---

## v0.68 — 2026-04-03

### Fixed — Group names (v0.67 incomplete)

v0.67 fixed the flag for LAST groups but missed consecutive groups.
Full rule (confirmed from TEST21 and TEST51):

| Case | Flag |
|------|------|
| Group with a following group (chain) | `0x20` |
| Last group, custom name | `0x00` |
| Last group, blank/default name | `0x30` |

The preceding NON-group button still gets `0x20`. Groups in a chain carry
the signal in their own flag instead.

TEST52 (`Vox` + `Band1`): Btn1 now gets `0x20` (chain), Btn2 gets `0x00` ✓

### Fixed
- **"Label required" error when using default name checkbox** — validation
  now checks whether the default-name checkbox is ticked before blocking.
  Error message updated to "Enter a group label or use the default name".

---

## v0.69 — 2026-04-03

### Fixed — Group names (again, confirmed from TEST53 device file)

Two more bugs found by diffing TEST53 (device) against TEST54 (v0.68 software):

**1. Label padding wrong** — device pads labels to **7 chars + 1 null** (`"Band   \x00"`),
not 6 chars + 2 nulls. `_encode_label` updated to match. This affected ALL group and
single-channel labels, which may have been the primary reason names didn't display.

**2. Group chain flag wrong** — device uses `0x30` for ALL non-last groups in a chain
(regardless of whether the name is custom or default), not `0x20`. Updated rule:
- Non-last group (has following group) → `0x30`
- Last group, custom name → `0x00`
- Last group, blank/default name → `0x30`

TEST53 now round-trips with **0 non-cpan diffs**. ✓

---

## v0.70 — 2026-04-04

### Added — EQ fully wired to device

Mid frequency lookup table confirmed from 18 device-generated test files
(EQ1–EQ17 covering all 16 frequencies, EQ18 confirming gain independence).

**Confirmed EQ byte positions in the 807-byte preset tail:**
- `tail+9`  = Lo gain (signed byte, −12 to +12)
- `tail+20` = Mid gain (signed byte, −12 to +12)
- `tail+24,25` = Mid frequency (2-byte lookup, 16 values)
- `tail+31` = Hi gain (signed byte, −12 to +12)

Freq and gain bytes are **completely independent** — confirmed by EQ18
(3k4 at gain=+6 has identical freq bytes to EQ11 at gain=0).

**New `/api/update-eq` route** — writes Lo/Mid/Hi gain and Mid freq into the
active preset's tail bytes and returns `{"ok": true}`.

**EQ state loaded on file open** — when a `.ME1` file is opened (upload,
load from saved, or initial load), the EQ sliders and freq dropdown are
populated from the file's tail bytes.

**"Hardware mapping TBD" notice removed** — EQ is now fully confirmed.

---

## v0.71 — 2026-04-04

### Fixed
- **Pressing Enter in the config name added a newline** — `contenteditable` spans
  don't always respect `preventDefault()` alone for Enter. Added `stopPropagation()`
  and an explicit `clean()` call before `blur()` so Enter now saves and exits
  the field cleanly without inserting a line break.

---

## v0.72 — 2026-04-04

### Fixed — Config name Enter key (properly this time)
- Changed `contenteditable="true"` to `contenteditable="plaintext-only"` on
  the filename span — this blocks multiline input natively in modern browsers.
- Added `beforeinput` handler that intercepts `insertParagraph` and
  `insertLineBreak` events before the browser inserts them, then cleans
  and blurs the field.
- Added `input` handler that strips any stray newlines that slip through
  in older browsers as a fallback.
- Together these three layers ensure Enter always saves and exits cleanly.

---

## v0.73 — 2026-04-04

### Added — Limiter fully wired to device

Confirmed from 10 device-generated files (LIM1–LIM10). No duplicates.

**Limiter byte: `tail+42` (signed byte)**
- Position 1 (Off): `0x00` = 0 dBFS
- Each step: −3 dBFS (encoded as `step × −3` as a signed byte)
- Position 10 (full): `0xe5` = −27 dBFS

**Slider updated:** range changed from 0–24 (placeholder) to 0–9.
Display shows "Off" at 0, "−3 dB" through "−27 dB" for steps 1–9.
Limiter value is included in Apply EQ & Limiter and loaded from file on open.

---

## v0.74 — 2026-04-04

### Fixed — Config name Enter key (definitive fix)
Replaced the `contenteditable` span with a plain `<input type="text">`.
`contenteditable` has unavoidable cross-browser inconsistencies with Enter
key handling regardless of how many event layers are added. A real input
element handles Enter, Escape, blur, and the clean/format logic reliably
with a simple two-handler setup.

---

## v0.75 — 2026-04-04

### Fixed — Config name reformatting and download filename

Two bugs found:

1. **`clean()` used case-sensitive extension removal** — `text.replace('.ME1','')`
   doesn't match `'band.me1'` or `'Band.ME1'`, so lowercase filenames from
   the device would have `me1` embedded in the name (e.g. `BANDME1.ME1`).
   Fixed to `/\.ME1$/i` (case-insensitive, end-of-string anchor).

2. **Download used stale filename** — clicking Download while the name field
   was focused would navigate away before the blur event fired the rename API,
   so the server still had the old name. The download handler now explicitly
   calls `/api/rename` with the current input value before triggering the download.

---

## v0.76 — 2026-04-04

### Fixed — Config name Enter key (again)
The Enter handler now applies `clean()` and sends `/api/rename` immediately
and synchronously, then defers `el.blur()` via `setTimeout(0)`. Previously,
calling `el.blur()` inline caused some browsers to fire the blur handler
before the visual update, so the reformatted value wasn't visible. The blur
handler still also cleans and renames on normal focus-loss (e.g. clicking away).

---

## v0.77 — 2026-04-04

### Fixed — Config name reformatting now visible
Removed `text-transform: uppercase` from the config name input. The CSS
transform was making lowercase input look uppercase while typing, so pressing
Enter appeared to do nothing even though `clean()` was running correctly.
Now the field shows whatever case you type, and Enter visibly reformats it
to uppercase, strips special characters, and adds `.ME1`.

---

## v0.78 — 2026-04-04

### Fixed — Config name Enter/blur handling (definitive)
Moved clean-and-rename logic from a separate `addEventListener` setup block
to inline `onchange` and `onkeydown` attributes directly on the input element.
This eliminates any possible issue with listener attachment timing or scope.
- `onchange`: fires when value changes and focus leaves — cleans the value
  and calls `/api/rename`
- `onkeydown`: Enter key dispatches a `change` event then blurs, triggering
  the same clean-and-rename path

---

## v0.79 — 2026-04-04

### Changed
- Right sidebar (Button Editor and EQ/Limiter panel) widened from 340px to 400px.
