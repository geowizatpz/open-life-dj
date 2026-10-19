"""Render the top-down controller image the app uses as its background (M0).

  /Applications/Blender.app/Contents/MacOS/Blender -b blender/open_life_dj_controller.blend \
      -P blender/export_app_background.py -- [width] [samples]

Writes assets/controller_top.png (8-bit RGB) with the aspect of Camera_UI_Top's render size.
"""
import bpy, os, sys

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
width = int(argv[0]) if argv else 2400
samples = int(argv[1]) if len(argv) > 1 else 256
root = os.path.dirname(os.path.dirname(bpy.data.filepath))
out = os.path.join(root, "assets", "controller_top.png")
os.makedirs(os.path.dirname(out), exist_ok=True)

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
            break
    except TypeError:
        continue
sc.cycles.samples = samples
sc.cycles.use_denoising = True
sc.camera = bpy.data.objects["Camera_UI_Top"]
sc.render.resolution_percentage = 100
sc.render.resolution_x = width
sc.render.resolution_y = round(width * 1747 / 3200)
sc.render.image_settings.file_format = "PNG"
sc.render.image_settings.color_mode = "RGB"
sc.render.image_settings.color_depth = "8"
sc.render.image_settings.compression = 90
sc.render.filepath = out
bpy.ops.render.render(write_still=True)
print("wrote", out, sc.render.resolution_x, "x", sc.render.resolution_y)
