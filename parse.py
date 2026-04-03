from bisect import bisect_right
from pprint import pp
import re
from collections import defaultdict
from chart import BGMEvent, BPMChange, Chart, Note, MeasureLine, StopEvent

# Matches header lines: #KEY value
HEADER_PATTERN = re.compile('^#([A-Za-z][A-Za-z0-9]*)[ \t]+(.+)$')
# Matches data lines: #MMMcc:data  (MMM=measure, cc=channel)
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
    
def parse_bms(filepath):
    """Parse a BMS/BME file and return a populated Chart."""
    notes = []
    bpm_changes = []
    measure_lines = []
    bgm_events = []
    stop_events = []

    title, artist, genre, initial_bpm, rank, total, level, player, wav_table, bpm_table, stop_table, ln_obj, measure_count, raw_data, measure_lengths = _read_file(filepath)

    measure_to_absolute_beat = _build_measure_beats(measure_count, measure_lengths)

    bpm_changes_raw = _extract_bpm_events(bpm_table, raw_data, measure_to_absolute_beat, measure_lengths)

    time_anchors = _build_time_anchors(bpm_changes_raw, initial_bpm)
    # for quicker search
    time_anchors_beat_only = [t[0] for t in time_anchors]
        
    for r in raw_data:
        if r[1] in {'11', '12', '13', '14', '15', '16', '18', '19'}:
            notes.extend(_create_notes(*r, measure_to_absolute_beat, measure_lengths, time_anchors, time_anchors_beat_only, wav_table, ln_obj))

    final_note = notes[len(notes) - 1]

    return Chart(
        title=title,
        artist=artist,
        genre=genre,
        initial_bpm=initial_bpm,
        rank=rank,
        total=total,
        level=level,
        player=player,
        wav_table=wav_table,
        bpm_table=bpm_table,
        stop_table=stop_table,
        notes=notes,
        bpm_changes=bpm_changes,
        measure_lines=measure_lines,
        bgm_events=bgm_events,
        stop_events=stop_events,
        ln_obj=ln_obj,
        total_beats=final_note.beat,
        total_time=final_note.time,
    )

def _decode_slots(measure, data, measure_to_absolute_beat, measure_lengths):
    """Yield (beat, slot_id) for every non-zero slot in a data string."""
    values = [data[i:i+2] for i in range(0, len(data), 2)]
    measure_start = measure_to_absolute_beat.get(measure, 0.0)
    measure_beats = measure_lengths.get(measure, 1.0) * 4

    for i, v in enumerate(values):
        if v == '00':
            continue
        
        beat = measure_start + (measure_beats * i / len(values))
        yield beat, v

def _beat_to_time(beat, time_anchors, time_anchors_beat_only):
    beat_anchor_index = bisect_right(time_anchors_beat_only, beat) - 1
    start_measure = time_anchors[beat_anchor_index]
    beat_delta = beat - start_measure[0]
    time_delta = beat_delta * (60.0 / start_measure[2])
    return start_measure[1] + time_delta
        
def _create_notes(measure, channel, data, measure_to_absolute_beat, measure_lengths, time_anchors, time_anchors_beat_only, wav_table, ln_obj):
    notes = []

    for beat, v in _decode_slots(measure, data, measure_to_absolute_beat, measure_lengths):
        time = _beat_to_time(beat, time_anchors, time_anchors_beat_only)
        lane = CHANNEL_TO_LANE.get(channel)
        wav_id = wav_table.get(v)
        is_ln_end = wav_id == ln_obj
        notes.append(
            Note(
                beat=beat,
                time=time,
                lane=lane,
                wav_id=wav_id,
                is_ln_start=False,
                is_ln_end=is_ln_end,
                ln_end_time=0.0,
            )
        )

    return notes

def _read_file(filepath):
    """Read the file once, collecting all header values and raw data lines.

    Channel 02 (measure length multipliers) is extracted immediately.
    All other data lines are returned as a flat list of (measure, channel, data) tuples
    for processing in a second pass once all headers are known.
    """
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

def _build_measure_beats(measure_count, measure_lengths):
    """Build a mapping from measure number to its absolute beat position.

    Each measure is (measure_length * 4) beats wide. Missing entries in
    measure_lengths default to 1.0 (a standard 4-beat measure).
    """
    measure_to_absolute_beat = {}
    total_beats = 0.0

    for i in range(measure_count + 1):
        measure_length = measure_lengths.get(i, 1.0)
        measure_to_absolute_beat[i] = total_beats
        total_beats += measure_length * 4

    return measure_to_absolute_beat

def parse_bpm_change_data(measure, channel, data, bpm_table, measure_to_absolute_beat, measure_lengths):
    bpm_changes_raw = {}

    for beat, v in _decode_slots(measure, data, measure_to_absolute_beat, measure_lengths):
        # todo: support for channel 09
        bpm = (
            bpm_table.get(v) if channel == '08'
            else int(v, 16) if v != '00'
            else None
        )

        if bpm is None:
            continue

        bpm_changes_raw[beat] = bpm

    return bpm_changes_raw

def _extract_bpm_events(bpm_table, raw_data, measure_to_absolute_beat, measure_lengths):
    """Extract BPM change events from raw data and map them to absolute beat positions.

    Channel 03: BPM value is hex-encoded directly in the slot (e.g. 'FE' -> 254).
    Channel 08: slot value is a key into bpm_table (e.g. '01' -> bpm_table['01']).
    Returns a dict of {beat: bpm}, sorted by beat.
    """
    bpm_changes_raw = {}

    for r in raw_data:
        if r[1] == '03' or r[1] == '08':
            bpm_changes_raw.update(parse_bpm_change_data(*r, bpm_table, measure_to_absolute_beat, measure_lengths))

    return dict(sorted(bpm_changes_raw.items()))

def _build_time_anchors(bpm_changes_raw, initial_bpm):
    """Build a list of (beat, time, bpm) anchors for beat-to-time interpolation.

    Each anchor marks the start of a constant-BPM segment. A BPM change at
    beat 0 replaces the initial anchor rather than adding a duplicate.
    Input dict must be sorted by beat (or will be sorted internally).
    """
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
    chart = parse_bms('./assets/AltMirroBell_MX_EXH.bme')
    pp(chart)
