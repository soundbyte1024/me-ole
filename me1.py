# -*- coding: utf-8 -*-
"""
me1.py  -  Allen & Heath ME-1 Config File Library
================================================
Read, modify, and write .ME1 config files for the Allen & Heath ME-1
personal monitor mixer.

QUICK START
-----------

Load an existing config and change some assignments::

    from me1 import ME1Config, PAN_CENTRE, PAN_LEFT, PAN_RIGHT, LEVEL_UNITY

    cfg = ME1Config.load("MECFG.ME1")

    p = cfg.preset("BAND")      # get preset by name
    # or: p = cfg.presets[0]    # get by index (0 = Preset 1)

    p.keys[0].assign_mono(src_ch=1,  label="Kick",  pan=PAN_CENTRE)
    p.keys[1].assign_mono(src_ch=2,  label="Snare", pan=PAN_CENTRE)
    p.keys[2].assign_stereo(src_ch=3, label="OH",   pan=PAN_CENTRE)
    p.keys[3].assign_unassigned()

    cfg.save("MECFG_MODIFIED.ME1")

Build a config from scratch::

    cfg = ME1Config()
    p = cfg.presets[0]
    p.name = "MECFG"
    p.keys[0].assign_mono(src_ch=1, label="Kick")
    p.keys[1].assign_mono(src_ch=2, label="Snare")
    cfg.save("MECFG.ME1")

KEY ASSIGNMENT METHODS
----------------------
  key.assign_mono(src_ch, label, pan, level)
      Single input from the console. src_ch = 1-40.

  key.assign_stereo(src_ch, label, pan, level)
      Stereo linked pair. Right channel = src_ch + 1. src_ch must be 1-39.

  key.assign_unassigned(label, pan)
      No source  -  key appears blank on the device.

  key.assign_group(...)
      NOT YET IMPLEMENTED. Group encoding not confirmed from hardware.
      See assign_group() for details on how to help unlock this.

"""

from __future__ import annotations

__version__ = "0.93"

import os
from typing import List, Optional


# ── Level and Pan constants ─────────────────────────────────────────────────
LEVEL_OFF   = 0x80    # Fader fully off / sentinel (below active range)
LEVEL_UNITY = 0xF5    # 0 dB (unity gain)  -  confirmed from TEST34
_LEVEL_ACTIVE_MIN = 0xCE   # Minimum active fader position (-39 dB, confirmed from TEST44)
_LEVEL_ACTIVE_MAX = 0xFF   # Maximum fader position (+10 dB)
_DB_MIN = -39.0            # dB at _LEVEL_ACTIVE_MIN (0xCE)
_DB_MAX =  10.0            # dB at _LEVEL_ACTIVE_MAX

def level_to_db(raw: int):
    """Convert a raw level byte to dB. Returns None for off/silent."""
    if raw <= LEVEL_OFF:
        return None
    t = max(0.0, min(1.0, (raw - _LEVEL_ACTIVE_MIN) / (_LEVEL_ACTIVE_MAX - _LEVEL_ACTIVE_MIN)))
    return round(_DB_MIN + t * (_DB_MAX - _DB_MIN), 1)

def db_to_level(db) -> int:
    """Convert a dB value to a raw level byte. Pass None for off/silent."""
    if db is None:
        return LEVEL_OFF
    t = max(0.0, min(1.0, (float(db) - _DB_MIN) / (_DB_MAX - _DB_MIN)))
    return round(_LEVEL_ACTIVE_MIN + t * (_LEVEL_ACTIVE_MAX - _LEVEL_ACTIVE_MIN))


# ── File layout constants ─────────────────────────────────────────────────────

_SLOT    = 4096                          # bytes per preset slot
_TOTAL   = 73728                         # full config file size (18 x 4096)
_NSLOTS  = _TOTAL // _SLOT               # 18 slots total
_NPRESETS = 16                           # usable preset slots

# Preset i (0-indexed) lives at:  _preset_offset(i)
def _preset_offset(i: int) -> int:
    # File layout (18 × 4096-byte slots), confirmed from TEST60 + TEST68 device testing:
    #   slot  0 = Preset 1 boot/display copy (shown on load; device reads this for boot state)
    #   slot  1 = Name table
    #   slot  2 = Preset 1 button slot (device loads this when user presses button 1)
    #   slot  3 = Preset 2 button slot (device loads this when user presses button 2)
    #   slot  4 = Preset 3 button slot
    #   ...
    #   slot 17 = Preset 16 button slot
    # Device behaviour: button N → slot(N+1). Slot0 is boot/display only.
    # For correct operation: slot0 = slot2 = P1 data (boot shows P1, button 1 loads P1).
    if i == 0: return 0
    return (i + 2) * _SLOT   # P1→slot2(i=0 special), P2→slot3, P3→slot4 … P16→slot17

_NAME_TABLE_OFFSET = _SLOT               # 0x01000
_NAME_TABLE_ENTRY  = 10

# ── Key record constants ──────────────────────────────────────────────────────

_HEADER     = bytes([0x1d, 0x1c, 0x02, 0x00, 0x00, 0x0c, 0xda, 0x00, 0x00])  # byte7=0x00 matches device-exported files
# Default trailing EQ/config data for new presets. Present in all device-generated
# files starting with signature 5538cf01. Without it the device may ignore the preset.
_DEFAULT_TAIL = (
    bytes.fromhex('5538cf010000002d'            # signature
                  '0100000000539600000200000000'  # EQ band 1 (flat)
                  '000099e90000020002'            # EQ band 2 (flat)
                  '00000000b92d000002000000'      # EQ band 3 (flat)
                  '0054df0000'                    # EQ band 4 (flat)
                  ) + b'\x00' * 757              # rest is zeros (807 bytes total)
)
_SLOT_DEF   = bytes([0x00, 0x80, 0x01, 0x25])   # default slot entry
_NSLOTS_KEY = 48                                  # slot entries per key
_SLOT_BYTES = _NSLOTS_KEY * 4                     # 192
_SEP        = 0x25
_STRIDE     = 205                                 # bytes from sep to sep
_NKEYS      = 16
_KEY_DATA_SIZE = len(_HEADER) + _NKEYS * _STRIDE  # 3289 bytes of actual key data

# Offset of key 0's separator within a preset block
_SEP0 = len(_HEADER) + _SLOT_BYTES + 2           # = 203 = 0xCB

# ── Level / pan constants (public) ───────────────────────────────────────────

LEVEL_OFF   = 0x80   # Fader at minimum (ME-1 zero point  -  what device stores for 'off')   # Fader fully down / silent
_LEVEL_UNSET = 0x80  # Device sentinel for unconfigured keys (not a real level)

# ME-1 pan override stored at +194 in the key record
# Range: 0x00 (hard left) to 0x4A (hard right), centre = 0x25
# Confirmed from TEST40 (device-generated with known pan positions)
PAN_LEFT   = 0x00   # Hard left
PAN_CENTRE = 0x25   # Centre (default / passthrough)
PAN_RIGHT  = 0x4A   # Hard right
_PAN_MIN   = 0x00
_PAN_MAX   = 0x4A
# Console pan stored at +193. Must match the canonical value for the level.
# Derived from all device-generated files.
_CONSOLE_PAN_DEFAULT = 0x9F  # fallback only

# Valid level bytes — the ME-1 fader only lands on these quantised steps.
# Writing any other value causes the device to ignore the level.
# Derived from scanning all device-generated files.
_VALID_LEVELS = [
    # Confirmed from device files — TEST44 provides full-range sweep
    0xce,0xcf,0xd1,0xd2,0xd3,0xd5,0xd6,0xd7,0xd8,0xd9,0xdd,0xde,0xe0,0xe1,0xe3,0xe4,0xe5,0xe6,0xe7,0xe8,0xe9,0xea,0xeb,0xec,0xed,0xee,0xef,0xf0,0xf1,0xf2,0xf3,0xf5,0xf6,0xf8,0xfb,0xfc,0xfe,0xff,
]

# Canonical cpan (+193) for each valid level byte.
# Derived from the most common cpan value observed for each level across
# all device-generated files. The cpan must match for the device to apply level.
_LEVEL_CPAN = {
    # Canonical cpan per level, from device files (TEST44 full-range sweep)
    0xce:0x00, 0xcf:0xec, 0xd1:0x76, 0xd2:0x9f, 0xd3:0xc6,
    0xd5:0x50, 0xd6:0xda, 0xd7:0x9f, 0xd8:0x00, 0xd9:0x27,
    0xdd:0x62, 0xde:0x8b, 0xe0:0x76, 0xe1:0x3b, 0xe3:0x27,
    0xe4:0x50, 0xe5:0x76, 0xe6:0x9f, 0xe7:0x62, 0xe8:0x27,
    0xe9:0x80, 0xea:0xda, 0xeb:0x9f, 0xec:0x62, 0xed:0x8b,
    0xee:0x50, 0xef:0x15, 0xf0:0x80, 0xf1:0x00, 0xf2:0x8b,
    0xf3:0x50, 0xf5:0x3b, 0xf6:0x62, 0xf8:0xb1, 0xfb:0x62,
    0xfc:0xec, 0xfe:0x15, 0xff:0x9f,
}

def snap_level(raw: int) -> int:
    """Snap a raw level byte to the nearest valid device level step.
    The ME-1 fader only produces quantised level values; writing an
    inter-step value causes the device to ignore the level entirely."""
    if raw <= LEVEL_OFF:
        return LEVEL_OFF
    return min(_VALID_LEVELS, key=lambda v: abs(v - raw))


SRC_NONE   = 0xFF    # Unassigned source
SRC_AUXIN  = 0x28    # Aux Input (3.5mm jack on rear of unit): ch_field=0x28
SRC_SINE   = 0x2F    # 1 kHz sine wave test tone: ch_field=0x2F

# ── Flag byte values ──────────────────────────────────────────────────────────

_FLAG_MONO       = 0x00
_FLAG_STEREO     = 0x10   # Stereo pair; right = src_ch + 1
_FLAG_GROUP      = 0xFF   # Internal sentinel: group key (detected via slot data, not a real on-disk flag)
_FLAG_AUTO       = 0x40   # AUTO MODE: device assigns channel automatically from console routing;
                              #             src_ch byte is ignored by the device.
_FLAG_SPECIAL    = 0x01   # Special source (personal mix bus, etc.)
_FLAG_GROUP_ALT  = 0x20   # Preceding-button flag: signals next button is a group
_FLAG_GROUP_DEFAULT = 0x30 # Group own flag when using device default name (0x20|0x10)
_FLAG_UNASSIGNED = 0x30   # No source; src_ch should be 0xFF

# ── Label encoding ────────────────────────────────────────────────────────────

def _encode_label(text: str) -> bytes:
    """
    Encode a label string into the 8-byte on-disk field.
    Matches the format written by the device:
      Named:  up to 6 chars, space-padded to 7, then 0x00
      Blank:  0x00 + 6 spaces + 0x00
    """
    if not text:
        return b'\x00' + b' ' * 6 + b'\x00'
    b = text[:6].encode('ascii', errors='replace')
    return b.ljust(7, b' ') + b'\x00'

def _decode_label(raw: bytes) -> str:
    """Decode the 8-byte on-disk label field into a display string."""
    return raw.strip(b'\x00 ').decode('ascii', errors='replace')


# ── Key ───────────────────────────────────────────────────────────────────────

class Key:
    """
    One of the 16 assignable buttons on the ME-1 front panel.

    Do not create these directly  -  they live inside a Preset.
    Use the assign_* methods to set or change the assignment.

    Attributes:
        label  (str):   Text shown on the button (max 6 chars visible on device).
        src_ch (int):   Console input number (1-40), or SRC_NONE if unassigned.
        pan    (int):   Pan byte. Use PAN_LEFT / PAN_CENTRE / PAN_RIGHT, or 0x00-0xFF.
        level  (int):   Level byte. LEVEL_OFF = fader down, LEVEL_UNITY ~ 0 dB.
        slots  (bytes): Raw 192-byte EQ / extended data. Preserved on round-trip.
    """

    def __init__(self):
        self._raw_label:    bytes = b'\x00' + b' ' * 5 + b'\x00\x00'
        self._flag:         int   = _FLAG_UNASSIGNED
        self.src_ch:        int   = SRC_NONE
        self._raw_ch_field: int   = 0x22  # raw +204 byte; 0x22 required by device for last key
        self.level:      int   = _LEVEL_UNSET
        self.pan:        int   = PAN_CENTRE      # default: centre (0x25)
        self.slots:      bytes = _SLOT_DEF * _NSLOTS_KEY
        self._group_channels: list = []
        self._console_pan:    int   = _CONSOLE_PAN_DEFAULT  # +193: console pan
        self._disk_flag:      int   = _FLAG_MONO         # device uses 0x00 for blank buttons

    # ── label property ────────────────────────────────────────────────────────

    @property
    def label(self) -> str:
        return _decode_label(self._raw_label)

    @label.setter
    def label(self, value: str) -> None:
        self._raw_label = _encode_label(value)

    # ── Assignment methods ─────────────────────────────────────────────────────

    def assign_mono(self, src_ch: int, label: str = '',
                    pan: int = PAN_CENTRE, level: int = LEVEL_UNITY) -> 'Key':
        """
        Assign a single mono console input to this button.

        Args:
            src_ch: Input channel number, 1-40.
            label:  Button label (max 6 chars shown on device screen).
            pan:    Pan position. PAN_LEFT / PAN_CENTRE / PAN_RIGHT or raw 0x00-0xFF.
            level:  Level byte. LEVEL_OFF (default) = fader fully down / silent.
                    Use LEVEL_UNITY (~0xF0) to start at approximate unity gain.

        Returns:
            self  (so you can chain: key.assign_mono(1).level = LEVEL_UNITY)
        """
        _validate_ch(src_ch)
        self._raw_label = _encode_label(label)
        self._flag      = _FLAG_MONO
        self._disk_flag = _FLAG_MONO   # device uses 0x00 for single-channel buttons
        self.src_ch     = src_ch
        self.level      = level
        self.pan        = pan
        return self

    def assign_stereo(self, src_ch: int, label: str = '',
                      pan: int = PAN_CENTRE, level: int = LEVEL_UNITY) -> 'Key':
        """
        Assign a stereo linked pair to this button.

        The device treats src_ch as the left channel and src_ch+1 as the right.

        Args:
            src_ch:  Left input channel, 1-39.  (right = src_ch + 1)
            label:   Button label (max 6 chars).
            pan:     Pan position.
            level:   Level byte.

        Returns:
            self
        """
        if not (1 <= src_ch <= 39):
            raise ValueError(f"Stereo src_ch must be 1-39 (right = src_ch+1), got {src_ch}")
        self._raw_label = _encode_label(label)
        self._flag  = _FLAG_STEREO
        self.src_ch = src_ch
        self.level  = level
        self.pan    = pan
        return self

    def assign_auto(self) -> 'Key':
        """
        Set this button to AUTO MODE (flag=0x40).

        In auto mode the ME-1 device assigns the source channel automatically
        from the console's routing. The src_ch field is ignored by the firmware.
        Auto mode is the factory default for all buttons and is set by the console
        when it configures the ME-1 remotely.

        Returns:
            self
        """
        self._raw_label = _encode_label('')
        self._flag      = _FLAG_AUTO
        self._disk_flag = _FLAG_AUTO
        self.src_ch     = 0x01     # placeholder; ignored by device in auto mode
        self.level      = _LEVEL_UNSET
        self.pan        = 0x01
        self.slots      = bytes(_SLOT_DEF * _NSLOTS_KEY)
        self._group_channels = []
        return self

    def assign_unassigned(self, label: str = '', pan: int = PAN_CENTRE) -> 'Key':
        """
        Mark this button as unassigned (blank, no source).

        Args:
            label: Optional label to show on the blank button.
            pan:   Pan value to retain. The device stores pan even for blank buttons.

        Returns:
            self
        """
        self._raw_label      = _encode_label(label)
        self._flag           = _FLAG_UNASSIGNED
        self._disk_flag      = _FLAG_MONO   # device uses 0x00 for blank buttons, not 0x30
        self.src_ch          = SRC_NONE
        self.level           = _LEVEL_UNSET
        self.pan             = 0x01         # device sentinel for unset pan
        self._console_pan    = 0x01         # device sentinel for inactive channel
        self.slots           = bytes(_SLOT_DEF * _NSLOTS_KEY)  # clear all slot data
        self._group_channels = []
        return self

    def assign_auxin(self, level: int = LEVEL_OFF) -> 'Key':
        """Assign this button to the Aux Input (3.5mm rear jack).
        The device auto-labels the button 'AuxIn'."""
        self._flag           = _FLAG_GROUP_ALT   # internal marker (0x20)
        self._disk_flag      = _FLAG_MONO        # 0x00 on disk  -  flag=0x20 on AuxIn button
                                                 # corrupts the NEXT button's routing
        self.src_ch          = SRC_AUXIN + 1     # store as 1-indexed internally
        self.level           = level
        self.pan             = 0x01              # sentinel
        self._raw_label      = bytes(8)          # device assigns label automatically
        self._group_channels = []
        self.slots           = bytes(_SLOT_DEF * _NSLOTS_KEY)
        return self

    def assign_sine(self, level: int = LEVEL_OFF) -> 'Key':
        """Assign this button to the 1 kHz sine wave test tone.
        The device auto-labels the button '1kSine'."""
        self._flag           = _FLAG_MONO        # 0x00  -  device writes this for 1kSine
        self._disk_flag      = _FLAG_MONO
        self.src_ch          = SRC_SINE + 1      # store as 1-indexed internally
        self.level           = level
        self.pan             = 0x01              # sentinel
        self._raw_label      = bytes(8)          # device assigns label automatically
        self._group_channels = []
        self.slots           = bytes(_SLOT_DEF * _NSLOTS_KEY)
        return self

    def is_auxin(self) -> bool:
        """True if this button is assigned to the Aux Input."""
        return self.src_ch == SRC_AUXIN + 1

    def is_sine(self) -> bool:
        """True if this button is assigned to the 1 kHz sine wave."""
        return self.src_ch == SRC_SINE + 1


    def assign_group(self, channels: list, label: str = '',
                     pan: int = PAN_CENTRE, level: int = LEVEL_OFF,
                     per_channel: dict = None) -> 'Key':
        """
        Assign a group of channels to this button.

        The group is stored in the slot data: for each member channel c,
        slot[c-1] is set to [0x04, level, pan, 0x25].

        Args:
            channels:    List of console channel numbers (1-40) in the group.
            label:       Button label (max 6 chars). Required for groups.
            pan:         Button-level field at +193 (not a true pan  -  groups have
                         no overall pan; per-channel pans live in slot data).
                         Device consistently writes 0x00 here for groups.
            level:       Overall group level byte.
            per_channel: Optional dict {ch: {'level': int, 'pan': int}} for
                         per-member level/pan overrides. Defaults to group level/pan.

        Returns:
            self
        """
        if not channels:
            raise ValueError("Group requires at least one channel")
        for ch in channels:
            if not (1 <= ch <= 40):
                raise ValueError(f"Channel must be 1-40, got {ch}")

        self._raw_label      = _encode_label(label)
        self._flag           = _FLAG_GROUP
        # Preserve existing _disk_flag if it's already a group-compatible value (0x00 or 0x20).
        # For new keys or keys coming from non-group assignments, default to _FLAG_MONO (0x00).
        if getattr(self, '_disk_flag', _FLAG_UNASSIGNED) not in (_FLAG_MONO, _FLAG_GROUP_ALT):
            self._disk_flag  = _FLAG_MONO
        self.src_ch          = channels[0]          # primary channel stored as src_ch
        self.level           = level
        self.pan             = pan
        self._group_channels = list(channels)

        # Build slot data: default slots, then mark each member channel
        slots = bytearray(_SLOT_DEF * _NSLOTS_KEY)
        for ch in channels:
            slot_idx = ch - 1
            ch_level = level
            ch_pan   = pan
            if per_channel and ch in per_channel:
                ch_level = per_channel[ch].get('level', level)
                ch_pan   = per_channel[ch].get('pan',   pan)
            # Snap level and get canonical cpan for slot
            sl = snap_level(ch_level) if ch_level > LEVEL_OFF else LEVEL_OFF
            sl_cpan = _LEVEL_CPAN.get(sl, _CONSOLE_PAN_DEFAULT) if sl > LEVEL_OFF else 0x01
            slots[slot_idx * 4 : slot_idx * 4 + 4] = bytes([0x04, sl, sl_cpan, ch_pan & 0xFF])
        # Write the firmware sentinel at slot[40] for single-channel groups only.
        # The device writes 03 80 01 25 at slot[40] for single-channel groups,
        # and leaves it as the default 00 80 01 25 for multi-channel groups.
        # This sentinel is what ME-OLE uses to detect single-channel groups on load.
        if len(channels) == 1:
            slots[40 * 4 : 40 * 4 + 4] = bytes([0x03, 0x80, 0x01, 0x25])
        self.slots = bytes(slots)
        return self

    # ── Read-only state ───────────────────────────────────────────────────────

    def is_assigned(self) -> bool:
        """True if this button has any source assigned."""
        return self._flag != _FLAG_UNASSIGNED

    def is_mono(self) -> bool:
        return self._flag == _FLAG_MONO

    def is_stereo(self) -> bool:
        return self._flag == _FLAG_STEREO

    def is_group(self) -> bool:
        return self._flag == _FLAG_GROUP

    def is_auto(self) -> bool:
        """True if this button is in AUTO MODE (flag=0x40).
        The device assigns the channel automatically from console routing;
        the src_ch field is ignored by the device firmware."""
        return self._flag == _FLAG_AUTO

    def __repr__(self) -> str:
        if not self.is_assigned():
            extra = f" label={self.label!r}" if self.label else ''
            return f"Key(unassigned{extra})"
        src = (f"stereo ch{self.src_ch}+{self.src_ch+1}"
               if self.is_stereo() else f"ch{self.src_ch}")
        lbl = f"{self.label!r} " if self.label else ''
        return f"Key({lbl}src={src}, pan=0x{self.pan:02x}, level=0x{self.level:02x})"

    # ── Encode / decode (internal) ────────────────────────────────────────────

    def _encode(self) -> bytes:
        """192-byte slots + level + pan + sep + 8-byte label + flag + src = 205 bytes."""
        out = bytearray(self.slots)
        # Snap level to nearest valid device step; look up canonical cpan for it
        _snapped_level = snap_level(self.level)
        _cpan = _LEVEL_CPAN.get(_snapped_level,
                getattr(self, '_console_pan', _CONSOLE_PAN_DEFAULT))
        if self.level <= LEVEL_OFF:
            _snapped_level = LEVEL_OFF
            _cpan = 0x01  # sentinel for off/unassigned
        out += bytes([_snapped_level, _cpan, self.pan & 0xFF])
        assert len(self._raw_label) == 8
        out += self._raw_label
        # Determine flag to write on disk:
        # - Group keys write _FLAG_MONO (0x00); the group membership is in the slots
        # - All other keys preserve their original disk flag (_disk_flag) for round-trip
        #   fidelity and device compatibility. The device distinguishes between flag=0x00
        #   and flag=0x40 even for single-channel keys  -  using the wrong one causes the
        #   device to read the channel number from the wrong byte position.
        # - New keys with no original disk flag default to _FLAG_AUTO (0x40),
        #   which matches what the console writes when setting up channels initially.
        # All key types preserve their original on-disk flag for round-trip fidelity.
        # Groups default to _FLAG_MONO (0x00) if no prior disk flag is known,
        # matching what the device writes for most group buttons.
        on_disk_flag = getattr(self, '_disk_flag', _FLAG_MONO)
        out += bytes([on_disk_flag & 0xFF, getattr(self, '_raw_ch_field', self.src_ch) & 0xFF])
        assert len(out) == _STRIDE
        return bytes(out)

    @classmethod
    def _decode(cls, data: bytes, sep_pos: int) -> 'Key':
        """Decode one key.
        
        Layout (confirmed from TEST40 device-generated file):
          sep_pos - _SLOT_BYTES - 2  :  +0    slots (192 bytes, 48 x 4)
          sep_pos - 2                :  +192  level
          sep_pos - 1                :  +193  console_pan (physical pan from console,
                                               stored by device; we write 0x00)
          sep_pos                    :  +194  me1_pan (ME-1 pan override; 0x25=centre)
          sep_pos + 1..8             :  +195  label (8 bytes)
          sep_pos + 9                :  +203  flag
          sep_pos + 10               :  +204  next button channel (0-indexed) or 0x22
        """
        k = cls()
        k.slots       = bytes(data[sep_pos - _SLOT_BYTES - 2 : sep_pos - 2])
        k.level       = data[sep_pos - 2]
        k._console_pan = data[sep_pos - 1]   # +193: console-sourced pan (read-only)
        k.pan         = data[sep_pos]         # +194: ME-1 pan override
        k._raw_label  = bytes(data[sep_pos + 1 : sep_pos + 9])
        k._flag       = data[sep_pos + 9]
        k.src_ch      = data[sep_pos + 10]

        # Save raw on-disk bytes for faithful round-trip encoding
        k._disk_flag     = k._flag
        k._raw_ch_field  = data[sep_pos + 10]  # raw +204 byte; next btn's channel-1 or residual

        # Detect group: slots with byte 0 == 0x04 mark group member channels.
        # The firmware always writes a sentinel at slot[40] (marker=0x03) for ALL group
        # buttons, including single-channel groups.  We use this to distinguish a genuine
        # single-channel group (1 × 0x04 slot + slot[40] sentinel) from a stale 0x04
        # slot left over from a previous assignment.
        _SLOT40_SENTINEL = bytes([0x03, 0x80, 0x01, 0x25])
        _has_group_sentinel = (k.slots[40 * 4 : 40 * 4 + 4] == _SLOT40_SENTINEL)
        group_chs = [
            j + 1
            for j in range(_NSLOTS_KEY)
            if k.slots[j * 4] == 0x04
        ]
        if len(group_chs) >= 2 or (len(group_chs) == 1 and _has_group_sentinel):
            k._flag = _FLAG_GROUP
            k._group_channels = group_chs

        # Unassigned: flag=0x00/0x40 + src=0xFF is only truly unassigned when the
        # key also has sentinel level AND sentinel pan (completely blank/default state).
        # Keys with a real label or non-sentinel values but src=0xFF have a corrupted
        # src byte from a firmware export bug  -  treat them as assigned with unknown ch.
        if k._flag in (_FLAG_MONO, _FLAG_AUTO) and k.src_ch == SRC_NONE:
            # A key is truly unassigned when it has sentinel level, sentinel pan,
            # and a blank label (either all-zeros or our encoded blank format)
            _blank_encoded = _encode_label('')
            _label_is_blank = (k._raw_label == _blank_encoded or
                               k._raw_label == bytes(8) or
                               k._raw_label.strip(b'\x00 ') == b'')
            is_blank = (k.level == _LEVEL_UNSET and k.pan == PAN_CENTRE
                        and _label_is_blank)
            if is_blank:
                k._flag = _FLAG_UNASSIGNED

        return k


# ── Preset ────────────────────────────────────────────────────────────────────

class Preset:
    """
    One of 16 preset slots in a ME-1 config.

    Attributes:
        name     (str):        Name shown on the device (max 8 chars).
        has_data (bool):       Whether this slot contains saved data.
        keys     (List[Key]):  16 button assignments. keys[0] = Button 1, etc.
    """

    def __init__(self, name: str = '', has_data: bool = False):
        self.name:     str       = name[:8]
        self.has_data: bool      = has_data
        self.keys:     List[Key] = [Key() for _ in range(_NKEYS)]
        self._tail:    bytes     = _DEFAULT_TAIL  # EQ/config data; required by device
        self._header:  bytes     = _HEADER  # preset file header (preserved from load)

    def __repr__(self) -> str:
        n = sum(1 for k in self.keys if k.is_assigned())
        return f"Preset(name={self.name!r}, assigned={n}/{_NKEYS})"

    # ── Per-preset file I/O ───────────────────────────────────────────────────

    @classmethod
    def load(cls, path: str) -> 'Preset':
        """
        Load a 4096-byte single-preset .ME1 file.

        The ME-1 exports single presets via "Export Preset to USB" and imports
        them with "Import Preset from USB" (to any slot).
        """
        with open(path, 'rb') as f:
            data = f.read()
        if len(data) != _SLOT:
            raise ValueError(
                f"Expected a {_SLOT}-byte single-preset file, got {len(data)} bytes.\n"
                "For a full config (73728 bytes) use ME1Config.load()."
            )
        return cls._decode(data, name='', has_data=True)

    def save(self, path: str) -> None:
        """
        Save this preset as a 4096-byte single-preset .ME1 file.
        Importable to any slot via USB.
        """
        _ensure_dir(path)
        with open(path, 'wb') as f:
            f.write(self._encode())
        print(f"Saved preset '{self.name}' → {path}")

    # ── Encode / decode (internal) ────────────────────────────────────────────

    def _encode(self) -> bytes:
        out = bytearray(getattr(self, '_header', _HEADER))
        for key in self.keys:
            out += key._encode()
        # Re-append the original tail (EQ data etc); pad or trim to _SLOT bytes
        tail = self._tail
        space = _SLOT - len(out)
        if len(tail) <= space:
            out += tail
            out += b'\x00' * (space - len(tail))
        else:
            out += tail[:space]
        assert len(out) == _SLOT
        # Channel encoding: button N's channel (0-indexed) is stored at out[8 + (N-1)*STRIDE].
        # For button 1 this is header byte 8; for buttons 2-16 it is the +204 byte of
        # the previous key record.  Write all 16 channel positions now.
        for i, key in enumerate(self.keys):
            pos = 8 + i * _STRIDE  # button (i+1)'s channel field (0-indexed = ch-1)
            # Groups and unassigned buttons store 0xFF in the channel field.
            # The group's actual member channels live in the slot data (b0=0x04 entries).
            if key.src_ch == SRC_NONE or key.src_ch == 0 or key.is_group():
                out[pos] = 0xFF
            elif key.is_auxin():
                out[pos] = SRC_AUXIN          # 0x28  -  special AuxIn channel index
            elif key.is_sine():
                out[pos] = SRC_SINE           # 0x2F  -  special 1kHz sine index
            else:
                out[pos] = (key.src_ch - 1) & 0xFF
        # Header byte 7 = 0x30 only when btn1 is a group (device rule, confirmed from BASS.ME1).
        # Never carry orig_hdr7 as fallback  -  a stale value causes the device
        # to put all buttons into Auto Mode.
        btn1_is_group = self.keys[0].is_group()
        out[7] = 0x30 if btn1_is_group else 0x00

        # Group preceding-button flag rule:
        # The device uses the FLAG byte (+203) of the button IMMEDIATELY BEFORE
        # a group button as a group-presence signal. That flag must be 0x20 for
        # the device to accept the group assignment on file load.
        # - Button 1 group: handled by header[7]=0x20 (above).
        # - Button N group (N>1): button(N-1) flag at out[FIRST_KEY+(N-2)*STRIDE+203]
        #   must be 0x20. We write it here, overriding whatever Key._encode put there.
        # - If button N-1 is itself a group, its flag is already 0x20 (from _disk_flag).
        # - If button N-1 is a non-group, we force its flag to 0x20.
        # Also: button 1 group needs its OWN flag=0x20 (no preceding button to carry it).
        for i, key in enumerate(self.keys):
            if key.is_group():
                # Group button own-flag rules (confirmed from TEST21 and TEST51):
                #   Has a following group → 0x20 (chain signal)
                #   Last group, custom name → 0x00
                #   Last group, blank/default name → 0x30
                # Rule confirmed from TEST53 (device):
                #   Non-last group (has a following group) → 0x30 always
                #   Last group, custom name               → 0x00
                #   Last group, blank/default name         → 0x30
                # Simplified: 0x00 only when last group AND has a custom label.
                next_is_group = (i + 1 < _NKEYS and self.keys[i + 1].is_group())
                is_last_custom = not next_is_group and key.label.strip()
                own_flag = _FLAG_MONO if is_last_custom else _FLAG_GROUP_DEFAULT
                out[len(_HEADER) + i * _STRIDE + 203] = own_flag

                # The NON-group button immediately preceding a group must have flag=0x30.
                # (Groups in a chain carry the signal in their own flag instead.)
                # Confirmed from TEST60 (latest firmware): device writes 0x30 here.
                if i > 0 and not self.keys[i - 1].is_group():
                    out[len(_HEADER) + (i - 1) * _STRIDE + 203] = _FLAG_GROUP_DEFAULT
            elif key.is_auxin():
                # AuxIn on button N: the preceding button (N-1) must have flag=0x01
                # (FLAG_SPECIAL). This is confirmed from device-generated TEST21.ME1.
                # The channel field 0x28 at the normal position is already handled by
                # the channel encoding loop above. Only the preceding flag needs forcing.
                if i > 0:
                    out[len(_HEADER) + (i - 1) * _STRIDE + 203] = _FLAG_SPECIAL

        return bytes(out)

    @classmethod
    def _decode(cls, data: bytes, name: str, has_data: bool) -> 'Preset':
        p = cls(name=name, has_data=has_data)
        p._header = bytes(data[:len(_HEADER)])  # preserve original header bytes
        for i in range(_NKEYS):
            sep = _SEP0 + i * _STRIDE
            p.keys[i] = Key._decode(data, sep)
        p._tail = bytes(data[_KEY_DATA_SIZE:])
        # Channel encoding: button N's channel is stored at data[8 + (N-1)*STRIDE]
        # as a 0-indexed value (ch = byte_value + 1).  For button 1 this lands on
        # header byte 8; for buttons 2-16 it lands on the +204 byte of the previous
        # key record.  Key._decode reads data[sep_pos+10] (= key_record+204) as
        # src_ch, which is actually the NEXT key's channel; override all 16 here.
        for i in range(_NKEYS):
            ch_byte = data[8 + i * _STRIDE]          # 0-indexed channel value
            if ch_byte == 0xFF:
                p.keys[i].src_ch = SRC_NONE
            elif ch_byte == SRC_AUXIN:
                p.keys[i].src_ch = SRC_AUXIN + 1     # AuxIn special index
                p.keys[i]._flag = _FLAG_GROUP_ALT     # internal marker only
                # _disk_flag preserved from Key._decode  -  device uses 0x00 or 0x20
            elif ch_byte == SRC_SINE:
                p.keys[i].src_ch = SRC_SINE + 1      # 1kHz Sine special index
                p.keys[i]._flag = _FLAG_MONO          # clear any unassigned flag
                p.keys[i]._disk_flag = _FLAG_MONO
            else:
                p.keys[i].src_ch = ch_byte + 1        # convert to 1-indexed

        # Bug A / Bug A2 fix: firmware export quirk — some single-channel buttons have
        # flag=0x30 (_FLAG_UNASSIGNED/_FLAG_GROUP_DEFAULT) or flag=0x20 (_FLAG_GROUP_ALT)
        # on disk but a valid channel byte in the standard encoding position.  These are
        # genuine single-channel buttons whose flag byte was set by the firmware as a
        # "preceding group" signal, not as their own assignment type.
        # Promote them to _FLAG_MONO.  Guard: must have a valid src_ch AND the key must
        # not have been detected as a group (which would have set _flag=_FLAG_GROUP already).
        _AFFECTED_FLAGS = (_FLAG_UNASSIGNED, _FLAG_GROUP_ALT)
        for i in range(_NKEYS):
            k = p.keys[i]
            if k._flag in _AFFECTED_FLAGS and k.src_ch != SRC_NONE:
                k._flag = _FLAG_MONO
                # _disk_flag stays as original for faithful round-trip

        return p

    def _name_entry(self) -> bytes:
        """10-byte name-table entry."""
        flag = 0x01 if self.has_data else 0x00
        name = self.name[:8].ljust(8).encode('ascii', errors='replace')
        return bytes([flag]) + name + bytes([0x02])


# ── ME1Config ─────────────────────────────────────────────────────────────────

class ME1Config:
    """
    A complete ME-1 configuration file (73728 bytes, 16 presets).

    Presets 1-16 are addressable as presets[0]-presets[15].
    Only presets 1-16 have their own data blocks; they're all listed
    in the name table.

    Attributes:
        presets (List[Preset]):  All 16 preset slots.
    """

    def __init__(self):
        self.presets: List[Preset] = [
            Preset(name='PRESET1' if i == 0 else f'P{i+1}', has_data=(i == 0))
            for i in range(_NPRESETS)
        ]
        self._tail_block: bytes = bytes(_SLOT)   # slot 17 — device working state

    def __repr__(self) -> str:
        names = [p.name for p in self.presets if p.name.strip()]
        return f"ME1Config([{', '.join(repr(n) for n in names)}])"

    # ── I/O ───────────────────────────────────────────────────────────────────

    @classmethod
    def load(cls, path: str) -> 'ME1Config':
        """
        Load a full .ME1 config file from disk.

        Args:
            path: Path to the .ME1 file exported from the device.

        Returns:
            ME1Config with all 16 presets populated.
        """
        with open(path, 'rb') as f:
            data = f.read()
        if len(data) != _TOTAL:
            raise ValueError(
                f"Expected a {_TOTAL}-byte full config file, got {len(data)} bytes.\n"
                "For a single-preset file (4096 bytes) use Preset.load()."
            )

        cfg = cls.__new__(cls)
        cfg.presets = []

        # Decode name table
        names = []
        for i in range(_NPRESETS):
            off      = _NAME_TABLE_OFFSET + i * _NAME_TABLE_ENTRY
            flag     = data[off]
            name_raw = data[off+1:off+9].rstrip(b'\x00 ').decode('ascii', errors='replace')
            names.append((name_raw, bool(flag & 0x01)))

        # Decode each preset's data block
        for i in range(_NPRESETS):
            off      = _preset_offset(i)
            name, has_data = names[i]
            block    = data[off:off+_SLOT]
            # Detect blocks with no real preset data:
            # - all 0xFF = erased flash
            # - all 0x00 = unused/zero block  
            # - header byte2 = 0x01 = uninitialized flash (not a saved preset)
            # Only header byte2 = 0x02 indicates a properly-written preset block.
            block_is_empty = (
                all(b == 0xFF for b in block[:32]) or
                all(b == 0x00 for b in block[:32]) or
                (len(block) >= 3 and block[2] == 0x01)
            )
            if block_is_empty:
                p = Preset(name=name, has_data=False)
            else:
                p = Preset._decode(block, name=name, has_data=has_data)
            cfg.presets.append(p)

        # Preserve slot 17 (device working state) for round-trip fidelity.
        cfg._tail_block = bytes(data[17 * _SLOT : 18 * _SLOT])

        return cfg

    def save(self, path: str) -> None:
        """
        Save the full config as a .ME1 file ready to load onto the device.

        Copy to a USB drive and use the ME-1's "Import Config from USB" menu.

        Args:
            path: Destination file path (e.g. "MECFG.ME1").
        """
        _ensure_dir(path)
        with open(path, 'wb') as f:
            f.write(self._encode())
        print(f"Saved config → {path} ({_TOTAL} bytes)")

    # ── Convenience ───────────────────────────────────────────────────────────

    def preset(self, name: str) -> Preset:
        """
        Look up a preset by name (case-insensitive).

        Args:
            name: Preset name as shown on the device.

        Returns:
            The matching Preset.

        Raises:
            KeyError: If no preset with that name exists.
        """
        for p in self.presets:
            if p.name.strip().lower() == name.strip().lower():
                return p
        available = [p.name for p in self.presets if p.name.strip()]
        raise KeyError(f"No preset named {name!r}. Available: {available}")

    def summary(self) -> str:
        """Human-readable summary of all presets and their button assignments."""
        lines = ['ME-1 Config', '=' * 52]
        for i, p in enumerate(self.presets):
            status = '[active]' if p.has_data else '[empty] '
            lines.append(f'\nPreset {i+1:2d}: {p.name!r:10s} {status}')
            if any(k.is_assigned() for k in p.keys):
                for j, k in enumerate(p.keys):
                    lines.append(f'  Button {j+1:2d}: {k}')
        return '\n'.join(lines)

    # ── Encode (internal) ─────────────────────────────────────────────────────

    def _encode(self) -> bytes:
        out = bytearray(_TOTAL)

        # Slot 0 — P1 boot/display copy.
        # Device shows this preset on load. Must match slot2 (P1 button slot) so the
        # boot display matches what button 1 loads.
        p1_enc = self.presets[0]._encode()
        out[0 : _SLOT] = p1_enc

        # Slot 1 — Name table.
        # Entry[1] always 0x01 (slot2 = P1 button slot, always has data).
        # Entry[2] always 0x01 (slot3 = P2 button slot, always has data).
        nt = bytearray()
        for i, p in enumerate(self.presets):
            entry = bytearray(p._name_entry())
            if i in (1, 2):
                entry[0] = 0x01
            nt += entry
        out[_NAME_TABLE_OFFSET : _NAME_TABLE_OFFSET + len(nt)] = nt

        # Slot 2 — P1 button slot.
        # Device loads this when user presses button 1. Always contains P1 data.
        # Apply group-flag normalisation (0x30→0x20) as the device expects here.
        blk2 = bytearray(p1_enc)
        for gi in range(_NKEYS):
            gpos = len(_HEADER) + gi * _STRIDE + 203
            if gpos < len(blk2) and blk2[gpos] == _FLAG_GROUP_DEFAULT:
                blk2[gpos] = _FLAG_GROUP_ALT
        out[2 * _SLOT : 3 * _SLOT] = bytes(blk2)

        # Slots 3-17 — P2-P16 button slots (via _preset_offset: P2→slot3, P3→slot4…P16→slot17)
        for i in range(1, _NPRESETS):
            off = _preset_offset(i)
            p   = self.presets[i]
            if p.has_data or any(k.is_assigned() for k in p.keys):
                out[off : off + _SLOT] = p._encode()
            else:
                for j in range(off, off + _SLOT):
                    out[j] = 0xFF   # erased flash

        # Slot 17 — device working state; preserve for round-trip fidelity
        tail = getattr(self, '_tail_block', None)
        if tail and len(tail) == _SLOT:
            out[17 * _SLOT : 18 * _SLOT] = tail

        return bytes(out)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _validate_ch(src_ch: int) -> None:
    if not (1 <= src_ch <= 40):
        raise ValueError(f"src_ch must be 1-40, got {src_ch}")

def _ensure_dir(path: str) -> None:
    d = os.path.dirname(os.path.abspath(path))
    if d:
        os.makedirs(d, exist_ok=True)
