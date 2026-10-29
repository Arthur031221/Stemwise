# Stemwise

Un estudio de práctica local. Separa una canción en seis pistas, muestra los acordes y el pulso, y ralentiza un bucle sin cambiar el tono.

Separación de pistas 122,5 veces más rápida que el tiempo real en una RTX 5090. Una canción de 2 minutos y 3 segundos tarda 1,00 s (`stemwise bench`, fp32, mejor de 3 tras una pasada de calentamiento). En un Ryzen 5 7500F con 3 hilos la misma canción tarda 45,2 s, es decir, 2,7 veces el tiempo real.

[Demo en vivo](https://arthur031221.github.io/Stemwise/) | [Instalación](docs/install.md) | [Uso](docs/usage.md) | [Configuración](docs/config.md) | [Arquitectura](docs/architecture.md) | [Benchmarks](docs/benchmarks.md)

[English](README.md) | [繁體中文](README.zh-TW.md) | [简体中文](README.zh-CN.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | Español | [Français](README.fr.md) | [Deutsch](README.de.md) | [Português (Brasil)](README.pt-BR.md)

![Stemwise: silenciar la batería, repetir un compás, bajar al 70 %, activar el clic, transponer](assets/demo.gif)

Tus archivos no salen de tu equipo, y prefiero enseñarte dónde se equivoca la pista de acordes antes que esconderlo.

## Antes y después

| Practicar un compás difícil | Un reproductor normal | Stemwise |
| --- | --- | --- |
| Ralentizar un bucle al 70 % | El varispeed baja el tono 6,2 semitonos | El tono no cambia. Una prueba unitaria cuenta los cruces por cero de una senoidal de 440 Hz al 50 %, 70 % y 150 % de velocidad |
| Oír solo el bajo | Imposible con un archivo estéreo | Pon el bajo en solo o silencia las otras cinco pistas |
| Conseguir una pista de acompañamiento | Buscar una versión de karaoke | Exporta la mezcla sin las pistas que silenciaste, en WAV |
| Encontrar los acordes | Rebobinar y escuchar | Una pista de acordes sobre la rejilla de pulsos. La precisión de la fundamental es 0,739 en guitarra rasgueada y 0,265 en solos (ver abajo) |
| Tocar con un clic | Un metrónomo que ajustas a mano | Un clic que sigue la rejilla de pulsos de la propia canción, con cuenta atrás |
| Subir el tempo por pasos | Mover el control y perder la cuenta | El entrenador de velocidad sube un paso tras un número de bucles limpios (tres por defecto). Pulsa `X` cuando falles y la cuenta empieza de nuevo |

## Instalación

Todavía no está en PyPI, así que se instala desde GitHub. También necesitas Python 3.10 o superior y ffmpeg.

<details>
<summary>Linux (GPU NVIDIA o CPU)</summary>

```sh
sudo apt install ffmpeg libsndfile1
pip install git+https://github.com/Arthur031221/Stemwise
stemwise doctor
```

En Linux pip descarga la versión CUDA de torch, que es grande. Añade `--extra-index-url https://download.pytorch.org/whl/cpu` para una instalación solo con CPU.

</details>

<details>
<summary>macOS (Apple Silicon o Intel)</summary>

```sh
brew install ffmpeg
pip install git+https://github.com/Arthur031221/Stemwise
stemwise doctor
```

Apple Silicon usa el dispositivo MPS cuando torch lo indica. No he medido la velocidad en un Mac.

</details>

<details>
<summary>Windows</summary>

```powershell
winget install Gyan.FFmpeg
pip install git+https://github.com/Arthur031221/Stemwise
stemwise doctor
```

No he ejecutado Stemwise en Windows. La CI solo cubre Linux.

</details>

El primer análisis descarga unos 55 MB de Demucs y 81 MB de beat_this. Después no hace falta red.

## Uso

```sh
stemwise                      # abre el estudio en el navegador
stemwise split song.mp3       # pistas, chords.txt y beats.mid junto al archivo
```

Salida real de `stemwise split` con una canción de 2 minutos:

```
surf.mp3: 123s, 166.7 BPM, B major, 105 chords, on cuda
```

Suelta un archivo en la página y espera a la barra de progreso. Arrastra sobre la regla para elegir un bucle, pulsa `L` para repetir el compás donde está el cursor y usa las teclas de abajo. La lista completa está en [docs/usage.md](docs/usage.md).

| Tecla | Acción | Tecla | Acción |
| --- | --- | --- | --- |
| Space | reproducir y pausar | `[` `]` | bajar y subir el tempo un 5 % |
| L | repetir este compás o alternar el bucle | Up, Down | transponer un semitono |
| C | activar y desactivar el clic | Left, Right | saltar un compás |
| X | fallo, para el entrenador | 1 a 6 | silenciar una pista |

## Qué incluye

| Parte | Qué es |
| --- | --- |
| Separación | Demucs v4 `htdemucs_6s`: voz, batería, bajo, guitarra, piano, otros |
| Pulso | beat_this para pulsos, tiempos fuertes y BPM |
| Acordes | Cromagrama CQT, plantillas mayor, menor, 7 y min7, suavizado de Viterbi y estimación de tonalidad. Sin modelo neuronal de acordes |
| Reproductor | Un motor AudioWorklet con estiramiento temporal WSOLA, remuestreador cúbico, bucles, clic y cuenta atrás |
| Estudio | Módulos ES y CSS sin paso de compilación, nueve idiomas de interfaz, temas oscuro y claro |
| Exportación | Pista de acompañamiento, zip de pistas, hoja de acordes en texto o HTML imprimible, rejilla de pulsos en MIDI |
| API | Una pequeña API JSON local, documentada en [docs/usage.md](docs/usage.md) |

La aplicación del navegador está en `web/`, la misma carpeta que GitHub Pages sirve como demo en vivo. La demo reproduce una canción ya separada y no puede separar tus archivos.

## Qué tal funciona

Ejecuté `bench/chords_guitarset.py` sobre [GuitarSet](https://guitarset.weebly.com/) (360 fragmentos de guitarra sola). Ajusté las constantes de acordes con uno de cada cinco fragmentos y puntué los otros 288.

| Fragmentos | Fundamental | Mayor y menor | Pulso F | Tiempo fuerte F |
| --- | --- | --- | --- | --- |
| Acompañamiento, 144 | 0.739 | 0.671 | 0.971 | 0.944 |
| Solos, 144 | 0.265 | 0.201 | 0.605 | 0.403 |

Los pulsos en las partes rasgueadas son fiables. Los acordes son un punto de partida para aprender una canción, así que compruébalos de oído. Un solo de notas sueltas casi no contiene información de acordes, por lo que la pista se equivoca casi siempre ahí. Estos fragmentos son de guitarra sola, así que no puedo decirte cómo puntúa una mezcla de banda completa. La tabla completa y el método están en [docs/benchmarks.md](docs/benchmarks.md).

## Límites

- La pista de acordes conoce cuatro tipos de acorde. Los acordes con bajo distinto, suspendidos y con extensiones aparecen como el más cercano de los cuatro.
- La tonalidad es una sola estimación para toda la canción. En la salida de arriba dice Si mayor mientras que los acordes son sobre todo Em, D y Bm, así que tómala como una pista.
- El tempo mostrado es la mediana del detector de pulsos, por lo que puede diferir del tempo publicado. La canción de la demo figura con 170 BPM y el detector da 166,7.
- Una canción instrumental deja las pistas de voz y piano casi vacías. Eso es la separación funcionando bien.
- En una CPU una canción de cuatro minutos tarda unos 90 segundos a las 2,7 veces que medí, y más en chips más lentos.
- El estiramiento temporal es WSOLA, que puede emborronar las notas largas en los ajustes más lentos.
- Solo se procesa una canción a la vez.

## Desarrollo

```sh
pip install -e ".[dev]"
ruff check . && pytest -m "not slow and not e2e"
node --test tests/js/*.test.mjs
STEMWISE_BROWSER_CHANNEL=chrome pytest -m e2e
```

Consulta [CONTRIBUTING.md](CONTRIBUTING.md). Una etiqueta que empiece por `v` activa el flujo de lanzamiento, que construye el wheel y el sdist y los adjunta a una release de GitHub.

## Créditos y licencias

Stemwise tiene licencia MIT. Se apoya en [Demucs](https://github.com/facebookresearch/demucs) (MIT), [beat_this](https://github.com/CPJKU/beat_this) (código y pesos MIT), librosa y Starlette. La demo en vivo reproduce "Surf Shimmy" de Kevin MacLeod ([incompetech.com](https://incompetech.com)), con licencia [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), recortada a un fragmento de 36 segundos y separada con Stemwise. GuitarSet es de Xi et al. (2018), CC BY 4.0.

Assisted by Claude/Codex.
