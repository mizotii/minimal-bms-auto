import argparse
import json
import pygame
from audio import Mixer
from parse import BMSParser
from play import Player
from system import _elevate_process_priority
from render import PygameRenderer, RenderConfig
import pprint

DEFAULT_BMS_PATH = r'sample\ceu\7keys_white.bms'
DEFAULT_CONFIG_PATH = r'config.json'
OUTRO_DURATION = 2.0

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('bms_filepath', nargs='?', default=DEFAULT_BMS_PATH)
    parser.add_argument('config_filepath', nargs='?', default=DEFAULT_CONFIG_PATH)
    args = parser.parse_args()

    _elevate_process_priority()

    # parse chart, print summary
    chart = BMSParser(args.bms_filepath).build()
    print(chart)

    # setup
    with open(args.config_filepath) as config_file:
        config_raw = json.load(config_file)

    config = RenderConfig(**config_raw)
    renderer = PygameRenderer(config)
    audio = Mixer(chart)
    player = Player(chart, renderer, config, audio)

    # play loop
    player.start()
    prev_time = pygame.time.get_ticks()

    while True:
        renderer.poll_quit()

        cur_time = pygame.time.get_ticks()
        time_delta = (cur_time - prev_time) / 1000
        prev_time = cur_time
        player.update(time_delta)

        player.render_frame()
        renderer.flip()

        if player.current_time > chart.total_time + OUTRO_DURATION:
            break

    pygame.quit()

if __name__ == '__main__':
    main()