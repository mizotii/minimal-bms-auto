"""Integration tests for parse_bms against the real 7keys_kiritan chart.

Ground-truth values were captured from a known-good parse run:
  total notes : 2323   (includes both LN head and LN tail notes)
  ln_starts   : 262
  ln_ends     : 262
  initial_bpm : 135.0
  total_beats : 308.0
  total_time  : ~136.89 s  (308 beats * 60/135)
  measure_lines : 78
  ln_obj      : 'ZZ'

Note: bgm_event count is intentionally not tested here because gap-4
(duplicate data-line deduplication) is deferred, so the raw count
differs from the fully-authored reference.
"""
import pytest
from pathlib import Path
from parse import parse_bms

KIRITAN = Path(__file__).parent / 'assets' / 'ceu' / '7keys_kiritan.bms'


@pytest.fixture(scope='module')
def kiritan():
    return parse_bms(str(KIRITAN))


class TestHeaders:
    def test_initial_bpm(self, kiritan):
        assert kiritan.initial_bpm == 135.0

    def test_title_is_nonempty(self, kiritan):
        assert kiritan.title != ''

    def test_ln_obj(self, kiritan):
        assert kiritan.ln_obj == 'ZZ'

    def test_wav_table_is_nonempty(self, kiritan):
        assert len(kiritan.wav_table) > 0


class TestNoteCounts:
    def test_total_note_count(self, kiritan):
        assert len(kiritan.notes) == 2323

    def test_ln_start_count(self, kiritan):
        assert sum(1 for n in kiritan.notes if n.is_ln_start) == 262

    def test_ln_end_count(self, kiritan):
        assert sum(1 for n in kiritan.notes if n.is_ln_end) == 262

    def test_ln_starts_equal_ln_ends(self, kiritan):
        starts = sum(1 for n in kiritan.notes if n.is_ln_start)
        ends = sum(1 for n in kiritan.notes if n.is_ln_end)
        assert starts == ends

    def test_bgm_events_present(self, kiritan):
        assert len(kiritan.bgm_events) > 0

    def test_measure_line_count(self, kiritan):
        assert len(kiritan.measure_lines) == 78


class TestSorting:
    def test_notes_sorted_by_beat(self, kiritan):
        beats = [n.beat for n in kiritan.notes]
        assert beats == sorted(beats)

    def test_bgm_events_sorted_by_beat(self, kiritan):
        beats = [e.beat for e in kiritan.bgm_events]
        assert beats == sorted(beats)

    def test_measure_lines_sorted_by_beat(self, kiritan):
        beats = [m.beat for m in kiritan.measure_lines]
        assert beats == sorted(beats)

    def test_bpm_changes_sorted_by_beat(self, kiritan):
        beats = [b.beat for b in kiritan.bpm_changes]
        assert beats == sorted(beats)


class TestLnIntegrity:
    def test_ln_start_end_time_is_after_head_time(self, kiritan):
        for note in kiritan.notes:
            if note.is_ln_start:
                assert note.ln_end_time > note.time, (
                    f"LN at beat={note.beat:.3f}: ln_end_time={note.ln_end_time} "
                    f"not after head time={note.time}"
                )

    def test_no_note_is_both_ln_start_and_ln_end(self, kiritan):
        for note in kiritan.notes:
            assert not (note.is_ln_start and note.is_ln_end)

    def test_non_ln_start_notes_have_zero_ln_end_time(self, kiritan):
        for note in kiritan.notes:
            if not note.is_ln_start:
                assert note.ln_end_time == 0.0

    def test_all_note_lanes_are_valid(self, kiritan):
        for note in kiritan.notes:
            assert 0 <= note.lane <= 7, f"Invalid lane {note.lane} at beat {note.beat}"


class TestTiming:
    def test_total_beats(self, kiritan):
        assert kiritan.total_beats == 308.0

    def test_total_time_approximately_137s(self, kiritan):
        assert 134.0 < kiritan.total_time < 140.0

    def test_total_time_matches_beat_duration_at_135_bpm(self, kiritan):
        expected = 308.0 * (60.0 / 135.0)
        assert abs(kiritan.total_time - expected) < 0.001

    def test_measure_zero_starts_at_beat_zero(self, kiritan):
        m0 = next(m for m in kiritan.measure_lines if m.measure == 0)
        assert m0.beat == 0.0

    def test_measure_zero_is_at_time_zero(self, kiritan):
        m0 = next(m for m in kiritan.measure_lines if m.measure == 0)
        assert abs(m0.time) < 1e-9

    def test_all_note_times_are_nonnegative(self, kiritan):
        for note in kiritan.notes:
            assert note.time >= 0.0

    def test_all_bgm_event_times_are_nonnegative(self, kiritan):
        for event in kiritan.bgm_events:
            assert event.time >= 0.0
