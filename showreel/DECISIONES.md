# DECISIONES — Showreel de motion design (15 s)

**Entregable:** `showreel.mp4` · 1920×1080 · 60 fps · 15,000 s · H.264 + AAC 320 kbps
**Regla:** solo código. Ni un modelo de imagen, vídeo o audio; ni un sample. Cada píxel lo dibuja `reel.html` y cada onda la sintetiza `music.py`.

```
music.py     → síntesis de la banda sonora (numpy + scipy), 48 kHz estéreo
reel.html    → las 7 escenas, el HUD y el post-proceso (Canvas 2D + WebGL2)
render.mjs   → renderiza cada fotograma en Chromium headless, 4 procesos en paralelo
build.sh     → música → fotogramas → MP4
```

---

## 1. La idea

Un showreel de diseñador no cuenta una historia. **Demuestra un repertorio**. Por eso cada compás enseña una técnica distinta, y todo está unido por una única regla: **la imagen y la música comparten la misma retícula temporal**.

- **128 BPM** → negra = 0,46875 s, compás = 1,875 s.
- **8 compases = 15,000 s exactos.** No elegí 15 s y luego un tempo: elegí el tempo *porque* hace que 15 s sean 8 compases redondos. Así cada corte cae en un tiempo fuerte.

| Compás | Tiempo | Escena | Qué demuestra | Música |
|---|---|---|---|---|
| 1 | 0,00–1,88 | **00 HELLO**: un punto que se estira en línea y abre una retícula de diseño | anticipación, *squash & stretch*, *stagger* | pad filtrado, ticks de máquina de escribir, riser |
| 2 | 1,88–3,75 | **01 TYPE**: "MOTION" cae letra a letra sobre una línea que vibra como una cuerda; zoom **a través de la O** | tipografía cinética, física falsa, transición por máscara | 6 golpes de tom en corcheas, redoble, *reverse crash*, silencio |
| 3 | 3,75–5,63 | **02 MORPH**: círculo → cuadrado → triángulo → estrella, un *morph* por tiempo | interpolación de formas en coordenadas polares, ondas de color | **el drop**: kick, clap, bajo rodante, pad con sidechain |
| 4 | 5,63–7,50 | **03 DEPTH**: 576 puntos en 3D: esfera → nudo toroidal → superficie ondulada → **se aplanan en la retícula** | proyección en perspectiva propia, ordenación por profundidad | entra el arpegio con delay ping-pong |
| 5 | 7,50–9,38 | **04 GRID**: 576 baldosas que giran en ondas (diagonal, radial, aleatoria) y escriben **DESIGN** | animación procedural de cuadrícula, giro 3D falso con sombreado | — |
| 6 | 9,38–11,25 | **05 FLOW**: 2304 partículas en un campo de *curl noise* que se reúnen en **CODE** y explotan | simulación determinista, trazos con estela | el filtro del pad se abre |
| 7 | 11,25–13,13 | **06 RHYTHM**: 8 mini-escenas de 14 fotogramas: TIMING, EASING, RHYTHM, SPACING, CONTRAST, TENSION, RELEASE, DETAIL | composición rápida, 8 tratamientos tipográficos distintos | un acorde *stab* por corte, *trance gate*, redoble de fusas |
| 8 | 13,13–15,00 | **07 HELLO AGAIN**: firma "CLAUDE / Motion Designer", la retícula del principio regresa | cierre con eco del inicio | golpe final, acorde de La♭ mayor, campanas FM |

## 2. Decisiones clave (y por qué)

**Transiciones que se encadenan, no cortes al azar.** Cada escena *nace* del último estado de la anterior:
- la O de "MOTION" se llena de color y la cámara la atraviesa; dentro ya está la escena siguiente;
- la estrella implosiona a un punto y de ese punto estalla la esfera 3D;
- los puntos 3D aterrizan exactamente en los centros de las 576 baldosas de la cuadrícula (asignados ordenando sus posiciones proyectadas en filas y columnas, para que nadie cruce la pantalla);
- cada baldosa se encoge a un punto y suelta 4 partículas: 576 × 4 = 2304.

Eso es lo que separa un reel de un collage.

**Todo es una función pura del tiempo.** `renderFrame(f)` no tiene estado: hasta la simulación de partículas se precalcula de forma determinista (paso de 1/240 s, semilla fija). Por eso puedo renderizar fotogramas sueltos para revisar, o los 900 en paralelo en 4 navegadores, y obtener siempre el mismo resultado.

**Motion blur real, no un filtro.** Cada fotograma es la media de 6 sub-fotogramas dentro de un obturador de 180° (1/120 s). Con una salvedad que me importaba: **los sub-fotogramas nunca cruzan un corte duro**, así que los cortes siguen siendo secos y no aparece un fotograma "fantasma" mezclando dos escenas.

**Post-proceso en WebGL2** (un único shader): aberración cromática radial que se dispara en los impactos, un "punch" de lente, *bloom* a partir de los mipmaps, viñeta, grano de película y flashes. El *bloom* y la viñeta se atenúan automáticamente cuando el fotograma es claro (mido la luminancia media en el último mipmap).

**Paleta corta y con intención:** tinta `#0B0B0E`, papel `#F2EEE6`, arcilla `#E4693F` (el color principal), cobalto `#2F4BFF` y lima `#D4FF3A` solo para los golpes. Tipografía Inter Display Black para titulares e Inter 600 espaciada para el HUD.

**Un HUD de "sala de montaje":** marcas de corte, timecode a 60 fps, nombre de sección que rueda como una tragaperras en cada cambio y 4 luces que marcan el tiempo del compás. Cambia de color según el fondo de cada escena, incluso por lados en CONTRAST, que tiene media pantalla blanca y media negra.

**Detalles que casi nadie verá pero que se notan:**
- la línea base de "MOTION" vibra como una cuerda donde cae cada letra;
- cada carácter del texto mecanografiado tiene su "tick" en el audio;
- la forma interior del *morph* va desfasada 60 ms (acción secundaria);
- las baldosas de las letras de DESIGN se adelantan 4 px;
- la marca final son las 4 formas del compás 3, que siguen transformándose a tempo.

**Música compuesta, no decorativa.** Fa menor: `Fm9 | E♭add9 | Fm9 | D♭maj7 | A♭add9 | E♭add9 | D♭ – E♭ | A♭`. El final (IV–V–I hacia La♭ mayor) resuelve hacia arriba justo cuando aparece la firma. Todo está sintetizado:
- **Kick:** seno con barrido de tono más un clic de ruido.
- **Clap:** 3 ráfagas de ruido filtrado.
- **Hi-hats y crash:** 6 osciladores cuadrados inarmónicos al estilo 808, más ruido.
- **Supersaw:** 7 sierras *PolyBLEP* (sin aliasing) desafinadas en estéreo.
- **Bajo rodante:** semicorcheas que dejan hueco al kick.
- **Pluck, riser y whooshes:** filtros biquad con barrido.
- **Campanas:** síntesis FM.
- **Reverb:** convolución con una respuesta al impulso que también es sintética (ruido con decaimiento exponencial).
- **Sidechain:** generado a partir de los tiempos del kick.

## 3. Lo que descarté

- **Renderizar con Python/PIL:** sin antialiasing en las formas, texto pobre y lento. Chromium headless me da Canvas 2D con antialiasing, tipografía real y WebGL para el post.
- **Descargar fuentes de Google Fonts:** Inter ya estaba instalada en el sistema; menos dependencias.
- **Un vídeo de 30 fps "porque basta":** el brief pide 60, y el motion blur se diseñó para 60.
- **Motion blur como desenfoque direccional en post:** falla en rotaciones y zooms; el muestreo temporal es correcto en cualquier movimiento.
- **Fundidos entre escenas:** son la transición más perezosa. Usé *match cuts*, máscaras e iris.
- **Un asterisco/estallido de rayos como logo final:** en la primera prueba se parecía demasiado a una marca existente. Lo sustituí por las 4 formas del *morph*, que además cierran el círculo narrativo.
- **Melodía principal (lead):** en 15 s competía con el arpegio y los *stabs*. Menos capas, cada una con su espacio.
- **Muestreo de baterías o one-shots:** prohibido por el brief, y además innecesario.

## 4. Iteraciones

1. **Exploración del entorno:** comprobé Chromium + WebGL (SwiftShader), las fuentes disponibles y ffmpeg/libx264. Medí el coste: unos 230 ms por captura PNG, así que 4 procesos en paralelo.
2. **Música v1:** el análisis espectral por compás mostró un subgrave que acaparaba casi toda la energía y unos medios enterrados (pad y arpegio a −12/−15 dB relativos) y casi mono.
3. **Música v2:** reduje a la mitad el sub del bajo y subí el pad (×2,3), el arpegio (×1,8) y los hi-hats. Los medios quedaron alrededor de −8 dB y el estéreo más abierto.
4. **Música v3:** en el compás final el *boom* tapaba el acorde. Bajé el sub y subí el acorde y las campanas.
5. **Visual v1:** primer render de prueba, 24 fotogramas repartidos por los 15 s, revisados en una hoja de contactos. Problemas: el *bloom* quemaba los fondos claros (el papel se volvía blanco puro y la viñeta lo ensuciaba) y la marca final recordaba a un logo existente.
6. **Visual v2:** *bloom* y viñeta adaptativos según la luminancia media, y marca nueva. Segunda hoja de contactos con 46 fotogramas, centrada en las transiciones y en las 8 mini-escenas del compás 7.
7. **Render final:** 900 fotogramas × 6 sub-fotogramas = 5400 imágenes compuestas, en 17 min 46 s con 4 navegadores en paralelo.
8. **Codificación v1, descartada:** H.264 con CRF 15 pesaba **140 MB**. El grano de película, distinto en cada fotograma, se come los bits, y además el archivo superaba el límite de 100 MB de GitHub.
9. **Codificación v2:** H.264 High, CRF 19 con techo de 36 Mbit/s, BT.709 y AAC 320k: **26 MB**. Comparé un fotograma decodificado con el PNG original y no hay diferencia visible.

## 5. Tiempo total

Medido con reloj real (UTC), desde que leí el encargo hasta el commit:

| Fase | Tiempo |
|---|---|
| Exploración del entorno y pruebas de rendimiento | ~3 min |
| Composición, síntesis y 3 mezclas de la música | ~6 min |
| Diseño y código de las 7 escenas, el HUD y el post-proceso | ~9 min |
| 2 rondas de renders de prueba y correcciones | ~3 min |
| Render final (900 fotogramas) | ~18 min |
| Codificación (2 pasadas), verificación y documentación | ~6 min |
| **Total** | **≈ 45 minutos** (13:46 → 14:31 UTC) |

Casi la mitad del tiempo fue la máquina renderizando. El trabajo de diseño y código ocupó unos 25 minutos.

Para regenerarlo todo: `./build.sh`. Hay una hoja de contactos en `contact_sheet.jpg`.
