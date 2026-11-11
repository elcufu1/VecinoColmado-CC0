"""Producción final: Actions + escena de previsualización (.blend), GLB verificado, videos y fotos.

  blender -b Vecino_Boxer.blend --python final.py -- build <dir_salida>
  blender -b <dir_salida>/Vecino_Boxer_Animado.blend --python final.py -- render <dir_frames> [Nombre ...]
  blender -b <dir_salida>/Vecino_Boxer_Animado.blend --python final.py -- photos <dir_fotos> [Nombre ...]
"""
import json
import math
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
from mathutils import Vector, Matrix  # noqa: E402

import vc_core as C  # noqa: E402
import vc_scene as S  # noqa: E402

GAP = 12
CHAR_OBJS = None


def char_objects():
    arm = bpy.data.objects[C.ARM_NAME]
    return [arm] + [o for o in bpy.data.objects if o.parent == arm and o.type == 'MESH']


# ---------------------------------------------------------------------------------------------- build
def build(out_dir):
    import build_all as BA
    import vc_pose as VP
    os.makedirs(out_dir, exist_ok=True)
    P = BA.Pipeline(engine='WORKBENCH', res=(1280, 720))
    P.ensure_preview()
    rep = {}
    for A in P.anims:
        P.bake(A)
        rep[A.name] = P.report(A)
    rig = P.rig
    scene = P.scene

    # ---------------- GLB (solo personaje, todas las Actions) ----------------
    glb = os.path.join(out_dir, 'Vecino_Boxer_Animado.glb')
    export_glb(P, glb)
    glb_info = verify_glb(glb, P.anims)

    # ---------------- escena de previsualización (línea de tiempo con NLA) ----------------
    timeline = build_timeline(P)

    # metadatos para render/fotos
    meta = dict(timeline=timeline, report=rep, log=P.ctx.report, glb=glb_info)
    scene['vc_meta'] = json.dumps(meta)
    with open(os.path.join(out_dir, 'reporte_verificacion.json'), 'w') as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=1)
    blend = os.path.join(out_dir, 'Vecino_Boxer_Animado.blend')
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=blend, compress=True)
    print('GUARDADO', blend)


def export_glb(P, path):
    rig = P.rig
    for o in bpy.data.objects:
        o.select_set(False)
    for o in char_objects():
        o.select_set(True)
    bpy.context.view_layer.objects.active = rig.arm
    ad = rig.arm.animation_data_create()
    ad.action = None
    for mn in C.FACE_MESHES:
        key = bpy.data.objects[mn].data.shape_keys
        if key.animation_data:
            key.animation_data.action = None
    # cada Action en su propia pista NLA (armadura y morfos), el exportador las agrupa por nombre
    tracks = []
    for A in P.anims:
        act = bpy.data.actions[A.name]
        tr = ad.nla_tracks.new()
        tr.name = A.name
        st = tr.strips.new(A.name, 1, act)
        st.action_slot = act.slots['OB' + rig.arm.name]
        tr.mute = True
        tracks.append((ad, tr))
        for mn in C.FACE_MESHES:
            key = bpy.data.objects[mn].data.shape_keys
            kad = key.animation_data_create()
            ktr = kad.nla_tracks.new()
            ktr.name = A.name
            kst = ktr.strips.new(A.name, 1, act)
            kst.action_slot = act.slots['KE' + key.name]
            ktr.mute = True
            tracks.append((kad, ktr))
    _export(path)
    for owner, tr in tracks:
        owner.nla_tracks.remove(tr)


def _export(path):
    kw = dict(filepath=path, export_format='GLB', use_selection=True,
              export_animations=True, export_animation_mode='ACTIONS',
              export_force_sampling=True, export_optimize_animation_size=True, export_frame_range=False,
              export_anim_slide_to_zero=True,
              export_anim_single_armature=True, export_reset_pose_bones=True,
              export_morph=True, export_morph_normal=False, export_morph_tangent=False, export_morph_animation=True,
              export_skins=True, export_all_influences=False, export_def_bones=False,
              export_apply=False, export_yup=True, export_texcoords=True, export_normals=True, export_tangents=False,
              export_image_format='AUTO', export_cameras=False, export_lights=False)
    props = bpy.ops.export_scene.gltf.get_rna_type().properties.keys()
    kw = {k: v for k, v in kw.items() if k in props}
    print('EXPORT GLB', kw)
    bpy.ops.export_scene.gltf(**kw)


def read_glb_json(path):
    data = open(path, 'rb').read()
    ln = struct.unpack('<I', data[12:16])[0]
    return json.loads(data[20:20 + ln]), len(data)


def verify_glb(path, anims):
    j, size = read_glb_json(path)
    names = [a.get('name') for a in j.get('animations', [])]
    info = {'tamano_MB': round(size / 1e6, 2), 'animaciones': {}, 'faltan': []}
    for A in anims:
        if A.name not in names:
            info['faltan'].append(A.name)
            continue
        an = j['animations'][names.index(A.name)]
        paths = {}
        tmax = 0.0
        for ch in an['channels']:
            pth = ch['target']['path']
            paths[pth] = paths.get(pth, 0) + 1
            acc = j['accessors'][an['samplers'][ch['sampler']]['input']]
            tmax = max(tmax, acc.get('max', [0])[0])
        info['animaciones'][A.name] = dict(canales=paths, duracion_s=round(tmax, 3),
                                           esperado_s=round(A.frames / 24.0, 3))
    extra = [n for n in names if n not in [a.name for a in anims]]
    info['extra'] = extra
    print('GLB VERIFICACION', json.dumps(info, ensure_ascii=False)[:3000])
    return info


def reimport_check(glb, anims_names):
    """Reimporta el GLB en una escena vacía y lista las Actions resultantes."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=glb)
    acts = {a.name: (round(a.frame_range[0], 1), round(a.frame_range[1], 1)) for a in bpy.data.actions}
    arm = [o for o in bpy.data.objects if o.type == 'ARMATURE']
    meshes = [o.name for o in bpy.data.objects if o.type == 'MESH']
    keyed = {}
    for a in bpy.data.actions:
        n_key = 0
        n_bone = 0
        try:
            for layer in a.layers:
                for strip in layer.strips:
                    for cb in strip.channelbags:
                        for fc in cb.fcurves:
                            if fc.data_path.startswith('key_blocks'):
                                n_key += 1
                            elif fc.data_path.startswith('pose.bones'):
                                n_bone += 1
        except Exception:
            for fc in a.fcurves:
                if fc.data_path.startswith('key_blocks'):
                    n_key += 1
                else:
                    n_bone += 1
        keyed[a.name] = dict(huesos=n_bone, morfos=n_key)
    res = dict(acciones=acts, curvas=keyed, armaduras=[o.name for o in arm], mallas=meshes,
               faltan=[n for n in anims_names if not any(k == n or k.startswith(n) for k in acts)])
    return res


# ---------------------------------------------------------------------------------------------- timeline
def key_hide(ob, frame, hidden):
    ob.hide_render = hidden
    ob.hide_viewport = hidden
    ob.keyframe_insert('hide_render', frame=frame)
    ob.keyframe_insert('hide_viewport', frame=frame)


def set_constant(ob):
    ad = ob.animation_data
    if not ad or not ad.action:
        return
    act = ad.action
    try:
        fcs = [fc for layer in act.layers for strip in layer.strips for cb in strip.channelbags for fc in cb.fcurves]
    except Exception:
        fcs = list(act.fcurves)
    for fc in fcs:
        if fc.data_path.startswith('hide'):
            for k in fc.keyframe_points:
                k.interpolation = 'CONSTANT'


def build_timeline(P):
    import build_all as BA
    rig = P.rig
    scene = P.scene
    scene.name = 'Previsualizacion_Animaciones'
    scene.render.fps = 24
    ad = rig.arm.animation_data_create()
    ad.action = None
    trk = ad.nla_tracks.new()
    trk.name = 'Animaciones'
    ktr = {}
    for mn in C.FACE_MESHES:
        key = bpy.data.objects[mn].data.shape_keys
        kad = key.animation_data_create()
        kad.action = None
        ktr[mn] = kad.nla_tracks.new()
        ktr[mn].name = 'Morfos'
    props = [o for o in bpy.data.objects if o.name.startswith(('Mesa', 'Silla'))]
    chair = bpy.data.objects['Silla']
    cams = {k: P.cam(k) for k in BA.CAMS}
    timeline = []
    start = 1
    tile_objs = {}
    for A in P.anims:
        b = P.baked[A.name]
        act = b['act']
        st = trk.strips.new(A.name, start, act)
        st.action_slot = act.slots['OB' + rig.arm.name]
        st.extrapolation = 'NOTHING'
        for mn in C.FACE_MESHES:
            key = bpy.data.objects[mn].data.shape_keys
            s2 = ktr[mn].strips.new(A.name, start, act)
            s2.action_slot = act.slots['KE' + key.name]
            s2.extrapolation = 'NOTHING'
        end = start + A.frames
        m = scene.timeline_markers.new(A.name, frame=start)
        m.camera = cams[A.props.get('cam', 'mesa')]
        nochair = bool(A.props.get('nochair'))
        notable = nochair or bool(A.props.get('notable'))
        for ob in props:
            key_hide(ob, start, notable if ob.name.startswith('Mesa') else nochair)
        for f, pb in enumerate(b['poses']):
            chair.location = (0, float(pb.P['chair'][0]) if not nochair else 0.0, 0)
            chair.keyframe_insert('location', frame=start + f)
        # fichas
        for n, mats in b['tiles'].items():
            on = f'{A.name}__{n}'
            ob = S.make_tile(scene, on)
            ob.rotation_mode = 'QUATERNION'
            face_down = n.startswith(('Ficha_mesa', 'Ficha_l', 'Ficha_r'))
            for ch in ob.children:
                ch.hide_render = face_down
                ch.hide_viewport = face_down
            key_hide(ob, 1, True)
            key_hide(ob, start, False)
            key_hide(ob, end + 1, True)
            for f, M in enumerate(mats):
                loc, rot, _ = M.decompose()
                ob.location = loc
                ob.rotation_quaternion = rot
                ob.keyframe_insert('location', frame=start + f)
                ob.keyframe_insert('rotation_quaternion', frame=start + f)
            set_constant(ob)
            tile_objs[on] = ob
        timeline.append(dict(name=A.name, start=start, end=end, frames=A.frames, loop=A.loop,
                             duracion_s=round(A.frames / 24.0, 3), desc=A.desc, uso=A.props.get('use', ''),
                             cam=A.props.get('cam', 'mesa'), mesa=not notable, silla=not nochair,
                             markers=[(start + t, nm) for t, nm in A.markers]))
        for t, nm in A.markers:
            scene.timeline_markers.new(f'{A.name}:{nm}', frame=start + t)
        start = end + 1 + GAP
    for ob in props:
        set_constant(ob)
    scene.frame_start = 1
    scene.frame_end = start - GAP
    return timeline


# ---------------------------------------------------------------------------------------------- render
def load_meta():
    return json.loads(bpy.context.scene['vc_meta'])


def setup_wb(res=(1280, 720)):
    S.setup_render(bpy.context.scene, 'WORKBENCH', res)
    sc = bpy.context.scene
    sc.render.image_settings.file_format = 'PNG'
    sc.render.film_transparent = False


def hand_cams():
    sc = bpy.context.scene
    return {
        'mesa_mano': S.add_camera(sc, 'Cam_mesa_mano', (-0.48, -0.92, 1.13), (-0.08, -0.50, 0.86), 42),
        'mesa_mano_lejos': S.add_camera(sc, 'Cam_mesa_mano_lejos', (-0.55, -1.15, 1.15), (-0.05, -0.68, 0.86), 42),
        'mano_izq': S.add_camera(sc, 'Cam_mano_izq', (0.45, -0.95, 1.18), (0.07, -0.38, 0.98), 42),
        'barajar': S.add_camera(sc, 'Cam_barajar', (-0.05, -1.05, 1.30), (0.0, -0.48, 0.86), 40),
        'manos_rango': S.add_camera(sc, 'Cam_manos_rango', (-0.12, -1.25, 1.40), (0.0, -0.32, 1.33), 42),
        'cara': S.add_camera(sc, 'Cam_cara', (-0.12, -0.75, 1.68), (0.0, -0.05, 1.66), 45),
    }


INSET = {
    'Agarrar_Ficha_Cerca': 'mesa_mano', 'Colocar_Ficha_Cerca': 'mesa_mano', 'Golpe_Ficha': 'mesa_mano',
    'Pasar': 'mesa_mano', 'Agarrar_Ficha_Lejos': 'mesa_mano_lejos', 'Colocar_Ficha_Lejos': 'mesa_mano_lejos',
    'Sostener_Fichas': 'mano_izq', 'Barajar_Fichas': 'barajar', 'Idle_Sentado': 'mesa_mano',
}


def render_seq(cam, f0, f1, out_dir, res):
    sc = bpy.context.scene
    sc.render.resolution_x, sc.render.resolution_y = res
    os.makedirs(out_dir, exist_ok=True)
    # sin marcadores-cámara durante el render explícito
    saved = {m.name: m.camera for m in sc.timeline_markers}
    for m in sc.timeline_markers:
        m.camera = None
    sc.camera = cam
    for f in range(f0, f1 + 1):
        p = os.path.join(out_dir, f'{f - f0:05d}.png')
        if os.path.exists(p):
            continue
        sc.frame_set(f)
        sc.render.filepath = p
        bpy.ops.render.render(write_still=True)
    for m in sc.timeline_markers:
        m.camera = saved.get(m.name)


def render(frames_dir, names):
    meta = load_meta()
    setup_wb()
    hc = hand_cams()
    for t in meta['timeline']:
        if names and t['name'] not in names:
            continue
        f1 = t['end'] - (1 if t['loop'] else 0)
        cam = bpy.data.objects['Cam_' + t['cam']]
        render_seq(cam, t['start'], f1, os.path.join(frames_dir, t['name'], 'main'), (1280, 720))
        if t['name'] in INSET:
            render_seq(hc[INSET[t['name']]], t['start'], f1, os.path.join(frames_dir, t['name'], 'inset'), (480, 270))
        if t['name'] == 'Prueba_Rango_Completo':
            mk = {n: f for f, n in t['markers']}
            a, b = mk['Dedos'], mk['Columna']
            render_seq(hc['manos_rango'], a, b, os.path.join(frames_dir, t['name'], 'manos'), (1280, 720))
            a, b = mk['Cara'], mk['Todo_Junto']
            render_seq(hc['cara'], a, b, os.path.join(frames_dir, t['name'], 'cara'), (1280, 720))
        print('RENDER OK', t['name'])


# ---------------------------------------------------------------------------------------------- fotos
KEY_FRAMES = {
    'Idle_De_Pie': [48], 'Caminar': [0, 7], 'Sentarse': [26, 46, 100], 'Levantarse': [52, 72],
    'Idle_Sentado': [30], 'Agarrar_Ficha_Cerca': [10, 20], 'Agarrar_Ficha_Lejos': [14],
    'Colocar_Ficha_Cerca': [7], 'Colocar_Ficha_Lejos': [11], 'Golpe_Ficha': [9, 15], 'Pasar': [8],
    'Barajar_Fichas': [12], 'Sostener_Fichas': [0], 'Celebrar_Ganar': [12, 36], 'Perder': [24],
    'Pensar': [30], 'Saludar': [18], 'Senalar': [13], 'Pulgar_Arriba': [14], 'Aplaudir': [12], 'Reir': [20],
    'Enojado': [13, 30], 'Prueba_Rango_Completo': [420, 1160, 1650, 2320],
}


def photos(out_dir, names):
    meta = load_meta()
    sc = bpy.context.scene
    S.setup_render(sc, 'EEVEE', (1280, 720))
    sc.eevee.taa_render_samples = 16
    sc.render.image_settings.file_format = 'JPEG'
    sc.render.image_settings.quality = 90
    for m in sc.timeline_markers:
        m.camera = None
    os.makedirs(out_dir, exist_ok=True)
    for t in meta['timeline']:
        if names and t['name'] not in names:
            continue
        seated = t['silla'] and t['name'] not in ('Sentarse', 'Levantarse')
        if t['name'] in ('Sentarse', 'Levantarse'):
            tgt = Vector((0, 0.05, 0.80))
        elif seated:
            tgt = Vector((0, -0.10, 0.95))
        else:
            tgt = Vector((0, 0, 0.92))
        dist = 2.9 if not seated else 2.4
        views = {'frente': (0, -1, 0.18), 'tres_cuartos': (-0.72, -0.70, 0.22), 'perfil': (-1, 0, 0.12)}
        for f in KEY_FRAMES.get(t['name'], [t['frames'] // 2]):
            sc.frame_set(t['start'] + f)
            for vn, d in views.items():
                dv = Vector(d).normalized() * dist
                cam = S.add_camera(sc, 'Cam_foto', tgt + dv, tgt, 40 if seated else 38)
                sc.camera = cam
                sc.render.filepath = os.path.join(out_dir, f"{t['name']}_f{f:04d}_{vn}.jpg")
                bpy.ops.render.render(write_still=True)
        print('FOTOS OK', t['name'])


def main():
    argv = sys.argv[sys.argv.index('--') + 1:]
    mode = argv[0]
    if mode == 'build':
        build(argv[1])
    elif mode == 'render':
        render(argv[1], [n for a in argv[2:] for n in a.split(',') if n])
    elif mode == 'photos':
        photos(argv[1], [n for a in argv[2:] for n in a.split(',') if n])
    elif mode == 'reimport':
        res = reimport_check(argv[1], argv[2].split(','))
        print('REIMPORT', json.dumps(res, ensure_ascii=False))
        with open(argv[3], 'w') as fh:
            json.dump(res, fh, ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
