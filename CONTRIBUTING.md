# Contributing

Thanks for looking. Bug reports with a file that reproduces the problem are the most useful thing you can send.

## Set up

```sh
git clone https://github.com/Arthur031221/Stemwise
cd Stemwise
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
```

You need ffmpeg on your PATH. For the browser tests also run `playwright install chrome`.

## Checks

Run these before opening a pull request. CI runs the same ones.

```sh
ruff check . && ruff format --check .
pytest -m "not slow and not e2e"        # fast, no model weights
node --test tests/js/*.test.mjs
STEMWISE_BROWSER_CHANNEL=chrome pytest -m e2e
pytest -m slow                          # real Demucs and beat_this, downloads weights
```

## Guidelines

- Keep the browser side free of a build step. Plain ES modules, no framework.
- A new UI string goes into every file in `web/locales/`. `tests/js/pure.test.mjs` fails if the keys or placeholders differ.
  A machine translation is fine for a first pass, say so in the pull request and a native speaker can fix it.
- A change to the chord or beat logic should come with a number from `bench/chords_guitarset.py`.
- Add a test with the fix. The stub separator in `tests/conftest.py` keeps most tests fast.
- Keep pull requests small and describe what you ran.

## Adding a language

Copy `web/locales/en.json`, translate the values, add the code to the list in `web/js/i18n.js`, and add a
translated README as `README.<code>.md` at the top of the repository if you want one. It must end with the same last
line as the English README.
