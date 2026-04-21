"""
Unit and integration tests for play.py

Tests are written against intended behavior. Failures indicate bugs in Player.
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, call
from chart import Chart, Note, BPMChange, MeasureLine, BGMEvent, StopEvent
from render import RenderConfig
from play import Player


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_note(time, lane=0, beat=0.0, wav_id='01',
              is_ln_start=False, is_ln_end=False, ln_end_time=0.0):
    return Note(beat=beat, time=time, lane=lane, wav_id=wav_id,
                is_ln_start=is_ln_start, is_ln_end=is_ln_end,
                ln_end_time=ln_end_time)


def make_bpm_change(time, bpm, beat=0.0):
    return BPMChange(beat=beat, time=time, bpm=bpm)


def make_measure_line(time, measure=0, beat=0.0):
    return MeasureLine(beat=beat, time=time, measure=measure)


def make_chart(notes=None, bpm_changes=None, measure_lines=None,
               bgm_events=None, initial_bpm=120.0, total_time=60.0):
    return Chart(
        filepath=Path('.'),
        title='Test', subtitle='', artist='', subartist='', genre='',
        initial_bpm=initial_bpm,
        rank=2, total=200.0, level=5, player=1,
        wav_table={}, bpm_table={}, stop_table={},
        sound_events=[],
        notes=sorted(notes or []),
        bpm_changes=sorted(bpm_changes or [make_bpm_change(0.0, initial_bpm)]),
        measure_lines=sorted(measure_lines or []),
        bgm_events=bgm_events or [],
        stop_events=[],
        ln_obj='ZZ',
        total_beats=0.0,
        total_time=total_time,
    )


def make_config(**overrides):
    defaults = dict(
        window_width=800,
        window_height=600,
        fps=60.0,
        scroll_speed=400.0,
        judgement_y_ratio=0.8,
        lane_widths=(40,) * 8,
        note_height=10,
        background=(0, 0, 0),
        lane=(30, 30, 30),
        border=(80, 80, 80),
        judgement_line=(255, 255, 0),
        measure_line=(100, 100, 100),
        hud_text=(255, 255, 255),
        notes=((255, 255, 255),) * 8,
        ln_bodies=((128, 128, 255),) * 8,
    )
    defaults.update(overrides)
    return RenderConfig(**defaults)


def make_player(chart=None, config=None, audio=None):
    chart  = chart  or make_chart()
    config = config or make_config()
    mock_renderer_cls = MagicMock(return_value=MagicMock())
    player = Player(chart, mock_renderer_cls, config, audio=audio)
    return player


# ---------------------------------------------------------------------------
# Transport controls
# ---------------------------------------------------------------------------

class TestTransport:
    def test_initial_is_not_playing(self):
        p = make_player()
        assert p.is_playing is False

    def test_start_sets_playing(self):
        p = make_player()
        p.start()
        assert p.is_playing is True

    def test_pause_clears_playing(self):
        p = make_player()
        p.start()
        p.pause()
        assert p.is_playing is False

    def test_seek_updates_current_time(self):
        p = make_player()
        p.seek(10.0)
        assert p.current_time == pytest.approx(10.0)

    def test_seek_calls_audio_seek(self):
        audio = MagicMock()
        p = make_player(audio=audio)
        p.seek(5.0)
        audio.seek.assert_called_once_with(5.0)

    def test_seek_without_audio_does_not_crash(self):
        p = make_player(audio=None)
        p.seek(5.0)  # should not raise


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------

class TestUpdate:
    def test_update_advances_time_when_playing(self):
        p = make_player()
        p.start()
        t_before = p.current_time
        p.update(0.5)
        assert p.current_time == pytest.approx(t_before + 0.5)

    def test_update_does_not_advance_time_when_paused(self):
        p = make_player()
        t_before = p.current_time
        p.update(0.5)
        assert p.current_time == pytest.approx(t_before)

    def test_update_calls_audio_update_when_playing(self):
        audio = MagicMock()
        p = make_player(audio=audio)
        p.start()
        p.update(0.1)
        audio.update.assert_called_once()

    def test_update_does_not_call_audio_when_paused(self):
        audio = MagicMock()
        p = make_player(audio=audio)
        p.update(0.1)
        audio.update.assert_not_called()


# ---------------------------------------------------------------------------
# current_bpm
# ---------------------------------------------------------------------------

class TestCurrentBpm:
    def test_returns_initial_bpm_before_any_changes(self):
        chart = make_chart(bpm_changes=[make_bpm_change(0.0, 120.0)])
        p = make_player(chart=chart)
        p.seek(0.0)
        assert p.current_bpm == pytest.approx(120.0)

    def test_returns_new_bpm_after_change(self):
        chart = make_chart(bpm_changes=[
            make_bpm_change(0.0, 120.0),
            make_bpm_change(4.0, 180.0),
        ])
        p = make_player(chart=chart)
        p.seek(5.0)
        assert p.current_bpm == pytest.approx(180.0)

    def test_returns_bpm_active_at_exact_change_time(self):
        chart = make_chart(bpm_changes=[
            make_bpm_change(0.0, 120.0),
            make_bpm_change(4.0, 180.0),
        ])
        p = make_player(chart=chart)
        p.seek(4.0)
        assert p.current_bpm == pytest.approx(180.0)

    def test_returns_first_bpm_before_first_change(self):
        chart = make_chart(bpm_changes=[
            make_bpm_change(0.0, 120.0),
            make_bpm_change(4.0, 180.0),
        ])
        p = make_player(chart=chart)
        p.seek(2.0)
        assert p.current_bpm == pytest.approx(120.0)


# ---------------------------------------------------------------------------
# lookahead / lookbehind
# ---------------------------------------------------------------------------

class TestVisibilityWindow:
    def test_lookahead_equals_time_above_judgement_line(self):
        # judgement_y = 0.8 * 600 = 480px; above = 480px; at 400px/s = 1.2s
        config = make_config(window_height=600, judgement_y_ratio=0.8, scroll_speed=400.0)
        p = make_player(config=config)
        assert p.lookahead == pytest.approx(480.0 / 400.0)

    def test_lookbehind_equals_time_below_judgement_line(self):
        # below judgement = 600 - 480 = 120px; at 400px/s = 0.3s
        config = make_config(window_height=600, judgement_y_ratio=0.8, scroll_speed=400.0)
        p = make_player(config=config)
        assert p.lookbehind == pytest.approx(120.0 / 400.0)

    def test_lookahead_plus_lookbehind_equals_pixel_visibility(self):
        config = make_config(window_height=600, judgement_y_ratio=0.8, scroll_speed=400.0)
        p = make_player(config=config)
        assert p.lookahead + p.lookbehind == pytest.approx(p.pixel_visibility)


# ---------------------------------------------------------------------------
# time_to_y
# ---------------------------------------------------------------------------

class TestTimeToY:
    def test_event_at_current_time_lands_on_judgement_line(self):
        config = make_config(window_height=600, judgement_y_ratio=0.8, scroll_speed=400.0)
        p = make_player(config=config)
        p.seek(5.0)
        assert p.time_to_y(5.0) == pytest.approx(480.0)

    def test_future_event_is_above_judgement_line(self):
        config = make_config(window_height=600, judgement_y_ratio=0.8, scroll_speed=400.0)
        p = make_player(config=config)
        p.seek(0.0)
        # 1 second ahead at 400 px/s = 400px above judgement_y (480)
        assert p.time_to_y(1.0) == pytest.approx(480.0 - 400.0)

    def test_past_event_is_below_judgement_line(self):
        config = make_config(window_height=600, judgement_y_ratio=0.8, scroll_speed=400.0)
        p = make_player(config=config)
        p.seek(1.0)
        # 1 second in the past at 400 px/s = 400px below judgement_y (480)
        assert p.time_to_y(0.0) == pytest.approx(480.0 + 400.0)

    def test_scroll_speed_scales_distance(self):
        config_slow = make_config(scroll_speed=200.0, judgement_y_ratio=0.5, window_height=600)
        config_fast = make_config(scroll_speed=800.0, judgement_y_ratio=0.5, window_height=600)
        p_slow = make_player(config=config_slow)
        p_fast = make_player(config=config_fast)
        p_slow.seek(0.0)
        p_fast.seek(0.0)
        # Same 1-second-ahead note, fast should be twice as far from judgement_y
        dy_slow = p_slow.config.judgement_y - p_slow.time_to_y(1.0)
        dy_fast = p_fast.config.judgement_y - p_fast.time_to_y(1.0)
        assert dy_fast == pytest.approx(dy_slow * 4)


# ---------------------------------------------------------------------------
# get_visible_notes
# ---------------------------------------------------------------------------

class TestGetVisibleNotes:
    def test_note_within_window_is_included(self):
        note = make_note(time=0.0)
        chart = make_chart(notes=[note])
        p = make_player(chart=chart)
        p.seek(0.0)
        assert note in p.get_visible_notes()

    def test_note_far_in_future_is_excluded(self):
        note = make_note(time=100.0)
        chart = make_chart(notes=[note])
        p = make_player(chart=chart)
        p.seek(0.0)
        assert note not in p.get_visible_notes()

    def test_note_far_in_past_is_excluded(self):
        note = make_note(time=0.0)
        chart = make_chart(notes=[note])
        p = make_player(chart=chart)
        p.seek(100.0)
        assert note not in p.get_visible_notes()

    def test_ln_start_with_tail_still_visible_is_included(self):
        # Head passed lookbehind, but tail is still on screen
        config = make_config(window_height=600, judgement_y_ratio=0.8, scroll_speed=400.0)
        # lookbehind = 120/400 = 0.3s; lookahead = 480/400 = 1.2s
        note = make_note(time=0.0, is_ln_start=True, ln_end_time=0.1)
        chart = make_chart(notes=[note])
        p = make_player(chart=chart, config=config)
        p.seek(0.25)  # head is 0.25s in the past (within lookbehind=0.3)
        assert note in p.get_visible_notes()

    def test_ln_end_notes_are_included_for_rendering_tail_cap(self):
        # is_ln_end notes appear in the visible list — render_frame decides what to draw
        head = make_note(time=0.0, is_ln_start=True, ln_end_time=0.5)
        tail = make_note(time=0.5, is_ln_end=True)
        chart = make_chart(notes=[head, tail])
        p = make_player(chart=chart)
        p.seek(0.25)
        visible = p.get_visible_notes()
        assert head in visible
        assert tail in visible

    def test_returns_only_notes_in_window(self):
        notes = [make_note(time=float(i)) for i in range(20)]
        chart = make_chart(notes=notes)
        p = make_player(chart=chart)
        p.seek(10.0)
        visible = p.get_visible_notes()
        for n in visible:
            assert n.time >= p.current_time - p.lookbehind
            assert n.time <= p.current_time + p.lookahead


# ---------------------------------------------------------------------------
# render_frame — draw call ordering and correctness
# ---------------------------------------------------------------------------

class TestRenderFrame:
    def _make_player_with_mock_renderer(self, chart=None, config=None):
        chart  = chart  or make_chart()
        config = config or make_config()
        mock_renderer = MagicMock()
        player = Player(chart, mock_renderer, config)
        return player, mock_renderer

    def test_begin_frame_called_first(self):
        p, r = self._make_player_with_mock_renderer()
        p.render_frame()
        assert r.method_calls[0] == call.begin_frame()

    def test_end_frame_called_last(self):
        p, r = self._make_player_with_mock_renderer()
        p.render_frame()
        assert r.method_calls[-1] == call.end_frame()

    def test_draw_note_called_for_visible_non_ln_end_note(self):
        note = make_note(time=0.0, lane=3)
        chart = make_chart(notes=[note])
        p, r = self._make_player_with_mock_renderer(chart=chart)
        p.seek(0.0)
        p.render_frame()
        r.draw_note.assert_called()

    def test_draw_note_not_called_for_ln_end(self):
        # is_ln_end notes: only the tail cap is drawn via draw_ln_body route
        head = make_note(time=0.0, is_ln_start=True, ln_end_time=0.5, lane=0)
        tail = make_note(time=0.5, is_ln_end=True, lane=0)
        chart = make_chart(notes=[head, tail])
        p, r = self._make_player_with_mock_renderer(chart=chart)
        p.seek(0.25)
        p.render_frame()
        # draw_note should be called for head, not called with tail's y
        tail_y = p.time_to_y(tail.time)
        for c in r.draw_note.call_args_list:
            assert c.kwargs.get('y') != tail_y or c.kwargs.get('x') != p.config.lane_x(tail.lane)

    def test_draw_ln_body_called_for_ln_start(self):
        head = make_note(time=0.0, is_ln_start=True, ln_end_time=0.5, lane=0)
        tail = make_note(time=0.5, is_ln_end=True, lane=0)
        chart = make_chart(notes=[head, tail])
        p, r = self._make_player_with_mock_renderer(chart=chart)
        p.seek(0.25)
        p.render_frame()
        r.draw_ln_body.assert_called()

    def test_draw_note_receives_correct_x_for_lane(self):
        config = make_config(window_width=800, lane_widths=(40,) * 8)
        note = make_note(time=0.0, lane=2)
        chart = make_chart(notes=[note])
        p, r = self._make_player_with_mock_renderer(chart=chart, config=config)
        p.seek(0.0)
        p.render_frame()
        expected_x = config.lane_x(2)
        called_x = r.draw_note.call_args.kwargs['x']
        assert called_x == expected_x

    def test_draw_note_receives_correct_y(self):
        config = make_config()
        note = make_note(time=1.0, lane=0)
        chart = make_chart(notes=[note])
        p, r = self._make_player_with_mock_renderer(chart=chart, config=config)
        p.seek(0.0)
        p.render_frame()
        expected_y = p.time_to_y(1.0)
        called_y = r.draw_note.call_args.kwargs['y']
        assert called_y == pytest.approx(expected_y)

    def test_draw_note_receives_correct_width(self):
        config = make_config(lane_widths=(50, 40, 40, 40, 40, 40, 40, 40))
        note = make_note(time=0.0, lane=0)
        chart = make_chart(notes=[note])
        p, r = self._make_player_with_mock_renderer(chart=chart, config=config)
        p.seek(0.0)
        p.render_frame()
        called_width = r.draw_note.call_args.kwargs['width']
        assert called_width == 50

    def test_draw_ln_body_top_y_is_above_bottom_y(self):
        # LN body: head is below tail on screen (head closer to judgement, tail higher up)
        head = make_note(time=1.0, is_ln_start=True, ln_end_time=2.0, lane=0)
        tail = make_note(time=2.0, is_ln_end=True, lane=0)
        chart = make_chart(notes=[head, tail])
        p, r = self._make_player_with_mock_renderer(chart=chart)
        p.seek(0.0)
        p.render_frame()
        kw = r.draw_ln_body.call_args.kwargs
        assert kw['top_y'] < kw['bottom_y']
