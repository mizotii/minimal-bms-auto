from bisect import bisect_right
from pygame import mixer
from typing import Dict
from chart import Chart

class Mixer:
    def __init__(self, chart: Chart):
        self.quit()
        self.init()

        self.parent_dir = chart.filepath.parent.absolute()
        self.sound_table: Dict[str, mixer.Sound] = {}

        self.wav_table = chart.wav_table
        self.sound_events = chart.sound_events
        self.sound_events_time_only = [e.time for e in self.sound_events]

        self.current_time = -2.0

        self._next_sound_idx = 0
        
        self.load_sounds()
        _play_silent_sound()

    def init(self):
        mixer.init(channels=128, buffer=2048)

    def quit(self):
        mixer.quit()

    def load_sounds(self):
        for k, sound in self.wav_table.items():
            path = self.parent_dir / sound
            if path.exists():
                self.sound_table[k] = mixer.Sound(str(path))

    def seek(self, time):
        self._next_sound_idx = bisect_right(self.sound_events_time_only, time) - 1

    def update(self, time):
        while self._next_sound_idx < len(self.sound_events) and self.sound_events[self._next_sound_idx].time <= time:
            wav_id = self.sound_events[self._next_sound_idx].wav_id
            if wav_id in self.sound_table:
                self.sound_table[wav_id].play()
            self._next_sound_idx += 1

def _play_silent_sound():
    mixer.Sound(buffer=bytearray(4)).play()