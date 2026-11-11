"""Presets calibrados y poses base (de pie / sentado a la mesa)."""
import math
import numpy as np
from mathutils import Vector

import vc_core as C
import vc_pose as VP
import vc_scene as S

# Pulgar (semántica izquierda): thumb_01 (x aduce hacia el meñique, y gira, z flexiona hacia la palma),
# thumb_02/03 (x flexiona). Calibrado con renders de primer plano (scripts/explorar_*).
THUMB = dict(
    relax=((10, 0, 10), (8, 0, 0), (10, 0, 0)),
    pinch=((40.0, 31.0, 34.7), (-0.2, 0, 0), (7.3, 0, 0)),   # optimizado: yemas enfrentadas a ~4.7 cm
    fist=((35, 10, 30), (25, 0, 0), (35, 0, 0)),
    up=((-10, 0, -10), (-5, 0, 0), (-5, 0, 0)),
    flat=((0, 0, 0), (0, 0, 0), (0, 0, 0)),
    knock=((35, 10, 30), (25, 0, 0), (35, 0, 0)),
    count=((40, 0, 40), (35, 0, 0), (40, 0, 0)),
)

PINCH_V = (45.0, 20.0, 15.7, 0.5, -14.9, 64.1, -20.8, 4.6, -0.1)

SEATED = {}
STAND = {}


def setup(rig, ev):
    VP.define_presets(THUMB['relax'], THUMB['pinch'], THUMB['fist'], THUMB['up'], THUMB['flat'],
                      THUMB['knock'], THUMB['count'])
    F = VP.F
    F['table_rest'] = VP.fingers(((10, 0, 10), (6, 0, 0), (8, 0, 0)), (6, 8, 4), (7, 9, 5), (8, 10, 6), (10, 12, 7),
                                 spread=(2, 0, -2, -4))
    # pinza: índice optimizado, medio/anular/meñique relajados y algo curvos (sin puño)
    F['pinch'] = VP.fingers(THUMB['pinch'], (39.6, 17.5, 11.1), (66, 56, 30), (71, 61, 35), (74, 64, 38),
                            spread=(-10.8, 0, -3, -6))
    # pre-forma (abierta antes de cerrar la pinza)
    F['pinch_open'] = VP.finger_mix(('pinch', 0.55), ('open', 0.45))
    F['pinch_open'][3:6] = F['pinch'][3:6] * 0.5
    F['tap_up'] = VP.fingers(THUMB['relax'], (-8, 4, 2), (12, 16, 10), (14, 18, 10), (16, 20, 12))
    # pinza fina para la ficha parada (yemas a 14.5 mm, enfrentadas; optimizado dentro de los límites)
    pv = VP.fingers(THUMB['pinch'], (39.6, 17.5, 11.1), (34, 38, 22), (40, 44, 26), (46, 48, 30),
                    spread=(-6, 0, -4, -8))
    x = PINCH_V
    pv[0] = (x[0], x[1], x[2])
    pv[1] = (x[3], 0, 0)
    pv[2] = (x[4], 0, 0)
    pv[3] = (x[5], 0, x[6])
    pv[4] = (x[7], 0, 0)
    pv[5] = (x[8], 0, 0)
    F['pinch_v'] = pv
    F['pinch_v_open'] = VP.finger_mix(('pinch_v', 0.6), ('relax', 0.4))
    F['pinch_v_open'][0] = pv[0] + np.array((-12.0, 0, -10.0))
    F['pinch_v_open'][3] = pv[3] + np.array((-14.0, 0, 0))
    VP.F.update(F)
    ev.defaults = VP.defaults(rig)
    ev.defaults['fingL'] = F['relax'].copy()
    ev.defaults['fingR'] = F['relax'].copy()
    # ---------------- sentado ----------------
    base = dict(hips=(0, 0.135, -0.41), hips_rot=(-4, 0, 0), spine=(20, 0, 0), clavL=(4, 8), clavR=(4, 8),
                neck=(-4, 0, 0), head=(10, 0, 0), footL=(0.15, -0.29, 0.074), footR=(-0.15, -0.29, 0.074),
                kneeL=(0.1, -1, 0), kneeR=(-0.1, -1, 0))
    pb = VP.torso_eval(ev, base)
    ud, fd = (-0.14, -0.80, -0.48), (0.36, -0.93, -0.06)
    WR, ER = VP.arm_from_dirs(pb, 'R', ud, fd, space='world')
    WL, EL = VP.arm_from_dirs(pb, 'L', C.mirror_v(C.vec(ud)), C.mirror_v(C.vec(fd)), space='world')
    SEATED.clear()
    SEATED.update(base)
    # manos apoyadas a los lados de la fila de fichas paradas
    WR, ER = (-0.255, -0.415, 0.85), (-0.345, -0.15, 0.88)
    WL, EL = tuple(C.mirror_v(C.vec(WR))[:]), tuple(C.mirror_v(C.vec(ER))[:])
    SEATED.update(armR=WR, elbowR=ER, armL=WL, elbowL=EL, hdirR=(0.38, -1, 0.1), hpalmR=(0.25, 0, -1),
                  hdirL=(-0.38, -1, 0.1), hpalmL=(-0.25, 0, -1), autoR=3.0, autoL=3.0, tableR=1.0, tableL=1.0,
                  fingL=F['table_rest'], fingR=F['table_rest'])
    # ---------------- de pie ----------------
    STAND.clear()
    STAND.update(hips=(0, 0, -0.005), hips_rot=(0, 0, 0), spine=(0, 0, 0), neck=(0, 0, 0), head=(0, 0, 0),
                 clavL=(0, 0), clavR=(0, 0),
                 armR=('chest', (-0.225, -0.03, 0.93)), armL=('chest', (0.225, -0.03, 0.93)),
                 hdirR=('chest', (-0.08, -0.15, -1)), hpalmR=('chest', (1, 0.15, 0)),
                 hdirL=('chest', (0.08, -0.15, -1)), hpalmL=('chest', (-1, 0.15, 0)),
                 poleR=(-0.35, 1, -0.2), poleL=(0.35, 1, -0.2), autoR=0.8, autoL=0.8, tableR=0.0, tableL=0.0,
                 elbowR=('chest', (-0.25, 0.03, 1.19)), elbowL=('chest', (0.25, 0.03, 1.19)),
                 footL=tuple(rig.head['foot_l'][:]), footR=tuple(rig.head['foot_r'][:]),
                 kneeL=(0.1, -1, 0), kneeR=(-0.1, -1, 0), fingL=F['relax'], fingR=F['relax'])


def seated(**over):
    d = dict(SEATED)
    d.update(over)
    return d


def stand(**over):
    d = dict(STAND)
    d.update(over)
    return d


def breathe(period, amp=1.0, phase=0.0, seated_mode=False):
    def fn(f, P, ev):
        s = math.sin(2 * math.pi * f / period + phase)
        P['spine'] = P['spine'] + np.array([-1.2 * amp * s, 0, 0])
        P['chest'] = P['chest'] + np.array([-0.6 * amp * s, 0, 0])
        P['neck'] = P['neck'] + np.array([0.9 * amp * s, 0, 0])
        P['head'] = P['head'] + np.array([0.6 * amp * s, 0, 0])
        P['clavL'] = P['clavL'] + np.array([0.9 * amp * s, 0])
        P['clavR'] = P['clavR'] + np.array([0.9 * amp * s, 0])
    return fn


def finger_fidget(period, amp=3.0, sides='LR', phase=0.0):
    rng = np.random.RandomState(7)
    ph = rng.uniform(0, 2 * math.pi, (2, 15))
    harm = rng.randint(1, 3, (2, 15))

    def fn(f, P, ev):
        for i, s in enumerate(sides):
            add = np.zeros((15, 3))
            add[:, 0] = amp * np.sin(2 * math.pi * f * harm[i] / period + ph[i] + phase)
            add[0:3, 0] *= 0.5
            P['fing' + s] = P['fing' + s].reshape(15, 3) + add
    return fn
