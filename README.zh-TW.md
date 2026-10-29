# Stemwise

本機運行的練習工作室。它把一首歌分成六軌，顯示和弦與節拍，並能在不改變音高的情況下放慢循環段落。

[線上示範](https://arthur031221.github.io/Stemwise/) | [安裝](docs/install.md) | [使用](docs/usage.md) | [設定](docs/config.md) | [架構](docs/architecture.md) | [效能測試](docs/benchmarks.md)

[English](README.md) | 繁體中文 | [简体中文](README.zh-CN.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Español](README.es.md) | [Français](README.fr.md) | [Deutsch](README.de.md) | [Português (Brasil)](README.pt-BR.md)

![Stemwise：鼓靜音、循環一小節、放慢到 70%、開啟節拍器、移調](assets/demo.gif)

在 RTX 5090 上，音軌分離速度是即時的 122.5 倍。一首 2 分 3 秒的歌只要 1.00 秒（`stemwise bench`，fp32，暖機一次後三次取最佳）。在 3 個執行緒的 Ryzen 5 7500F 上，同一首歌需要 45.2 秒，也就是即時的 2.7 倍。

你的檔案不會離開你的電腦，而且我寧可讓你看到和弦軌哪裡出錯，也不想把它藏起來。

## 使用前後

| 練習一個難的小節 | 一般播放器 | Stemwise |
| --- | --- | --- |
| 把循環放慢到 70% | 變速播放會讓音高降低 6.2 個半音 | 音高不變。單元測試會在 50%、70%、150% 速度下計算 440 Hz 正弦波的過零次數 |
| 只聽貝斯 | 立體聲檔案做不到 | 單獨播放貝斯軌，或把其他五軌靜音 |
| 取得伴奏 | 去找卡拉 OK 版本 | 匯出靜音後剩下的混音，格式為 WAV |
| 找出和弦 | 倒帶再聽 | 和弦軌對齊節拍格線。扒弦吉他的根音準確率是 0.739，獨奏是 0.265（見下方） |
| 跟著節拍器練 | 自己手動設定節拍器 | 節拍器跟著歌曲本身的節拍格線走，並有預備拍 |
| 逐步提高速度 | 拉動滑桿後數不清楚 | 速度訓練器在指定次數的無失誤循環後加一級（預設三次）。失誤時按 `X`，計數會重新開始 |

## 安裝

目前還沒有上架 PyPI，請從 GitHub 安裝。你還需要 Python 3.10 或更新版本，以及 ffmpeg。

<details>
<summary>Linux（NVIDIA GPU 或 CPU）</summary>

```sh
sudo apt install ffmpeg libsndfile1
pip install git+https://github.com/Arthur031221/Stemwise
stemwise doctor
```

在 Linux 上 pip 會下載 CUDA 版的 torch，檔案很大。若只用 CPU，請加上 `--extra-index-url https://download.pytorch.org/whl/cpu`。

</details>

<details>
<summary>macOS（Apple Silicon 或 Intel）</summary>

```sh
brew install ffmpeg
pip install git+https://github.com/Arthur031221/Stemwise
stemwise doctor
```

torch 回報有 MPS 時，Apple Silicon 會使用 MPS 裝置。我沒有在 Mac 上測過速度。

</details>

<details>
<summary>Windows</summary>

```powershell
winget install Gyan.FFmpeg
pip install git+https://github.com/Arthur031221/Stemwise
stemwise doctor
```

我沒有在 Windows 上執行過 Stemwise。CI 只涵蓋 Linux。

</details>

第一次分析會下載約 55 MB 的 Demucs 和 81 MB 的 beat_this。之後就不需要網路。

## 使用方式

```sh
stemwise                      # 在瀏覽器中開啟工作室
stemwise split song.mp3       # 在檔案旁邊產生音軌、chords.txt 和 beats.mid
```

在一首約 2 分鐘的歌上執行 `stemwise split` 的實際輸出：

```
surf.mp3: 123s, 166.7 BPM, B major, 105 chords, on cuda
```

把檔案拖進頁面，等進度條跑完。在時間尺上拖曳可選取循環範圍，按 `L` 可循環播放頭所在的小節，其他按鍵見下表。完整列表在 [docs/usage.md](docs/usage.md)。

| 按鍵 | 動作 | 按鍵 | 動作 |
| --- | --- | --- | --- |
| Space | 播放與暫停 | `[` `]` | 速度降低與提高 5% |
| L | 循環這一小節，或切換循環 | Up、Down | 移調一個半音 |
| C | 節拍器開關 | Left、Right | 跳一小節 |
| X | 失誤，給速度訓練器 | 1 到 6 | 音軌靜音 |
| Esc | 清除循環 | Shift + Left, Right | 循環加長或縮短一小節 |

Stemwise 會在瀏覽器裡記住每首歌的速度、音高、靜音、音量和循環，下次開啟時回到你上次用的那首歌。

## 內容一覽

| 部分 | 說明 |
| --- | --- |
| 分離 | Demucs v4 `htdemucs_6s`：人聲、鼓、貝斯、吉他、鋼琴、其他 |
| 節拍 | 用 beat_this 取得節拍、強拍與 BPM |
| 和弦 | CQT 色度、大三、小三、7 與 min7 範本、維特比平滑和調性估計。沒有使用神經網路和弦模型 |
| 播放器 | AudioWorklet 引擎，含 WSOLA 時間伸縮、三次重取樣器、循環、節拍器和預備拍 |
| 介面 | 純 ES 模組和 CSS，不需建置，支援九種介面語言，深色與淺色主題 |
| 匯出 | 伴奏、音軌 zip、純文字或可列印 HTML 的和弦譜、MIDI 節拍格線 |
| API | 小型本機 JSON API，文件在 [docs/usage.md](docs/usage.md) |

瀏覽器應用程式在 `web/`，也就是 GitHub Pages 提供線上示範的同一個資料夾。示範播放的是事先分離好的歌曲，無法分離你自己的檔案。

## 效果如何

我在 [GuitarSet](https://guitarset.weebly.com/)（360 段獨奏吉他）上執行了 `bench/chords_guitarset.py`。和弦常數是用每五段取一段來調整，評分用的是其餘 288 段。

| 片段 | 根音 | 大小調 | 節拍 F | 強拍 F |
| --- | --- | --- | --- | --- |
| 伴奏，144 段 | 0.739 | 0.671 | 0.971 | 0.944 |
| 獨奏，144 段 | 0.265 | 0.201 | 0.605 | 0.403 |

扒弦部分的節拍很可靠。和弦只是學歌的起點，請用耳朵確認。單音獨奏幾乎沒有和弦資訊，所以和弦軌在那裡大多是錯的。這些片段都是獨奏吉他，所以我無法告訴你完整樂團混音的成績。完整表格和方法在 [docs/benchmarks.md](docs/benchmarks.md)。

## 限制

- 和弦軌只認得四種和弦類型。轉位和弦、掛留和弦與延伸和弦會顯示成最接近的那一種。
- 調性是整首歌的單一猜測。上方輸出說是 B 大調，但和弦大多是 Em、D 和 Bm，所以請當成提示。
- 顯示的速度是節拍追蹤器的中位數，可能和公開的速度不同。示範歌曲標示為 170 BPM，追蹤器回報 166.7。
- 純樂器編曲的歌曲，人聲和鋼琴軌幾乎是空的。這是分離正確運作的結果。
- 在 CPU 上，一首四分鐘的歌以我測得的 2.7 倍速約需 90 秒，較慢的晶片會更久。
- 時間伸縮用的是 WSOLA，在最慢的設定下可能讓持續音變得模糊。
- 一次只處理一首歌。

## 開發

```sh
pip install -e ".[dev]"
ruff check . && pytest -m "not slow and not e2e"
node --test tests/js/*.test.mjs
STEMWISE_BROWSER_CHANNEL=chrome pytest -m e2e
```

請見 [CONTRIBUTING.md](CONTRIBUTING.md)。以 `v` 開頭的標籤會觸發發行工作流程，建置 wheel 和 sdist 並附加到 GitHub 發行版。

## 致謝與授權

Stemwise 採用 MIT 授權。它建立在 [Demucs](https://github.com/facebookresearch/demucs)（MIT）、[beat_this](https://github.com/CPJKU/beat_this)（程式碼與權重皆為 MIT）、librosa 和 Starlette 之上。線上示範播放的是 Kevin MacLeod 的「Surf Shimmy」（[incompetech.com](https://incompetech.com)），以 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 授權，剪成 36 秒片段並用 Stemwise 分離。GuitarSet 由 Xi 等人（2018）製作，採 CC BY 4.0。

Assisted by Claude/Codex.
