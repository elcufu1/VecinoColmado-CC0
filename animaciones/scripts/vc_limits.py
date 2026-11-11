"""Límites anatómicos de rotación ("stops") para los 53 huesos del rig.

Cada hueso tiene rangos en grados, definidos para el lado IZQUIERDO (el derecho es el espejo: X igual, Y y Z
con signo invertido, igual que el rig). Dos modos:

- 'euler': rotación local (pose) descompuesta en Euler con el orden indicado; se recorta cada ángulo.
  El constraint Limit Rotation usa exactamente los mismos rangos y orden.
- 'st' (swing/twist): para hombro, codo, muñeca y cadera. Se separa el giro sobre el eje del hueso (twist, Y)
  del balanceo (swing, vector de rotación en el plano X-Z del marco anatómico) y se recortan por separado.
  Es lo que evita giros de 180° y saltos de codo. El constraint Limit Rotation de esos huesos lleva la caja
  Euler que contiene ese rango (se calcula muestreando el borde), así que nunca modifica lo horneado.

Semántica (lado izquierdo, + = sentido indicado):
  columna/cuello/cabeza/pelvis  X + = flexión hacia delante, Y = giro, Z = inclinación lateral
  codo (lowerarm)               X + = flexión desde la pose de reposo (en reposo el codo ya está a 45.5°)
  rodilla (calf)                X + = flexión
  dedos                         X + = cerrar (curl), Y = giro, Z = separación
"""
import math
import numpy as np
from mathutils import Matrix, Quaternion, Vector, Euler

FING = ('index', 'middle', 'ring', 'pinky')

# (modo, orden, (xlo, xhi), (ylo, yhi), (zlo, zhi)) — lado izquierdo
BASE = {
    'Root': ('euler', 'XYZ', (0, 0), (0, 0), (0, 0)),
    'pelvis': ('euler', 'XZY', (-35, 45), (-35, 35), (-25, 25)),
    'spine_01': ('euler', 'XZY', (-15, 30), (-20, 20), (-15, 15)),
    'spine_02': ('euler', 'XZY', (-15, 30), (-20, 20), (-15, 15)),
    'spine_03': ('euler', 'XZY', (-15, 30), (-20, 20), (-15, 15)),
    'neck_01': ('euler', 'XZY', (-30, 35), (-35, 35), (-20, 20)),
    'head': ('euler', 'XZY', (-35, 30), (-45, 45), (-20, 20)),
    'clavicle': ('euler', 'XYZ', (-20, 25), (-10, 10), (-20, 25)),
    # hombro: swing X (+ = adelante), Z (balanceo lateral), twist Y
    'upperarm': ('st', 'XZY', (-90, 130), (-105, 105), (-80, 110)),
    # codo: flexión X (reposo = 45.5°: -45.5 extiende del todo, +100 = 145.5° de flexión total)
    'lowerarm': ('st', 'YXZ', (-48, 100), (-85, 85), (-12, 12)),
    # muñeca: marco anatómico (X = flexión palmar +, Z = desviación), twist pequeño
    'hand': ('st', 'XZY', (-70, 80), (-28, 28), (-35, 22)),
    'thigh': ('st', 'XZY', (-125, 30), (-40, 40), (-45, 35)),
    'calf': ('euler', 'XYZ', (-2, 150), (-12, 12), (-4, 4)),
    'foot': ('euler', 'XZY', (-32, 50), (-18, 18), (-25, 30)),
    'ball': ('st', 'XZY', (-55, 40), (-8, 8), (-8, 8)),
    'thumb_01': ('euler', 'YXZ', (-25, 50), (-35, 40), (-25, 60)),
    'thumb_02': ('euler', 'YXZ', (-12, 60), (-6, 6), (-6, 6)),
    'thumb_03': ('euler', 'YXZ', (-20, 80), (-6, 6), (-6, 6)),
    'f_01': ('euler', 'YXZ', (-25, 92), (-6, 6), (-25, 25)),
    'f_02': ('euler', 'YXZ', (-6, 108), (-6, 6), (-6, 6)),
    'f_03': ('euler', 'YXZ', (-6, 82), (-6, 6), (-6, 6)),
}

SEMANTIC = {
    'pelvis': ('Pelvis', 'flexión adelante / atrás', 'giro', 'inclinación lateral'),
    'spine_01': ('Columna lumbar (spine_01)', 'flexión / extensión', 'giro', 'inclinación lateral'),
    'spine_02': ('Columna torácica (spine_02)', 'flexión / extensión', 'giro', 'inclinación lateral'),
    'spine_03': ('Columna alta (spine_03)', 'flexión / extensión', 'giro', 'inclinación lateral'),
    'neck_01': ('Cuello', 'flexión / extensión', 'giro', 'inclinación lateral'),
    'head': ('Cabeza', 'flexión / extensión', 'giro', 'inclinación lateral'),
    'clavicle': ('Clavícula (hombro)', 'protracción / retracción', 'giro', 'elevación / depresión'),
    'upperarm': ('Hombro (upperarm)', 'balanceo adelante / atrás', 'rotación interna / externa', 'balanceo lateral'),
    'lowerarm': ('Codo (lowerarm)', 'flexión (desde reposo 45.5°)', 'pronación / supinación', 'desvío lateral'),
    'hand': ('Muñeca (hand)', 'flexión palmar / extensión', 'giro residual', 'desviación radial / cubital'),
    'thigh': ('Cadera (thigh)', 'extensión / flexión', 'rotación interna / externa', 'abducción / aducción'),
    'calf': ('Rodilla (calf)', 'flexión', 'rotación tibial', 'varo / valgo'),
    'foot': ('Tobillo (foot)', 'flexión plantar / dorsal', 'giro', 'inversión / eversión'),
    'ball': ('Dedos del pie (ball)', 'flexión / extensión', 'giro', 'desvío'),
    'thumb_01': ('Pulgar falange 1 (thumb_01)', 'flexión', 'giro', 'oposición / separación'),
    'thumb_02': ('Pulgar falange 2 (thumb_02)', 'flexión', 'giro', 'desvío'),
    'thumb_03': ('Pulgar falange 3 (thumb_03)', 'flexión', 'giro', 'desvío'),
    'f_01': ('Dedos falange 1 (index/middle/ring/pinky _01)', 'flexión', 'giro', 'separación'),
    'f_02': ('Dedos falange 2 (_02)', 'flexión', 'giro', 'desvío'),
    'f_03': ('Dedos falange 3 (_03)', 'flexión', 'giro', 'desvío'),
}


def base_key(name):
    parts = name.split('_')
    if parts[0] in FING:
        return 'f_' + parts[1]
    if parts[0] == 'thumb':
        return 'thumb_' + parts[1]
    if name.endswith(('_l', '_r')):
        return name[:-2]
    return name


def side_of(name):
    return 'r' if name.endswith('_r') else 'l'


class Limits:
    def __init__(self, rig):
        self.rig = rig
        self.spec = {}
        self.frame = {}
        for n in rig.names:
            mode, order, x, y, z = BASE[base_key(n)]
            if side_of(n) == 'r':
                y = (-y[1], -y[0])
                z = (-z[1], -z[0])
            lo = np.radians([x[0], y[0], z[0]])
            hi = np.radians([x[1], y[1], z[1]])
            self.spec[n] = (mode, order, lo, hi)
            self.frame[n] = self._semantic_frame(n) if mode == 'st' else None
        self.enabled = True
        self.stats = {}
        self.box = {}

    def _semantic_frame(self, n):
        """Matriz A (columnas = ejes anatómicos X, Y, Z en coordenadas locales del hueso)."""
        rig = self.rig
        if base_key(n) == 'ball':
            # flexión de los dedos del pie alrededor del eje lateral (X del mundo), no del X local inclinado
            y = Vector((0, 1, 0))
            k = rig.rest3[n].inverted() @ Vector((1, 0, 0))
            x = (k - y * k.dot(y)).normalized()
            return Matrix((x, y, x.cross(y).normalized())).transposed()
        if base_key(n) != 'hand':
            return Matrix.Identity(3)
        s = side_of(n)
        F0, P0 = rig.hand_ref[s]
        r3i = rig.rest3[n].inverted()
        y = Vector((0, 1, 0))
        p = r3i @ P0
        k = (r3i @ F0).cross(p)          # eje de flexión palmar (+X)
        x = (k - y * k.dot(y)).normalized()
        z = x.cross(y).normalized()
        return Matrix((x, y, z)).transposed()

    # ------------------------------------------------------------------ descomposición
    def decompose(self, n, q):
        mode, order, lo, hi = self.spec[n]
        if mode == 'euler':
            e = q.to_euler(order)
            return np.array([e.x, e.y, e.z])
        A = self.frame[n]
        qs = (A.transposed() @ q.to_matrix() @ A).to_quaternion()
        if qs.w < 0:
            qs = -qs
        tw = 2 * math.atan2(qs.y, qs.w)
        twq = Quaternion((0, 1, 0), tw)
        sw = qs @ twq.inverted()
        if sw.w < 0:
            sw = -sw
        ang = sw.angle
        ax = sw.axis
        v = Vector(ax) * ang
        return np.array([v.x, tw, v.z])

    def compose(self, n, a):
        mode, order, lo, hi = self.spec[n]
        if mode == 'euler':
            return Euler((float(a[0]), float(a[1]), float(a[2])), order).to_quaternion()
        A = self.frame[n]
        v = Vector((float(a[0]), 0.0, float(a[2])))
        sw = Quaternion(v.normalized(), v.length) if v.length > 1e-12 else Quaternion()
        qs = sw @ Quaternion((0, 1, 0), float(a[1]))
        return (A @ qs.to_matrix() @ A.transposed()).to_quaternion()

    def clamp_q(self, n, q):
        mode, order, lo, hi = self.spec[n]
        a = self.decompose(n, q)
        c = np.clip(a, lo, hi)
        if np.all(np.abs(c - a) < 1e-9):
            return q, 0.0
        exceed = float(np.degrees(np.max(np.maximum(a - hi, lo - a))))
        st = self.stats.setdefault(n, [0, 0.0])
        st[0] += 1
        st[1] = max(st[1], exceed)
        return self.compose(n, c), exceed

    def clamp_local(self, n, M):
        if not self.enabled:
            return M
        q = M.to_quaternion()
        q2, ex = self.clamp_q(n, q)
        if ex == 0.0:
            return M
        out = q2.to_matrix().to_4x4()
        out.translation = M.translation
        return out

    def excess(self, n, q):
        """Grados por los que q excede el rango (0 si está dentro)."""
        mode, order, lo, hi = self.spec[n]
        a = self.decompose(n, q)
        return float(np.degrees(np.max(np.maximum(np.maximum(a - hi, lo - a), 0.0))))

    # ------------------------------------------------------------------ caja Euler para el constraint
    def constraint_box(self, n, margin_deg=1.0):
        """Rangos Euler (orden, xlo..zhi en grados) del constraint Limit Rotation."""
        mode, order, lo, hi = self.spec[n]
        if mode == 'euler':
            return order, np.degrees(lo), np.degrees(hi)
        if n in self.box:
            return self.box[n]
        pts = []
        g = 9
        xs = np.linspace(lo[0], hi[0], g)
        ys = np.linspace(lo[1], hi[1], g)
        zs = np.linspace(lo[2], hi[2], g)
        for x in xs:
            for y in ys:
                for z in zs:
                    pts.append(self.compose(n, (x, y, z)))
        best = None
        for o in ('XZY', 'YXZ', 'XYZ', 'ZXY', 'YZX', 'ZYX'):
            E = np.array([q.to_euler(o)[:] for q in pts])
            span = (E.max(0) - E.min(0)).sum()
            if np.any(E.max(0) - E.min(0) > math.radians(350)):
                continue
            if best is None or span < best[0]:
                best = (span, o, E.min(0), E.max(0))
        _, o, elo, ehi = best
        m = math.radians(margin_deg)
        self.box[n] = (o, np.degrees(elo - m), np.degrees(ehi + m))
        return self.box[n]
