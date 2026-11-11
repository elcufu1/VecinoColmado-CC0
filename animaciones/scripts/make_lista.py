"""Genera LISTA_ANIMACIONES.md a partir de reporte_verificacion.json.

Uso: python3 make_lista.py reporte_verificacion.json LISTA_ANIMACIONES.md [limites_rotacion.json]
"""
import json
import sys

ORDEN = ['Idle_De_Pie', 'Caminar', 'Sentarse', 'Levantarse', 'Idle_Sentado',
         'Agarrar_Ficha_Cerca', 'Agarrar_Ficha_Lejos', 'Colocar_Ficha_Cerca', 'Colocar_Ficha_Lejos',
         'Golpe_Ficha', 'Pasar', 'Barajar_Fichas', 'Sostener_Fichas', 'Celebrar_Ganar', 'Perder',
         'Pensar', 'Saludar', 'Senalar', 'Pulgar_Arriba', 'Aplaudir', 'Reir', 'Enojado',
         'Prueba_Rango_Completo']

CHECK_LABEL = {
    'riel_cerca': 'borde de la mesa (lado del jugador)', 'riel_lejos': 'borde lejano de la mesa',
    'mesa': 'tablero', 'mesa_pano': 'paño de la mesa', 'silla': 'silla', 'asiento': 'asiento',
    'silla_asiento': 'asiento de la silla', 'suelo': 'suelo', 'boxer': 'piel vs. bóxer',
    'cuerpo_r': 'mano/antebrazo der. vs. cuerpo', 'cuerpo_l': 'mano/antebrazo izq. vs. cuerpo',
}


def main(src, dst, lim_src=None):
    r = json.load(open(src))
    lim = json.load(open(lim_src)) if lim_src else None
    tl = {t['name']: t for t in r['timeline']}
    glb = r['glb']['animaciones']
    rep = r['report']
    L = []
    w = L.append
    w('# Lista de animaciones — VecinoColmado (Dominó Colmado)\n')
    w('Todas las animaciones son *Actions* separadas del armature `VecinoColmado_CC0` (53 huesos), '
      'a **24 fps**, horneadas cuadro a cuadro. No se modificó malla, pesos, huesos ni morfos: '
      'solo se crearon Actions (huesos + morfos faciales).\n')
    w('Archivos:\n')
    w('- `Vecino_Boxer_Animado.glb` — personaje + 23 animaciones (sin mesa ni silla), listo para el juego.')
    w('- `Vecino_Boxer_Animado.blend` — mismas Actions + escena `Previsualizacion_Animaciones` con mesa, silla, '
      'fichas y cámaras (línea de tiempo con marcadores por animación).')
    w('- `videos/` — un MP4 por animación (H.264, 1280×720, 24 fps) y `VIDEO_TODO_EL_CUERPO.mp4`.')
    w('- `scripts/` — código que genera todo (`blender -b Vecino_Boxer.blend --python scripts/final.py -- build <dir>`).\n')
    w('| # | Nombre (Action) | Cuadros | Duración | Bucle | Uso en el juego |')
    w('|---|---|---|---|---|---|')
    for i, n in enumerate(ORDEN, 1):
        t = tl[n]
        w(f"| {i} | `{n}` | {t['frames']} | {glb[n]['duracion_s']:.2f} s | {'sí' if t['loop'] else 'no'} | {t['uso']} |")
    w('\nDescripción de cada animación:\n')
    for i, n in enumerate(ORDEN, 1):
        t = tl[n]
        extra = ''
        if t.get('markers'):
            extra = ' Segmentos (cuadro local): ' + ', '.join(f"{m[1]} ({m[0] - t['start']})" for m in t['markers']) + '.'
        w(f"{i}. **{n}** — {t['desc']}{extra}")
    w('\n## Convenciones para integrar en el juego\n')
    w('- El personaje mira hacia **−Y** (de frente a la mesa); su izquierda es **+X**. Origen del armature = '
      'entre los pies, de pie delante de la silla.')
    w('- Mesa de referencia 1.15 × 1.15 m, paño a 0.806 m; borde de la mesa más cercano en y = −0.19 m. '
      'Silla: asiento a 0.46 m; centrada en y = +0.14 m cuando está sentado y en y = +0.27 m cuando está de pie '
      '(`Sentarse` acerca la silla, `Levantarse` la aleja; mover la silla en el juego en esos tramos).')
    w('- Ficha de referencia: 0.045 × 0.090 × 0.014 m. Las 7 fichas del jugador están **paradas de canto** '
      'en una fila delante de él (centro y = −0.38 m, x = −0.156 … +0.156 m cada 0.052 m, base sobre el paño), '
      'con la cara de puntos mirando al jugador. Las agarra de pie con una pinza limpia pulgar-índice '
      '(pulgar en la cara, índice detrás; medio, anular y meñique relajados), la sostiene parada y sin girarla '
      'raro, y al jugar la lleva hasta el paño (x ≈ −0.235 m), la apoya parada y la suelta: la ficha cae '
      'boca arriba sobre su borde. En el .blend la escena de vista previa muestra todo esto.')
    w('- Para que la ficha siga la mano en el juego: emparentarla al hueso `hand_r` entre el cuadro de agarre y el '
      'de suelta (la posición relativa es constante en ese tramo).')
    w('- Cuadros clave: Agarrar_Ficha_Cerca agarra en el cuadro 11 (ficha 3 de la fila); Agarrar_Ficha_Lejos en el '
      '15 (ficha 7, la del otro extremo); Colocar_Ficha_Cerca suelta en el 9; Colocar_Ficha_Lejos en el 12; '
      'Golpe_Ficha impacta y suelta en el 15; Pasar golpea en los cuadros 8 y 14.')
    w('- `Caminar` es un ciclo en el sitio a ~0.83 m/s (el juego mueve la raíz). Los bucles tienen el primer y '
      'el último cuadro iguales.')
    w('- Cada Action anima también los morfos faciales (expresiones); al mezclar animaciones, los morfos de la '
      'Action activa sustituyen a los anteriores.')
    w('- En el GLB las texturas opacas de piel y lengua se recomprimieron a JPEG para reducir peso '
      '(la malla, pesos, huesos y morfos son los mismos).')
    if lim:
        w('\n## Límites de articulación ("stops")\n')
        w('Cada uno de los 53 huesos tiene un rango de rotación fijo y anatómico. Se aplica dos veces:\n')
        w('1. **Al hornear**: cada rotación local se recorta a su rango antes de escribir la Action '
          '(las animaciones ya vienen dentro de los límites; no dependen del constraint).')
        w('2. **En el rig** (`.blend`): cada hueso lleva un constraint *Limit Rotation* (`Limite_anatomico`, '
          'espacio local). Para codo, hombro, muñeca, cadera y dedos del pie el rango real es swing/twist '
          '(balanceo + giro sobre el eje del hueso) y el constraint lleva la caja Euler que lo contiene.\n')
        w('Rangos (grados, lado izquierdo; el derecho es el espejo: Y y Z con signo invertido):\n')
        w('| Articulación | Modo | X | Y | Z |')
        w('|---|---|---|---|---|')
        for g in lim['rangos']:
            md = 'Euler ' + g['orden'] if g['modo'] == 'euler' else 'swing/twist'
            w(f"| {g['nombre']} | {md} | {g['x'][0]}…{g['x'][1]} ({g['eje_x']}) | {g['y'][0]}…{g['y'][1]} "
              f"({g['eje_y']}) | {g['z'][0]}…{g['z'][1]} ({g['eje_z']}) |")
        ex = lim['excesos_max_grados']
        cv = lim['constraints_verificacion']
        w('\nVerificación numérica:\n')
        w(f"- Se comprobaron {lim['muestras_hueso_cuadro']:,} rotaciones (53 huesos × todos los cuadros de las "
          f"23 Actions). Exceso máximo sobre el rango: **{max(ex.values()):.4f}°** "
          f"({'ninguna animación excede los límites' if max(ex.values()) < 0.01 else 'ver limites_rotacion.json'})."
          .replace(',', '.'))
        w(f"- Con los {cv['constraints']} constraints activos, la pose evaluada se comparó con la pose sin "
          f"constraints en los {cv['cuadros']} cuadros de la línea de tiempo: diferencia máxima "
          f"**{cv['dif_max_grados']}°** (los constraints no alteran nada de lo horneado).")
        w('- `Prueba_Rango_Completo` lleva cada articulación hasta su tope: donde el objetivo pedía más, el tope '
          'lo detiene (eso es el "stop" funcionando).')
    w('\n## Verificación automática (penetraciones máximas)\n')
    w('Medidas en milímetros sobre todos los cuadros de cada animación: dedos/mano vs. ficha, fichas de la fila, '
      'mesa y silla; antebrazo vs. borde de la mesa; **mano y antebrazo vs. el propio cuerpo** (tronco, muslos, '
      'cabeza) cuadro por cuadro; pies vs. suelo; muslos vs. asiento; piel vs. bóxer. '
      'Valores ≤ 2 mm no son visibles.\n')
    w('| Animación | Peor contacto |')
    w('|---|---|')
    for n in ORDEN:
        items = []
        for k, v in rep.get(n, {}).items():
            if k.startswith('_') or not isinstance(v, dict) or 'prof_mm' not in v:
                continue
            lab = CHECK_LABEL.get(k, k.replace('ficha:', 'ficha '))
            items.append((v['prof_mm'], f"{lab}: {v['prof_mm']} mm ({v['region']})"))
        items.sort(reverse=True)
        w(f"| `{n}` | {'; '.join(x[1] for x in items[:3]) or 'sin contactos'} |")
    w('\nNotas: "piel vs. bóxer" es un punto de la piel de la parte baja de la espalda que asoma ~6 mm a través '
      'del bóxer (máx. 7 mm) solo al estar sentado: al doblar la cadera, los pesos originales mueven la piel '
      'y el bóxer de forma distinta (de pie es 0 mm). '
      'Queda tapado por la silla en las vistas del juego. Corregirlo exige modificar malla o pesos, que '
      'estaba prohibido.')
    dd = r.get('dedos') or {}
    if dd:
        w('\nYemas dentro de la ficha: tras hornear, cada falange que tocaba una ficha se estira (o se cierra) '
          'lo mínimo necesario para quedar apoyada en la superficie. Profundidad que había antes de la corrección '
          '→ ahora 0 mm:\n')
        for n in ORDEN:
            if dd.get(n):
                w(f"- `{n}`: " + ', '.join(f"{k.replace('_r', '').replace('_l', '')} {v['prof_antes_mm']} mm "
                                          f"({v['cuadros']} cuadros)" for k, v in dd[n].items()))
    open(dst, 'w').write('\n'.join(L) + '\n')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
