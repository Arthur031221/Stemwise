# Install

Stemwise needs Python 3.10 or newer and ffmpeg on your PATH.

```sh
pip install stemwise
stemwise doctor
```

`stemwise doctor` prints the Python, torch and ffmpeg versions and the compute device it will use. If it says
`cpu only`, everything still works, it is just slower (see [benchmarks](benchmarks.md)).

The first analysis downloads two model files: the Demucs `htdemucs_6s` weights (about 55 MB) and the beat_this
checkpoint (about 81 MB). After that everything runs offline.

## ffmpeg

| System | Command |
| --- | --- |
| macOS | `brew install ffmpeg` |
| Debian, Ubuntu | `sudo apt install ffmpeg libsndfile1` |
| Windows | `winget install Gyan.FFmpeg` |

## GPU

The default `pip install` pulls the torch build for your platform. On Linux with an NVIDIA card that is a CUDA
build and Stemwise uses it automatically. On Apple Silicon it uses MPS. Force a device with `--device cpu`,
`--device cuda` or `--device mps`.

## From source

```sh
git clone https://github.com/Arthur031221/Stemwise
cd Stemwise
pip install -e ".[dev]"
```

## Try it without installing

The [live demo](https://arthur031221.github.io/Stemwise/) runs the same player on a pre-separated, CC BY 4.0
licensed song. It cannot split your own files, because that needs the Python side.
