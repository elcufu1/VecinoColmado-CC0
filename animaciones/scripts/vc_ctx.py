"""Contexto de construcción: caminar, sentarse/levantarse, sostener fichas y prueba de rango."""
import math
import numpy as np
from mathutils import Vector, Matrix

import vc_core as C
import vc_pose as VP
import vc_lib as L
import vc_scene as S
import vc_hand as H
from vc_core import rot_pyr, R

F = VP.F


def sstep(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


class Ctx:
    def __init__(self, rig, ev, skin):
        self.rig, self.ev, self.skin = rig, ev, skin
        self.report = {}
        self._foot_geom()

    def log(self, name, what, info):
        self.report.setdefault(name, {})[what] = {k: round(float(v), 3) for k, v in info.items()}
        print('LOG', name, what, self.report[name][what])

    # ------------------------------------------------------------------ pies
    def _foot_geom(self):
        rig, sk = self.rig, self.skin
        self.foot = {}
        for s in 'lr':
            A = rig.head['foot_' + s].copy()
            B = rig.head['ball_' + s].copy()
            w = sk.bone_weight(['foot_' + s, 'ball_' + s])
            P = sk.co[w > 0.3]
            sole = P[:, 2].min()
            back = P[P[:, 2] < sole + 0.03]
            heel = Vector((A.x, float(back[:, 1].max()) - 0.012, float(sole)))
            ball = Vector((B.x, B.y, float(sole)))
            self.foot[s] = dict(A=A, heel=heel - A, ball=ball - A, sole=float(sole))
        print('PIE', {s: (tuple(round(v, 3) for v in self.foot[s]['A']), tuple(round(v, 3) for v in self.foot[s]['heel']),
                          tuple(round(v, 3) for v in self.foot[s]['ball'])) for s in 'lr'})

    def ankle_for(self, s, contact, pitch, pivot):
        """Posición del tobillo para que el punto 'pivot' (heel/ball) quede en 'contact' con el pie inclinado."""
        g = self.foot[s]
        off = g[pivot]
        return contact - R('X', pitch) @ off

    # ------------------------------------------------------------------ caminar
    def walk(self, A):
        rig = self.rig
        N = A.frames
        v = 0.83 / 24.0
        stance = 0.58
        span = v * stance * N
        y0 = -span / 2
        lift = 0.075

        def foot_state(s, ph):
            g = self.foot[s]
            x = g['A'].x
            dh = g['ball'].y - g['heel'].y  # (negativo: la bola está delante)
            if ph < stance:
                yc = y0 + v * ph * N  # punto del talón en el suelo (se desliza hacia atrás)
                if ph < 0.09:
                    p = -15 * (1 - sstep(ph / 0.09))
                    return self.ankle_for(s, Vector((x, yc, g['sole'])), p, 'heel'), p, p
                if ph < 0.40:
                    return self.ankle_for(s, Vector((x, yc, g['sole'])), 0.0, 'heel'), 0.0, 0.0
                p = 42 * sstep((ph - 0.40) / (stance - 0.40)) ** 1.2
                bc = Vector((x, yc + dh, g['sole']))
                return self.ankle_for(s, bc, p, 'ball'), p, 0.0
            u = (ph - stance) / (1 - stance)
            a0, p0, _ = foot_state(s, stance - 1e-6)
            a1, p1, _ = foot_state(s, 0.0)
            e = sstep(u)
            pos = a0.lerp(a1, e)
            pos.z += lift * math.sin(math.pi * min(1, u * 1.15)) ** 1.3
            if u < 0.45:
                p = p0 + (5 - p0) * sstep(u / 0.45)
            else:
                p = 5 + (p1 - 5) * sstep((u - 0.45) / 0.55)
            toe = p * sstep(u / 0.35)
            return pos, p, toe

        self._foot_state = foot_state
        ST = L.stand()
        A.key(0, ST, **VP.neutral_face())
        hip_j = {s: rig.head['thigh_' + s].copy() for s in 'lr'}
        Ltot = {s: rig.length['thigh_' + s] + rig.length['calf_' + s] for s in 'lr'}
        for f in range(N):
            ph = f / N
            pl = ph
            pr = (ph + 0.5) % 1.0
            aL, pL, tL = foot_state('l', pl)
            aR, pR, tR = foot_state('r', pr)
            c2 = math.cos(4 * math.pi * ph)
            sway = 0.018 * math.sin(2 * math.pi * (ph - 0.12))
            hz = -0.022 - 0.012 * c2
            # limitar extensión de la pierna
            for s, a in (('l', aL), ('r', aR)):
                hj = hip_j[s] + Vector((sway, 0, hz))
                d = (a - hj)
                lim = Ltot[s] * 0.985
                if d.length > lim:
                    dz = math.sqrt(max(lim * lim - d.x * d.x - d.y * d.y, 0)) - (hj.z - a.z)
                    hz += dz
            yaw = -5 * math.cos(2 * math.pi * ph)
            roll = -3.5 * math.sin(2 * math.pi * ph)
            A.key(f, footL=tuple(aL[:]), footR=tuple(aR[:]), frotL=(pL, 0, 0), frotR=(pR, 0, 0), toeL=tL, toeR=tR,
                  hips=(sway, 0.0, hz), hips_rot=(4, yaw, roll), spine=(3, -yaw * 1.4, -roll * 0.6),
                  head=(-1 + 1.5 * c2, -yaw * 0.4, 0), neck=(0, 0, -roll * 0.3))
            # brazos: oposición a las piernas (pierna izquierda adelante en f0 -> brazo derecho adelante)
            sw = math.cos(2 * math.pi * ph)
            for s, sg, k in (('R', -1, sw), ('L', 1, -sw)):
                fw = max(k, 0)
                bw = max(-k, 0)
                arm = (sg * (0.225 - 0.03 * fw), -0.03 - 0.15 * fw + 0.11 * bw, 0.93 + 0.05 * fw + 0.015 * bw)
                elb = (sg * 0.25, 0.03 - 0.035 * fw + 0.06 * bw, 1.19 + 0.01 * bw)
                A.key(f, **{'arm' + s: ('chest', arm), 'elbow' + s: ('chest', elb),
                            'hdir' + s: ('chest', (sg * -0.08, -0.15 - 0.35 * fw + 0.15 * bw, -1)),
                            'clav' + s: (0, 3 * k)})
        A.key(0, fingL=F['relax'], fingR=F['relax'])
        A.proc(VP.blink_proc([18]))
        A.props['cam'] = 'pie'
        A.props['nochair'] = True
        A.props['walk_speed'] = 0.83

    # ------------------------------------------------------------------ sentarse
    def seat_hands(self, dy):
        y = S.SEAT_CY + dy - S.SEAT_D / 2 + 0.05
        z = S.SEAT_Z + 0.03
        x = S.SEAT_W / 2 + 0.078
        fg = VP.finger_mix(('flat', 0.6), ('relax', 0.4))
        return (dict(armR=(-x, y, z), hdirR=(0.05, -0.30, -1), hpalmR=(0.95, 0, 0.0), fingR=fg,
                     elbowR=(-0.29, y + 0.10, z + 0.25), tableR=0.0),
                dict(armL=(x, y, z), hdirL=(-0.05, -0.30, -1), hpalmL=(-0.95, 0, 0.0), fingL=fg,
                     elbowL=(0.29, y + 0.10, z + 0.25), tableL=0.0))

    def sit(self, A, SB, ST):
        dyo = S.SEAT_CY_OUT - S.SEAT_CY
        hy_out = SB['hips'][1] + dyo
        fl0, fr0 = ST['footL'], ST['footR']
        A.key(0, ST, chair=dyo, **VP.neutral_face(), eyes=(0, 0))
        A.key(8, head=(14, 18, 0), neck=(4, 8, 0), eyes=(15, 12))
        A.key(16, head=(4, 0, 0), neck=(0, 0, 0), eyes=(0, 6), hips=(0, 0.01, -0.01), spine=(4, 0, 0))
        A.key(26, hips=(0, 0.10, -0.17), hips_rot=(18, 0, 0), spine=(30, 0, 0), head=(-14, 0, 0), neck=(-8, 0, 0),
              armR=(-0.21, -0.33, 0.84), armL=(0.21, -0.33, 0.84),
              elbowR=(-0.29, -0.08, 0.96), elbowL=(0.29, -0.08, 0.96),
              hdirR=(0.1, -1, -0.3), hdirL=(-0.1, -1, -0.3),
              hpalmR=(0.5, 0, -1), hpalmL=(-0.5, 0, -1), fingR=F['relax'], fingL=F['relax'])
        A.key(34, hips=(0, hy_out - 0.02, -0.37), hips_rot=(14, 0, 0), spine=(30, 0, 0))
        A.key(38, armR=(-0.31, 0.02, 0.62), armL=(0.31, 0.02, 0.62), elbowR=(-0.30, 0.15, 0.85),
              elbowL=(0.30, 0.15, 0.85), hdirR=(0.0, -0.3, -1), hdirL=(0.0, -0.3, -1), hpalmR=(0.95, 0, 0),
              hpalmL=(-0.95, 0, 0))
        A.key(40, hips=(0, hy_out, -0.412), hips_rot=(-2, 0, 0), spine=(14, 0, 0), head=(4, 0, 0), neck=(-2, 0, 0))
        hR, hL = self.seat_hands(dyo)
        A.key(46, **hR, **hL, spine=(22, 0, 0), eyes=(0, 14))
        A.key(50, hips=(0, hy_out, -0.412), chair=dyo, footL=fl0, footR=fr0)
        # paso de los pies hacia delante bajo la mesa
        fL, fR = SB['footL'], SB['footR']
        midL = (fL[0], (fl0[1] + fL[1]) / 2, fL[2] + 0.05)
        midR = (fR[0], (fr0[1] + fR[1]) / 2, fR[2] + 0.05)
        A.key(54, footL=midL)
        A.key(58, footL=fL)
        A.key(60, footR=fr0)
        A.key(64, footR=midR, hips=(0, hy_out - 0.06, -0.402), chair=dyo - 0.06)
        A.key(68, footR=fR)
        hR2, hL2 = self.seat_hands(0.0)
        A.key(56, **self.seat_hands(dyo - 0.0)[0], **self.seat_hands(dyo)[1])
        A.key(72, hips=(0, SB['hips'][1], SB['hips'][2]), chair=0.0, **hR2, **hL2, spine=(24, 0, 0))
        A.key(76, **hR2, **hL2)
        # manos a la mesa por encima del riel
        A.key(82, armR=(-0.24, -0.15, 0.97), armL=(0.24, -0.15, 0.97), elbowR=(-0.30, 0.02, 0.93),
              elbowL=(0.30, 0.02, 0.93), hdirR=(0.3, -1, -0.3), hdirL=(-0.3, -1, -0.3), hpalmR=(0.3, 0, -1),
              hpalmL=(-0.3, 0, -1), fingR=F['relax'], fingL=F['relax'])
        A.key(92, SB, chair=0.0, eyes=(0, 10))
        A.key(100, SB, chair=0.0, eyes=(0, 8))
        A.proc(VP.blink_proc([20, 86]))
        A.props['cam'] = 'lado'

    def stand_up(self, A, SB, ST):
        dyo = S.SEAT_CY_OUT - S.SEAT_CY
        hy_out = SB['hips'][1] + dyo
        fl0, fr0 = ST['footL'], ST['footR']
        A.key(0, SB, chair=0.0, **VP.neutral_face(), eyes=(0, 8))
        A.key(8, armR=(-0.24, -0.15, 0.97), armL=(0.24, -0.15, 0.97), elbowR=(-0.30, 0.02, 0.93),
              elbowL=(0.30, 0.02, 0.93), hdirR=(0.3, -1, -0.3), hdirL=(-0.3, -1, -0.3), hpalmR=(0.3, 0, -1),
              hpalmL=(-0.3, 0, -1), fingR=F['relax'], fingL=F['relax'], tableR=0.0, tableL=0.0, spine=(22, 0, 0),
              eyes=(0, 0))
        hR, hL = self.seat_hands(0.0)
        A.key(16, **hR, **hL)
        A.key(20, hips=(0, SB['hips'][1], SB['hips'][2]), chair=0.0, footR=SB['footR'], footL=SB['footL'])
        fL, fR = SB['footL'], SB['footR']
        A.key(24, footR=(fR[0], (fr0[1] + fR[1]) / 2, fR[2] + 0.05))
        A.key(28, footR=fr0)
        A.key(30, footL=fL)
        A.key(34, footL=(fL[0], (fl0[1] + fL[1]) / 2, fL[2] + 0.05))
        A.key(38, footL=fl0)
        hR2, hL2 = self.seat_hands(dyo)
        A.key(28, hips=(0, SB['hips'][1], SB['hips'][2]), **hR, **hL)
        A.key(40, hips=(0, hy_out, -0.405), chair=dyo, **hR2, **hL2, spine=(20, 0, 0))
        A.key(46, hips=(0, hy_out, -0.412), spine=(30, 0, 0), hips_rot=(-2, 0, 0), **hR2, **hL2)
        A.key(49, armR=(-0.31, 0.10, 0.62), armL=(0.31, 0.10, 0.62), elbowR=(-0.30, 0.22, 0.85),
              elbowL=(0.30, 0.22, 0.85), hdirR=(0.0, -0.3, -1), hdirL=(0.0, -0.3, -1), hpalmR=(0.95, 0, 0),
              hpalmL=(-0.95, 0, 0))
        A.key(52, hips=(0, hy_out - 0.04, -0.37), hips_rot=(14, 0, 0), spine=(36, 0, 0), head=(-10, 0, 0),
              neck=(-8, 0, 0), armR=(-0.17, -0.13, 0.64), armL=(0.17, -0.13, 0.64),
              elbowR=(-0.31, 0.05, 0.84), elbowL=(0.31, 0.05, 0.84),
              hdirR=(0.05, -1, -0.5), hdirL=(-0.05, -1, -0.5),
              hpalmR=(0.2, 0, -1), hpalmL=(-0.2, 0, -1), fingR=F['relax'], fingL=F['relax'])
        A.key(62, hips=(0, 0.10, -0.17), hips_rot=(16, 0, 0), spine=(24, 0, 0), head=(-4, 0, 0), neck=(-4, 0, 0))
        A.key(72, hips=(0, 0.01, -0.012), hips_rot=(2, 0, 0), spine=(3, 0, 0), head=(2, 0, 0), neck=(0, 0, 0))
        A.key(80, ST, chair=dyo)
        A.key(90, ST, chair=dyo, eyes=(0, 0))
        A.proc(VP.blink_proc([60]))
        A.props['cam'] = 'lado'

    # ------------------------------------------------------------------ sostener fichas (mano izquierda)
    def stack_hold(self, tb):
        rig, ev = self.rig, self.ev
        s = 'l'
        hb = 'hand_' + s
        center, axis, pt, pi = H.grip_local(rig, self.skin, F['pinch'], s)
        c_h = rig.rest[hb].inverted() @ center
        a_h = (rig.rest3[hb].inverted() @ axis).normalized()
        F0, P0 = rig.hand_ref[s]
        f_h = rig.rest3[hb].inverted() @ F0
        y = (f_h - a_h * f_h.dot(a_h)).normalized()
        z = -a_h  # cara con puntos hacia el pulgar (hacia sus ojos)
        x = y.cross(z)
        Rl = Matrix((x, y, z)).transposed()
        base_off = Rl.to_4x4()
        base_off.translation = c_h + y * 0.028
        th = S.TILE[2] + 0.0005
        offs = []
        for k in (-1, 0, 1):
            o = base_off.copy()
            o.translation = base_off.translation + z * (k * th)
            offs.append(o)
        ch = VP.natural_hand(ev, tb, 'l', arm=(0.09, -0.37, 0.975), elbow=(0.28, -0.17, 0.90),
                             palm=(-0.6, 0.75, 0.2), flex=5)
        ch.update(fingL=F['pinch'], autoL=0.6)
        A = C.Anim('_s', 1)
        d = dict(tb)
        d.update(ch)
        A.key(0, d)
        ev.prev_theta = {}
        pb, _ = ev.evaluate(A, 0)
        HW = pb.pose[hb]
        top = HW @ (base_off.translation + y * (S.TILE[1] / 2))
        tiles = [dict(name=f'FichaMano{i + 1}', side='l', start=('hand', o)) for i, o in enumerate(offs)]
        self.log('Sostener_Fichas', 'mano', {k: v for k, v in pb.diag['arm_l'].items() if k not in ('E', 'S')})
        return dict(ch=ch, tiles=tiles, top=Vector(top))

    def stack_fidget(self, period):
        def fn(f, P, ev):
            arr = P['fingL'].reshape(15, 3).copy()
            a = math.sin(2 * math.pi * f / period * 2)
            b = math.sin(2 * math.pi * f / period * 3 + 1.0)
            arr[6, 0] += 6 * a   # medio
            arr[9, 0] += 6 * b   # anular
            arr[12, 0] += 7 * a  # meñique
            arr[3, 2] += 0.0
            P['fingL'] = arr
        return fn

    # ------------------------------------------------------------------ prueba de rango completo
    def range_test(self, A, ST):
        t = [0]
        F_ = F
        cur = dict(ST)
        cur.update(VP.neutral_face())
        cur.update(eyes=(0, 0), frotL=(0, 0, 0), frotR=(0, 0, 0), toeL=0.0, toeR=0.0, chest=(0, 0, 0))

        def K(dt, *ds, **kw):
            # pose a pose: cada clave guarda el estado completo (las claves vacías son pausas)
            t[0] += dt
            for d in ds:
                cur.update(d)
            cur.update(kw)
            A.key(t[0], dict(cur))

        def M(name, t0):
            A.mark(t0, name)

        neutral_arms = {k: ST[k] for k in ('armR', 'armL', 'elbowR', 'elbowL', 'hdirR', 'hdirL', 'hpalmR', 'hpalmL',
                                           'fingR', 'fingL', 'clavL', 'clavR')}
        A.key(0, ST, **VP.neutral_face(), eyes=(0, 0))
        # --- cuello / cabeza
        M('Cuello_Cabeza', 12)
        K(12)
        K(22, neck=(0, 22, 0), head=(0, 38, 0), eyes=(18, 0))
        K(10)
        K(28, neck=(0, -22, 0), head=(0, -38, 0), eyes=(-18, 0))
        K(10)
        K(20, neck=(0, 0, 0), head=(0, 0, 0), eyes=(0, 0))
        K(20, neck=(-12, 0, 0), head=(-22, 0, 0), eyes=(0, -15))
        K(24, neck=(14, 0, 0), head=(24, 0, 0), eyes=(0, 15))
        K(20, neck=(0, 0, 0), head=(0, 0, 0), eyes=(0, 0))
        K(18, neck=(0, 0, 10), head=(0, 0, 16))
        K(22, neck=(0, 0, -10), head=(0, 0, -16))
        K(18, neck=(0, 0, 0), head=(0, 0, 0))
        # --- hombros (clavículas)
        M('Hombros', t[0])
        K(18, clavL=(14, 0), clavR=(14, 0))
        K(18, clavL=(-6, 0), clavR=(-6, 0))
        K(18, clavL=(0, 14), clavR=(0, 14))
        K(18, clavL=(0, -12), clavR=(0, -12))
        K(16, clavL=(14, 0), clavR=(-4, 0))
        K(16, clavL=(-4, 0), clavR=(14, 0))
        K(16, clavL=(0, 0), clavR=(0, 0))
        # --- brazos (hombro)
        M('Brazos', t[0])
        fwdR = dict(armR=('chest', (-0.20, -0.53, 1.36)), elbowR=('chest', (-0.24, -0.27, 1.36)),
                    hdirR=('chest', (0, -1, 0)), hpalmR=('chest', (0, 0, -1)), fingR=F_['open'])
        fwdL = dict(armL=('chest', (0.20, -0.53, 1.36)), elbowL=('chest', (0.24, -0.27, 1.36)),
                    hdirL=('chest', (0, -1, 0)), hpalmL=('chest', (0, 0, -1)), fingL=F_['open'])
        upR = dict(armR=('chest', (-0.22, -0.06, 1.86)), elbowR=('chest', (-0.21, -0.03, 1.60)),
                   hdirR=('chest', (0, 0, 1)), hpalmR=('chest', (1, 0, 0)))
        upL = dict(armL=('chest', (0.22, -0.06, 1.86)), elbowL=('chest', (0.21, -0.03, 1.60)),
                   hdirL=('chest', (0, 0, 1)), hpalmL=('chest', (-1, 0, 0)))
        sideR = dict(armR=('chest', (-0.71, -0.02, 1.38)), elbowR=('chest', (-0.45, 0.0, 1.38)),
                     hdirR=('chest', (-1, 0, 0)), hpalmR=('chest', (0, 0, -1)))
        sideL = dict(armL=('chest', (0.71, -0.02, 1.38)), elbowL=('chest', (0.45, 0.0, 1.38)),
                     hdirL=('chest', (1, 0, 0)), hpalmL=('chest', (0, 0, -1)))
        crossR = dict(armR=('chest', (0.17, -0.36, 1.30)), elbowR=('chest', (-0.12, -0.30, 1.22)),
                      hdirR=('chest', (1, -0.2, 0.1)), hpalmR=('chest', (0, 1, 0)))
        crossL = dict(armL=('chest', (-0.17, -0.40, 1.24)), elbowL=('chest', (0.12, -0.34, 1.16)),
                      hdirL=('chest', (-1, -0.2, 0.1)), hpalmL=('chest', (0, 1, 0)))
        backR = dict(armR=('chest', (-0.18, 0.28, 0.98)), elbowR=('chest', (-0.24, 0.14, 1.18)),
                     hdirR=('chest', (0, 0.3, -1)), hpalmR=('chest', (0.3, 1, 0)))
        backL = dict(armL=('chest', (0.18, 0.28, 0.98)), elbowL=('chest', (0.24, 0.14, 1.18)),
                     hdirL=('chest', (0, 0.3, -1)), hpalmL=('chest', (-0.3, 1, 0)))
        K(24, **fwdR, **fwdL)
        K(24, **upR, **upL)
        K(10)
        K(24, **sideR, **sideL)
        K(10)
        K(24, **crossR, **crossL)
        K(22, **sideR, **sideL)
        K(24, **neutral_arms)
        K(22, **backR, **backL)
        K(22, **neutral_arms)
        # --- codos
        M('Codos', t[0])
        fwd_up = dict(fwdR, hpalmR=('chest', (0, 0, 1)))
        fwd_upL = dict(fwdL, hpalmL=('chest', (0, 0, 1)))
        bentR = dict(armR=('chest', (-0.19, -0.14, 1.52)), elbowR=('chest', (-0.24, -0.27, 1.36)),
                     hdirR=('chest', (0, 0.4, 1)), hpalmR=('chest', (0.2, -1, 0.3)), fingR=F_['open'])
        bentL = dict(armL=('chest', (0.19, -0.14, 1.52)), elbowL=('chest', (0.24, -0.27, 1.36)),
                     hdirL=('chest', (0, 0.4, 1)), hpalmL=('chest', (-0.2, -1, 0.3)), fingL=F_['open'])
        K(22, **fwd_up, **fwd_upL)
        K(20, **bentR, **bentL)
        K(20, **fwd_up, **fwd_upL)
        K(18, **bentR)
        K(18, **fwd_up, **bentL)
        K(18, **fwd_upL)
        # --- muñecas (brazos al frente)
        M('Munecas', t[0])
        K(16, **fwdR, **fwdL)
        K(16, hdirR=('chest', (0, -0.55, -0.85)), hdirL=('chest', (0, -0.55, -0.85)),
          hpalmR=('chest', (0, 0.85, -0.55)), hpalmL=('chest', (0, 0.85, -0.55)))
        K(18, hdirR=('chest', (0, -0.6, 0.8)), hdirL=('chest', (0, -0.6, 0.8)),
          hpalmR=('chest', (0, -0.8, -0.6)), hpalmL=('chest', (0, -0.8, -0.6)))
        K(16, hdirR=('chest', (0, -1, 0)), hdirL=('chest', (0, -1, 0)), hpalmR=('chest', (0, 0, -1)),
          hpalmL=('chest', (0, 0, -1)))
        K(16, hdirR=('chest', (-0.4, -0.92, 0)), hdirL=('chest', (0.4, -0.92, 0)))
        K(16, hdirR=('chest', (0.3, -0.95, 0)), hdirL=('chest', (-0.3, -0.95, 0)))
        K(14, hdirR=('chest', (0, -1, 0)), hdirL=('chest', (0, -1, 0)))
        K(18, hpalmR=('chest', (1, 0, 0)), hpalmL=('chest', (-1, 0, 0)))
        K(18, hpalmR=('chest', (0, 0, 1)), hpalmL=('chest', (0, 0, 1)))
        K(18, hpalmR=('chest', (0, 0, -1)), hpalmL=('chest', (0, 0, -1)))
        # --- dedos (manos delante del pecho, palmas a la cámara)
        M('Dedos', t[0])
        showR = dict(armR=('chest', (-0.17, -0.38, 1.33)), elbowR=('chest', (-0.30, -0.18, 1.12)),
                     hdirR=('chest', (0.15, -0.2, 1)), hpalmR=('chest', (0, 1, 0.2)), fingR=F_['open'])
        showL = dict(armL=('chest', (0.17, -0.38, 1.33)), elbowL=('chest', (0.30, -0.18, 1.12)),
                     hdirL=('chest', (-0.15, -0.2, 1)), hpalmL=('chest', (0, 1, 0.2)), fingL=F_['open'])
        K(24, **showR, **showL)
        K(14, fingR=F_['fist'], fingL=F_['fist'])
        K(14, fingR=F_['open'], fingL=F_['open'])
        K(14, fingR=F_['fist'], fingL=F_['fist'])
        K(14, fingR=F_['open'], fingL=F_['open'])
        K(14, fingR=F_['fan'], fingL=F_['fan'])
        K(14, fingR=F_['open'], fingL=F_['open'])
        # cada dedo, uno por uno
        names = ['thumb', 'index', 'middle', 'ring', 'pinky']
        for i, n in enumerate(names):
            arr = F_['open'].copy()
            if i == 0:
                arr[0:3] = np.array([(35, 10, 35), (35, 0, 0), (45, 0, 0)])
            else:
                arr[3 * i:3 * i + 3, 0] = (85, 95, 55)
                # los vecinos acompañan un poco (anatomía)
                for j in (i - 1, i + 1):
                    if 1 <= j <= 4:
                        arr[3 * j:3 * j + 3, 0] += (15, 15, 8) if i >= 3 else (8, 8, 4)
            M('Dedo_' + n, t[0] + 8)
            K(10, fingR=arr, fingL=arr)
            K(8)
            K(10, fingR=F_['open'], fingL=F_['open'])
        # contar 1..5
        M('Contar', t[0] + 6)
        K(12, fingR=F_['count0'], fingL=F_['count0'])
        for k in range(1, 6):
            K(14, fingR=F_['count%d' % k], fingL=F_['count%d' % k])
            K(4)
        K(14, fingR=F_['pinch'], fingL=F_['pinch'])
        K(8)
        K(14, fingR=F_['open'], fingL=F_['open'])
        K(20, **neutral_arms)
        # --- columna
        M('Columna', t[0])
        K(24, spine=(40, 0, 0), neck=(-10, 0, 0))
        K(24, spine=(-18, 0, 0), neck=(6, 0, 0))
        K(18, spine=(0, 0, 0), neck=(0, 0, 0))
        K(22, spine=(0, 0, 22))
        K(24, spine=(0, 0, -22))
        K(18, spine=(0, 0, 0))
        K(22, spine=(0, 38, 0), head=(0, 8, 0))
        K(26, spine=(0, -38, 0), head=(0, -8, 0))
        K(20, spine=(0, 0, 0), head=(0, 0, 0))
        # --- cadera
        M('Cadera', t[0])
        K(20, hips=(0.05, 0, -0.02), hips_rot=(0, 0, -6), spine=(0, 0, 6))
        K(24, hips=(-0.05, 0, -0.02), hips_rot=(0, 0, 6), spine=(0, 0, -6))
        K(18, hips=(0, 0, -0.005), hips_rot=(0, 0, 0), spine=(0, 0, 0))
        K(20, hips_rot=(0, 14, 0), spine=(0, -14, 0))
        K(22, hips_rot=(0, -14, 0), spine=(0, 14, 0))
        K(16, hips_rot=(12, 0, 0), spine=(-12, 0, 0))
        K(16, hips_rot=(-12, 0, 0), spine=(12, 0, 0))
        K(16, hips_rot=(0, 0, 0), spine=(0, 0, 0))
        # --- rodillas
        M('Rodillas', t[0])
        squat_arms = dict(armR=('chest', (-0.20, -0.50, 1.30)), armL=('chest', (0.20, -0.50, 1.30)),
                          elbowR=('chest', (-0.25, -0.25, 1.30)), elbowL=('chest', (0.25, -0.25, 1.30)),
                          hdirR=('chest', (0, -1, 0)), hdirL=('chest', (0, -1, 0)),
                          hpalmR=('chest', (0.3, 0, -1)), hpalmL=('chest', (-0.3, 0, -1)))
        K(26, hips=(0, 0.10, -0.30), hips_rot=(28, 0, 0), spine=(14, 0, 0), head=(-12, 0, 0), **squat_arms)
        K(10)
        K(24, hips=(0, 0, -0.005), hips_rot=(0, 0, 0), spine=(0, 0, 0), head=(0, 0, 0), **neutral_arms)
        fl, fr = Vector(ST['footL']), Vector(ST['footR'])
        K(10, footL=tuple(fl[:]), footR=tuple(fr[:]), hips=(0, 0, -0.005))
        K(16, hips=(-0.035, 0, -0.01), hips_rot=(0, 0, 4))
        K(20, footL=tuple((fl + Vector((0, -0.22, 0.34)))[:]), frotL=(20, 0, 0), kneeL=(0.05, -1, 0.2))
        K(14)
        K(20, footL=tuple(fl[:]), frotL=(0, 0, 0))
        K(14, hips=(0.035, 0, -0.01), hips_rot=(0, 0, -4))
        K(20, footR=tuple((fr + Vector((0, -0.22, 0.34)))[:]), frotR=(20, 0, 0), kneeR=(-0.05, -1, 0.2))
        K(14)
        K(20, footR=tuple(fr[:]), frotR=(0, 0, 0))
        K(10, hips=(-0.035, 0, -0.01), hips_rot=(0, 0, 4))
        # --- tobillos / dedos del pie (pie izquierdo levantado al frente)
        M('Tobillos_DedosPie', t[0])
        fup = fl + Vector((0, -0.12, 0.10))
        K(16, footL=tuple(fup[:]), kneeL=(0.05, -1, 0.1))
        K(14, frotL=(35, 0, 0), toeL=35)
        K(18, frotL=(-25, 0, 0), toeL=-25)
        K(14, frotL=(0, 0, 0), toeL=0)
        K(12, frotL=(0, 25, 0), toeL=0)
        K(14, frotL=(0, -25, 0))
        K(12, frotL=(0, 0, 0))
        K(14, toeL=40)
        K(14, toeL=-30)
        K(12, toeL=0)
        K(16, footL=tuple(fl[:]))
        K(12, hips=(0, 0, -0.005), hips_rot=(0, 0, 0))
        # puntillas (talones arriba, bola en el suelo)
        g = self.foot
        tip = 26
        aL = self.ankle_for('l', Vector((fl.x, fl.y + g['l']['ball'].y, g['l']['sole'])), tip, 'ball')
        aR = self.ankle_for('r', Vector((fr.x, fr.y + g['r']['ball'].y, g['r']['sole'])), tip, 'ball')
        dzh = aL.z - fl.z
        K(18, footL=tuple(aL[:]), footR=tuple(aR[:]), frotL=(tip, 0, 0), frotR=(tip, 0, 0), toeL=0, toeR=0,
          hips=(0, aL.y - fl.y, -0.005 + dzh))
        K(10)
        K(18, footL=tuple(fl[:]), footR=tuple(fr[:]), frotL=(0, 0, 0), frotR=(0, 0, 0), hips=(0, 0, -0.005))
        # --- cara
        M('Cara', t[0])
        K(10, head=(-4, 0, 0), neck=(-2, 0, 0))
        fz = VP.neutral_face()
        for nm, w in (('blink', 1.0), (None, 0), ('smile', 1.0), (None, 0), ('surprise', 1.0), (None, 0),
                      ('mouth_open', 1.0), (None, 0), ('angry', 1.0), (None, 0), ('sad', 1.0), (None, 0),
                      ('laugh', 1.0), (None, 0)):
            d = dict(fz)
            if nm:
                d.update(VP.face((nm, w)))
            K(10, **d)
            if nm:
                K(6)
        K(12, eyes=(25, 0))
        K(12, eyes=(-25, 0))
        K(12, eyes=(0, -20))
        K(12, eyes=(0, 25))
        K(10, eyes=(0, 0), head=(0, 0, 0), neck=(0, 0, 0))
        # --- todo junto
        M('Todo_Junto', t[0])
        fz = VP.neutral_face()
        K(24, upR, fwdL, fz, VP.face(('laugh', 1.0)), spine=(10, 20, 6), hips=(0, 0.04, -0.12),
          hips_rot=(10, -6, 0), head=(-10, 16, 0), fingR=F_['fan'], fingL=F_['fist'], clavR=(10, 6))
        K(24, sideR, sideL, fz, VP.face(('surprise', 1.0)), spine=(-6, -20, -6), hips=(0, 0.0, -0.06),
          hips_rot=(-4, 8, 0), head=(6, -16, 4), fingR=F_['open'], fingL=F_['fan'], clavR=(0, 0))
        K(24, fwd_up, fwd_upL, fz, VP.face(('smile', 1.0)), spine=(24, 0, 0), hips=(0, 0.08, -0.22),
          hips_rot=(20, 0, 0), head=(-6, 0, 0), fingR=F_['count3'], fingL=F_['count2'])
        K(28, ST, **VP.neutral_face(), eyes=(0, 0), frotL=(0, 0, 0), frotR=(0, 0, 0), toeL=0.0, toeR=0.0)
        K(12)
        A.frames = t[0]
        print('RANGO cuadros', t[0])
        A.props['cam'] = 'pie'
        A.props['nochair'] = True
        A.props['notable'] = True
