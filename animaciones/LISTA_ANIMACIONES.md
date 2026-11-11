# Lista de animaciones — VecinoColmado (Dominó Colmado)

Todas las animaciones son *Actions* separadas del armature `VecinoColmado_CC0` (53 huesos), a **24 fps**, horneadas cuadro a cuadro. No se modificó malla, pesos, huesos ni morfos: solo se crearon Actions (huesos + morfos faciales).

Archivos:

- `Vecino_Boxer_Animado.glb` — personaje + 23 animaciones (sin mesa ni silla), listo para el juego.
- `Vecino_Boxer_Animado.blend` — mismas Actions + escena `Previsualizacion_Animaciones` con mesa, silla, fichas y cámaras (línea de tiempo con marcadores por animación).
- `videos/` — un MP4 por animación (H.264, 1280×720, 24 fps) y `VIDEO_TODO_EL_CUERPO.mp4`.
- `scripts/` — código que genera todo (`blender -b Vecino_Boxer.blend --python scripts/final.py -- build <dir>`).

| # | Nombre (Action) | Cuadros | Duración | Bucle | Uso en el juego |
|---|---|---|---|---|---|
| 1 | `Idle_De_Pie` | 192 | 8.00 s | sí | Espera de pie / lobby (bucle). |
| 2 | `Caminar` | 28 | 1.17 s | sí | Desplazamiento (el juego mueve el personaje). |
| 3 | `Sentarse` | 100 | 4.17 s | no | Llegar a la mesa. |
| 4 | `Levantarse` | 90 | 3.75 s | no | Salir de la mesa. |
| 5 | `Idle_Sentado` | 144 | 6.00 s | sí | Espera de turno (bucle). |
| 6 | `Agarrar_Ficha_Cerca` | 22 | 0.92 s | no | Tomar una ficha propia para jugarla. |
| 7 | `Agarrar_Ficha_Lejos` | 28 | 1.17 s | no | Tomar una ficha propia para jugarla. |
| 8 | `Colocar_Ficha_Cerca` | 22 | 0.92 s | no | Jugar una ficha cerca del jugador. |
| 9 | `Colocar_Ficha_Lejos` | 30 | 1.25 s | no | Jugar una ficha en el extremo lejano de la mesa. |
| 10 | `Golpe_Ficha` | 34 | 1.42 s | no | Jugada final (tranque o capicúa). |
| 11 | `Pasar` | 26 | 1.08 s | no | Pasar turno. |
| 12 | `Barajar_Fichas` | 48 | 2.00 s | sí | Revolver fichas al inicio de la mano (bucle). |
| 13 | `Sostener_Fichas` | 72 | 3.00 s | sí | Mirar las fichas propias (bucle). |
| 14 | `Celebrar_Ganar` | 72 | 3.00 s | no | Ganar la mano/partida. |
| 15 | `Perder` | 76 | 3.17 s | no | Perder la mano/partida. |
| 16 | `Pensar` | 96 | 4.00 s | sí | Pensar la jugada (bucle). |
| 17 | `Saludar` | 48 | 2.00 s | no | Saludo al entrar/llegar jugadores. |
| 18 | `Senalar` | 40 | 1.67 s | no | Indicar jugada o jugador. |
| 19 | `Pulgar_Arriba` | 40 | 1.67 s | no | Aprobar jugada del compañero. |
| 20 | `Aplaudir` | 48 | 2.00 s | no | Felicitar a otro jugador. |
| 21 | `Reir` | 60 | 2.50 s | no | Reacción a una buena jugada/chiste. |
| 22 | `Enojado` | 50 | 2.08 s | no | Perder una jugada clave / protestar. |
| 23 | `Prueba_Rango_Completo` | 2382 | 99.25 s | no | Solo pruebas de rig (no usar en juego). |

Descripción de cada animación:

1. **Idle_De_Pie** — De pie: respira, cambia el peso de pierna, dedos relajados.
2. **Caminar** — Ciclo de caminar en el sitio (in place), 0.83 m/s.
3. **Sentarse** — De pie frente a la silla: se sienta y se arrima a la mesa con la silla.
4. **Levantarse** — Se separa de la mesa con la silla y se levanta.
5. **Idle_Sentado** — Sentado a la mesa: respira, mira las fichas, tamborilea los dedos.
6. **Agarrar_Ficha_Cerca** — Agarra una ficha parada de su fila con pinza limpia pulgar-índice (pulgar en la cara, índice detrás) y la levanta mirándola.
7. **Agarrar_Ficha_Lejos** — Agarra una ficha parada del otro extremo de su fila con pinza limpia pulgar-índice (pulgar en la cara, índice detrás) y la levanta mirándola.
8. **Colocar_Ficha_Cerca** — Lleva la ficha parada, la gira cara arriba mientras avanza y la deja en la mesa; vuelve a la pose sentada.
9. **Colocar_Ficha_Lejos** — Coloca la ficha lejos: la otra mano se apoya firme al lado de su fila, el cuerpo se estira y la ficha llega cara arriba.
10. **Golpe_Ficha** — Tranque/capicúa: levanta la ficha, la gira cara arriba en el aire y la planta fuerte en la mesa.
11. **Pasar** — Toca la mesa dos veces con los nudillos al lado de sus fichas ("paso").
12. **Barajar_Fichas** — Ambas manos revuelven fichas boca abajo en círculos sobre la mesa (antes de repartir: todavía no hay fichas paradas).
13. **Sostener_Fichas** — Cuida sus fichas paradas: las dos manos las encierran por los extremos, las mira y mueve los dedos (bucle).
14. **Celebrar_Ganar** — Celebra: puño arriba dos veces y aplaude.
15. **Perder** — Pierde: se lleva las manos a la cabeza y se echa atrás en la silla.
16. **Pensar** — Piensa: mano en la barbilla, tamborilea con la otra mano (bucle).
17. **Saludar** — Saluda con la mano abierta.
18. **Senalar** — Señala con el índice hacia el centro/otro jugador.
19. **Pulgar_Arriba** — Pulgar arriba con sonrisa y asentimiento.
20. **Aplaudir** — Aplaude cuatro veces.
21. **Reir** — Se ríe: hombros y cabeza rebotan, cara de risa.
22. **Enojado** — Enojado: golpe con la palma abierta en la mesa y cara de enojo.
23. **Prueba_Rango_Completo** — Demostración: mueve cada parte una por una y luego todo junto. Segmentos (cuadro local): Cuello_Cabeza (12), Hombros (224), Brazos (344), Codos (550), Munecas (666), Dedos (832), Dedo_thumb (948), Dedo_index (976), Dedo_middle (1004), Dedo_ring (1032), Dedo_pinky (1060), Contar (1086), Columna (1238), Cadera (1436), Rodillas (1588), Tobillos_DedosPie (1806), Cara (2020), Todo_Junto (2270).

## Convenciones para integrar en el juego

- El personaje mira hacia **−Y** (de frente a la mesa); su izquierda es **+X**. Origen del armature = entre los pies, de pie delante de la silla.
- Mesa de referencia 1.15 × 1.15 m, paño a 0.806 m; borde de la mesa más cercano en y = −0.19 m. Silla: asiento a 0.46 m; centrada en y = +0.14 m cuando está sentado y en y = +0.27 m cuando está de pie (`Sentarse` acerca la silla, `Levantarse` la aleja; mover la silla en el juego en esos tramos).
- Ficha de referencia: 0.045 × 0.090 × 0.014 m. Las 7 fichas del jugador están **paradas de canto** en una fila delante de él (centro y = −0.38 m, x = −0.156 … +0.156 m cada 0.052 m, base sobre el paño), con la cara de puntos mirando al jugador. Las agarra de pie con una pinza limpia pulgar-índice (pulgar en la cara, índice detrás; medio, anular y meñique relajados), la sostiene parada y sin girarla raro, y al jugar la lleva hasta el paño (x ≈ −0.235 m), la apoya parada y la suelta: la ficha cae boca arriba sobre su borde. En el .blend la escena de vista previa muestra todo esto.
- Para que la ficha siga la mano en el juego: emparentarla al hueso `hand_r` entre el cuadro de agarre y el de suelta (la posición relativa es constante en ese tramo).
- Cuadros clave: Agarrar_Ficha_Cerca agarra en el cuadro 11 (ficha 3 de la fila); Agarrar_Ficha_Lejos en el 15 (ficha 7, la del otro extremo); Colocar_Ficha_Cerca suelta en el 9; Colocar_Ficha_Lejos en el 12; Golpe_Ficha impacta y suelta en el 15; Pasar golpea en los cuadros 8 y 14.
- `Caminar` es un ciclo en el sitio a ~0.83 m/s (el juego mueve la raíz). Los bucles tienen el primer y el último cuadro iguales.
- Cada Action anima también los morfos faciales (expresiones); al mezclar animaciones, los morfos de la Action activa sustituyen a los anteriores.
- En el GLB las texturas opacas de piel y lengua se recomprimieron a JPEG para reducir peso (la malla, pesos, huesos y morfos son los mismos).

## Límites de articulación ("stops")

Cada uno de los 53 huesos tiene un rango de rotación fijo y anatómico. Se aplica dos veces:

1. **Al hornear**: cada rotación local se recorta a su rango antes de escribir la Action (las animaciones ya vienen dentro de los límites; no dependen del constraint).
2. **En el rig** (`.blend`): cada hueso lleva un constraint *Limit Rotation* (`Limite_anatomico`, espacio local). Para codo, hombro, muñeca, cadera y dedos del pie el rango real es swing/twist (balanceo + giro sobre el eje del hueso) y el constraint lleva la caja Euler que lo contiene.

Rangos (grados, lado izquierdo; el derecho es el espejo: Y y Z con signo invertido):

| Articulación | Modo | X | Y | Z |
|---|---|---|---|---|
| Pelvis | Euler XZY | -35…45 (flexión adelante / atrás) | -35…35 (giro) | -25…25 (inclinación lateral) |
| Columna lumbar (spine_01) | Euler XZY | -15…30 (flexión / extensión) | -20…20 (giro) | -15…15 (inclinación lateral) |
| Columna torácica (spine_02) | Euler XZY | -15…30 (flexión / extensión) | -20…20 (giro) | -15…15 (inclinación lateral) |
| Columna alta (spine_03) | Euler XZY | -15…30 (flexión / extensión) | -20…20 (giro) | -15…15 (inclinación lateral) |
| Cuello | Euler XZY | -30…35 (flexión / extensión) | -35…35 (giro) | -20…20 (inclinación lateral) |
| Cabeza | Euler XZY | -35…30 (flexión / extensión) | -45…45 (giro) | -20…20 (inclinación lateral) |
| Clavícula (hombro) | Euler XYZ | -20…25 (protracción / retracción) | -10…10 (giro) | -20…25 (elevación / depresión) |
| Hombro (upperarm) | swing/twist | -90…130 (balanceo adelante / atrás) | -105…105 (rotación interna / externa) | -80…110 (balanceo lateral) |
| Codo (lowerarm) | swing/twist | -48…100 (flexión (desde reposo 45.5°)) | -85…85 (pronación / supinación) | -12…12 (desvío lateral) |
| Muñeca (hand) | swing/twist | -70…80 (flexión palmar / extensión) | -28…28 (giro residual) | -35…22 (desviación radial / cubital) |
| Cadera (thigh) | swing/twist | -125…30 (extensión / flexión) | -40…40 (rotación interna / externa) | -45…35 (abducción / aducción) |
| Rodilla (calf) | Euler XYZ | -2…150 (flexión) | -12…12 (rotación tibial) | -4…4 (varo / valgo) |
| Tobillo (foot) | Euler XZY | -32…50 (flexión plantar / dorsal) | -18…18 (giro) | -25…30 (inversión / eversión) |
| Dedos del pie (ball) | swing/twist | -55…40 (flexión / extensión) | -8…8 (giro) | -8…8 (desvío) |
| Pulgar falange 1 (thumb_01) | Euler YXZ | -25…50 (flexión) | -35…40 (giro) | -25…60 (oposición / separación) |
| Pulgar falange 2 (thumb_02) | Euler YXZ | -12…60 (flexión) | -6…6 (giro) | -6…6 (desvío) |
| Pulgar falange 3 (thumb_03) | Euler YXZ | -20…80 (flexión) | -6…6 (giro) | -6…6 (desvío) |
| Dedos falange 1 (index/middle/ring/pinky _01) | Euler YXZ | -25…92 (flexión) | -6…6 (giro) | -25…25 (separación) |
| Dedos falange 2 (_02) | Euler YXZ | -6…108 (flexión) | -6…6 (giro) | -6…6 (desvío) |
| Dedos falange 3 (_03) | Euler YXZ | -6…82 (flexión) | -6…6 (giro) | -6…6 (desvío) |

Verificación numérica:

- Se comprobaron 199.863 rotaciones (53 huesos × todos los cuadros de las 23 Actions). Exceso máximo sobre el rango: **0.0001°** (ninguna animación excede los límites).
- Con los 53 constraints activos, la pose evaluada se comparó con la pose sin constraints en los 3771 cuadros de la línea de tiempo: diferencia máxima **0.0°** (los constraints no alteran nada de lo horneado).
- `Prueba_Rango_Completo` lleva cada articulación hasta su tope: donde el objetivo pedía más, el tope lo detiene (eso es el "stop" funcionando).

## Verificación automática (penetraciones máximas)

Medidas en milímetros sobre todos los cuadros de cada animación: dedos/mano vs. ficha, fichas de la fila, mesa y silla; antebrazo vs. borde de la mesa; **mano y antebrazo vs. el propio cuerpo** (tronco, muslos, cabeza) cuadro por cuadro; pies vs. suelo; muslos vs. asiento; piel vs. bóxer. Valores ≤ 2 mm no son visibles.

| Animación | Peor contacto |
|---|---|
| `Idle_De_Pie` | sin contactos |
| `Caminar` | sin contactos |
| `Sentarse` | piel vs. bóxer: 7.1 mm (tronco) |
| `Levantarse` | piel vs. bóxer: 6.8 mm (tronco) |
| `Idle_Sentado` | piel vs. bóxer: 5.8 mm (tronco) |
| `Agarrar_Ficha_Cerca` | piel vs. bóxer: 5.8 mm (tronco) |
| `Agarrar_Ficha_Lejos` | piel vs. bóxer: 5.8 mm (tronco) |
| `Colocar_Ficha_Cerca` | piel vs. bóxer: 5.8 mm (tronco) |
| `Colocar_Ficha_Lejos` | piel vs. bóxer: 6.7 mm (tronco) |
| `Golpe_Ficha` | piel vs. bóxer: 5.8 mm (tronco) |
| `Pasar` | piel vs. bóxer: 5.8 mm (tronco) |
| `Barajar_Fichas` | piel vs. bóxer: 5.6 mm (tronco) |
| `Sostener_Fichas` | piel vs. bóxer: 5.8 mm (tronco) |
| `Celebrar_Ganar` | piel vs. bóxer: 5.8 mm (tronco) |
| `Perder` | piel vs. bóxer: 5.8 mm (tronco) |
| `Pensar` | piel vs. bóxer: 5.8 mm (tronco) |
| `Saludar` | piel vs. bóxer: 5.8 mm (tronco) |
| `Senalar` | piel vs. bóxer: 5.8 mm (tronco) |
| `Pulgar_Arriba` | piel vs. bóxer: 5.8 mm (tronco) |
| `Aplaudir` | piel vs. bóxer: 5.8 mm (tronco) |
| `Reir` | piel vs. bóxer: 5.8 mm (tronco) |
| `Enojado` | piel vs. bóxer: 5.8 mm (tronco) |
| `Prueba_Rango_Completo` | piel vs. bóxer: 5.6 mm (tronco) |

Notas: "piel vs. bóxer" es un punto de la piel de la parte baja de la espalda que asoma ~6 mm a través del bóxer (máx. 7 mm) solo al estar sentado: al doblar la cadera, los pesos originales mueven la piel y el bóxer de forma distinta (de pie es 0 mm). Queda tapado por la silla en las vistas del juego. Corregirlo exige modificar malla o pesos, que estaba prohibido.

Yemas dentro de la ficha: tras hornear, cada falange que tocaba una ficha se estira (o se cierra) lo mínimo necesario para quedar apoyada en la superficie. Profundidad que había antes de la corrección → ahora 0 mm:

- `Agarrar_Ficha_Cerca`: thumb 2.5 mm (20 cuadros), index 4.4 mm (15 cuadros)
- `Agarrar_Ficha_Lejos`: thumb 2.5 mm (18 cuadros), index 4.4 mm (17 cuadros)
- `Colocar_Ficha_Cerca`: thumb 2.5 mm (12 cuadros), index 4.4 mm (12 cuadros), middle 5.6 mm (5 cuadros), ring 1.2 mm (5 cuadros)
- `Colocar_Ficha_Lejos`: thumb 2.5 mm (15 cuadros), index 4.4 mm (15 cuadros)
- `Golpe_Ficha`: thumb 2.5 mm (18 cuadros), index 6.1 mm (19 cuadros), middle 6.9 mm (10 cuadros), ring 6.7 mm (12 cuadros)
