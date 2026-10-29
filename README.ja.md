# Stemwise

手元のマシンで動く練習スタジオです。曲を6つのステムに分け、コードとビートを表示し、音程を変えずにループを遅くできます。

[ライブデモ](https://arthur031221.github.io/Stemwise/) | [インストール](docs/install.md) | [使い方](docs/usage.md) | [設定](docs/config.md) | [アーキテクチャ](docs/architecture.md) | [ベンチマーク](docs/benchmarks.md)

[English](README.md) | [繁體中文](README.zh-TW.md) | [简体中文](README.zh-CN.md) | 日本語 | [한국어](README.ko.md) | [Español](README.es.md) | [Français](README.fr.md) | [Deutsch](README.de.md) | [Português (Brasil)](README.pt-BR.md)

![Stemwise：ドラムをミュートし、1小節をループし、70%に減速し、クリックを入れ、移調する](assets/demo.gif)

RTX 5090 でのステム分離は実時間の 122.5 倍です。2分3秒の曲が 1.00 秒で終わります（`stemwise bench`、fp32、ウォームアップ1回の後に3回計測して最良値）。3スレッドの Ryzen 5 7500F では同じ曲に 45.2 秒かかり、実時間の 2.7 倍です。

ファイルはあなたのマシンから出ません。そして、コードレーンが間違っている場所は隠さずに見せたいと考えています。

## 使う前と後

| 難しい1小節を練習する | 一般的なプレーヤー | Stemwise |
| --- | --- | --- |
| ループを70%に遅くする | バリスピードでは音程が6.2半音下がる | 音程は変わりません。ユニットテストが 50%、70%、150% の速度で 440 Hz の正弦波のゼロ交差を数えます |
| ベースだけを聴く | ステレオファイルでは不可能 | ベースのステムをソロにするか、他の5つをミュートします |
| バッキングトラックを作る | カラオケ版を探す | ミュートしたステムを除いたミックスを WAV で書き出します |
| コードを知る | 巻き戻して聴く | ビートグリッドに合わせたコードレーン。ルート正解率はストロークのギターで 0.739、ソロで 0.265（下記参照） |
| クリックに合わせて弾く | メトロノームを手で設定する | 曲自身のビートグリッドに従うクリックとカウントイン |
| テンポを段階的に上げる | スライダーを動かして回数を忘れる | スピードトレーナーは、ミスなしのループが決まった回数（初期値は3回）続くと1段階上げます。ミスしたら `X` を押すと数え直しになります |

## インストール

まだ PyPI にはないので、GitHub からインストールしてください。Python 3.10 以降と ffmpeg も必要です。

<details>
<summary>Linux（NVIDIA GPU または CPU）</summary>

```sh
sudo apt install ffmpeg libsndfile1
pip install git+https://github.com/Arthur031221/Stemwise
stemwise doctor
```

Linux では pip が CUDA 版の torch を取得するため、ダウンロードが大きくなります。CPU のみで使うなら `--extra-index-url https://download.pytorch.org/whl/cpu` を付けてください。

</details>

<details>
<summary>macOS（Apple Silicon または Intel）</summary>

```sh
brew install ffmpeg
pip install git+https://github.com/Arthur031221/Stemwise
stemwise doctor
```

torch が MPS を報告すると、Apple Silicon では MPS デバイスを使います。Mac での速度は測っていません。

</details>

<details>
<summary>Windows</summary>

```powershell
winget install Gyan.FFmpeg
pip install git+https://github.com/Arthur031221/Stemwise
stemwise doctor
```

Windows では Stemwise を動かしていません。CI がカバーするのは Linux のみです。

</details>

最初の解析で Demucs 約 55 MB と beat_this 約 81 MB をダウンロードします。その後はネットワークが不要です。

## 使ってみる

```sh
stemwise                      # ブラウザでスタジオを開く
stemwise split song.mp3       # ファイルの隣にステム、chords.txt、beats.mid を書き出す
```

約2分の曲で `stemwise split` を実行した実際の出力です。

```
surf.mp3: 123s, 166.7 BPM, B major, 105 chords, on cuda
```

ページにファイルをドロップして、進捗バーが終わるのを待ちます。ルーラー上をドラッグしてループを選び、`L` で再生位置の小節をループし、下のキーを使います。全キーの一覧は [docs/usage.md](docs/usage.md) にあります。

| キー | 動作 | キー | 動作 |
| --- | --- | --- | --- |
| Space | 再生と一時停止 | `[` `]` | テンポを5%下げる、上げる |
| L | この小節をループ、またはループの切り替え | Up、Down | 半音ずつ移調 |
| C | クリックのオンとオフ | Left、Right | 1小節移動 |
| X | ミス（トレーナー用） | 1 から 6 | ステムのミュート |
| Esc | ループを解除 | Shift + Left, Right | ループを1小節長く、または短く |

Stemwise は曲ごとの速度、ピッチ、ミュート、音量、ループをブラウザに保存し、前回使った曲をそのまま開きます。

## 構成

| 部分 | 内容 |
| --- | --- |
| 分離 | Demucs v4 `htdemucs_6s`：ボーカル、ドラム、ベース、ギター、ピアノ、その他 |
| ビート | beat_this によるビート、ダウンビート、BPM |
| コード | CQT クロマ、メジャー、マイナー、7 と min7 のテンプレート、ビタビ平滑化、キー推定。ニューラルのコードモデルは使っていません |
| プレーヤー | WSOLA タイムストレッチ、3次リサンプラー、ループ、クリック、カウントインを備えた AudioWorklet エンジン |
| スタジオ | ビルド不要の ES モジュールと CSS、9つの UI 言語、ダークとライトのテーマ |
| 書き出し | バッキングトラック、ステムの zip、テキストまたは印刷用 HTML のコード譜、MIDI のビートグリッド |
| API | 小さなローカル JSON API。[docs/usage.md](docs/usage.md) に記載 |

ブラウザアプリは `web/` にあり、GitHub Pages がライブデモとして公開しているのと同じフォルダです。デモは分離済みの曲を再生するだけで、あなたのファイルは分離できません。

## 精度はどうか

[GuitarSet](https://guitarset.weebly.com/)（ソロギター 360 クリップ）で `bench/chords_guitarset.py` を実行しました。コードの定数は5クリップに1つで調整し、残りの 288 クリップで採点しています。

| クリップ | ルート | メジャーとマイナー | ビート F | ダウンビート F |
| --- | --- | --- | --- | --- |
| 伴奏、144 | 0.739 | 0.671 | 0.971 | 0.944 |
| ソロ、144 | 0.265 | 0.201 | 0.605 | 0.403 |

ストロークのパートでは、ビートは信頼できます。コードは曲を覚えるための出発点なので、耳で確認してください。単音のソロにはコードの情報がほとんどないため、そこではコードレーンの大半が外れます。このクリップはソロギターなので、バンド全体のミックスでの成績は分かりません。完全な表と方法は [docs/benchmarks.md](docs/benchmarks.md) にあります。

## 制限

- コードレーンが知っているコードは4種類だけです。分数コード、サスペンデッドコード、テンションは最も近い4種類のどれかとして表示されます。
- キーは曲全体に対する1つの推定です。上の出力では B メジャーと出ていますが、コードは主に Em、D、Bm なので、ヒントとして扱ってください。
- 表示されるテンポはビートトラッカーの中央値なので、公表されているテンポと違うことがあります。デモ曲は 170 BPM とされていますが、トラッカーは 166.7 と報告します。
- インストゥルメンタルの曲では、ボーカルとピアノのステムがほぼ空になります。これは分離が正しく動いている結果です。
- CPU では4分の曲が、私の測定した 2.7 倍速で約90秒かかり、遅いチップではさらにかかります。
- タイムストレッチは WSOLA なので、最も遅い設定では持続音がにじむことがあります。
- 一度に処理できる曲は1つだけです。

## 開発

```sh
pip install -e ".[dev]"
ruff check . && pytest -m "not slow and not e2e"
node --test tests/js/*.test.mjs
STEMWISE_BROWSER_CHANNEL=chrome pytest -m e2e
```

[CONTRIBUTING.md](CONTRIBUTING.md) を参照してください。`v` で始まるタグはリリースワークフローを起動し、wheel と sdist をビルドして GitHub のリリースに添付します。

## クレジットとライセンス

Stemwise は MIT ライセンスです。[Demucs](https://github.com/facebookresearch/demucs)（MIT）、[beat_this](https://github.com/CPJKU/beat_this)（コードも重みも MIT）、librosa、Starlette を利用しています。ライブデモで再生する「Surf Shimmy」は Kevin MacLeod の作品（[incompetech.com](https://incompetech.com)）で、[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) のもと提供されており、36秒に切り出して Stemwise で分離しました。GuitarSet は Xi らによる（2018）もので、CC BY 4.0 です。

Assisted by Claude/Codex.
