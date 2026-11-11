"""Chequeo numérico de penetraciones cuadro a cuadro (skinning LBS idéntico al modificador Armature)."""
import numpy as np
import bpy
from mathutils import Vector, Matrix
from mathutils.kdtree import KDTree

import vc_core as C
import vc_scene as S


def box(name, cx, cy, cz, sx, sy, sz):
    return (name, np.array([cx - sx / 2, cy - sy / 2, cz - sz / 2]), np.array([cx + sx / 2, cy + sy / 2, cz + sz / 2]))


def table_boxes():
    T = S
    rh = T.RAIL_TOP - (T.TABLE_TOP - T.TABLE_THICK)
    rz = (T.RAIL_TOP + T.TABLE_TOP - T.TABLE_THICK) / 2
    return [
        box('mesa_pano', 0, T.TABLE_CY, T.TABLE_TOP - T.TABLE_THICK / 2, T.TABLE_SIZE, T.TABLE_SIZE, T.TABLE_THICK),
        box('riel_cerca', 0, T.TABLE_NEAR_Y - T.RAIL_W / 2, rz, T.TABLE_SIZE, T.RAIL_W, rh),
        box('riel_izq', T.TABLE_SIZE / 2 - T.RAIL_W / 2, T.TABLE_CY, rz, T.RAIL_W, T.TABLE_SIZE, rh),
        box('riel_der', -T.TABLE_SIZE / 2 + T.RAIL_W / 2, T.TABLE_CY, rz, T.RAIL_W, T.TABLE_SIZE, rh),
    ]


def chair_boxes(dy=0.0):
    T = S
    return [
        box('silla_asiento', 0, T.SEAT_CY + dy, T.SEAT_Z - T.SEAT_THICK / 2, T.SEAT_W, T.SEAT_D, T.SEAT_THICK),
        box('silla_respaldo', 0, T.BACK_Y + 0.015 + dy, T.SEAT_Z + 0.25, T.SEAT_W, 0.03, 0.42),
    ]


def depth_in_box(P, lo, hi, tol=0.0):
    inside = np.all((P > lo + tol) & (P < hi - tol), axis=1)
    if not inside.any():
        return inside, np.zeros(0)
    Q = P[inside]
    d = np.minimum(Q - lo, hi - Q).min(1)
    return inside, d


REGIONS = {
    'mano_dedos': ['hand', 'thumb', 'index', 'middle', 'ring', 'pinky'],
    'antebrazo': ['lowerarm'],
    'brazo': ['upperarm', 'clavicle'],
    'muslo': ['thigh'],
    'pierna': ['calf'],
    'pie': ['foot', 'ball'],
    'tronco': ['pelvis', 'spine'],
    'cabeza': ['neck', 'head'],
}


class Checker:
    def __init__(self, rig):
        self.rig = rig
        self.body = C.Skinner(rig, 'Cuerpo_CC0')
        self.boxer = C.Skinner(rig, 'Boxer_CC0')
        # región dominante por vértice
        dom = self.body.idx[np.arange(len(self.body.idx)), np.argmax(self.body.w, 1)]
        names = rig.names
        self.region = np.array(['otro'] * len(dom), dtype=object)
        self.bone = np.array([names[i] for i in dom], dtype=object)
        for reg, pref in REGIONS.items():
            ids = [i for i, n in enumerate(names) if n.split('_')[0] in pref]
            self.region[np.isin(dom, ids)] = reg
        # correspondencias bóxer <-> cuerpo
        bx = bpy.data.objects['Boxer_CC0'].data
        nb = len(bx.vertices)
        bn = np.empty(nb * 3)
        bx.vertices.foreach_get('normal', bn)
        self.bnorm = bn.reshape(nb, 3)
        # bordes abiertos del bóxer
        edge_count = {}
        for p in bx.polygons:
            vs = list(p.vertices)
            for i in range(len(vs)):
                e = tuple(sorted((vs[i], vs[(i + 1) % len(vs)])))
                edge_count[e] = edge_count.get(e, 0) + 1
        border = set()
        for e, c in edge_count.items():
            if c == 1:
                border.update(e)
        self.bborder = np.zeros(nb, bool)
        self.bborder[list(border)] = True
        kd = KDTree(nb)
        for i, co in enumerate(self.boxer.co):
            kd.insert(co, i)
        kd.balance()
        near, sgn = [], []
        for vi, co in enumerate(self.body.co):
            if co[2] < 0.6 or co[2] > 1.05:
                continue
            p, j, d = kd.find(co)
            if d > 0.03 or self.bborder[j]:
                continue
            s = np.dot(co - self.boxer.co[j], self.bnorm[j])
            if s < -0.002:
                # descartar vértices cerca del borde (dobladillo)
                near.append((vi, j))
        self.cover = np.array(near, dtype=np.int64)

    def check_frame(self, pose, extra_boxes=(), tiles=(), chair=False, table=False, floor=True):
        res = {}
        P = self.body.deform(pose)
        boxes = []
        if table:
            boxes += table_boxes()
        if chair is not False and chair is not None:
            dy = 0.0 if chair is True else float(chair)
            boxes += chair_boxes(dy)
            T = S
            m = (np.abs(P[:, 0]) < T.SEAT_W / 2) & (np.abs(P[:, 1] - T.SEAT_CY - dy) < T.SEAT_D / 2)
            if m.any():
                res['_hueco_asiento'] = float(P[m, 2].min() - T.SEAT_Z)
        boxes += list(extra_boxes)
        for name, lo, hi in boxes:
            ins, d = depth_in_box(P, lo, hi, 0.0005)
            if d.size:
                regs = self.region[ins]
                k = int(np.argmax(d))
                res[name] = (float(d.max()), str(regs[k]), int(ins.sum()))
        if floor:
            mz = P[:, 2].min()
            if mz < -0.004:
                res['suelo'] = (float(-mz), str(self.region[np.argmin(P[:, 2])]), int((P[:, 2] < -0.004).sum()))
        for tname, M in tiles:
            Mi = np.array(M.inverted())
            Q = P @ Mi[:3, :3].T + Mi[:3, 3]
            half = np.array(S.TILE) / 2
            ins, d = depth_in_box(Q, -half, half, 0.0005)
            if d.size:
                regs = self.bone[ins]
                k = int(np.argmax(d))
                res['ficha:' + tname] = (float(d.max()), str(regs[k]), int(ins.sum()))
        # bóxer
        if len(self.cover):
            B = self.boxer.deform(pose)
            vi, bj = self.cover[:, 0], self.cover[:, 1]
            # normal deformada aproximada: rotación de la matriz de skin del vértice del bóxer
            rig = self.rig
            M = np.array([np.array(pose[nm]) for nm in rig.names]) @ self.boxer.inv_rest
            Mv = M[self.boxer.idx[bj]][:, :, :3, :3]
            nrm = np.einsum('nkij,nj->nki', Mv, self.bnorm[bj])
            nrm = (nrm * self.boxer.w[bj][:, :, None]).sum(1)
            nrm /= np.linalg.norm(nrm, axis=1)[:, None] + 1e-9
            s = ((P[vi] - B[bj]) * nrm).sum(1)
            if s.max() > 0.001:
                res['boxer'] = (float(s.max()), str(self.region[vi[np.argmax(s)]]), int((s > 0.001).sum()))
        return res, P


def summarize(per_frame):
    """per_frame: lista de dicts -> resumen {colisión: (max_depth, region, frames)}"""
    out = {}
    for f, r in enumerate(per_frame):
        for k, v in r.items():
            if k.startswith('_'):
                out.setdefault(k, []).append(v)
                continue
            d, reg, n = v
            if k not in out:
                out[k] = [d, reg, [f]]
            else:
                if d > out[k][0]:
                    out[k][0], out[k][1] = d, reg
                out[k][2].append(f)
    return out
