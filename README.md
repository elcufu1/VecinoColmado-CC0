# VecinoColmado CC0 — animaciones v2 · REVISIÓN

**Versión de REVISIÓN para la rama `review/piel-clara-animaciones-v2`. No es una entrega final ni una integración terminada.** Se conserva `piel-clara-v1`. Los ajustes de ropa se han aplazado expresamente: siguen existiendo defectos visibles en algunas posturas. El alcance lejano y la prueba real de la partida con el nuevo GLB están pendientes. Esta revisión se conserva en una rama separada; no reemplaza la versión v1.

Personaje MakeHuman de piel clara, cabeza sin cabellera, rasgos y ropa conservados respecto a `piel-clara-v1`. El rig real tiene 53 huesos y el cuerpo conserva sus 56 morphs originales. La versión v1 se mantiene como base independiente.

## Archivos de la revisión

| Archivo | Contenido | Estado |
| --- | --- | --- |
| `VecinoColmado_CC0_PielClara_Animaciones_v2.blend` | Modelo editable, texturas empaquetadas, rig, biblioteca y demo NLA nativa | Reabierto en Blender 4.3.2 con autoejecución deshabilitada; texturas empaquetadas verificadas |
| `VecinoColmado_CC0_PielClara_Animaciones_v2.glb` | Modelo y clips para motores compatibles con glTF 2.0 | 60 clips; 53 huesos, 56 morphs y 10 texturas originales verificados |
| `inventario/acciones.json` | Nombres y separación de biblioteca, diagnósticos y jugadas | 26 de biblioteca + 24 extras + 10 de alcance cercano; coincide con el GLB incluido |
| `inventario/validacion.json` | Pruebas realizadas, alcance y pendientes | Resumen de pruebas de manos; no sustituye la validación de la entrega completa |
| `evidencia/` | Capturas y vídeos propios renderizados en Blender | Pruebas de manos, cara, cuerpo y reproducción nativa NLA de Blender; no son una partida web |
| `procedencia/` y `LICENCIA_Y_ALCANCE.txt` | Componentes, créditos y avisos de licencia | Documentación preparada |
| `MANIFIESTO_SHA256.json` | Tamaños y SHA-256 de cada archivo entregado | Tamaños y hashes de los archivos incluidos |

El paquete público no incluye scripts de autoría, código de aplicaciones, datos de partidas ni recursos de un juego. Tampoco requiere el addon MPFB para abrir el modelo ya guardado en Blender. El editable se reabrió y verificó en Blender 4.3.2 con autoejecución deshabilitada.

## Biblioteca de 26 acciones

Las acciones articulares son ejercicios de diagnóstico; no se deben elegir aleatoriamente como jugadas.

| Grupo | Nombres |
| --- | --- |
| Brazo/mano derechos, 8 | `puno_mano`, `puno_abrir_cerrar`, `muneca_lados`, `muneca_arriba_abajo`, `codo_doblar`, `antebrazo_giro`, `hombro_circulo`, `hombro_movimientos` |
| Brazo/mano izquierdos, 8 | Los ocho nombres anteriores con sufijo `_izq` |
| Posturas, 2 | `sentado_silla`, `sentado_ficha` |
| Expresiones, 6 | `cara_neutral`, `cara_sonrisa`, `cara_enojado`, `cara_ojos_cerrados`, `cara_boca_abierta`, `cara_sorprendido` |
| Mandíbula, 2 | `cara_boca_abierta_mandibula`, `cara_sorprendido_mandibula` |

Las expresiones se adaptan a los morphs y mallas reales de este personaje, incluidos dientes y lengua. Los nombres «mandíbula» identifican ejercicios lógicos: no implican que el rig MakeHuman tenga los huesos de otro personaje. Las pistas compañeras por malla y los correctivos de ropa no se cuentan como nuevas acciones lógicas.

## Diagnósticos adicionales

Hay 24 ejercicios adicionales: diez dedos individuales —cinco por mano, incluidos los pulgares—, un cierre corregido de ambas manos y trece pruebas de cuello, cabeza, torso, cintura, caderas, piernas, rodillas, tobillos y pies. La acción original de v1 se conserva únicamente como `REFERENCIA_v1_Prueba_cierre_ambas_manos_NO_USAR`, marcada `source_reference_not_for_playback`. No se exporta al GLB ni se activa al abrir el Blender. La corregida mantiene el nombre `Prueba_cierre_ambas_manos_corregida`; la fuente v1 permanece intacta.

La corrección de manos combina una pose propia del pulgar con reparación documentada de pesos en 788 vértices. No cambia la geometría de reposo, los morphs originales ni el bind del rig. Los correctivos de ropa son específicos de las poses revisadas; no equivalen a un sistema de ajuste corporal general.

## Diez clips de partida de alcance cercano

`partida_reposo`, `partida_mirar_fichas`, `partida_pensar`, `partida_agarrar`, `partida_sostener`, `partida_colocar`, `partida_golpear`, `partida_pasar`, `partida_ganar` y `partida_perder`.

Estos clips forman una biblioteca nominal de alcance cercano y requieren integración con el motor: selección, objetivos, propiedad de la ficha, contacto, suelta y cancelación. No se afirma alcance universal ni funcionamiento en cualquier mesa. No se incluye ni se afirma una animación humana de barajar.

El agarre toma desde arriba la esquina del mismo lado de la mano: derecha con derecha, izquierda con izquierda. La muñeca conserva una orientación natural. La colocación termina con la ficha plana mediante apoyo de un extremo, retirada de los dedos y basculación apoyada. El golpe es una adaptación explícita: se golpea con el extremo inferior de la ficha inclinada, aproximadamente 52°, se mantiene la pinza durante la pausa y se retorna. No se presenta como un golpe plano con el índice debajo de la mesa.

## Demostración nativa en Blender

El Blender de revisión incluye `DEMO_Juego_cercano`: cuerpo, una única ficha de prueba y correctivos de ropa coordinados mediante pistas NLA nativas. Las claves están horneadas a **120 Hz** y la escena se reproduce a **24 fps**; 120 Hz describe el muestreo de claves, no una promesa de rendimiento del juego. Se puede reproducir la línea de tiempo con la autoejecución de scripts deshabilitada. El bloque `LEEME_DEMO_Y_BIBLIOTECA.txt` contiene instrucciones, no Python.

Para revisar una acción individual, silenciar `DEMO_Juego_cercano` en el esqueleto, la ficha de prueba y las Shape Keys de la ropa; activar la acción deseada y su pista de correctivos correspondiente. Las expresiones usan sus pistas compañeras por malla. La demo y la mesa/silla/ficha no son clips adicionales del GLB del personaje. Esta escena es una demostración de Blender, no una partida web.

## Evidencia y límites

`evidencia/jugadas_blender_nla.mp4` muestra reproducción nativa del editable, con cámara general y detalle. Está capturado con la vista Workbench de Blender, a velocidad 0,5×; sirve para observar el movimiento, no para aprobar el acabado de materiales. Los demás vídeos están identificados como pruebas de Blender.


La revisión de manos en Blender pasó 252 poses densas y 622 muestras de fotograma/lado de 15 acciones, sin autocruces en la mano completa en esas muestras. La pinza estática de ambas manos pasó la comprobación de penetraciones contra ficha y mesa. La secuencia de vídeo de manos tiene 336 fotogramas a 12 fps, resolución 960×540 y duración de 28 s. Distingue el cierre original con pesos originales del cierre corregido y los diez dedos individuales.

El Blender y GLB incluidos preservan geometría de reposo, UVs, los 53 huesos, los 56 morphs y los bytes de las 10 texturas originales. El GLB conserva hasta seis influencias reales mediante ocho ranuras de pesos; un motor limitado a cuatro pierde fidelidad. Los diez clips cercanos pasaron 479 poses/958 comprobaciones de manos; la demo nativa también pasó 42 comprobaciones entre claves. El vídeo de diagnósticos no demuestra una partida, transiciones de juego ni comportamiento multicliente. La revisión deberá documentar cada comprobación por separado, sin usar imágenes antiguas como aprobación de la versión nueva. El vídeo corporal de esta revisión se generó con los módulos congelados de esta entrega. El vídeo facial comprueba el mismo módulo y los morphs preservados; no es evidencia del alcance corporal.

**Ropa aplazada:** esta revisión conserva los correctivos ya válidos, pero no declara resueltos los defectos visibles de ropa, las intersecciones restantes ni el ajuste durante todos los movimientos. **Alcance lejano pendiente:** los diez clips cercanos no demuestran que pueda alcanzarse cualquier objetivo de una mesa. **Juego pendiente:** el nuevo GLB todavía necesita su prueba dentro de una partida real, incluidos contacto, suelta, interrupciones y repetición; las pruebas de otra revisión no sustituyen esa comprobación.

**La personalización corporal está deshabilitada.** Se conservan los controles originales, pero cambiar cintura o volumen facial todavía no adapta automáticamente ropa, rig y accesorios. Tampoco se declara rendimiento validado en todos los dispositivos.

## Licencia y procedencia

Los componentes gráficos de origen están identificados como CC0 1.0 Universal en la documentación incluida. La política oficial distingue la licencia CC0 de los assets de las licencias del código de MakeHuman y MPFB, que no se distribuye aquí. [Licencia oficial de MakeHuman](https://static.makehumancommunity.org/about/license.html).

La procedencia conserva componentes, hashes y avisos originales. Faceunits 01 se atribuye a Mika Suominen, según su ficha oficial. [Faceunits 01](https://static.makehumancommunity.org/assets/assetpacks/faceunits01.html). El alcance de la distribución de revisión se detalla en `LICENCIA_Y_ALCANCE.txt`; el texto oficial de CC0 está disponible en [Creative Commons](https://creativecommons.org/publicdomain/zero/1.0/legalcode.en).
