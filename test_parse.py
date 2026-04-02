import pytest
from parse import _build_measure_beats, _extract_bpm_events, _build_time_anchors


class TestBuildMeasureBeats:
    def test_measure_zero_starts_at_beat_zero(self):
        result = _build_measure_beats(0, {})
        assert result[0] == 0.0

    def test_default_measures_are_four_beats(self):
        result = _build_measure_beats(2, {})
        assert result[0] == 0.0
        assert result[1] == 4.0
        assert result[2] == 8.0

    def test_half_length_measure(self):
        # measure 0 is 0.5 * 4 = 2 beats, so measure 1 starts at beat 2
        result = _build_measure_beats(1, {0: 0.5})
        assert result[0] == 0.0
        assert result[1] == 2.0

    def test_double_length_measure(self):
        # measure 0 is 2.0 * 4 = 8 beats, so measure 1 starts at beat 8
        result = _build_measure_beats(1, {0: 2.0})
        assert result[0] == 0.0
        assert result[1] == 8.0

    def test_mixed_measure_lengths(self):
        # measure 0: 1.0 (4 beats), measure 1: 0.75 (3 beats), measure 2 starts at beat 7
        result = _build_measure_beats(2, {1: 0.75})
        assert result[0] == 0.0
        assert result[1] == 4.0
        assert result[2] == 7.0


class TestExtractBpmEvents:
    def test_channel03_at_measure_zero_start(self):
        # single slot 'FE' -> hex 254, beat 0.0
        m2b = {0: 0.0}
        lengths = {0: 1.0}
        result = _extract_bpm_events({}, [(0, '03', 'FE')], m2b, lengths)
        assert result.get(0.0) == 254

    def test_channel03_midmeasure(self):
        # '00FE': 2 slots, slot 1 -> fraction 1/2 -> beat 0 + (1.0 * 4 * 0.5) = 2.0
        m2b = {0: 0.0}
        lengths = {0: 1.0}
        result = _extract_bpm_events({}, [(0, '03', '00FE')], m2b, lengths)
        assert result.get(2.0) == 254

    def test_channel03_at_measure_one_start(self):
        # measure 1 starts at beat 4.0, single slot 'FE' -> absolute beat 4.0
        m2b = {0: 0.0, 1: 4.0}
        lengths = {1: 1.0}
        result = _extract_bpm_events({}, [(1, '03', 'FE')], m2b, lengths)
        assert result.get(4.0) == 254

    def test_channel08_lookup(self):
        m2b = {0: 0.0}
        lengths = {0: 1.0}
        result = _extract_bpm_events({'01': 180.0}, [(0, '08', '01')], m2b, lengths)
        assert result.get(0.0) == 180.0

    def test_channel08_midmeasure(self):
        # '0001': 2 slots, slot 1 -> fraction 1/2 -> beat 0 + (1.0 * 4 * 0.5) = 2.0
        m2b = {0: 0.0}
        lengths = {0: 1.0}
        result = _extract_bpm_events({'01': 180.0}, [(0, '08', '0001')], m2b, lengths)
        assert result.get(2.0) == 180.0

    def test_channel08_at_measure_one_start(self):
        # measure 1 starts at beat 4.0, single slot '01' -> absolute beat 4.0
        m2b = {0: 0.0, 1: 4.0}
        lengths = {0: 1.0, 1: 1.0}
        result = _extract_bpm_events({'01': 180.0}, [(1, '08', '01')], m2b, lengths)
        assert result.get(4.0) == 180.0

    def test_channel08_missing_id_is_skipped(self):
        m2b = {0: 0.0}
        lengths = {0: 1.0}
        result = _extract_bpm_events({'01': 180.0}, [(0, '08', '02')], m2b, lengths)
        assert len(result) == 0

    def test_channel03_zero_slot_is_ignored(self):
        m2b = {0: 0.0}
        lengths = {0: 1.0}
        result = _extract_bpm_events({}, [(0, '03', '00')], m2b, lengths)
        assert len(result) == 0

    def test_non_bpm_channel_produces_no_output(self):
        m2b = {0: 0.0}
        lengths = {0: 1.0}
        result = _extract_bpm_events({}, [(0, '01', 'AB')], m2b, lengths)
        assert len(result) == 0


class TestBuildTimeAnchors:
    def test_no_changes_gives_single_initial_anchor(self):
        result = _build_time_anchors({}, 120.0)
        assert result == [(0.0, 0.0, 120.0)]

    def test_bpm_change_at_beat_four(self):
        # 4 beats at 120 BPM = 2.0 seconds
        result = _build_time_anchors({4.0: 180.0}, 120.0)
        assert len(result) == 2
        beat, time, bpm = result[1]
        assert beat == 4.0
        assert abs(time - 2.0) < 1e-9
        assert bpm == 180.0

    def test_bpm_change_at_beat_zero_replaces_initial(self):
        # change at beat 0 should overwrite the initial anchor, not add a second
        result = _build_time_anchors({0.0: 180.0}, 120.0)
        assert len(result) == 1
        assert result[0] == (0.0, 0.0, 180.0)

    def test_two_sequential_bpm_changes(self):
        # 4 beats at 120 BPM = 2.0s, then 4 beats at 60 BPM = 4.0s more = 6.0s total
        result = _build_time_anchors({4.0: 60.0, 8.0: 120.0}, 120.0)
        assert len(result) == 3
        assert abs(result[1][1] - 2.0) < 1e-9
        assert abs(result[2][1] - 6.0) < 1e-9

    def test_anchors_are_ordered_by_beat(self):
        # changes inserted out of order — result must still be sorted by beat
        result = _build_time_anchors({8.0: 90.0, 4.0: 60.0}, 120.0)
        beats = [a[0] for a in result]
        assert beats == sorted(beats)
