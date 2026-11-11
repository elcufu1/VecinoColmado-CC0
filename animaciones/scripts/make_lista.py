"""Genera LISTA_ANIMACIONES.md a partir de reporte_verificacion.json.

Uso: python3 make_lista.py reporte_verificacion.json LISTA_ANIMACIONES.md [limites_rotacion.json]
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vc_domino as DOM  # noqa: E402

PARTIDA_ACTIONS = ['Salida_Doble_Seis', 'Agarrar_Ficha_Cerca', 'Agarrar_Ficha_Lejos', 'Colocar_Doble',
                   'Colocar_Izq_Lejos', 'Colocar_Esquina', 'Colocar_Der_Cerca', 'Colocar_Der_Frente', 'Pasar',
                   'Domino_Golpe', 'Capicua_Golpe_Celebrar', 'Tranque']
ORDEN = ['Idle_De_Pie', 'Caminar', 'Sentarse', 'Levantarse', 'Idle_Sentado'] + PARTIDA_ACTIONS + [
         'Barajar_Fichas', 'Sostener_Fichas', 'Celebrar_Ganar', 'Perder',
         'Pensar', 'Saludar', 'Senalar', 'Pulgar_Arriba', 'Aplaudir', 'Reir', 'Enojado',
         'Prueba_Rango_Completo']
FOTOS = [
    ('01_salida_doble_seis_al_centro.jpg', 'Salida: el doble seis cae atravesado en el centro.'),
    ('02_agarra_ficha_parada_en_pinza.jpg', 'Agarra una ficha parada de su fila con pinza pulgar-índice.'),
    ('03_coloca_casando_numero_con_numero.jpg', 'Coloca 3-5 en el extremo derecho: el 3 toca al 3.'),
    ('04_doble_atravesado_y_esquina.jpg', 'Cadena con dobles atravesados y la esquina (forma de L) en el borde.'),
    ('05_pasa_tocando_la_mesa.jpg', 'Pasa: toca la mesa con los nudillos, sin agarrar ficha.'),
    ('06_domino_golpe_final.jpg', 'Dominó: planta de golpe su última ficha.'),
    ('07_capicua_golpe.jpg', 'Capicúa: cámara cinemática en el golpe, texto y chispas (efectos de ejemplo).'),
    ('08_capicua_celebracion.jpg', 'Capicúa: celebración con los dos puños arriba.'),
]
NOMBRES = DOM.JUGADORES

CHECK_LABEL = {
    'riel_cerca': 'borde de la mesa (lado del jugador)', 'riel_lejos': 'borde lejano de la mesa',
    'mesa': 'tablero', 'mesa_pano': 'paño de la mesa', 'silla': 'silla', 'asiento': 'asiento',
    'silla_asiento': 'asiento de la silla', 'suelo': 'suelo', 'boxer': 'piel vs. bóxer',
    'cuerpo_r': 'mano/antebrazo der. vs. cuerpo', 'cuerpo_l': 'mano/antebrazo izq. vs. cuerpo',
}


def fmt_t(t):
    return f"{t[0]}-{t[1]}" if t else '—'


def partida_docs(w, tl):
    est = DOM.partida()
    w('\n## Reglas del dominó implementadas (estilo dominicano)\n')
    w('- Por parejas: el Vecino y su compañero (enfrente) contra los otros dos. Juego de doble seis: '
      '**28 fichas, 7 por jugador**, sin pozo.')
    w('- **Salida**: en la primera mano sale quien tiene el doble seis y lo pone en el centro de la mesa, '
      '**atravesado**. El turno sigue hacia la derecha (Vecino → Derecha → Compañero → Izquierda).')
    w('- **Casar**: cada ficha se pone en uno de los dos extremos de la cadena y el número que casa **toca al número '
      'igual** (la mitad que casa queda pegada al extremo; la otra mitad es el nuevo extremo).')
    w('- **Dobles atravesados**: los dobles van perpendiculares a la cadena (el extremo sigue siendo ese número).')
    w('- **Esquinas**: cuando la siguiente ficha recta ya no cabe en el paño (contando una ficha de margen para '
      'poder doblar), la cadena dobla 90° formando una L. Extremo derecho del Vecino: crece hacia su derecha (−X), '
      'dobla hacia él (+Y) y luego hacia su izquierda (+X). Extremo izquierdo: crece hacia +X, dobla hacia el '
      'fondo (−Y) y luego hacia −X. Delante de su fila (y > −0.45 m) no se juega.')
    w('- **Pasar**: solo se pasa si ninguna ficha casa en ningún extremo (el validador lo comprueba). El que pasa '
      'toca la mesa, sin agarrar ficha.')
    w('- **Dominó**: gana la pareja del que pone su última ficha (la planta de golpe). **Capicúa**: el dominó con '
      'una ficha (no doble) que casaba en los DOS extremos; en muchas mesas da puntos extra (el bono lo decide el '
      'juego).')
    w('- **Tranque**: si nadie puede jugar, se acuestan las fichas que quedan y se cuentan los puntos.')
    w('\nLa geometría y las reglas están en `scripts/vc_domino.py` (Python puro): `validate()` reproduce la partida y '
      'comprueba 28 fichas, 7 por mano, turnos, que cada ficha case, que cada pase sea legal, que el Vecino domine '
      'y que su última ficha sea capicúa. `search(60)` regenera exactamente esta partida.')
    w('\n### Partida de ejemplo (la que muestran las animaciones)\n')
    w('Mano del Vecino: ' + ', '.join(fmt_t(t) for t in DOM.MANOS[0]) + '. Su fila (hueco 0 = su derecha, −X → '
      'hueco 6 = su izquierda): ' + ', '.join(f'{i}: {fmt_t(t)}' for i, t in enumerate(DOM.FILA)) + '.\n')
    w('| # | Jugador | Ficha | Extremo | Casa con | Tipo | Centro (x, y) m | Eje largo |')
    w('|---|---|---|---|---|---|---|---|')
    for st in est:
        pl = st['placed']
        if pl is None:
            w(f"| {st['i']} | {NOMBRES[st['player']]} | pasa | — | — | — | — | — |")
            continue
        ax = 'X' if abs(pl['axis'][0]) > 0.5 else 'Y'
        lado = {'C': 'centro', 'D': 'derecho', 'I': 'izquierdo'}[st['side']]
        w(f"| {st['i']} | {NOMBRES[st['player']]} | {fmt_t(st['tile'])} | {lado} | "
          f"{pl['match'] if st['side'] != 'C' else '—'} | {pl['kind']}{' ¡CAPICÚA!' if st['capicua'] else ''} | "
          f"({pl['c'][0]:.3f}, {pl['c'][1]:.3f}) | {ax} |")
    w('\n## Cómo llama el juego a cada animación\n')
    w('Cada Action de la partida está hecha para una jugada concreta de la partida de ejemplo: la ficha termina '
      '**exactamente** en su hueco (centro y eje de la tabla), cara arriba, con el número que casa tocando al igual. '
      'Para otras jugadas el juego elige la variante del mismo tipo y ajusta el destino así:\n')
    w('1. Elegir la Action por tipo de hueco: salida → `Salida_Doble_Seis`; doble → `Colocar_Doble`; esquina → '
      '`Colocar_Esquina`; ficha en línea → `Colocar_Der_Cerca` / `Colocar_Der_Frente` / `Colocar_Izq_Lejos` '
      '(la de destino más parecido); última ficha → `Domino_Golpe`, o `Capicua_Golpe_Celebrar` si casa en los dos '
      'extremos; sin jugada → `Pasar`; trancado → `Tranque`. Antes de colocar, `Agarrar_Ficha_Cerca` (huecos 0–3 de '
      'la fila) o `Agarrar_Ficha_Lejos` (huecos 4–6).')
    w('2. Emparentar la ficha al hueso `hand_r` desde el cuadro de agarre hasta el de suelta. En las fichas que van '
      'a lo largo de X la ficha **gira 90° entre las yemas** mientras se lleva (se suelta apaisada) en los '
      'cuadros de la columna «Giro»: en ese tramo el offset ficha→mano rota 90° alrededor del eje de la pinza '
      '(normal a la cara) y la ficha se desliza para que la pinza quede en la esquina superior del canto largo.')
    w('3. En el cuadro de suelta el juego toma la ficha y la hace caer sobre su canto inferior (el que apoya en el '
      'paño) hasta quedar acostada, en los cuadros de caída indicados, terminando en la posición y orientación '
      'del hueco real (centro, eje largo y mitad que casa hacia el extremo). Si el hueco real está a pocos cm del '
      'de referencia, la caída lo absorbe; si está lejos, mover el objetivo IK de la mano no es posible en el GLB: '
      'conviene elegir la variante más cercana.')
    w('4. La ficha de la fila no se mueve sola: el hueco queda vacío (en la vista previa se ve el hueco); el juego '
      'puede correr las demás si quiere.\n')
    w('| Action | Jugada | Extremo / tipo | Destino centro (x, y) m | Eje largo | Cae hacia | Suelta | '
      'Agarre | Giro 90° en la pinza | Suelta en | Caída (cuadros) |')
    w('|---|---|---|---|---|---|---|---|---|---|---|')
    for n in PARTIDA_ACTIONS:
        t = tl.get(n)
        if not t:
            continue
        j = t.get('juego', {})
        sl = j.get('slot')
        fi = j.get('ficha') or {}
        if sl:
            ax = 'X' if abs(sl['axis'][0]) > 0.5 else 'Y'
            u = sl['u']
            cae = {(1, 0): '+X (su izq.)', (-1, 0): '−X (su der.)', (0, 1): '+Y (hacia él)',
                   (0, -1): '−Y (al fondo)'}.get((round(u[0]), round(u[1])), str(u))
            lado = {'C': 'centro', 'D': 'derecho', 'I': 'izquierdo'}[sl['side']]
            w(f"| `{n}` | {j.get('jugada')} | {lado} / {sl['kind']} | ({sl['c'][0]:.3f}, {sl['c'][1]:.3f}) | {ax} | "
              f"{cae} | {'apaisada' if sl.get('suelta') == 'apaisada' else 'de pie'} | "
              f"{fi.get('agarre') if fi.get('agarre') is not None else 'ya en la mano'} | "
              f"{'%d–%d' % tuple(fi['giro']) if fi.get('giro') else '—'} | {fi.get('suelta')} | "
              f"{fi.get('caida')} |")
        else:
            extra = {'Pasar': 'golpes en los cuadros 8 y 14', 'Tranque': 'golpes en 8 y 14; acuesta su fila'}
            w(f"| `{n}` | {j.get('jugada', '—')} | {extra.get(n, '—')} | — | — | — | — | "
              f"{fi.get('agarre', '—') if fi else '—'} | — | — | — |")
    w('\nNotas de la tabla: «de pie» = la ficha se apoya parada sobre su canto corto, algo inclinada, y cae hacia '
      'el fondo (dobles y salida, eje largo en Y). «apaisada» = se apoya sobre su canto largo con la cara hacia el '
      'jugador y cae hacia el fondo (fichas a lo largo de X): así la muñeca no tiene que girar 90°. En los dos casos '
      'la cara de puntos queda arriba. `Colocar_Esquina` inclina el cuerpo hacia su derecha porque la esquina está '
      'junto al borde del paño. Al terminar `Domino_Golpe` y `Capicua_Golpe_Celebrar` la mano izquierda queda a un '
      'lado del paño (en su sitio de reposo cae la última ficha).')
    w('\nEn el .blend cada Action muestra la cadena tal como estaba **antes** de esa jugada (objetos `CadenaNN`, con '
      'sus puntos) y solo las fichas que le quedan en la fila (`Fila1`…`Fila7`).')
    w('\n### Capicúa: cinemática y efectos que dispara el juego\n')
    tc = tl.get('Capicua_Golpe_Celebrar', {})
    ev = (tc.get('juego') or {}).get('eventos') or {}
    if ev:
        w('`Capicua_Golpe_Celebrar` está animada a velocidad real (24 fps); la cámara lenta la pone el juego. '
          'Cuadros (desde 0) en los que disparar cada efecto:\n')
        w('| Cuadro | Evento | Qué hace el juego |')
        w('|---|---|---|')
        w(f"| 0 | inicio | Cambiar a la cámara cinemática (`Capicua_Camara`), bajar música, ocultar el resto de la UI. |")
        w(f"| {ev['slowmo_ini']} | inicio de cámara lenta | Escala de tiempo del personaje, cámara y partículas a "
          f"**0.35×** (rampa de 4 cuadros). Sonido: «whoosh» grave mientras levanta y lleva la ficha. |")
        w(f"| {ev['impacto']} | golpe | Sonido de **golpe fuerte** de ficha contra madera; **temblor** de la mesa y "
          f"todas sus fichas ({ev['temblor'][0]}–{ev['temblor'][1]}: 3–5 mm, amortiguado); **destello** blanco-dorado "
          f"de 3–4 cuadros en la ficha (y un flash de pantalla suave); la cámara ya trae su propio temblor. |")
        w(f"| {ev['texto']} | texto | Letras grandes **«¡CAPICÚA!»** en pantalla: escala 0 → 1.25 → 1.0 en 6 cuadros, "
          f"dorado con contorno oscuro, leve pulso; visibles ~2.5 s. |")
        w(f"| {ev['particulas']} | partículas | Estallido de chispas doradas/blancas desde la ficha (40–60 partículas, "
          f"0.5–1.2 m/s, gravedad, vida ~1 s) y destellos alrededor del texto. |")
        w(f"| {ev['slowmo_fin']} | fin de cámara lenta | Volver a 1.0× (rampa de 6 cuadros). Sonido: grito/ovación "
          f"«¡Capicúa!». |")
        w(f"| {ev['celebracion'][0]}–{ev['celebracion'][1]} | celebración | Puños arriba; mantener texto; "
          f"confeti opcional. |")
        w(f"| {ev['fin']} | fin | Volver a la cámara de juego y mostrar el marcador con el bono de capicúa. |")
        w('\nCámara: objeto `Camara_Capicua` con la Action `Capicua_Camara` (un slot para posición y rotación del '
          'objeto y otro para la focal de la cámara, 32 → 40 → 38 mm), cuadros 0–120 con la misma numeración que la '
          'Action del personaje. Recorrido: plano general desde delante a la izquierda → se acerca a la ficha mientras el Vecino '
          'la lleva → primer plano con temblor en el golpe → se abre para ver la celebración. Está hecha para el hueco '
          'de la partida de ejemplo: para otro hueco, desplazar la cámara la diferencia entre el hueco real y el de '
          'referencia. No va en el GLB (el GLB lleva solo el personaje).')
        w('\nLa colección `FX_Capicua_Previsualizacion` del .blend (texto 3D pegado a la cámara, chispas y luz '
          '`Destello_Capicua`) es solo una referencia visual de los efectos de arriba; el juego debe hacerlos con su '
          'propia interfaz y sistema de partículas.')
    w('\n### Pasar y tranque\n')
    w('- `Pasar`: toca la mesa dos veces con los nudillos entre su fila y la cadena (cuadros 8 y 14), sin agarrar '
      'ficha. Sonido de «toc toc» en esos cuadros.')
    tt = (tl.get('Tranque', {}).get('juego') or {})
    if tt.get('acuesta_fila'):
        w('- `Tranque`: toca la mesa (8 y 14) y luego acuesta cara arriba las fichas que le quedan, de una en una '
          '(' + ', '.join(f'{n} en el cuadro {f}' for n, f in tt['acuesta_fila']) + '), para contar los puntos. '
          'Estado de mesa ilustrativo (le quedan ' + ', '.join(fmt_t(tuple(x)) for x in tt.get('tranque', [])) + ').')


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
    w(f'- `Vecino_Boxer_Animado.glb` — personaje + {len(ORDEN)} animaciones (sin mesa, silla ni fichas), listo '
      'para el juego.')
    w('- `Vecino_Boxer_Animado.blend` — mismas Actions + escena `Previsualizacion_Animaciones` con mesa, silla, '
      'fichas con sus puntos reales, la cadena de la partida y cámaras (línea de tiempo con marcadores por '
      'animación). Incluye la cámara cinemática `Camara_Capicua` (Action de cámara `Capicua_Camara`) y la colección `FX_Capicua_Previsualizacion` (texto, chispas y destello de ejemplo).')
    w('- `fotos_partida/` — fotos (1280×720, Eevee) de los momentos clave de la partida (ver abajo).')
    w('- `videos/` — videos de la entrega anterior (antes de las reglas del dominó): siguen valiendo para las '
      'animaciones que no cambiaron (de pie, caminar, sentarse/levantarse, idle y gestos). Los de `Agarrar_*` y '
      '`Pasar` y el tramo de mesa de `VIDEO_TODO_EL_CUERPO.mp4` muestran la versión anterior (sin cadena ni '
      'reglas); por indicación de JuAn esta vez no se re-renderizaron videos.')
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
      'con la cara de puntos mirando al jugador (el público ve el dorso). Las agarra de pie con una pinza limpia '
      'pulgar-índice (pulgar en la cara, índice detrás; medio, anular y meñique relajados). Cómo se colocan en la '
      'cadena: ver «Cómo llama el juego a cada animación».')
    w('- Para que la ficha siga la mano en el juego: emparentarla al hueso `hand_r` entre el cuadro de agarre y el '
      'de suelta (la posición relativa es constante en ese tramo).')
    w('- Cuadros clave de agarre y suelta: ver la tabla de integración de la partida.')
    w('- `Caminar` es un ciclo en el sitio a ~0.83 m/s (el juego mueve la raíz). Los bucles tienen el primer y '
      'el último cuadro iguales.')
    w('- Las animaciones de la partida (ver secciones siguientes) sustituyen a las antiguas `Colocar_Ficha_Cerca`, '
      '`Colocar_Ficha_Lejos` y `Golpe_Ficha`, que se eliminaron.')
    w('- Cada Action anima también los morfos faciales (expresiones); al mezclar animaciones, los morfos de la '
      'Action activa sustituyen a los anteriores.')
    w('- En el GLB las texturas opacas de piel y lengua se recomprimieron a JPEG para reducir peso '
      '(la malla, pesos, huesos y morfos son los mismos).')
    partida_docs(w, tl)
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
          f"{len(ORDEN)} Actions). Exceso máximo sobre el rango: **{max(ex.values()):.4f}°** "
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
    w('\n## Fotos de la partida (`fotos_partida/`)\n')
    for fn, d in FOTOS:
        w(f'- `{fn}` — {d}')
    open(dst, 'w').write('\n'.join(L) + '\n')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
