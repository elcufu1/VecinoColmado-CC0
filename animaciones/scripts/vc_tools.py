"""Utilidades comunes: cargar rig, renders de prueba y hojas de contacto."""
import os
import sys
import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(__file__))
import vc_core as C  # noqa: E402
import vc_scene as S  # noqa: E402
import vc_pose as VP  # noqa: E402


def init(engine='WORKBENCH', res=(1280, 720), table=True, chair=True):
    scene = bpy.context.scene
    S.setup_render(scene, engine, res)
    rig = C.Rig()
    for pb in rig.arm.pose.bones:
        pb.rotation_mode = 'QUATERNION'
    box = bpy.data.materials['VecinoColmado_CC0.boxer']
    S.wb_color(box, tuple(box.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value))
    objs = {}
    if table and bpy.data.objects.get('Mesa_pano') is None:
        objs['table'] = S.build_table(scene)
    if chair and bpy.data.objects.get('Silla_asiento') is None:
        objs['chair'] = S.build_chair(scene)
    return scene, rig


def render_still(scene, cam, path):
    scene.camera = cam
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


def hide_preview(hide=True, names_prefix=('Mesa', 'Silla')):
    for ob in bpy.data.objects:
        if ob.name.startswith(names_prefix):
            ob.hide_render = hide
            ob.hide_viewport = hide
