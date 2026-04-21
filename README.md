# minimal-bms-auto

A minimal BMS 7K+S chart player written in Python using pygame. I wrote this for fun because I wanted to understand how BMS is parsed and how players are (generally) built. This is the most fun I have ever had completing a project.

This parses a `.bms`/`.bme` file, builds a chart representation, renders falling notes in a pygame window, and plays keysounds + BGM audio in sync.

## Requirements

- Python 3.12+
- pygame 2.x (SDL 2)

## Setup

```sh
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install pygame pytest
```

## Running

```sh
python main.py [bms_filepath] [config_filepath]
```

Defaults to `sample/ceu/7keys_white.bms` and `config.json`.

## Tests

```sh
python -m pytest tests/
```

## Note (AI)

All unit/integration tests were written by AI, but I manually reviewed all of them.
