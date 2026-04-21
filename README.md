# minimal-bms-auto

[![wakatime](https://wakatime.com/badge/user/018dd8a2-8532-40da-867c-26fa74be2cc0/project/304059e3-e448-4ca1-a5b5-7bf6741973f7.svg)](https://wakatime.com/badge/user/018dd8a2-8532-40da-867c-26fa74be2cc0/project/304059e3-e448-4ca1-a5b5-7bf6741973f7)

Minimal BMS (7KEY) player. Eventually plan to port this to some minimal display that plays charts nonstop on my desk, but for now it plays in a pygame window. I don't plan on making this a full-blown playable client, I just wanted to autoplay songs/charts I like.

To get into more detail, this parses a `.bms` or `.bme` into a Chart object. It then creates a Renderer which draws all the necessary objects (notes, measure lines, HUD, etc.) The Player keeps track of time and draws the frame at each tick using the Renderer. It also takes control of a Mixer (wrapper around pygame Mixer) to play sounds at whatever time.

## Demo

Playing: [Kyuzo Sameura feat. きりたん - ceu \[WHITE ANOTHER\] obj:Holy](http://www.dream-pro.info/~lavalse/LR2IR/search.cgi?mode=ranking&bmsid=298358)

https://github.com/user-attachments/assets/2c8ad7ce-cfaa-4a4b-ae3e-59bc9218d02a

## Setup

```sh
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install pygame pytest
```

## Run

```sh
python main.py [bms_filepath] [config_filepath]
```

defaults: `sample/ceu/7keys_white.bms` and `config.json`. Change as necessary

## Tests

```sh
python -m pytest tests/
```
