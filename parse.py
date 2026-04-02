from pprint import pp
import re
from collections import defaultdict
from chart import BGMEvent, BPMChange, Chart, Note, MeasureLine, StopEvent

HEADER_PATTERN = re.compile('^#([A-Za-z][A-Za-z0-9]*)[ \t]+(.+)$')
DATA_PATTERN = re.compile(r'^#(\d{3})([0-9A-Za-z]{2}):(.*)$')

def parse_bms(filepath):
    # for final headers that only need one pass
    title = ''
    artist = ''
    genre = ''
    initial_bpm = 120.0
    rank = 0
    total = 0.0
    level = 0
    player = 0

    wav_table = {}
    bpm_table = {}
    stop_table = {}

    ln_obj = ''

    # for calculating timing / storing data lines
    measure_count = 0

    raw_data = []
    measure_lengths = {}
    bpm_changes_raw = {} # absolute beat -> bpm until next change
    time_anchors = [] # (beat, time, bpm)
    measure_to_absolute_beat = {}

    notes = []
    bpm_changes = []
    measure_lines = []
    bgm_events = []
    stop_events = []

    # initial pass for headers and storing data
    with open(filepath, 'rb') as f:
        lines = f.readlines()
        for line in lines:
            try:
                decoded_line = line.decode('shift_jis')
            except ValueError:
                decoded_line = line.decode('latin-1')
            
            # store headers
            m = HEADER_PATTERN.search(decoded_line)
            if m:
                k = m.group(1).upper()
                v = m.group(2).strip()

                match k:
                    case 'TITLE':
                        title = v
                    case 'ARTIST':
                        artist = v
                    case 'GENRE':
                        genre = v
                    case 'BPM':
                        try:
                            initial_bpm = float(v)
                        except:
                            pass
                    case 'RANK':
                        try:
                            rank = int(v)
                        except:
                            pass
                    case 'TOTAL':
                        try:
                            total = float(v)
                        except:
                            pass
                    case 'PLAYLEVEL':
                        try:
                            level = int(v)
                        except:
                            pass
                    case 'PLAYER':
                        try:
                            player = int(v)
                        except:
                            pass
                    case 'LNOBJ':
                        ln_obj = v
                    case s if s.startswith('WAV'):
                        wav_table[k[3:]] = v
                    case s if s.startswith('BPM'):
                        try:
                            bpm_table[k[3:]] = float(v)
                        except:
                            pass
                    case s if s.startswith('STOP'):
                        try:
                            stop_table[k[4:]] = float(v)
                        except:
                            pass
                    case _:
                        pass

                continue
            
            # or store data
            m = DATA_PATTERN.search(decoded_line)
            if m:
                measure, channel, data = m.groups()
                data = data.strip()

                try:
                    measure = int(measure)
                except:
                    continue

                match channel:
                    case '02':
                        try:
                            measure_lengths[measure] = float(data)
                        except:
                            pass
                    case _:
                        raw_data.append((measure, channel, data))
                measure_count = max(measure, measure_count)

                continue

    # get the absolute beat position of the start of every measure
    total_beats = 0.0

    for i in range(measure_count + 1):
        possible_measure_length = measure_lengths.get(i)
        measure_length = possible_measure_length if possible_measure_length is not None else 1.0
        total_beats += measure_length * 4
        measure_to_absolute_beat[i] = total_beats

    # get bpm change events
    def parse_bpm_change_data(measure, channel, data):
        values = [data[i:i+2] for i in range(0, len(data), 2)]

        # todo: these cases do something very similar to one another, reorganize
        match channel:
            # todo: support stops (case '09')
            case '08':
                for i, v in enumerate(values):
                    bpm = bpm_table.get(v)
                    if bpm is not None:
                        relative_beat = i / len(values)
                        bpm_changes_raw[measure + relative_beat] = bpm

            case '03':
                for i, v in enumerate(values):
                    if v != '00':
                        bpm = int(v, 16)
                        relative_beat = i / len(values)
                        bpm_changes_raw[measure + relative_beat] = bpm

            case _:
                pass

    for r in raw_data:
        # tuple: measure, channel, data
        if r[1] == '03' or '08':
            parse_bpm_change_data(r[0], r[1], r[2])

    pp(bpm_changes_raw)

    # calculate time given beat, bpm, and previous time anchors
    time_anchors.append((0.0, 0.0, initial_bpm))
    for k, v in bpm_changes_raw.items():
        # c: beat, bpm
        previous_time_anchor = time_anchors[len(time_anchors) - 1]
        print(type(previous_time_anchor[0]))
        print(type(previous_time_anchor[1]))
        print(type(previous_time_anchor[2]))
        print(type(k))
        print(type(v))
        previous_beat, previous_time, previous_bpm, current_beat, current_bpm = previous_time_anchor[0], previous_time_anchor[1], previous_time_anchor[2], k, v
        beat_delta = current_beat - previous_beat
        current_time = (beat_delta * (60.0 / previous_bpm)) + previous_time
        if previous_beat == current_beat:
            time_anchors.pop()
        time_anchors.append((current_beat, current_time, current_bpm))

    pp(time_anchors)

"""
case '01':
    bgm_events.append(
        BGMEvent(measure_to_absolute_beat[r[0]], 0.0, 0)
    )
"""

if __name__ == '__main__':
    parse_bms('./AltMirroBell_MX_.bme')
