"""Escena de previsualización: mesa, silla, fichas, luces, cámaras y render Workbench/Eevee."""
import math
import bpy
from mathutils import Vector, Matrix

# Medidas de referencia (metros). Origen del personaje = pies de pie frente a la silla.
TABLE_SIZE = 1.15
TABLE_TOP = 0.806          # paño
TABLE_THICK = 0.035
RAIL_TOP = 0.839           # riel superior
RAIL_W = 0.045
TABLE_NEAR_Y = -0.19       # borde cercano de la mesa (lado del personaje)
TABLE_CY = TABLE_NEAR_Y - TABLE_SIZE / 2
SEAT_Z = 0.46
SEAT_W, SEAT_D = 0.44, 0.42
SEAT_CY = 0.14             # centro del asiento (silla arrimada, posición sentada canónica)
SEAT_CY_OUT = 0.27         # silla separada (antes de sentarse / después de levantarse)
SEAT_THICK = 0.035
BACK_Y = SEAT_CY + SEAT_D / 2  # respaldo (relativo a la silla arrimada)
TILE = (0.045, 0.090, 0.014)   # ancho (x), largo (y), grosor (z) de la ficha de prueba

PREVIEW_COLL = 'Previsualizacion'


def _mat(name, rgba, rough=0.6):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.diffuse_color = rgba
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get('Principled BSDF')
    if bsdf:
        bsdf.inputs['Base Color'].default_value = rgba
        bsdf.inputs['Roughness'].default_value = rough
    wb_color(m, rgba)
    return m


def wb_color(m, rgba):
    """Nodo de imagen de color liso, SIN conectar, activo: solo lo usa Workbench (modo Texture).
    No altera el sombreado de Eevee/Cycles ni la exportación glTF."""
    nt = m.node_tree
    node = nt.nodes.get('WB_color')
    if node is None:
        img = bpy.data.images.new('WB_' + m.name, 4, 4)
        img.generated_color = rgba
        img.pack()
        node = nt.nodes.new('ShaderNodeTexImage')
        node.name = 'WB_color'
        node.label = 'Solo Workbench (no conectado)'
        node.image = img
        node.location = (-700, -400)
    nt.nodes.active = node


def _box(name, size, loc, mat, coll):
    me = bpy.data.meshes.new(name)
    sx, sy, sz = (s / 2 for s in size)
    vs = [(-sx, -sy, -sz), (sx, -sy, -sz), (sx, sy, -sz), (-sx, sy, -sz),
          (-sx, -sy, sz), (sx, -sy, sz), (sx, sy, sz), (-sx, sy, sz)]
    fs = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    me.from_pydata(vs, [], fs)
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    ob.location = loc
    coll.objects.link(ob)
    return ob


def preview_collection(scene):
    coll = bpy.data.collections.get(PREVIEW_COLL)
    if coll is None:
        coll = bpy.data.collections.new(PREVIEW_COLL)
        scene.collection.children.link(coll)
    return coll


def build_table(scene):
    coll = preview_collection(scene)
    wood = _mat('Madera_mesa', (0.30, 0.17, 0.08, 1))
    felt = _mat('Pano_mesa', (0.05, 0.28, 0.12, 1), 0.9)
    objs = []
    cx, cy = 0.0, TABLE_CY
    objs.append(_box('Mesa_pano', (TABLE_SIZE - 2 * RAIL_W, TABLE_SIZE - 2 * RAIL_W, TABLE_THICK),
                     (cx, cy, TABLE_TOP - TABLE_THICK / 2), felt, coll))
    rh = RAIL_TOP - (TABLE_TOP - TABLE_THICK)
    rz = (RAIL_TOP + TABLE_TOP - TABLE_THICK) / 2
    objs.append(_box('Mesa_riel_cerca', (TABLE_SIZE, RAIL_W, rh), (cx, TABLE_NEAR_Y - RAIL_W / 2, rz), wood, coll))
    objs.append(_box('Mesa_riel_lejos', (TABLE_SIZE, RAIL_W, rh), (cx, TABLE_NEAR_Y - TABLE_SIZE + RAIL_W / 2, rz), wood, coll))
    objs.append(_box('Mesa_riel_izq', (RAIL_W, TABLE_SIZE, rh), (TABLE_SIZE / 2 - RAIL_W / 2, cy, rz), wood, coll))
    objs.append(_box('Mesa_riel_der', (RAIL_W, TABLE_SIZE, rh), (-TABLE_SIZE / 2 + RAIL_W / 2, cy, rz), wood, coll))
    leg_h = TABLE_TOP - TABLE_THICK
    for i, (sx, sy) in enumerate([(1, 1), (-1, 1), (1, -1), (-1, -1)]):
        objs.append(_box(f'Mesa_pata_{i}', (0.06, 0.06, leg_h),
                         (sx * (TABLE_SIZE / 2 - 0.06), cy + sy * (TABLE_SIZE / 2 - 0.06), leg_h / 2), wood, coll))
    return objs


def build_chair(scene):
    coll = preview_collection(scene)
    wood = _mat('Madera_silla', (0.42, 0.26, 0.12, 1))
    objs = [_box('Silla_asiento', (SEAT_W, SEAT_D, SEAT_THICK), (0, SEAT_CY, SEAT_Z - SEAT_THICK / 2), wood, coll)]
    lh = SEAT_Z - SEAT_THICK
    for i, (sx, sy) in enumerate([(1, 1), (-1, 1), (1, -1), (-1, -1)]):
        objs.append(_box(f'Silla_pata_{i}', (0.035, 0.035, lh),
                         (sx * (SEAT_W / 2 - 0.03), SEAT_CY + sy * (SEAT_D / 2 - 0.03), lh / 2), wood, coll))
    objs.append(_box('Silla_respaldo', (SEAT_W, 0.03, 0.42), (0, BACK_Y + 0.015, SEAT_Z + 0.21 + 0.04), wood, coll))
    for i, sx in enumerate([1, -1]):
        objs.append(_box(f'Silla_poste_{i}', (0.035, 0.035, 0.5), (sx * (SEAT_W / 2 - 0.03), BACK_Y + 0.015, SEAT_Z + 0.25), wood, coll))
    return objs


PIPS = {0: [], 1: [(0, 0)], 2: [(-1, -1), (1, 1)], 3: [(-1, -1), (0, 0), (1, 1)],
        4: [(-1, -1), (-1, 1), (1, -1), (1, 1)], 5: [(-1, -1), (-1, 1), (0, 0), (1, -1), (1, 1)],
        6: [(-1, -1), (-1, 0), (-1, 1), (1, -1), (1, 0), (1, 1)]}


def make_tile(scene, name='Ficha', vals=None):
    """Ficha 0.045 x 0.090 x 0.014 m, cara con puntos en +Z local. vals=(a, b): a = mitad +Y, b = mitad -Y.
    Sin vals se usa un dibujo genérico."""
    coll = preview_collection(scene)
    ivory = _mat('Ficha_marfil', (0.92, 0.90, 0.84, 1), 0.3)
    dot = _mat('Ficha_punto', (0.05, 0.05, 0.05, 1), 0.4)
    ob = _box(name, TILE, (0, 0, 0), ivory, coll)
    me = ob.data
    me.materials.append(dot)
    zt = TILE[2] / 2 + 0.0004
    sub = _box(name + '_marcas', (TILE[0] * 0.8, 0.0025, 0.0012), (0, 0, zt), dot, coll)
    sub.parent = ob
    if vals is None:
        pts = [(0, 0.022), (0, -0.022), (0.012, 0.034), (-0.012, -0.034)]
    else:
        g = 0.0115
        hc = TILE[1] / 4
        pts = [(gx * g, hc + gy * g) for gx, gy in PIPS[int(vals[0])]] + \
              [(gx * g, -hc + gy * g) for gx, gy in PIPS[int(vals[1])]]
    for k, (px, py) in enumerate(pts):
        d = _box(f'{name}_p{k}', (0.0065, 0.0065, 0.0012), (px, py, zt), dot, coll)
        d.parent = ob
    ob['valores'] = list(vals) if vals is not None else []
    return ob


def setup_render(scene, engine='WORKBENCH', res=(1280, 720)):
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.resolution_percentage = 100
    scene.render.fps = 24
    world = scene.world or bpy.data.worlds.new('Mundo')
    scene.world = world
    # mismo tono que el suelo cerca del horizonte: sin franja clara al fondo
    world.color = (0.058, 0.060, 0.066)
    if engine == 'WORKBENCH':
        scene.render.engine = 'BLENDER_WORKBENCH'
        sh = scene.display.shading
        sh.light = 'STUDIO'
        try:
            sh.studio_light = 'paint.sl'
        except Exception:
            pass
        sh.color_type = 'TEXTURE'
        sh.show_shadows = True
        sh.shadow_intensity = 0.35
        sh.show_cavity = True
        sh.cavity_type = 'WORLD'
        sh.cavity_ridge_factor = 0.6
        sh.cavity_valley_factor = 0.8
        sh.show_specular_highlight = True
        scene.display.light_direction = (0.45, -0.55, 0.70)
        scene.display.shadow_shift = 0.05
        scene.display.render_aa = '8'
        scene.view_settings.view_transform = 'Standard'
        scene.view_settings.look = 'None'
    else:
        scene.render.engine = 'BLENDER_EEVEE_NEXT'
        scene.eevee.taa_render_samples = 24
        # mismo tono que el suelo lejano (sin franja) y luz de relleno baja: más contraste, menos "lavado"
        world.color = (0.004, 0.004, 0.005)
        for ln, e in (('Principal', 650.0), ('Relleno', 90.0), ('Borde', 320.0)):
            lo = bpy.data.objects.get(ln)
            if lo is not None and lo.type == 'LIGHT':
                lo.data.energy = e
        # paño mate: sin brillo especular rasante que lo aclare
        m = bpy.data.materials.get('Pano_mesa')
        b = m.node_tree.nodes.get('Principled BSDF') if m and m.use_nodes else None
        if b is not None:
            b.inputs['Roughness'].default_value = 1.0
            if 'Specular IOR Level' in b.inputs:
                b.inputs['Specular IOR Level'].default_value = 0.1
        scene.view_settings.view_transform = 'AgX'
        for look in ('AgX - Punchy', 'AgX - Medium High Contrast'):
            try:
                scene.view_settings.look = look
                break
            except Exception:
                pass
        scene.view_settings.exposure = -0.5
    scene.render.image_settings.file_format = 'PNG'


def add_camera(scene, name, loc, target, lens=35.0):
    cam = bpy.data.objects.get(name)
    if cam is None:
        cd = bpy.data.cameras.new(name)
        cam = bpy.data.objects.new(name, cd)
        preview_collection(scene).objects.link(cam)
    cam.data.lens = lens
    cam.data.clip_start = 0.02
    cam.location = loc
    look_at(cam, target)
    return cam


def look_at(cam, target):
    d = Vector(target) - cam.location
    cam.rotation_mode = 'QUATERNION'
    cam.rotation_quaternion = d.to_track_quat('-Z', 'Y')
