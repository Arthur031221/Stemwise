# Stemwise

내 컴퓨터에서 돌아가는 연습 스튜디오입니다. 곡을 여섯 개의 스템으로 나누고, 코드와 박자를 보여 주며, 음높이를 바꾸지 않고 반복 구간을 느리게 할 수 있습니다.

[라이브 데모](https://arthur031221.github.io/Stemwise/) | [설치](docs/install.md) | [사용법](docs/usage.md) | [설정](docs/config.md) | [아키텍처](docs/architecture.md) | [벤치마크](docs/benchmarks.md)

[English](README.md) | [繁體中文](README.zh-TW.md) | [简体中文](README.zh-CN.md) | [日本語](README.ja.md) | 한국어 | [Español](README.es.md) | [Français](README.fr.md) | [Deutsch](README.de.md) | [Português (Brasil)](README.pt-BR.md)

![Stemwise: 드럼 음소거, 한 마디 반복, 70%로 감속, 클릭 켜기, 키 이동](assets/demo.gif)

RTX 5090에서 스템 분리 속도는 실시간의 122.5배입니다. 2분 3초짜리 곡이 1.00초 만에 끝납니다(`stemwise bench`, fp32, 워밍업 한 번 뒤 세 번 측정해 최고값). 스레드 3개의 Ryzen 5 7500F에서는 같은 곡에 45.2초가 걸리며 실시간의 2.7배입니다.

파일은 내 컴퓨터를 떠나지 않습니다. 그리고 코드 레인이 틀린 곳은 숨기지 않고 보여 드리고 싶습니다.

## 사용 전과 후

| 어려운 한 마디 연습 | 일반 플레이어 | Stemwise |
| --- | --- | --- |
| 반복 구간을 70%로 늦추기 | 배속 조절은 음높이를 6.2반음 낮춥니다 | 음높이가 그대로입니다. 단위 테스트가 50%, 70%, 150% 속도에서 440 Hz 사인파의 영점 교차를 셉니다 |
| 베이스만 듣기 | 스테레오 파일로는 불가능 | 베이스 스템을 솔로로 두거나 나머지 다섯 개를 음소거합니다 |
| 반주 트랙 만들기 | 노래방 버전을 찾아봄 | 음소거한 스템을 뺀 믹스를 WAV로 내보냅니다 |
| 코드 알아내기 | 되감아서 들어 봄 | 박자 격자에 맞춘 코드 레인. 근음 정확도는 스트럼 기타에서 0.739, 솔로에서 0.265입니다(아래 참고) |
| 클릭에 맞춰 연주하기 | 메트로놈을 직접 설정 | 곡 자체의 박자 격자를 따르는 클릭과 카운트인 |
| 템포를 단계적으로 올리기 | 슬라이더를 만지다 횟수를 놓침 | 스피드 트레이너는 실수 없는 반복이 정해진 횟수(기본 세 번) 이어지면 한 단계 올립니다. 실수하면 `X`를 누르고 횟수는 다시 시작됩니다 |

## 설치

아직 PyPI에 없으므로 GitHub에서 설치하세요. Python 3.10 이상과 ffmpeg도 필요합니다.

<details>
<summary>Linux(NVIDIA GPU 또는 CPU)</summary>

```sh
sudo apt install ffmpeg libsndfile1
pip install git+https://github.com/Arthur031221/Stemwise
stemwise doctor
```

Linux에서는 pip가 CUDA 빌드의 torch를 받아 오기 때문에 다운로드가 큽니다. CPU 전용 설치는 `--extra-index-url https://download.pytorch.org/whl/cpu`를 붙이세요.

</details>

<details>
<summary>macOS(Apple Silicon 또는 Intel)</summary>

```sh
brew install ffmpeg
pip install git+https://github.com/Arthur031221/Stemwise
stemwise doctor
```

torch가 MPS를 보고하면 Apple Silicon에서는 MPS 장치를 사용합니다. Mac에서의 속도는 측정하지 않았습니다.

</details>

<details>
<summary>Windows</summary>

```powershell
winget install Gyan.FFmpeg
pip install git+https://github.com/Arthur031221/Stemwise
stemwise doctor
```

Windows에서 Stemwise를 실행해 본 적은 없습니다. CI는 Linux만 다룹니다.

</details>

첫 분석에서 Demucs 약 55 MB와 beat_this 약 81 MB를 내려받습니다. 그 뒤에는 네트워크가 필요 없습니다.

## 사용해 보기

```sh
stemwise                      # 브라우저에서 스튜디오 열기
stemwise split song.mp3       # 파일 옆에 스템, chords.txt, beats.mid 저장
```

약 2분짜리 곡에서 `stemwise split`을 실행한 실제 출력입니다.

```
surf.mp3: 123s, 166.7 BPM, B major, 105 chords, on cuda
```

페이지에 파일을 끌어다 놓고 진행 표시줄이 끝나기를 기다립니다. 눈금자를 드래그해 반복 구간을 고르고, `L`을 누르면 재생 위치가 있는 마디를 반복하며, 아래 키를 쓸 수 있습니다. 전체 목록은 [docs/usage.md](docs/usage.md)에 있습니다.

| 키 | 동작 | 키 | 동작 |
| --- | --- | --- | --- |
| Space | 재생과 일시정지 | `[` `]` | 템포 5% 내리기, 올리기 |
| L | 이 마디 반복 또는 반복 전환 | Up, Down | 반음씩 키 이동 |
| C | 클릭 켜기와 끄기 | Left, Right | 한 마디 이동 |
| X | 실수(트레이너용) | 1에서 6 | 스템 음소거 |
| Esc | 루프 지우기 | Shift + Left, Right | 루프를 한 마디 늘이거나 줄이기 |

Stemwise는 곡마다 속도, 음높이, 음소거, 음량, 루프를 브라우저에 기억하고 마지막에 쓰던 곡을 다시 엽니다.

## 구성

| 부분 | 내용 |
| --- | --- |
| 분리 | Demucs v4 `htdemucs_6s`: 보컬, 드럼, 베이스, 기타, 피아노, 기타 악기 |
| 박자 | beat_this로 박, 강박, BPM 추적 |
| 코드 | CQT 크로마, 메이저, 마이너, 7, min7 템플릿, 비터비 평활화, 조 추정. 신경망 코드 모델은 쓰지 않습니다 |
| 플레이어 | WSOLA 시간 늘이기, 3차 리샘플러, 반복, 클릭, 카운트인을 갖춘 AudioWorklet 엔진 |
| 스튜디오 | 빌드가 필요 없는 ES 모듈과 CSS, UI 언어 아홉 개, 다크와 라이트 테마 |
| 내보내기 | 반주 트랙, 스템 zip, 텍스트 또는 인쇄용 HTML 코드 악보, MIDI 박자 격자 |
| API | 작은 로컬 JSON API. [docs/usage.md](docs/usage.md)에 설명되어 있습니다 |

브라우저 앱은 `web/`에 있으며, GitHub Pages가 라이브 데모로 서비스하는 바로 그 폴더입니다. 데모는 미리 분리해 둔 곡을 재생하며 내 파일은 분리할 수 없습니다.

## 얼마나 잘 되나

[GuitarSet](https://guitarset.weebly.com/)(솔로 기타 360클립)에서 `bench/chords_guitarset.py`를 실행했습니다. 코드 상수는 다섯 클립마다 하나씩으로 조정했고, 나머지 288클립으로 채점했습니다.

| 클립 | 근음 | 메이저와 마이너 | 박 F | 강박 F |
| --- | --- | --- | --- | --- |
| 반주, 144 | 0.739 | 0.671 | 0.971 | 0.944 |
| 솔로, 144 | 0.265 | 0.201 | 0.605 | 0.403 |

스트럼 연주에서는 박자를 믿을 수 있습니다. 코드는 곡을 익히기 위한 출발점이니 귀로 확인하세요. 단음 솔로에는 코드 정보가 거의 없어서 코드 레인은 대부분 틀립니다. 이 클립은 솔로 기타라서 밴드 전체 믹스에서 어떤 점수가 나올지는 말씀드릴 수 없습니다. 전체 표와 방법은 [docs/benchmarks.md](docs/benchmarks.md)에 있습니다.

## 한계

- 코드 레인이 아는 코드 종류는 네 가지뿐입니다. 슬래시 코드, 서스펜디드 코드, 확장 코드는 가장 가까운 네 가지 중 하나로 표시됩니다.
- 조는 곡 전체에 대한 하나의 추정입니다. 위 출력은 B 메이저라고 했지만 코드는 대부분 Em, D, Bm이므로 힌트로만 보세요.
- 표시되는 템포는 박자 추적기의 중앙값이라 공식 템포와 다를 수 있습니다. 데모 곡은 170 BPM으로 알려져 있지만 추적기는 166.7을 보고합니다.
- 연주곡 편곡에서는 보컬과 피아노 스템이 거의 비어 있습니다. 분리가 제대로 동작한 결과입니다.
- CPU에서 4분짜리 곡은 제가 측정한 2.7배속 기준으로 약 90초가 걸리고, 느린 칩에서는 더 걸립니다.
- 시간 늘이기는 WSOLA라서 가장 느린 설정에서는 길게 끄는 음이 번질 수 있습니다.
- 한 번에 한 곡만 처리합니다.

## 개발

```sh
pip install -e ".[dev]"
ruff check . && pytest -m "not slow and not e2e"
node --test tests/js/*.test.mjs
STEMWISE_BROWSER_CHANNEL=chrome pytest -m e2e
```

[CONTRIBUTING.md](CONTRIBUTING.md)를 참고하세요. `v`로 시작하는 태그는 릴리스 워크플로를 실행하여 wheel과 sdist를 빌드하고 GitHub 릴리스에 첨부합니다.

## 크레딧과 라이선스

Stemwise는 MIT 라이선스입니다. [Demucs](https://github.com/facebookresearch/demucs)(MIT), [beat_this](https://github.com/CPJKU/beat_this)(코드와 가중치 모두 MIT), librosa, Starlette를 바탕으로 합니다. 라이브 데모는 Kevin MacLeod의 "Surf Shimmy"([incompetech.com](https://incompetech.com))를 재생하며, [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 라이선스로 36초 구간을 잘라 Stemwise로 분리했습니다. GuitarSet은 Xi 외(2018)의 자료이며 CC BY 4.0입니다.

Assisted by Claude/Codex.
