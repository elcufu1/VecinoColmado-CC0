# Lista de animaciones — VecinoColmado (Dominó Colmado)

Todas las animaciones son *Actions* separadas del armature `VecinoColmado_CC0` (53 huesos), a **24 fps**, horneadas cuadro a cuadro. No se modificó malla, pesos, huesos ni morfos: solo se crearon Actions (huesos + morfos faciales).

Archivos:

- `Vecino_Boxer_Animado.glb` — personaje + 29 animaciones (sin mesa, silla ni fichas), listo para el juego.
- `Vecino_Boxer_Animado.blend` — mismas Actions + escena `Previsualizacion_Animaciones` con mesa, silla, fichas con sus puntos reales, la cadena de la partida y cámaras (línea de tiempo con marcadores por animación). Incluye la cámara cinemática `Camara_Capicua` (Action de cámara `Capicua_Camara`) y la colección `FX_Capicua_Previsualizacion` (texto, chispas y destello de ejemplo).
- `fotos_partida/` — fotos (1280×720, Eevee) de los momentos clave de la partida (ver abajo).
- `videos/` — videos de la entrega anterior (antes de las reglas del dominó): siguen valiendo para las animaciones que no cambiaron (de pie, caminar, sentarse/levantarse, idle y gestos). Los de `Agarrar_*` y `Pasar` y el tramo de mesa de `VIDEO_TODO_EL_CUERPO.mp4` muestran la versión anterior (sin cadena ni reglas); por indicación de JuAn esta vez no se re-renderizaron videos.
- `scripts/` — código que genera todo (`blender -b Vecino_Boxer.blend --python scripts/final.py -- build <dir>`).

| # | Nombre (Action) | Cuadros | Duración | Bucle | Uso en el juego |
|---|---|---|---|---|---|
| 1 | `Idle_De_Pie` | 192 | 8.00 s | sí | Espera de pie / lobby (bucle). |
| 2 | `Caminar` | 28 | 1.17 s | sí | Desplazamiento (el juego mueve el personaje). |
| 3 | `Sentarse` | 100 | 4.17 s | no | Llegar a la mesa. |
| 4 | `Levantarse` | 90 | 3.75 s | no | Salir de la mesa. |
| 5 | `Idle_Sentado` | 144 | 6.00 s | sí | Espera de turno (bucle). |
| 6 | `Salida_Doble_Seis` | 46 | 1.92 s | no | Primera jugada de la primera mano (quien tiene el doble seis sale). |
| 7 | `Agarrar_Ficha_Cerca` | 22 | 0.92 s | no | Tomar una ficha propia para jugarla (la fila sigue en su sitio, con el hueco). |
| 8 | `Agarrar_Ficha_Lejos` | 28 | 1.17 s | no | Tomar una ficha propia para jugarla (la fila sigue en su sitio, con el hueco). |
| 9 | `Colocar_Doble` | 30 | 1.25 s | no | Jugar un doble: siempre atravesado (aquí por el extremo derecho, hueco lejano). |
| 10 | `Colocar_Izq_Lejos` | 30 | 1.25 s | no | Jugar por el extremo izquierdo, hueco lejano. |
| 11 | `Colocar_Esquina` | 22 | 0.92 s | no | Jugar cuando la cadena llega al borde y dobla (ficha de esquina, en L). |
| 12 | `Colocar_Der_Cerca` | 22 | 0.92 s | no | Jugar por el extremo derecho, hueco cercano a su derecha. |
| 13 | `Colocar_Der_Frente` | 22 | 0.92 s | no | Jugar por el extremo derecho cuando la cadena ya dio la vuelta y pasa delante de él (hueco cercano, frente a su izquierda). |
| 14 | `Pasar` | 26 | 1.08 s | no | Pasar turno (no lleva). |
| 15 | `Domino_Golpe` | 64 | 2.67 s | no | Cuando juega su última ficha (se "domina"). Al terminar, el juego cuenta los puntos. |
| 16 | `Capicua_Golpe_Celebrar` | 120 | 5.00 s | no | Ganar dominando con capicúa (momento épico; ver eventos de cámara lenta, texto, partículas y sonido). |
| 17 | `Tranque` | 60 | 2.50 s | no | Cuando la partida se tranca (ningún jugador lleva). Estado de mesa ilustrativo. |
| 18 | `Barajar_Fichas` | 48 | 2.00 s | sí | Revolver fichas al inicio de la mano (bucle). |
| 19 | `Sostener_Fichas` | 72 | 3.00 s | sí | Mirar las fichas propias (bucle). |
| 20 | `Celebrar_Ganar` | 72 | 3.00 s | no | Ganar la mano/partida. |
| 21 | `Perder` | 76 | 3.17 s | no | Perder la mano/partida. |
| 22 | `Pensar` | 96 | 4.00 s | sí | Pensar la jugada (bucle). |
| 23 | `Saludar` | 48 | 2.00 s | no | Saludo al entrar/llegar jugadores. |
| 24 | `Senalar` | 40 | 1.67 s | no | Indicar jugada o jugador. |
| 25 | `Pulgar_Arriba` | 40 | 1.67 s | no | Aprobar jugada del compañero. |
| 26 | `Aplaudir` | 48 | 2.00 s | no | Felicitar a otro jugador. |
| 27 | `Reir` | 60 | 2.50 s | no | Reacción a una buena jugada/chiste. |
| 28 | `Enojado` | 50 | 2.08 s | no | Perder una jugada clave / protestar. |
| 29 | `Prueba_Rango_Completo` | 2382 | 99.25 s | no | Solo pruebas de rig (no usar en juego). |

Descripción de cada animación:

1. **Idle_De_Pie** — De pie: respira, cambia el peso de pierna, dedos relajados.
2. **Caminar** — Ciclo de caminar en el sitio (in place), 0.83 m/s.
3. **Sentarse** — De pie frente a la silla: se sienta y se arrima a la mesa con la silla.
4. **Levantarse** — Se separa de la mesa con la silla y se levanta.
5. **Idle_Sentado** — Sentado a la mesa: respira, mira las fichas, tamborilea los dedos.
6. **Salida_Doble_Seis** — Salida: agarra el doble seis parado del centro de su fila con pinza y lo pone atravesado en el centro de la mesa.
7. **Agarrar_Ficha_Cerca** — Agarra la ficha parada 1-1 de su fila (hueco 2) con pinza limpia pulgar-índice (pulgar en la cara, índice detrás) y la levanta mirándola.
8. **Agarrar_Ficha_Lejos** — Agarra la ficha parada 1-6 del otro extremo de su fila (hueco 6) con pinza limpia pulgar-índice (pulgar en la cara, índice detrás) y la levanta mirándola.
9. **Colocar_Doble** — Juega 1-1 en el extremo derecho (D) que pedía 1: el 1 toca al 1 de la cadena; el doble va atravesado (perpendicular a la cadena). Lleva la ficha parada, la apoya de pie junto al hueco y cae cara arriba en el hueco exacto.
10. **Colocar_Izq_Lejos** — Juega 1-6 en el extremo izquierdo (I) que pedía 6: el 6 toca al 6 de la cadena. Lleva la ficha parada, la gira 90° entre las yemas mientras la lleva, la apoya apaisada (sobre su canto largo) junto al hueco y cae cara arriba en el hueco exacto.
11. **Colocar_Esquina** — Juega 2-4 en el extremo derecho (D) que pedía 4: el 4 toca al 4 de la cadena; no cabe recta y la cadena dobla la esquina. Lleva la ficha parada, la gira 90° entre las yemas mientras la lleva, la apoya apaisada (sobre su canto largo) junto al hueco y cae cara arriba en el hueco exacto.
12. **Colocar_Der_Cerca** — Juega 3-5 en el extremo derecho (D) que pedía 3: el 3 toca al 3 de la cadena. Lleva la ficha parada, la gira 90° entre las yemas mientras la lleva, la apoya apaisada (sobre su canto largo) junto al hueco y cae cara arriba en el hueco exacto.
13. **Colocar_Der_Frente** — Juega 4-5 en el extremo derecho (D) que pedía 5: el 5 toca al 5 de la cadena. Lleva la ficha parada, la gira 90° entre las yemas mientras la lleva, la apoya apaisada (sobre su canto largo) junto al hueco y cae cara arriba en el hueco exacto.
14. **Pasar** — Pasa: no tiene ficha que case con ningún extremo; toca la mesa dos veces con los nudillos entre su fila y la cadena, sin agarrar nada.
15. **Domino_Golpe** — Dominó: levanta la última ficha (4-6), la planta de golpe en su hueco exacto y celebra con el puño.
16. **Capicua_Golpe_Celebrar** — ¡CAPICÚA! Su última ficha (4-6) casa en los dos extremos (D pide 4, I pide 6): la levanta alto mostrándola, la sostiene un instante, la planta de un golpe fuerte en su hueco exacto y celebra a lo grande (dos puños arriba, grito, señala la ficha).
17. **Tranque** — Tranque: nadie puede jugar; toca la mesa dos veces y luego acuesta cara arriba las fichas que le quedan, de una en una con la punta de los dedos, para contar los puntos.
18. **Barajar_Fichas** — Ambas manos revuelven fichas boca abajo en círculos sobre la mesa (antes de repartir: todavía no hay fichas paradas).
19. **Sostener_Fichas** — Cuida sus fichas paradas: las dos manos las encierran por los extremos, las mira y mueve los dedos (bucle).
20. **Celebrar_Ganar** — Celebra: puño arriba dos veces y aplaude.
21. **Perder** — Pierde: se lleva las manos a la cabeza y se echa atrás en la silla.
22. **Pensar** — Piensa: mano en la barbilla, tamborilea con la otra mano (bucle).
23. **Saludar** — Saluda con la mano abierta.
24. **Senalar** — Señala con el índice hacia el centro/otro jugador.
25. **Pulgar_Arriba** — Pulgar arriba con sonrisa y asentimiento.
26. **Aplaudir** — Aplaude cuatro veces.
27. **Reir** — Se ríe: hombros y cabeza rebotan, cara de risa.
28. **Enojado** — Enojado: golpe con la palma abierta en la mesa y cara de enojo.
29. **Prueba_Rango_Completo** — Demostración: mueve cada parte una por una y luego todo junto. Segmentos (cuadro local): Cuello_Cabeza (12), Hombros (224), Brazos (344), Codos (550), Munecas (666), Dedos (832), Dedo_thumb (948), Dedo_index (976), Dedo_middle (1004), Dedo_ring (1032), Dedo_pinky (1060), Contar (1086), Columna (1238), Cadera (1436), Rodillas (1588), Tobillos_DedosPie (1806), Cara (2020), Todo_Junto (2270).

## Convenciones para integrar en el juego

- El personaje mira hacia **−Y** (de frente a la mesa); su izquierda es **+X**. Origen del armature = entre los pies, de pie delante de la silla.
- Mesa de referencia 1.15 × 1.15 m, paño a 0.806 m; borde de la mesa más cercano en y = −0.19 m. Silla: asiento a 0.46 m; centrada en y = +0.14 m cuando está sentado y en y = +0.27 m cuando está de pie (`Sentarse` acerca la silla, `Levantarse` la aleja; mover la silla en el juego en esos tramos).
- Ficha de referencia: 0.045 × 0.090 × 0.014 m. Las 7 fichas del jugador están **paradas de canto** en una fila delante de él (centro y = −0.38 m, x = −0.156 … +0.156 m cada 0.052 m, base sobre el paño), con la cara de puntos mirando al jugador (el público ve el dorso). Las agarra de pie con una pinza limpia pulgar-índice (pulgar en la cara, índice detrás; medio, anular y meñique relajados). Cómo se colocan en la cadena: ver «Cómo llama el juego a cada animación».
- Para que la ficha siga la mano en el juego: emparentarla al hueso `hand_r` entre el cuadro de agarre y el de suelta (la posición relativa es constante en ese tramo).
- Cuadros clave de agarre y suelta: ver la tabla de integración de la partida.
- `Caminar` es un ciclo en el sitio a ~0.83 m/s (el juego mueve la raíz). Los bucles tienen el primer y el último cuadro iguales.
- Las animaciones de la partida (ver secciones siguientes) sustituyen a las antiguas `Colocar_Ficha_Cerca`, `Colocar_Ficha_Lejos` y `Golpe_Ficha`, que se eliminaron.
- Cada Action anima también los morfos faciales (expresiones); al mezclar animaciones, los morfos de la Action activa sustituyen a los anteriores.
- En el GLB las texturas opacas de piel y lengua se recomprimieron a JPEG para reducir peso (la malla, pesos, huesos y morfos son los mismos).

## Reglas del dominó implementadas (estilo dominicano)

- Por parejas: el Vecino y su compañero (enfrente) contra los otros dos. Juego de doble seis: **28 fichas, 7 por jugador**, sin pozo.
- **Salida**: en la primera mano sale quien tiene el doble seis y lo pone en el centro de la mesa, **atravesado**. El turno sigue hacia la derecha (Vecino → Derecha → Compañero → Izquierda).
- **Casar**: cada ficha se pone en uno de los dos extremos de la cadena y el número que casa **toca al número igual** (la mitad que casa queda pegada al extremo; la otra mitad es el nuevo extremo).
- **Dobles atravesados**: los dobles van perpendiculares a la cadena (el extremo sigue siendo ese número).
- **Esquinas**: cuando la siguiente ficha recta ya no cabe en el paño (contando una ficha de margen para poder doblar), la cadena dobla 90° formando una L. Extremo derecho del Vecino: crece hacia su derecha (−X), dobla hacia él (+Y) y luego hacia su izquierda (+X). Extremo izquierdo: crece hacia +X, dobla hacia el fondo (−Y) y luego hacia −X. Delante de su fila (y > −0.45 m) no se juega.
- **Pasar**: solo se pasa si ninguna ficha casa en ningún extremo (el validador lo comprueba). El que pasa toca la mesa, sin agarrar ficha.
- **Dominó**: gana la pareja del que pone su última ficha (la planta de golpe). **Capicúa**: el dominó con una ficha (no doble) que casaba en los DOS extremos; en muchas mesas da puntos extra (el bono lo decide el juego).
- **Tranque**: si nadie puede jugar, se acuestan las fichas que quedan y se cuentan los puntos.

La geometría y las reglas están en `scripts/vc_domino.py` (Python puro): `validate()` reproduce la partida y comprueba 28 fichas, 7 por mano, turnos, que cada ficha case, que cada pase sea legal, que el Vecino domine y que su última ficha sea capicúa. `search(60)` regenera exactamente esta partida.

### Partida de ejemplo (la que muestran las animaciones)

Mano del Vecino: 6-6, 4-6, 3-5, 1-6, 2-4, 4-5, 1-1. Su fila (hueco 0 = su derecha, −X → hueco 6 = su izquierda): 0: 4-6, 1: 2-4, 2: 1-1, 3: 6-6, 4: 3-5, 5: 4-5, 6: 1-6.

| # | Jugador | Ficha | Extremo | Casa con | Tipo | Centro (x, y) m | Eje largo |
|---|---|---|---|---|---|---|---|
| 0 | Vecino | 6-6 | centro | — | salida | (0.000, -0.700) | Y |
| 1 | Derecha | 5-6 | derecho | 6 | linea | (-0.068, -0.700) | X |
| 2 | Companero | 5-5 | derecho | 5 | doble | (-0.135, -0.700) | Y |
| 3 | Izquierda | 1-5 | derecho | 5 | linea | (-0.202, -0.700) | X |
| 4 | Vecino | 1-1 | derecho | 1 | doble | (-0.270, -0.700) | Y |
| 5 | Derecha | 1-4 | derecho | 1 | linea | (-0.337, -0.700) | X |
| 6 | Companero | 3-4 | derecho | 4 | linea | (-0.427, -0.700) | X |
| 7 | Izquierda | 0-3 | derecho | 3 | esquina | (-0.495, -0.677) | Y |
| 8 | Vecino | 1-6 | izquierdo | 6 | linea | (0.068, -0.700) | X |
| 9 | Derecha | 0-4 | derecho | 0 | linea | (-0.495, -0.587) | Y |
| 10 | Companero | 0-1 | izquierdo | 1 | linea | (0.157, -0.700) | X |
| 11 | Izquierda | 0-6 | izquierdo | 0 | linea | (0.247, -0.700) | X |
| 12 | Vecino | 2-4 | derecho | 4 | esquina | (-0.472, -0.520) | X |
| 13 | Derecha | 2-2 | derecho | 2 | doble | (-0.405, -0.520) | Y |
| 14 | Companero | 2-3 | derecho | 2 | linea | (-0.337, -0.520) | X |
| 15 | Izquierda | 3-6 | izquierdo | 6 | linea | (0.337, -0.700) | X |
| 16 | Vecino | 3-5 | derecho | 3 | linea | (-0.247, -0.520) | X |
| 17 | Derecha | 2-5 | derecho | 5 | linea | (-0.157, -0.520) | X |
| 18 | Companero | 1-3 | izquierdo | 3 | linea | (0.427, -0.700) | X |
| 19 | Izquierda | 0-2 | derecho | 2 | linea | (-0.067, -0.520) | X |
| 20 | Vecino | pasa | — | — | — | — | — |
| 21 | Derecha | 0-5 | derecho | 0 | linea | (0.023, -0.520) | X |
| 22 | Companero | pasa | — | — | — | — | — |
| 23 | Izquierda | 1-2 | izquierdo | 1 | esquina | (0.495, -0.722) | Y |
| 24 | Vecino | 4-5 | derecho | 5 | linea | (0.113, -0.520) | X |
| 25 | Derecha | 4-4 | derecho | 4 | doble | (0.180, -0.520) | Y |
| 26 | Companero | 2-6 | izquierdo | 2 | linea | (0.495, -0.812) | Y |
| 27 | Izquierda | pasa | — | — | — | — | — |
| 28 | Vecino | 4-6 | derecho | 4 | linea ¡CAPICÚA! | (0.247, -0.520) | X |

## Cómo llama el juego a cada animación

Cada Action de la partida está hecha para una jugada concreta de la partida de ejemplo: la ficha termina **exactamente** en su hueco (centro y eje de la tabla), cara arriba, con el número que casa tocando al igual. Para otras jugadas el juego elige la variante del mismo tipo y ajusta el destino así:

1. Elegir la Action por tipo de hueco: salida → `Salida_Doble_Seis`; doble → `Colocar_Doble`; esquina → `Colocar_Esquina`; ficha en línea → `Colocar_Der_Cerca` / `Colocar_Der_Frente` / `Colocar_Izq_Lejos` (la de destino más parecido); última ficha → `Domino_Golpe`, o `Capicua_Golpe_Celebrar` si casa en los dos extremos; sin jugada → `Pasar`; trancado → `Tranque`. Antes de colocar, `Agarrar_Ficha_Cerca` (huecos 0–3 de la fila) o `Agarrar_Ficha_Lejos` (huecos 4–6).
2. Emparentar la ficha al hueso `hand_r` desde el cuadro de agarre hasta el de suelta. En las fichas que van a lo largo de X la ficha **gira 90° entre las yemas** mientras se lleva (se suelta apaisada) en los cuadros de la columna «Giro»: en ese tramo el offset ficha→mano rota 90° alrededor del eje de la pinza (normal a la cara) y la ficha se desliza para que la pinza quede en la esquina superior del canto largo.
3. En el cuadro de suelta el juego toma la ficha y la hace caer sobre su canto inferior (el que apoya en el paño) hasta quedar acostada, en los cuadros de caída indicados, terminando en la posición y orientación del hueco real (centro, eje largo y mitad que casa hacia el extremo). Si el hueco real está a pocos cm del de referencia, la caída lo absorbe; si está lejos, mover el objetivo IK de la mano no es posible en el GLB: conviene elegir la variante más cercana.
4. La ficha de la fila no se mueve sola: el hueco queda vacío (en la vista previa se ve el hueco); el juego puede correr las demás si quiere.

| Action | Jugada | Extremo / tipo | Destino centro (x, y) m | Eje largo | Cae hacia | Suelta | Agarre | Giro 90° en la pinza | Suelta en | Caída (cuadros) |
|---|---|---|---|---|---|---|---|---|---|---|
| `Salida_Doble_Seis` | 0 | centro / salida | (0.000, -0.700) | Y | −Y (al fondo) | de pie | 11 | — | 29 | 5 |
| `Agarrar_Ficha_Cerca` | 4 | — | — | — | — | — | 11 | — | — | — |
| `Agarrar_Ficha_Lejos` | 8 | — | — | — | — | — | 15 | — | — | — |
| `Colocar_Doble` | 4 | derecho / doble | (-0.270, -0.700) | Y | −Y (al fondo) | de pie | ya en la mano | — | 12 | 5 |
| `Colocar_Izq_Lejos` | 8 | izquierdo / linea | (0.068, -0.700) | X | +X (su izq.) | apaisada | ya en la mano | 4–10 | 12 | 5 |
| `Colocar_Esquina` | 12 | derecho / esquina | (-0.472, -0.520) | X | −X (su der.) | apaisada | ya en la mano | 1–7 | 9 | 5 |
| `Colocar_Der_Cerca` | 16 | derecho / linea | (-0.247, -0.520) | X | +X (su izq.) | apaisada | ya en la mano | 1–7 | 9 | 5 |
| `Colocar_Der_Frente` | 24 | derecho / linea | (0.113, -0.520) | X | −X (su der.) | apaisada | ya en la mano | 1–7 | 9 | 5 |
| `Pasar` | 20 | golpes en los cuadros 8 y 14 | — | — | — | — | — | — | — | — |
| `Domino_Golpe` | 28 | derecho / linea | (0.247, -0.520) | X | −X (su der.) | apaisada | ya en la mano | 9–13 | 15 | 4 |
| `Capicua_Golpe_Celebrar` | 28 | derecho / linea | (0.247, -0.520) | X | −X (su der.) | apaisada | ya en la mano | 21–25 | 27 | 3 |
| `Tranque` | — | golpes en 8 y 14; acuesta su fila | — | — | — | — | — | — | — | — |

Notas de la tabla: «de pie» = la ficha se apoya parada sobre su canto corto, algo inclinada, y cae hacia el fondo (dobles y salida, eje largo en Y). «apaisada» = se apoya sobre su canto largo con la cara hacia el jugador y cae hacia el fondo (fichas a lo largo de X): así la muñeca no tiene que girar 90°. En los dos casos la cara de puntos queda arriba. `Colocar_Esquina` inclina el cuerpo hacia su derecha porque la esquina está junto al borde del paño. Al terminar `Domino_Golpe` y `Capicua_Golpe_Celebrar` la mano izquierda queda a un lado del paño (en su sitio de reposo cae la última ficha).

En el .blend cada Action muestra la cadena tal como estaba **antes** de esa jugada (objetos `CadenaNN`, con sus puntos) y solo las fichas que le quedan en la fila (`Fila1`…`Fila7`).

### Capicúa: cinemática y efectos que dispara el juego

`Capicua_Golpe_Celebrar` está animada a velocidad real (24 fps); la cámara lenta la pone el juego. Cuadros (desde 0) en los que disparar cada efecto:

| Cuadro | Evento | Qué hace el juego |
|---|---|---|
| 0 | inicio | Cambiar a la cámara cinemática (`Capicua_Camara`), bajar música, ocultar el resto de la UI. |
| 12 | inicio de cámara lenta | Escala de tiempo del personaje, cámara y partículas a **0.35×** (rampa de 4 cuadros). Sonido: «whoosh» grave mientras levanta y lleva la ficha. |
| 27 | golpe | Sonido de **golpe fuerte** de ficha contra madera; **temblor** de la mesa y todas sus fichas (27–33: 3–5 mm, amortiguado); **destello** blanco-dorado de 3–4 cuadros en la ficha (y un flash de pantalla suave); la cámara ya trae su propio temblor. |
| 28 | texto | Letras grandes **«¡CAPICÚA!»** en pantalla: escala 0 → 1.25 → 1.0 en 6 cuadros, dorado con contorno oscuro, leve pulso; visibles ~2.5 s. |
| 28 | partículas | Estallido de chispas doradas/blancas desde la ficha (40–60 partículas, 0.5–1.2 m/s, gravedad, vida ~1 s) y destellos alrededor del texto. |
| 40 | fin de cámara lenta | Volver a 1.0× (rampa de 6 cuadros). Sonido: grito/ovación «¡Capicúa!». |
| 42–64 | celebración | Puños arriba; mantener texto; confeti opcional. |
| 120 | fin | Volver a la cámara de juego y mostrar el marcador con el bono de capicúa. |

Cámara: objeto `Camara_Capicua` con la Action `Capicua_Camara` (un slot para posición y rotación del objeto y otro para la focal de la cámara, 32 → 40 → 38 mm), cuadros 0–120 con la misma numeración que la Action del personaje. Recorrido: plano general desde delante a la izquierda → se acerca a la ficha mientras el Vecino la lleva → primer plano con temblor en el golpe → se abre para ver la celebración. Está hecha para el hueco de la partida de ejemplo: para otro hueco, desplazar la cámara la diferencia entre el hueco real y el de referencia. No va en el GLB (el GLB lleva solo el personaje).

La colección `FX_Capicua_Previsualizacion` del .blend (texto 3D pegado a la cámara, chispas y luz `Destello_Capicua`) es solo una referencia visual de los efectos de arriba; el juego debe hacerlos con su propia interfaz y sistema de partículas.

### Pasar y tranque

- `Pasar`: toca la mesa dos veces con los nudillos entre su fila y la cadena (cuadros 8 y 14), sin agarrar ficha. Sonido de «toc toc» en esos cuadros.
- `Tranque`: toca la mesa (8 y 14) y luego acuesta cara arriba las fichas que le quedan, de una en una (Fila1 en el cuadro 27, Fila6 en el cuadro 35), para contar los puntos. Estado de mesa ilustrativo (le quedan 4-6, 4-5).

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

- Se comprobaron 217.671 rotaciones (53 huesos × todos los cuadros de las 29 Actions). Exceso máximo sobre el rango: **0.0001°** (ninguna animación excede los límites).
- Con los 53 constraints activos, la pose evaluada se comparó con la pose sin constraints en los 4107 cuadros de la línea de tiempo: diferencia máxima **0.0°** (los constraints no alteran nada de lo horneado).
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
| `Salida_Doble_Seis` | piel vs. bóxer: 6.7 mm (tronco) |
| `Agarrar_Ficha_Cerca` | piel vs. bóxer: 5.8 mm (tronco) |
| `Agarrar_Ficha_Lejos` | piel vs. bóxer: 5.8 mm (tronco) |
| `Colocar_Doble` | piel vs. bóxer: 6.7 mm (tronco) |
| `Colocar_Izq_Lejos` | piel vs. bóxer: 6.7 mm (tronco) |
| `Colocar_Esquina` | piel vs. bóxer: 5.8 mm (tronco) |
| `Colocar_Der_Cerca` | piel vs. bóxer: 5.8 mm (tronco) |
| `Colocar_Der_Frente` | piel vs. bóxer: 5.8 mm (tronco) |
| `Pasar` | piel vs. bóxer: 5.8 mm (tronco) |
| `Domino_Golpe` | piel vs. bóxer: 5.8 mm (tronco) |
| `Capicua_Golpe_Celebrar` | piel vs. bóxer: 5.8 mm (tronco) |
| `Tranque` | piel vs. bóxer: 5.8 mm (tronco) |
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

- `Salida_Doble_Seis`: thumb 2.5 mm (29 cuadros), index 4.4 mm (24 cuadros)
- `Agarrar_Ficha_Cerca`: thumb 2.5 mm (20 cuadros), index 4.4 mm (15 cuadros)
- `Agarrar_Ficha_Lejos`: thumb 2.5 mm (18 cuadros), index 4.4 mm (17 cuadros)
- `Colocar_Doble`: thumb 2.5 mm (15 cuadros), index 4.4 mm (15 cuadros)
- `Colocar_Izq_Lejos`: thumb 2.9 mm (15 cuadros), index 5.1 mm (15 cuadros)
- `Colocar_Esquina`: thumb 2.9 mm (12 cuadros), index 5.1 mm (12 cuadros)
- `Colocar_Der_Cerca`: thumb 2.9 mm (12 cuadros), index 5.0 mm (12 cuadros), pinky 0.9 mm (4 cuadros)
- `Colocar_Der_Frente`: thumb 0.3 mm (5 cuadros), thumb 2.8 mm (12 cuadros), index 5.0 mm (12 cuadros)
- `Domino_Golpe`: thumb 2.9 mm (18 cuadros), index 5.0 mm (18 cuadros)
- `Capicua_Golpe_Celebrar`: thumb 2.9 mm (30 cuadros), index 5.0 mm (30 cuadros)
- `Tranque`: index 6.6 mm (5 cuadros), middle 2.8 mm (5 cuadros)

## Fotos de la partida (`fotos_partida/`)

- `01_salida_doble_seis_al_centro.jpg` — Salida: el doble seis cae atravesado en el centro.
- `02_agarra_ficha_parada_en_pinza.jpg` — Agarra una ficha parada de su fila con pinza pulgar-índice.
- `03_coloca_casando_numero_con_numero.jpg` — Coloca 3-5 en el extremo derecho: el 3 toca al 3.
- `04_doble_atravesado_y_esquina.jpg` — Cadena con dobles atravesados y la esquina (forma de L) en el borde.
- `05_pasa_tocando_la_mesa.jpg` — Pasa: toca la mesa con los nudillos, sin agarrar ficha.
- `06_domino_golpe_final.jpg` — Dominó: planta de golpe su última ficha.
- `07_capicua_golpe.jpg` — Capicúa: cámara cinemática en el golpe, texto y chispas (efectos de ejemplo).
- `08_capicua_celebracion.jpg` — Capicúa: celebración con los dos puños arriba.
