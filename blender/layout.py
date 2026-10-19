"""Open Life DJ — control layout (single source of truth).

Pure Python, no bpy: the Blender build script and the app both read this.
Units are millimetres. Top view: origin at the centre of the top surface,
+X to the right, +Y away from the DJ (towards the screen strip).

Layout proportions follow a 4-channel all-in-one (XDJ-AZ class), with the
screen moved to a full-width strip across the top.
"""

# --- Body -------------------------------------------------------------------
BODY_W = 1000.0
BODY_TOP = 280.0       # back edge (Y)
BODY_BOTTOM = -284.0   # front edge (Y)
BODY_H = 60.0          # height below the top surface

# --- Bands (Y) ----------------------------------------------------------------
SCREEN_BEZEL = dict(x=0.0, y=204.0, w=980.0, h=120.0)
SCREEN_ACTIVE = dict(x=0.0, y=204.0, w=960.0, h=104.0)   # 3840 x 416 px at 4 px/mm
NAV_Y = 128.0
MAIN_TOP = 112.0       # top of the deck / mixer area

DECK_W = 330.0
DECK_L_X0 = -500.0     # left edge of the left deck
DECK_R_X0 = 170.0      # left edge of the right deck
MIXER_X0, MIXER_X1 = -170.0, 170.0

# Control size presets (mm)
KNOB_S, KNOB_M, KNOB_L = 11.0, 15.0, 20.0
BTN_ROUND = 9.0


def _c(id, type, x, y, group, label="", **kw):
    d = dict(id=id, type=type, x=round(x, 2), y=round(y, 2), group=group, label=label)
    d.update(kw)
    return d


def _deck(deck, x0, select_labels):
    """One deck. u: mm from the deck's left edge; v: mm down from MAIN_TOP."""
    g = f"deck_{deck}"
    P = f"D{deck}_"

    def at(u, v):
        return x0 + u, MAIN_TOP - v

    out = []

    def add(id, type, u, v, label="", **kw):
        x, y = at(u, v)
        out.append(_c(P + id, type, x, y, g, label, **kw))

    # Top row: cue / loop / deck select / memory
    add("IN_CUE", "button_round", 21, 28, "IN/CUE", d=12, led="orange")
    add("OUT", "button_round", 49, 28, "OUT", d=12, led="orange")
    add("RELOOP_EXIT", "button_round", 81, 28, "RELOOP/EXIT", d=BTN_ROUND, led="orange")
    add("DECK_SELECT_A", "button_rect", 144, 28, select_labels[0], w=22, h=12, led="blue")
    add("DECK_SELECT_B", "button_rect", 172, 28, select_labels[1], w=22, h=12, led="blue")
    add("CUE_LOOP_CALL_PREV", "button_round", 232, 28, "CALL ◀", d=BTN_ROUND)
    add("CUE_LOOP_CALL_NEXT", "button_round", 254, 28, "CALL ▶", d=BTN_ROUND)
    add("DELETE", "button_round", 279, 28, "DELETE", d=BTN_ROUND)
    add("MEMORY", "button_round", 301, 28, "MEMORY", d=BTN_ROUND, led="red")

    # Loop / beat jump
    add("BEAT_LOOP_4", "button_round", 23, 56, "4 BEAT", d=12, led="orange")
    add("BEAT_LOOP_8", "button_round", 49, 56, "8 BEAT", d=12, led="orange")
    add("BEAT_JUMP_BACK", "button_rect", 21, 85, "◀", w=16, h=8)
    add("BEAT_JUMP_FWD", "button_rect", 49, 85, "▶", w=16, h=8)

    # Jog settings
    add("JOG_FEEL", "knob", 259, 71, "JOG FEEL", d=KNOB_S, range=(-1, 1), detent=True)
    add("VINYL_SPEED_ADJUST", "knob", 299, 56, "VINYL SPEED", d=KNOB_S, range=(0, 1))
    add("JOG_MODE", "button_rect", 299, 85, "JOG MODE", w=16, h=8, led="blue")

    # Left side
    add("SLIP", "button_round", 21, 120, "SLIP", d=BTN_ROUND, led="red")
    add("REVERSE", "button_rect", 21, 165, "REV", w=16, h=8, led="red")
    add("SHIFT", "button_rect", 33, 218, "SHIFT", w=18, h=10)
    add("TRACK_SEARCH_BACK", "button_rect", 25, 250, "|◀◀", w=18, h=12)
    add("TRACK_SEARCH_FWD", "button_rect", 47, 250, "▶▶|", w=18, h=12)
    add("SEARCH_BACK", "button_rect", 25, 276, "◀◀", w=18, h=12)
    add("SEARCH_FWD", "button_rect", 47, 276, "▶▶", w=18, h=12)
    add("CUE", "button_big", 36, 316, "CUE", d=38, led="orange")
    add("PLAY_PAUSE", "button_big", 36, 365, "PLAY/PAUSE", d=38, led="green")

    # Jog wheel
    add("JOG", "jog", 166, 167, "", d=226, platter_d=200, display_d=56)

    # Right side: sync / tempo
    add("BEAT_SYNC", "button_rect", 290, 113, "BEAT SYNC", w=16, h=10, led="orange")
    add("MASTER", "button_rect", 312, 113, "MASTER", w=16, h=10, led="orange")
    add("KEY_SYNC", "button_rect", 301, 135, "KEY SYNC", w=32, h=8, led="blue")
    add("TEMPO_RANGE", "button_round", 299, 190, "TEMPO ±6/10/16/WIDE", d=BTN_ROUND)
    add("MASTER_TEMPO", "button_round", 299, 226, "MASTER TEMPO", d=BTN_ROUND, led="red")
    add("TEMPO_RESET", "button_round", 263, 311, "TEMPO RESET", d=BTN_ROUND, led="green")
    add("TEMPO", "fader", 299, 298, "TEMPO", length=103, travel=92, axis="y", cap=(18, 10))

    # Pads
    for i, (lab, col) in enumerate([("HOT CUE", "white"), ("BEAT LOOP", "orange"),
                                    ("SLIP LOOP", "blue"), ("BEAT JUMP", "red")]):
        add(f"PAD_MODE_{i + 1}", "button_rect", 117 + 33 * i, 300, lab, w=30, h=8, led=col)
    for row in range(2):
        for col in range(4):
            n = row * 4 + col + 1
            add(f"PAD_{n}", "pad", 117 + 33 * col, 329 + 34 * row, "", w=30, h=30, led="rgb")
    return out


def _mixer():
    g = "mixer"
    out = []

    def add(id, type, x, v, label="", **kw):
        out.append(_c(id, type, x, MAIN_TOP - v, g, label, **kw))

    # Mic band (top left of the mixer)
    for row, v in ((1, 20), (2, 46)):
        add(f"MIC{row}_ON", "button_round", -158, v, f"MIC {row}", d=BTN_ROUND, led="blue")
        add(f"MIC{row}_LEVEL", "knob", -136, v, "LEVEL", d=13, range=(0, 1))
        for name, x in (("LOW", -114), ("MID", -92), ("HI", -70)):
            add(f"MIC{row}_{name}", "knob", x, v, name, d=13, range=(-1, 1), detent=True)
    add("TALK_OVER", "button_round", -44, 33, "TALK OVER", d=BTN_ROUND, led="red")

    # Master band (top right of the mixer)
    add("MASTER_LEVEL", "knob", 20, 22, "MASTER", d=KNOB_M, range=(0, 1))
    add("MASTER_CUE", "button_rect", 20, 48, "CUE", w=16, h=9, led="orange")
    add("MASTER_METER", "meter", 91, 21, "", length=54, axis="x", channels=2, segments=15)
    add("BOOTH_LEVEL", "knob", 148, 22, "BOOTH", d=KNOB_M, range=(0, 1))
    add("QUANTIZE", "button_round", 148, 48, "QUANTIZE", d=BTN_ROUND, led="red")

    # Left column: settings, sound colour FX, headphones
    add("MIXER_SETTINGS", "button_rect", -141, 87, "SETTINGS", w=14, h=9)
    for i, name in enumerate(["SPACE", "DUB ECHO", "CRUSH", "SWEEP", "NOISE", "FILTER"]):
        add(f"SCFX_{name.replace(' ', '_')}", "button_rect", -152 + 22 * (i % 2),
            142 + 22 * (i // 2), name, w=18, h=9, led="blue")
    add("SCFX_PARAMETER", "knob", -141, 216, "PARAMETER", d=KNOB_M, range=(0, 1))
    add("HP_LINK_CUE", "button_rect", -141, 250, "LINK CUE", w=14, h=8, led="orange")
    add("HP_MIX", "knob", -141, 280, "MIX", d=KNOB_M, range=(0, 1), detent=True)
    add("HP_LEVEL", "knob", -141, 320, "LEVEL", d=KNOB_M, range=(0, 1))

    # Channel strips, ordered 3-1-2-4 like club mixers
    for i, ch in enumerate([3, 1, 2, 4]):
        x = -97.5 + 47 * i
        P = f"CH{ch}_"
        add(P + "TRIM", "knob", x, 75, "TRIM", d=KNOB_M, range=(0, 1), detent=True)
        add(P + "EQ_HI", "knob", x, 109, "HI", d=KNOB_M, range=(-1, 1), detent=True)
        add(P + "EQ_MID", "knob", x, 144, "MID", d=KNOB_M, range=(-1, 1), detent=True)
        add(P + "EQ_LOW", "knob", x, 178, "LOW", d=KNOB_M, range=(-1, 1), detent=True)
        add(P + "COLOR", "knob", x, 216, "COLOR", d=KNOB_L, range=(-1, 1), detent=True)
        add(P + "CUE", "button_rect", x, 244, "CUE", w=16, h=9, led="orange")
        add(P + "METER", "meter", x - 17, 144, "", length=104, axis="y", channels=1, segments=15)
        add(P + "FADER", "fader", x, 314, str(ch), length=72, travel=60, axis="y", cap=(10, 18))
    add("CROSSFADER", "fader", -27, 368, "A          B", length=58, travel=45, axis="x", cap=(10, 18))

    # Right column: beat FX
    add("BEAT_FX_XPAD", "xpad", 105, 87, "X-PAD", w=72, h=10, segments=8)
    add("BEAT_FX_BEAT_LEFT", "button_rect", 90, 112, "◀ BEAT", w=14, h=8)
    add("BEAT_FX_BEAT_RIGHT", "button_rect", 120, 112, "BEAT ▶", w=14, h=8)
    add("BEAT_FX_AUTO_TAP", "button_round", 82, 134, "AUTO/TAP", d=BTN_ROUND)
    add("BEAT_FX_TAP", "button_round", 105, 134, "TAP", d=12, led="green")
    add("BEAT_FX_QUANTIZE", "button_round", 128, 134, "FX QUANTIZE", d=BTN_ROUND, led="red")
    for i, name in enumerate(["LOW", "MID", "HI"]):
        add(f"BEAT_FX_FREQ_{name}", "button_rect", 84 + 21 * i, 158, name, w=16, h=8, led="blue")
    add("BEAT_FX_SELECT", "knob", 105, 194, "FX SELECT", d=KNOB_L, steps=14)
    for i, name in enumerate(["1", "2", "3", "4", "MIC", "CF.A", "CF.B", "MST"]):
        add(f"BEAT_FX_CH_{name.replace('.', '')}", "button_rect", 81 + 16 * (i % 4),
            232 + 16 * (i // 4), name, w=14, h=8, led="blue")
    add("BEAT_FX_TIME", "encoder", 105, 277, "TIME", d=16)
    add("BEAT_FX_LEVEL_DEPTH", "knob", 105, 317, "LEVEL/DEPTH", d=KNOB_M, range=(0, 1))
    add("BEAT_FX_ON_OFF", "button_round", 105, 356, "ON/OFF", d=18, led="blue")
    return out


def _nav():
    g = "nav"
    out = []

    def add(id, type, x, label="", **kw):
        out.append(_c(id, type, x, NAV_Y, g, label, **kw))

    for i, name in enumerate(["SOURCE", "BROWSE", "TAG LIST", "PLAYLIST", "SEARCH", "MENU"]):
        add(name.replace(" ", "_"), "button_rect", -125 + 50 * i, name, w=22, h=9, led="blue")
    for deck, x in ((3, -205), (1, -180), (2, 180), (4, 205)):
        add(f"LOAD_{deck}", "button_rect", x, f"LOAD {deck}", w=18, h=9, led="blue")
    add("BACK", "button_rect", 250, "BACK", w=18, h=9)
    add("BROWSE_ENCODER", "encoder", 285, "", d=20, push=True)
    add("TAG_TRACK", "button_rect", 320, "TAG TRACK", w=18, h=9)
    add("SHORTCUT", "button_rect", 350, "SHORTCUT", w=18, h=9)
    add("USB1", "usb_port", 405, "USB 1", w=16, h=8)
    add("USB1_STOP", "button_round", 428, "STOP", d=8, led="red")
    add("USB2", "usb_port", 458, "USB 2", w=16, h=8)
    add("USB2_STOP", "button_round", 481, "STOP", d=8, led="red")
    return out


def controls():
    out = [_c("SCREEN", "screen", SCREEN_ACTIVE["x"], SCREEN_ACTIVE["y"], "screen",
              w=SCREEN_ACTIVE["w"], h=SCREEN_ACTIVE["h"], px=(3840, 416))]
    out += _nav()
    out += _deck(1, DECK_L_X0, ("3", "1"))
    out += _mixer()
    out += _deck(2, DECK_R_X0, ("2", "4"))
    return out


if __name__ == "__main__":
    import collections
    cs = controls()
    print(len(cs), "controls")
    print(collections.Counter(c["type"] for c in cs))
