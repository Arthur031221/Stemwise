# Stemwise

Um estúdio de prática local. Ele separa uma música em seis faixas, mostra acordes e batidas e desacelera um trecho em loop sem mudar o tom.

Separação de faixas 122,5 vezes mais rápida que o tempo real em uma RTX 5090. Uma música de 2 minutos e 3 segundos leva 1,00 s (`stemwise bench`, fp32, melhor de 3 após uma execução de aquecimento). Em um Ryzen 5 7500F com 3 threads, a mesma música leva 45,2 s, ou seja, 2,7 vezes o tempo real.

[Demo ao vivo](https://arthur031221.github.io/Stemwise/) | [Instalação](docs/install.md) | [Uso](docs/usage.md) | [Configuração](docs/config.md) | [Arquitetura](docs/architecture.md) | [Benchmarks](docs/benchmarks.md)

[English](README.md) | [繁體中文](README.zh-TW.md) | [简体中文](README.zh-CN.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Español](README.es.md) | [Français](README.fr.md) | [Deutsch](README.de.md) | Português (Brasil)

![Stemwise: silenciar a bateria, repetir um compasso, reduzir para 70 %, ligar o clique, transpor](assets/demo.gif)

Seus arquivos não saem da sua máquina, e prefiro mostrar onde a faixa de acordes erra a esconder isso.

## Antes e depois

| Praticar um compasso difícil | Um player comum | Stemwise |
| --- | --- | --- |
| Desacelerar um loop para 70 % | O varispeed baixa o tom em 6,2 semitons | O tom não muda. Um teste unitário conta os cruzamentos por zero de uma senoide de 440 Hz a 50 %, 70 % e 150 % de velocidade |
| Ouvir só o baixo | Impossível com um arquivo estéreo | Coloque o baixo em solo ou silencie as outras cinco faixas |
| Conseguir uma faixa de acompanhamento | Procurar uma versão de karaokê | Exporte a mixagem sem as faixas silenciadas, em WAV |
| Descobrir os acordes | Voltar a fita e ouvir de novo | Uma faixa de acordes sobre a grade de batidas. A precisão da fundamental é 0,739 em violão de acompanhamento e 0,265 em solos (veja abaixo) |
| Tocar com um clique | Um metrônomo que você ajusta à mão | Um clique que segue a grade de batidas da própria música, com contagem regressiva |
| Subir o andamento aos poucos | Mexer no controle e perder a conta | O treinador de velocidade sobe um passo depois de um número de loops limpos (três por padrão). Aperte `X` quando errar e a contagem recomeça |

## Instalação

Ainda não está no PyPI, então a instalação é pelo GitHub. Você também precisa de Python 3.10 ou mais novo e do ffmpeg.

<details>
<summary>Linux (GPU NVIDIA ou CPU)</summary>

```sh
sudo apt install ffmpeg libsndfile1
pip install git+https://github.com/Arthur031221/Stemwise
stemwise doctor
```

No Linux o pip baixa a versão CUDA do torch, que é grande. Acrescente `--extra-index-url https://download.pytorch.org/whl/cpu` para uma instalação só com CPU.

</details>

<details>
<summary>macOS (Apple Silicon ou Intel)</summary>

```sh
brew install ffmpeg
pip install git+https://github.com/Arthur031221/Stemwise
stemwise doctor
```

O Apple Silicon usa o dispositivo MPS quando o torch o informa. Não medi a velocidade em um Mac.

</details>

<details>
<summary>Windows</summary>

```powershell
winget install Gyan.FFmpeg
pip install git+https://github.com/Arthur031221/Stemwise
stemwise doctor
```

Não executei o Stemwise no Windows. A CI cobre apenas Linux.

</details>

A primeira análise baixa cerca de 55 MB do Demucs e 81 MB do beat_this. Depois disso não precisa de rede.

## Uso

```sh
stemwise                      # abre o estúdio no navegador
stemwise split song.mp3       # faixas, chords.txt e beats.mid ao lado do arquivo
```

Saída real de `stemwise split` em uma música de 2 minutos:

```
surf.mp3: 123s, 166.7 BPM, B major, 105 chords, on cuda
```

Solte um arquivo na página e espere a barra de progresso. Arraste sobre a régua para escolher um loop, aperte `L` para repetir o compasso sob o cursor e use as teclas abaixo. A lista completa está em [docs/usage.md](docs/usage.md).

| Tecla | Ação | Tecla | Ação |
| --- | --- | --- | --- |
| Space | tocar e pausar | `[` `]` | andamento menos e mais 5 % |
| L | repetir este compasso ou alternar o loop | Up, Down | transpor um semitom |
| C | clique ligado e desligado | Left, Right | pular um compasso |
| X | erro, para o treinador | 1 a 6 | silenciar uma faixa |

## O que vem dentro

| Parte | O que é |
| --- | --- |
| Separação | Demucs v4 `htdemucs_6s`: voz, bateria, baixo, guitarra, piano, outros |
| Batidas | beat_this para batidas, tempos fortes e BPM |
| Acordes | Cromagrama CQT, modelos de maior, menor, 7 e min7, suavização de Viterbi e estimativa de tonalidade. Sem modelo neural de acordes |
| Player | Um motor AudioWorklet com esticamento de tempo WSOLA, reamostrador cúbico, loops, clique e contagem regressiva |
| Estúdio | Módulos ES e CSS sem etapa de build, nove idiomas de interface, temas escuro e claro |
| Exportações | Faixa de acompanhamento, zip das faixas, cifra em texto ou em HTML para impressão, grade de batidas em MIDI |
| API | Uma pequena API JSON local, descrita em [docs/usage.md](docs/usage.md) |

O app de navegador fica em `web/`, a mesma pasta que o GitHub Pages serve como demo ao vivo. A demo toca uma música já separada e não consegue separar os seus arquivos.

## Como funciona na prática

Rodei `bench/chords_guitarset.py` no [GuitarSet](https://guitarset.weebly.com/) (360 trechos de violão solo). Ajustei as constantes de acordes em um a cada cinco trechos e pontuei os outros 288.

| Trechos | Fundamental | Maior e menor | Batida F | Tempo forte F |
| --- | --- | --- | --- | --- |
| Acompanhamento, 144 | 0.739 | 0.671 | 0.971 | 0.944 |
| Solos, 144 | 0.265 | 0.201 | 0.605 | 0.403 |

As batidas são confiáveis nas partes de acompanhamento. Os acordes são um ponto de partida para aprender uma música, então confira de ouvido. Um solo de notas soltas quase não tem informação de acorde, e a faixa erra na maior parte do tempo. Esses trechos são de violão solo, então não sei dizer como uma mixagem de banda completa se sai. A tabela completa e o método estão em [docs/benchmarks.md](docs/benchmarks.md).

## Limites

- A faixa de acordes conhece quatro tipos de acorde. Acordes com baixo diferente, suspensos e estendidos aparecem como o mais próximo dos quatro.
- A tonalidade é uma única estimativa para a música inteira. Na saída acima ela diz Si maior, enquanto os acordes são principalmente Em, D e Bm, então trate-a como uma pista.
- O andamento mostrado é a mediana do detector de batidas e pode diferir do andamento publicado. A música da demo consta com 170 BPM e o detector dá 166,7.
- Uma música instrumental deixa as faixas de voz e piano quase vazias. Isso é a separação funcionando direito.
- Em uma CPU, uma música de quatro minutos leva cerca de 90 segundos nas 2,7 vezes que medi, e mais em chips mais lentos.
- O esticamento de tempo é WSOLA, que pode borrar notas longas nos ajustes mais lentos.
- Só uma música é processada por vez.

## Desenvolvimento

```sh
pip install -e ".[dev]"
ruff check . && pytest -m "not slow and not e2e"
node --test tests/js/*.test.mjs
STEMWISE_BROWSER_CHANNEL=chrome pytest -m e2e
```

Veja [CONTRIBUTING.md](CONTRIBUTING.md). Uma tag que começa com `v` dispara o workflow de lançamento, que constrói o wheel e o sdist e os anexa a uma release do GitHub.

## Créditos e licenças

O Stemwise usa a licença MIT. Ele se apoia em [Demucs](https://github.com/facebookresearch/demucs) (MIT), [beat_this](https://github.com/CPJKU/beat_this) (código e pesos MIT), librosa e Starlette. A demo ao vivo toca "Surf Shimmy" de Kevin MacLeod ([incompetech.com](https://incompetech.com)), sob [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), cortada em um trecho de 36 segundos e separada com o Stemwise. O GuitarSet é de Xi et al. (2018), CC BY 4.0.

Assisted by Claude/Codex.
