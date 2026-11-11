"""Reglas del dominó (estilo dominicano: por parejas, doble-seis, 28 fichas, 7 por jugador) y geometría de la
cadena sobre la mesa de referencia.

Este módulo es Python puro (sin bpy) para poder validar la partida fuera de Blender.

Coordenadas: las de la escena de previsualización. El Vecino está sentado en +Y mirando hacia -Y; su izquierda
es +X. Centro de la mesa (0, -0.765); la cadena se centra en (0, -0.70), 6.5 cm hacia el jugador para que alcance los dos extremos; paño útil |x| <= 0.53, -1.295 <= y <= -0.235.

Cadena:
- La salida (doble seis) va al centro, atravesada (eje largo a lo largo de Y).
- El extremo DERECHO del Vecino crece hacia -X; el IZQUIERDO hacia +X.
- Cada ficha normal va en línea con la cadena; los dobles van atravesados (perpendiculares).
- Cuando la siguiente ficha se saldría del paño, la cadena dobla en esquina: en el extremo derecho dobla hacia el
  jugador (+Y) y en el izquierdo hacia el fondo (-Y). La ficha de la esquina apoya su mitad que casa al lado del
  extremo anterior (forma de "L").
- La mitad que casa siempre toca el número igual del extremo.
"""
import math
import random

TILE_W, TILE_L = 0.045, 0.090
HW, HL = TILE_W / 2, TILE_L / 2
CENTER = (0.0, -0.70)
FELT_X = 0.53 - 0.012
FELT_Y = (-1.295 + 0.012, -0.45)    # no más cerca que -0.45: delante de su fila no se juega
ROW_Y = -0.38
SHOULDER_R = (-0.18, -0.08)
REACH_MAX = 0.74        # distancia horizontal hombro derecho -> punto donde se suelta la ficha
JUGADORES = ('Vecino', 'Derecha', 'Companero', 'Izquierda')   # orden de juego (a la derecha)


def all_tiles():
    return [(a, b) for a in range(7) for b in range(a, 7)]


def norm(t):
    return (min(t), max(t))


def add(p, d, k):
    return (p[0] + d[0] * k, p[1] + d[1] * k)


class Branch:
    def __init__(self, name, d, turns):
        self.name = name
        self.d = d
        self.turns = turns            # sentidos sucesivos al doblar en las esquinas
        self.p = add(CENTER, d, HW)    # punto medio del borde del extremo
        self.n_tiles = 0
        self.corners = 0

    @property
    def turn(self):
        return self.turns[min(self.corners, len(self.turns) - 1)]

    def copy(self):
        b = Branch(self.name, self.d, self.turns)
        b.p, b.n_tiles, b.corners = self.p, self.n_tiles, self.corners
        return b

    def inside(self, c, axis_long, room=0.0):
        """room: espacio extra que debe quedar más allá de la ficha (para poder doblar después)."""
        hx, hy = (HL, HW) if abs(axis_long[0]) > 0.5 else (HW, HL)
        ex = room if abs(self.d[0]) > 0.5 else 0.0
        ey = room if abs(self.d[1]) > 0.5 else 0.0
        return (abs(c[0]) + hx + ex <= FELT_X and FELT_Y[0] <= c[1] - hy - ey and c[1] + hy + ey <= FELT_Y[1])

    def slot(self, double):
        """Siguiente hueco: dict(c=centro, axis=eje largo, d=sentido de la cadena, kind, new_p, new_d)."""
        d = self.d
        if double:
            c = add(self.p, d, HW)
            axis = (-d[1], d[0])
            s = dict(c=c, axis=axis, d=d, kind='doble', new_p=add(self.p, d, TILE_W), new_d=d)
        else:
            c = add(self.p, d, HL)
            s = dict(c=c, axis=d, d=d, kind='linea', new_p=add(self.p, d, TILE_L), new_d=d)
        if self.inside(s['c'], s['axis'], TILE_W):
            return s
        if double:
            return None
        n = self.turn
        q = add(self.p, d, HW)
        c = add(q, n, HW)
        s = dict(c=c, axis=n, d=n, kind='esquina', new_p=add(q, n, HW + TILE_W), new_d=n)
        return s if self.inside(s['c'], s['axis']) else None

    def apply(self, s):
        self.p, self.d = s['new_p'], s['new_d']
        self.n_tiles += 1
        if s['kind'] == 'esquina':
            self.corners += 1


class Mesa:
    def __init__(self):
        self.ends = None
        self.br = {'D': Branch('D', (-1.0, 0.0), ((0.0, 1.0), (1.0, 0.0))),
                   'I': Branch('I', (1.0, 0.0), ((0.0, -1.0), (-1.0, 0.0)))}
        self.placed = []        # dict(tile, c, axis, u_match, kind, player, side)

    def copy(self):
        m = Mesa()
        m.ends = dict(self.ends) if self.ends else None
        m.br = {k: b.copy() for k, b in self.br.items()}
        m.placed = list(self.placed)
        return m

    def options(self, tile):
        """Lugares legales para la ficha: lista de (lado, valor_que_casa, slot)."""
        if self.ends is None:
            return [('C', None, None)] if tile == (6, 6) else []
        out = []
        for side in ('D', 'I'):
            v = self.ends[side]
            if v in tile:
                s = self.br[side].slot(tile[0] == tile[1])
                if s is not None:
                    out.append((side, v, s))
        return out

    def play(self, tile, side, player):
        if side == 'C':
            self.ends = {'D': 6, 'I': 6}
            self.placed.append(dict(tile=tile, c=CENTER, axis=(0.0, 1.0), d=(0.0, 1.0), match=6, other=6,
                                    kind='salida', player=player, side='C'))
            return
        v = self.ends[side]
        s = self.br[side].slot(tile[0] == tile[1])
        other = tile[1] if tile[0] == v else tile[0]
        self.br[side].apply(s)
        self.ends[side] = other
        self.placed.append(dict(tile=tile, c=s['c'], axis=s['axis'], d=s['d'], match=v, other=other,
                                kind=s['kind'], player=player, side=side))


def release_point(c, u):
    """Punto (x,y) donde la ficha parada apoya su arista antes de caer cara arriba hacia u."""
    return (c[0] - u[0] * HL, c[1] - u[1] * HL)


def reach(pt):
    return math.hypot(pt[0] - SHOULDER_R[0], pt[1] - SHOULDER_R[1])


def best_u(s_c, axis):
    """Sentido de caída (u = +eje o -eje) con el punto de apoyo más cómodo para la mano derecha."""
    cands = [axis, (-axis[0], -axis[1])]
    return min(cands, key=lambda u: reach(release_point(s_c, u)))


def reachable(c, axis):
    u = best_u(c, axis)
    rp = release_point(c, u)
    return reach(rp) <= REACH_MAX and rp[0] <= 0.22 and abs(rp[1] - ROW_Y) > 0.06


def comodo(s):
    """Hueco cómodo para la mano derecha del Vecino sentado: un doble (cae de pie hacia el fondo, sin girar la
    muñeca) o una ficha a lo largo de X (se suelta apaisada y cae hacia el fondo). Las fichas a lo largo de Y que no
    son dobles obligarían a girar la ficha 90° en la pinza: se descartan."""
    c, ax = s['c'], s['axis']
    if s['kind'] == 'doble':
        pt = (c[0], c[1] + HL)
    elif abs(ax[0]) > 0.5:
        pt = (c[0], c[1] + HW)
    else:
        return False
    return reach(pt) <= 0.66 and -0.48 <= c[0] <= 0.26 and pt[1] < -0.44


# ------------------------------------------------------------------------------------------------ partida
def search(seed=60, tries=200000):
    """Busca una mano corta y legal (reproduce PARTIDA con seed=60): mano del Vecino al azar con el doble seis y
    algún otro doble; sale con el doble seis, solo juega en huecos cómodos (comodo), juega por los dos extremos,
    un doble atravesado, una esquina, al menos dos fichas en línea, pasa una vez y domina con capicúa."""
    global MANO_VECINO
    rnd = random.Random(seed)
    alls = all_tiles()
    for _ in range(tries):
        rest = [t for t in alls if t != (6, 6)]
        V = [(6, 6)] + rnd.sample(rest, 6)
        if not any(t[0] == t[1] for t in V[1:]):
            continue
        others = [t for t in alls if t not in V]
        m = Mesa()
        hand = list(V)
        used = set()
        moves = []
        turn = 0
        ok = False
        while len(moves) < 40:
            p = turn % 4
            if p == 0:
                legal = [(t, o) for t in hand for o in m.options(t)]
                legal = [(t, o) for t, o in legal if o[0] == 'C' or comodo(o[2])]
                if not legal:
                    # el pase solo vale si de verdad no lleva (ninguna ficha casa en ningún extremo)
                    if any(m.options(t) for t in hand):
                        break
                    moves.append((0, None, None))
                else:
                    t, (side, v, s) = rnd.choice(legal)
                    if len(hand) == 1 and not es_capicua(m.ends, t):
                        break
                    m.play(t, side, 0)
                    hand.remove(t)
                    moves.append((0, t, side))
                    if not hand:
                        ok = True
                        break
            else:
                if m.ends is None:
                    break
                legal = [(t, o) for t in others if t not in used for o in m.options(t)]
                if legal and rnd.random() < 0.93:
                    pref = [x for x in legal if x[1][0] == 'D']
                    t, (side, v, s) = rnd.choice(pref if pref and rnd.random() < 0.7 else legal)
                    m.play(t, side, p)
                    used.add(t)
                    moves.append((p, t, side))
                else:
                    moves.append((p, None, None))
            turn += 1
        if not ok:
            continue
        vp = [mv for mv in moves if mv[0] == 0]
        if sum(1 for mv in vp if mv[1] is None) != 1:
            continue
        if not {'D', 'I'} <= {mv[2] for mv in vp if mv[1] is not None}:
            continue
        vd = [pl for pl in m.placed if pl['player'] == 0]
        if not {'doble', 'esquina', 'linea'} <= {pl['kind'] for pl in vd}:
            continue
        if sum(pl['kind'] == 'doble' for pl in vd) > 2 or sum(pl['kind'] == 'linea' for pl in vd) < 2:
            continue
        ys = [pl['c'][1] for pl in vd if pl['kind'] != 'salida']
        if min(ys) > -0.62 or max(ys) < -0.56:
            continue
        prev = MANO_VECINO
        MANO_VECINO = V
        manos = deal_rest(moves)
        if manos is None:
            MANO_VECINO = prev
            continue
        errs, _ = validate(moves, manos)
        if errs:
            MANO_VECINO = prev
            continue
        return dict(moves=moves, mesa=m, manos=manos)
    return None


def deal_rest(moves):
    """Reparte las fichas no jugadas entre los otros tres (7 cada uno) de modo que cada pase sea legal:
    quien pasa no puede tener (ni haber jugado después) ninguna ficha con los números de los extremos."""
    V = [norm(t) for t in MANO_VECINO]
    manos = {0: list(V), 1: [], 2: [], 3: []}
    m = Mesa()
    banned = {1: set(), 2: set(), 3: set()}
    for p, t, side in moves:
        if t is None:
            if p:
                banned[p] |= set(m.ends.values())
            continue
        if p:
            if set(t) & banned[p]:
                return None
            manos[p].append(t)
        m.play(t, side, p)
    used = {t for p in manos for t in manos[p]}
    rest = [t for t in all_tiles() if t not in used]
    rest.sort(key=lambda t: -sum(1 for p in (1, 2, 3) if not (set(t) & banned[p])) * -1)

    def bt(i):
        if i == len(rest):
            return all(len(manos[p]) == 7 for p in (1, 2, 3))
        t = rest[i]
        for p in (1, 2, 3):
            if len(manos[p]) < 7 and not (set(t) & banned[p]):
                manos[p].append(t)
                if bt(i + 1):
                    return True
                manos[p].pop()
        return False
    return manos if bt(0) else None


def validate(moves, manos):
    """Reproduce la partida y comprueba todas las reglas. Devuelve lista de errores (vacía = válida)."""
    errs = []
    seen = set()
    for p in range(4):
        if len(manos[p]) != 7:
            errs.append(f'jugador {p} tiene {len(manos[p])} fichas')
        for t in manos[p]:
            if t in seen:
                errs.append(f'ficha repetida {t}')
            seen.add(t)
    if len(seen) != 28:
        errs.append('no están las 28 fichas')
    hands = {p: list(manos[p]) for p in range(4)}
    m = Mesa()
    for i, (p, t, side) in enumerate(moves):
        if i == 0 and t != (6, 6):
            errs.append('la salida no es el doble seis')
        if t is None:
            if any(m.options(x) for x in hands[p]):
                errs.append(f'jugada {i}: {JUGADORES[p]} pasa pero lleva')
            continue
        if t not in hands[p]:
            errs.append(f'jugada {i}: {JUGADORES[p]} no tiene {t}')
            continue
        if side not in [o[0] for o in m.options(t)]:
            errs.append(f'jugada {i}: {t} no casa en {side}')
        m.play(t, side, p)
        hands[p].remove(t)
        if (i + 1 < len(moves)) and moves[i + 1][0] != (p + 1) % 4:
            errs.append(f'jugada {i + 1}: turno fuera de orden')
    if hands[0]:
        errs.append('el Vecino no dominó')
    return errs, m


# ------------------------------------------------------------------------------------------------ la mano jugada
# Mano fija (encontrada con search(60) y validada por validate()). (jugador, ficha, extremo) — None = pasa.
# El Vecino: sale con el doble seis, juega un doble atravesado, los dos extremos, una esquina, pasa una vez y
# domina con CAPICÚA (su última ficha, 4-6, casa en los dos extremos: D pide 4 e I pide 6).
PARTIDA = [
    (0, (6, 6), 'C'), (1, (5, 6), 'D'), (2, (5, 5), 'D'), (3, (1, 5), 'D'),
    (0, (1, 1), 'D'), (1, (1, 4), 'D'), (2, (3, 4), 'D'), (3, (0, 3), 'D'),
    (0, (1, 6), 'I'), (1, (0, 4), 'D'), (2, (0, 1), 'I'), (3, (0, 6), 'I'),
    (0, (2, 4), 'D'), (1, (2, 2), 'D'), (2, (2, 3), 'D'), (3, (3, 6), 'I'),
    (0, (3, 5), 'D'), (1, (2, 5), 'D'), (2, (1, 3), 'I'), (3, (0, 2), 'D'),
    (0, None, None), (1, (0, 5), 'D'), (2, None, None), (3, (1, 2), 'I'),
    (0, (4, 5), 'D'), (1, (4, 4), 'D'), (2, (2, 6), 'I'), (3, None, None),
    (0, (4, 6), 'D'),
]
MANOS = {0: [(6, 6), (4, 6), (3, 5), (1, 6), (2, 4), (4, 5), (1, 1)],
         1: [(5, 6), (1, 4), (0, 4), (2, 2), (2, 5), (0, 5), (4, 4)],
         2: [(5, 5), (3, 4), (0, 1), (2, 3), (1, 3), (2, 6), (0, 0)],
         3: [(1, 5), (0, 3), (0, 6), (3, 6), (0, 2), (1, 2), (3, 3)]}
MANO_VECINO = MANOS[0]
# Orden de las fichas del Vecino en su fila (hueco 0 = su derecha, -X)
FILA = [(4, 6), (2, 4), (1, 1), (6, 6), (3, 5), (4, 5), (1, 6)]


def es_capicua(ends, tile):
    """Capicúa: la ficha (no doble) que domina casa en los DOS extremos."""
    return tile is not None and tile[0] != tile[1] and ends is not None and {ends['D'], ends['I']} == set(tile)


def partida():
    """Reproduce PARTIDA; devuelve la lista de estados: para cada jugada, la mesa ANTES y la colocación."""
    errs, _ = validate(PARTIDA, MANOS)
    if errs:
        raise ValueError('partida inválida: ' + '; '.join(errs))
    m = Mesa()
    out = []
    for i, (p, t, side) in enumerate(PARTIDA):
        before = m.copy()
        if t is not None:
            m.play(t, side, p)
            pl = m.placed[-1]
        else:
            pl = None
        out.append(dict(i=i, player=p, tile=t, side=side, before=before, placed=pl, ends=dict(m.ends),
                        capicua=p == 0 and i == len(PARTIDA) - 1 and es_capicua(before.ends, t)))
    return out


def tile_halves(pl, u):
    """Valores (mitad +Y local, mitad -Y local) de una ficha colocada con su eje largo según u: la mitad que casa
    queda del lado de la cadena (sentido -d)."""
    a, b = pl['match'], pl['other']
    if pl['kind'] in ('doble', 'salida'):
        return (a, b)
    d = pl['d']
    far = u[0] * d[0] + u[1] * d[1] > 0
    return (b, a) if far else (a, b)
