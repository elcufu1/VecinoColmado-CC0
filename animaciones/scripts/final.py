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

import numpy as np

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

    # ---------------- capicúa: cámara cinemática (Action aparte) + efectos de previsualización ----------------
    capicua_cine(P, timeline)

    # ---------------- límites de rotación: verificación numérica + constraints en el rig ----------------
    lim_info = check_limits(P)
    lim_info['constraints'] = add_constraints(P)
    lim_info['constraints_verificacion'] = verify_constraints(P, timeline)
    with open(os.path.join(out_dir, 'limites_rotacion.json'), 'w') as fh:
        json.dump(lim_info, fh, ensure_ascii=False, indent=1)

    # metadatos para render/fotos
    meta = dict(timeline=timeline, report=rep, log=P.ctx.report, glb=glb_info,
                limites=dict(excesos=lim_info['excesos_max_grados'], verificacion=lim_info['constraints_verificacion']),
                dedos={A.name: P.baked[A.name].get('dedos', {}) for A in P.anims})
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


# ---------------------------------------------------------------------------------------------- límites
def check_limits(P):
    """Recorre todos los cuadros horneados de todas las Actions y mide cuánto excede cada hueso su rango."""
    lim = P.rig.limits
    worst = {}
    total = 0
    per_anim = {}
    for A in P.anims:
        mx = 0.0
        for pb in P.baked[A.name]['poses']:
            for n in P.rig.names:
                e = lim.excess(n, pb.local[n].to_quaternion())
                total += 1
                if e > worst.get(n, (0.0, ''))[0]:
                    worst[n] = (e, A.name)
                mx = max(mx, e)
        per_anim[A.name] = round(mx, 4)
    import vc_limits
    rangos = []
    for k, (mode, order, x, y, z) in vc_limits.BASE.items():
        if k == 'Root':
            continue
        sem = vc_limits.SEMANTIC.get(k, (k, 'X', 'Y', 'Z'))
        rangos.append(dict(clave=k, nombre=sem[0], modo=mode, orden=order, x=list(x), y=list(y), z=list(z),
                           eje_x=sem[1], eje_y=sem[2], eje_z=sem[3]))
    clamps = {n: dict(cuadros=v[0], max_grados=round(v[1], 2)) for n, v in lim.stats.items()}
    return dict(muestras_hueso_cuadro=total, excesos_max_grados=per_anim, rangos=rangos,
                recortes_al_hornear=clamps,
                peores={n: [round(v[0], 4), v[1]] for n, v in worst.items() if v[0] > 0})


def add_constraints(P):
    """Limit Rotation (espacio local) en los 53 huesos. Para los huesos swing/twist la caja Euler cubre la región
    anatómica y todo lo horneado, de modo que el constraint nunca cambia la animación."""
    rig, lim = P.rig, P.rig.limits
    out = {}
    for n in rig.names:
        order, lo, hi = lim.constraint_box(n)
        lo, hi = np.array(lo, float), np.array(hi, float)
        if lim.spec[n][0] == 'st':
            E = np.degrees(np.array([pb.local[n].to_quaternion().to_euler(order)[:]
                                     for A in P.anims for pb in P.baked[A.name]['poses']]))
            lo = np.minimum(lo, E.min(0) - 0.5)
            hi = np.maximum(hi, E.max(0) + 0.5)
        pbn = rig.arm.pose.bones[n]
        for c in list(pbn.constraints):
            if c.type == 'LIMIT_ROTATION':
                pbn.constraints.remove(c)
        c = pbn.constraints.new('LIMIT_ROTATION')
        c.name = 'Limite_anatomico'
        c.owner_space = 'LOCAL'
        c.euler_order = order
        c.use_limit_x = c.use_limit_y = c.use_limit_z = True
        c.min_x, c.max_x = math.radians(lo[0]), math.radians(hi[0])
        c.min_y, c.max_y = math.radians(lo[1]), math.radians(hi[1])
        c.min_z, c.max_z = math.radians(lo[2]), math.radians(hi[2])
        if hasattr(c, 'use_transform_limit'):
            c.use_transform_limit = True
        out[n] = dict(orden=order, x=[round(lo[0], 1), round(hi[0], 1)], y=[round(lo[1], 1), round(hi[1], 1)],
                      z=[round(lo[2], 1), round(hi[2], 1)])
    return out


def verify_constraints(P, timeline):
    """Compara la pose evaluada con los constraints activos contra la misma pose sin constraints, en TODOS
    los cuadros de la línea de tiempo: diferencia máxima de rotación (grados)."""
    sc = bpy.context.scene
    arm = P.rig.arm
    cons = [c for pb in arm.pose.bones for c in pb.constraints if c.type == 'LIMIT_ROTATION']
    worst = (0.0, None, None)
    nfr = 0
    for t in timeline:
        for f in range(t['start'], t['end'] + 1):
            for c in cons:
                c.mute = True
            sc.frame_set(f)
            a = {pb.name: pb.matrix.to_quaternion() for pb in arm.pose.bones}
            for c in cons:
                c.mute = False
            sc.frame_set(f)
            for pb in arm.pose.bones:
                d = math.degrees(a[pb.name].rotation_difference(pb.matrix.to_quaternion()).angle)
                d = min(d, 360 - d)
                if d > worst[0]:
                    worst = (d, t['name'], pb.name)
            nfr += 1
    return dict(cuadros=nfr, constraints=len(cons), dif_max_grados=round(worst[0], 5), anim=worst[1], hueso=worst[2])


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


def juego_info(A):
    """Datos para integrar la partida en el juego (hueco, sentido de caída, cuadros de agarre/suelta...)."""
    out = {}
    for k in ('jugada', 'slot', 'eventos', 'tranque', 'mesa'):
        if k in A.props:
            out[k] = A.props[k]
    for t in A.tiles:
        if t['name'] == 'Ficha':
            out['ficha'] = dict(agarre=t.get('grab'), suelta=t.get('release'), caida=t.get('fall'),
                                valores=A.props.get('vals', {}).get('Ficha'),
                                giro=list(t['roll'][:2]) if t.get('roll') else None)
    fall = [(t['name'], t['release']) for t in A.tiles if t['name'].startswith('Fila') and t.get('release')]
    if fall:
        out['acuesta_fila'] = fall
    return out


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
            shared = n.startswith(('Fila', 'Cadena'))
            on = n if shared else f'{A.name}__{n}'
            face_down = n.startswith(('Ficha_mesa', 'Ficha_l', 'Ficha_r'))
            ob = tile_objs.get(on)
            if ob is None:
                ob = S.make_tile(scene, on, A.props.get('vals', {}).get(n))
                ob.rotation_mode = 'QUATERNION'
                for o in [ob] + list(ob.children):
                    key_hide(o, 1, True)
            # las marcas (hijos) se ocultan junto con la ficha: si no, quedan flotando en otras animaciones
            for o in [ob] + list(ob.children):
                key_hide(o, start, face_down and o is not ob)
                key_hide(o, end + 1, True)
            static = all((M.translation - mats[0].translation).length < 1e-7 for M in mats)
            for f, M in enumerate(mats[:1] if static else mats):
                loc, rot, _ = M.decompose()
                ob.location = loc
                ob.rotation_quaternion = rot
                ob.keyframe_insert('location', frame=start + f)
                ob.keyframe_insert('rotation_quaternion', frame=start + f)
            tile_objs[on] = ob
        timeline.append(dict(name=A.name, start=start, end=end, frames=A.frames, loop=A.loop,
                             duracion_s=round(A.frames / 24.0, 3), desc=A.desc, uso=A.props.get('use', ''),
                             cam=A.props.get('cam', 'mesa'), mesa=not notable, silla=not nochair,
                             markers=[(start + t, nm) for t, nm in A.markers], juego=juego_info(A)))
        for t, nm in A.markers:
            scene.timeline_markers.new(f'{A.name}:{nm}', frame=start + t)
        start = end + 1 + GAP
    for ob in props:
        set_constant(ob)
    for ob in tile_objs.values():
        for o in [ob] + list(ob.children):
            set_constant(o)
        fc_owner = ob.animation_data.action if ob.animation_data else None
        if fc_owner is not None:
            try:
                fcs = [fc for layer in fc_owner.layers for strip in layer.strips for cb in strip.channelbags
                       for fc in cb.fcurves]
            except Exception:
                fcs = list(fc_owner.fcurves)
            for fc in fcs:
                if not fc.data_path.startswith('hide'):
                    for k in fc.keyframe_points:
                        k.interpolation = 'LINEAR'
    scene.frame_start = 1
    scene.frame_end = start - GAP
    return timeline


# ---------------------------------------------------------------------------------------------- capicúa
CAPI = 'Capicua_Golpe_Celebrar'


def _smooth(k):
    k = min(1.0, max(0.0, k))
    return k * k * (3 - 2 * k)


def _emit_mat(name, rgb, strength):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    em = nt.nodes.new('ShaderNodeEmission')
    em.inputs['Color'].default_value = (*rgb, 1.0)
    em.inputs['Strength'].default_value = strength
    nt.links.new(em.outputs[0], out.inputs[0])
    m.diffuse_color = (*rgb, 1.0)
    return m


def capicua_camera_path(P, A):
    """Trayectoria de la cámara cinemática (cuadros de la Action, desde 0): plano general -> se acerca a la ficha
    mientras la lleva -> temblor en el golpe -> se abre para ver la celebración."""
    b = P.baked[A.name]
    ev = A.props['eventos']
    tiles = b['tiles']['Ficha']
    imp = ev['impacto']
    slot = tiles[-1].translation.copy()
    W0, L0 = Vector((-0.62, -1.55, 1.42)), Vector((0.0, -0.30, 1.05))
    W1, L1 = Vector((-0.30, -1.32, 1.42)), Vector((0.0, -0.08, 1.30))
    near = Vector((-0.16, -0.34, 0.12))
    out = []
    for f in range(A.frames + 1):
        tp = tiles[min(f, len(tiles) - 1)].translation
        if f <= 8:
            pos, look, lens = W0.copy(), L0.copy(), 32.0
        elif f <= imp:
            k = _smooth((f - 8) / float(imp - 8))
            pos, look, lens = W0.lerp(tp + near, k), L0.lerp(tp, k), 32.0 + 8.0 * k
        elif f <= imp + 9:
            pos, look, lens = slot + near, slot.copy(), 40.0
            a = 0.009 * math.exp(-(f - imp) / 3.0)
            pos = pos + Vector((math.sin(f * 2.7), math.cos(f * 3.9), math.sin(f * 5.1))) * a
            look = look + Vector((math.cos(f * 4.3), math.sin(f * 3.1), 0)) * a * 0.6
        elif f <= ev['celebracion'][0] + 6:
            k = _smooth((f - imp - 9) / float(ev['celebracion'][0] + 6 - imp - 9))
            pos, look, lens = (slot + near).lerp(W1, k), slot.lerp(L1, k), 40.0 - 2.0 * k
        else:
            d = f - ev['celebracion'][0] - 6
            pos, look, lens = W1 + Vector((0.0006 * d, -0.0004 * d, 0.0002 * d)), L1.copy(), 38.0
        out.append((pos, look, lens))
    return out


def capicua_cine(P, timeline):
    """Cámara 'Camara_Capicua' con su propia Action 'Capicua_Camara' (slots de objeto y de focal),
    más un ejemplo de los efectos que debe hacer el juego (texto, chispas, destello) en la colección
    FX_Capicua_Previsualizacion. Nada de esto va en el GLB del personaje."""
    A = next(a for a in P.anims if a.name == CAPI)
    t = next(x for x in timeline if x['name'] == CAPI)
    ev = A.props['eventos']
    scene = P.scene
    start = t['start']
    coll = bpy.data.collections.get('FX_Capicua_Previsualizacion') or bpy.data.collections.new(
        'FX_Capicua_Previsualizacion')
    if coll.name not in scene.collection.children:
        scene.collection.children.link(coll)
    cd = bpy.data.cameras.new('Camara_Capicua')
    cd.clip_start = 0.01
    cam = bpy.data.objects.new('Camara_Capicua', cd)
    coll.objects.link(cam)
    cam.rotation_mode = 'QUATERNION'
    for f, (pos, look, lens) in enumerate(capicua_camera_path(P, A)):
        cam.location = pos
        cam.rotation_quaternion = (look - pos).to_track_quat('-Z', 'Y')
        cam.keyframe_insert('location', frame=f)
        cam.keyframe_insert('rotation_quaternion', frame=f)
        cd.lens = lens
        cd.keyframe_insert('lens', frame=f)
    # Blender 4.4+: posición/rotación y focal quedan en la MISMA Action, en dos slots (objeto y cámara)
    act = cam.animation_data.action
    act.name = 'Capicua_Camara'
    act.use_fake_user = True
    lact = cd.animation_data.action
    if lact is not act:
        lact.name = 'Capicua_Camara_Lente'
        lact.use_fake_user = True
    slot_ob, slot_cd = cam.animation_data.action_slot, cd.animation_data.action_slot
    # en la línea de tiempo de previsualización: tiras NLA en el inicio de la animación del personaje
    cam.animation_data.action = None
    tr = cam.animation_data.nla_tracks.new()
    tr.name = 'Capicua_Camara'
    st = tr.strips.new('Capicua_Camara', start, act)
    st.action_slot = slot_ob
    cd.animation_data.action = None
    tr2 = cd.animation_data.nla_tracks.new()
    tr2.name = 'Capicua_Camara_Lente'
    st2 = tr2.strips.new(lact.name, start, lact)
    st2.action_slot = slot_cd
    for m in scene.timeline_markers:
        if m.name == CAPI:
            m.camera = cam

    slot = P.baked[CAPI]['tiles']['Ficha'][-1].translation.copy()
    capicua_fx(scene, coll, cam, start, ev, slot)


# el texto va muy cerca de la cámara (delante de la mano en el primer plano), mismo tamaño en pantalla
FX_D = 0.30


def capicua_fx(scene, coll, cam, start, ev, slot):
    """Efectos de ejemplo (los hace el juego): texto pegado a la cámara, chispas desde la ficha y destello."""
    imp = start + ev['impacto']
    fin = start + ev['celebracion'][1] + 36
    # texto grande pegado a la cámara (como lo pondría la interfaz del juego)
    cu = bpy.data.curves.new('Texto_Capicua', 'FONT')
    cu.body = '¡CAPICÚA!'
    cu.align_x, cu.align_y = 'CENTER', 'CENTER'
    cu.size = 0.05 * FX_D
    cu.extrude = 0.003 * FX_D
    cu.bevel_depth = 0.0008 * FX_D
    txt = bpy.data.objects.new('Texto_Capicua', cu)
    coll.objects.link(txt)
    txt.data.materials.append(_emit_mat('FX_Oro', (1.0, 0.62, 0.08), 9.0))
    txt.visible_shadow = False
    txt.parent = cam
    txt.location = (0.0, 0.055 * FX_D, -0.42 * FX_D)
    for f, sc_ in ((ev['texto'] - 1, 0.0), (ev['texto'], 0.05), (ev['texto'] + 3, 1.25), (ev['texto'] + 6, 1.0),
                   (ev['texto'] + 20, 1.08), (ev['texto'] + 34, 1.0), (ev['celebracion'][1] + 30, 1.0),
                   (ev['celebracion'][1] + 36, 0.0)):
        txt.scale = (sc_, sc_, sc_)
        txt.keyframe_insert('scale', frame=start + f)
    key_hide(txt, 1, True)
    key_hide(txt, start + ev['texto'], False)
    key_hide(txt, fin + 1, True)
    # chispas: estallido desde el hueco de la ficha + destellos alrededor del texto
    rnd = np.random.RandomState(7)
    mats = [_emit_mat('FX_Chispa_Oro', (1.0, 0.70, 0.15), 24.0), _emit_mat('FX_Chispa_Blanca', (1.0, 0.95, 0.8), 30.0)]
    sparks = []
    for i in range(46):
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=0.0011 + 0.0009 * rnd.rand(), location=slot)
        o = bpy.context.active_object
        o.name = f'Chispa_{i:02d}'
        for c in list(o.users_collection):
            c.objects.unlink(o)
        coll.objects.link(o)
        o.data.materials.append(mats[i % 2])
        o.visible_shadow = False
        az = rnd.rand() * 2 * math.pi
        el = math.radians(25 + 55 * rnd.rand())
        sp = 0.45 + 0.75 * rnd.rand()
        v = Vector((math.cos(az) * math.cos(el), math.sin(az) * math.cos(el), math.sin(el))) * sp
        n = 22
        for k in range(n + 1):
            tt = k / 24.0
            p_ = slot + v * tt + Vector((0, 0, -4.9 * tt * tt))
            p_.z = max(p_.z, S.TABLE_TOP + 0.002)
            o.location = p_
            o.keyframe_insert('location', frame=imp + k)
            s_ = 1.0 - (k / n) ** 2
            o.scale = (s_, s_, s_)
            o.keyframe_insert('scale', frame=imp + k)
        key_hide(o, 1, True)
        key_hide(o, imp, False)
        key_hide(o, imp + n + 1, True)
        sparks.append(o)
    for i in range(26):
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=(0.0012 + 0.001 * rnd.rand()) * FX_D)
        o = bpy.context.active_object
        o.name = f'Chispa_texto_{i:02d}'
        for c in list(o.users_collection):
            c.objects.unlink(o)
        coll.objects.link(o)
        o.data.materials.append(mats[(i + 1) % 2])
        o.visible_shadow = False
        o.parent = cam
        a_ = 2 * math.pi * i / 26 + rnd.rand() * 0.3
        o.location = (0.18 * FX_D * math.cos(a_) * (0.9 + 0.3 * rnd.rand()),
                      FX_D * (0.06 + abs(0.075 * math.sin(a_)) * (0.9 + 0.3 * rnd.rand()) *
                              (1 if math.sin(a_) >= 0 else 0.45)),
                      -0.43 * FX_D)
        ph = rnd.randint(0, 6)
        for f in range(ev['texto'], ev['celebracion'][1] + 31, 3):
            s_ = 0.4 + 1.1 * abs(math.sin((f + ph) * 0.7))
            o.scale = (s_, s_, s_)
            o.keyframe_insert('scale', frame=start + f)
        key_hide(o, 1, True)
        key_hide(o, start + ev['texto'] + i % 4, False)
        key_hide(o, fin + 1, True)
        sparks.append(o)
    # destello de luz en el golpe
    ld = bpy.data.lights.new('Destello_Capicua', 'POINT')
    ld.color = (1.0, 0.85, 0.55)
    ld.shadow_soft_size = 0.05
    lo = bpy.data.objects.new('Destello_Capicua', ld)
    coll.objects.link(lo)
    lo.location = slot + Vector((0, 0.02, 0.06))
    for f, e in ((imp - 1, 0.0), (imp, 18.0), (imp + 2, 8.0), (imp + 6, 0.0)):
        ld.energy = e
        ld.keyframe_insert('energy', frame=f)
    for o in [txt] + sparks:
        set_constant(o)


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
        # de lado y un poco por delante del hombro: se ven la pinza (pulgar en la cara, índice detrás) y la cara
        # de las fichas paradas
        'mesa_mano': S.add_camera(sc, 'Cam_mesa_mano', (0.34, -0.04, 1.16), (-0.13, -0.47, 0.90), 40),
        'mesa_mano_lejos': S.add_camera(sc, 'Cam_mesa_mano_lejos', (0.60, -0.18, 1.26), (0.10, -0.44, 0.90), 40),
        'mano_izq': S.add_camera(sc, 'Cam_mano_izq', (-0.55, 0.02, 1.30), (0.0, -0.39, 0.88), 42),
        'mesa_frente_mano': S.add_camera(sc, 'Cam_mesa_frente_mano', (-0.42, -1.05, 1.12), (-0.12, -0.45, 0.88), 40),
        'barajar': S.add_camera(sc, 'Cam_barajar', (-0.05, -1.05, 1.30), (0.0, -0.48, 0.86), 40),
        'manos_rango': S.add_camera(sc, 'Cam_manos_rango', (-0.12, -1.25, 1.40), (0.0, -0.32, 1.33), 42),
        'cara': S.add_camera(sc, 'Cam_cara', (-0.12, -0.75, 1.68), (0.0, -0.05, 1.66), 45),
    }


INSET = {
    'Agarrar_Ficha_Cerca': 'mesa_mano', 'Colocar_Der_Cerca': 'mesa_mano', 'Domino_Golpe': 'mesa_mano',
    'Pasar': 'mesa_mano', 'Agarrar_Ficha_Lejos': 'mesa_mano_lejos', 'Colocar_Izq_Lejos': 'mesa_mano_lejos',
    'Sostener_Fichas': 'mano_izq', 'Barajar_Fichas': 'barajar', 'Idle_Sentado': 'mesa_mano',
}

# primeros planos grandes de la pinza con la ficha parada (se añaden al final de VIDEO_TODO_EL_CUERPO.mp4)
CLOSEUPS = ('Agarrar_Ficha_Cerca', 'Colocar_Der_Cerca', 'Agarrar_Ficha_Lejos', 'Colocar_Izq_Lejos',
            'Domino_Golpe', 'Sostener_Fichas')


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
        if t['name'] in CLOSEUPS:
            render_seq(hc[INSET[t['name']]], t['start'], f1, os.path.join(frames_dir, t['name'], 'primer_plano'),
                       (1280, 720))
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
    'Idle_Sentado': [30], 'Agarrar_Ficha_Cerca': [11, 18], 'Agarrar_Ficha_Lejos': [15, 24],
    'Salida_Doble_Seis': [11, 29], 'Colocar_Doble': [12], 'Colocar_Izq_Lejos': [12], 'Colocar_Esquina': [9],
    'Colocar_Der_Cerca': [9], 'Colocar_Der_Frente': [9], 'Domino_Golpe': [9, 15], 'Capicua_Golpe_Celebrar': [14, 27, 53],
    'Tranque': [11, 30], 'Pasar': [8],
    'Barajar_Fichas': [12], 'Sostener_Fichas': [0, 30], 'Celebrar_Ganar': [12, 36], 'Perder': [24],
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
    hc = hand_cams()
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
            if t['name'] in INSET:
                sc.camera = hc[INSET[t['name']]]
                sc.render.filepath = os.path.join(out_dir, f"{t['name']}_f{f:04d}_primer_plano.jpg")
                bpy.ops.render.render(write_still=True)
        print('FOTOS OK', t['name'])


def refx(out_blend):
    """Rehace solo los efectos de ejemplo de la capicúa en un .blend ya construido."""
    meta = load_meta()
    t = next(x for x in meta['timeline'] if x['name'] == CAPI)
    coll = bpy.data.collections['FX_Capicua_Previsualizacion']
    for o in list(coll.objects):
        if o.name.startswith(('Texto_Capicua', 'Chispa', 'Destello_Capicua')):
            bpy.data.objects.remove(o, do_unlink=True)
    for d in (bpy.data.curves, bpy.data.lights, bpy.data.meshes):
        for x in list(d):
            if x.users == 0:
                d.remove(x)
    slot = bpy.data.objects[f'{CAPI}__Ficha']
    sc = bpy.context.scene
    sc.frame_set(t['end'])
    capicua_fx(sc, coll, bpy.data.objects['Camara_Capicua'], t['start'], t['juego']['eventos'],
               slot.matrix_world.translation.copy())
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=out_blend, compress=True)


# ---------------------------------------------------------------------------------------------- fotos partida
def _obj_pos(name):
    ob = bpy.data.objects.get(name)
    return ob.matrix_world.translation.copy() if ob is not None else None


def _bone_pos(bone):
    arm = bpy.data.objects[C.ARM_NAME]
    return arm.matrix_world @ arm.pose.bones[bone].head


# (archivo, animación, cuadro, cámara): cámara = ('mira', objetivo, desplazamiento, lente) | ('cam', nombre)
FOTOS_PARTIDA = [
    ('01_salida_doble_seis_al_centro', 'Salida_Doble_Seis', 34, ('mira', 'ficha', (-0.12, -0.56, 0.50), 30)),
    ('02_agarra_ficha_parada_en_pinza', 'Agarrar_Ficha_Cerca', 12, ('cam', 'mesa_mano')),
    ('03_coloca_casando_numero_con_numero', 'Colocar_Der_Cerca', 14, ('mira', 'ficha', (0.02, -0.34, 0.34), 38)),
    ('04_doble_atravesado_y_esquina', 'Colocar_Esquina', 9, ('mira', (-0.33, -0.60, 0.81), (-0.10, -0.42, 0.52), 34)),
    ('05_pasa_tocando_la_mesa', 'Pasar', 8, ('mira', 'mano', (-0.06, -0.40, 0.22), 36)),
    ('06_domino_golpe_final', 'Domino_Golpe', 15, ('mira', 'ficha', (-0.18, -0.38, 0.24), 36)),
    ('07_capicua_golpe', CAPI, 31, ('cam', 'Camara_Capicua')),
    ('08_capicua_celebracion', CAPI, 53, ('cam', 'Camara_Capicua')),
]


def fotos_partida(out_dir, only=()):
    meta = load_meta()
    sc = bpy.context.scene
    S.setup_render(sc, 'EEVEE', (1280, 720))
    sc.eevee.taa_render_samples = 16
    sc.render.image_settings.file_format = 'JPEG'
    sc.render.image_settings.quality = 92
    for m in sc.timeline_markers:
        m.camera = None
    os.makedirs(out_dir, exist_ok=True)
    hc = hand_cams()
    tl = {t['name']: t for t in meta['timeline']}
    for fn, an, f, cs in FOTOS_PARTIDA:
        if only and fn not in only:
            continue
        t = tl[an]
        sc.frame_set(t['start'] + f)
        if cs[0] == 'cam':
            cam = hc.get(cs[1]) or bpy.data.objects[cs[1]]
        else:
            tgt = cs[1]
            if tgt == 'ficha':
                tgt = _obj_pos(f'{an}__Ficha')
            elif tgt == 'mano':
                tgt = _bone_pos('hand_r')
            tgt = Vector(tgt)
            cam = S.add_camera(sc, 'Cam_foto_partida', tgt + Vector(cs[2]), tgt, cs[3])
        sc.camera = cam
        sc.render.filepath = os.path.join(out_dir, fn + '.jpg')
        bpy.ops.render.render(write_still=True)
        print('FOTO OK', fn)


def main():
    argv = sys.argv[sys.argv.index('--') + 1:]
    mode = argv[0]
    if mode == 'build':
        build(argv[1])
    elif mode == 'render':
        render(argv[1], [n for a in argv[2:] for n in a.split(',') if n])
    elif mode == 'refx':
        refx(argv[1])
    elif mode == 'fotos_partida':
        fotos_partida(argv[1], argv[2:])
    elif mode == 'photos':
        photos(argv[1], [n for a in argv[2:] for n in a.split(',') if n])
    elif mode == 'reimport':
        res = reimport_check(argv[1], argv[2].split(','))
        print('REIMPORT', json.dumps(res, ensure_ascii=False))
        with open(argv[3], 'w') as fh:
            json.dump(res, fh, ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
