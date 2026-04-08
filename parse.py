from chart import BGMEvent, BPMChange, Chart, Note, MeasureLine, StopEvent
from bisect import bisect_right
from parse_helpers import _decode_line
import re
from typing import List

HEADER_PATTERN = re.compile('^#([A-Za-z][A-Za-z0-9]*)[ \t]+(.+)$')
DATA_PATTERN = re.compile(r'^#(\d{3})([0-9A-Za-z]{2}):(.*)$')
CHANNEL_TO_LANE = {
    '11': 0,
    '12': 1,
    '13': 2,
    '14': 3,
    '15': 4,
    '18': 5,
    '19': 6,
    '16': 7,
}

class _BMSParser:
    def __init__(self, filepath) -> None:
        self.filepath = filepath

        # headers
        self.title = ''
        self.artist = ''
        self.genre = ''
        self.initial_bpm = 120.0
        self.rank = 0
        self.total = 0.0
        self.level = 0
        self.player = 0
        self.ln_obj = ''

        # events
        self.notes: List[Note] = []
        self.bpm_changes: List[BPMChange] = []
        self.measure_lines: List[MeasureLine] = []
        self.bgm_events: List[BGMEvent] = []
        self.stop_events: List[StopEvent] = []

        # tables
        self.wav_table = {}
        self.bpm_table = {}
        self.stop_table = {}

        # raw data
        self.measure_lengths = {}
        self.raw_data = []
        self.measure_count = 0

        self.measure_starts = {}
        self.timing_changes_raw = []
        self.timing_changes = {}

        self.bpm_changes_beat_only = []

        self.total_beats = 0.0
        self.total_time = 0.0

    def build(self):
        self._read_file()
        self._calc_measure_starts()
        self._extract_timing_changes()
        self._build_bpm_changes()
        self._build_events()
        self._resolve_lns()
        self._calc_final_events()

        return Chart(
            title=self.title,
            artist=self.artist,
            genre=self.genre,
            initial_bpm=self.initial_bpm,
            rank=self.rank,
            total=self.total,
            level=self.level,
            player=self.player,
            wav_table=self.wav_table,
            bpm_table=self.bpm_table,
            stop_table=self.stop_table,
            notes=self.notes,
            bpm_changes=self.bpm_changes,
            measure_lines=self.measure_lines,
            bgm_events=self.bgm_events,
            stop_events=self.stop_events,
            ln_obj=self.ln_obj,
            total_beats=self.total_beats,
            total_time=self.total_time,
        )

    def _read_file(self):
        with open(self.filepath, 'rb') as f:
            lines = f.readlines()
            for line in lines:
                decoded_line = _decode_line(line)

                match = HEADER_PATTERN.search(decoded_line)
                if match:
                    self._fill_header(match)
                    continue

                match = DATA_PATTERN.search(decoded_line)
                if match:
                    self._fill_data(match)

    def _calc_measure_starts(self):
        total_beats = 0.0

        for i in range(self.measure_count + 1):
            measure_length = self.measure_lengths.get(i, 1.0)
            self.measure_starts[i] = total_beats
            total_beats += measure_length * 4

    def _extract_timing_changes(self):
        for tcr in self.timing_changes_raw:
            measure, channel, data = tcr
            for beat, v in self._decode_slots(measure, data):
                match channel:
                    case '03':
                        bpm = int(v, 16)
                    case '08':
                        bpm = self.bpm_table.get(v)
                    # todo: stop events
                    case '09':
                        bpm = self.stop_table.get(v)
                        continue
                    case _:
                        continue

                self.timing_changes[(beat, channel, v)] = bpm
        
        self.timing_changes = dict(sorted(self.timing_changes.items()))

    def _build_bpm_changes(self):
        # only read in initial bpm AFTER first pass
        self.bpm_changes.append(
            BPMChange(
                0.0,
                0.0,
                self.initial_bpm,
            )
        )

        for k, bpm in self.timing_changes.items():
            beat, channel, v = k

            if channel in ('03', '08'):
                prev_bpm_change = self.bpm_changes[-1]
                prev_beat, prev_time, prev_bpm = prev_bpm_change.beat, prev_bpm_change.time, prev_bpm_change.bpm

                beat_delta = beat - prev_beat
                time = (beat_delta * (60.0 / prev_bpm)) + prev_time

                if prev_beat == beat:
                    self.bpm_changes.pop()

            # todo: have stop events affect time in each change
            elif channel == '09':
                self.stop_events.append(
                    StopEvent(
                        beat,
                        self._beat_to_time(beat),
                        self._calculate_stop_duration(v, bpm)
                    )
                )
                continue

            else:
                continue
            
            self.bpm_changes.append(
                BPMChange(
                    beat,
                    time,
                    bpm,
                )
            )

        self.bpm_changes.sort()
        self.bpm_changes_beat_only = [c.beat for c in self.bpm_changes]

    def _build_events(self):
        for r in self.raw_data:
            measure, channel, data = r
            match channel:
                case '01': # BGM events
                    self._build_bgm_events(measure, data)
                case c if c in CHANNEL_TO_LANE: # notes
                    self._build_notes(measure, channel, data)

        self._build_measure_lines()

        self.bgm_events.sort()

    def _fill_header(self, match):
        k = match.group(1).upper()
        v = match.group(2).strip()

        match k:
            case 'TITLE':
                self.title = v
            case 'ARTIST':
                self.artist = v
            case 'GENRE':
                self.genre = v
            case 'BPM':
                try:
                    self.initial_bpm = float(v)
                except ValueError:
                    pass
            case 'RANK':
                try:
                    self.rank = int(v)
                except ValueError:
                    pass
            case 'TOTAL':
                try:
                    self.total = float(v)
                except ValueError:
                    pass
            case 'PLAYLEVEL':
                try:
                    self.level = int(v)
                except ValueError:
                    pass
            case 'PLAYER':
                try:
                    self.player = int(v)
                except ValueError:
                    pass
            case 'LNOBJ':
                self.ln_obj = v
            case s if s.startswith('WAV'):
                self.wav_table[k[3:]] = v
            case s if s.startswith('BPM'):
                try:
                    self.bpm_table[k[3:]] = float(v)
                except ValueError:
                    pass
            case s if s.startswith('STOP'):
                try:
                    self.stop_table[k[4:]] = float(v)
                except ValueError:
                    pass
            case _:
                pass

    def _fill_data(self, match):
        measure, channel, data = match.groups()
        data = data.strip()

        try:
            measure = int(measure)
        except ValueError:
            return

        match channel:
            case '02':
                try:
                    self.measure_lengths[measure] = float(data)
                except ValueError:
                    pass
            case '03' | '08' | '09':
                self.timing_changes_raw.append((measure, channel, data))
            case _:
                self.raw_data.append((measure, channel, data))
        self.measure_count = max(measure, self.measure_count)

    def _decode_slots(self, measure, data):
        values = [data[i:i+2] for i in range(0, len(data), 2)]
        measure_start, measure_beats = self._get_measure_start_and_beats(measure)

        for i, v in enumerate(values):
            if v == '00':
                continue

            beat = measure_start + (measure_beats * i / len(values))
            yield beat, v

    def _beat_to_time(self, beat):
        floor_bpm_change_idx = bisect_right(self.bpm_changes_beat_only, beat) - 1
        floor_bpm_change = self.bpm_changes[floor_bpm_change_idx]
        floor_beat, floor_time, floor_bpm = floor_bpm_change.beat, floor_bpm_change.time, floor_bpm_change.bpm
        beat_delta = beat - floor_beat
        time_delta = beat_delta * (60.0 / floor_bpm)
        return floor_time + time_delta
    
    def _calculate_stop_duration(self, v, bpm):
        return (self.stop_table.get(v) * 5.0) / (bpm * 4.0)

    def _build_bgm_events(self, measure, data):
        for beat, v in self._decode_slots(measure, data):
            self.bgm_events.append(
                BGMEvent(
                    beat=beat,
                    time=self._beat_to_time(beat),
                    wav_id=v,
                )
            )

    def _build_notes(self, measure, channel, data):
        for beat, v in self._decode_slots(measure, data):
            self.notes.append(
                Note(
                    beat=beat,
                    time=self._beat_to_time(beat),
                    lane=CHANNEL_TO_LANE.get(channel),
                    wav_id=v,
                    is_ln_start=False,
                    is_ln_end=(v == self.ln_obj),
                    ln_end_time=0.0,
                )
            )
    
    def _build_measure_lines(self):
        self.measure_lines = [
            MeasureLine(
                beat=beat,
                time=self._beat_to_time(beat),
                measure=measure
            )
            for measure, beat in self.measure_starts.items()
        ]

        self.measure_lines.sort()
    
    def _resolve_lns(self):
        if not self.notes:
            return
        
        self.notes.sort()
        notes_indexed_by_lane = [None] * 8

        for note in self.notes:
            if note.is_ln_end:
                prev_note = notes_indexed_by_lane[note.lane]
                if prev_note:
                    prev_note.is_ln_start = True
                    prev_note.ln_end_time = note.time

            else:
                notes_indexed_by_lane[note.lane] = note

    def _calc_final_events(self):
        last_note_beat = max((n.beat for n in self.notes), default=0.0)
        last_measure_beat = sum(self._get_measure_start_and_beats(self.measure_count))
        self.total_beats = max(last_note_beat, last_measure_beat)
        self.total_time = self._beat_to_time(self.total_beats)

    def _get_measure_start_and_beats(self, measure):
        return self.measure_starts.get(measure, 0.0), self.measure_lengths.get(measure, 1.0) * 4.0

if __name__ == '__main__':
    from pprint import pp
    chart = _BMSParser('assets\AltMirroBell_MX_.bme').build()
    pp(chart)