"""Open Life DJ — procedural build of the all-in-one controller.

Run inside Blender:  exec(open("/Users/orbit/open life dj/blender/build_controller.py").read())
Rebuilds the whole scene from scratch. Units are metres; +Y is away from the DJ.
Every control is its own named object (with custom props) so the app can animate it later.
"""
import bpy, bmesh, math, random
from mathutils import Vector

random.seed(7)

# ---------------------------------------------------------------- layout constants
W, D = 0.90, 0.49            # chassis footprint
FOOT_H = 0.006
BODY_TOP = 0.060
PLATE_T = 0.003
PZ = BODY_TOP + PLATE_T      # top surface of the faceplates
PLATE_Y0, PLATE_Y1 = -0.235, 0.161
MIX_HALF = 0.153             # mixer plate half width
DECK_X = 0.30                # deck centres at +-DECK_X
JOG_Y = 0.030
CH_X = [-0.093, -0.031, 0.031, 0.093]
LABEL_SCALE = 1.15           # printed legend size multiplier


# ---------------------------------------------------------------- scene reset
def reset():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.curves,
                 bpy.data.lights, bpy.data.cameras):
        for d in list(coll):
            coll.remove(d)
    for c in list(bpy.data.collections):
        bpy.data.collections.remove(c)


def collection(name, parent=None):
    c = bpy.data.collections.new(name)
    (parent or bpy.context.scene.collection).children.link(c)
    return c


# ---------------------------------------------------------------- materials
def _set(node, name, value):
    if name in node.inputs:
        node.inputs[name].default_value = value


def mat(name, base, rough=0.5, metal=0.0, **kw):
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except Exception:
        pass
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    _set(b, "Base Color", (*base, 1.0))
    _set(b, "Roughness", rough)
    _set(b, "Metallic", metal)
    for k, v in kw.items():
        _set(b, k, v)
    m.diffuse_color = (*base, 1.0)
    return m


def add_grain(m, scale=4000.0, strength=0.12, rough_range=None, stretch=(1, 1, 1)):
    """Procedural micro surface: fine paint grain or (with stretch) brushed metal."""
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = stretch
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = scale
    nz.inputs["Detail"].default_value = 6.0
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], nz.inputs["Vector"])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = strength
    bump.inputs["Distance"].default_value = 0.0002
    nt.links.new(nz.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    if rough_range:
        mr = nt.nodes.new("ShaderNodeMapRange")
        mr.inputs["To Min"].default_value = rough_range[0]
        mr.inputs["To Max"].default_value = rough_range[1]
        nt.links.new(nz.outputs["Fac"], mr.inputs["Value"])
        nt.links.new(mr.outputs["Result"], b.inputs["Roughness"])


def add_radial_aniso(m, amount=0.75):
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    t = nt.nodes.new("ShaderNodeTangent")
    t.direction_type = "RADIAL"
    t.axis = "Z"
    _set(b, "Anisotropic", amount)
    nt.links.new(t.outputs["Tangent"], b.inputs["Tangent"])


def add_smudges(m, socket="Coat Roughness", lo=0.01, hi=0.22, scale=9.0, seed=0.0):
    """Fingerprint/wipe patches: blotchy noise broken up by fine voronoi ridges -> roughness."""
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.noise_dimensions = "4D"
    nz.inputs["W"].default_value = seed
    nz.inputs["Scale"].default_value = scale
    nz.inputs["Detail"].default_value = 4.0
    nz.inputs["Roughness"].default_value = 0.65
    vo = nt.nodes.new("ShaderNodeTexVoronoi")
    vo.feature = "DISTANCE_TO_EDGE"
    vo.inputs["Scale"].default_value = scale * 40
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    nt.links.new(tc.outputs["Object"], vo.inputs["Vector"])
    blot = nt.nodes.new("ShaderNodeMapRange")
    blot.inputs["From Min"].default_value = 0.52
    blot.inputs["From Max"].default_value = 0.72
    nt.links.new(nz.outputs["Fac"], blot.inputs["Value"])
    ridge = nt.nodes.new("ShaderNodeMapRange")
    ridge.inputs["From Min"].default_value = 0.0
    ridge.inputs["From Max"].default_value = 0.12
    ridge.inputs["To Min"].default_value = 0.35
    ridge.inputs["To Max"].default_value = 1.0
    nt.links.new(vo.outputs["Distance"], ridge.inputs["Value"])
    mul = nt.nodes.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    nt.links.new(blot.outputs["Result"], mul.inputs[0])
    nt.links.new(ridge.outputs["Result"], mul.inputs[1])
    out = nt.nodes.new("ShaderNodeMapRange")
    out.inputs["To Min"].default_value = lo
    out.inputs["To Max"].default_value = hi
    nt.links.new(mul.outputs["Value"], out.inputs["Value"])
    nt.links.new(out.outputs["Result"], b.inputs[socket])


def emissive(name, color, strength, base=None, rough=0.35):
    return mat(name, base or tuple(c * 0.4 for c in color), rough,
               **{"Emission Color": (*color, 1.0), "Emission Strength": strength})


def build_materials():
    M = {}
    M["chassis"] = mat("MAT_Chassis_Plastic", (0.012, 0.012, 0.013), 0.42, **{"Coat Weight": 0.15})
    add_grain(M["chassis"], 2500, 0.08)
    M["deckplate"] = mat("MAT_Deck_Paint", (0.018, 0.018, 0.02), 0.5)
    add_grain(M["deckplate"], 5000, 0.10, rough_range=(0.42, 0.58))
    M["mixplate"] = mat("MAT_Mixer_BrushedAlu", (0.045, 0.046, 0.05), 0.34, 1.0, Anisotropic=0.6)
    add_grain(M["mixplate"], 3.0, 0.03, rough_range=(0.24, 0.40), stretch=(2, 700, 2))
    M["housing"] = mat("MAT_Housing_Plastic", (0.010, 0.010, 0.011), 0.38, **{"Coat Weight": 0.3})
    add_grain(M["housing"], 2500, 0.06)
    add_smudges(M["housing"], "Coat Roughness", 0.05, 0.4, 5.0, 4.0)
    M["glass"] = mat("MAT_Screen_Glass", (0.0, 0.0, 0.0), 0.06,
                     **{"Coat Weight": 1.0, "Coat Roughness": 0.01, "Specular IOR Level": 0.35})
    add_smudges(M["glass"], "Coat Roughness", 0.015, 0.28, 7.0, 1.3)
    # display panels sit under a cover glass: dark panel + glossy anti-glare coat with fingerprints
    M["screen"] = mat("MAT_Screen_Off", (0.004, 0.005, 0.007), 0.3,
                      **{"Emission Color": (0.01, 0.015, 0.03, 1), "Emission Strength": 0.12,
                         "Coat Weight": 1.0, "Coat Roughness": 0.02, "Coat IOR": 1.52,
                         "Specular IOR Level": 0.2})
    add_smudges(M["screen"], "Coat Roughness", 0.02, 0.3, 6.0, 9.1)
    M["knob"] = mat("MAT_Knob_SoftTouch", (0.02, 0.02, 0.021), 0.62)
    add_grain(M["knob"], 6000, 0.08)
    M["knob_skirt"] = mat("MAT_Knob_Skirt", (0.008, 0.008, 0.009), 0.35)
    M["knob_cap"] = mat("MAT_Knob_Cap_Alu", (0.42, 0.42, 0.44), 0.36, 1.0)
    add_radial_aniso(M["knob_cap"], 0.8)
    M["print"] = mat("MAT_Print_White", (0.75, 0.75, 0.74), 0.55)
    M["print_grey"] = mat("MAT_Print_Grey", (0.16, 0.16, 0.17), 0.55)
    M["indicator"] = mat("MAT_Knob_Indicator", (0.9, 0.9, 0.9), 0.4)
    M["rubber"] = mat("MAT_Button_Rubber", (0.035, 0.035, 0.037), 0.7)
    add_grain(M["rubber"], 3000, 0.1)
    M["rubber_dark"] = mat("MAT_Rubber_Black", (0.006, 0.006, 0.006), 0.85)
    M["slot"] = mat("MAT_Fader_Slot_Trim", (0.02, 0.02, 0.022), 0.3, 0.6)
    M["void"] = mat("MAT_Void", (0.0, 0.0, 0.0), 1.0)
    M["fadercap"] = mat("MAT_Fader_Cap", (0.03, 0.03, 0.032), 0.48)
    add_grain(M["fadercap"], 5000, 0.08)
    M["jog_silver"] = mat("MAT_Jog_Silver", (0.80, 0.80, 0.82), 0.18, 1.0)
    add_radial_aniso(M["jog_silver"], 0.85)
    add_smudges(M["jog_silver"], "Roughness", 0.16, 0.34, 20.0, 3.1)
    M["jog_top"] = mat("MAT_Jog_Top", (0.012, 0.012, 0.013), 0.5, **{"Coat Weight": 0.25})
    add_grain(M["jog_top"], 1800, 0.25)
    M["jog_collar"] = mat("MAT_Jog_Collar", (0.004, 0.004, 0.005), 0.12, **{"Coat Weight": 0.6})
    add_smudges(M["jog_collar"], "Coat Roughness", 0.02, 0.35, 14.0, 2.2)
    M["chrome"] = mat("MAT_Chrome", (0.9, 0.9, 0.9), 0.08, 1.0)
    M["led_off"] = mat("MAT_LED_Off", (0.03, 0.03, 0.03), 0.3)
    M["led_green"] = emissive("MAT_LED_Green", (0.1, 1.0, 0.25), 6.0)
    M["led_amber"] = emissive("MAT_LED_Amber", (1.0, 0.55, 0.05), 6.0)
    M["led_red"] = emissive("MAT_LED_Red", (1.0, 0.06, 0.04), 6.0)
    M["led_white"] = emissive("MAT_LED_White", (0.85, 0.9, 1.0), 2.5)
    M["led_blue"] = emissive("MAT_LED_Blue", (0.1, 0.45, 1.0), 4.0)
    M["led_green_dim"] = emissive("MAT_LED_Green_Dim", (0.1, 1.0, 0.25), 0.25, base=(0.02, 0.05, 0.025))
    M["led_amber_dim"] = emissive("MAT_LED_Amber_Dim", (1.0, 0.55, 0.05), 0.25, base=(0.05, 0.03, 0.01))
    M["led_red_dim"] = emissive("MAT_LED_Red_Dim", (1.0, 0.06, 0.04), 0.25, base=(0.05, 0.01, 0.01))
    M["floor"] = mat("MAT_Studio_Sweep", (0.04, 0.04, 0.043), 0.5)
    add_grain(M["floor"], 2.5, 0.02, rough_range=(0.38, 0.62))
    M["screw"] = mat("MAT_Screw_BlackOxide", (0.05, 0.05, 0.055), 0.32, 1.0)
    add_radial_aniso(M["screw"], 0.5)
    return M


PAD_COLORS = [(1.0, 0.08, 0.12), (1.0, 0.45, 0.02), (1.0, 0.85, 0.05), (0.15, 1.0, 0.25),
              (0.05, 0.85, 1.0), (0.15, 0.3, 1.0), (0.6, 0.15, 1.0), (1.0, 0.2, 0.7)]


def pad_material(i):
    c = PAD_COLORS[i % 8]
    # backlit silicone: saturated body, light scattered in the pad's own colour, matte skin
    m = mat(f"MAT_Pad_{i}", tuple(0.55 * x for x in c), 0.6,
            **{"Emission Color": (*c, 1.0), "Emission Strength": 0.8, "Specular IOR Level": 0.22,
               "Subsurface Weight": 0.6, "Subsurface Radius": tuple(0.0005 + 0.005 * x for x in c),
               "Subsurface Scale": 1.0})
    add_grain(m, 2200, 0.18, rough_range=(0.5, 0.66))
    return m


# ---------------------------------------------------------------- geometry helpers
def finish(name, bm, coll, material=None, bevel=0.0, seg=3, angle=35, smooth=True):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    if material:
        me.materials.append(material)
    if smooth:
        me.shade_smooth()
    if bevel > 0:
        m = ob.modifiers.new("Bevel", "BEVEL")
        m.width = bevel
        m.segments = seg
        m.limit_method = "ANGLE"
        m.angle_limit = math.radians(angle)
        m.harden_normals = True
    elif smooth:
        me.set_sharp_from_angle(angle=math.radians(angle))
    return ob


def box(name, dims, loc, coll, material, bevel=0.0, seg=3, parent=None):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * dims[0], v.co.y * dims[1], v.co.z * dims[2]))
    ob = finish(name, bm, coll, material, bevel, seg)
    ob.location = loc
    if parent:
        ob.parent = parent
    return ob


def cyl(name, r, h, coll, material, seg=64, knurl=0.0, bevel=0.0, bseg=3, loc=(0, 0, 0), parent=None):
    """Cylinder with its base at local z=0. knurl>0 alternates the rim radius (grip ridges)."""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg,
                          radius1=r, radius2=r, depth=h)
    step = 2 * math.pi / seg
    for v in bm.verts:
        v.co.z += h / 2
        if knurl:
            i = round(math.atan2(v.co.y, v.co.x) / step)
            if i % 2:
                v.co.x *= 1 - knurl
                v.co.y *= 1 - knurl
    ob = finish(name, bm, coll, material, bevel, bseg)
    ob.location = loc
    if parent:
        ob.parent = parent
    return ob


def tube(name, r_in, r_out, h, coll, material, seg=96, loc=(0, 0, 0), parent=None):
    bm = bmesh.new()
    rings = []
    for z in (0.0, h):
        for r in (r_in, r_out):
            rings.append([bm.verts.new((r * math.cos(2 * math.pi * i / seg),
                                        r * math.sin(2 * math.pi * i / seg), z)) for i in range(seg)])
    bi, bo, ti, to = rings
    for i in range(seg):
        j = (i + 1) % seg
        bm.faces.new((ti[i], to[i], to[j], ti[j]))   # top
        bm.faces.new((bi[j], bo[j], bo[i], bi[i]))   # bottom
        bm.faces.new((bo[i], bo[j], to[j], to[i]))   # outer
        bm.faces.new((bi[j], bi[i], ti[i], ti[j]))   # inner
    ob = finish(name, bm, coll, material)
    ob.location = loc
    if parent:
        ob.parent = parent
    return ob


def multi_box(name, items, coll, material):
    """Many small boxes in one mesh: items = [(center, dims), ...]. For printed lines/ticks."""
    bm = bmesh.new()
    for c, d in items:
        res = bmesh.ops.create_cube(bm, size=1.0)
        for v in res["verts"]:
            v.co = Vector((c[0] + v.co.x * d[0], c[1] + v.co.y * d[1], c[2] + v.co.z * d[2]))
    return finish(name, bm, coll, material, smooth=False)


def label(text, x, y, size, coll, material, align="CENTER", z=None, rot=None, extrude=0.0, bold=False):
    cu = bpy.data.curves.new("TXT_" + text, "FONT")
    cu.body = text
    cu.size = size * LABEL_SCALE
    cu.align_x = align
    cu.align_y = "CENTER"
    cu.space_character = 1.12
    cu.extrude = extrude
    if bold:
        cu.offset = size * 0.035
    ob = bpy.data.objects.new("Label_" + text, cu)
    coll.objects.link(ob)
    cu.materials.append(material)
    ob.location = (x, y, PZ + 0.00012 if z is None else z)
    if rot:
        ob.rotation_euler = rot
    return ob


def tag(ob, **props):
    for k, v in props.items():
        ob[k] = v
    return ob


# ---------------------------------------------------------------- controls
def knob(name, x, y, r, h, coll, M, value=None, cap=False):
    value = random.uniform(-0.5, 0.5) if value is None else value
    body = cyl(name, r, h, coll, M["knob"], seg=48, knurl=0.045, bevel=r * 0.14, loc=(x, y, PZ + 0.0012))
    cyl(name + "_Skirt", r * 1.2, 0.0014, coll, M["knob_skirt"], seg=64, bevel=0.0004,
        loc=(x, y, PZ), parent=None)
    if cap:
        cyl(name + "_Cap", r * 0.7, 0.0008, coll, M["knob_cap"], seg=64, bevel=0.0002,
            loc=(0, 0, h - 0.0003), parent=body)
    box(name + "_Indicator", (0.0011, r * 0.62, 0.0004), (0, r * 0.5, h + 0.00005), coll,
        M["indicator"], parent=body)
    body.rotation_euler.z = -value * math.radians(270)
    return tag(body, control="knob", value=value, range_deg=270.0)


def fader(name, x, y, travel, coll, M, horizontal=False, value=0.5):
    """travel = full cap travel in metres. Cap moves along local Y (or X if horizontal)."""
    L = travel + 0.012
    sx, sy = (L, 0.0085) if horizontal else (0.0085, L)
    box(name + "_Slot", (sx, sy, 0.0007), (x, y, PZ + 0.00035), coll, M["slot"], bevel=0.0003)
    gx, gy = (travel + 0.004, 0.0022) if horizontal else (0.0022, travel + 0.004)
    box(name + "_Slit", (gx, gy, 0.0002), (x, y, PZ + 0.0008), coll, M["void"])
    cw, cd, ch = 0.019, 0.011, 0.011
    if horizontal:
        cw, cd = cd, cw
    t = (value - 0.5) * travel
    cx, cy = (x + t, y) if horizontal else (x, y + t)
    cap = box(name + "_Cap", (cw, cd, ch), (cx, cy, PZ + 0.0016 + ch / 2), coll, M["fadercap"],
              bevel=0.0018, seg=4)
    lw, ld = (0.0009, cd * 0.92) if horizontal else (cw * 0.92, 0.0009)
    box(name + "_Cap_Line", (lw, ld, 0.0003), (0, 0, ch / 2 + 0.00005), coll, M["print"], parent=cap)
    axis = "X" if horizontal else "Y"
    c0 = x if horizontal else y
    return tag(cap, control="fader", axis=axis, value=value,
               min=c0 - travel / 2, max=c0 + travel / 2)


def ticks(name, x, y, travel, n, coll, M, side=1, horizontal=False):
    items = []
    for i in range(n):
        t = -travel / 2 + travel * i / (n - 1)
        major = i in (0, n // 2, n - 1)
        ln = 0.0045 if major else 0.0028
        if horizontal:
            items.append(((x + t, y + side * (0.0075 + ln / 2), PZ + 0.0001), (0.0005, ln, 0.0002)))
        else:
            items.append(((x + side * (0.0075 + ln / 2), y + t, PZ + 0.0001), (ln, 0.0005, 0.0002)))
    return multi_box(name, items, coll, M["print_grey"])


def rect_button(name, x, y, w, d, coll, M, led=None, h=0.0042, text=None, text_size=0.0022):
    b = box(name, (w, d, h), (x, y, PZ + h / 2), coll, M["rubber"], bevel=min(w, d) * 0.22, seg=4)
    if led:
        box(name + "_LED", (w * 0.55, 0.0012, 0.0002), (0, d / 2 - 0.0018, h / 2 + 0.00005), coll,
            M[led], parent=b)
    if text:
        label(text, x, y + d / 2 + 0.0032, text_size, coll, M["print"])
    return tag(b, control="button", lit=bool(led))


def round_button(name, x, y, r, coll, M, h=0.0045, ring=None):
    b = cyl(name, r, h, coll, M["rubber"], seg=48, bevel=r * 0.25, bseg=4, loc=(x, y, PZ))
    if ring:
        tube(name + "_LEDRing", r + 0.0004, r + 0.0016, 0.0006, coll, M[ring], seg=96, loc=(x, y, PZ))
    return tag(b, control="button")


# ---------------------------------------------------------------- assemblies
def build_chassis(M, C):
    c = C["chassis"]
    box("Chassis_Body", (W, D, BODY_TOP - FOOT_H), (0, 0, FOOT_H + (BODY_TOP - FOOT_H) / 2), c,
        M["chassis"], bevel=0.007, seg=4)
    # faceplates: two painted deck plates and a brushed mixer plate, with real panel gaps
    py = (PLATE_Y0 + PLATE_Y1) / 2
    pd = PLATE_Y1 - PLATE_Y0
    deck_w = (W / 2 - 0.012) - (MIX_HALF + 0.003)
    for side, nm in ((-1, "Plate_DeckA"), (1, "Plate_DeckB")):
        cx = side * (MIX_HALF + 0.003 + deck_w / 2)
        box(nm, (deck_w, pd, PLATE_T), (cx, py, BODY_TOP + PLATE_T / 2), c, M["deckplate"], bevel=0.0008)
    box("Plate_Mixer", (2 * MIX_HALF, pd, PLATE_T), (0, py, BODY_TOP + PLATE_T / 2), c,
        M["mixplate"], bevel=0.0008)
    # black-oxide hex screws holding each faceplate
    plates = [(-(MIX_HALF + 0.003 + deck_w / 2), deck_w), (MIX_HALF + 0.003 + deck_w / 2, deck_w),
              (0.0, 2 * MIX_HALF)]
    n = 0
    for pcx, pw in plates:
        for sx in (-1, 1):
            for sy in (PLATE_Y0 + 0.0065, PLATE_Y1 - 0.0065):
                n += 1
                sc = cyl(f"Screw_{n:02d}", 0.0021, 0.0005, c, M["screw"], seg=32, bevel=0.0003,
                         loc=(pcx + sx * (pw / 2 - 0.0065), sy, PZ))
                hx = cyl(f"Screw_{n:02d}_Socket", 0.00085, 0.0003, c, M["void"], seg=6,
                         loc=(0, 0, 0.0003), parent=sc)
                hx.rotation_euler.z = random.uniform(0, math.pi)
    # rubber feet
    for fx in (-0.40, 0.40):
        for fy in (-0.20, 0.20):
            cyl("Foot", 0.014, FOOT_H, c, M["rubber_dark"], seg=32, bevel=0.0015, loc=(fx, fy, 0))
    # front panel: headphone jacks + mic/aux hints
    for i, (jx, rr) in enumerate(((-0.395, 0.0065), (-0.365, 0.0042))):
        j = cyl(f"Jack_Phones_{i}", rr, 0.0025, c, M["chrome"], seg=48, bevel=0.0005,
                loc=(jx, -D / 2 + 0.0005, 0.032))
        j.rotation_euler.x = math.radians(90)
        h = cyl(f"Jack_Phones_{i}_Hole", rr * 0.55, 0.0030, c, M["void"], seg=32,
                loc=(jx, -D / 2 + 0.0002, 0.032))
        h.rotation_euler.x = math.radians(90)
    label("PHONES", -0.38, -D / 2 - 0.0002, 0.0035, c, M["print"], z=0.020, rot=(math.radians(90), 0, 0))


def build_screen(M, C):
    """Full-width display strip in a raked housing along the back edge (left empty for the app)."""
    c = C["screen"]
    y0, y1, yb = PLATE_Y1 + 0.002, 0.232, D / 2
    z0, z1 = PZ + 0.001, 0.096
    prof = [(y0, FOOT_H + 0.004), (y0, z0), (y1, z1), (yb, z1 - 0.002), (yb, FOOT_H + 0.004)]
    bm = bmesh.new()
    left = [bm.verts.new((-W / 2, py, pz)) for py, pz in prof]
    right = [bm.verts.new((W / 2, py, pz)) for py, pz in prof]
    bm.faces.new(list(reversed(left)))
    bm.faces.new(right)
    n = len(prof)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((left[i], left[j], right[j], right[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    finish("Screen_Housing", bm, c, M["housing"], bevel=0.006, seg=5, angle=20)
    # glass + active area on the raked face
    ang = math.atan2(z1 - z0, y1 - y0)
    slope = math.hypot(y1 - y0, z1 - z0)
    mid = Vector(((y0 + y1) / 2, (z0 + z1) / 2))
    nrm = Vector((-math.sin(ang), math.cos(ang)))
    def plate(name, w, h, off, material):
        bm = bmesh.new()
        bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=0.5, calc_uvs=True)
        for v in bm.verts:
            v.co.x *= w
            v.co.y *= h
        ob = finish(name, bm, c, material, smooth=False)
        p = mid + nrm * off
        ob.location = (0, p.x, p.y)
        ob.rotation_euler.x = ang
        return ob
    plate("Screen_Glass", W - 0.03, slope - 0.010, 0.0004, M["glass"])
    scr = plate("Screen_Main", W - 0.07, slope - 0.022, 0.0006, M["screen"])
    tag(scr, control="display", note="App draws waveforms/browser here; UVs span the active area.",
        width_mm=round((W - 0.07) * 1000, 1), height_mm=round((slope - 0.022) * 1000, 1))


def build_jog(prefix, x, y, M, coll):
    base_z = PZ
    cyl(prefix + "_Jog_Collar", 0.1035, 0.0035, coll, M["jog_collar"], seg=128, bevel=0.0012,
        loc=(x, y, base_z))
    tube(prefix + "_Jog_Gap", 0.0965, 0.1, 0.0036, coll, M["void"], seg=128, loc=(x, y, base_z + 0.0001))
    pivot = bpy.data.objects.new(prefix + "_Jog", None)
    pivot.empty_display_type = "CIRCLE"
    pivot.empty_display_size = 0.1
    pivot.rotation_euler.x = 0
    coll.objects.link(pivot)
    pivot.location = (x, y, base_z + 0.0035)
    tag(pivot, control="jog", note="Rotate around local Z; children turn with it.")
    cyl(prefix + "_Jog_Ring", 0.0975, 0.0165, coll, M["jog_silver"], seg=240, knurl=0.0035,
        bevel=0.0009, loc=(0, 0, 0), parent=pivot)
    cyl(prefix + "_Jog_Platter", 0.0925, 0.0016, coll, M["jog_top"], seg=128, bevel=0.0005,
        loc=(0, 0, 0.0163), parent=pivot)
    box(prefix + "_Jog_Marker", (0.0022, 0.012, 0.0003), (0, 0.078, 0.0181), coll, M["print"], parent=pivot)
    # fixed centre display (does not rotate)
    top = base_z + 0.0035 + 0.0181
    cyl(prefix + "_JogDisplay_Bezel", 0.047, 0.0012, coll, M["jog_collar"], seg=96, bevel=0.0004,
        loc=(x, y, top))
    tube(prefix + "_JogDisplay_LEDRing", 0.0432, 0.0458, 0.0003, coll, M["led_white"], seg=128,
         loc=(x, y, top + 0.0012))
    d = cyl(prefix + "_JogDisplay", 0.042, 0.0004, coll, M["screen"], seg=96, loc=(x, y, top + 0.0012))
    tag(d, control="display")


def build_deck(prefix, side, M, C):
    coll = C[prefix]
    dx = side * DECK_X
    build_jog(prefix, dx, JOG_Y, M, coll)

    # tempo fader on the right of each deck
    px = dx + 0.118
    fader(prefix + "_Tempo", px, JOG_Y, 0.11, coll, M, value=0.5)
    ticks(prefix + "_Tempo_Ticks", px, JOG_Y, 0.11, 13, coll, M, side=-1)
    label("TEMPO", px, JOG_Y + 0.071, 0.0024, coll, M["print"])
    rect_button(prefix + "_TempoRange", px, JOG_Y + 0.082, 0.014, 0.007, coll, M, text=None)
    rect_button(prefix + "_MasterTempo", px, JOG_Y - 0.077, 0.014, 0.007, coll, M, led="led_amber")
    label("MT", px, JOG_Y - 0.0865, 0.0022, coll, M["print"])

    # play / cue + sync / shift (bottom-left of each deck)
    bx = dx - 0.112
    play = round_button(prefix + "_Play", bx, -0.160, 0.0175, coll, M, h=0.006, ring="led_green")
    cue = round_button(prefix + "_Cue", bx, -0.117, 0.0175, coll, M, h=0.006, ring="led_amber")
    # play/pause glyph
    bm = bmesh.new()
    s = 0.0055
    vs = [bm.verts.new(p) for p in ((-s * 0.75, -s * 0.8, 0), (-s * 0.75, s * 0.8, 0), (s * 0.35, 0, 0))]
    bm.faces.new(vs)
    for ox in (s * 0.65, s * 1.05):
        q = [bm.verts.new(p) for p in ((ox, -s * 0.75, 0), (ox + s * 0.22, -s * 0.75, 0),
                                       (ox + s * 0.22, s * 0.75, 0), (ox, s * 0.75, 0))]
        bm.faces.new(q)
    g = finish(prefix + "_Play_Glyph", bm, coll, M["print"], smooth=False)
    g.parent = play
    g.location = (-0.0015, 0, 0.0061)
    lc = label("CUE", 0, 0, 0.0042, coll, M["print"], z=0.0061, bold=True)
    lc.name = prefix + "_Cue_Glyph"
    lc.parent = cue
    lc.location = (0, 0, 0.0061)
    round_button(prefix + "_Shift", bx - 0.0105, -0.084, 0.0062, coll, M, ring=None)
    round_button(prefix + "_Sync", bx + 0.0105, -0.084, 0.0062, coll, M, ring="led_blue")
    label("SHIFT", bx - 0.0105, -0.0945, 0.0021, coll, M["print"])
    label("SYNC", bx + 0.0105, -0.0945, 0.0021, coll, M["print"])

    # performance pads 2x4 + mode buttons
    pcx = dx + 0.02
    cols = [-0.06, -0.02, 0.02, 0.06]
    rows = [-0.118, -0.158]
    box(prefix + "_Pad_Bed", (0.166, 0.086, 0.0012), (pcx, -0.138, PZ + 0.0006), coll,
        M["rubber_dark"], bevel=0.003, seg=4)
    k = 0
    for ry in rows:
        for cx_ in cols:
            p = box(f"{prefix}_Pad_{k + 1}", (0.0345, 0.0345, 0.0072), (pcx + cx_, ry, PZ + 0.0012 + 0.0036),
                    coll, pad_material(k if side < 0 else 7 - k), bevel=0.0035, seg=5)
            tag(p, control="pad", index=k + 1, velocity=True)
            k += 1
    for cx_, txt in zip(cols, ("HOT CUE", "PAD FX", "BEAT JUMP", "SAMPLER")):
        rect_button(f"{prefix}_PadMode_{txt.replace(' ', '')}", pcx + cx_, -0.087, 0.030, 0.0075, coll, M,
                    led="led_white" if txt == "HOT CUE" else "led_off")
        label(txt, pcx + cx_, -0.0955, 0.0021, coll, M["print"])

    # top row: browse encoder + loop / beat jump buttons
    knob(prefix + "_Browse", bx, 0.145, 0.0105, 0.013, coll, M, value=0.0, cap=True)
    names = ("IN", "OUT", "RELOOP", "4 BEAT", "< JUMP", "JUMP >", "SLIP")
    for i, txt in enumerate(names):
        rect_button(f"{prefix}_Top_{txt.replace(' ', '').replace('<', 'Back').replace('>', 'Fwd')}",
                    dx - 0.075 + 0.03 * i, 0.143, 0.024, 0.0085, coll, M,
                    led="led_amber_dim" if i < 3 else None, text=txt, text_size=0.0021)
    label("DECK 1" if side < 0 else "DECK 2", dx - 0.112, 0.118, 0.0032, coll, M["print"], bold=True)
    label("BROWSE", bx, 0.1595, 0.0019, coll, M["print"])


def build_mixer(M, C):
    coll = C["mixer"]
    rows = (("TRIM", 0.135, 0.0085), ("HI", 0.103, 0.0095), ("MID", 0.073, 0.0095),
            ("LOW", 0.043, 0.0095), ("COLOR", 0.006, 0.0115))
    for ci, cx in enumerate(CH_X, start=1):
        ch = f"Mixer_Ch{ci}"
        for nm, ky, kr in rows:
            knob(f"{ch}_{nm}", cx, ky, kr, 0.015 if nm != "COLOR" else 0.016, coll, M,
                 value=0.0 if nm != "TRIM" else random.uniform(-0.1, 0.25), cap=(nm == "COLOR"))
            label(nm, cx, ky + kr + 0.0040, 0.0021, coll, M["print"])
        # channel cue
        rect_button(f"{ch}_Cue", cx, -0.032, 0.020, 0.010, coll, M, led="led_amber" if ci == 2 else "led_amber_dim")
        label("CUE", cx, -0.0245, 0.0021, coll, M["print"])
        # level meter (11 segments)
        lit = random.randint(5, 9) if ci in (1, 2) else 0
        for s in range(11):
            colr = "green" if s < 8 else ("amber" if s < 10 else "red")
            m_ = M[f"led_{colr}"] if s < lit else M[f"led_{colr}_dim"]
            box(f"{ch}_Meter_{s + 1:02d}", (0.0032, 0.0021, 0.0005),
                (cx + 0.021, 0.028 + s * 0.0098, PZ + 0.00025), coll, m_)
        # channel fader
        fader(f"{ch}_Fader", cx, -0.105, 0.07, coll, M, value=(0.8 if ci in (1, 2) else 0.0))
        ticks(f"{ch}_Fader_Ticks", cx, -0.105, 0.07, 11, coll, M, side=1)
        label(str(ci), cx, -0.155, 0.0048, coll, M["print"], bold=True)

    # crossfader
    fader("Mixer_Crossfader", 0, -0.195, 0.08, coll, M, horizontal=True, value=0.38)
    ticks("Mixer_Crossfader_Ticks", 0, -0.195, 0.08, 9, coll, M, side=1, horizontal=True)

    # headphones (left) / master (right) column
    for nm, ky, sx in (("PHONES MIX", 0.135, -1), ("PHONES LEVEL", 0.103, -1),
                       ("MASTER", 0.135, 1), ("BOOTH", 0.103, 1)):
        knob(f"Mixer_{nm.replace(' ', '')}", sx * 0.132, ky, 0.0085, 0.015, coll, M,
             value=random.uniform(-0.1, 0.3))
        label(nm, sx * 0.132, ky + 0.0128, 0.0019, coll, M["print"])
    for s in range(11):
        colr = "green" if s < 8 else ("amber" if s < 10 else "red")
        for li, lx in enumerate((0.128, 0.136)):
            on = s < (7 if li == 0 else 6)
            box(f"Mixer_MasterMeter_{'LR'[li]}_{s + 1:02d}", (0.0034, 0.0021, 0.0005),
                (lx, -0.005 + s * 0.0062, PZ + 0.00025), coll,
                M[f"led_{colr}"] if on else M[f"led_{colr}_dim"])
    rect_button("Mixer_MasterCue", -0.132, 0.066, 0.016, 0.009, coll, M, led="led_amber_dim")
    label("MASTER CUE", -0.132, 0.0565, 0.0018, coll, M["print"])

    # printed section lines
    lines = []
    for lx in (-0.062, 0.0, 0.062):
        lines.append(((lx, 0.05, PZ + 0.0001), (0.0004, 0.19, 0.0002)))
    for lx in (-0.1165, 0.1165):
        lines.append(((lx, 0.05, PZ + 0.0001), (0.0004, 0.19, 0.0002)))
    multi_box("Mixer_Print_Lines", lines, coll, M["print_grey"])

    # brand
    logo = label("OPEN LIFE DJ", 0, -0.2215, 0.0068, coll, M["print"], bold=True, extrude=0.00005)
    logo.name = "Brand_Logo"
    label("4-CHANNEL ALL-IN-ONE DJ SYSTEM", -0.38, -0.226, 0.0026, coll, M["print_grey"], align="LEFT")


def build_studio(M, C):
    c = C["studio"]
    # seamless sweep
    prof = [(-3.0, 0.0), (0.6, 0.0)]
    R = 1.2
    for i in range(1, 13):
        a = math.radians(90 * i / 12)
        prof.append((0.6 + R * math.sin(a), R * (1 - math.cos(a))))
    prof.append((0.6 + R, 3.0))
    bm = bmesh.new()
    L = [bm.verts.new((-4, y, z)) for y, z in prof]
    Rr = [bm.verts.new((4, y, z)) for y, z in prof]
    for i in range(len(prof) - 1):
        bm.faces.new((L[i], Rr[i], Rr[i + 1], L[i + 1]))
    finish("Studio_Sweep", bm, c, M["floor"], angle=60)

    target = Vector((0, 0.0, 0.05))
    def area(name, loc, power, size, size_y=None, color=(1, 1, 1)):
        ld = bpy.data.lights.new(name, "AREA")
        ld.energy = power
        ld.color = color
        ld.shape = "RECTANGLE"
        ld.size = size
        ld.size_y = size_y or size
        ob = bpy.data.objects.new(name, ld)
        c.objects.link(ob)
        ob.location = loc
        ob.rotation_euler = (target - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        return ob
    area("Light_Key", (-0.9, -0.8, 1.2), 30, 1.0, 0.6, (1.0, 0.97, 0.93))
    area("Light_Fill", (1.1, -0.7, 0.5), 6, 0.8, 0.8, (0.9, 0.95, 1.0))
    area("Light_Rim", (1.05, 0.85, 0.32), 22, 1.4, 0.3)
    area("Light_Top", (0.0, -0.15, 1.5), 12, 1.6, 0.9)

    world = bpy.context.scene.world or bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    try:
        world.use_nodes = True
    except Exception:
        pass
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.012, 0.012, 0.014, 1)
    bg.inputs["Strength"].default_value = 1.0


def build_cameras(C):
    c = C["studio"]
    def cam(name, loc, target, lens=50, ortho=None):
        cd = bpy.data.cameras.new(name)
        cd.lens = lens
        cd.clip_start = 0.01
        cd.clip_end = 20
        if ortho:
            cd.type = "ORTHO"
            cd.ortho_scale = ortho
        ob = bpy.data.objects.new(name, cd)
        c.objects.link(ob)
        ob.location = loc
        ob.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        return ob
    hero = cam("Camera_Hero", (-0.868, -1.652, 1.148), (0.0, 0.0, 0.03), lens=70)
    hero.data.dof.use_dof = True
    hero.data.dof.focus_distance = (Vector((-0.05, -0.03, 0.06)) - hero.location).length
    hero.data.dof.aperture_fstop = 5.6
    # macro detail shot across deck A pads into the mixer
    det = cam("Camera_Detail", (-0.42, -0.42, 0.20), (-0.16, -0.08, 0.06), lens=85)
    det.data.dof.use_dof = True
    det.data.dof.focus_distance = (Vector((-0.19, -0.11, 0.07)) - det.location).length
    det.data.dof.aperture_fstop = 5.6
    cam("Camera_Front", (0.0, -1.0, 0.62), (0.0, -0.01, 0.04), lens=55)
    top = cam("Camera_UI_Top", (0.0, 0.0, 1.2), (0.0, 0.0, 0.0), ortho=0.94)
    top.rotation_euler = (0, 0, 0)
    bpy.context.scene.camera = hero


def render_settings():
    sc = bpy.context.scene
    for eng in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
        try:
            sc.render.engine = eng
            break
        except TypeError:
            continue
    ee = sc.eevee
    for k, v in (("use_raytracing", True), ("use_shadows", True), ("taa_render_samples", 128),
                 ("use_gtao", True), ("shadow_ray_count", 2), ("shadow_step_count", 8)):
        try:
            setattr(ee, k, v)
        except Exception:
            pass
    try:
        ee.ray_tracing_options.resolution_scale = "1"
    except Exception:
        pass
    sc.render.resolution_x, sc.render.resolution_y = 1920, 1080
    try:
        sc.view_settings.view_transform = "AgX"
        sc.view_settings.look = "AgX - Medium High Contrast"
    except Exception:
        pass
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.length_unit = "MILLIMETERS"
    try:
        sc.cycles.samples = 256
        sc.cycles.use_denoising = True
    except Exception:
        pass


def build():
    reset()
    M = build_materials()
    root = bpy.context.scene.collection
    C = {
        "chassis": collection("OLDJ_Chassis"),
        "screen": collection("OLDJ_Screen"),
        "DeckA": collection("OLDJ_DeckA"),
        "DeckB": collection("OLDJ_DeckB"),
        "mixer": collection("OLDJ_Mixer"),
        "studio": collection("Studio"),
    }
    build_chassis(M, C)
    build_screen(M, C)
    build_deck("DeckA", -1, M, C)
    build_deck("DeckB", 1, M, C)
    build_mixer(M, C)
    build_studio(M, C)
    build_cameras(C)
    render_settings()
    print("built", len(bpy.data.objects), "objects")


build()
