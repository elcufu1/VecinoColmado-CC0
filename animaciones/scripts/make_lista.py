"""Genera LISTA_ANIMACIONES.md a partir de reporte_verificacion.json.

Uso: python3 make_lista.py reporte_verificacion.json LISTA_ANIMACIONES.md
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
    'mesa': 'tablero', 'silla': 'silla', 'asiento': 'asiento', 'suelo': 'suelo', 'boxer': 'piel vs. bóxer',
}


def main(src, dst):
    r = json.load(open(src))
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
    w('- `fotos/` — JPG de frente, 3/4 y perfil en las poses clave.')
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
    w('- Ficha usada como referencia: 0.045 × 0.090 × 0.014 m. En `Agarrar_*` la ficha queda en la pinza '
      'pulgar-índice a partir del cuadro de agarre; en `Colocar_*` se suelta en el cuadro indicado abajo. '
      'Para que la ficha siga la mano, emparentarla al hueso `hand_r` entre agarre y suelta.')
    w('- Cuadros clave: Agarrar_Ficha_Cerca agarra en el cuadro 10; Agarrar_Ficha_Lejos en el 14; '
      'Colocar_Ficha_Cerca suelta en el 7; Colocar_Ficha_Lejos en el 11; Golpe_Ficha impacta en el 15; '
      'Pasar golpea en los cuadros 8 y 14.')
    w('- `Caminar` es un ciclo en el sitio a ~0.83 m/s (el juego mueve la raíz). Los bucles tienen el primer y '
      'el último cuadro iguales.')
    w('- Cada Action anima también los morfos faciales (expresiones); al mezclar animaciones, los morfos de la '
      'Action activa sustituyen a los anteriores.')
    w('- En el GLB las texturas opacas de piel y lengua se recomprimieron a JPEG para reducir peso '
      '(la malla, pesos, huesos y morfos son los mismos).')
    w('\n## Verificación automática (penetraciones máximas)\n')
    w('Medidas en milímetros sobre todos los cuadros de cada animación (dedos vs. ficha/mesa, '
      'brazos vs. borde de la mesa, piel vs. bóxer/silla/suelo). Valores ≤ 2 mm no son visibles.\n')
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
    w('\nNotas: "piel vs. bóxer" es un punto de la piel de la parte baja de la espalda/glúteo que asoma unos '
      '6–7 mm a través del bóxer al estar sentado; queda tapado por la silla en todas las vistas del juego. '
      'Se dejó así porque corregirlo exige modificar malla o pesos, que estaba prohibido. '
      'Los contactos de ficha (1–4 mm) son la yema del dedo apoyada en la ficha durante la pinza o el golpe.')
    open(dst, 'w').write('\n'.join(L) + '\n')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
