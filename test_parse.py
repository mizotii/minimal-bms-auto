"""
Unit and integration tests for parse.py

Synthetic tests write minimal BMS strings to tmp_path fixtures.
Integration tests use real chart files in assets/.
"""

import os
import pytest
from parse import _BMSParser


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_bms(tmp_path, content: str, filename='test.bms') -> str:
    """Write a BMS string to a temp file and return its path."""
    path = tmp_path / filename
    path.write_bytes(content.encode('shift_jis'))
    return str(path)


def parse(tmp_path, content: str):
    return _BMSParser(make_bms(tmp_path, content)).build()


# A complete minimal BMS that should parse successfully.
MINIMAL_BMS = """\
#PLAYER 1
#TITLE Test Chart
#ARTIST Test Artist
#GENRE Test Genre
#BPM 120
#RANK 2
#TOTAL 200
#PLAYLEVEL 5
#LNOBJ ZZ

#WAV01 kick.wav
#WAV02 snare.wav

*---------------------- MAIN DATA FIELD

#00011:01000000
"""


# ---------------------------------------------------------------------------
# Header field parsing
# ---------------------------------------------------------------------------

class TestHeaderParsing:
    def test_title(self, tmp_path):
        chart = parse(tmp_path, MINIMAL_BMS)
        assert chart.title == 'Test Chart'

    def test_artist(self, tmp_path):
        chart = parse(tmp_path, MINIMAL_BMS)
        assert chart.artist == 'Test Artist'

    def test_genre(self, tmp_path):
        chart = parse(tmp_path, MINIMAL_BMS)
        assert chart.genre == 'Test Genre'

    def test_initial_bpm(self, tmp_path):
        chart = parse(tmp_path, MINIMAL_BMS)
        assert chart.initial_bpm == pytest.approx(120.0)

    def test_rank(self, tmp_path):
        chart = parse(tmp_path, MINIMAL_BMS)
        assert chart.rank == 2

    def test_total(self, tmp_path):
        chart = parse(tmp_path, MINIMAL_BMS)
        assert chart.total == pytest.approx(200.0)

    def test_level(self, tmp_path):
        chart = parse(tmp_path, MINIMAL_BMS)
        assert chart.level == 5

    def test_ln_obj(self, tmp_path):
        chart = parse(tmp_path, MINIMAL_BMS)
        assert chart.ln_obj == 'ZZ'

    def test_wav_table_keys_are_raw_ids(self, tmp_path):
        # WAV table keys must be the raw 2-char base-36 IDs, not lowercased.
        chart = parse(tmp_path, MINIMAL_BMS)
        assert '01' in chart.wav_table
        assert '02' in chart.wav_table

    def test_wav_table_values_are_filenames(self, tmp_path):
        chart = parse(tmp_path, MINIMAL_BMS)
        assert chart.wav_table['01'] == 'kick.wav'
        assert chart.wav_table['02'] == 'snare.wav'

    def test_missing_bpm_defaults_to_120(self, tmp_path):
        bms = "#WAV01 a.wav\n\n#00011:01000000\n"
        chart = parse(tmp_path, bms)
        assert chart.initial_bpm == pytest.approx(120.0)


# ---------------------------------------------------------------------------
# Asset tables (#BPMxx, #STOPxx)
# ---------------------------------------------------------------------------

class TestAssetTables:
    def test_bpm_table_key_is_raw_id(self, tmp_path):
        bms = "#BPM 100\n#BPM01 175.5\n#WAV01 a.wav\n\n#00011:01000000\n"
        chart = parse(tmp_path, bms)
        assert '01' in chart.bpm_table

    def test_bpm_table_value(self, tmp_path):
        bms = "#BPM 100\n#BPM01 175.5\n#WAV01 a.wav\n\n#00011:01000000\n"
        chart = parse(tmp_path, bms)
        assert chart.bpm_table['01'] == pytest.approx(175.5)

    def test_stop_table_key_is_raw_id(self, tmp_path):
        bms = "#BPM 120\n#STOP01 48\n#WAV01 a.wav\n\n#00011:01000000\n"
        chart = parse(tmp_path, bms)
        assert '01' in chart.stop_table

    def test_stop_table_value(self, tmp_path):
        bms = "#BPM 120\n#STOP01 48\n#WAV01 a.wav\n\n#00011:01000000\n"
        chart = parse(tmp_path, bms)
        assert chart.stop_table['01'] == pytest.approx(48.0)


# ---------------------------------------------------------------------------
# Beat position calculation
# ---------------------------------------------------------------------------

class TestBeatPositions:
    def test_first_slot_of_measure_0_is_beat_0(self, tmp_path):
        bms = "#BPM 120\n#WAV01 a.wav\n\n#00011:01000000\n"
        chart = parse(tmp_path, bms)
        assert chart.notes[0].beat == pytest.approx(0.0)

    def test_first_slot_of_measure_1_is_beat_4(self, tmp_path):
        bms = "#BPM 120\n#WAV01 a.wav\n\n#00111:01000000\n"
        chart = parse(tmp_path, bms)
        assert chart.notes[0].beat == pytest.approx(4.0)

    def test_second_slot_of_four_is_beat_1(self, tmp_path):
        # "00 01 00 00": slot 1 of 4 → beat = 4 * (1/4) = 1.0
        bms = "#BPM 120\n#WAV01 a.wav\n\n#00011:00010000\n"
        chart = parse(tmp_path, bms)
        assert chart.notes[0].beat == pytest.approx(1.0)

    def test_slot_4_of_16_is_beat_1(self, tmp_path):
        # 16-slot measure (32 chars): slot 4 → beat = 4 * (4/16) = 1.0
        data = '00' * 4 + '01' + '00' * 11   # slot 4 of 16
        bms = f"#BPM 120\n#WAV01 a.wav\n\n#00011:{data}\n"
        chart = parse(tmp_path, bms)
        assert chart.notes[0].beat == pytest.approx(1.0)

    def test_measure_length_02_shifts_next_measure(self, tmp_path):
        # Measure 0 shortened to 0.5 (= 2 beats), measure 1 starts at beat 2.
        bms = (
            "#BPM 120\n#WAV01 a.wav\n\n"
            "#00002:0.5\n"
            "#00111:01000000\n"
        )
        chart = parse(tmp_path, bms)
        assert chart.notes[0].beat == pytest.approx(2.0)

    def test_multiple_notes_in_one_measure(self, tmp_path):
        # "01 00 02 00": slots 0 and 2 of 4 → beats 0.0 and 2.0
        bms = "#BPM 120\n#WAV01 a.wav\n#WAV02 b.wav\n\n#00011:01000200\n"
        chart = parse(tmp_path, bms)
        beats = sorted(n.beat for n in chart.notes)
        assert beats[0] == pytest.approx(0.0)
        assert beats[1] == pytest.approx(2.0)


# ---------------------------------------------------------------------------
# Beat-to-time conversion
# ---------------------------------------------------------------------------

class TestBeatToTime:
    def test_beat_0_is_time_0(self, tmp_path):
        bms = "#BPM 120\n#WAV01 a.wav\n\n#00011:01000000\n"
        chart = parse(tmp_path, bms)
        assert chart.notes[0].time == pytest.approx(0.0)

    def test_beat_4_at_120_bpm_is_2_seconds(self, tmp_path):
        # 4 beats / 120 BPM = 2.0 s
        bms = "#BPM 120\n#WAV01 a.wav\n\n#00111:01000000\n"
        chart = parse(tmp_path, bms)
        assert chart.notes[0].time == pytest.approx(2.0)

    def test_beat_4_at_60_bpm_is_4_seconds(self, tmp_path):
        bms = "#BPM 60\n#WAV01 a.wav\n\n#00111:01000000\n"
        chart = parse(tmp_path, bms)
        assert chart.notes[0].time == pytest.approx(4.0)

    def test_beat_1_at_120_bpm_is_half_second(self, tmp_path):
        bms = "#BPM 120\n#WAV01 a.wav\n\n#00011:00010000\n"
        chart = parse(tmp_path, bms)
        assert chart.notes[0].time == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# BPM change events
# ---------------------------------------------------------------------------

class TestBPMChanges:
    def test_initial_bpm_change_at_beat_0_time_0(self, tmp_path):
        bms = "#BPM 120\n#WAV01 a.wav\n\n#00011:01000000\n"
        chart = parse(tmp_path, bms)
        first = min(chart.bpm_changes, key=lambda c: c.beat)
        assert first.beat == pytest.approx(0.0)
        assert first.time == pytest.approx(0.0)
        assert first.bpm  == pytest.approx(120.0)

    def test_channel_03_hex_bpm_change(self, tmp_path):
        # 0x96 = 150.  Change at beat 1.0 (slot 1 of 4 in measure 0).
        bms = "#BPM 120\n#WAV01 a.wav\n\n#00003:00960000\n#00011:01000000\n"
        chart = parse(tmp_path, bms)
        assert any(abs(bc.bpm - 150.0) < 0.01 for bc in chart.bpm_changes)

    def test_channel_08_extended_bpm_lookup(self, tmp_path):
        bms = (
            "#BPM 120\n#BPM01 180\n#WAV01 a.wav\n\n"
            "#00008:01000000\n"
            "#00011:01000000\n"
        )
        chart = parse(tmp_path, bms)
        assert any(abs(bc.bpm - 180.0) < 0.01 for bc in chart.bpm_changes)

    def test_bpm_change_affects_subsequent_note_time(self, tmp_path):
        # BPM 120 at beat 0 → then BPM 240 at beat 0 (same beat, replaces it).
        # 0xF0 = 240.  Note at beat 8 (measure 2): 8 * (60/240) = 2.0 s.
        bms = (
            "#BPM 120\n#WAV01 a.wav\n\n"
            "#00003:F0000000\n"
            "#00211:01000000\n"
        )
        chart = parse(tmp_path, bms)
        note = chart.notes[0]
        assert note.time == pytest.approx(2.0)

    def test_bpm_change_time_is_calculated_correctly(self, tmp_path):
        # 4 beats at 120 BPM = 2.0 s, then BPM changes to 60.
        # The BPMChange event itself must have time = 2.0 s.
        bms = (
            "#BPM 120\n#WAV01 a.wav\n\n"
            "#00003:3C000000\n"   # 0x3C = 60, at beat 1.0 (slot 0 of measure 0? no...)
            # slot 0 of measure 1 = beat 4.0
            "#00103:3C000000\n"
            "#00211:01000000\n"
        )
        chart = parse(tmp_path, bms)
        change = next(bc for bc in chart.bpm_changes if abs(bc.bpm - 60.0) < 0.01)
        assert change.time == pytest.approx(2.0)

    def test_bpm_changes_sorted_by_beat(self, tmp_path):
        bms = (
            "#BPM 120\n#WAV01 a.wav\n\n"
            "#00003:96000000\n"
            "#00011:01000000\n"
        )
        chart = parse(tmp_path, bms)
        beats = [bc.beat for bc in chart.bpm_changes]
        assert beats == sorted(beats)


# ---------------------------------------------------------------------------
# Lane mapping
# ---------------------------------------------------------------------------

class TestLaneMapping:
    @pytest.mark.parametrize("channel,expected_lane", [
        ('11', 0),
        ('12', 1),
        ('13', 2),
        ('14', 3),
        ('15', 4),
        ('18', 5),
        ('19', 6),
        ('16', 7),
    ])
    def test_channel_to_lane(self, tmp_path, channel, expected_lane):
        bms = f"#BPM 120\n#WAV01 a.wav\n\n#000{channel}:01000000\n"
        chart = parse(tmp_path, bms)
        assert len(chart.notes) > 0
        assert chart.notes[0].lane == expected_lane


# ---------------------------------------------------------------------------
# Note wav_id
# ---------------------------------------------------------------------------

class TestNoteWavId:
    def test_note_wav_id_is_raw_object_id(self, tmp_path):
        # wav_id on a Note should be the raw 2-char object ID ('01'),
        # not the resolved filename.  The caller resolves via wav_table.
        bms = "#BPM 120\n#WAV01 kick.wav\n\n#00011:01000000\n"
        chart = parse(tmp_path, bms)
        assert chart.notes[0].wav_id == '01'

    def test_note_wav_id_resolvable_via_wav_table(self, tmp_path):
        bms = "#BPM 120\n#WAV01 kick.wav\n\n#00011:01000000\n"
        chart = parse(tmp_path, bms)
        wav_id = chart.notes[0].wav_id
        assert chart.wav_table.get(wav_id) == 'kick.wav'


# ---------------------------------------------------------------------------
# BGM events (channel 01)
# ---------------------------------------------------------------------------

class TestBGMEvents:
    def test_channel_01_creates_bgm_event_not_note(self, tmp_path):
        bms = "#BPM 120\n#WAV01 a.wav\n\n#00001:01000000\n"
        chart = parse(tmp_path, bms)
        assert len(chart.bgm_events) == 1
        assert len(chart.notes) == 0

    def test_bgm_event_beat(self, tmp_path):
        bms = "#BPM 120\n#WAV01 a.wav\n\n#00001:01000000\n"
        chart = parse(tmp_path, bms)
        assert chart.bgm_events[0].beat == pytest.approx(0.0)

    def test_bgm_event_time(self, tmp_path):
        # beat 0 = time 0
        bms = "#BPM 120\n#WAV01 a.wav\n\n#00001:01000000\n"
        chart = parse(tmp_path, bms)
        assert chart.bgm_events[0].time == pytest.approx(0.0)

    def test_bgm_event_wav_id_is_raw_id(self, tmp_path):
        bms = "#BPM 120\n#WAV01 a.wav\n\n#00001:01000000\n"
        chart = parse(tmp_path, bms)
        assert chart.bgm_events[0].wav_id == '01'

    def test_multiple_bgm_events_per_measure(self, tmp_path):
        bms = "#BPM 120\n#WAV01 a.wav\n#WAV02 b.wav\n\n#00001:01000200\n"
        chart = parse(tmp_path, bms)
        assert len(chart.bgm_events) == 2


# ---------------------------------------------------------------------------
# Measure lines
# ---------------------------------------------------------------------------

class TestMeasureLines:
    def test_first_measure_line_at_beat_0_time_0(self, tmp_path):
        bms = "#BPM 120\n#WAV01 a.wav\n\n#00011:01000000\n"
        chart = parse(tmp_path, bms)
        first = min(chart.measure_lines, key=lambda m: m.beat)
        assert first.beat == pytest.approx(0.0)
        assert first.time == pytest.approx(0.0)

    def test_measure_lines_spaced_4_beats_at_default_length(self, tmp_path):
        bms = "#BPM 120\n#WAV01 a.wav\n\n#00011:01000000\n#00211:01000000\n"
        chart = parse(tmp_path, bms)
        by_measure = sorted(chart.measure_lines, key=lambda m: m.measure)
        assert by_measure[0].beat == pytest.approx(0.0)
        assert by_measure[1].beat == pytest.approx(4.0)
        assert by_measure[2].beat == pytest.approx(8.0)

    def test_measure_line_times_at_120_bpm(self, tmp_path):
        # 4 beats at 120 BPM = 2.0 s per measure
        bms = "#BPM 120\n#WAV01 a.wav\n\n#00011:01000000\n#00211:01000000\n"
        chart = parse(tmp_path, bms)
        by_measure = sorted(chart.measure_lines, key=lambda m: m.measure)
        assert by_measure[1].time == pytest.approx(2.0)
        assert by_measure[2].time == pytest.approx(4.0)

    def test_measure_line_beat_shifted_by_measure_length(self, tmp_path):
        # Measure 0 is 0.5x (2 beats), so measure 1 starts at beat 2.
        bms = (
            "#BPM 120\n#WAV01 a.wav\n\n"
            "#00002:0.5\n"
            "#00111:01000000\n"
        )
        chart = parse(tmp_path, bms)
        by_measure = sorted(chart.measure_lines, key=lambda m: m.measure)
        assert by_measure[1].beat == pytest.approx(2.0)


# ---------------------------------------------------------------------------
# Long notes (LNOBJ)
# ---------------------------------------------------------------------------

class TestLongNotes:
    # Lane 0 (ch11): head at slot 0, tail (ZZ) at slot 2 of 4
    LN_BMS = (
        "#BPM 120\n#LNOBJ ZZ\n#WAV01 a.wav\n\n"
        "#00011:010000ZZ\n"
    )

    def test_ln_head_is_ln_start(self, tmp_path):
        chart = parse(tmp_path, self.LN_BMS)
        head = next(n for n in chart.notes if not n.is_ln_end)
        assert head.is_ln_start is True

    def test_ln_tail_is_ln_end(self, tmp_path):
        chart = parse(tmp_path, self.LN_BMS)
        tail = next(n for n in chart.notes if n.is_ln_end)
        assert tail.is_ln_end is True

    def test_ln_head_ln_end_time_matches_tail_time(self, tmp_path):
        chart = parse(tmp_path, self.LN_BMS)
        head = next(n for n in chart.notes if n.is_ln_start)
        tail = next(n for n in chart.notes if n.is_ln_end)
        assert head.ln_end_time == pytest.approx(tail.time)

    def test_ln_head_beat_less_than_tail_beat(self, tmp_path):
        chart = parse(tmp_path, self.LN_BMS)
        head = next(n for n in chart.notes if n.is_ln_start)
        tail = next(n for n in chart.notes if n.is_ln_end)
        assert head.beat < tail.beat

    def test_ln_pairing_is_independent_per_lane(self, tmp_path):
        bms = (
            "#BPM 120\n#LNOBJ ZZ\n#WAV01 a.wav\n#WAV02 b.wav\n\n"
            "#00011:010000ZZ\n"
            "#00012:020000ZZ\n"
        )
        chart = parse(tmp_path, bms)
        heads = [n for n in chart.notes if n.is_ln_start]
        tails = [n for n in chart.notes if n.is_ln_end]
        assert len(heads) == 2
        assert len(tails) == 2
        for h in heads:
            assert h.ln_end_time > h.time

    def test_regular_note_is_not_ln(self, tmp_path):
        bms = "#BPM 120\n#LNOBJ ZZ\n#WAV01 a.wav\n\n#00011:01000000\n"
        chart = parse(tmp_path, bms)
        note = chart.notes[0]
        assert note.is_ln_start is False
        assert note.is_ln_end is False

    def test_ln_head_count_equals_tail_count(self, tmp_path):
        chart = parse(tmp_path, self.LN_BMS)
        heads = sum(1 for n in chart.notes if n.is_ln_start)
        tails = sum(1 for n in chart.notes if n.is_ln_end)
        assert heads == tails


# ---------------------------------------------------------------------------
# Notes are sorted by beat
# ---------------------------------------------------------------------------

class TestNoteSorting:
    def test_notes_sorted_by_beat(self, tmp_path):
        bms = (
            "#BPM 120\n#WAV01 a.wav\n#WAV02 b.wav\n\n"
            "#00211:01000000\n"   # measure 2 (later) appears first in file
            "#00011:02000000\n"   # measure 0 (earlier)
        )
        chart = parse(tmp_path, bms)
        beats = [n.beat for n in chart.notes]
        assert beats == sorted(beats)

    def test_notes_from_different_lanes_interleaved_by_beat(self, tmp_path):
        # ch11 at beat 0, ch12 at beat 1 -- must come out in beat order
        bms = (
            "#BPM 120\n#WAV01 a.wav\n#WAV02 b.wav\n\n"
            "#00011:01000000\n"
            "#00012:00020000\n"
        )
        chart = parse(tmp_path, bms)
        beats = [n.beat for n in chart.notes]
        assert beats == sorted(beats)


# ---------------------------------------------------------------------------
# Multiple data lines for same measure+channel are merged
# ---------------------------------------------------------------------------

class TestMultipleDataLines:
    def test_two_data_lines_for_same_channel_merged(self, tmp_path):
        # Two lines on ch11 measure 0: first puts a note at slot 0, second at slot 2.
        bms = (
            "#BPM 120\n#WAV01 a.wav\n#WAV02 b.wav\n\n"
            "#00011:01000000\n"
            "#00011:00000200\n"
        )
        chart = parse(tmp_path, bms)
        # Both notes should be present
        assert len(chart.notes) == 2
        beats = sorted(n.beat for n in chart.notes)
        assert beats[0] == pytest.approx(0.0)
        assert beats[1] == pytest.approx(2.0)


# ---------------------------------------------------------------------------
# Integration tests -- real chart files in assets/
# ---------------------------------------------------------------------------

ASSETS_DIR = os.path.join(os.path.dirname(__file__), 'assets')
CEU_DIR    = os.path.join(ASSETS_DIR, 'ceu')


@pytest.mark.skipif(not os.path.isdir(ASSETS_DIR), reason='assets/ not present')
class TestIntegrationAltMirroBell:
    FILE = os.path.join(ASSETS_DIR, 'AltMirroBell_MX_.bme')

    @pytest.fixture(scope='class')
    def chart(self):
        return _BMSParser(self.FILE).build()

    def test_parses_without_error(self, chart):
        assert chart is not None

    def test_title(self, chart):
        assert 'AltMirrorBell' in chart.title or 'AltMirroBell' in chart.title

    def test_initial_bpm(self, chart):
        assert chart.initial_bpm == pytest.approx(156.0)

    def test_has_notes(self, chart):
        assert len(chart.notes) > 0

    def test_has_bgm_events(self, chart):
        assert len(chart.bgm_events) > 0

    def test_has_measure_lines(self, chart):
        assert len(chart.measure_lines) > 0

    def test_notes_sorted_by_beat(self, chart):
        beats = [n.beat for n in chart.notes]
        assert beats == sorted(beats)

    def test_all_notes_have_non_negative_time(self, chart):
        assert all(n.time >= 0.0 for n in chart.notes)

    def test_all_notes_have_valid_lane(self, chart):
        assert all(0 <= n.lane <= 7 for n in chart.notes)

    def test_all_notes_have_a_wav_id(self, chart):
        assert all(n.wav_id for n in chart.notes)

    def test_total_time_is_positive(self, chart):
        assert chart.total_time > 0.0

    def test_first_bpm_change_is_at_beat_0(self, chart):
        first = min(chart.bpm_changes, key=lambda c: c.beat)
        assert first.beat == pytest.approx(0.0)
        assert first.time == pytest.approx(0.0)

    def test_ln_head_count_equals_tail_count(self, chart):
        heads = sum(1 for n in chart.notes if n.is_ln_start)
        tails = sum(1 for n in chart.notes if n.is_ln_end)
        assert heads == tails

    def test_ln_heads_end_after_they_start(self, chart):
        for n in chart.notes:
            if n.is_ln_start:
                assert n.ln_end_time > n.time, f'LN at beat {n.beat} has ln_end_time <= time'

    def test_measure_lines_monotonically_increasing(self, chart):
        by_measure = sorted(chart.measure_lines, key=lambda m: m.measure)
        times = [m.time for m in by_measure]
        assert times == sorted(times)

    def test_bpm_changes_sorted_by_beat(self, chart):
        beats = [bc.beat for bc in chart.bpm_changes]
        assert beats == sorted(beats)

    def test_wav_table_populated(self, chart):
        assert len(chart.wav_table) > 0


@pytest.mark.skipif(not os.path.isdir(CEU_DIR), reason='assets/ceu/ not present')
class TestIntegrationCeuKiritan:
    FILE = os.path.join(CEU_DIR, '7keys_kiritan.bms')

    @pytest.fixture(scope='class')
    def chart(self):
        return _BMSParser(self.FILE).build()

    def test_parses_without_error(self, chart):
        assert chart is not None

    def test_title_contains_ceu(self, chart):
        assert 'ceu' in chart.title.lower()

    def test_initial_bpm(self, chart):
        assert chart.initial_bpm == pytest.approx(135.0)

    def test_note_count(self, chart):
        # Known chart; 2323 total notes including LN ends
        assert 2000 <= len(chart.notes) <= 3000

    def test_all_lanes_valid(self, chart):
        assert all(0 <= n.lane <= 7 for n in chart.notes)

    def test_no_bpm_changes_beyond_initial(self, chart):
        # This chart is constant 135 BPM
        assert len(chart.bpm_changes) == 1
        assert chart.bpm_changes[0].bpm == pytest.approx(135.0)

    def test_total_duration_reasonable(self, chart):
        # Song is ~2 min 20 s
        assert 130.0 <= chart.total_time <= 160.0

    def test_ln_obj(self, chart):
        assert chart.ln_obj == 'ZZ'

    def test_ln_pairs_balanced(self, chart):
        heads = sum(1 for n in chart.notes if n.is_ln_start)
        tails = sum(1 for n in chart.notes if n.is_ln_end)
        assert heads == tails

    def test_all_bgm_events_have_valid_time(self, chart):
        assert all(ev.time >= 0.0 for ev in chart.bgm_events)

    def test_bgm_events_sorted_by_beat(self, chart):
        beats = [ev.beat for ev in chart.bgm_events]
        assert beats == sorted(beats)
