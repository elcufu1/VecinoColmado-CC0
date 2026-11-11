"""Núcleo de animación procedimental para VecinoColmado (Blender 4.5, sin interfaz).

Las poses se describen con canales semánticos (posición de muñeca/tobillo en el
mundo, rotaciones de columna en ejes del mundo, presets de dedos, morfos) que se
interpolan con splines de Hermite (auto-clamped) y se resuelven cuadro a cuadro
con IK analítico de dos huesos. El resultado se hornea como claves por cuadro en
una Action con ranuras (armadura + shape keys de cada malla de la cara).

Ejes del personaje (Blender): Z arriba, mira hacia -Y, su izquierda (_l) en +X.
"""
import math
import bpy
import numpy as np
from mathutils import Matrix, Vector, Quaternion

ARM_NAME = 'VecinoColmado_CC0'
FPS = 24
FACE_MESHES = ['Cuerpo_CC0', 'VecinoColmado_CC0.eyebrow002', 'VecinoColmado_CC0.eyelashes01',
               'VecinoColmado_CC0.low-poly', 'VecinoColmado_CC0.teeth_base', 'VecinoColmado_CC0.tongue01']
FINGERS = ['thumb', 'index', 'middle', 'ring', 'pinky']
FBONES = [f'{f}_0{i}' for f in FINGERS for i in (1, 2, 3)]  # 15 por mano


def vec(*a):
    return Vector(a[0] if len(a) == 1 else a)


def R(axis, deg):
    return Matrix.Rotation(math.radians(deg), 3, axis)


def rot_pyr(p=0.0, y=0.0, r=0.0):
    """Rotación en ejes del mundo: pitch (X, + = inclinar adelante), yaw (Z, + = girar a SU izquierda),
    roll (Y, + = ladear hacia SU izquierda)."""
    return R('Z', y) @ R('X', p) @ R('Y', r)


def frame3(d, h):
    d = d.normalized()
    h = (h - d * d.dot(h)).normalized()
    return Matrix((d, h, d.cross(h))).transposed()


def align(d0, h0, d1, h1):
    return frame3(d1, h1) @ frame3(d0, h0).transposed()


def mirror_v(v):
    return Vector((-v[0], v[1], v[2]))


# --------------------------------------------------------------------------------------
# Splines
# --------------------------------------------------------------------------------------
class Track:
    """Canal con claves (frame, valor, tin, tout). Valores: float o arrays numpy o 'resolvibles'.
    tin/tout: None = automático (catmull-rom con clamp), número = multiplicador de la secante."""

    def __init__(self):
        self.keys = []

    def add(self, t, v, tin=None, tout=None):
        self.keys = [k for k in self.keys if abs(k[0] - t) > 1e-6]
        self.keys.append((float(t), v, tin, tout))
        self.keys.sort(key=lambda k: k[0])


def _as_arr(v):
    return np.atleast_1d(np.asarray(v, dtype=np.float64))


def eval_track(track, t, resolve, period=None):
    keys = track.keys
    n = len(keys)
    if n == 1:
        return resolve(keys[0][1])
    ts = [k[0] for k in keys]
    if period is None:
        if t <= ts[0]:
            return resolve(keys[0][1])
        if t >= ts[-1]:
            return resolve(keys[-1][1])
    # índices con envoltura para bucles
    def key_at(i):
        if period is None:
            return keys[i]
        q, r = divmod(i, n)
        k = keys[r]
        return (k[0] + q * period, k[1], k[2], k[3])
    if period is not None:
        tt = (t - ts[0]) % period + ts[0]
    else:
        tt = t
    i = 0
    while True:
        k1 = key_at(i + 1)
        if k1[0] >= tt or (period is None and i + 1 >= n - 1):
            break
        i += 1
    k0 = key_at(i)
    k1 = key_at(i + 1)
    v0 = _as_arr(resolve(k0[1]))
    v1 = _as_arr(resolve(k1[1]))
    h = k1[0] - k0[0]
    d01 = (v1 - v0) / h

    def tangent(ia, side):
        ka = key_at(ia)
        va = v0 if ia == i else v1
        flag = ka[2] if side == 'in' else ka[3]
        has_prev = period is not None or ia - 1 >= 0
        has_next = period is not None or ia + 1 <= n - 1
        if not has_prev or not has_next:
            if isinstance(flag, (int, float)):
                sec = d01
                return sec * flag
            return np.zeros_like(va)
        kp = key_at(ia - 1)
        kn = key_at(ia + 1)
        vp = v0 if ia - 1 == i else _as_arr(resolve(kp[1]))
        vn = v1 if ia + 1 == i + 1 else _as_arr(resolve(kn[1]))
        dl = (va - vp) / max(ka[0] - kp[0], 1e-6)
        dr = (vn - va) / max(kn[0] - ka[0], 1e-6)
        if isinstance(flag, (int, float)):
            return (dl if side == 'in' else dr) * flag
        m = (vn - vp) / max(kn[0] - kp[0], 1e-6)
        m = np.where(dl * dr <= 0, 0.0, m)
        lim = 3.0 * np.minimum(np.abs(dl), np.abs(dr))
        return np.clip(m, -lim, lim)

    m0 = tangent(i, 'out')
    m1 = tangent(i + 1, 'in')
    s = (tt - k0[0]) / h
    s2, s3 = s * s, s * s * s
    h00 = 2 * s3 - 3 * s2 + 1
    h10 = s3 - 2 * s2 + s
    h01 = -2 * s3 + 3 * s2
    h11 = s3 - s2
    return h00 * v0 + h10 * h * m0 + h01 * v1 + h11 * h * m1


def smooth(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


# --------------------------------------------------------------------------------------
# Rig
# --------------------------------------------------------------------------------------
class Rig:
    def __init__(self):
        self.arm = bpy.data.objects[ARM_NAME]
        bones = self.arm.data.bones
        self.names = []

        def visit(b):
            self.names.append(b.name)
            for c in b.children:
                visit(c)
        for b in bones:
            if b.parent is None:
                visit(b)
        self.idx = {n: i for i, n in enumerate(self.names)}
        self.par = {b.name: (b.parent.name if b.parent else None) for b in bones}
        self.rest = {b.name: b.matrix_local.copy() for b in bones}
        self.rest3 = {n: m.to_3x3() for n, m in self.rest.items()}
        self.rest_rel = {}
        for n in self.names:
            p = self.par[n]
            self.rest_rel[n] = self.rest[p].inverted() @ self.rest[n] if p else self.rest[n].copy()
        self.head = {b.name: b.head_local.copy() for b in bones}
        self.tail = {b.name: b.tail_local.copy() for b in bones}
        self.length = {n: (self.tail[n] - self.head[n]).length for n in self.names}
        # marcos de referencia de la mano en reposo
        self.hand_ref = {}
        for s in 'lr':
            wrist = self.head['hand_' + s]
            F0 = (self.head['middle_01_' + s] - wrist).normalized()
            # normal de la palma = hacia donde se mueve la punta al curvar (+X local)
            acc = Vector()
            for f in ('index', 'middle', 'ring'):
                b = f'{f}_01_{s}'
                axis = self.rest3[b].col[0]
                tip = self.tail[f'{f}_03_{s}'] - self.head[b]
                acc += axis.cross(tip).normalized()
            P0 = (acc - F0 * F0.dot(acc)).normalized()
            self.hand_ref[s] = (F0, P0)
        # bisagras
        self.hinge = {}
        for s in 'lr':
            u0 = (self.tail['upperarm_' + s] - self.head['upperarm_' + s]).normalized()
            f0 = (self.tail['lowerarm_' + s] - self.head['lowerarm_' + s]).normalized()
            self.hinge['arm_' + s] = (u0, f0, u0.cross(f0).normalized())
            t0 = (self.tail['thigh_' + s] - self.head['thigh_' + s]).normalized()
            c0 = (self.tail['calf_' + s] - self.head['calf_' + s]).normalized()
            self.hinge['leg_' + s] = (t0, c0, self.rest3['calf_' + s].col[0].normalized())


class PoseBuilder:
    def __init__(self, rig):
        self.rig = rig
        self.local = {}
        self.pose = {}
        self.diag = {}

    def parent_base(self, n):
        rig = self.rig
        p = rig.par[n]
        P = self.pose[p] if p else Matrix.Identity(4)
        return P @ rig.rest_rel[n]

    def set_local(self, n, M):
        self.local[n] = M
        self.pose[n] = self.parent_base(n) @ M

    def set_world_rot(self, n, R3, offset=None):
        base = self.parent_base(n)
        L = (base.to_3x3().normalized().inverted() @ R3).to_4x4()
        if offset is not None:
            L.translation = base.to_3x3().inverted() @ offset
        self.set_local(n, L)

    def set_delta(self, n, D):
        """Rotación D (ejes del mundo en reposo) aplicada en el marco del padre ya rotado."""
        r3 = self.rig.rest3[n]
        self.set_local(n, (r3.inverted() @ D @ r3).to_4x4())

    def world_rot(self, n):
        return self.pose[n].to_3x3().normalized()

    def head_of(self, n):
        return (self.parent_base(n)).translation if n not in self.pose else self.pose[n].translation

    def finish(self):
        for n in self.rig.names:
            if n not in self.pose:
                self.set_local(n, Matrix.Identity(4))

    def space_point(self, space, p):
        """Convierte un punto expresado 'como si el hueso estuviera en reposo' al mundo actual."""
        if space == 'world':
            return Vector(p)
        b = {'chest': 'spine_03', 'pelvis': 'pelvis', 'head': 'head', 'spine2': 'spine_02'}.get(space, space)
        return self.pose[b] @ self.rig.rest[b].inverted() @ Vector(p)

    def space_dir(self, space, d):
        if space == 'world':
            return Vector(d)
        b = {'chest': 'spine_03', 'pelvis': 'pelvis', 'head': 'head', 'spine2': 'spine_02'}.get(space, space)
        return self.world_rot(b) @ self.rig.rest3[b].inverted() @ Vector(d)

    # ---------------- IK de brazo -----------------
    def solve_arm(self, s, W, pole, hdir, hpalm, auto=0.0, twist_split=0.5, prev_theta=None, seg_cost=None):
        rig = self.rig
        up, lo, ha = 'upperarm_' + s, 'lowerarm_' + s, 'hand_' + s
        S = self.parent_base(up).translation
        L1, L2 = rig.length[up], rig.length[lo]
        ax = W - S
        D = ax.length
        reach = D / (L1 + L2)
        D = min(max(D, abs(L1 - L2) + 1e-3), (L1 + L2) * 0.9985)
        ax.normalize()
        Wc = S + ax * D
        a = (L1 * L1 - L2 * L2 + D * D) / (2 * D)
        h = math.sqrt(max(L1 * L1 - a * a, 0.0))
        pole = Vector(pole)
        pp = pole - ax * ax.dot(pole)
        if pp.length < 1e-6:
            pp = Vector((0, 0, -1)) - ax * ax.dot(Vector((0, 0, -1)))
        pp.normalize()
        e2 = ax.cross(pp)
        u0, f0, n0 = rig.hinge['arm_' + s]
        F0, P0 = rig.hand_ref[s]
        Rh = align(F0, P0, Vector(hdir), Vector(hpalm))
        hand_world = Rh @ rig.rest3[ha]

        def build(theta):
            dirp = pp * math.cos(theta) + e2 * math.sin(theta)
            E = S + ax * a + dirp * h
            d1 = (E - S).normalized()
            d2 = (Wc - E).normalized()
            n = dirp.cross(ax).normalized()
            Ru = align(u0, n0, d1, n)
            Rl = align(f0, n0, d2, n)
            Q = (Rh @ Rl.inverted()).to_quaternion()
            pr = Vector((Q.x, Q.y, Q.z)).dot(d2)
            tw = Quaternion((Q.w, *(d2 * pr)))
            if tw.magnitude < 1e-9:
                tw = Quaternion()
            tw.normalize()
            sw = Q @ tw.inverted()
            twa = 2 * math.atan2(pr, Q.w)
            if twa > math.pi:
                twa -= 2 * math.pi
            if twa < -math.pi:
                twa += 2 * math.pi
            return Ru, Rl, d2, sw.angle, twa, E

        def build_E(theta):
            dirp = pp * math.cos(theta) + e2 * math.sin(theta)
            return S + ax * a + dirp * h

        theta = 0.0
        if auto > 0:
            best = None
            for k in range(-36, 37):
                th = math.radians(k * 2.5)
                _, _, _, swa, twa, _ = build(th)
                c = swa * swa + 0.15 * twa * twa + auto * th * th
                if seg_cost is not None:
                    c += seg_cost(S, build_E(th), Wc)
                if prev_theta is not None:
                    c += 2.0 * (th - prev_theta) ** 2
                if best is None or c < best[0]:
                    best = (c, th)
            theta = best[1]
        Ru, Rl, d2, swa, twa, E = build(theta)
        self.set_world_rot(up, Ru @ rig.rest3[up])
        Rtw = Matrix.Rotation(twa * twist_split, 3, d2)
        self.set_world_rot(lo, Rtw @ Rl @ rig.rest3[lo])
        self.set_world_rot(ha, hand_world)
        elbow = math.degrees(math.acos(max(-1, min(1, (E - S).normalized().dot((Wc - E).normalized())))))
        self.diag['arm_' + s] = dict(reach=reach, wrist=math.degrees(swa), twist=math.degrees(twa), elbow=elbow,
                                     theta=theta, E=E.copy(), S=S.copy())
        return theta

    # ---------------- IK de pierna -----------------
    def solve_leg(self, s, A, pole, Dfoot, toe_pitch=0.0, toe_yaw=0.0):
        rig = self.rig
        th, ca, fo, ba = 'thigh_' + s, 'calf_' + s, 'foot_' + s, 'ball_' + s
        H = self.parent_base(th).translation
        L1, L2 = rig.length[th], rig.length[ca]
        ax = A - H
        D = ax.length
        reach = D / (L1 + L2)
        D = min(max(D, abs(L1 - L2) + 1e-3), (L1 + L2) * 0.9995)
        ax.normalize()
        Ac = H + ax * D
        a = (L1 * L1 - L2 * L2 + D * D) / (2 * D)
        h = math.sqrt(max(L1 * L1 - a * a, 0.0))
        pole = Vector(pole)
        pp = (pole - ax * ax.dot(pole)).normalized()
        E = H + ax * a + pp * h
        d1 = (E - H).normalized()
        d2 = (Ac - E).normalized()
        n = pp.cross(ax).normalized()
        t0, c0, n0 = rig.hinge['leg_' + s]
        self.set_world_rot(th, align(t0, n0, d1, n) @ rig.rest3[th])
        self.set_world_rot(ca, align(c0, n0, d2, n) @ rig.rest3[ca])
        self.set_world_rot(fo, Dfoot @ rig.rest3[fo])
        yaw_only = R('Z', toe_yaw)
        self.set_world_rot(ba, yaw_only @ R('X', toe_pitch) @ rig.rest3[ba])
        knee = math.degrees(math.acos(max(-1, min(1, d1.dot(d2)))))
        self.diag['leg_' + s] = dict(reach=reach, knee=knee)

    # ---------------- dedos -----------------
    def set_fingers(self, s, arr):
        """arr: (15,3) grados (curl X, giro Y, abducción Z) en semántica de mano IZQUIERDA."""
        sg = np.array([1.0, -1.0, -1.0]) if s == 'r' else np.array([1.0, 1.0, 1.0])
        for i, b in enumerate(FBONES):
            x, y, z = (np.asarray(arr[i]) * sg)
            q = (R('Z', z) @ R('X', x) @ R('Y', y)) if True else None
            self.set_local(f'{b}_{s}', q.to_4x4())


# --------------------------------------------------------------------------------------
# Skinning en numpy (para detectar penetraciones)
# --------------------------------------------------------------------------------------
class Skinner:
    def __init__(self, rig, obj_name, max_inf=6):
        self.rig = rig
        ob = bpy.data.objects[obj_name]
        me = ob.data
        n = len(me.vertices)
        co = np.empty(n * 3)
        me.vertices.foreach_get('co', co)
        self.co = co.reshape(n, 3)
        gname = {g.index: g.name for g in ob.vertex_groups}
        idx = np.zeros((n, max_inf), dtype=np.int32)
        w = np.zeros((n, max_inf))
        for v in me.vertices:
            infl = [(rig.idx[gname[g.group]], g.weight) for g in v.groups
                    if g.group in gname and gname[g.group] in rig.idx and g.weight > 0]
            infl.sort(key=lambda x: -x[1])
            infl = infl[:max_inf]
            tot = sum(x[1] for x in infl)
            for k, (bi, wt) in enumerate(infl):
                idx[v.index, k] = bi
                w[v.index, k] = wt / tot if tot > 0 else 0
        self.idx, self.w = idx, w
        self.inv_rest = np.array([np.array(rig.rest[nm].inverted()) for nm in rig.names])
        self.co_h = np.concatenate([self.co, np.ones((n, 1))], 1)

    def bone_weight(self, bone_names):
        ids = [self.rig.idx[b] for b in bone_names]
        return (np.isin(self.idx, ids) * self.w).sum(1)

    def deform(self, pose, sel=None):
        rig = self.rig
        M = np.array([np.array(pose[nm]) for nm in rig.names]) @ self.inv_rest  # (B,4,4)
        idx = self.idx if sel is None else self.idx[sel]
        w = self.w if sel is None else self.w[sel]
        co = self.co_h if sel is None else self.co_h[sel]
        Mv = M[idx][:, :, :3, :]  # (n,k,3,4)
        out = np.einsum('nkij,nj->nki', Mv, co)
        return (out * w[:, :, None]).sum(1)


# --------------------------------------------------------------------------------------
# Acción
# --------------------------------------------------------------------------------------
class Anim:
    def __init__(self, name, frames, loop=False, desc=''):
        self.name = name
        self.frames = frames  # número de intervalos; frames 0..frames
        self.loop = loop
        self.desc = desc
        self.tracks = {}
        self.procs = []
        self.tiles = []  # instrucciones de fichas (solo previsualización)
        self.markers = []
        self.props = {}

    def key(self, t, d=None, tin=None, tout=None, **kw):
        d = dict(d or {})
        d.update(kw)
        for ch, v in d.items():
            self.tracks.setdefault(ch, Track()).add(t, v, tin, tout)
        return self

    def proc(self, fn):
        self.procs.append(fn)
        return fn

    def mark(self, t, name):
        self.markers.append((t, name))
