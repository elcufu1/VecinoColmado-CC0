"""Definición de las animaciones de VecinoColmado (24 fps)."""
import math
import numpy as np
from mathutils import Vector, Matrix

import vc_core as C
import vc_pose as VP
import vc_lib as L
import vc_scene as S
import vc_domino as DOM
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

    # ---------------------------------------------------------------- PARTIDA (dominó dominicano, por parejas)
    NH = lambda base, side, **kw: VP.natural_hand(ev, base, side, **kw)  # noqa: E731
    EST = DOM.partida()
    SLOT = {t: i for i, t in enumerate(DOM.FILA)}
    MOVES_V = [s for s in EST if s['player'] == 0]
    M_CERCA, M_LEJOS = 4, 8
    I_CERCA, I_LEJOS = SLOT[EST[M_CERCA]['tile']], SLOT[EST[M_LEJOS]['tile']]
    TOP_Z = S.TABLE_TOP + S.TILE[1] / 2
    T_cerca = VP.stand_matrix(VP.ROW_X[I_CERCA], VP.ROW_Y)
    T_lejos = VP.stand_matrix(VP.ROW_X[I_LEJOS], VP.ROW_Y)
    th = L.seated(spine=(20, -2, 0), clavR=(4, 8), **look(-6, 10))
    tb_c = L.seated(spine=(24, -5, 0), clavR=(4, 10), **look(-8, 14))
    tb_l = L.seated(hips=(0, 0.125, -0.405), spine=(28, 4, 0), clavR=(4, 14), clavL=(2, 2), **look(12, 16))
    for d_ in (tb_c, tb_l, th):
        d_['poleR'] = (-0.7, 0.4, -0.6)
        d_['autoR'] = 0.6
    obst_c = VP.row_obstacles((I_CERCA,))
    obst_l = VP.row_obstacles((I_LEJOS,))
    _, ALPHA, OFF, ginfo = VP.best_vgrip(ev, 'r', [(tb_c, T_cerca, obst_c), (tb_l, T_lejos, obst_l)])
    ctx.log('Agarrar_Ficha_Cerca', 'agarre', dict(ginfo[0], alpha=ALPHA))
    ctx.log('Agarrar_Ficha_Lejos', 'agarre', dict(ginfo[1], alpha=ALPHA))
    HT = lambda T, fk='pinch_v': VP.hand_for_tile(rig, 'r', T, OFF, fk)  # noqa: E731

    def moved(T, dx=0.0, dy=0.0, dz=0.0):
        M = T.copy()
        M.translation += Vector((dx, dy, dz))
        return M

    hbest = None
    for tip_h in (-20, -10, 0, 10):
        for yaw_h in (-30, -15, 0, 15):
            Th_ = VP.stand_matrix(-0.10, -0.31, TOP_Z + 0.085, tip=tip_h, yaw=yaw_h)
            c_, info_, _ = VP.grip_cost(ev, th, 'r', HT(Th_), obst_c)
            if hbest is None or c_ < hbest[0]:
                hbest = (c_, Th_, info_, tip_h, yaw_h)
    T_hold = hbest[1]
    ctx.log('Agarrar_Ficha_Cerca', 'sostener', dict(hbest[2], tip=hbest[3], yaw=hbest[4]))
    HOLD = HT(T_hold)
    HOLD, _ = with_elbow(ev, th, HOLD, 'r')
    ctx.HOLD, ctx.HOLD_T, ctx.OFF = HOLD, th, OFF

    # torsos para soltar: cerca (sin inclinarse) y lejos (cadera adelante, la izquierda apoyada)
    tb_n = L.seated(spine=(27, -4, 0), clavR=(4, 12), **look(-6, 16))
    tb_f = L.seated(hips=(0, 0.11, -0.31), hips_rot=(8, 0, 0), spine=(44, -5, 0), clavR=(3, 18), clavL=(8, 4),
                    **look(-4, 0))
    tb_n['poleR'] = (-0.7, 0.4, -0.6)
    tb_f['poleR'] = (-0.8, 0.3, -0.5)
    tb_n['autoR'] = tb_f['autoR'] = 0.6
    tmid_f = L.seated(hips=(0, 0.12, -0.38), hips_rot=(4, 0, 0), spine=(36, -3, 0), clavR=(3, 14), **look(-4, 8))
    supL = dict(armL=(0.30, -0.45, 0.85), elbowL=(0.40, -0.22, 0.90), hdirL=(-0.25, -1, 0.1), hpalmL=(-0.1, 0, -1),
                fingL=F['flat'], tableL=1.0)

    # torsos que se inclinan hacia su derecha (huecos del extremo derecho junto al borde del paño)
    TB_R = []
    for hx_, pitch in ((-0.06, 40), (-0.08, 45)):
        for bend in (-10, -15):
            t_ = L.seated(hips=(hx_, 0.12, -0.39), spine=(pitch, 0, bend), clavR=(4, 18), **look(-14, 14))
            t_['poleR'] = (-0.8, 0.3, -0.5)
            t_['autoR'] = 0.6
            TB_R.append(t_)

    def chain_u(pl):
        return pl['axis'] if pl['kind'] in ('doble', 'salida') else pl['d']

    def chain_rects(mesa):
        return [VP.chain_obstacle(p['c'], p['axis']) for p in mesa.placed]

    def is_far(rp):
        return rp[1] < -0.60

    # Cómo se suelta cada ficha del Vecino:
    #  - doble / salida (eje largo en Y): de pie sobre su canto corto, cae hacia el fondo (sin girar la muñeca);
    #  - ficha a lo largo de X: la gira 90° entre las yemas mientras la lleva, la apoya APAISADA sobre su canto
    #    largo, cara hacia él, y cae hacia el fondo. Así la muñeca nunca gira 90° para alinear la ficha.
    # Se elige el sentido u (y el giro en la pinza) con la muñeca más cómoda; la cara siempre queda arriba.
    U, REL = {}, {}
    for st in MOVES_V:
        if st['placed'] is None:
            continue
        pl = st['placed']
        rects = chain_rects(st['before'])
        land = abs(pl['axis'][0]) > 0.5
        best = None
        for sg in (1, -1):
            u = (sg * chain_u(pl)[0], sg * chain_u(pl)[1])
            for opt in ((0, 1) if land else (None,)):
                pen = 0.0
                for lift in (0.0, S.TILE[2] + 0.0008):
                    if land:
                        Mr, Mf, piv = VP.land_release(pl['c'], u, lift=lift)
                        sc_, th_, Pp_ = VP.land_grip(rig, OFF, piv)[opt]
                        roll = (th_, Pp_)
                        # agarrar por el extremo del lado del meñique: posible, pero la ficha roza los dedos
                        pen = 0.0 if sc_ > 0 else 40.0
                        Tv = Mr @ VP.roll_Q(*roll).inverted()
                    else:
                        Mr, Mf, piv = VP.slot_release(pl['c'], u, lift=lift), None, None
                        Tv, roll = Mr, None
                    if not VP.standing_hits(Mr, rects):
                        break
                rp = (Mr.translation.x, Mr.translation.y)
                tb0 = tb_f if is_far(rp) else tb_n
                for tb in [tb0] + (TB_R if rp[0] < -0.30 else []):
                    c, info, _ = VP.grip_cost(ev, tb, 'r', HT(Tv), VP.row_obstacles() + rects)
                    c += pen + (0.0 if tb is tb0 else 3.0)
                    if best is None or c < best[0]:
                        best = (c, u, dict(M=Mr, Tv=Tv, lift=lift, land=(Mf, piv) if land else None, roll=roll,
                                           tb=tb), info)
        U[st['i']] = best[1]
        REL[st['i']] = best[2]
        rl = best[2]['roll']
        ctx.log('Partida', f'jugada_{st["i"]}', dict(best[3], ux=best[1][0], uy=best[1][1], lift=best[2]['lift'],
                                                     roll=rl[0] if rl else 0, cx=pl['c'][0], cy=pl['c'][1]))
    ROWVALS = {}
    for st in MOVES_V:
        if st['placed'] is not None:
            ROWVALS[f'Fila{SLOT[st["tile"]] + 1}'] = DOM.tile_halves(st['placed'], U[st['i']])

    def chain_u_final(k, pl):
        for st in MOVES_V:
            if st['placed'] is pl or (st['placed'] is not None and st['placed']['tile'] == pl['tile']):
                return U[st['i']]
        return chain_u(pl)

    def vals_of(A):
        return A.props.setdefault('vals', {})

    def add_row(A, skip=(), mesa=None):
        """Fila del Vecino (fichas paradas que le quedan) + cadena de la mesa (estado antes de su jugada)."""
        for i, M in VP.row_tiles(skip):
            n = f'Fila{i + 1}'
            A.tiles.append(dict(name=n, side='r', start=('table', M)))
            vals_of(A)[n] = ROWVALS.get(n)
        o = VP.row_obstacles(skip)
        if mesa is not None:
            for k, pl in enumerate(mesa.placed):
                n = f'Cadena{k + 1:02d}'
                u = chain_u_final(k, pl)
                A.tiles.append(dict(name=n, side='r', start=('table', VP.chain_matrix(pl['c'], u))))
                vals_of(A)[n] = DOM.tile_halves(pl, u)
            o = o + chain_rects(mesa)
            A.props['mesa'] = [dict(tile=p['tile'], c=p['c'], kind=p['kind'], side=p['side']) for p in mesa.placed]
        A.obstacles = lambda f, o=o: o

    def played_before(i):
        return tuple(SLOT[s['tile']] for s in MOVES_V if s['i'] < i and s['tile'] is not None)

    def ficha(A):
        return next(t for t in A.tiles if t['name'] == 'Ficha')

    def grab_keys(A, T, tb, f_hover, f_grab, far=False, f_end=None):
        ch = HT(T)
        ch, _ = with_elbow(ev, tb, ch, 'r')
        chh = HT(moved(T, dz=0.035), 'pinch_v_open')
        chh['elbowR'] = tuple((Vector(ch['elbowR']) + Vector((0, 0, 0.03)))[:])
        lift = HT(moved(T, dy=0.01, dz=0.05))
        lift['elbowR'] = tuple((Vector(ch['elbowR']) + Vector((0, 0.01, 0.04)))[:])
        A.key(0, SB, **look(0, 4), eyes=(0, 10), **NEUT())
        A.key(3, eyes=(-8 if not far else 8, 16))
        if far:
            mid = (Vector(SB['armR']) + Vector(chh['armR'])) / 2 + Vector((0, 0, 0.10))
            A.key(3, armR=tuple((Vector(SB['armR']) + Vector((0.02, 0.0, 0.07)))[:]), tableR=0.0)
            A.key(f_hover // 2 + 1, armR=tuple(mid[:]), tableR=0.0, fingR=F['pinch_v_open'])
            # la mano izquierda se aparta hacia fuera para dejar pasar el brazo derecho
            A.key(f_hover - 2, armL=(0.33, -0.40, 0.85), elbowL=(0.42, -0.16, 0.88), hdirL=(-0.2, -1, 0.1),
                  hpalmL=(-0.2, 0, -1), fingL=F['table_rest'], tableL=1.0)
            A.key(f_end - 4, armL=(0.33, -0.40, 0.85), elbowL=(0.42, -0.16, 0.88))
            A.key(f_end, armL=SB['armL'], elbowL=SB['elbowL'], hdirL=SB['hdirL'], hpalmL=SB['hpalmL'])
        A.key(f_hover, torso(tb), **chh)
        A.key(f_grab, torso(tb), **ch, **VP.face(('focus', 1.0)))
        A.key(f_grab + 1, **ch)
        A.key(f_grab + 4, **lift)
        A.tiles.append(dict(name='Ficha', side='r', start=('table', T), grab=f_grab))

    def agarrar(name, move_i, T, tb, frames, f_hover, f_grab, far=False):
        st = EST[move_i]
        idx = SLOT[st['tile']]
        A = new(name, frames, False,
                f'Agarra la ficha parada {st["tile"][0]}-{st["tile"][1]} '
                f'{"del otro extremo de su fila (hueco " + str(idx) + ")" if far else "de su fila (hueco " + str(idx) + ")"} '
                'con pinza limpia pulgar-índice (pulgar en la cara, índice detrás) y la levanta mirándola.',
                'Tomar una ficha propia para jugarla (la fila sigue en su sitio, con el hueco).')
        grab_keys(A, T, tb, f_hover, f_grab, far, frames)
        A.key(frames, torso(th), **HOLD, **look(-6, 10), eyes=(-3, 12), **NEUT())
        vals_of(A)['Ficha'] = ROWVALS[f'Fila{idx + 1}']
        add_row(A, played_before(move_i) + (idx,), st['before'])
        A.proc(L.breathe(48, 0.5))
        A.props['cam'] = 'mesa'
        A.props['jugada'] = move_i
        return A

    agarrar('Agarrar_Ficha_Cerca', M_CERCA, T_cerca, tb_c, 22, 7, 11)
    agarrar('Agarrar_Ficha_Lejos', M_LEJOS, T_lejos, tb_l, 28, 10, 15, far=True)

    def blend_T(Ta, Tb, k, pos):
        q = Ta.to_quaternion().slerp(Tb.to_quaternion(), k)
        M = q.to_matrix().to_4x4()
        M.translation = Vector(pos)
        return M

    def place_keys(A, move_i, T_from, f_mid, f_pre, f_rel, tin=None, fall=5, rise=0.06):
        """Lleva la ficha parada sobre su hueco exacto, la apoya de pie inclinada hacia u (sobre el paño o sobre el
        borde de la ficha anterior), la suelta y cae cara arriba justo en el hueco: el número que casa toca el igual."""
        R_ = REL[move_i]
        Tr, lift = R_['Tv'], R_['lift']
        tb = R_['tb']
        u = U[move_i]
        Tp = moved(Tr, dy=0.004, dz=0.03)
        mid = (Vector(T_from.translation) + Vector(Tp.translation)) / 2 + Vector((0, 0, rise))
        Tm = blend_T(T_from, Tp, 0.5, mid)
        chm, chp, chr_ = HT(Tm), HT(Tp), HT(Tr)
        chr_, _ = with_elbow(ev, tb, chr_, 'r')
        ctx.log(A.name, 'suelta', dict(VP.grip_cost(ev, tb, 'r', chr_, A.obstacles(0))[1],
                                       lift=lift, roll=R_['roll'][0] if R_['roll'] else 0))
        chp['elbowR'] = tuple((Vector(chr_['elbowR']) + Vector((0, 0.01, 0.02)))[:])
        chm['elbowR'] = tuple((Vector(chr_['elbowR']) + Vector((0, 0.05, 0.05)))[:])
        far = tb is tb_f
        if far:
            A.key(max(1, f_mid - 2), torso(tmid_f), **supL, eyes=(-4, 6))
            A.key(f_mid, **chm)
        else:
            A.key(f_mid, torso(tb), **chm)
        A.key(f_pre, **chp)
        kw = dict(tin=tin) if tin else {}
        A.key(f_rel, torso(tb), **chr_, **kw)
        A.key(f_rel + 1, armR=Vector(chr_['armR']) + Vector((0, 0.008, 0.03)), fingR=F['pinch_v_open'])
        if far:
            A.key(f_rel, **supL, **VP.face(('determined', 0.8)))
        t = ficha(A)
        t['release'] = f_rel
        t['fall'] = fall
        if R_['land'] is not None:
            t['land'] = R_['land']
            t['roll'] = (max(1, f_mid - 3), f_pre) + tuple(R_['roll'])
        A.props['slot'] = dict(c=[round(v, 4) for v in EST[move_i]['placed']['c']], u=list(u),
                               axis=list(EST[move_i]['placed']['axis']), kind=EST[move_i]['placed']['kind'],
                               side=EST[move_i]['side'], lift=lift,
                               suelta='apaisada' if R_['land'] is not None else 'de_pie')
        return chr_, far

    def retreat(A, chr_, far, f0, frames):
        if far:
            A.key(f0 + 5, torso(tmid_f), armR=Vector(chr_['armR']) + Vector((0.0, 0.12, 0.07)),
                  fingR=VP.finger_mix(('pinch_v_open', 0.5), ('relax', 0.5)),
                  elbowR=Vector(chr_['elbowR']) + Vector((0, 0.08, 0.03)))
            A.key(f0 + 8, **supL)
            A.key(f0 + 13, torso(SB), armL=SB['armL'], elbowL=SB['elbowL'], hdirL=SB['hdirL'], hpalmL=SB['hpalmL'],
                  fingL=SB['fingL'], **NEUT())
        else:
            A.key(f0 + 4, armR=Vector(chr_['armR']) + Vector((0.01, 0.05, 0.06)),
                  fingR=VP.finger_mix(('pinch_v_open', 0.5), ('relax', 0.5)), **VP.face(('determined', 0.6)))
        # al volver, el antebrazo pasa por encima de las fichas paradas que le quedan
        fa = frames - 6 if far else f0 + 4 + max(2, (frames - f0 - 4) // 2)
        pa = (Vector(chr_['armR']) + Vector(SB['armR'])) / 2 + Vector((0, 0, 0.13))
        A.key(fa, armR=tuple(pa[:]), elbowR=tuple((Vector(SB['elbowR']) + Vector((0, -0.02, 0.10)))[:]),
              tableR=0.0)
        A.key(frames, SB, **look(0, 4), eyes=(0, 10), **NEUT())

    def jugar(name, move_i, desc, use, frames=None):
        st = EST[move_i]
        idx = SLOT[st['tile']]
        far = is_far(tuple(REL[move_i]['M'].translation.xy))
        A = new(name, frames or (30 if far else 22), False, desc, use)
        A.key(0, ctx.HOLD_T, **ctx.HOLD, eyes=(-3, 12), **NEUT())
        A.tiles.append(dict(name='Ficha', side='r', start=('hand', OFF), release=None))
        vals_of(A)['Ficha'] = ROWVALS[f'Fila{idx + 1}']
        add_row(A, played_before(move_i) + (idx,), st['before'])
        f_mid, f_pre, f_rel = (7, 10, 12) if far else (4, 7, 9)
        chr_, far = place_keys(A, move_i, T_hold, f_mid, f_pre, f_rel)
        retreat(A, chr_, far, f_rel, A.frames)
        A.proc(L.breathe(48, 0.5))
        A.props['cam'] = 'mesa_lejos' if far else 'mesa'
        A.props['jugada'] = move_i
        return A

    def lado(st):
        return 'derecho (D)' if st['side'] == 'D' else 'izquierdo (I)'

    def desc_jugada(i, extra=''):
        st = EST[i]
        pl = st['placed']
        b = st['before'].ends
        e = b['D'] if st['side'] == 'D' else b['I']
        como = ('la gira 90° entre las yemas mientras la lleva, la apoya apaisada (sobre su canto largo) junto al '
                'hueco y cae cara arriba en el hueco exacto.' if REL[i]['land'] is not None else
                'la apoya de pie junto al hueco y cae cara arriba en el hueco exacto.')
        return (f'Juega {st["tile"][0]}-{st["tile"][1]} en el extremo {lado(st)} que pedía {e}: '
                f'el {pl["match"]} toca al {pl["match"]} de la cadena{extra}. Lleva la ficha parada, {como}')

    # ---------------------------------------------------------------- Salida
    A = new('Salida_Doble_Seis', 46, False,
            'Salida: agarra el doble seis parado del centro de su fila con pinza y lo pone atravesado en el centro '
            'de la mesa.', 'Primera jugada de la primera mano (quien tiene el doble seis sale).')
    st = EST[0]
    T_s = VP.stand_matrix(VP.ROW_X[SLOT[(6, 6)]], VP.ROW_Y)
    grab_keys(A, T_s, tb_c, 7, 11, False, 46)
    vals_of(A)['Ficha'] = ROWVALS[f'Fila{SLOT[(6, 6)] + 1}']
    add_row(A, (SLOT[(6, 6)],), st['before'])
    chr_, far = place_keys(A, 0, moved(T_s, dy=0.01, dz=0.05), 22, 26, 29, rise=0.04)
    retreat(A, chr_, far, 29, 46)
    A.proc(L.breathe(48, 0.5))
    A.props['cam'] = 'mesa_lejos'
    A.props['jugada'] = 0

    # ---------------------------------------------------------------- Colocar (variantes por extremo y distancia)
    jugar('Colocar_Doble', 4, desc_jugada(4, '; el doble va atravesado (perpendicular a la cadena)'),
          'Jugar un doble: siempre atravesado (aquí por el extremo derecho, hueco lejano).')
    jugar('Colocar_Izq_Lejos', 8, desc_jugada(8), 'Jugar por el extremo izquierdo, hueco lejano.')
    jugar('Colocar_Esquina', 12, desc_jugada(12, '; no cabe recta y la cadena dobla la esquina'),
          'Jugar cuando la cadena llega al borde y dobla (ficha de esquina, en L).')
    jugar('Colocar_Der_Cerca', 16, desc_jugada(16), 'Jugar por el extremo derecho, hueco cercano a su derecha.')
    jugar('Colocar_Der_Frente', 24, desc_jugada(24), 'Jugar por el extremo derecho cuando la cadena ya dio la '
          'vuelta y pasa delante de él (hueco cercano, frente a su izquierda).')

    # ---------------------------------------------------------------- Dominó (golpe + celebración)
    A = new('Domino_Golpe', 64, False,
            f'Dominó: levanta la última ficha ({EST[28]["tile"][0]}-{EST[28]["tile"][1]}), la planta de golpe en su '
            'hueco exacto y celebra con el puño.',
            'Cuando juega su última ficha (se "domina"). Al terminar, el juego cuenta los puntos.')
    st = EST[28]
    A.key(0, ctx.HOLD_T, **ctx.HOLD, eyes=(-3, 12), **NEUT())
    A.tiles.append(dict(name='Ficha', side='r', start=('hand', OFF), release=None))
    vals_of(A)['Ficha'] = ROWVALS[f'Fila{SLOT[st["tile"]] + 1}']
    add_row(A, played_before(28) + (SLOT[st['tile']],), st['before'])
    tup = L.seated(spine=(10, -8, 0), clavR=(10, 4), **look(-4, -4))
    tup['poleR'] = (-0.7, 0.4, -0.6)
    Tr = REL[28]['Tv']
    # la mano izquierda descansa justo donde cae la última ficha: se aparta a un lado del paño antes del golpe
    asideL = dict(armL=(0.40, -0.35, 0.85), elbowL=(0.47, -0.11, 0.88), hdirL=(-0.12, -1, 0.05),
                  hpalmL=(-0.15, 0, -1), fingL=F['table_rest'], tableL=1.0)
    A.key(6, **asideL)
    Tu = blend_T(T_hold, Tr, 0.6, (Tr.translation.x + 0.02, Tr.translation.y + 0.16, 1.12))
    chU = HT(Tu)
    chU['elbowR'] = (-0.36, -0.10, 1.00)
    A.key(9, torso(tup), **chU, **VP.face(('determined', 1.0)), eyes=(-4, 12))
    A.key(11, armR=Vector(chU['armR']) + Vector((0, -0.01, 0.02)))
    chr_, _ = place_keys(A, 28, Tu, 12, 13, 15, tin=1.6, fall=4, rise=0.0)
    A.key(16, **VP.face(('shout', 1.0)), spine=(30, -4, 0))
    A.key(22, armR=Vector(chr_['armR']) + Vector((0, 0.006, 0.02)), fingR=F['pinch_v_open'])
    tback = L.seated(spine=(10, -6, 0), clavR=(10, 2), clavL=(4, 4), **look(-4, -10))
    fistup = NH(tback, 'r', arm=('chest', (-0.20, -0.06, 1.86)), elbow=('chest', (-0.40, -0.02, 1.60)),
                palm=('chest', (0.7, -0.6, 0)), flex=5)
    fistmid = NH(tback, 'r', arm=('chest', (-0.27, -0.20, 1.52)), elbow=('chest', (-0.34, -0.10, 1.22)),
                 palm=('chest', (0.7, -0.6, 0)), flex=5)
    A.key(30, torso(tback), **fistmid, fingR=VP.finger_mix(('fist', 0.6), ('relax', 0.4)),
          **FACE(('laugh', 1.0)))
    A.key(36, **fistup, fingR=F['fist'])
    A.key(41, **fistmid)
    A.key(46, **fistup, **VP.face(('smile', 0.9)))
    A.key(64, SB, **asideL, **look(0, 4), eyes=(0, 10), **NEUT())
    A.proc(VP.blink_proc([52]))
    A.props['cam'] = 'mesa'
    A.props['jugada'] = 28

    # ---------------------------------------------------------------- Capicúa (cinemática)
    st = EST[28]
    assert st['capicua'], 'la última jugada del Vecino debe ser capicúa'
    A = new('Capicua_Golpe_Celebrar', 120, False,
            f'¡CAPICÚA! Su última ficha ({st["tile"][0]}-{st["tile"][1]}) casa en los dos extremos '
            f'(D pide {st["before"].ends["D"]}, I pide {st["before"].ends["I"]}): la levanta alto mostrándola, '
            'la sostiene un instante, la planta de un golpe fuerte en su hueco exacto y celebra a lo grande '
            '(dos puños arriba, grito, señala la ficha).',
            'Ganar dominando con capicúa (momento épico; ver eventos de cámara lenta, texto, partículas y sonido).')
    A.key(0, ctx.HOLD_T, **ctx.HOLD, eyes=(-3, 12), **NEUT())
    A.tiles.append(dict(name='Ficha', side='r', start=('hand', OFF), release=None))
    vals_of(A)['Ficha'] = ROWVALS[f'Fila{SLOT[st["tile"]] + 1}']
    add_row(A, played_before(28) + (SLOT[st['tile']],), st['before'])
    Tr = REL[28]['Tv']
    tshow = L.seated(spine=(8, -10, 0), clavR=(12, 4), **look(-10, -8))
    tshow['poleR'] = (-0.7, 0.4, -0.6)
    Tshow = blend_T(T_hold, Tr, 0.3, (Tr.translation.x - 0.04, Tr.translation.y + 0.20, 1.27))
    chS = HT(Tshow)
    chS['elbowR'] = (-0.38, -0.12, 1.12)
    Tup = blend_T(T_hold, Tr, 0.65, (Tr.translation.x + 0.01, Tr.translation.y + 0.15, 1.20))
    chU = HT(Tup)
    chU['elbowR'] = (-0.36, -0.08, 1.04)
    fistL0 = NH(L.seated(), 'l', arm=('chest', (0.16, -0.30, 1.30)), elbow=('chest', (0.34, -0.10, 1.14)),
                palm=('chest', (-0.7, -0.6, 0)), flex=5)
    fistL0['fingL'] = F['fist']
    A.key(4, armL=tuple((Vector(SB['armL']) + Vector((0, 0.03, 0.07)))[:]),
          elbowL=tuple((Vector(SB['elbowL']) + Vector((0, 0.0, 0.05)))[:]), tableL=0.0)
    A.key(6, torso(tshow), **chS, **VP.face(('determined', 0.8), ('smile', 0.3)), eyes=(-6, -4))
    A.key(10, **fistL0)
    A.key(14, **chS, **VP.face(('determined', 1.0)), eyes=(-2, 6))
    A.key(21, torso(tup), **chU, eyes=(-4, 14))
    A.key(23, armR=Vector(chU['armR']) + Vector((0, -0.005, 0.03)))
    chr_, _ = place_keys(A, 28, Tup, 24, 25, 27, tin=1.9, fall=3, rise=0.0)
    A.key(27, **fistL0)
    A.key(28, **VP.face(('shout', 1.0)), spine=(34, -6, 0))
    A.key(31, armR=Vector(chr_['armR']) + Vector((0, 0.004, 0.012)), fingR=F['pinch_v_open'])
    A.key(35, armR=Vector(chr_['armR']) + Vector((0.01, 0.04, 0.06)),
          fingR=VP.finger_mix(('pinch_v_open', 0.4), ('fist', 0.6)))
    tback = L.seated(spine=(4, -2, 0), clavR=(14, 2), clavL=(14, 2), **look(0, -14))
    upR = NH(tback, 'r', arm=('chest', (-0.22, -0.04, 1.88)), elbow=('chest', (-0.42, 0.0, 1.60)),
             palm=('chest', (0.7, -0.6, 0)), flex=5)
    upL = NH(tback, 'l', arm=('chest', (0.22, -0.04, 1.88)), elbow=('chest', (0.42, 0.0, 1.60)),
             palm=('chest', (-0.7, -0.6, 0)), flex=5)
    midR = NH(tback, 'r', arm=('chest', (-0.29, -0.16, 1.58)), elbow=('chest', (-0.38, -0.06, 1.28)),
              palm=('chest', (0.7, -0.6, 0)), flex=5)
    midL = NH(tback, 'l', arm=('chest', (0.29, -0.16, 1.58)), elbow=('chest', (0.38, -0.06, 1.28)),
              palm=('chest', (-0.7, -0.6, 0)), flex=5)
    for d_, s_ in ((upR, 'R'), (upL, 'L'), (midR, 'R'), (midL, 'L')):
        d_['fing' + s_] = F['fist']
    A.key(42, torso(tback), **upR, **upL, **FACE(('shout', 0.6), ('laugh', 0.6)))
    A.key(48, **midR, **midL, spine=(10, 0, 0))
    A.key(53, **upR, **upL, spine=(2, -2, 0), **FACE(('laugh', 1.0)))
    A.key(59, **midR, **midL, spine=(10, 2, 0))
    A.key(64, **upR, **upL, spine=(2, 0, 0))
    tp = L.seated(spine=(20, -4, 0), **look(-6, 12))
    point = NH(tp, 'r', arm=(Tr.translation.x - 0.06, Tr.translation.y + 0.20, 1.04),
               elbow=(-0.22, -0.20, 1.02), palm=(0.25, 0.1, -1), flex=-8)
    point['fingR'] = F['point']
    restL = asideL
    A.key(76, torso(tp), **point, **midL, **VP.face(('smile', 1.0)), eyes=(-4, 14))
    A.key(82, armL=(0.42, -0.30, 1.00), elbowL=(0.50, -0.06, 1.00), tableL=0.0)
    A.key(88, **point, **restL, **look(4, 2), eyes=(0, 0), **VP.face(('laugh', 0.8)))
    A.key(120, SB, **asideL, **look(0, 4), eyes=(0, 10), **NEUT())
    A.proc(VP.blink_proc([70, 100]))
    A.props['cam'] = 'mesa'
    A.props['jugada'] = 28
    A.props['eventos'] = dict(slowmo_ini=12, impacto=27, temblor=(27, 33), texto=28, particulas=28,
                              slowmo_fin=40, celebracion=(42, 64), fin=120)

    # ---------------------------------------------------------------- Pasar
    A = new('Pasar', 26, False, 'Pasa: no tiene ficha que case con ningún extremo; toca la mesa dos veces con los '
            'nudillos entre su fila y la cadena, sin agarrar nada.', 'Pasar turno (no lleva).')
    pos = Vector((-0.28, -0.445, 0.0))
    kb = L.seated(spine=(23, -3, 0), **look(-4, 10))
    add_row(A, played_before(20), EST[20]['before'])

    def knock(z, tab):
        d = NH(kb, 'r', arm=tuple((pos + Vector((0, 0, z)))[:]), elbow=(-0.38, -0.22, 0.90), palm=(0.25, 0.7, -0.6),
               flex=28)
        d['fingR'] = F['knock']
        d['tableR'] = tab
        return d
    up1, dn, up2 = knock(0.95, 0.0), knock(0.87, 1.0), knock(0.92, 0.0)

    def knock_keys(A, f0):
        A.key(f0 + 5, torso(kb), **up1, **VP.face(mouthPressLeft=0.4, mouthPressRight=0.4))
        A.key(f0 + 8, **dn, tin=1.5)
        A.key(f0 + 11, **up2)
        A.key(f0 + 14, **dn, tin=1.5)
        A.key(f0 + 18, **up2, **look(-3, 6))
    A.key(0, SB, **look(0, 4), **NEUT())
    knock_keys(A, 0)
    A.key(26, SB, **look(0, 4), **NEUT())
    A.proc(VP.blink_proc([20]))
    A.props['cam'] = 'mesa'
    A.props['jugada'] = 20

    # ---------------------------------------------------------------- Tranque
    A = new('Tranque', 60, False,
            'Tranque: nadie puede jugar; toca la mesa dos veces y luego acuesta cara arriba las fichas que le '
            'quedan, de una en una con la punta de los dedos, para contar los puntos.',
            'Cuando la partida se tranca (ningún jugador lleva). Estado de mesa ilustrativo.')
    sk = played_before(24)
    add_row(A, sk, EST[24]['before'])
    A.key(0, SB, **look(0, 4), **NEUT())
    knock_keys(A, 0)
    tt = L.seated(spine=(24, -2, 0), clavR=(4, 10), **look(0, 18))
    tt['poleR'] = (-0.7, 0.4, -0.6)
    tt['autoR'] = 0.6
    left = [i for i in range(7) if i not in sk]
    f = 24
    for i in left:
        x = VP.ROW_X[i]
        T_push = VP.stand_matrix(x, VP.ROW_Y + 0.008, TOP_Z + S.TILE[1] / 2 + 0.03)
        chp = HT(T_push, 'pinch_v_open')
        chp, _ = with_elbow(ev, tt, chp, 'r')
        A.key(f, torso(tt), **chp)
        A.key(f + 3, armR=Vector(chp['armR']) + Vector((0, -0.03, -0.012)))
        for t in A.tiles:
            if t['name'] == f'Fila{i + 1}':
                t['release'] = f + 3
                t['fall'] = 6
        f += 8
    A.key(f + 2, **VP.face(('focus', 0.4)), **look(4, 14))
    A.key(60, SB, **look(0, 4), **NEUT())
    A.props['cam'] = 'mesa'
    A.props['tranque'] = [DOM.FILA[i] for i in left]

    # ---------------------------------------------------------------- 12. Barajar
    A = new('Barajar_Fichas', 48, True, 'Ambas manos revuelven fichas boca abajo en círculos sobre la mesa '
            '(antes de repartir: todavía no hay fichas paradas).',
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
            'Cuida sus fichas paradas: las dos manos las encierran por los extremos, las mira y mueve los dedos '
            '(bucle).',
            'Mirar las fichas propias (bucle).')
    tb = L.seated(spine=(24, 0, 0), **look(4, 20))
    xe = VP.ROW_X[-1] + S.TILE[0] / 2
    cupL = dict(armL=(xe + 0.034, -0.285, 0.885), elbowL=(0.34, -0.08, 0.86), hdirL=(-0.12, -1, -0.12),
                hpalmL=(-1, 0, 0.05), fingL=VP.finger_mix(('flat', 0.3), ('relax', 0.7)), tableL=0.0)
    cupR = dict(armR=(-xe - 0.034, -0.285, 0.885), elbowR=(-0.34, -0.08, 0.86), hdirR=(0.12, -1, -0.12),
                hpalmR=(1, 0, 0.05), fingR=VP.finger_mix(('flat', 0.3), ('relax', 0.7)), tableR=0.0)
    A.key(0, tb, **cupL, **cupR, eyes=(4, 16), **NEUT())
    A.key(24, **look(-4, 22), eyes=(-6, 18))
    A.key(48, **look(8, 18), eyes=(8, 14))
    A.proc(L.breathe(36, 0.7))
    A.proc(L.finger_fidget(72, 3.0))
    A.proc(VP.blink_proc([8, 50]))
    add_row(A)
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
    # muñecas a la altura de las sienes, dedos hacia arriba y atrás sobre el cráneo (sin cruzar la línea media)
    handsR = NH(back, 'r', arm=('head', (-0.128, 0.03, 1.69)), elbow=('chest', (-0.33, -0.04, 1.47)),
                palm=('head', (1, 0, -0.25)), exact_palm=True)
    handsL = NH(back, 'l', arm=('head', (0.128, 0.03, 1.69)), elbow=('chest', (0.33, -0.04, 1.47)),
                palm=('head', (-1, 0, -0.25)), exact_palm=True)
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
    chin = NH(tb, 'r', arm=('head', (-0.03, -0.135, 1.50)), elbow=(-0.20, -0.45, 0.885),
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
    point = NH(tp, 'r', arm=(-0.04, -0.48, 1.06), elbow=(-0.25, -0.28, 1.01), palm=(0.25, 0.1, -1), flex=-8)
    point['fingR'] = F['point']
    A.key(9, torso(tp), **point, **FACE(('determined', 0.6)), eyes=(10, 0))
    A.key(13, armR=(-0.035, -0.50, 1.065))
    # la mano sube antes de cruzar por encima de la fila de fichas paradas (ida y vuelta)
    lift = dict(armR=(-0.22, -0.43, 1.00), elbowR=(-0.34, -0.17, 0.98))
    A.key(4, **lift)
    A.key(26, **point, **VP.face(mouthSmileLeft=0.3))
    A.key(32, armR=(-0.20, -0.44, 1.04), elbowR=(-0.33, -0.18, 1.00))
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
    slap_up = NH(ta, 'r', arm=(-0.24, -0.44, 1.04), elbow=(-0.38, -0.20, 1.0), palm=(0.15, 0, -1), exact_palm=True)
    slap_up['fingR'] = F['flat']
    ts = L.seated(spine=(30, -3, 0), **look(-4, 10))
    slap = NH(ts, 'r', arm=(-0.25, -0.47, 0.84), elbow=(-0.36, -0.24, 0.88), palm=(0.1, 0, -1), exact_palm=True)
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
    for A in anims:
        if A.name in ('Idle_Sentado', 'Celebrar_Ganar', 'Perder', 'Pensar', 'Saludar', 'Senalar', 'Pulgar_Arriba',
                      'Aplaudir', 'Reir', 'Enojado'):
            add_row(A)
    return anims
