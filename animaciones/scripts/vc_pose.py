"""Evaluación de canales -> pose, horneado de Actions y chequeo de colisiones."""
import math
import bpy
import numpy as np
from mathutils import Matrix, Vector, Quaternion

import vc_core as C
import vc_scene as S
from vc_core import R, rot_pyr, vec

# --------------------------------------------------------------------------------------
# Presets de dedos (semántica mano IZQUIERDA; filas = thumb1..3, index1..3, middle, ring, pinky)
# columnas: (curl X, giro Y, abducción Z) en grados
# --------------------------------------------------------------------------------------


def fingers(thumb=((0, 0, 0), (0, 0, 0), (0, 0, 0)), index=(0, 0, 0), middle=(0, 0, 0), ring=(0, 0, 0),
            pinky=(0, 0, 0), spread=(0, 0, 0, 0)):
    """index..pinky: (curl1, curl2, curl3). spread: abducción en _01 de index, middle, ring, pinky."""
    a = np.zeros((15, 3))
    for i in range(3):
        a[i] = thumb[i]
    for fi, (f, sp) in enumerate(zip((index, middle, ring, pinky), spread)):
        for j in range(3):
            a[3 + fi * 3 + j, 0] = f[j]
        a[3 + fi * 3, 2] = sp
    return a


# valores calibrados con renders (ver scripts/explorar_mano.py)
THUMB_REST = ((0, 0, 0), (0, 0, 0), (0, 0, 0))
F = {}


def define_presets(thumb_relax, thumb_pinch, thumb_fist, thumb_up, thumb_flat, thumb_knock, thumb_count):
    F['open'] = fingers(thumb_flat, (-2, -2, 0), (-2, -2, 0), (-2, -2, 0), (-2, -2, 0), spread=(3, 0, -2, -4))
    F['flat'] = fingers(thumb_flat, (0, 2, 2), (0, 2, 2), (0, 2, 2), (0, 2, 2), spread=(2, 0, -2, -4))
    F['relax'] = fingers(thumb_relax, (14, 18, 10), (18, 22, 12), (22, 26, 14), (26, 30, 16), spread=(2, 0, -2, -4))
    F['fan'] = fingers(thumb_flat, (-5, -3, 0), (-5, -3, 0), (-5, -3, 0), (-5, -3, 0), spread=(-14, -3, 9, 20))
    F['fist'] = fingers(thumb_fist, (85, 95, 55), (88, 98, 55), (88, 95, 55), (85, 92, 55), spread=(0, 0, 0, 0))
    F['pinch'] = fingers(thumb_pinch, (28, 22, 12), (40, 42, 22), (52, 48, 26), (62, 52, 28), spread=(2, 0, -3, -6))
    F['point'] = fingers(thumb_fist, (0, 0, 0), (88, 98, 55), (88, 95, 55), (85, 92, 55))
    F['thumbup'] = fingers(thumb_up, (85, 95, 55), (88, 98, 55), (88, 95, 55), (85, 92, 55))
    F['knock'] = fingers(thumb_knock, (88, 95, 40), (90, 98, 40), (90, 95, 40), (88, 92, 40))
    F['claw'] = fingers(thumb_relax, (30, 35, 20), (32, 38, 22), (34, 40, 22), (36, 42, 24), spread=(4, 0, -3, -6))
    F['cup'] = fingers(thumb_relax, (20, 25, 15), (22, 28, 16), (24, 30, 18), (26, 32, 18), spread=(0, 0, 0, 0))
    F['count0'] = F['fist']
    # contar 1..5 (índice, +medio, +anular, +meñique, +pulgar)
    F['count1'] = fingers(thumb_count, (0, 0, 0), (88, 98, 55), (88, 95, 55), (85, 92, 55))
    F['count2'] = fingers(thumb_count, (0, 0, 0), (0, 0, 0), (88, 95, 55), (85, 92, 55), spread=(3, -3, 0, 0))
    F['count3'] = fingers(thumb_count, (0, 0, 0), (0, 0, 0), (0, 0, 0), (85, 92, 55), spread=(4, 0, -4, 0))
    F['count4'] = fingers(thumb_count, (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0), spread=(5, 0, -5, -9))
    F['count5'] = F['fan']


def finger_mix(*pairs):
    out = np.zeros((15, 3))
    tot = 0.0
    for name, w in pairs:
        out += F[name] * w if isinstance(name, str) else name * w
        tot += w
    return out / tot


# --------------------------------------------------------------------------------------
# Valores por defecto (de pie, relajado)
# --------------------------------------------------------------------------------------
REST_ANKLE = {}


def defaults(rig):
    d = {}
    d['hips'] = np.zeros(3)
    d['hips_rot'] = np.zeros(3)
    d['spine'] = np.zeros(3)
    d['chest'] = np.zeros(3)
    d['neck'] = np.zeros(3)
    d['head'] = np.zeros(3)
    for s, sg in (('L', 1), ('R', -1)):
        d['clav' + s] = np.zeros(2)
        d['arm' + s] = ('chest', (sg * 0.215, -0.035, 0.925))
        d['pole' + s] = np.array([sg * 0.35, 1.0, -0.2])
        d['hdir' + s] = ('chest', (sg * 0.06, -0.12, -1.0))
        d['hpalm' + s] = ('chest', (-sg * 1.0, 0.1, 0.0))
        d['auto' + s] = 0.8
        d['split' + s] = 0.5
        d['fing' + s] = F['relax'].copy() if 'relax' in F else np.zeros((15, 3))
        a = rig.head['foot_' + ('l' if s == 'L' else 'r')]
        d['foot' + s] = np.array(a[:])
        d['frot' + s] = np.zeros(3)
        d['knee' + s] = np.array([sg * 0.1, -1.0, 0.0])
        d['toe' + s] = 0.0
    d['eyes'] = np.zeros(2)
    d['tableL'] = 0.0
    d['tableR'] = 0.0
    d['liftL'] = 0.0
    d['liftR'] = 0.0
    d['chair'] = 0.0
    return d


# --------------------------------------------------------------------------------------
# Morfos
# --------------------------------------------------------------------------------------
FACE_PRESETS = {
    'smile': {'mouthSmileLeft': 0.8, 'mouthSmileRight': 0.8, 'cheekSquintLeft': 0.4, 'cheekSquintRight': 0.4,
              'eyeSquintLeft': 0.25, 'eyeSquintRight': 0.25},
    'laugh': {'mouthSmileLeft': 1.0, 'mouthSmileRight': 1.0, 'jawOpen': 0.45, 'cheekSquintLeft': 0.7,
              'cheekSquintRight': 0.7, 'eyeSquintLeft': 0.6, 'eyeSquintRight': 0.6, 'mouthUpperUpLeft': 0.3,
              'mouthUpperUpRight': 0.3, 'browInnerUp': 0.2},
    'surprise': {'eyeWideLeft': 0.9, 'eyeWideRight': 0.9, 'browInnerUp': 0.8, 'browOuterUpLeft': 0.8,
                 'browOuterUpRight': 0.8, 'jawOpen': 0.35, 'mouthFunnel': 0.25},
    'mouth_open': {'jawOpen': 0.8, 'mouthLowerDownLeft': 0.3, 'mouthLowerDownRight': 0.3},
    'angry': {'browDownLeft': 0.95, 'browDownRight': 0.95, 'noseSneerLeft': 0.6, 'noseSneerRight': 0.6,
              'mouthFrownLeft': 0.6, 'mouthFrownRight': 0.6, 'eyeSquintLeft': 0.4, 'eyeSquintRight': 0.4,
              'mouthPressLeft': 0.5, 'mouthPressRight': 0.5, 'jawForward': 0.2},
    'shout': {'browDownLeft': 0.9, 'browDownRight': 0.9, 'noseSneerLeft': 0.7, 'noseSneerRight': 0.7,
              'jawOpen': 0.5, 'mouthStretchLeft': 0.5, 'mouthStretchRight': 0.5, 'mouthUpperUpLeft': 0.4,
              'mouthUpperUpRight': 0.4, 'eyeSquintLeft': 0.4, 'eyeSquintRight': 0.4},
    'sad': {'browInnerUp': 0.8, 'mouthFrownLeft': 0.7, 'mouthFrownRight': 0.7, 'mouthShrugLower': 0.4,
            'eyeSquintLeft': 0.15, 'eyeSquintRight': 0.15, 'eyeLookDownLeft': 0.3, 'eyeLookDownRight': 0.3},
    'dismay': {'browInnerUp': 1.0, 'jawOpen': 0.3, 'mouthFrownLeft': 0.6, 'mouthFrownRight': 0.6,
               'mouthStretchLeft': 0.4, 'mouthStretchRight': 0.4, 'eyeWideLeft': 0.4, 'eyeWideRight': 0.4},
    'think': {'browDownLeft': 0.35, 'browInnerUp': 0.25, 'mouthPressLeft': 0.35, 'mouthPressRight': 0.35,
              'mouthLeft': 0.25, 'eyeSquintLeft': 0.2, 'eyeSquintRight': 0.2, 'mouthRollLower': 0.2},
    'focus': {'browDownLeft': 0.2, 'browDownRight': 0.2, 'eyeSquintLeft': 0.15, 'eyeSquintRight': 0.15,
              'mouthPressLeft': 0.2, 'mouthPressRight': 0.2},
    'determined': {'browDownLeft': 0.45, 'browDownRight': 0.45, 'mouthPressLeft': 0.5, 'mouthPressRight': 0.5,
                   'jawForward': 0.15, 'eyeSquintLeft': 0.2, 'eyeSquintRight': 0.2, 'mouthSmileLeft': 0.2},
    'blink': {'eyeBlinkLeft': 1.0, 'eyeBlinkRight': 1.0},
    'pucker': {'mouthPucker': 0.8, 'mouthFunnel': 0.2},
}


def face(*pairs, **extra):
    """face(('smile',1.0), ('surprise',0.3), jawOpen=0.2) -> dict de canales face.*"""
    out = {}
    for name, w in pairs:
        for k, v in FACE_PRESETS[name].items():
            out[k] = out.get(k, 0.0) + v * w
    for k, v in extra.items():
        out[k] = out.get(k, 0.0) + v
    return {'face.' + k: min(1.0, v) for k, v in out.items()}


ALL_FACE_KEYS = None


def all_face_keys():
    global ALL_FACE_KEYS
    if ALL_FACE_KEYS is None:
        names = []
        for mn in C.FACE_MESHES:
            ob = bpy.data.objects[mn]
            for kb in ob.data.shape_keys.key_blocks[1:]:
                if kb.name not in names and not kb.name.startswith(('Cintura', 'Cara_volumen')):
                    names.append(kb.name)
        ALL_FACE_KEYS = names
    return ALL_FACE_KEYS


def neutral_face():
    return {'face.' + k: 0.0 for k in all_face_keys()}


def blink_proc(frames_list, dur=5):
    """Parpadeos en los cuadros dados (inicio)."""
    def fn(f, P, ev):
        w = 0.0
        for b in frames_list:
            x = (f - b) / dur
            if 0 <= x <= 1:
                w = max(w, math.sin(math.pi * x) ** 0.7)
        if w > 0:
            for k in ('eyeBlinkLeft', 'eyeBlinkRight'):
                P['face.' + k] = max(P.get('face.' + k, 0.0), w)
    return fn


# --------------------------------------------------------------------------------------
# Evaluador
# --------------------------------------------------------------------------------------
_TS = np.linspace(0.0, 1.0, 7)


def seg_cost(S_, E, W):
    """Costo de que el brazo (cilindro) quede por debajo del paño/riel."""
    E = np.array(E[:])
    W = np.array(W[:])
    S0 = np.array(S_[:])
    pts = np.concatenate([E + (W - E) * _TS[:, None], S0 + (E - S0) * _TS[3:, None]])
    rad = np.concatenate([0.040 * (1 - _TS) + 0.030 * _TS, np.full(4, 0.052)])
    sup = support_height(pts)
    ok = np.isfinite(sup)
    if not ok.any():
        return 0.0
    pen = np.maximum(0.0, sup[ok] + rad[ok] - pts[ok, 2])
    return float((pen ** 2).sum() * 4e6)


def support_height(P):
    """Altura del soporte (paño o riel) bajo cada punto; -inf fuera de la mesa."""
    x, y = P[:, 0], P[:, 1]
    h = np.full(len(P), -np.inf)
    half = S.TABLE_SIZE / 2
    inside = (np.abs(x) < half) & (y < S.TABLE_NEAR_Y) & (y > S.TABLE_NEAR_Y - S.TABLE_SIZE)
    h[inside] = S.TABLE_TOP
    rail = inside & ((y > S.TABLE_NEAR_Y - S.RAIL_W) | (y < S.TABLE_NEAR_Y - S.TABLE_SIZE + S.RAIL_W) |
                     (np.abs(x) > half - S.RAIL_W))
    h[rail] = S.RAIL_TOP
    return h


class Evaluator:
    def __init__(self, rig, skin=None):
        self.rig = rig
        self.defaults = defaults(rig)
        self.prev_theta = {}
        self.skin = skin
        self.hand_sel = {}
        if skin is not None:
            for s in 'lr':
                bones = [n for n in rig.names if n.endswith('_' + s) and n.split('_')[0] in
                         ('hand', 'thumb', 'index', 'middle', 'ring', 'pinky')]
                self.hand_sel[s] = np.where(skin.bone_weight(bones) > 0.35)[0]
                self.fore_sel = getattr(self, 'fore_sel', {})
                self.fore_sel[s] = np.where(skin.bone_weight(['lowerarm_' + s]) > 0.35)[0]

    def channels_at(self, anim, f, pb):
        """Devuelve dict de canales numéricos en el cuadro f. Necesita pb para resolver espacios."""
        period = anim.frames if anim.loop else None
        P = {}

        def resolver(kind):
            def res(v):
                if isinstance(v, tuple) and len(v) == 2 and isinstance(v[0], str):
                    sp, val = v
                    if kind == 'point':
                        return np.array(pb.space_point(sp, val)[:])
                    return np.array(pb.space_dir(sp, val)[:])
                return np.asarray(v, dtype=np.float64)
            return res
        return P, resolver, period

    def value(self, anim, ch, f, pb, kind='plain'):
        period = anim.frames if anim.loop else None
        res = self._resolver(pb, kind)
        tr = anim.tracks.get(ch)
        if tr is None or not tr.keys:
            return res(self.defaults[ch]) if ch in self.defaults else None
        return C.eval_track(tr, f, res, period)

    def _resolver(self, pb, kind):
        def res(v):
            if isinstance(v, tuple) and len(v) == 2 and isinstance(v[0], str):
                sp, val = v
                if kind == 'point':
                    return np.array(pb.space_point(sp, val)[:])
                return np.array(pb.space_dir(sp, val)[:])
            return np.atleast_1d(np.asarray(v, dtype=np.float64))
        return res

    def evaluate(self, anim, f):
        """Construye la pose del cuadro f. Devuelve (PoseBuilder, face_dict)."""
        rig = self.rig
        pb = C.PoseBuilder(rig)
        # Canales escalares/vectoriales simples primero (permite procs que los modifiquen)
        P = {}
        simple = ['hips', 'hips_rot', 'spine', 'chest', 'neck', 'head', 'clavL', 'clavR', 'poleL', 'poleR',
                  'autoL', 'autoR', 'splitL', 'splitR', 'fingL', 'fingR', 'footL', 'footR', 'frotL', 'frotR',
                  'kneeL', 'kneeR', 'toeL', 'toeR', 'eyes', 'tableL', 'tableR', 'liftL', 'liftR', 'chair']
        for ch in simple:
            P[ch] = self.value(anim, ch, f, pb)
        for ch in anim.tracks:
            if ch.startswith('face.'):
                P[ch] = float(self.value(anim, ch, f, pb)[0])
        P['_pb'] = pb
        P['_f'] = f
        for fn in anim.procs:
            if getattr(fn, 'stage', 'pre') == 'pre':
                fn(f, P, self)
        # Cadera / columna
        pb.set_local('Root', Matrix.Identity(4))
        hp = P['hips_rot']
        Dp = rot_pyr(*hp)
        r3 = rig.rest3['pelvis']
        L = (r3.inverted() @ Dp @ r3).to_4x4()
        base = pb.parent_base('pelvis')
        L.translation = base.to_3x3().inverted() @ Vector(P['hips'][:3])
        pb.set_local('pelvis', L)
        sp = P['spine']
        for b, w in (('spine_01', 0.25), ('spine_02', 0.35), ('spine_03', 0.40)):
            extra = P['chest'] if b == 'spine_03' else np.zeros(3)
            pb.set_delta(b, rot_pyr(*(sp * w + extra)))
        pb.set_delta('neck_01', rot_pyr(*P['neck']))
        pb.set_delta('head', rot_pyr(*P['head']))
        # Clavículas
        for s, sg in (('L', 1), ('R', -1)):
            up, fw = P['clav' + s]
            # + up eleva el hombro, + fw lo lleva adelante
            D = R('Y', -sg * up) @ R('Z', -sg * fw)
            pb.set_delta('clavicle_' + s.lower(), D)
        # Brazos (pueden referirse a espacios de pecho/cabeza)
        for s in ('R', 'L'):
            if 'elbow' + s in anim.tracks:
                Et = self.value(anim, 'elbow' + s, f, pb, 'point')
                Sx = pb.parent_base('upperarm_' + s.lower()).translation
                P['pole' + s] = np.array((Vector(Et[:3]) - Sx)[:])
            W = self.value(anim, 'arm' + s, f, pb, 'point')
            hd = self.value(anim, 'hdir' + s, f, pb, 'dir')
            hpm = self.value(anim, 'hpalm' + s, f, pb, 'dir')
            P['arm' + s], P['hdir' + s], P['hpalm' + s] = W, hd, hpm
        for fn in anim.procs:
            if getattr(fn, 'stage', 'pre') == 'arms':
                fn(f, P, self)
        for s in ('R', 'L'):
            sl = s.lower()
            key = (anim.name, s)
            W = Vector(P['arm' + s][:3])
            wt = float(P['table' + s][0])
            prev = self.prev_theta.get(key)
            for it in range(4):
                th = pb.solve_arm(sl, W, Vector(P['pole' + s][:3]), Vector(P['hdir' + s][:3]),
                                  Vector(P['hpalm' + s][:3]), auto=float(P['auto' + s][0]),
                                  twist_split=float(P['split' + s][0]), prev_theta=prev, seg_cost=seg_cost)
                pb.set_fingers(sl, P['fing' + s].reshape(15, 3))
                if self.skin is None:
                    break
                full = dict(pb.pose)
                for n in self.rig.names:
                    if n not in full:
                        full[n] = Matrix.Identity(4)
                Q = self.skin.deform(full, self.hand_sel[sl])
                Qf = self.skin.deform(full, self.fore_sel[sl])
                sup = support_height(Q) + float(P['lift' + s][0])
                supf = support_height(Qf)
                ok = np.isfinite(sup)
                okf = np.isfinite(supf)
                if not ok.any() and not okf.any():
                    break
                margin = 0.0015
                gh = float((Q[ok, 2] - sup[ok]).min()) if ok.any() else 1.0
                gf = float((Qf[okf, 2] - supf[okf]).min()) if okf.any() else 1.0
                pen = gh
                if getattr(self, "debug", False): print("CONTACT", s, it, round(gh,4), round(gf,4), tuple(round(v,3) for v in W))
                dz = 0.0
                if pen < margin:
                    dz = margin - pen
                elif wt > 0 and gh < 1.0:
                    dz = -wt * min(gh - margin, pen - margin)
                if abs(dz) < 2e-4:
                    break
                W = W + Vector((0, 0, dz))
            self.prev_theta[key] = th
            pb.diag['arm_' + sl]['contact_dz'] = float((W - Vector(P['arm' + s][:3])).z)
            P['arm' + s] = np.array(W[:])
        # Piernas
        for s in ('L', 'R'):
            sl = s.lower()
            fr = P['frot' + s]
            pb.solve_leg(sl, Vector(P['foot' + s][:3]), Vector(P['knee' + s][:3]), rot_pyr(*fr),
                         toe_pitch=float(P['toe' + s][0]), toe_yaw=float(fr[1]))
        pb.finish()
        # Cara
        fd = {}
        for k, v in P.items():
            if k.startswith('face.'):
                fd[k[5:]] = float(np.clip(v, 0, 1))
        ey, ep = P['eyes']
        if ey > 0:
            fd['eyeLookOutLeft'] = max(fd.get('eyeLookOutLeft', 0), min(1, ey / 30))
            fd['eyeLookInRight'] = max(fd.get('eyeLookInRight', 0), min(1, ey / 30))
        elif ey < 0:
            fd['eyeLookOutRight'] = max(fd.get('eyeLookOutRight', 0), min(1, -ey / 30))
            fd['eyeLookInLeft'] = max(fd.get('eyeLookInLeft', 0), min(1, -ey / 30))
        if ep > 0:
            fd['eyeLookDownLeft'] = max(fd.get('eyeLookDownLeft', 0), min(1, ep / 30))
            fd['eyeLookDownRight'] = max(fd.get('eyeLookDownRight', 0), min(1, ep / 30))
        elif ep < 0:
            fd['eyeLookUpLeft'] = max(fd.get('eyeLookUpLeft', 0), min(1, -ep / 25))
            fd['eyeLookUpRight'] = max(fd.get('eyeLookUpRight', 0), min(1, -ep / 25))
        pb.P = P
        return pb, fd


# --------------------------------------------------------------------------------------
# Horneado
# --------------------------------------------------------------------------------------
def frame_list(anim):
    return list(range(0, anim.frames + 1))


def bake(anim, rig, ev, start=1):
    """Evalúa todos los cuadros; crea la Action. Devuelve (action, poses, faces)."""
    frames = frame_list(anim)
    poses, faces = [], []
    ev.prev_theta = {}
    for f in frames:
        pb, fd = ev.evaluate(anim, f)
        poses.append(pb)
        faces.append(fd)
    if anim.loop:
        # cierre exacto del bucle
        poses[-1] = poses[0]
        faces[-1] = faces[0]
    act = bpy.data.actions.get(anim.name)
    if act:
        bpy.data.actions.remove(act)
    act = bpy.data.actions.new(anim.name)
    act.use_fake_user = True
    act.use_frame_range = True
    act.frame_start = start
    act.frame_end = start + anim.frames
    act.use_cyclic = anim.loop
    layer = act.layers.new('Base')
    strip = layer.strips.new(type='KEYFRAME')
    slot = act.slots.new(id_type='OBJECT', name=rig.arm.name)
    cb = strip.channelbag(slot, ensure=True)
    n = len(frames)
    xs = np.array([start + f for f in frames], dtype=np.float64)

    def add_curve(cbag, path, idx, vals, group):
        fc = cbag.fcurves.new(path, index=idx)
        if group:
            grp = cbag.groups.get(group) if hasattr(cbag.groups, 'get') else None
            if grp is None:
                grp = next((g for g in cbag.groups if g.name == group), None) or cbag.groups.new(group)
            fc.group = grp
        fc.keyframe_points.add(n)
        co = np.empty(2 * n)
        co[0::2] = xs
        co[1::2] = vals
        fc.keyframe_points.foreach_set('co', co)
        fc.keyframe_points.foreach_set('interpolation', [1] * n)  # LINEAR (ya está horneado)
        fc.update()
        return fc

    for bn in rig.names:
        qs = []
        prev = None
        for pb in poses:
            q = pb.local[bn].to_quaternion()
            if prev is not None and prev.dot(q) < 0:
                q.negate()
            qs.append(q)
            prev = q
        qa = np.array([q[:] for q in qs])
        path = f'pose.bones["{bn}"].rotation_quaternion'
        for i in range(4):
            add_curve(cb, path, i, qa[:, i], bn)
        if bn == 'pelvis':
            la = np.array([pb.local[bn].translation[:] for pb in poses])
            for i in range(3):
                add_curve(cb, f'pose.bones["{bn}"].location', i, la[:, i], bn)
    # Shape keys: un slot por malla
    keys_all = all_face_keys()
    act['_face_slots'] = []
    for mn in C.FACE_MESHES:
        ob = bpy.data.objects[mn]
        key = ob.data.shape_keys
        kslot = act.slots.new(id_type='KEY', name=key.name)
        kcb = strip.channelbag(kslot, ensure=True)
        names = [kb.name for kb in key.key_blocks[1:] if kb.name in keys_all]
        for kn in names:
            vals = np.array([fd.get(kn, 0.0) for fd in faces])
            add_curve(kcb, f'key_blocks["{kn}"].value', 0, vals, None)
    return act, poses, faces


def assign(act, rig):
    ad = rig.arm.animation_data or rig.arm.animation_data_create()
    ad.action = act
    ad.action_slot = act.slots['OB' + rig.arm.name]
    for mn in C.FACE_MESHES:
        key = bpy.data.objects[mn].data.shape_keys
        kad = key.animation_data or key.animation_data_create()
        kad.action = act
        kad.action_slot = act.slots['KE' + key.name]


def apply_pose_static(pb, rig, fd=None):
    """Aplica una pose directamente (sin action), para fotos de prueba."""
    for bn in rig.names:
        p = rig.arm.pose.bones[bn]
        p.rotation_mode = 'QUATERNION'
        p.matrix_basis = pb.local[bn]
    if fd is not None:
        for mn in C.FACE_MESHES:
            key = bpy.data.objects[mn].data.shape_keys
            for kb in key.key_blocks[1:]:
                if kb.name in all_face_keys():
                    kb.value = fd.get(kb.name, 0.0)


# --------------------------------------------------------------------------------------
# Ayudas de diseño de poses
# --------------------------------------------------------------------------------------
def torso_eval(ev, chans):
    """Evalúa solo el torso con los canales dados y devuelve el PoseBuilder."""
    A = C.Anim('_tmp', 1)
    A.key(0, chans)
    pb, _ = ev.evaluate(A, 0)
    return pb


def to_space(pb, space, p_world):
    """Punto del mundo -> coordenadas 'de reposo' del espacio dado (inverso de space_point)."""
    b = {'chest': 'spine_03', 'pelvis': 'pelvis', 'head': 'head', 'spine2': 'spine_02'}.get(space, space)
    return tuple((pb.rig.rest[b] @ pb.pose[b].inverted() @ Vector(p_world))[:])


def dir_to_space(pb, space, d_world):
    b = {'chest': 'spine_03', 'pelvis': 'pelvis', 'head': 'head', 'spine2': 'spine_02'}.get(space, space)
    return tuple((pb.rig.rest3[b] @ pb.world_rot(b).inverted() @ Vector(d_world))[:])


def arm_from_dirs(pb, side, upper_dir, fore_dir, space='chest'):
    """Devuelve (muñeca, codo) en el espacio dado a partir de direcciones del brazo y antebrazo."""
    rig = pb.rig
    s = side.lower()
    S_ = pb.parent_base('upperarm_' + s).translation
    E = S_ + Vector(upper_dir).normalized() * rig.length['upperarm_' + s]
    W = E + Vector(fore_dir).normalized() * rig.length['lowerarm_' + s] * 0.995
    if space == 'world':
        return tuple(W[:]), tuple(E[:])
    return (space, to_space(pb, space, W)), (space, to_space(pb, space, E))


# --------------------------------------------------------------------------------------
# Fichas (solo previsualización + chequeo)
# --------------------------------------------------------------------------------------
GRIP_OFFSET = {}


def flat_tile(M):
    """Proyecta la ficha sobre la mesa: solo guiñada, z = paño + medio grosor."""
    x = M.to_3x3().col[0].copy()
    x.z = 0
    if x.length < 1e-6:
        x = Vector((1, 0, 0))
    x.normalize()
    z = Vector((0, 0, 1))
    y = z.cross(x)
    R3 = Matrix((x, y, z)).transposed()
    out = R3.to_4x4()
    out.translation = Vector((M.translation.x, M.translation.y, S.TABLE_TOP + S.TILE[2] / 2))
    return out


def tile_matrix(x, y, yaw_deg, z=None):
    M = (R('Z', yaw_deg)).to_4x4()
    M.translation = Vector((x, y, (S.TABLE_TOP + S.TILE[2] / 2) if z is None else z))
    return M


def compute_tiles(anim, poses):
    """anim.tiles: lista de dicts {name, side, start:('table',M)|('hand',offset|None), grab, release, flat}"""
    out = {}
    for t in anim.tiles:
        bone = 'hand_' + t.get('side', 'r')
        mats = []
        kind = t['start'][0]
        if kind == 'table':
            M = t['start'][1].copy()
            offset = None
        else:
            offset = t['start'][1] if len(t['start']) > 1 and t['start'][1] is not None else GRIP_OFFSET[t.get('side', 'r')]
            M = None
        grab = t.get('grab')
        rel = t.get('release')
        for f, pb in enumerate(poses):
            hp = pb.pose[bone]
            if grab is not None and f == grab and offset is None:
                offset = hp.inverted() @ M
            attached = offset is not None and (grab is None or f >= grab) and (rel is None or f < rel)
            if attached:
                Mf = hp @ offset
                if t.get('flat'):
                    Mf = flat_tile(Mf)
                mats.append(Mf)
            else:
                if rel is not None and f == rel and offset is not None:
                    M = flat_tile(hp @ offset)
                mats.append(M.copy())
        out[t['name']] = mats
    return out


GRIP_CANON = {}


def compute_grip(rig, skin, side='r', fdir=(0.30, -0.90, -0.30), palm_hint=(0.2, 0.2, -1.0)):
    """Calcula el offset canónico mano->ficha para la pinza (yemas reales de pulgar e índice)."""
    import vc_hand as H
    s = side
    sg = -1 if s == 'r' else 1
    arr = F['pinch']
    center, axis, pt, pi = H.grip_local(rig, skin, arr, s)
    hb = 'hand_' + s
    c_h = rig.rest[hb].inverted() @ center
    a_h = rig.rest3[hb].inverted() @ axis
    fd = Vector((fdir[0] * (-sg), fdir[1], fdir[2]))  # espejo para la izquierda
    ph = Vector((palm_hint[0] * (-sg), palm_hint[1], palm_hint[2]))
    _, _, Rh = H.hand_frame_for_grip(rig, s, axis, fd, ph)
    Rw = Rh @ rig.rest3[hb]
    HW = Rw.to_4x4()
    tc = HW @ c_h
    ax = Rw @ a_h
    ax.z = 0
    ax.normalize()
    z = Vector((0, 0, 1))
    T = Matrix((ax, z.cross(ax), z)).transposed().to_4x4()
    T.translation = tc
    offset = HW.inverted() @ T
    GRIP_OFFSET[s] = offset
    F0, P0 = rig.hand_ref[s]
    fh = Rh @ F0
    heading = math.degrees(math.atan2(fh.y, fh.x))
    tile_yaw = math.degrees(math.atan2(ax.y, ax.x))
    GRIP_CANON[s] = dict(heading=heading, tile_yaw=tile_yaw, gap=(pi - pt).length)
    return offset


def hand_channels_for_tile(rig, side, T):
    """Canales de brazo/mano para que la ficha (matriz T en el mundo) quede entre las yemas."""
    s = side
    S_ = s.upper()
    HW = T @ GRIP_OFFSET[s].inverted()
    Rw = HW.to_3x3()
    Rh = Rw @ rig.rest3['hand_' + s].inverted()
    F0, P0 = rig.hand_ref[s]
    return {'arm' + S_: tuple(HW.translation[:]), 'hdir' + S_: tuple((Rh @ F0)[:]),
            'hpalm' + S_: tuple((Rh @ P0)[:])}


def grip_at(rig, side, x, y, heading=None, z=None, lift=0.0):
    """Mano en pinza sobre una ficha en (x,y). heading: dirección (grados en XY) hacia donde apuntan los dedos.
    Devuelve (canales, matriz de la ficha)."""
    s = side
    c = GRIP_CANON[s]
    if heading is None:
        heading = c['heading']
    yaw = c['tile_yaw'] + (heading - c['heading'])
    T = tile_matrix(x, y, yaw, z)
    Th = T.copy()
    Th.translation.z += lift
    return hand_channels_for_tile(rig, s, Th), T


def heading_to(rig, pb, side, x, y):
    S_ = pb.parent_base('upperarm_' + side).translation
    return math.degrees(math.atan2(y - S_.y, x - S_.x))


_GRIP_LOCAL = {}


def grip_offset(rig, skin, side, fd, palm_hint):
    """Offset mano->ficha para una orientación de mano (fd = dirección de dedos)."""
    import vc_hand as H
    s = side
    hb = 'hand_' + s
    if s not in _GRIP_LOCAL:
        center, axis, pt, pi = H.grip_local(rig, skin, F['pinch'], s)
        _GRIP_LOCAL[s] = (rig.rest[hb].inverted() @ center, rig.rest3[hb].inverted() @ axis, axis)
    c_h, a_h, axis_rest = _GRIP_LOCAL[s]
    _, _, Rh = H.hand_frame_for_grip(rig, s, axis_rest, Vector(fd), Vector(palm_hint))
    Rw = Rh @ rig.rest3[hb]
    HW = Rw.to_4x4()
    tc = HW @ c_h
    ax = Rw @ a_h
    tilt = abs(ax.normalized().z)
    ax.z = 0
    ax.normalize()
    z = Vector((0, 0, 1))
    yv = z.cross(ax)
    # pinza cerca de un extremo: el cuerpo de la ficha queda hacia fuera, lejos de los dedos curvados
    away = tc - HW.translation
    if yv.dot(away) < 0:
        yv = -yv
        ax = -ax
    T = Matrix((ax, yv, z)).transposed().to_4x4()
    T.translation = tc + yv * GRIP_END_SHIFT
    return HW.inverted() @ T, tilt


GRIP_END_SHIFT = 0.026


def natural_hand(ev, base, side, arm, elbow, palm, flex=0.0, dev=0.0, exact_palm=False, extra=None):
    """Dirección de mano coherente con el antebrazo real (IK) -> canales de brazo en el mundo.
    palm: dirección deseada de la palma (mundo o (espacio, v)). flex + = flexión hacia la palma.
    exact_palm: la palma se respeta exactamente y los dedos siguen la proyección del antebrazo."""
    S_ = side.upper()
    d = dict(base)
    d.update({'arm' + S_: arm, 'elbow' + S_: elbow, 'table' + S_: 0.0})
    if extra:
        d.update(extra)
    A = C.Anim('_n', 1)
    A.key(0, d)
    ev.prev_theta = {}
    pb, _ = ev.evaluate(A, 0)
    dg = pb.diag['arm_' + side.lower()]
    W = Vector(pb.P['arm' + S_][:3])
    fore = (W - dg['E']).normalized()
    pv = Vector(pb.space_dir(*palm) if isinstance(palm[0], str) else palm).normalized()
    if exact_palm:
        hd = (fore - pv * fore.dot(pv)).normalized()
        pn = pv
    else:
        hd = fore
        pn = (pv - fore * fore.dot(pv)).normalized()
    if flex:
        a = math.radians(flex)
        hd, pn = (hd * math.cos(a) + pn * math.sin(a)).normalized(), (pn * math.cos(a) - hd * math.sin(a)).normalized()
    if dev:
        hd = (Matrix.Rotation(math.radians(dev), 3, pn) @ hd).normalized()
    out = {'arm' + S_: arm, 'elbow' + S_: elbow, 'hdir' + S_: tuple(hd[:]), 'hpalm' + S_: tuple(pn[:]),
           'table' + S_: 0.0}
    return out


def best_grip(ev, base, side, x, y, z=None, lift=0.0, fingers_key='pinch', pitches=None, dheads=None,
              offset=None, yaws=None):
    """Busca la orientación de mano más natural para agarrar/soltar una ficha en (x,y).
    Si offset se da (ficha ya en la mano), solo se busca la guiñada de la ficha."""
    rig, skin = ev.rig, ev.skin
    s = side
    S_ = s.upper()
    pbt = torso_eval(ev, base)
    Sh = pbt.parent_base('upperarm_' + s).translation
    head0 = math.degrees(math.atan2(y - Sh.y, x - Sh.x))
    best = None
    cands = []
    if offset is None:
        for pitch in (pitches or range(-60, 1, 6)):
            for dh in (dheads or range(-30, 31, 10)):
                hh = math.radians(head0 + dh)
                pr = math.radians(pitch)
                fd = Vector((math.cos(hh) * math.cos(pr), math.sin(hh) * math.cos(pr), math.sin(pr)))
                side_v = Vector((-math.sin(hh), math.cos(hh), 0)) * (1 if s == 'r' else -1)
                ph = Vector((0, 0, -1)) + side_v * 0.25
                off, tilt = grip_offset(rig, skin, s, fd, ph)
                if tilt > 0.15:
                    continue
                cands.append(off)
    else:
        cands = [offset]
    for off in cands:
        # guiñada de la ficha: la que deja la mano apuntando hacia el rumbo deseado
        HW0 = off.inverted()
        fdir0 = (HW0.to_3x3() @ rig.rest3['hand_' + s].inverted() @ rig.hand_ref[s][0])
        base_yaw = head0 - math.degrees(math.atan2(fdir0.y, fdir0.x))
        for dy in (yaws or ((0,) if offset is None else range(-40, 41, 10))):
            T = tile_matrix(x, y, base_yaw + dy, z)
            Th = T.copy()
            Th.translation.z += lift
            HW = Th @ off.inverted()
            Rh = HW.to_3x3() @ rig.rest3['hand_' + s].inverted()
            F0, P0 = rig.hand_ref[s]
            ch = {'arm' + S_: tuple(HW.translation[:]), 'hdir' + S_: tuple((Rh @ F0)[:]),
                  'hpalm' + S_: tuple((Rh @ P0)[:]), 'fing' + S_: F[fingers_key], 'table' + S_: 0.0}
            d = dict(base)
            d.update(ch)
            d.pop('elbow' + S_, None)
            A = C.Anim('_g', 1)
            A.key(0, d)
            ev.prev_theta = {}
            pb, _ = ev.evaluate(A, 0)
            dg = pb.diag['arm_' + s]
            cost = (dg['wrist'] / 10) ** 2 + (max(0, dg['reach'] - 0.95) / 0.02) ** 2 + \
                   (dg['contact_dz'] / 0.002) ** 2 + (abs(dg['twist']) / 40) ** 2 + 0.002 * dy * dy
            if best is None or cost < best[0]:
                best = (cost, ch, T, off, dict(wrist=dg['wrist'], reach=dg['reach'], dz=dg['contact_dz'],
                                               twist=dg['twist'], elbow=dg['elbow']))
    return best[1], best[2], best[3], best[4]
