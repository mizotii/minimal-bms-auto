# minimal-bms-auto

A minimal BMS 7K+S chart player written in Python using pygame. I wrote this for fun because I wanted to understand how BMS is parsed and how players are (generally) built. I structured it the way I did because I eventually want to port this to some minimal LED display that just plays BMS charts nonstop. This is the most fun I have ever had completing a project.

This parses a `.bms`/`.bme` file, builds a chart representation, renders falling notes in a pygame window, and plays keysounds + BGM audio in sync.

## Demo

Playing: [Kyuzo Sameura feat. きりたん - ceu \[WHITE ANOTHER\] obj:Holy](http://www.dream-pro.info/~lavalse/LR2IR/search.cgi?mode=ranking&bmsid=298358)

https://github.com/user-attachments/assets/2c8ad7ce-cfaa-4a4b-ae3e-59bc9218d02a

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
