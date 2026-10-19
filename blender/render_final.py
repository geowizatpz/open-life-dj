"""Cycles path-traced stills of the controller, run headless:

  /Applications/Blender.app/Contents/MacOS/Blender -b "blender/open_life_dj_controller.blend" \
      -P "blender/render_final.py" -- [samples] [cameras...]

Defaults: 384 samples, cameras Camera_Hero Camera_Detail Camera_UI_Top. Writes to blender/renders/.
"""
import bpy, os, sys, time

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
samples = int(argv[0]) if argv else 384
cams = argv[1:] or ["Camera_Hero", "Camera_Detail", "Camera_UI_Top"]
out = os.path.join(os.path.dirname(bpy.data.filepath), "renders")
os.makedirs(out, exist_ok=True)

sc = bpy.context.scene
sc.render.engine = "CYCLES"
prefs = bpy.context.preferences.addons["cycles"].preferences
for dev_type in ("METAL", "OPTIX", "CUDA", "HIP", "ONEAPI"):
    try:
        prefs.compute_device_type = dev_type
        prefs.get_devices()
        if any(d.type == dev_type for d in prefs.devices):
            for d in prefs.devices:
                d.use = True
            sc.cycles.device = "GPU"
            print("device:", dev_type)
            break
    except TypeError:
        continue

cy = sc.cycles
cy.samples = samples
cy.use_adaptive_sampling = True
cy.adaptive_threshold = 0.01
cy.use_denoising = True
cy.max_bounces = 12
cy.glossy_bounces = 6
cy.transmission_bounces = 8
cy.caustics_reflective = False
cy.caustics_refractive = False
cy.blur_glossy = 0.5
sc.render.film_transparent = False
sc.render.resolution_percentage = 100
sc.render.image_settings.file_format = "PNG"
sc.render.image_settings.color_depth = "16"

sizes = {"Camera_UI_Top": (3200, 1747)}
for name in cams:
    sc.camera = bpy.data.objects[name]
    sc.render.resolution_x, sc.render.resolution_y = sizes.get(name, (2560, 1440))
    sc.render.filepath = os.path.join(out, f"{name.replace('Camera_', '').lower()}_cycles.png")
    t = time.time()
    bpy.ops.render.render(write_still=True)
    print(f"rendered {name} in {time.time() - t:.0f}s -> {sc.render.filepath}")
