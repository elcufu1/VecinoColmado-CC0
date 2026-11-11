"""Definición de las 23 animaciones de VecinoColmado (24 fps)."""
import math
import numpy as np
from mathutils import Vector, Matrix

import vc_core as C
import vc_pose as VP
import vc_lib as L
import vc_scene as S
from vc_core import rot_pyr

F = VP.F
TOP = S.TABLE_TOP


def NEUT():
    return VP.neutral_face()


def FACE(*pairs, **kw):
    d = NEUT()
    d.update(VP.face(*pairs, **kw))
    return d


def look(yaw=0.0, pitch=0.0, roll=0.0, base_neck=(-4, 0, 0), base_head=(10, 0, 0)):
    return dict(neck=(base_neck[0] + pitch * 0.4, base_neck[1] + yaw * 0.4, base_neck[2] + roll * 0.4),
                head=(base_head[0] + pitch * 0.6, base_head[1] + yaw * 0.6, base_head[2] + roll * 0.6))


def pick(d, side):
    S_ = side.upper()
    return {k: d[k] for k in ('arm' + S_, 'elbow' + S_, 'hdir' + S_, 'hpalm' + S_, 'fing' + S_, 'table' + S_,
                              'auto' + S_) if k in d}


def torso(d):
    return {k: d[k] for k in ('hips', 'hips_rot', 'spine', 'chest', 'neck', 'head', 'clavL', 'clavR',
                              'footL', 'footR', 'kneeL', 'kneeR') if k in d}


def drum_proc(side, starts, period=12, amp=28.0, tap=5):
    """Tamborileo: meñique->anular->medio->índice. starts: cuadros de inicio de cada pasada."""
    S_ = side.upper()

    def fn(f, P, ev):
        arr = P['fing' + S_].reshape(15, 3).copy()
        for st in starts:
            for k, fi in enumerate((4, 3, 2, 1)):  # pinky, ring, middle, index
                t0 = st + k * (period / 4.0)
                x = (f - t0) / tap
                if 0 <= x <= 1:
                    b = math.sin(math.pi * x)
                    arr[fi * 3, 0] -= amp * b
                    arr[fi * 3 + 1, 0] -= amp * 0.35 * b
        P['fing' + S_] = arr
    return fn


def with_elbow(ev, base, ch, side):
    """Completa canales de brazo con el codo resultante (para claves con codo explícito)."""
    S_ = side.upper()
    d = dict(base)
    d.update(ch)
    d.pop('elbow' + S_, None)
    A = C.Anim('_e', 1)
    A.key(0, d)
    ev.prev_theta = {}
    pb, _ = ev.evaluate(A, 0)
    out = dict(ch)
    out['elbow' + S_] = tuple(pb.diag['arm_' + side.lower()]['E'][:])
    return out, pb


# =====================================================================================
def build(ctx):
    rig, ev = ctx.rig, ctx.ev
    SB = L.seated()
    anims = []

    def new(name, frames, loop=False, desc='', use=''):
        A = C.Anim(name, frames, loop, desc)
        A.props['use'] = use
        anims.append(A)
        return A

    # ---------------------------------------------------------------- 5. Idle sentado
    A = new('Idle_Sentado', 144, True, 'Sentado a la mesa: respira, mira las fichas, tamborilea los dedos.',
            'Espera de turno (bucle).')
    drum_rest = F['tap_up'].copy()
    A.key(0, SB, **look(0, 0), eyes=(0, 8), fingR=F['table_rest'], **NEUT())
    A.key(20, fingR=VP.finger_mix(('table_rest', 0.4), ('claw', 0.6)), armR=Vector(SB['armR']) + Vector((0.0, -0.01, 0.0)))
    A.key(40, **look(10, 4), eyes=(8, 12))
    A.key(64, fingR=VP.finger_mix(('table_rest', 0.4), ('claw', 0.6)))
    A.key(76, **look(-8, 2), eyes=(-6, 10), fingR=F['table_rest'], armR=SB['armR'])
    A.key(96, fingR=VP.finger_mix(('table_rest', 0.4), ('claw', 0.6)), armR=Vector(SB['armR']) + Vector((0.0, -0.01, 0.0)))
    A.key(112, **look(3, 6), eyes=(2, 14))
    A.key(130, fingR=VP.finger_mix(('table_rest', 0.4), ('claw', 0.6)))
    A.key(140, fingR=F['table_rest'], armR=SB['armR'])
    A.proc(L.breathe(72, 1.0))
    A.proc(drum_proc('R', [26, 38, 100, 112]))
    A.proc(L.finger_fidget(144, 2.0, 'L'))
    A.proc(VP.blink_proc([12, 70, 122]))
    A.props['cam'] = 'mesa'

    # ---------------------------------------------------------------- 6/7. Agarrar
    NH = lambda base, side, **kw: VP.natural_hand(ev, base, side, **kw)  # noqa: E731
    th = L.seated(spine=(22, -2, 0), clavR=(4, 9), **look(-4, 6))
    HOLD = NH(th, 'r', arm=(-0.16, -0.37, 0.935), elbow=(-0.33, -0.17, 0.89), palm=(0.35, 0.15, -1), flex=10)
    HOLD['fingR'] = F['pinch']
    ctx.HOLD, ctx.HOLD_T = HOLD, th

    def agarrar(name, x, y, frames, f_hover, f_grab, far=False, offset=None):
        A = new(name, frames, False,
                f'Agarra una ficha {"lejana" if far else "cercana"} con pinza pulgar-índice y la levanta.',
                'Tomar ficha de la mesa (pozo o propias).')
        if far:
            tb = L.seated(hips=(0, 0.11, -0.405), spine=(36, -4, 0), clavR=(2, 14), clavL=(4, 6), **look(-6, 12))
        else:
            tb = L.seated(spine=(25, -5, 0), clavR=(4, 11), **look(-10, 10))
        tb['poleR'] = (-0.7, 0.4, -0.6)
        tb['autoR'] = 0.6
        ch, T, off, info = VP.best_grip(ev, tb, 'r', x, y, offset=offset)
        ch['fingR'] = F['pinch']
        ctx.log(name, 'agarre', info)
        ch, _ = with_elbow(ev, tb, ch, 'r')
        chh = dict(ch, armR=tuple((Vector(ch['armR']) + Vector((0.01, 0.02, 0.05)))[:]), fingR=F['pinch_open'])
        chh, _ = with_elbow(ev, tb, chh, 'r')
        A.key(0, SB, **look(0, 4), eyes=(0, 10), **NEUT())
        A.key(3, eyes=(-8, 16))
        if far:
            mid = (Vector(SB['armR']) + Vector(chh['armR'])) / 2 + Vector((0, 0, 0.06))
            A.key(f_hover // 2 + 1, armR=tuple(mid[:]), tableR=0.0, fingR=VP.finger_mix(('relax', 0.5), ('pinch_open', 0.5)))
        A.key(f_hover, torso(tb), **chh)
        A.key(f_grab, torso(tb), **ch, **VP.face(('focus', 1.0)))
        A.key(f_grab + 1, **ch)
        A.key(frames, torso(th), **HOLD, **look(-4, 6), eyes=(-3, 10), **NEUT())
        if far:
            # la mano izquierda se adelanta y se apoya (soporte)
            A.key(f_hover - 2, armL=(0.13, -0.50, 0.84), elbowL=(0.24, -0.29, 0.86), hdirL=(-0.45, -1, 0.15),
                  hpalmL=(-0.25, 0, -1), fingL=F['table_rest'], tableL=1.0)
            A.key(f_grab + 3, armL=(0.13, -0.50, 0.84), elbowL=(0.24, -0.29, 0.86))
            A.key(frames, armL=SB['armL'], elbowL=SB['elbowL'], hdirL=SB['hdirL'], hpalmL=SB['hpalmL'])
        A.tiles.append(dict(name='Ficha', side='r', start=('table', T), grab=f_grab))
        A.proc(L.breathe(48, 0.5))
        A.props['cam'] = 'mesa'
        return A, off

    A6, OFF = agarrar('Agarrar_Ficha_Cerca', -0.13, -0.43, 20, 6, 10)
    A7, _ = agarrar('Agarrar_Ficha_Lejos', -0.07, -0.64, 26, 9, 14, far=True, offset=OFF)
    ctx.OFF = OFF

    def held_start(A):
        A.key(0, ctx.HOLD_T, **ctx.HOLD, eyes=(-3, 10), **NEUT())
        A.tiles.append(dict(name='Ficha', side='r', start=('hand', OFF), release=None))
        return ctx.HOLD_T, ctx.HOLD

    # ---------------------------------------------------------------- 8. Colocar cerca
    A = new('Colocar_Ficha_Cerca', 20, False,
            'Lleva la ficha rápido y decidido a la mesa, la suelta y vuelve a la pose sentada.',
            'Jugar una ficha cerca del jugador.')
    th, chH = held_start(A)
    tb = L.seated(spine=(26, -4, 0), clavR=(4, 12), **look(-6, 12))
    tb['poleR'] = (-0.7, 0.4, -0.6)
    tb['autoR'] = 0.6
    ch, T, _, info = VP.best_grip(ev, tb, 'r', -0.09, -0.52, offset=OFF)
    ctx.log(A.name, 'suelta', info)
    ch, _ = with_elbow(ev, tb, ch, 'r')
    chv = dict(ch, armR=tuple((Vector(ch['armR']) + Vector((0.0, 0.015, 0.03)))[:]))
    chv, _ = with_elbow(ev, tb, chv, 'r')
    A.key(5, torso(tb), **chv, eyes=(-6, 16), **VP.face(('determined', 0.7)))
    A.key(7, torso(tb), **ch)
    A.key(9, fingR=F['pinch_open'], armR=Vector(ch['armR']) + Vector((0, 0, 0.004)))
    A.key(12, armR=Vector(ch['armR']) + Vector((0.01, 0.03, 0.045)), fingR=VP.finger_mix(('pinch_open', 0.5), ('relax', 0.5)))
    A.key(20, SB, **look(0, 4), eyes=(0, 10), **NEUT())
    A.tiles[-1]['release'] = 7
    A.proc(L.breathe(48, 0.5))
    A.props['cam'] = 'mesa'

    # ---------------------------------------------------------------- 9. Colocar lejos
    A = new('Colocar_Ficha_Lejos', 30, False,
            'Coloca la ficha lejos: la otra mano se apoya firme, el cuerpo se levanta un poco y todo se mueve a la vez.',
            'Jugar una ficha en el extremo lejano de la mesa.')
    th, chH = held_start(A)
    tb = L.seated(hips=(0, 0.11, -0.31), hips_rot=(8, 0, 0), spine=(44, -5, 0), clavR=(3, 18), clavL=(8, 4),
                  **look(-4, 0))
    tb['poleR'] = (-0.8, 0.3, -0.5)
    tb['autoR'] = 0.6
    ch, T, _, info = VP.best_grip(ev, tb, 'r', -0.04, -0.74, offset=OFF)
    ctx.log(A.name, 'suelta', info)
    ch, _ = with_elbow(ev, tb, ch, 'r')
    chv = dict(ch, armR=tuple((Vector(ch['armR']) + Vector((0.0, 0.02, 0.035)))[:]))
    chv, _ = with_elbow(ev, tb, chv, 'r')
    tmid = L.seated(hips=(0, 0.12, -0.38), hips_rot=(4, 0, 0), spine=(36, -3, 0), clavR=(3, 14), **look(-4, 8))
    supL = dict(armL=(0.17, -0.47, 0.835), elbowL=(0.27, -0.25, 0.92), hdirL=(-0.35, -1, 0.1), hpalmL=(-0.1, 0, -1),
                fingL=F['flat'], tableL=1.0)
    A.key(5, torso(tmid), **supL, eyes=(-4, 6))
    A.key(9, torso(tb), **chv, **VP.face(('determined', 0.8)))
    A.key(11, torso(tb), **ch, **supL)
    A.key(13, fingR=F['pinch_open'], armR=Vector(ch['armR']) + Vector((0, 0, 0.004)))
    A.key(16, torso(tmid), armR=Vector(ch['armR']) + Vector((0.0, 0.12, 0.06)),
          fingR=VP.finger_mix(('pinch_open', 0.5), ('relax', 0.5)), elbowR=Vector(ch['elbowR']) + Vector((0, 0.08, 0.02)))
    A.key(19, **supL)
    A.key(24, torso(SB), armL=SB['armL'], elbowL=SB['elbowL'], hdirL=SB['hdirL'], hpalmL=SB['hpalmL'],
          fingL=SB['fingL'], **NEUT())
    A.key(30, SB, **look(0, 4), eyes=(0, 10))
    A.tiles[-1]['release'] = 11
    A.props['cam'] = 'mesa_lejos'

    # ---------------------------------------------------------------- 10. Golpe
    A = new('Golpe_Ficha', 34, False,
            'Tranque/capicúa: levanta la ficha y la golpea fuerte contra la mesa.',
            'Jugada final (tranque o capicúa).')
    th, chH = held_start(A)
    tb = L.seated(spine=(32, -4, 0), clavR=(2, 12), **look(-6, 14))
    tb['poleR'] = (-0.7, 0.4, -0.6)
    tb['autoR'] = 0.6
    ch, T, _, info = VP.best_grip(ev, tb, 'r', -0.09, -0.53, offset=OFF)
    ctx.log(A.name, 'golpe', info)
    ch, _ = with_elbow(ev, tb, ch, 'r')
    tup = L.seated(spine=(8, -8, 0), clavR=(10, 4), **look(-4, -6))
    chU = NH(tup, 'r', arm=(-0.21, -0.30, 1.17), elbow=(-0.37, -0.12, 0.99), palm=(0.3, 0.3, -1), flex=-5)
    chU['fingR'] = F['pinch']
    A.key(9, torso(tup), **chU, **VP.face(('determined', 1.0)), eyes=(-4, 12))
    A.key(11, armR=Vector(chU['armR']) + Vector((0, -0.01, 0.02)))
    A.key(15, torso(tb), **ch, tin=1.6)
    A.key(16, **VP.face(('shout', 1.0)), spine=(34, -4, 0))
    A.key(22, **ch)
    A.key(25, fingR=F['pinch_open'], armR=Vector(ch['armR']) + Vector((0.01, 0.02, 0.03)), **VP.face(('determined', 0.6)))
    A.key(34, SB, **look(0, 4), eyes=(0, 10), **NEUT())
    A.tiles[-1]['release'] = 15
    A.props['cam'] = 'mesa'

    # ---------------------------------------------------------------- 11. Pasar
    A = new('Pasar', 26, False, 'Toca la mesa dos veces con los nudillos ("paso").', 'Pasar turno.')
    pos = Vector((-0.11, -0.45, 0.0))
    kb = L.seated(spine=(23, -3, 0), **look(-4, 10))

    def knock(z, tab):
        d = NH(kb, 'r', arm=tuple((pos + Vector((0, 0, z)))[:]), elbow=(-0.29, -0.24, 0.90), palm=(0.25, 0.7, -0.6),
               flex=28)
        d['fingR'] = F['knock']
        d['tableR'] = tab
        return d
    up1, dn, up2 = knock(0.95, 0.0), knock(0.87, 1.0), knock(0.92, 0.0)
    A.key(0, SB, **look(0, 4), **NEUT())
    A.key(5, torso(kb), **up1, **VP.face(mouthPressLeft=0.4, mouthPressRight=0.4))
    A.key(8, **dn, tin=1.5)
    A.key(11, **up2)
    A.key(14, **dn, tin=1.5)
    A.key(18, **up2, **look(-3, 6))
    A.key(26, SB, **look(0, 4), **NEUT())
    A.proc(VP.blink_proc([20]))
    A.props['cam'] = 'mesa'

    # ---------------------------------------------------------------- 12. Barajar
    A = new('Barajar_Fichas', 48, True, 'Ambas manos revuelven fichas boca abajo en círculos sobre la mesa.',
            'Revolver fichas al inicio de la mano (bucle).')
    tb = L.seated(hips=(0, 0.11, -0.40), spine=(28, 0, 0), clavL=(5, 14), clavR=(5, 14), **look(0, 16))
    lift = S.TILE[2]
    shuffle = dict(fingR=F['claw'], fingL=F['claw'], tableR=1.0, tableL=1.0, liftR=lift, liftL=lift,
                   hdirR=(0.3, -1, -0.05), hpalmR=(0.1, 0, -1), hdirL=(-0.3, -1, -0.05), hpalmL=(-0.1, 0, -1))
    cR, cL, rad = Vector((-0.11, -0.49, 0.86)), Vector((0.11, -0.49, 0.86)), 0.06
    A.key(0, tb, **shuffle, eyes=(0, 10), **NEUT())
    A.key(24, eyes=(4, 12))
    for k in range(16):
        f = k * 3
        a = 2 * math.pi * k / 8.0
        pr = cR + Vector((rad * math.cos(a), rad * math.sin(a), 0))
        pl = cL + Vector((-rad * math.cos(a + 0.6), rad * math.sin(a + 0.6), 0))
        A.key(f, armR=tuple(pr[:]), armL=tuple(pl[:]),
              elbowR=tuple((pr + Vector((-0.14, 0.22, 0.10)))[:]), elbowL=tuple((pl + Vector((0.14, 0.22, 0.10)))[:]),
              spine=(28 + 1.5 * math.sin(a), 2.5 * math.cos(a), 0))
    A.proc(L.breathe(48, 0.6))
    A.props['shuffle'] = True
    A.props['cam'] = 'mesa'

    # ---------------------------------------------------------------- 13. Sostener
    A = new('Sostener_Fichas', 72, True,
            'Sostiene un grupo de fichas en la mano izquierda, las mira y mueve los dedos (bucle).',
            'Mirar las fichas propias (bucle).')
    tb = L.seated(spine=(18, 4, 0), **look(6, 18))
    hold = ctx.stack_hold(tb)
    A.key(0, tb, **hold['ch'], eyes=(6, 14), **NEUT())
    rR = dict(armR=(-0.16, -0.42, 0.845), elbowR=(-0.30, -0.20, 0.88), hdirR=(0.45, -1, 0.15),
              hpalmR=(0.3, 0, -1), fingR=F['table_rest'], tableR=1.0)
    A.key(0, **rR)
    A.key(24, **look(2, 20), eyes=(2, 16))
    A.key(36, armR=(-0.15, -0.43, 0.845), fingR=VP.finger_mix(('table_rest', 0.5), ('claw', 0.5)))
    A.key(52, **look(8, 16), eyes=(6, 14), **rR)
    A.proc(L.breathe(36, 0.7))
    A.proc(drum_proc('R', [40], period=12, amp=22))
    A.proc(ctx.stack_fidget(72))
    A.proc(VP.blink_proc([8, 50]))
    A.tiles.extend(hold['tiles'])
    A.props['cam'] = 'mesa'

    def lift_off(A, f, sides='R', dz=0.08, dy=0.02):
        d = {}
        for S_ in sides:
            d['arm' + S_] = tuple((Vector(SB['arm' + S_]) + Vector((0, dy, dz)))[:])
            d['elbow' + S_] = tuple((Vector(SB['elbow' + S_]) + Vector((0, dy, dz * 0.6)))[:])
            d['hdir' + S_], d['hpalm' + S_] = SB['hdir' + S_], SB['hpalm' + S_]
            d['table' + S_] = 0.0
        A.key(f, **d)

    def rest_back(dy, sides='LR'):
        """Manos apoyadas deslizadas hacia el borde cuando el torso se echa atrás."""
        d = {}
        for S_ in sides:
            d['arm' + S_] = tuple((Vector(SB['arm' + S_]) + Vector((0, dy, 0)))[:])
            d['elbow' + S_] = tuple((Vector(SB['elbow' + S_]) + Vector((0, dy, 0)))[:])
        return d

    # ---------------------------------------------------------------- 14. Celebrar
    A = new('Celebrar_Ganar', 72, False, 'Celebra: puño arriba dos veces y aplaude.', 'Ganar la mano/partida.')
    A.key(0, SB, **NEUT(), **look(0, 4))
    tback = L.seated(spine=(10, -6, 0), clavR=(10, 2), clavL=(4, 4), **look(-4, -10))
    fistup = NH(tback, 'r', arm=('chest', (-0.20, -0.06, 1.86)), elbow=('chest', (-0.40, -0.02, 1.60)),
                palm=('chest', (0.7, -0.6, 0)), flex=5)
    fistmid = NH(tback, 'r', arm=('chest', (-0.27, -0.20, 1.52)), elbow=('chest', (-0.34, -0.10, 1.22)),
                 palm=('chest', (0.7, -0.6, 0)), flex=5)
    fistlow = NH(tback, 'r', arm=('chest', (-0.25, -0.30, 1.46)), elbow=('chest', (-0.34, -0.07, 1.25)),
                 palm=('chest', (0.6, -0.3, -0.6)), flex=5)
    A.key(6, torso(tback), **fistlow, fingR=VP.finger_mix(('fist', 0.6), ('relax', 0.4)),
          **VP.face(('surprise', 0.4), ('smile', 0.6)))
    A.key(12, **fistup, fingR=F['fist'], **FACE(('laugh', 1.0)))
    A.key(17, **fistmid, spine=(14, -4, 0))
    A.key(21, **fistup, spine=(8, -6, 0))
    A.key(26, **fistmid)
    tclap = L.seated(spine=(14, -2, 0), **look(0, 0))
    clapR = NH(tclap, 'r', arm=('chest', (-0.032, -0.40, 1.47)), elbow=('chest', (-0.27, -0.10, 1.40)),
               palm=('chest', (1, 0.05, 0)), exact_palm=True, flex=0)
    clapL = NH(tclap, 'l', arm=('chest', (0.032, -0.40, 1.47)), elbow=('chest', (0.27, -0.10, 1.40)),
               palm=('chest', (-1, 0.05, 0)), exact_palm=True, flex=0)
    openR = NH(tclap, 'r', arm=('chest', (-0.14, -0.38, 1.49)), elbow=('chest', (-0.29, -0.08, 1.41)),
               palm=('chest', (1, 0.05, 0)), exact_palm=True, flex=0)
    openL = NH(tclap, 'l', arm=('chest', (0.14, -0.38, 1.49)), elbow=('chest', (0.29, -0.08, 1.41)),
               palm=('chest', (-1, 0.05, 0)), exact_palm=True, flex=0)
    for d_, s_ in ((clapR, 'R'), (clapL, 'L'), (openR, 'R'), (openL, 'L')):
        d_['fing' + s_] = VP.finger_mix(('flat', 0.8), ('relax', 0.2))
    A.key(32, torso(tclap), **openR, **openL)
    for f in (36, 42, 48):
        A.key(f, **clapR, **clapL, tin=1.4)
        A.key(f + 3, **openR, **openL)
    A.key(58, **VP.face(('smile', 0.8)))
    lift_off(A, 3, 'R')
    lift_off(A, 64, 'LR', dz=0.06)
    A.key(72, SB, **NEUT(), **look(0, 4))
    A.proc(VP.blink_proc([60]))
    A.props['cam'] = 'mesa_frente'

    # ---------------------------------------------------------------- 15. Perder
    A = new('Perder', 76, False, 'Pierde: se lleva las manos a la cabeza y se echa atrás en la silla.',
            'Perder la mano/partida.')
    A.key(0, SB, **NEUT(), **look(0, 4))
    back = L.seated(hips=(0, 0.15, -0.413), hips_rot=(-10, 0, 0), spine=(-2, 0, 0), clavL=(6, -4), clavR=(6, -4),
                    **look(0, -14))
    handsR = NH(back, 'r', arm=('head', (-0.10, 0.005, 1.775)), elbow=('chest', (-0.36, -0.10, 1.60)),
                palm=('head', (0.6, 0, -0.8)), exact_palm=True)
    handsL = NH(back, 'l', arm=('head', (0.10, 0.005, 1.775)), elbow=('chest', (0.36, -0.10, 1.60)),
                palm=('head', (-0.6, 0, -0.8)), exact_palm=True)
    handsR['fingR'] = handsL['fingL'] = VP.finger_mix(('flat', 0.5), ('relax', 0.5))
    A.key(8, **VP.face(('surprise', 0.8)))
    A.key(16, torso(back), **handsR, **handsL, **FACE(('dismay', 1.0)))
    A.key(30, **look(8, -10))
    A.key(40, **look(-8, -12), **FACE(('dismay', 0.6), ('sad', 0.6)))
    A.key(50, **look(4, -8))
    A.key(54, **handsR, **handsL)
    A.key(64, torso(SB), **pick(SB, 'R'), **pick(SB, 'L'), **FACE(('sad', 0.7)))
    A.key(76, SB, **look(0, 4), **FACE(('sad', 0.3)))
    A.proc(VP.blink_proc([34, 60]))
    A.props['cam'] = 'mesa_frente'

    # ---------------------------------------------------------------- 16. Pensar
    A = new('Pensar', 96, True, 'Piensa: mano en la barbilla, tamborilea con la otra mano (bucle).',
            'Pensar la jugada (bucle).')
    tb = L.seated(spine=(30, -3, 0), clavR=(8, 6), **look(4, 0, 4))
    chin = NH(tb, 'r', arm=('head', (-0.03, -0.125, 1.50)), elbow=(-0.15, -0.37, 0.885),
              palm=('head', (0.5, 0.85, 0.2)), flex=-25)
    chin.update(fingR=VP.finger_mix(('fist', 0.6), ('relax', 0.4)), autoR=3.0)
    A.key(0, tb, **chin, **FACE(('think', 1.0)), eyes=(10, -10),
          fingL=VP.finger_mix(('table_rest', 0.3), ('claw', 0.7)))
    A.key(30, **look(8, -2, 6), eyes=(14, -14))
    A.key(60, **look(-2, 2, 2), eyes=(-6, -6), **FACE(('think', 0.8), browInnerUp=0.2))
    A.proc(drum_proc('L', [10, 22, 34, 58, 70, 82]))
    A.proc(L.breathe(48, 0.8))
    A.proc(VP.blink_proc([18, 76]))
    A.props['cam'] = 'mesa_frente'

    # ---------------------------------------------------------------- 17. Saludar
    A = new('Saludar', 48, False, 'Saluda con la mano abierta.', 'Saludo al entrar/llegar jugadores.')
    A.key(0, SB, **NEUT(), **look(0, 4))
    tw = L.seated(spine=(14, -6, 0), clavR=(10, 0), **look(-6, -4, -5))
    wave = NH(tw, 'r', arm=('chest', (-0.34, -0.17, 1.42)), elbow=('chest', (-0.43, -0.04, 1.19)),
              palm=('chest', (0.15, -1, 0)), exact_palm=True)
    wave['fingR'] = F['open']
    A.key(8, torso(tw), **wave, **FACE(('smile', 1.0), browInnerUp=0.3), **rest_back(0.03, 'L'))
    for i, f in enumerate((13, 18, 23, 28, 33)):
        sgn = 1 if i % 2 == 0 else -1
        w2 = NH(tw, 'r', arm=('chest', (-0.34 + 0.04 * sgn, -0.17, 1.42)), elbow=wave['elbowR'],
                palm=('chest', (0.15, -1, 0)), exact_palm=True, dev=-22 * sgn)
        A.key(f, **w2)
    A.key(36, **wave)
    lift_off(A, 3, 'R')
    lift_off(A, 42, 'R', dz=0.06)
    A.key(48, SB, **NEUT(), **look(0, 4))
    A.proc(VP.blink_proc([40]))
    A.props['cam'] = 'mesa_frente'

    # ---------------------------------------------------------------- 18. Señalar
    A = new('Senalar', 40, False, 'Señala con el índice hacia el centro/otro jugador.', 'Indicar jugada o jugador.')
    A.key(0, SB, **NEUT(), **look(0, 4))
    tp = L.seated(spine=(20, 8, 0), clavR=(6, 12), **look(14, 0))
    point = NH(tp, 'r', arm=(-0.04, -0.47, 1.02), elbow=(-0.24, -0.27, 0.95), palm=(0.25, 0.1, -1), flex=-8)
    point['fingR'] = F['point']
    A.key(9, torso(tp), **point, **FACE(('determined', 0.6)), eyes=(10, 0))
    A.key(13, armR=(-0.035, -0.49, 1.025))
    A.key(26, **point, **VP.face(mouthSmileLeft=0.3))
    A.key(40, SB, **NEUT(), **look(0, 4), eyes=(0, 0))
    A.proc(VP.blink_proc([30]))
    A.props['cam'] = 'mesa_frente'

    # ---------------------------------------------------------------- 19. Pulgar arriba
    A = new('Pulgar_Arriba', 40, False, 'Pulgar arriba con sonrisa y asentimiento.', 'Aprobar jugada del compañero.')
    A.key(0, SB, **NEUT(), **look(0, 4))
    tt = L.seated(spine=(18, -2, 0), **look(0, 4))
    tu = NH(tt, 'r', arm=('chest', (-0.16, -0.38, 1.50)), elbow=('chest', (-0.32, -0.11, 1.35)),
            palm=('chest', (1, 0.15, 0)), exact_palm=True)
    tu['fingR'] = F['thumbup']
    A.key(9, torso(tt), **tu, **FACE(('smile', 1.0)))
    A.key(14, **look(0, 12))
    A.key(19, **look(0, -2))
    A.key(24, **look(0, 10))
    A.key(28, **tu)
    lift_off(A, 3, 'R')
    lift_off(A, 34, 'R', dz=0.06)
    A.key(40, SB, **NEUT(), **look(0, 4))
    A.props['cam'] = 'mesa_frente'

    # ---------------------------------------------------------------- 20. Aplaudir
    A = new('Aplaudir', 48, False, 'Aplaude cuatro veces.', 'Felicitar a otro jugador.')
    A.key(0, SB, **NEUT(), **look(0, 4))
    lift_off(A, 3, 'LR')
    A.key(8, torso(tclap), **openR, **openL, **FACE(('smile', 0.9)))
    lift_off(A, 41, 'LR', dz=0.06)
    for f in (12, 18, 24, 30):
        A.key(f, **clapR, **clapL, tin=1.4)
        A.key(f + 3, **openR, **openL)
    A.key(48, SB, **NEUT(), **look(0, 4))
    A.proc(VP.blink_proc([22]))
    A.props['cam'] = 'mesa_frente'

    # ---------------------------------------------------------------- 21. Reír
    A = new('Reir', 60, False, 'Se ríe: hombros y cabeza rebotan, cara de risa.', 'Reacción a una buena jugada/chiste.')
    A.key(0, SB, **NEUT(), **look(0, 4))
    tl = L.seated(spine=(12, 0, 0), **look(2, -12))
    A.key(8, torso(tl), **FACE(('laugh', 1.0)), **rest_back(0.05))
    A.key(30, spine=(22, 0, 0), **look(-2, 8), **rest_back(0.0))
    A.key(44, spine=(14, 0, 0), **look(0, -6), **rest_back(0.04))
    A.key(52, **FACE(('smile', 0.7)))
    A.key(60, SB, **NEUT(), **look(0, 4))

    def laugh_bounce(f, P, ev):
        env = min(1, max(0, (f - 6) / 4)) * min(1, max(0, (52 - f) / 6))
        b = math.sin(2 * math.pi * f / 6.0) * env
        P['clavL'] = P['clavL'] + np.array([3.0 * b, 0])
        P['clavR'] = P['clavR'] + np.array([3.0 * b, 0])
        P['spine'] = P['spine'] + np.array([1.5 * b, 0, 0])
        P['head'] = P['head'] + np.array([-2.0 * b, 0, 0])
        P['face.jawOpen'] = float(np.clip(P.get('face.jawOpen', 0) + 0.15 * b, 0, 1))
    A.proc(laugh_bounce)
    A.props['cam'] = 'mesa_frente'

    # ---------------------------------------------------------------- 22. Enojado
    A = new('Enojado', 50, False, 'Enojado: golpe con la palma abierta en la mesa y cara de enojo.',
            'Perder una jugada clave / protestar.')
    A.key(0, SB, **NEUT(), **look(0, 4))
    ta = L.seated(spine=(14, -6, 0), clavR=(8, 4), **look(-4, -6))
    slap_up = NH(ta, 'r', arm=(-0.12, -0.40, 1.04), elbow=(-0.30, -0.18, 1.0), palm=(0.15, 0, -1), exact_palm=True)
    slap_up['fingR'] = F['flat']
    ts = L.seated(spine=(30, -3, 0), **look(-4, 10))
    slap = NH(ts, 'r', arm=(-0.12, -0.45, 0.84), elbow=(-0.27, -0.24, 0.88), palm=(0.1, 0, -1), exact_palm=True)
    slap.update(fingR=F['flat'], tableR=1.0)
    A.key(9, torso(ta), **slap_up, **FACE(('angry', 1.0)), **rest_back(0.03, 'L'))
    A.key(13, torso(ts), **slap, tin=1.7, **rest_back(0.0, 'L'))
    A.key(14, **FACE(('shout', 1.0)))
    A.key(22, **slap, **look(6, 6))
    A.key(28, **look(-8, 6))
    A.key(34, **look(4, 4), **FACE(('angry', 0.8)))
    A.key(50, SB, **NEUT(), **look(0, 4))
    A.props['cam'] = 'mesa_frente'

    # ================================================================ DE PIE
    ST = L.stand()
    # ---------------------------------------------------------------- 1. Idle de pie
    A = new('Idle_De_Pie', 192, True, 'De pie: respira, cambia el peso de pierna, dedos relajados.',
            'Espera de pie / lobby (bucle).')
    A.key(0, ST, **NEUT(), eyes=(0, 0))
    A.key(48, hips=(0.022, 0.0, -0.012), hips_rot=(0, 2, -3.5), spine=(1, -2, 2.5), head=(0, 4, 1.5), neck=(0, 0, 0.5),
          kneeR=(-0.25, -1, 0))
    A.key(96, hips=(0, 0, -0.005), hips_rot=(0, 0, 0), spine=(0, 0, 0), head=(2, 0, 0), eyes=(-6, 2))
    A.key(144, hips=(-0.022, 0.0, -0.012), hips_rot=(0, -2, 3.5), spine=(1, 2, -2.5), head=(-1, -5, -1.5),
          kneeL=(0.25, -1, 0), eyes=(4, 0))
    A.proc(L.breathe(96, 1.2))
    A.proc(L.finger_fidget(192, 3.0))
    A.proc(VP.blink_proc([30, 118, 170]))
    A.props['cam'] = 'pie'
    A.props['nochair'] = True

    # ---------------------------------------------------------------- 2. Caminar
    ctx.walk(new('Caminar', 28, True, 'Ciclo de caminar en el sitio (in place), 0.83 m/s.',
                 'Desplazamiento (el juego mueve el personaje).'))

    # ---------------------------------------------------------------- 3/4. Sentarse / Levantarse
    ctx.sit(new('Sentarse', 100, False, 'De pie frente a la silla: se sienta y se arrima a la mesa con la silla.',
                'Llegar a la mesa.'), SB, ST)
    ctx.stand_up(new('Levantarse', 90, False, 'Se separa de la mesa con la silla y se levanta.',
                     'Salir de la mesa.'), SB, ST)

    # ---------------------------------------------------------------- 23. Prueba rango completo
    ctx.range_test(new('Prueba_Rango_Completo', 1680, False,
                       'Demostración: mueve cada parte una por una y luego todo junto.',
                       'Solo pruebas de rig (no usar en juego).'), ST)
    return anims
