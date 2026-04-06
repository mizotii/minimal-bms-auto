import pytest
from parse import _build_measure_beats, _extract_bpm_events, _build_time_anchors, _decode_slots, _beat_to_time, _create_notes


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


class TestDecodeSlots:
    def test_single_slot_yields_one_event(self):
        result = list(_decode_slots(0, 'AB', {0: 0.0}, {}))
        assert result == [(0.0, 'AB')]

    def test_zero_slot_is_skipped(self):
        # '00AB': slot 0 empty, slot 1 at fraction 1/2 -> beat 2.0
        result = list(_decode_slots(0, '00AB', {0: 0.0}, {}))
        assert result == [(2.0, 'AB')]

    def test_all_zero_slots_yields_nothing(self):
        result = list(_decode_slots(0, '0000', {0: 0.0}, {}))
        assert result == []

    def test_multiple_nonempty_slots(self):
        # '000000AB' = 4 slots; last slot at fraction 3/4 -> beat 3.0
        result = list(_decode_slots(0, '000000AB', {0: 0.0}, {}))
        assert len(result) == 1
        beat, v = result[0]
        assert abs(beat - 3.0) < 1e-9
        assert v == 'AB'

    def test_two_nonempty_slots_both_emitted(self):
        # 'ABCD' = ['AB', 'CD']; beats 0.0 and 2.0
        result = list(_decode_slots(0, 'ABCD', {0: 0.0}, {}))
        assert len(result) == 2
        assert result[0] == (0.0, 'AB')
        assert abs(result[1][0] - 2.0) < 1e-9

    def test_measure_start_offset_is_applied(self):
        # measure 2 starts at beat 8; single slot -> absolute beat 8.0
        m2b = {0: 0.0, 1: 4.0, 2: 8.0}
        result = list(_decode_slots(2, 'AB', m2b, {}))
        assert result == [(8.0, 'AB')]

    def test_half_length_measure_compresses_beat_positions(self):
        # measure 0: length 0.5 -> 2 beats; '00AB' slot 1 at fraction 1/2 -> beat 1.0
        result = list(_decode_slots(0, '00AB', {0: 0.0}, {0: 0.5}))
        assert len(result) == 1
        beat, _ = result[0]
        assert abs(beat - 1.0) < 1e-9


class TestBeatToTime:
    _anchors = [(0.0, 0.0, 120.0)]
    _beats = [0.0]

    def test_beat_zero_is_time_zero(self):
        assert _beat_to_time(0.0, self._anchors, self._beats) == 0.0

    def test_four_beats_at_120_bpm_is_two_seconds(self):
        assert abs(_beat_to_time(4.0, self._anchors, self._beats) - 2.0) < 1e-9

    def test_fractional_beat_interpolates(self):
        # 2 beats at 120 BPM = 1.0 second
        assert abs(_beat_to_time(2.0, self._anchors, self._beats) - 1.0) < 1e-9

    def test_uses_correct_segment_after_bpm_change(self):
        # 4 beats at 120 BPM = 2.0s; then 2 more beats at 60 BPM = 2.0s -> total 4.0s
        anchors = [(0.0, 0.0, 120.0), (4.0, 2.0, 60.0)]
        beats = [0.0, 4.0]
        assert abs(_beat_to_time(6.0, anchors, beats) - 4.0) < 1e-9

    def test_beat_at_exact_anchor_returns_anchor_time(self):
        anchors = [(0.0, 0.0, 120.0), (4.0, 2.0, 60.0)]
        beats = [0.0, 4.0]
        assert abs(_beat_to_time(4.0, anchors, beats) - 2.0) < 1e-9


class TestCreateNotes:
    _m2b = {0: 0.0}
    _lengths = {}  # defaults to 1.0 -> 4 beats per measure
    _anchors = [(0.0, 0.0, 120.0)]
    _beats = [0.0]
    _wav = {'AB': 'kick.wav', 'ZZ': 'snare.wav'}
    _ln_obj = 'ZZ'

    def test_zero_slot_produces_no_notes(self):
        notes = _create_notes(0, '11', '00AB', self._m2b, self._lengths, self._anchors, self._beats, self._wav, self._ln_obj)
        assert len(notes) == 1  # '00' skipped, 'AB' kept

    def test_channel_11_maps_to_lane_0(self):
        notes = _create_notes(0, '11', 'AB', self._m2b, self._lengths, self._anchors, self._beats, self._wav, self._ln_obj)
        assert notes[0].lane == 0

    def test_channel_16_maps_to_lane_7(self):
        notes = _create_notes(0, '16', 'AB', self._m2b, self._lengths, self._anchors, self._beats, self._wav, self._ln_obj)
        assert notes[0].lane == 7

    def test_channel_18_maps_to_lane_5(self):
        notes = _create_notes(0, '18', 'AB', self._m2b, self._lengths, self._anchors, self._beats, self._wav, self._ln_obj)
        assert notes[0].lane == 5

    def test_ln_obj_slot_sets_is_ln_end(self):
        notes = _create_notes(0, '11', 'ZZ', self._m2b, self._lengths, self._anchors, self._beats, self._wav, self._ln_obj)
        assert notes[0].is_ln_end is True
        assert notes[0].is_ln_start is False

    def test_non_ln_obj_slot_is_not_ln_end(self):
        notes = _create_notes(0, '11', 'AB', self._m2b, self._lengths, self._anchors, self._beats, self._wav, self._ln_obj)
        assert notes[0].is_ln_end is False

    def test_wav_id_resolved_from_table(self):
        notes = _create_notes(0, '11', 'AB', self._m2b, self._lengths, self._anchors, self._beats, self._wav, self._ln_obj)
        assert notes[0].wav_id == 'kick.wav'

    def test_new_note_is_not_ln_start_and_has_zero_ln_end_time(self):
        notes = _create_notes(0, '11', 'AB', self._m2b, self._lengths, self._anchors, self._beats, self._wav, self._ln_obj)
        assert notes[0].is_ln_start is False
        assert notes[0].ln_end_time == 0.0

    def test_empty_ln_obj_never_triggers_ln_end(self):
        notes = _create_notes(0, '11', 'AB', self._m2b, self._lengths, self._anchors, self._beats, self._wav, '')
        assert notes[0].is_ln_end is False
