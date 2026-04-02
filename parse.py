from pprint import pp
import re
from collections import defaultdict
from chart import BGMEvent, BPMChange, Chart, Note, MeasureLine, StopEvent

HEADER_PATTERN = re.compile('^#([A-Za-z][A-Za-z0-9]*)[ \t]+(.+)$')
DATA_PATTERN = re.compile(r'^#(\d{3})([0-9A-Za-z]{2}):(.*)$')
    
def parse_bms(filepath):
    notes = []
    bpm_changes = []
    measure_lines = []
    bgm_events = []
    stop_events = []

    title, artist, genre, initial_bpm, rank, total, level, player, wav_table, bpm_table, stop_table, ln_obj, measure_count, raw_data, measure_lengths = initial_pass(filepath)

    measure_to_absolute_beat = calculate_beats(measure_count, measure_lengths)

    bpm_changes_raw = map_beats_to_bpm(bpm_table, raw_data, measure_to_absolute_beat, measure_lengths)

    time_anchors = calculate_time_anchors(bpm_changes_raw, initial_bpm)

    pp(time_anchors)

def initial_pass(filepath):
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

    measure_count = 0
    raw_data = []
    measure_lengths = {}

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

    return title, artist, genre, initial_bpm, rank, total, level, player, wav_table, bpm_table, stop_table, ln_obj, measure_count, raw_data, measure_lengths

def calculate_beats(measure_count, measure_lengths):
    measure_to_absolute_beat = {}
    total_beats = 0.0

    for i in range(measure_count + 1):
        possible_measure_length = measure_lengths.get(i)
        measure_length = possible_measure_length if possible_measure_length is not None else 1.0
        measure_to_absolute_beat[i] = total_beats
        total_beats += measure_length * 4

    return measure_to_absolute_beat

def map_beats_to_bpm(bpm_table, raw_data, measure_to_absolute_beat, measure_lengths):
    bpm_changes_raw = {}

    def parse_bpm_change_data(measure, channel, data):
        values = [data[i:i+2] for i in range(0, len(data), 2)]

        for i, v in enumerate(values):
            # todo: support for channel 09
            bpm = (
                bpm_table.get(v) if channel == '08'
                else int(v, 16) if v != '00'
                else None
            )

            if bpm is None:
                continue
            
            try:
                relative_measure = i / len(values)
                beat = measure_to_absolute_beat[measure] + ((measure_lengths[measure] * 4) * relative_measure)
            except:
                continue

            bpm_changes_raw[beat] = bpm

    for r in raw_data:
        if r[1] == '03' or r[1] ==  '08':
            parse_bpm_change_data(*r)

    return dict(sorted(bpm_changes_raw.items()))

def calculate_time_anchors(bpm_changes_raw, initial_bpm):
    time_anchors = [(0.0, 0.0, initial_bpm)]

    for k, v in sorted(bpm_changes_raw.items()):
        # c: beat, bpm
        previous_time_anchor = time_anchors[len(time_anchors) - 1]
        previous_beat, previous_time, previous_bpm, current_beat, current_bpm = previous_time_anchor[0], previous_time_anchor[1], previous_time_anchor[2], k, v
        beat_delta = current_beat - previous_beat
        current_time = (beat_delta * (60.0 / previous_bpm)) + previous_time
        if previous_beat == current_beat:
            time_anchors.pop()
        time_anchors.append((current_beat, current_time, current_bpm))

    return time_anchors

if __name__ == '__main__':
    parse_bms('./AltMirroBell_MX_.bme')
