"""Cálculo de yemas, optimización de la pinza pulgar-índice y marco de agarre de la ficha."""
import math
import numpy as np
from mathutils import Matrix, Vector

import vc_core as C


def nelder_mead(f, x0, step, iters=1500, tol=1e-9):
    n = len(x0)
    pts = [np.array(x0, float)]
    for i in range(n):
        p = np.array(x0, float)
        p[i] += step[i]
        pts.append(p)
    vals = [f(p) for p in pts]
    for _ in range(iters):
        order = np.argsort(vals)
        pts = [pts[i] for i in order]
        vals = [vals[i] for i in order]
        if abs(vals[-1] - vals[0]) < tol:
            break
        c = np.mean(pts[:-1], axis=0)
        xr = c + (c - pts[-1])
        fr = f(xr)
        if fr < vals[0]:
            xe = c + 2 * (c - pts[-1])
            fe = f(xe)
            if fe < fr:
                pts[-1], vals[-1] = xe, fe
            else:
                pts[-1], vals[-1] = xr, fr
        elif fr < vals[-2]:
            pts[-1], vals[-1] = xr, fr
        else:
            xc = c + 0.5 * (pts[-1] - c)
            fc = f(xc)
            if fc < vals[-1]:
                pts[-1], vals[-1] = xc, fc
            else:
                for i in range(1, len(pts)):
                    pts[i] = pts[0] + 0.5 * (pts[i] - pts[0])
                    vals[i] = f(pts[i])
    i = int(np.argmin(vals))
    return pts[i], vals[i]


class HandModel:
    """Yemas de pulgar e índice (vértices de la piel) para la mano s."""

    def __init__(self, rig, skin, s='r'):
        self.rig, self.skin, self.s = rig, skin, s
        self.pads = {}
        for f in ('thumb', 'index', 'middle'):
            b = f'{f}_03_{s}'
            w = skin.bone_weight([b])
            sel = np.where(w > 0.6)[0]
            head, tail = rig.head[b], rig.tail[b]
            axis_x = rig.rest3[b].col[0]
            d = (tail - head).normalized()
            nrm = axis_x.cross(d).normalized()  # hacia donde va la punta al flexionar = lado palmar
            pts = skin.co[sel]
            rel = pts - np.array(head[:])
            along = rel @ np.array(d[:])
            out = rel @ np.array(nrm[:])
            L = (tail - head).length
            cand = sel[(along > 0.60 * L) & (along < 1.0 * L)]
            sc = (skin.co[cand] - np.array(head[:])) @ np.array(nrm[:])
            top = cand[np.argsort(-sc)[:6]]
            self.pads[f] = (top, b, nrm)

    def pad_world(self, pose, f):
        top, b, nrm = self.pads[f]
        p = self.skin.deform(pose, top).mean(0)
        R = (pose[b].to_3x3() @ self.rig.rest3[b].inverted())
        return Vector(p), (R @ nrm).normalized()


def optimize_pinch(rig, skin, base_arr, gap, s='r', x0=None):
    """Optimiza pulgar (01 xyz, 02 x, 03 x) e índice (01 x, 01 z, 02 x, 03 x) para que las yemas
    queden enfrentadas a 'gap' metros."""
    hm = HandModel(rig, skin, s)

    def make(x):
        arr = base_arr.copy()
        arr[0] = (x[0], x[1], x[2])
        arr[1] = (x[3], 0, 0)
        arr[2] = (x[4], 0, 0)
        arr[3] = (x[5], 0, x[6])
        arr[4] = (x[7], 0, 0)
        arr[5] = (x[8], 0, 0)
        return arr

    def pose_of(arr):
        pb = C.PoseBuilder(rig)
        for n in rig.names:
            if n.split('_')[0] in C.FINGERS:
                continue
            pb.set_local(n, Matrix.Identity(4))
        pb.set_fingers(s, arr)
        pb.set_fingers('l' if s == 'r' else 'r', arr)
        pb.finish()
        return pb.pose

    def cost(x):
        arr = make(x)
        pose = pose_of(arr)
        pt, nt = hm.pad_world(pose, 'thumb')
        pi, ni = hm.pad_world(pose, 'index')
        d = pi - pt
        dist = d.length
        u = d / max(dist, 1e-6)
        c = ((dist - gap) / 0.004) ** 2
        c += 4 * (1 - nt.dot(u)) ** 2 * 25 + 4 * (1 + ni.dot(u)) ** 2 * 25
        # preferencias naturales
        c += 0.0004 * (x[1] ** 2) + 0.0002 * ((x[3] - 15) ** 2 + (x[4] - 15) ** 2)
        c += 0.0002 * ((x[5] - 30) ** 2 + (x[7] - 25) ** 2 + (x[8] - 15) ** 2) + 0.001 * x[6] ** 2
        for v, lo, hi in ((x[0], -20, 40), (x[1], -30, 30), (x[2], -30, 45), (x[3], 0, 40), (x[4], 8, 40),
                          (x[5], 0, 60), (x[6], -10, 10), (x[7], 18, 60), (x[8], 12, 40)):
            if v < lo:
                c += ((lo - v) / 3) ** 2
            if v > hi:
                c += ((v - hi) / 3) ** 2
        return c

    if x0 is None:
        x0 = [15, 0, 15, 15, 15, 30, 0, 25, 15]
    best = None
    for start in (x0, [30, -10, 30, 10, 10, 25, 0, 20, 10], [5, 10, 0, 20, 20, 35, 0, 30, 20],
                  [20, 15, 35, 25, 25, 40, 0, 40, 20], [0, -15, 20, 5, 20, 20, 0, 20, 30]):
        x, v = nelder_mead(cost, start, [10] * 9, iters=2500)
        x, v = nelder_mead(cost, x, [3] * 9, iters=2500)
        if best is None or v < best[1]:
            best = (x, v)
    x, v = best
    arr = make(x)
    pose = pose_of(arr)
    pt, nt = hm.pad_world(pose, 'thumb')
    pi, ni = hm.pad_world(pose, 'index')
    info = dict(cost=v, dist=(pi - pt).length, face_t=nt.dot((pi - pt).normalized()),
                face_i=-ni.dot((pi - pt).normalized()), x=[round(float(a), 1) for a in x])
    return arr, info


def grip_local(rig, skin, arr, s='r'):
    """Centro y eje de la pinza en coordenadas relativas a la mano en reposo (mundo de reposo)."""
    hm = HandModel(rig, skin, s)
    pb = C.PoseBuilder(rig)
    for n in rig.names:
        if n.split('_')[0] in C.FINGERS:
            continue
        pb.set_local(n, Matrix.Identity(4))
    pb.set_fingers(s, arr)
    pb.set_fingers('l' if s == 'r' else 'r', arr)
    pb.finish()
    pt, _ = hm.pad_world(pb.pose, 'thumb')
    pi, _ = hm.pad_world(pb.pose, 'index')
    return (pt + pi) / 2, (pi - pt), pt, pi


def hand_frame_for_grip(rig, s, axis_rest, fdir_desired, palm_hint):
    """Orientación de la mano (dir, palma) tal que el eje de pinza quede horizontal y la dirección de los
    dedos sea lo más cercana posible a fdir_desired."""
    F0, P0 = rig.hand_ref[s]
    fd = Vector(fdir_desired).normalized()
    best = None
    for k in range(0, 360, 2):
        # palma candidata girando alrededor de fd
        base = Vector(palm_hint)
        base = (base - fd * fd.dot(base)).normalized()
        pc = Matrix.Rotation(math.radians(k), 3, fd) @ base
        Rh = C.align(F0, P0, fd, pc)
        a = Rh @ axis_rest
        c = abs(a.normalized().z) + 0.002 * min(k, 360 - k)
        if best is None or c < best[0]:
            best = (c, pc, Rh)
    return fd, best[1], best[2]
