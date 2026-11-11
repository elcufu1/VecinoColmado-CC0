"""Construye, hornea y verifica las animaciones de VecinoColmado.

Uso:  blender -b Vecino_Boxer.blend --python build_all.py -- check [Nombre ...]
      (ver final.py para guardar .blend, exportar GLB y renderizar videos/fotos)
"""
import json
import math
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector, Matrix, Quaternion  # noqa: E402

import vc_tools as T  # noqa: E402
import vc_core as C  # noqa: E402
import vc_pose as VP  # noqa: E402
import vc_scene as S  # noqa: E402
import vc_check as K  # noqa: E402
import vc_lib as L  # noqa: E402
import vc_ctx as X  # noqa: E402
import vc_anims as AN  # noqa: E402

CAMS = {
    'mesa': ((-1.10, -1.60, 1.55), (0.0, -0.30, 0.95), 35),
    'mesa_lejos': ((-1.9, -1.45, 1.75), (0.0, -0.45, 0.90), 36),
    'mesa_frente': ((-0.42, -1.85, 1.38), (0.0, -0.05, 1.12), 38),
    'pie': ((-1.7, -2.7, 1.25), (0.0, 0.0, 0.88), 35),
    'lado': ((-2.7, -0.55, 1.15), (0.0, 0.0, 0.78), 35),
}


class Pipeline:
    def __init__(self, engine='WORKBENCH', res=(1280, 720)):
        self.scene, self.rig = T.init(engine, res)
        import vc_limits
        self.rig.limits = vc_limits.Limits(self.rig)
        self.ck = K.Checker(self.rig)
        self.ev = VP.Evaluator(self.rig, self.ck.body, self.ck)
        L.setup(self.rig, self.ev)
        VP.compute_grip(self.rig, self.ck.body, 'r')
        VP.compute_grip(self.rig, self.ck.body, 'l')
        self.ctx = X.Ctx(self.rig, self.ev, self.ck.body)
        self.anims = AN.build(self.ctx)
        self.baked = {}

    # ------------------------------------------------------------------
    def shuffle_tiles(self, A, poses):
        """Fichas boca abajo bajo las palmas (se mueven con la mano, planas) + fichas quietas alrededor."""
        A.tiles = []
        pb0 = poses[0]
        rng = np.random.RandomState(3)
        for s in 'lr':
            Hm = pb0.pose['hand_' + s]
            c = Hm @ Vector((0, 0.05, 0)) if False else None
            # centro de la palma: punto medio entre muñeca y nudillo del medio
            w = pb0.pose['hand_' + s].translation
            k = pb0.pose['middle_01_' + s].translation
            pc = (w + k) / 2
            for i, (dx, dy, yaw) in enumerate(((-0.03, 0.0, 15), (0.028, -0.01, -20))):
                M = VP.tile_matrix(pc.x + dx, pc.y + dy, yaw)
                A.tiles.append(dict(name=f'Ficha_{s}{i}', side=s, start=('hand', Hm.inverted() @ M), flat=True))
        for i in range(8):
            ang = 2 * math.pi * i / 8 + 0.3
            x = 0.30 * math.cos(ang)
            y = -0.58 + 0.20 * math.sin(ang)
            A.tiles.append(dict(name=f'Ficha_mesa{i}', side='r',
                                start=('table', VP.tile_matrix(x, y, rng.uniform(0, 180)))))

    def bake(self, A):
        t0 = time.time()
        real = getattr(self, 'real_off', None)
        if real is not None:
            for t in A.tiles:
                if t['start'][0] == 'hand' and t['start'][1] is self.ctx.OFF:
                    t['start'] = ('hand', real)
        box = {}

        def post(poses):
            if A.props.get('shuffle'):
                self.shuffle_tiles(A, poses)
            box['tiles'] = VP.compute_tiles(A, poses)
            box['fing'] = self.fix_fingers(A, poses, box['tiles'])
        act, poses, faces = VP.bake(A, self.rig, self.ev, post=post)
        tiles = box['tiles']
        if A.name == 'Agarrar_Ficha_Cerca':
            t = A.tiles[0]
            self.real_off = poses[t['grab']].pose['hand_r'].inverted() @ t['start'][1]
        per = []
        for f, pb in enumerate(poses):
            nochair = A.props.get('nochair')
            chair = False if nochair else float(pb.P['chair'][0])
            table = not nochair and not A.props.get('notable')
            tl = [(n, m[f]) for n, m in tiles.items()]
            r, _ = self.ck.check_frame(pb.pose, tiles=tl, chair=chair, table=table)
            for s in 'lr':
                dg = pb.diag['arm_' + s]
                r['_wrist_' + s] = dg['wrist']
                r['_elbow_' + s] = dg['elbow']
                r['_reach_' + s] = dg['reach']
                r['_twist_' + s] = dg['twist']
            per.append(r)
        self.baked[A.name] = dict(act=act, poses=poses, faces=faces, tiles=tiles, per=per, dedos=box.get('fing', {}))
        print(f'BAKE {A.name}: {A.frames + 1} cuadros en {time.time() - t0:.1f}s')
        return self.baked[A.name]

    # ------------------------------------------------------------------ dedos contra fichas
    FINGERS = ('thumb', 'index', 'middle', 'ring', 'pinky')

    def _finger_sel(self):
        if not hasattr(self, '_fsel'):
            self._fsel = {}
            for s in 'lr':
                for fn in self.FINGERS:
                    bones = [f'{fn}_0{k}_{s}' for k in (1, 2, 3)]
                    self._fsel[(s, fn)] = (bones, np.where(self.ck.body.bone_weight(bones) > 0.3)[0])
        return self._fsel

    @staticmethod
    def _tile_depth(Q, mats):
        hx, hy, hz = (v / 2 for v in S.TILE)
        best = 0.0
        for M in mats:
            Mi = np.array(M.inverted())
            L_ = Q @ Mi[:3, :3].T + Mi[:3, 3]
            ins = (np.abs(L_[:, 0]) < hx) & (np.abs(L_[:, 1]) < hy) & (np.abs(L_[:, 2]) < hz)
            if ins.any():
                d = np.minimum(np.minimum(hx - np.abs(L_[ins, 0]), hy - np.abs(L_[ins, 1])), hz - np.abs(L_[ins, 2]))
                best = max(best, float(d.max()))
        return best

    @staticmethod
    def _scaled(q, k):
        if k <= 1.0:
            return Quaternion().slerp(q, k)
        ax, ang = q.to_axis_angle()
        return Quaternion(ax, ang * k)

    def _apply_finger(self, pb, bones, base, k):
        for n, q in zip(bones, base):
            M = self._scaled(q, k).to_matrix().to_4x4()
            M.translation = pb.local[n].translation
            pb.set_local(n, M)

    def fix_fingers(self, A, poses, tiles, tol=0.0002):
        """Dedos que entran en una ficha: mínimo cambio de flexión (abrir o cerrar ese dedo) que lo saca."""
        if not tiles:
            return {}
        sel = self._finger_sel()
        names = list(tiles.keys())
        nf = len(poses)
        steps = [1 - 0.04 * i for i in range(1, 16)] + [1 + 0.04 * i for i in range(1, 9)]
        need = {}
        for f, pb in enumerate(poses):
            mats = [tiles[n][f] for n in names]
            for (s, fn), (bones, vi) in sel.items():
                hand = pb.pose['hand_' + s].translation
                if min((M.translation - hand).length for M in mats) > 0.25:
                    continue
                d0 = self._tile_depth(self.ck.body.deform(pb.pose, vi), mats)
                if d0 <= tol:
                    continue
                base = [pb.local[n].to_quaternion() for n in bones]
                best = None
                for k in sorted(steps, key=lambda k: abs(k - 1)):
                    self._apply_finger(pb, bones, base, k)
                    d = self._tile_depth(self.ck.body.deform(pb.pose, vi), mats)
                    if best is None or d < best[1]:
                        best = (k, d)
                    if d <= tol:
                        break
                self._apply_finger(pb, bones, base, 1.0)
                need[(f, s, fn)] = (best[0], d0, best[1])
        # suavizado temporal: el cambio se mantiene ±2 cuadros y entra/sale gradualmente
        out = {}
        for (s, fn) in sel:
            ks = np.ones(nf)
            for f in range(nf):
                if (f, s, fn) in need:
                    ks[f] = need[(f, s, fn)][0]
            dev = ks - 1.0
            sm = dev.copy()
            for f in range(nf):
                win = dev[max(0, f - 2):f + 3]
                j = int(np.argmax(np.abs(win)))
                w = 1.0 if dev[f] != 0 else 0.6
                sm[f] = win[j] * w if abs(win[j]) > abs(dev[f]) else dev[f]
            if not np.any(sm):
                continue
            bones = sel[(s, fn)][0]
            for f in range(nf):
                if sm[f] == 0:
                    continue
                pb = poses[f]
                base = [pb.local[n].to_quaternion() for n in bones]
                self._apply_finger(pb, bones, base, 1.0 + sm[f])
            out[f'{fn}_{s}'] = dict(cuadros=int((sm != 0).sum()), cambio_max=round(float(np.abs(sm).max()), 2),
                                    prof_antes_mm=round(1000 * max(v[1] for k_, v in need.items()
                                                                  if k_[1] == s and k_[2] == fn), 1))
        if A.loop and nf > 1:
            poses[-1] = poses[0]
        return out

    def report(self, A):
        per = self.baked[A.name]['per']
        out = {}
        sm = K.summarize(per)
        for k, v in sm.items():
            if k.startswith('_'):
                arr = np.array(v, dtype=float)
                if k.startswith('_hueco'):
                    out[k] = dict(min=round(float(arr.min()), 4), max=round(float(arr.max()), 4))
                else:
                    out[k] = dict(max=round(float(np.abs(arr).max()), 1), frame=int(np.argmax(np.abs(arr))))
            else:
                d, reg, frames = v
                out[k] = dict(prof_mm=round(d * 1000, 1), region=reg, cuadros=len(frames),
                              rango=[int(min(frames)), int(max(frames))])
        return out

    # ------------------------------------------------------------------ previsualización
    def ensure_preview(self):
        sc = self.scene
        coll = S.preview_collection(sc)
        if bpy.data.objects.get('Silla') is None:
            emp = bpy.data.objects.new('Silla', None)
            coll.objects.link(emp)
            for ob in list(bpy.data.objects):
                if ob.name.startswith('Silla_'):
                    ob.parent = emp
        self.tile_objs = {}

    def tile_obj(self, name):
        ob = bpy.data.objects.get(name)
        if ob is None:
            ob = S.make_tile(self.scene, name)
        return ob

    def show_frame(self, A, f):
        b = self.baked[A.name]
        pb = b['poses'][f]
        VP.apply_pose_static(pb, self.rig, b['faces'][f])
        nochair = A.props.get('nochair')
        notable = nochair or A.props.get('notable')
        for ob in bpy.data.objects:
            if ob.name.startswith('Mesa'):
                ob.hide_render = bool(notable)
            if ob.name.startswith('Silla'):
                ob.hide_render = bool(nochair)
            if ob.name.startswith('Ficha'):
                ob.hide_render = True
        if not nochair:
            bpy.data.objects['Silla'].location = (0, float(pb.P['chair'][0]), 0)
        for n, mats in b['tiles'].items():
            ob = self.tile_obj(n)
            ob.matrix_world = mats[f]
            ob.hide_render = False
            face_down = n.startswith(('Ficha_mesa', 'Ficha_l', 'Ficha_r'))
            for ch in ob.children:
                ch.hide_render = face_down

    def cam(self, key):
        loc, tgt, lens = CAMS[key]
        return S.add_camera(self.scene, 'Cam_' + key, loc, tgt, lens)

    def thumbs(self, A, out_dir, n=10, cam=None, extra_frames=()):
        os.makedirs(out_dir, exist_ok=True)
        frames = sorted(set([int(round(i * A.frames / (n - 1))) for i in range(n)] + list(extra_frames)))
        c = self.cam(cam or A.props.get('cam', 'mesa'))
        paths = []
        for f in frames:
            self.show_frame(A, f)
            p = os.path.join(out_dir, f'{A.name}_{f:04d}.png')
            T.render_still(self.scene, c, p)
            paths.append((f, p))
        return paths


def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    mode = argv[0] if argv else 'check'
    names = argv[1:]
    P = Pipeline(res=(512, 288))
    P.ensure_preview()
    rep = {}
    for A in P.anims:
        if names and A.name not in names:
            continue
        P.bake(A)
        rep[A.name] = P.report(A)
        print('REPORTE', A.name, json.dumps(rep[A.name], ensure_ascii=False))
        if mode == 'thumbs':
            paths = P.thumbs(A, '/tmp/work/thumbs')
            os.system('python3 /tmp/work/sheet.py /tmp/work/thumbs/sheet_%s.jpg 5 %s' % (
                A.name, ' '.join(f'f{f}={p}' for f, p in paths)))
    with open('/tmp/work/reporte.json', 'w') as fh:
        json.dump(dict(reporte=rep, log=P.ctx.report), fh, ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
