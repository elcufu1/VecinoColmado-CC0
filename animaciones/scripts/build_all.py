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
from mathutils import Vector, Matrix  # noqa: E402

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
        self.ck = K.Checker(self.rig)
        self.ev = VP.Evaluator(self.rig, self.ck.body)
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
        act, poses, faces = VP.bake(A, self.rig, self.ev)
        if A.props.get('shuffle'):
            self.shuffle_tiles(A, poses)
        tiles = VP.compute_tiles(A, poses)
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
        self.baked[A.name] = dict(act=act, poses=poses, faces=faces, tiles=tiles, per=per)
        print(f'BAKE {A.name}: {A.frames + 1} cuadros en {time.time() - t0:.1f}s')
        return self.baked[A.name]

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
