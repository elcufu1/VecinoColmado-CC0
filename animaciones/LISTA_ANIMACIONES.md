# Lista de animaciones — VecinoColmado (Dominó Colmado)

Todas las animaciones son *Actions* separadas del armature `VecinoColmado_CC0` (53 huesos), a **24 fps**, horneadas cuadro a cuadro. No se modificó malla, pesos, huesos ni morfos: solo se crearon Actions (huesos + morfos faciales).

Archivos:

- `Vecino_Boxer_Animado.glb` — personaje + 23 animaciones (sin mesa ni silla), listo para el juego.
- `Vecino_Boxer_Animado.blend` — mismas Actions + escena `Previsualizacion_Animaciones` con mesa, silla, fichas y cámaras (línea de tiempo con marcadores por animación).
- `videos/` — un MP4 por animación (H.264, 1280×720, 24 fps) y `VIDEO_TODO_EL_CUERPO.mp4`.
- `fotos/` — JPG de frente, 3/4 y perfil en las poses clave.
- `scripts/` — código que genera todo (`blender -b Vecino_Boxer.blend --python scripts/final.py -- build <dir>`).

| # | Nombre (Action) | Cuadros | Duración | Bucle | Uso en el juego |
|---|---|---|---|---|---|
| 1 | `Idle_De_Pie` | 192 | 8.00 s | sí | Espera de pie / lobby (bucle). |
| 2 | `Caminar` | 28 | 1.17 s | sí | Desplazamiento (el juego mueve el personaje). |
| 3 | `Sentarse` | 100 | 4.17 s | no | Llegar a la mesa. |
| 4 | `Levantarse` | 90 | 3.75 s | no | Salir de la mesa. |
| 5 | `Idle_Sentado` | 144 | 6.00 s | sí | Espera de turno (bucle). |
| 6 | `Agarrar_Ficha_Cerca` | 20 | 0.83 s | no | Tomar ficha de la mesa (pozo o propias). |
| 7 | `Agarrar_Ficha_Lejos` | 26 | 1.08 s | no | Tomar ficha de la mesa (pozo o propias). |
| 8 | `Colocar_Ficha_Cerca` | 20 | 0.83 s | no | Jugar una ficha cerca del jugador. |
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
6. **Agarrar_Ficha_Cerca** — Agarra una ficha cercana con pinza pulgar-índice y la levanta.
7. **Agarrar_Ficha_Lejos** — Agarra una ficha lejana con pinza pulgar-índice y la levanta.
8. **Colocar_Ficha_Cerca** — Lleva la ficha rápido y decidido a la mesa, la suelta y vuelve a la pose sentada.
9. **Colocar_Ficha_Lejos** — Coloca la ficha lejos: la otra mano se apoya firme, el cuerpo se levanta un poco y todo se mueve a la vez.
10. **Golpe_Ficha** — Tranque/capicúa: levanta la ficha y la golpea fuerte contra la mesa.
11. **Pasar** — Toca la mesa dos veces con los nudillos ("paso").
12. **Barajar_Fichas** — Ambas manos revuelven fichas boca abajo en círculos sobre la mesa.
13. **Sostener_Fichas** — Sostiene un grupo de fichas en la mano izquierda, las mira y mueve los dedos (bucle).
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
- Ficha usada como referencia: 0.045 × 0.090 × 0.014 m. En `Agarrar_*` la ficha queda en la pinza pulgar-índice a partir del cuadro de agarre; en `Colocar_*` se suelta en el cuadro indicado abajo. Para que la ficha siga la mano, emparentarla al hueso `hand_r` entre agarre y suelta.
- Cuadros clave: Agarrar_Ficha_Cerca agarra en el cuadro 10; Agarrar_Ficha_Lejos en el 14; Colocar_Ficha_Cerca suelta en el 7; Colocar_Ficha_Lejos en el 11; Golpe_Ficha impacta en el 15; Pasar golpea en los cuadros 8 y 14.
- `Caminar` es un ciclo en el sitio a ~0.83 m/s (el juego mueve la raíz). Los bucles tienen el primer y el último cuadro iguales.
- Cada Action anima también los morfos faciales (expresiones); al mezclar animaciones, los morfos de la Action activa sustituyen a los anteriores.
- En el GLB las texturas opacas de piel y lengua se recomprimieron a JPEG para reducir peso (la malla, pesos, huesos y morfos son los mismos).

## Verificación automática (penetraciones máximas)

Medidas en milímetros sobre todos los cuadros de cada animación (dedos vs. ficha/mesa, brazos vs. borde de la mesa, piel vs. bóxer/silla/suelo). Valores ≤ 2 mm no son visibles.

| Animación | Peor contacto |
|---|---|
| `Idle_De_Pie` | sin contactos |
| `Caminar` | suelo: 6.3 mm (pie) |
| `Sentarse` | piel vs. bóxer: 7.4 mm (tronco); silla_asiento: 1.0 mm (muslo) |
| `Levantarse` | piel vs. bóxer: 7.0 mm (tronco); silla_asiento: 6.1 mm (muslo) |
| `Idle_Sentado` | piel vs. bóxer: 5.9 mm (tronco) |
| `Agarrar_Ficha_Cerca` | piel vs. bóxer: 5.9 mm (tronco); borde de la mesa (lado del jugador): 4.3 mm (antebrazo); ficha Ficha: 1.0 mm (thumb_03_r) |
| `Agarrar_Ficha_Lejos` | piel vs. bóxer: 5.9 mm (tronco); borde de la mesa (lado del jugador): 3.8 mm (brazo); ficha Ficha: 1.5 mm (ring_03_r) |
| `Colocar_Ficha_Cerca` | piel vs. bóxer: 5.9 mm (tronco); ficha Ficha: 2.2 mm (ring_03_r) |
| `Colocar_Ficha_Lejos` | piel vs. bóxer: 6.7 mm (tronco); ficha Ficha: 3.7 mm (middle_03_r) |
| `Golpe_Ficha` | piel vs. bóxer: 5.9 mm (tronco); ficha Ficha: 4.2 mm (ring_03_r) |
| `Pasar` | piel vs. bóxer: 5.9 mm (tronco) |
| `Barajar_Fichas` | piel vs. bóxer: 5.6 mm (tronco) |
| `Sostener_Fichas` | piel vs. bóxer: 5.9 mm (tronco) |
| `Celebrar_Ganar` | piel vs. bóxer: 5.9 mm (tronco) |
| `Perder` | piel vs. bóxer: 5.9 mm (tronco); borde de la mesa (lado del jugador): 2.3 mm (antebrazo); silla_asiento: 1.2 mm (muslo) |
| `Pensar` | piel vs. bóxer: 5.9 mm (tronco) |
| `Saludar` | piel vs. bóxer: 5.9 mm (tronco); borde de la mesa (lado del jugador): 4.4 mm (antebrazo) |
| `Senalar` | piel vs. bóxer: 5.9 mm (tronco) |
| `Pulgar_Arriba` | piel vs. bóxer: 5.9 mm (tronco); borde de la mesa (lado del jugador): 3.4 mm (antebrazo) |
| `Aplaudir` | piel vs. bóxer: 5.9 mm (tronco) |
| `Reir` | piel vs. bóxer: 5.9 mm (tronco); borde de la mesa (lado del jugador): 2.2 mm (antebrazo) |
| `Enojado` | piel vs. bóxer: 5.9 mm (tronco); borde de la mesa (lado del jugador): 1.6 mm (antebrazo) |
| `Prueba_Rango_Completo` | piel vs. bóxer: 5.6 mm (tronco) |

Notas: "piel vs. bóxer" es un punto de la piel de la parte baja de la espalda/glúteo que asoma unos 6–7 mm a través del bóxer al estar sentado; queda tapado por la silla en todas las vistas del juego. Se dejó así porque corregirlo exige modificar malla o pesos, que estaba prohibido. Los contactos de ficha (1–4 mm) son la yema del dedo apoyada en la ficha durante la pinza o el golpe.
