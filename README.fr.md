# Stemwise

Un studio de pratique local. Il sépare un morceau en six pistes, affiche les accords et les temps, et ralentit une boucle sans changer la hauteur.

[Démo en ligne](https://arthur031221.github.io/Stemwise/) | [Installation](docs/install.md) | [Utilisation](docs/usage.md) | [Configuration](docs/config.md) | [Architecture](docs/architecture.md) | [Benchmarks](docs/benchmarks.md)

[English](README.md) | [繁體中文](README.zh-TW.md) | [简体中文](README.zh-CN.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Español](README.es.md) | Français | [Deutsch](README.de.md) | [Português (Brasil)](README.pt-BR.md)

![Stemwise : couper la batterie, boucler une mesure, ralentir à 70 %, activer le clic, transposer](assets/demo.gif)

Séparation des pistes 122,5 fois plus rapide que le temps réel sur une RTX 5090. Un morceau de 2 minutes 3 secondes prend 1,00 s (`stemwise bench`, fp32, meilleur de 3 après un passage d'échauffement). Sur un Ryzen 5 7500F avec 3 threads, le même morceau prend 45,2 s, soit 2,7 fois le temps réel.

Vos fichiers ne quittent pas votre machine, et je préfère vous montrer où la piste d'accords se trompe plutôt que de le cacher.

## Avant et après

| Travailler une mesure difficile | Un lecteur classique | Stemwise |
| --- | --- | --- |
| Ralentir une boucle à 70 % | Le varispeed baisse la hauteur de 6,2 demi-tons | La hauteur ne bouge pas. Un test unitaire compte les passages par zéro d'un sinus à 440 Hz à 50 %, 70 % et 150 % de vitesse |
| Entendre seulement la basse | Impossible avec un fichier stéréo | Mettez la basse en solo, ou coupez les cinq autres pistes |
| Obtenir une piste d'accompagnement | Chercher une version karaoké | Exportez le mix sans les pistes coupées, en WAV |
| Trouver les accords | Rembobiner et écouter | Une piste d'accords sur la grille de temps. La justesse de la fondamentale est de 0,739 sur la guitare en accompagnement et de 0,265 sur les solos (voir plus bas) |
| Jouer sur un clic | Un métronome réglé à la main | Un clic qui suit la grille de temps du morceau, avec un décompte |
| Monter le tempo par paliers | Bouger le curseur et perdre le compte | L'entraîneur de vitesse ajoute un palier après un nombre de boucles propres (trois par défaut). Appuyez sur `X` quand vous ratez et le compte repart de zéro |

## Installation

Le paquet n'est pas encore sur PyPI, il faut donc l'installer depuis GitHub. Il faut aussi Python 3.10 ou plus récent et ffmpeg.

<details>
<summary>Linux (GPU NVIDIA ou CPU)</summary>

```sh
sudo apt install ffmpeg libsndfile1
pip install git+https://github.com/Arthur031221/Stemwise
stemwise doctor
```

Sous Linux, pip récupère la version CUDA de torch, qui est volumineuse. Ajoutez `--extra-index-url https://download.pytorch.org/whl/cpu` pour une installation CPU seulement.

</details>

<details>
<summary>macOS (Apple Silicon ou Intel)</summary>

```sh
brew install ffmpeg
pip install git+https://github.com/Arthur031221/Stemwise
stemwise doctor
```

Apple Silicon utilise le périphérique MPS quand torch le signale. Je n'ai pas mesuré la vitesse sur un Mac.

</details>

<details>
<summary>Windows</summary>

```powershell
winget install Gyan.FFmpeg
pip install git+https://github.com/Arthur031221/Stemwise
stemwise doctor
```

Je n'ai pas lancé Stemwise sous Windows. La CI ne couvre que Linux.

</details>

La première analyse télécharge environ 55 Mo pour Demucs et 81 Mo pour beat_this. Ensuite, plus besoin de réseau.

## Utilisation

```sh
stemwise                      # ouvre le studio dans le navigateur
stemwise split song.mp3       # pistes, chords.txt et beats.mid à côté du fichier
```

Sortie réelle de `stemwise split` sur un morceau de 2 minutes :

```
surf.mp3: 123s, 166.7 BPM, B major, 105 chords, on cuda
```

Déposez un fichier sur la page et attendez la barre de progression. Faites glisser sur la règle pour choisir une boucle, appuyez sur `L` pour boucler la mesure où se trouve la tête de lecture, et utilisez les touches ci-dessous. La liste complète est dans [docs/usage.md](docs/usage.md).

| Touche | Action | Touche | Action |
| --- | --- | --- | --- |
| Space | lecture et pause | `[` `]` | tempo moins et plus 5 % |
| L | boucler cette mesure ou activer la boucle | Up, Down | transposer d'un demi-ton |
| C | clic activé et désactivé | Left, Right | aller d'une mesure |
| X | raté, pour l'entraîneur | 1 à 6 | couper une piste |
| Esc | effacer la boucle | Shift + Left, Right | boucle plus longue ou plus courte d'une mesure |

Stemwise garde dans votre navigateur la vitesse, la hauteur, les pistes coupées, les niveaux et la boucle de chaque morceau, et rouvre le dernier que vous avez utilisé.

## Ce qu'il y a dedans

| Partie | Ce que c'est |
| --- | --- |
| Séparation | Demucs v4 `htdemucs_6s` : voix, batterie, basse, guitare, piano, autres |
| Temps | beat_this pour les temps, les premiers temps et le BPM |
| Accords | Chromagramme CQT, modèles majeur, mineur, 7 et min7, lissage de Viterbi et estimation de la tonalité. Pas de modèle d'accords neuronal |
| Lecteur | Un moteur AudioWorklet avec étirement temporel WSOLA, rééchantillonneur cubique, boucles, clic et décompte |
| Studio | Modules ES et CSS sans étape de build, neuf langues d'interface, thèmes sombre et clair |
| Exports | Piste d'accompagnement, zip des pistes, grille d'accords en texte ou en HTML imprimable, grille de temps en MIDI |
| API | Une petite API JSON locale, décrite dans [docs/usage.md](docs/usage.md) |

L'application web se trouve dans `web/`, le même dossier que GitHub Pages sert comme démo en ligne. La démo joue un morceau déjà séparé et ne peut pas séparer vos fichiers.

## Ce que ça vaut

J'ai lancé `bench/chords_guitarset.py` sur [GuitarSet](https://guitarset.weebly.com/) (360 extraits de guitare seule). J'ai réglé les constantes d'accords sur un extrait sur cinq et noté les 288 autres.

| Extraits | Fondamentale | Majeur et mineur | Temps F | Premier temps F |
| --- | --- | --- | --- | --- |
| Accompagnement, 144 | 0.739 | 0.671 | 0.971 | 0.944 |
| Solos, 144 | 0.265 | 0.201 | 0.605 | 0.403 |

Les temps sont fiables sur les parties en accompagnement. Les accords sont un point de départ pour apprendre un morceau, vérifiez-les donc à l'oreille. Un solo en notes isolées contient presque aucune information d'accord, et la piste s'y trompe la plupart du temps. Ces extraits sont de la guitare seule, je ne peux donc pas dire ce que donnerait un mix de groupe complet. Le tableau complet et la méthode sont dans [docs/benchmarks.md](docs/benchmarks.md).

## Limites

- La piste d'accords ne connaît que quatre types d'accords. Les accords avec basse, suspendus ou enrichis apparaissent comme le plus proche des quatre.
- La tonalité est une seule estimation pour tout le morceau. Dans la sortie ci-dessus, elle indique si majeur alors que les accords sont surtout Em, D et Bm, il faut donc la prendre comme un indice.
- Le tempo affiché est la médiane du détecteur de temps, il peut donc différer du tempo publié. Le morceau de la démo est annoncé à 170 BPM et le détecteur donne 166,7.
- Un morceau instrumental laisse les pistes de voix et de piano presque vides. C'est la séparation qui fonctionne correctement.
- Sur CPU, un morceau de quatre minutes prend environ 90 secondes au rythme de 2,7 fois que j'ai mesuré, et plus sur des puces plus lentes.
- L'étirement temporel est du WSOLA, qui peut brouiller les notes tenues aux réglages les plus lents.
- Un seul morceau est traité à la fois.

## Développement

```sh
pip install -e ".[dev]"
ruff check . && pytest -m "not slow and not e2e"
node --test tests/js/*.test.mjs
STEMWISE_BROWSER_CHANNEL=chrome pytest -m e2e
```

Voir [CONTRIBUTING.md](CONTRIBUTING.md). Un tag qui commence par `v` déclenche le workflow de publication, qui construit le wheel et le sdist et les joint à une release GitHub.

## Crédits et licences

Stemwise est sous licence MIT. Il s'appuie sur [Demucs](https://github.com/facebookresearch/demucs) (MIT), [beat_this](https://github.com/CPJKU/beat_this) (code et poids sous MIT), librosa et Starlette. La démo en ligne joue « Surf Shimmy » de Kevin MacLeod ([incompetech.com](https://incompetech.com)), sous licence [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), coupé en un extrait de 36 secondes et séparé avec Stemwise. GuitarSet est de Xi et al. (2018), CC BY 4.0.

Assisted by Claude/Codex.
