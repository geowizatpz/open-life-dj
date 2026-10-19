"""Build the Open Life DJ blockout in Blender from layout.py.

Run inside Blender:  exec(open("<project>/blender/build_blockout.py").read())
Rebuilds the scene from scratch, so re-run it after any change to layout.py.
Every control object carries custom props: control_id, control_type, control_part.
"""
import importlib
import json
import math
import os
import sys

import bpy

PROJECT = "/Users/orbit/open life dj"
sys.path.insert(0, os.path.join(PROJECT, "blender"))
import layout as L  # noqa: E402
importlib.reload(L)

MM = 0.001


# --- Scene reset ----------------------------------------------------------------
def reset_scene():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for coll in list(bpy.data.collections):
        bpy.data.collections.remove(coll)
    for blocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials,
                   bpy.data.lights, bpy.data.cameras):
        for b in list(blocks):
            if b.users == 0:
                blocks.remove(b)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.length_unit = "MILLIMETERS"
    return scene


COLLS = {}


def coll(name):
    if name not in COLLS:
        c = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(c)
        COLLS[name] = c
    return COLLS[name]


# --- Materials -----------------------------------------------------------------
MATS = {}


def mat(name, rgb, rough=0.5, metal=0.0, emit=None, strength=0.0):
    if name in MATS:
        return MATS[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (*rgb, 1)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    if emit:
        bsdf.inputs["Emission Color"].default_value = (*emit, 1)
        bsdf.inputs["Emission Strength"].default_value = strength
    m.diffuse_color = (*rgb, 1)
    MATS[name] = m
    return m


LED = {
    "orange": (1.0, 0.35, 0.02), "green": (0.1, 1.0, 0.2), "blue": (0.1, 0.35, 1.0),
    "red": (1.0, 0.05, 0.05), "white": (1.0, 1.0, 1.0),
}
PAD_DEMO = ["red", "blue", "orange", "blue", "green", "orange", "blue", "orange"]


def led_mat(color):
    rgb = LED.get(color, LED["white"])
    return mat(f"LED_{color}", rgb, 0.4, emit=rgb, strength=4.0)


def materials():
    return dict(
        body=mat("Body_Black", (0.018, 0.018, 0.02), 0.55),
        plate=mat("Plate_Anodized", (0.03, 0.03, 0.033), 0.4, 0.6),
        bezel=mat("Screen_Bezel", (0.008, 0.008, 0.008), 0.3),
        glass=mat("Screen_Glass", (0.0, 0.0, 0.0), 0.05),
        knob=mat("Knob_Rubber", (0.02, 0.02, 0.022), 0.7),
        knob_cap=mat("Knob_Cap", (0.06, 0.06, 0.065), 0.35, 0.8),
        pointer=mat("Knob_Pointer", (0.9, 0.9, 0.9), 0.4),
        button=mat("Button_Rubber", (0.06, 0.06, 0.065), 0.75),
        pad=mat("Pad_Rubber", (0.03, 0.03, 0.03), 0.8),
        slot=mat("Fader_Slot", (0.0, 0.0, 0.0), 0.9),
        fader_cap=mat("Fader_Cap", (0.1, 0.1, 0.1), 0.5),
        fader_line=mat("Fader_Line", (0.9, 0.9, 0.9), 0.4),
        jog_ring=mat("Jog_Ring_Chrome", (0.8, 0.8, 0.82), 0.12, 1.0),
        jog_platter=mat("Jog_Platter", (0.015, 0.015, 0.015), 0.25),
        jog_display=mat("Jog_Display", (0.02, 0.03, 0.05), 0.1, emit=(0.4, 0.6, 1.0), strength=0.6),
        meter_off=mat("Meter_Off", (0.03, 0.04, 0.03), 0.3),
        usb=mat("USB_Port", (0.0, 0.0, 0.0), 0.6),
        label=mat("Silkscreen", (0.75, 0.75, 0.75), 0.6),
    )


# --- Primitive helpers ----------------------------------------------------------
def tag(ob, c, part, collection):
    ob["control_id"] = c["id"]
    ob["control_type"] = c["type"]
    ob["control_part"] = part
    for uc in ob.users_collection:
        uc.objects.unlink(ob)
    collection.objects.link(ob)
    return ob


def box(name, x, y, w, h, z0, z1, material, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x * MM, y * MM, (z0 + z1) / 2 * MM))
    ob = bpy.context.active_object
    ob.name = name
    ob.scale = (w * MM, h * MM, (z1 - z0) * MM)
    bpy.ops.object.transform_apply(scale=True)
    if bevel > 0:
        m = ob.modifiers.new("Bevel", "BEVEL")
        m.width = bevel * MM
        m.segments = 3
        m.limit_method = "ANGLE"
    ob.data.materials.append(material)
    return ob


def cyl(name, x, y, d, z0, z1, material, verts=48, bevel=0.0):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=d / 2 * MM, depth=(z1 - z0) * MM,
                                        location=(x * MM, y * MM, (z0 + z1) / 2 * MM))
    ob = bpy.context.active_object
    ob.name = name
    if bevel > 0:
        m = ob.modifiers.new("Bevel", "BEVEL")
        m.width = bevel * MM
        m.segments = 3
        m.limit_method = "ANGLE"
    ob.data.materials.append(material)
    bpy.ops.object.shade_smooth()
    return ob


def ring(name, x, y, d, thickness, z, material):
    bpy.ops.mesh.primitive_torus_add(major_radius=d / 2 * MM, minor_radius=thickness / 2 * MM,
                                     major_segments=64, minor_segments=8,
                                     location=(x * MM, y * MM, z * MM))
    ob = bpy.context.active_object
    ob.name = name
    ob.data.materials.append(material)
    return ob


def text(name, s, x, y, size, material, collection, z=0.65):
    cu = bpy.data.curves.new(name, "FONT")
    cu.body = s
    cu.size = size * MM
    cu.align_x = "CENTER"
    cu.align_y = "CENTER"
    ob = bpy.data.objects.new(name, cu)
    ob.location = (x * MM, y * MM, z * MM)
    ob.data.materials.append(material)
    collection.objects.link(ob)
    return ob


# --- Control builders -----------------------------------------------------------
def footprint_h(c):
    t = c["type"]
    if "d" in c:
        return c["d"]
    if t == "fader":
        return c["length"] if c["axis"] == "y" else c["cap"][1]
    if t == "meter":
        return c["length"] if c["axis"] == "y" else 8
    return c.get("h", 10)


def build_control(c, M, col, labels):
    t, x, y, n = c["type"], c["x"], c["y"], c["id"]
    parts = []
    if t == "knob":
        d = c["d"]
        parts.append(tag(cyl(n + "_skirt", x, y, d + 3, 0.6, 2.0, M["knob"]), c, "skirt", col))
        parts.append(tag(cyl(n + "_body", x, y, d, 2.0, 16.0, M["knob"], bevel=0.6), c, "body", col))
        parts.append(tag(cyl(n + "_cap", x, y, d - 3, 16.0, 16.6, M["knob_cap"]), c, "cap", col))
        parts.append(tag(box(n + "_pointer", x, y + d * 0.27, 0.9, d * 0.42, 16.0, 16.9, M["pointer"]),
                         c, "pointer", col))
    elif t == "encoder":
        d = c["d"]
        parts.append(tag(cyl(n + "_body", x, y, d, 0.6, 14.0, M["knob"], verts=24, bevel=0.5),
                         c, "body", col))
        parts.append(tag(cyl(n + "_cap", x, y, d - 4, 14.0, 14.6, M["knob_cap"]), c, "cap", col))
    elif t == "button_round":
        d = c["d"]
        parts.append(tag(cyl(n + "_cap", x, y, d, 0.6, 4.0, M["button"], bevel=0.6), c, "cap", col))
        if c.get("led"):
            parts.append(tag(ring(n + "_led", x, y, d + 1.6, 0.9, 1.0, led_mat(c["led"])), c, "led", col))
    elif t == "button_rect":
        w, h = c["w"], c["h"]
        parts.append(tag(box(n + "_cap", x, y, w, h, 0.6, 4.0, M["button"], bevel=1.0), c, "cap", col))
        if c.get("led"):
            parts.append(tag(box(n + "_led", x, y, w + 1.2, h + 1.2, 0.6, 1.4, led_mat(c["led"])),
                             c, "led", col))
    elif t == "button_big":
        d = c["d"]
        parts.append(tag(cyl(n + "_cap", x, y, d, 0.6, 6.0, M["button"], verts=64, bevel=1.5),
                         c, "cap", col))
        parts.append(tag(ring(n + "_led", x, y, d + 2.4, 2.0, 1.4, led_mat(c["led"])), c, "led", col))
    elif t == "pad":
        idx = int(n.split("_")[-1]) - 1
        parts.append(tag(box(n + "_led", x, y, c["w"] + 1.4, c["h"] + 1.4, 0.6, 2.0,
                             led_mat(PAD_DEMO[idx])), c, "led", col))
        parts.append(tag(box(n + "_cap", x, y, c["w"] - 1.6, c["h"] - 1.6, 0.6, 6.0, M["pad"], bevel=2.0),
                         c, "cap", col))
    elif t == "fader":
        length, (cw, ch) = c["length"], c["cap"]
        if c["axis"] == "y":
            parts.append(tag(box(n + "_slot", x, y, 2.5, length, 0.0, 0.7, M["slot"]), c, "slot", col))
            cap = box(n + "_cap", x, y, cw, ch, 0.7, 13.0, M["fader_cap"], bevel=1.2)
            line = box(n + "_line", x, y, cw + 0.2, 0.8, 12.5, 13.2, M["fader_line"])
        else:
            parts.append(tag(box(n + "_slot", x, y, length, 2.5, 0.0, 0.7, M["slot"]), c, "slot", col))
            cap = box(n + "_cap", x, y, ch, cw, 0.7, 13.0, M["fader_cap"], bevel=1.2)
            line = box(n + "_line", x, y, 0.8, cw + 0.2, 12.5, 13.2, M["fader_line"])
        parts.append(tag(cap, c, "cap", col))
        parts.append(tag(line, c, "cap_line", col))
    elif t == "jog":
        parts.append(tag(cyl(n + "_ring", x, y, c["d"], 0.6, 8.0, M["jog_ring"], verts=128, bevel=1.0),
                         c, "ring", col))
        parts.append(tag(cyl(n + "_platter", x, y, c["platter_d"], 8.0, 12.0, M["jog_platter"],
                             verts=128, bevel=0.8), c, "platter", col))
        parts.append(tag(ring(n + "_led", x, y, c["display_d"] + 10, 2.0, 12.2, led_mat("blue")),
                         c, "led", col))
        parts.append(tag(cyl(n + "_display", x, y, c["display_d"], 12.0, 12.6, M["jog_display"],
                             verts=64), c, "display", col))
    elif t == "meter":
        segs, length = c["segments"], c["length"]
        step = length / segs
        for ch_i in range(c["channels"]):
            for s in range(segs):
                k = s / (segs - 1)
                colr = "green" if k < 0.6 else ("orange" if k < 0.85 else "red")
                lit = s < segs * 0.55
                m = led_mat(colr) if lit else M["meter_off"]
                if c["axis"] == "y":
                    bx, by, bw, bh = x, y - length / 2 + step * (s + 0.5), 3.0, step * 0.7
                else:
                    bx, by = x - length / 2 + step * (s + 0.5), y + 3 - 6 * ch_i
                    bw, bh = step * 0.7, 3.0
                parts.append(tag(box(f"{n}_seg{ch_i}_{s}", bx, by, bw, bh, 0.6, 1.0, m),
                                 c, f"seg_{ch_i}_{s}", col))
    elif t == "xpad":
        parts.append(tag(box(n + "_strip", x, y, c["w"], c["h"], 0.6, 1.6, M["button"], bevel=1.0),
                         c, "strip", col))
        for s in range(c["segments"]):
            sx = x - c["w"] / 2 + c["w"] / c["segments"] * (s + 0.5)
            parts.append(tag(box(f"{n}_led{s}", sx, y, 2.0, 2.0, 1.6, 1.9, led_mat("blue")),
                             c, f"led_{s}", col))
    elif t == "usb_port":
        parts.append(tag(box(n + "_port", x, y, c["w"], c["h"], -2.0, 0.65, M["usb"]), c, "port", col))
    elif t == "screen":
        b = L.SCREEN_BEZEL
        parts.append(tag(box(n + "_bezel", b["x"], b["y"], b["w"], b["h"], 0.0, 3.0, M["bezel"], bevel=2.0),
                         c, "bezel", col))
        parts.append(tag(box(n + "_glass", x, y, c["w"], c["h"], 3.0, 3.3, M["glass"]), c, "glass", col))

    # Silkscreen label above the control
    if c.get("label") and t not in ("pad", "screen"):
        if t == "fader" and c["axis"] == "y" and c["group"] == "mixer":
            ly = y + c["length"] / 2 + 6          # channel number above the fader
        elif t == "fader" and c["axis"] == "x":
            ly = y - 9
        else:
            ly = y + footprint_h(c) / 2 + 3.2
        size = 5.0 if (t == "fader" and c["group"] == "mixer" and c["axis"] == "y") else 2.4
        text(f"{n}_label", c["label"], x, ly, size, M["label"], labels)
    return parts


# --- Body and panels ------------------------------------------------------------
def build_body(M):
    col = coll("Body")
    W, top, bot = L.BODY_W, L.BODY_TOP, L.BODY_BOTTOM
    ob = box("Body", 0, (top + bot) / 2, W, top - bot, -L.BODY_H, 0, M["body"], bevel=6.0)
    for uc in ob.users_collection:
        uc.objects.unlink(ob)
    col.objects.link(ob)
    gap = 1.2
    plates = [
        ("Plate_Top", 0, (top - 8 + L.MAIN_TOP) / 2, W - 16, top - 8 - L.MAIN_TOP),
        ("Plate_Deck1", L.DECK_L_X0 + 8 + (L.DECK_W - 8) / 2, (L.MAIN_TOP + bot + 8) / 2 - gap / 2,
         L.DECK_W - 8 - gap, L.MAIN_TOP - bot - 8 - gap),
        ("Plate_Mixer", 0, (L.MAIN_TOP + bot + 8) / 2 - gap / 2,
         L.MIXER_X1 - L.MIXER_X0 - gap, L.MAIN_TOP - bot - 8 - gap),
        ("Plate_Deck2", L.DECK_R_X0 + (L.DECK_W - 8) / 2 + gap / 2, (L.MAIN_TOP + bot + 8) / 2 - gap / 2,
         L.DECK_W - 8 - gap, L.MAIN_TOP - bot - 8 - gap),
    ]
    for name, x, y, w, h in plates:
        p = box(name, x, y, w, h, 0.0, 0.6, M["plate"], bevel=0.8)
        for uc in p.users_collection:
            uc.objects.unlink(p)
        col.objects.link(p)
    text("Brand", "OPEN LIFE DJ", -440, L.NAV_Y, 5.0, M["label"], col)


# --- Camera and lights ----------------------------------------------------------
def build_camera_and_lights(scene):
    col = coll("Camera_Lights")
    cam_data = bpy.data.cameras.new("TopOrtho")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = 1.04
    cam_data.clip_end = 10
    cam = bpy.data.objects.new("TopOrtho", cam_data)
    cam.location = (0, (L.BODY_TOP + L.BODY_BOTTOM) / 2 * MM, 2.0)
    col.objects.link(cam)
    scene.camera = cam
    scene.render.resolution_x = 4160
    scene.render.resolution_y = round(4160 * 0.60 / 1.04)
    scene.render.resolution_percentage = 25

    def area(name, loc, rot, size, power):
        ld = bpy.data.lights.new(name, "AREA")
        ld.size = size
        ld.energy = power
        lo = bpy.data.objects.new(name, ld)
        lo.location = loc
        lo.rotation_euler = rot
        col.objects.link(lo)

    area("Key", (-0.6, 0.9, 1.4), (math.radians(-35), math.radians(-20), 0), 1.5, 60)
    area("Fill", (0.8, -0.6, 1.2), (math.radians(30), math.radians(30), 0), 2.0, 15)
    world = scene.world or bpy.data.worlds.new("World")
    scene.world = world
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.05, 0.05, 0.055, 1)
    bg.inputs["Strength"].default_value = 0.25


# --- Main -----------------------------------------------------------------------
def build():
    scene = reset_scene()
    COLLS.clear()
    MATS.clear()
    M = materials()
    build_body(M)
    labels = coll("Labels")
    groups = {"screen": "Screen", "nav": "Nav", "deck_1": "Deck_1", "deck_2": "Deck_2", "mixer": "Mixer"}
    cs = L.controls()
    n_obj = 0
    for c in cs:
        n_obj += len(build_control(c, M, coll(groups[c["group"]]), labels))
    build_camera_and_lights(scene)

    os.makedirs(os.path.join(PROJECT, "design"), exist_ok=True)
    with open(os.path.join(PROJECT, "design", "controls.json"), "w") as f:
        json.dump(dict(units="mm", origin="top surface centre, +X right, +Y back",
                       body=dict(w=L.BODY_W, top=L.BODY_TOP, bottom=L.BODY_BOTTOM),
                       controls=cs), f, indent=1, ensure_ascii=False)
    print(f"Built {len(cs)} controls as {n_obj} objects")


build()
