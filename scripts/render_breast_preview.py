import bpy
import math
import os
from mathutils import Vector


KEEP_OBJECTS = {"Body_Tpose", "Breast_Base"}


def look_at(obj, target):
    direction = target - obj.location
    quat = direction.to_track_quat("-Z", "Y")
    obj.rotation_euler = quat.to_euler()


def ensure_camera(name, location, ortho_scale):
    camera_data = bpy.data.cameras.new(name)
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = ortho_scale
    camera_obj = bpy.data.objects.new(name, camera_data)
    bpy.context.scene.collection.objects.link(camera_obj)
    camera_obj.location = location
    look_at(camera_obj, Vector((0.0, 0.0, 1.18)))
    return camera_obj


def main():
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = 1200
    scene.render.resolution_y = 1600
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_xray = False

    for obj in scene.objects:
        obj.hide_render = obj.name not in KEEP_OBJECTS
        obj.hide_viewport = obj.name not in KEEP_OBJECTS

    result_dir = bpy.path.abspath("//Result")
    os.makedirs(result_dir, exist_ok=True)

    front_camera = ensure_camera("BreastPreviewFront", Vector((0.0, -3.0, 1.18)), 1.25)
    side_camera = ensure_camera("BreastPreviewSide", Vector((3.0, 0.0, 1.18)), 1.10)

    scene.camera = front_camera
    scene.render.filepath = os.path.join(result_dir, "breast_preview_front.png")
    bpy.ops.render.render(write_still=True)
    print(f"rendered={scene.render.filepath}")

    scene.camera = side_camera
    scene.render.filepath = os.path.join(result_dir, "breast_preview_side.png")
    bpy.ops.render.render(write_still=True)
    print(f"rendered={scene.render.filepath}")


if __name__ == "__main__":
    main()
