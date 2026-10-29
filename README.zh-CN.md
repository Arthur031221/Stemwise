# Stemwise

本机运行的练习工作室。它把一首歌分成六轨，显示和弦与节拍，并能在不改变音高的情况下放慢循环片段。

[在线演示](https://arthur031221.github.io/Stemwise/) | [安装](docs/install.md) | [使用](docs/usage.md) | [配置](docs/config.md) | [架构](docs/architecture.md) | [性能测试](docs/benchmarks.md)

[English](README.md) | [繁體中文](README.zh-TW.md) | 简体中文 | [日本語](README.ja.md) | [한국어](README.ko.md) | [Español](README.es.md) | [Français](README.fr.md) | [Deutsch](README.de.md) | [Português (Brasil)](README.pt-BR.md)

![Stemwise：鼓静音、循环一小节、放慢到 70%、开启节拍器、移调](assets/demo.gif)

在 RTX 5090 上，音轨分离速度是实时的 122.5 倍。一首 2 分 3 秒的歌只要 1.00 秒（`stemwise bench`，fp32，预热一次后三次取最佳）。在 3 个线程的 Ryzen 5 7500F 上，同一首歌需要 45.2 秒，也就是实时的 2.7 倍。

你的文件不会离开你的电脑，而且我宁可让你看到和弦轨哪里出错，也不想把它藏起来。

## 使用前后

| 练习一个难的小节 | 普通播放器 | Stemwise |
| --- | --- | --- |
| 把循环放慢到 70% | 变速播放会让音高降低 6.2 个半音 | 音高不变。单元测试会在 50%、70%、150% 速度下统计 440 Hz 正弦波的过零次数 |
| 只听贝斯 | 立体声文件做不到 | 单独播放贝斯轨，或把其他五轨静音 |
| 获取伴奏 | 去找卡拉 OK 版本 | 导出静音后剩下的混音，格式为 WAV |
| 找出和弦 | 倒带再听 | 和弦轨对齐节拍网格。扫弦吉他的根音准确率是 0.739，独奏是 0.265（见下方） |
| 跟着节拍器练 | 自己手动设置节拍器 | 节拍器跟着歌曲本身的节拍网格走，并有预备拍 |
| 逐步提高速度 | 拖动滑块后数不清楚 | 速度训练器在指定次数的无失误循环后加一级（默认三次）。失误时按 `X`，计数会重新开始 |

## 安装

目前还没有上架 PyPI，请从 GitHub 安装。你还需要 Python 3.10 或更新版本，以及 ffmpeg。

<details>
<summary>Linux（NVIDIA GPU 或 CPU）</summary>

```sh
sudo apt install ffmpeg libsndfile1
pip install git+https://github.com/Arthur031221/Stemwise
stemwise doctor
```

在 Linux 上 pip 会下载 CUDA 版的 torch，文件很大。若只用 CPU，请加上 `--extra-index-url https://download.pytorch.org/whl/cpu`。

</details>

<details>
<summary>macOS（Apple Silicon 或 Intel）</summary>

```sh
brew install ffmpeg
pip install git+https://github.com/Arthur031221/Stemwise
stemwise doctor
```

torch 报告有 MPS 时，Apple Silicon 会使用 MPS 设备。我没有在 Mac 上测过速度。

</details>

<details>
<summary>Windows</summary>

```powershell
winget install Gyan.FFmpeg
pip install git+https://github.com/Arthur031221/Stemwise
stemwise doctor
```

我没有在 Windows 上运行过 Stemwise。CI 只覆盖 Linux。

</details>

第一次分析会下载约 55 MB 的 Demucs 和 81 MB 的 beat_this。之后就不需要网络。

## 使用方式

```sh
stemwise                      # 在浏览器中打开工作室
stemwise split song.mp3       # 在文件旁边生成音轨、chords.txt 和 beats.mid
```

在一首约 2 分钟的歌上运行 `stemwise split` 的实际输出：

```
surf.mp3: 123s, 166.7 BPM, B major, 105 chords, on cuda
```

把文件拖进页面，等进度条跑完。在时间尺上拖动可选取循环范围，按 `L` 可循环播放头所在的小节，其他按键见下表。完整列表在 [docs/usage.md](docs/usage.md)。

| 按键 | 动作 | 按键 | 动作 |
| --- | --- | --- | --- |
| Space | 播放与暂停 | `[` `]` | 速度降低与提高 5% |
| L | 循环这一小节，或切换循环 | Up、Down | 移调一个半音 |
| C | 节拍器开关 | Left、Right | 跳一小节 |
| X | 失误，给速度训练器 | 1 到 6 | 音轨静音 |
| Esc | 清除循环 | Shift + Left, Right | 循环加长或缩短一小节 |

Stemwise 会在浏览器里记住每首歌的速度、音高、静音、音量和循环，下次打开时回到你上次用的那首歌。

## 内容一览

| 部分 | 说明 |
| --- | --- |
| 分离 | Demucs v4 `htdemucs_6s`：人声、鼓、贝斯、吉他、钢琴、其他 |
| 节拍 | 用 beat_this 获取节拍、强拍与 BPM |
| 和弦 | CQT 色度、大三、小三、7 与 min7 模板、维特比平滑和调性估计。没有使用神经网络和弦模型 |
| 播放器 | AudioWorklet 引擎，含 WSOLA 时间伸缩、三次重采样器、循环、节拍器和预备拍 |
| 界面 | 纯 ES 模块和 CSS，无需构建，支持九种界面语言，深色与浅色主题 |
| 导出 | 伴奏、音轨 zip、纯文本或可打印 HTML 的和弦谱、MIDI 节拍网格 |
| API | 小型本机 JSON API，文档在 [docs/usage.md](docs/usage.md) |

浏览器应用在 `web/`，也就是 GitHub Pages 提供在线演示的同一个文件夹。演示播放的是事先分离好的歌曲，无法分离你自己的文件。

## 效果如何

我在 [GuitarSet](https://guitarset.weebly.com/)（360 段独奏吉他）上运行了 `bench/chords_guitarset.py`。和弦常数是用每五段取一段来调整，评分用的是其余 288 段。

| 片段 | 根音 | 大小调 | 节拍 F | 强拍 F |
| --- | --- | --- | --- | --- |
| 伴奏，144 段 | 0.739 | 0.671 | 0.971 | 0.944 |
| 独奏，144 段 | 0.265 | 0.201 | 0.605 | 0.403 |

扫弦部分的节拍很可靠。和弦只是学歌的起点，请用耳朵确认。单音独奏几乎没有和弦信息，所以和弦轨在那里大多是错的。这些片段都是独奏吉他，所以我无法告诉你完整乐队混音的成绩。完整表格和方法在 [docs/benchmarks.md](docs/benchmarks.md)。

## 限制

- 和弦轨只认得四种和弦类型。转位和弦、挂留和弦与扩展和弦会显示成最接近的那一种。
- 调性是整首歌的单一猜测。上方输出说是 B 大调，但和弦大多是 Em、D 和 Bm，所以请当作提示。
- 显示的速度是节拍追踪器的中位数，可能和公布的速度不同。演示歌曲标注为 170 BPM，追踪器报告 166.7。
- 纯乐器编曲的歌曲，人声和钢琴轨几乎是空的。这是分离正确工作的结果。
- 在 CPU 上，一首四分钟的歌以我测得的 2.7 倍速约需 90 秒，较慢的芯片会更久。
- 时间伸缩用的是 WSOLA，在最慢的设置下可能让持续音变得模糊。
- 一次只处理一首歌。

## 开发

```sh
pip install -e ".[dev]"
ruff check . && pytest -m "not slow and not e2e"
node --test tests/js/*.test.mjs
STEMWISE_BROWSER_CHANNEL=chrome pytest -m e2e
```

请见 [CONTRIBUTING.md](CONTRIBUTING.md)。以 `v` 开头的标签会触发发布工作流，构建 wheel 和 sdist 并附加到 GitHub 发布版。

## 致谢与许可

Stemwise 采用 MIT 许可。它建立在 [Demucs](https://github.com/facebookresearch/demucs)（MIT）、[beat_this](https://github.com/CPJKU/beat_this)（代码与权重均为 MIT）、librosa 和 Starlette 之上。在线演示播放的是 Kevin MacLeod 的《Surf Shimmy》（[incompetech.com](https://incompetech.com)），以 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 授权，剪成 36 秒片段并用 Stemwise 分离。GuitarSet 由 Xi 等人（2018）制作，采用 CC BY 4.0。

Assisted by Claude/Codex.
