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


def seg_cost(S_, E, W, obst=()):
    """Costo de que el brazo (cilindro) quede por debajo del paño/riel/fichas paradas."""
    E = np.array(E[:])
    W = np.array(W[:])
    S0 = np.array(S_[:])
    pts = np.concatenate([E + (W - E) * _TS[:, None], S0 + (E - S0) * _TS[3:, None]])
    rad = np.concatenate([0.040 * (1 - _TS) + 0.030 * _TS, np.full(4, 0.052)])
    sup = support_height(pts, obst)
    ok = np.isfinite(sup)
    if not ok.any():
        return 0.0
    pen = np.maximum(0.0, sup[ok] + rad[ok] - pts[ok, 2])
    return float((pen ** 2).sum() * 4e6)


def support_height(P, obst=()):
    """Altura del soporte (paño, riel o ficha parada) bajo cada punto; -inf fuera de la mesa.
    obst: fichas paradas (cx, cy, cos, sin, medio_ancho, medio_grosor, z_arriba)."""
    x, y = P[:, 0], P[:, 1]
    h = np.full(len(P), -np.inf)
    half = S.TABLE_SIZE / 2
    inside = (np.abs(x) < half) & (y < S.TABLE_NEAR_Y) & (y > S.TABLE_NEAR_Y - S.TABLE_SIZE)
    h[inside] = S.TABLE_TOP
    rail = inside & ((y > S.TABLE_NEAR_Y - S.RAIL_W) | (y < S.TABLE_NEAR_Y - S.TABLE_SIZE + S.RAIL_W) |
                     (np.abs(x) > half - S.RAIL_W))
    h[rail] = S.RAIL_TOP
    for cx, cy, c, s_, hw, ht, top in obst:
        dx, dy = x - cx, y - cy
        u = dx * c + dy * s_
        v = -dx * s_ + dy * c
        m = (np.abs(u) < hw + 0.003) & (np.abs(v) < ht + 0.003)
        h[m] = np.maximum(h[m], top)
    return h


def full_pose(pb):
    """Pose completa (huesos aún no resueltos en reposo relativo a su padre) sin modificar pb."""
    rig = pb.rig
    out = dict(pb.pose)
    for n in rig.names:
        if n not in out:
            p = rig.par[n]
            out[n] = (out[p] if p else Matrix.Identity(4)) @ rig.rest_rel[n]
    return out


class Evaluator:
    def __init__(self, rig, skin=None, ck=None):
        self.rig = rig
        self.defaults = defaults(rig)
        self.prev_theta = {}
        self.skin = skin
        self.ck = ck
        self.hand_sel = {}
        self.fore_sel = {}
        self.upper_sel = {}
        self.foot_sel = {}
        self.contacts = True
        self.stats = {}
        if skin is not None:
            for s in 'lr':
                bones = [n for n in rig.names if n.endswith('_' + s) and n.split('_')[0] in
                         ('hand', 'thumb', 'index', 'middle', 'ring', 'pinky')]
                self.hand_sel[s] = np.where(skin.bone_weight(bones) > 0.35)[0]
                self.fore_sel[s] = np.where(skin.bone_weight(['lowerarm_' + s]) > 0.35)[0]
                self.upper_sel[s] = np.where(skin.bone_weight(['upperarm_' + s]) > 0.5)[0]
                self.foot_sel[s] = np.where(skin.bone_weight(['foot_' + s, 'ball_' + s]) > 0.3)[0]
        if ck is not None:
            reg = ck.region
            self.seat_sel = np.where(np.isin(reg, ('muslo', 'tronco')))[0]
            self.foot_bx = {}
            for s in 'lr':
                self.foot_bx[s] = None

    def _bump(self, k, v=1):
        self.stats[k] = self.stats.get(k, 0) + v

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

    # ------------------------------------------------------------------ contacto con el asiento
    def seat_pen(self, anim, pb):
        if self.ck is None or anim.props.get('nochair'):
            return 0.0
        dy = float(pb.P['chair'][0])
        full = full_pose(pb)
        pts = [self.ck.body.deform(full, self.seat_sel), self.ck.boxer.deform(full)]
        pen = 0.0
        for Q in pts:
            m = (np.abs(Q[:, 0]) < S.SEAT_W / 2) & (np.abs(Q[:, 1] - S.SEAT_CY - dy) < S.SEAT_D / 2) & \
                (Q[:, 2] > S.SEAT_Z - 0.06) & (Q[:, 2] < S.SEAT_Z + 0.002)
            if m.any():
                pen = max(pen, float(S.SEAT_Z + 0.002 - Q[m, 2].min()))
        return pen

    def evaluate(self, anim, f):
        """Construye la pose del cuadro f. Devuelve (PoseBuilder, face_dict)."""
        saved = dict(self.prev_theta)
        pb, fd = self._evaluate(anim, f, 0.0)
        if self.contacts:
            dz = 0.0
            for _ in range(3):
                pen = self.seat_pen(anim, pb)
                if pen <= 0.0003:
                    break
                dz += pen
                self.prev_theta = dict(saved)
                pb, fd = self._evaluate(anim, f, dz)
                self._bump('asiento')
        return pb, fd

    def _evaluate(self, anim, f, hip_dz):
        rig = self.rig
        pb = C.PoseBuilder(rig)
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
        if hip_dz:
            P['hips'] = np.array(P['hips'], dtype=float) + np.array([0, 0, hip_dz])
        obst = anim.obstacles(f) if hasattr(anim, 'obstacles') else ()
        self.obst = obst
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
        for s, sg in (('L', 1), ('R', -1)):
            up, fw = P['clav' + s]
            D = R('Y', -sg * up) @ R('Z', -sg * fw)
            pb.set_delta('clavicle_' + s.lower(), D)
        # Piernas (antes que los brazos: los muslos cuentan para la auto-colisión)
        for s in ('L', 'R'):
            sl = s.lower()
            fr = P['frot' + s]
            A_ = Vector(P['foot' + s][:3])
            for it in range(3):
                pb.solve_leg(sl, A_, Vector(P['knee' + s][:3]), rot_pyr(*fr),
                             toe_pitch=float(P['toe' + s][0]), toe_yaw=float(fr[1]))
                if not self.contacts or self.skin is None:
                    break
                Qf = self.skin.deform(full_pose(pb), self.foot_sel[sl])
                mz = float(Qf[:, 2].min())
                if mz >= -0.0002:
                    break
                A_ = A_ + Vector((0, 0, -mz + 0.0003))
                self._bump('suelo')
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
        sc = seg_cost if not obst else (lambda a, b, c: seg_cost(a, b, c, obst))
        # pasada previa sin contactos (completa la pose para la BVH del cuerpo)
        for s in ('R', 'L'):
            sl = s.lower()
            pb.solve_arm(sl, Vector(P['arm' + s][:3]), Vector(P['pole' + s][:3]), Vector(P['hdir' + s][:3]),
                         Vector(P['hpalm' + s][:3]), auto=float(P['auto' + s][0]),
                         twist_split=float(P['split' + s][0]), prev_theta=self.prev_theta.get((anim.name, s)),
                         seg_cost=sc)
            pb.set_fingers(sl, P['fing' + s].reshape(15, 3))
        tree = None
        use_contacts = self.contacts and self.skin is not None
        if use_contacts and self.ck is not None:
            tree, _ = self.ck.selfcol.tree(full_pose(pb))
        for s in ('R', 'L'):
            sl = s.lower()
            key = (anim.name, s)
            W = Vector(P['arm' + s][:3])
            wt = float(P['table' + s][0])
            prev = self.prev_theta.get(key)
            args = (Vector(P['pole' + s][:3]), Vector(P['hdir' + s][:3]), Vector(P['hpalm' + s][:3]))
            kw = dict(auto=float(P['auto' + s][0]), twist_split=float(P['split' + s][0]), prev_theta=prev,
                      seg_cost=sc)
            th_fix = None

            def solve(Wv, thv):
                th_ = pb.solve_arm(sl, Wv, *args, theta_override=thv, **kw)
                pb.set_fingers(sl, P['fing' + s].reshape(15, 3))
                return th_

            def hand_loop(Wv, thv, iters=6):
                th_ = solve(Wv, thv)
                for it in range(iters):
                    if not use_contacts:
                        break
                    full = full_pose(pb)
                    Q = self.skin.deform(full, self.hand_sel[sl])
                    sup = support_height(Q, obst) + float(P['lift' + s][0])
                    fin = np.isfinite(sup)
                    under = Wv.z < S.TABLE_TOP - 0.005
                    edge = Q[:, 1] > S.TABLE_NEAR_Y - 0.04
                    ok = fin & ((Q[:, 2] > sup - 0.02) | ~edge) & (not under)
                    dz = 0.0
                    margin = 0.0015
                    if ok.any():
                        gh = float((Q[ok, 2] - sup[ok]).min())
                        if gh < margin:
                            dz = margin - gh
                        elif wt > 0 and gh < 1.0:
                            dz = -wt * (gh - margin)
                    push = Vector()
                    slab = fin & ~ok & edge & (Q[:, 2] > S.TABLE_TOP - S.TABLE_THICK - 0.004)
                    if slab.any():
                        push.y = S.TABLE_NEAR_Y + 0.002 - float(Q[slab, 1].min())
                        self._bump('borde')
                    if tree is not None:
                        Qf = self.skin.deform(full, self.fore_sel[sl])
                        QQ = np.concatenate([Q, Qf])
                        d, nrm, i, fi = self.ck.selfcol.depth(tree, QQ)
                        if d > 0.0004:
                            dirn = self.ck.selfcol.push_dir(full, QQ[i], fi) or nrm
                            push = dirn * (d + 0.0015)
                            self._bump('cuerpo')
                            if getattr(self, 'debug', False):
                                print('PUSH', s, it, round(d * 1000, 1), i < len(Q),
                                      str(self.ck.selfcol.tgt_region[self.ck.selfcol.tgt_p[fi][0]]),
                                      tuple(round(v, 3) for v in QQ[i]), tuple(round(v, 2) for v in dirn),
                                      tuple(round(v, 3) for v in Wv))
                    if getattr(self, 'debug', False):
                        print('DZ', s, it, round(dz, 4), round(float(P['lift' + s][0]), 3), wt,
                              int(ok.sum()), tuple(round(v, 3) for v in Wv))
                    if abs(dz) < 2e-4 and push.length == 0:
                        break
                    Wv = Wv + Vector((0, 0, dz)) + push
                    th_ = solve(Wv, thv)
                return Wv, th_

            W, th = hand_loop(W, None)
            # brazo/antebrazo por encima del riel, paño y fichas paradas: girar el codo (mano fija)
            if use_contacts:
                def arm_clear():
                    full = full_pose(pb)
                    Qa = np.concatenate([self.skin.deform(full, self.fore_sel[sl]),
                                         self.skin.deform(full, self.upper_sel[sl])])
                    sup = support_height(Qa, obst)
                    ok = np.isfinite(sup) & ((Qa[:, 2] > sup - 0.02) | (Qa[:, 1] < S.TABLE_NEAR_Y - 0.04))
                    g = float((Qa[ok, 2] - sup[ok]).min()) if ok.any() else 1.0
                    if tree is not None:
                        d, _, _, _ = self.ck.selfcol.depth(tree, self.skin.deform(full, self.fore_sel[sl]))
                        g = min(g, -d)
                    return g
                g0 = arm_clear()
                if g0 < -0.0004:
                    self._bump('codo')
                    best = (g0, 0.0)
                    for k in (1, -1, 2, -2, 3, -3, 4, -4, 6, -6, 8, -8, 10, -10):
                        cand = th + math.radians(5 * k)
                        solve(W, cand)
                        g = arm_clear()
                        if g >= -0.0004:
                            best = (g, cand)
                            break
                        if g > best[0]:
                            best = (g, cand)
                    th_fix = best[1] if best[1] != 0.0 else th
                    W, th = hand_loop(W, th_fix, iters=3)
            self.prev_theta[key] = th
            pb.diag['arm_' + sl]['contact_dz'] = float((W - Vector(P['arm' + s][:3])).z)
            P['arm' + s] = np.array(W[:])
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


def bake(anim, rig, ev, start=1, post=None):
    """Evalúa todos los cuadros; crea la Action. Devuelve (action, poses, faces).
    post(poses): corrección posterior (p. ej. dedos contra fichas) antes de escribir la Action."""
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
    if post is not None:
        post(poses)
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
            if offset is not None and t.get('roll'):
                f0, f1, theta, Pp = t['roll']
                k = min(1.0, max(0.0, (f - f0) / float(f1 - f0)))
                k = k * k * (3 - 2 * k)
                offset_f = offset @ roll_Q(theta, Pp, k)
            else:
                offset_f = offset
            if attached:
                Mf = hp @ offset_f
                if t.get('flat'):
                    Mf = flat_tile(Mf)
                mats.append(Mf)
            else:
                if rel is not None and f == rel and (offset is not None or (kind == 'table' and t.get('fall'))):
                    Mrel = hp @ offset_f if offset is not None else M.copy()
                    M = flat_tile(Mrel)
                    if t.get('fall') and t.get('land'):
                        seq = land_seq(Mrel, t['land'][0], t['land'][1], t['fall'])
                        M = seq[-1]
                    elif t.get('fall'):
                        seq = fall_seq(Mrel, t['fall'])
                        M = seq[-1]
                if rel is not None and t.get('fall') and rel <= f < rel + t['fall']:
                    mats.append(seq[f - rel].copy())
                    continue
                ns = t.get('settle', 0)
                if rel is not None and ns and rel <= f < rel + ns:
                    k = ((f - rel) / ns) ** 2
                    q = Mrel.to_quaternion().slerp(M.to_quaternion(), k)
                    Mb = q.to_matrix().to_4x4()
                    Mb.translation = Mrel.translation.lerp(M.translation, k)
                    mats.append(Mb)
                else:
                    mats.append(M.copy())
        out[t['name']] = mats
    return out


GRIP_CANON = {}


def fall_seq(Mrel, n):
    """La ficha soltada de pie (algo inclinada hacia delante) cae cara arriba girando sobre su arista inferior
    lejana; n cuadros con aceleración (k^2). Devuelve n+1 matrices (la última, acostada en el paño)."""
    hx, hy, hz = (v / 2 for v in S.TILE)
    R3 = Mrel.to_3x3()
    xa = R3.col[0].normalized()
    piv = Mrel @ Vector((0, -hy, -hz))
    z0 = R3.col[2]
    zp = (z0 - xa * z0.dot(xa)).normalized()
    up = Vector((0, 0, 1))
    up = (up - xa * up.dot(xa)).normalized()
    ang = math.atan2(zp.cross(up).dot(xa), zp.dot(up))
    out = []
    for k in range(n + 1):
        a = ang * (k / n) ** 2
        Rm = Matrix.Translation(piv) @ Matrix.Rotation(a, 4, xa) @ Matrix.Translation(-piv)
        out.append(Rm @ Mrel)
    last = out[-1]
    zs = [(last @ Vector((sx * hx, sy * hy, sz * hz))).z for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]
    dz = S.TABLE_TOP + 0.0003 - min(zs)
    for k in range(1, n + 1):
        out[k].translation.z += dz * (k / n) ** 2
    return out


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


# --------------------------------------------------------------------------------------
# Fichas paradas (de canto, cara hacia el jugador)
# --------------------------------------------------------------------------------------
ROW_Y = -0.38
ROW_X = tuple(round(-0.156 + 0.052 * i, 3) for i in range(7))
STAND_E = 0.013            # yemas a 13 mm del borde superior de la ficha


def stand_rot(tip=0.0, yaw=0.0):
    """Rotación de una ficha parada (Y local arriba, cara +Z hacia +Y del mundo = hacia el jugador).
    tip: grados que se inclina hacia delante (90 = acostada boca arriba, punta lejos del jugador)."""
    base = Matrix(((-1, 0, 0), (0, 0, 1), (0, 1, 0))).transposed()
    return R('Z', yaw) @ R('X', -tip) @ base


def stand_matrix(x, y, z=None, tip=0.0, yaw=0.0):
    M = stand_rot(tip, yaw).to_4x4()
    M.translation = Vector((x, y, S.TABLE_TOP + S.TILE[1] / 2 if z is None else z))
    return M


def rest_on_felt(x, y, tip, yaw=0.0, clear=0.0005):
    """Ficha inclinada 'tip' grados apoyando su arista más baja en el paño, centrada en (x,y)."""
    M = stand_matrix(x, y, 0.0, tip, yaw)
    hx, hy, hz = (v / 2 for v in S.TILE)
    zs = [(M @ Vector((sx * hx, sy * hy, sz * hz))).z for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]
    M.translation.z = S.TABLE_TOP + clear - min(zs)
    return M


def row_tiles(skip=()):
    return [(i, stand_matrix(x, ROW_Y)) for i, x in enumerate(ROW_X) if i not in skip]


def row_obstacles(skip=()):
    hw, ht = S.TILE[0] / 2, S.TILE[2] / 2
    top = S.TABLE_TOP + S.TILE[1]
    return [(x, ROW_Y, 1.0, 0.0, hw, ht, top) for i, x in enumerate(ROW_X) if i not in skip]


_VGRIP = {}


def vgrip_offset(rig, skin, side, alpha, key='pinch_v'):
    """Offset mano->ficha para la pinza fina: pulgar sobre la cara, índice detrás, cerca del borde superior.
    alpha: giro (grados) de la ficha alrededor del eje de la pinza."""
    import vc_hand as H
    s = side
    hb = 'hand_' + s
    if (s, key) not in _VGRIP:
        center, axis, pt, pi = H.grip_local(rig, skin, F[key], s)
        c_h = rig.rest[hb].inverted() @ center
        a_h = (rig.rest3[hb].inverted() @ axis).normalized()
        F0, P0 = rig.hand_ref[s]
        p_h = rig.rest3[hb].inverted() @ P0
        _VGRIP[(s, key)] = (c_h, a_h, p_h)
    c_h, a_h, p_h = _VGRIP[(s, key)]
    z = -a_h
    y0 = -(p_h - a_h * p_h.dot(a_h)).normalized()
    y = (Matrix.Rotation(math.radians(alpha), 3, z) @ y0).normalized()
    x = y.cross(z).normalized()
    T = Matrix((x, y, z)).transposed().to_4x4()
    T.translation = c_h - y * (S.TILE[1] / 2 - STAND_E)
    return T


def hand_for_tile(rig, side, T, off, fingers_key='pinch_v'):
    s = side
    S_ = s.upper()
    HW = T @ off.inverted()
    Rh = HW.to_3x3() @ rig.rest3['hand_' + s].inverted()
    F0, P0 = rig.hand_ref[s]
    return {'arm' + S_: tuple(HW.translation[:]), 'hdir' + S_: tuple((Rh @ F0)[:]),
            'hpalm' + S_: tuple((Rh @ P0)[:]), 'fing' + S_: F[fingers_key], 'table' + S_: 0.0}


def grip_cost(ev, base, side, ch, obst=()):
    S_ = side.upper()
    d = dict(base)
    d.update(ch)
    A = C.Anim('_g', 1)
    A.key(0, d)
    if obst:
        A.obstacles = lambda f: obst
    ev.prev_theta = {}
    pb, _ = ev.evaluate(A, 0)
    dg = pb.diag['arm_' + side]
    cost = (dg['wrist'] / 10) ** 2 + (max(0, dg['reach'] - 0.95) / 0.02) ** 2 + \
        (dg['contact_dz'] / 0.002) ** 2 + (abs(dg['twist']) / 40) ** 2
    info = dict(wrist=round(dg['wrist'], 1), reach=round(dg['reach'], 3), dz=round(dg['contact_dz'], 4),
                twist=round(dg['twist'], 1), elbow=round(dg['elbow'], 1))
    return cost, info, pb


def best_vgrip(ev, side, targets, alphas=range(-20, 61, 5)):
    """targets: lista de (base, T, obst). Elige un único alpha (la ficha no gira en la mano entre animaciones)."""
    best = None
    for a in alphas:
        off = vgrip_offset(ev.rig, ev.skin, side, a)
        tot, infos = 0.0, []
        for base, T, obst in targets:
            c, info, _ = grip_cost(ev, base, side, hand_for_tile(ev.rig, side, T, off), obst)
            tot += c
            infos.append(info)
        if best is None or tot < best[0]:
            best = (tot, a, off, infos)
    return best


def best_place(ev, base, side, x, y, off, tip=78, obst=(), yaws=range(-180, 180, 15)):
    """Orientación final (cara arriba) de la ficha que deja la mano más natural; el extremo sujetado
    queda levantado (tip < 90) y el otro apoyado en el paño."""
    best = None
    for yw in yaws:
        T = rest_on_felt(x, y, tip, yw)
        ch = hand_for_tile(ev.rig, side, T, off)
        c, info, _ = grip_cost(ev, base, side, ch, obst)
        if best is None or c < best[0]:
            best = (c, yw, T, ch, info)
    return best


# --------------------------------------------------------------------------------------
# Cadena del dominó: huecos exactos
# --------------------------------------------------------------------------------------
def chain_matrix(c, u):
    """Ficha acostada cara arriba en el hueco: centro c=(x,y), eje largo (Y local) según u."""
    y = Vector((u[0], u[1], 0)).normalized()
    z = Vector((0, 0, 1))
    x = y.cross(z).normalized()
    M = Matrix((x, y, z)).transposed().to_4x4()
    M.translation = Vector((c[0], c[1], S.TABLE_TOP + S.TILE[2] / 2 + 0.0003))
    return M


def chain_obstacle(c, axis):
    top = S.TABLE_TOP + S.TILE[2]
    hl, hw = S.TILE[1] / 2, S.TILE[0] / 2
    if abs(axis[0]) > 0.5:
        return (c[0], c[1], 1.0, 0.0, hl, hw, top)
    return (c[0], c[1], 1.0, 0.0, hw, hl, top)


def slot_release(c, u, tip=12.0, lift=0.0, n=5):
    """Pose de la ficha parada (inclinada 'tip' hacia u) tal que, al soltarla y caer cara arriba sobre su arista
    inferior, termina EXACTAMENTE en el hueco (centro c, eje largo según u). lift: altura extra de la arista de
    apoyo (si apoya sobre la ficha anterior de la cadena)."""
    yaw = math.degrees(math.atan2(u[0], -u[1]))
    M = rest_on_felt(0.0, 0.0, tip, yaw)
    M.translation.z += lift
    last = fall_seq(M, n)[-1]
    tgt = chain_matrix(c, u)
    M.translation.x += tgt.translation.x - last.translation.x
    M.translation.y += tgt.translation.y - last.translation.y
    return M


def footprint_hits(M, rects, steps=5):
    """¿La base de la ficha parada M pisa alguna ficha acostada? rects: obstáculos chain_obstacle."""
    hx, hy, hz = (v / 2 for v in S.TILE)
    for i in range(steps):
        for j in range(3):
            q = M @ Vector((-hx + 2 * hx * i / (steps - 1), -hy, -hz + hz * j))
            for cx, cy, cs, sn, a, b, top in rects:
                if abs(q.x - cx) < a + 0.001 and abs(q.y - cy) < b + 0.001:
                    return True
    return False


def pinch_local():
    """Punto de la pinza en coordenadas de la ficha (entre las caras, a STAND_E del borde superior)."""
    return Vector((0.0, S.TILE[1] / 2 - STAND_E, 0.0))


def roll_Q(deg, Pp=None, k=1.0):
    """Giro de la ficha entre las yemas (alrededor del eje de la pinza, normal a la cara). Pp: punto de la ficha
    (coordenadas locales) que queda en la pinza al terminar (la ficha se desliza un poco entre los dedos)."""
    P = pinch_local()
    Pk = P if Pp is None else P.lerp(Vector(Pp), k)
    return Matrix.Translation(P) @ Matrix.Rotation(math.radians(deg * k), 4, 'Z') @ Matrix.Translation(-Pk)


def land_grip(rig, off, piv, side='r'):
    """Opciones (mejor primero) de giro y punto de agarre para soltar apaisada: la pinza toma la esquina superior del canto largo (los dedos no
    llegan al paño) y el cuerpo de la ficha queda del lado del pulgar (no atraviesa medio/anular/meñique)."""
    hx, hy, hz = (v / 2 for v in S.TILE)
    sx = 1.0 if piv.x > 0 else -1.0
    theta = -90.0 * sx
    Hr = rig.rest['hand_' + side].inverted()
    pk = Hr @ rig.head['pinky_01_' + side]
    th = Hr @ rig.head['thumb_01_' + side]
    out = []
    for e in (1.0, -1.0):
        Pp = Vector((-sx * (hx - 0.012), e * (hy - 0.020), 0.0))
        c = off @ roll_Q(theta, Pp).translation
        out.append(((c - pk).length - (c - th).length, theta, Pp))
    out.sort(key=lambda x: -x[0])
    return out


def land_release(c, u, tip=12.0, lift=0.0):
    """Ficha de pie sobre su canto LARGO (apaisada), cara hacia el jugador, que al soltarla cae hacia delante
    (lejos del jugador) y queda acostada cara arriba en el hueco (centro c, eje largo según u, u horizontal en X).
    Devuelve (M_suelta, M_final, pivote_local)."""
    hx, hy, hz = (v / 2 for v in S.TILE)
    Mf = chain_matrix(c, u)
    R3 = Mf.to_3x3()
    sx = 1.0 if R3.col[0].y > 0 else -1.0
    piv = Vector((sx * hx, 0.0, -hz))
    p = Mf @ piv
    ax = R3.col[1].normalized()
    best = None
    for sg in (1, -1):
        Rr = Matrix.Translation(p) @ Matrix.Rotation(sg * math.radians(90.0 - tip), 4, ax) @ Matrix.Translation(-p)
        M = Rr @ Mf
        if best is None or M.translation.z > best.translation.z:
            best = M
    best.translation.z += lift
    return best, Mf, piv


def land_seq(Mrel, Mfinal, piv, n):
    """Caída girando sobre el canto largo inferior: de Mrel a Mfinal con aceleración (k^2), pivote fijo."""
    p0, p1 = Mrel @ piv, Mfinal @ piv
    q0, q1 = Mrel.to_quaternion(), Mfinal.to_quaternion()
    out = []
    for k in range(n + 1):
        a = (k / n) ** 2
        R3 = q0.slerp(q1, a).to_matrix()
        M = R3.to_4x4()
        M.translation = p0.lerp(p1, a) - R3 @ piv
        out.append(M)
    out[-1] = Mfinal.copy()
    return out


def standing_hits(M, rects):
    """¿La ficha de pie M (cualquier canto apoyado) pisa alguna ficha acostada de la cadena?"""
    hx, hy, hz = (v / 2 for v in S.TILE)
    low = S.TABLE_TOP + S.TILE[2] + 0.0005
    for sx in (-1, -0.5, 0, 0.5, 1):
        for sy in (-1, -0.5, 0, 0.5, 1):
            for sz in (-1, 1):
                q = M @ Vector((sx * hx, sy * hy, sz * hz))
                if q.z > low:
                    continue
                for cx, cy, cs, sn, a, b, top in rects:
                    if abs(q.x - cx) < a - 0.0005 and abs(q.y - cy) < b - 0.0005:
                        return True
    return False
