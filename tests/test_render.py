"""
Unit tests for render.py

RenderConfig tests are pure Python — no pygame required.
PygameRenderer tests mock render.pygame to avoid requiring a display.
"""

import pytest
from unittest.mock import MagicMock, call, patch
from math import floor

from render import RenderConfig


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_config(**overrides):
    defaults = dict(
        window_width=800,
        window_height=600,
        fps=60.0,
        scroll_speed=400.0,
        judgement_y_ratio=0.8,
        lane_widths=(40, 40, 40, 40, 40, 40, 40, 40),
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


@pytest.fixture
def mock_pygame(monkeypatch):
    """Replace render.pygame with a MagicMock so no display is needed."""
    mock = MagicMock()
    mock.QUIT    = 256
    mock.KEYDOWN = 768
    mock.K_ESCAPE = 27
    monkeypatch.setattr('render.pygame', mock)
    return mock


@pytest.fixture
def renderer(mock_pygame):
    from render import PygameRenderer
    return PygameRenderer(make_config())


# ---------------------------------------------------------------------------
# RenderConfig.total_lane_width
# ---------------------------------------------------------------------------

class TestTotalLaneWidth:
    def test_uniform_widths(self):
        config = make_config(lane_widths=(40,) * 8)
        assert config.total_lane_width == 320

    def test_non_uniform_widths(self):
        config = make_config(lane_widths=(30, 40, 30, 40, 30, 40, 30, 40))
        assert config.total_lane_width == 280


# ---------------------------------------------------------------------------
# RenderConfig.lane_x_offset
# ---------------------------------------------------------------------------

class TestLaneXOffset:
    def test_centered_when_lanes_narrower_than_window(self):
        # (800 - 320) // 2 = 240
        config = make_config(window_width=800, lane_widths=(40,) * 8)
        assert config.lane_x_offset == 240

    def test_zero_when_lanes_exactly_fill_window(self):
        config = make_config(window_width=320, lane_widths=(40,) * 8)
        assert config.lane_x_offset == 0

    def test_integer_division(self):
        # (801 - 320) // 2 = 240
        config = make_config(window_width=801, lane_widths=(40,) * 8)
        assert config.lane_x_offset == 240


# ---------------------------------------------------------------------------
# RenderConfig.judgement_y
# ---------------------------------------------------------------------------

class TestJudgementY:
    def test_ratio_0_is_top(self):
        config = make_config(window_height=600, judgement_y_ratio=0.0)
        assert config.judgement_y == 0

    def test_ratio_1_is_bottom(self):
        config = make_config(window_height=600, judgement_y_ratio=1.0)
        assert config.judgement_y == 600

    def test_ratio_0_8(self):
        config = make_config(window_height=600, judgement_y_ratio=0.8)
        assert config.judgement_y == 480

    def test_floors_fractional_result(self):
        # floor(599 * 0.8) = floor(479.2) = 479
        config = make_config(window_height=599, judgement_y_ratio=0.8)
        assert config.judgement_y == 479


# ---------------------------------------------------------------------------
# RenderConfig.lane_x
# ---------------------------------------------------------------------------

class TestLaneX:
    def test_lane_0_is_left_edge_of_play_field(self):
        # Lane 0 starts at lane_x_offset; no preceding lanes
        config = make_config(window_width=800, lane_widths=(40,) * 8)
        assert config.lane_x(0) == config.lane_x_offset

    def test_lane_1_is_offset_plus_lane_0_width(self):
        config = make_config(window_width=800, lane_widths=(40,) * 8)
        assert config.lane_x(1) == config.lane_x_offset + 40

    def test_lane_2_is_offset_plus_first_two_widths(self):
        config = make_config(window_width=800, lane_widths=(30, 40, 35, 40, 30, 40, 35, 30))
        assert config.lane_x(2) == config.lane_x_offset + 30 + 40

    def test_lane_7_is_offset_plus_first_seven_widths(self):
        widths = (20, 30, 25, 35, 20, 30, 25, 35)
        config = make_config(window_width=800, lane_widths=widths)
        assert config.lane_x(7) == config.lane_x_offset + sum(widths[:7])


# ---------------------------------------------------------------------------
# RenderConfig.note_color / ln_body_color
# ---------------------------------------------------------------------------

class TestColors:
    def test_note_color_returns_per_lane_color(self):
        notes = tuple((i * 10, i * 10, i * 10) for i in range(8))
        config = make_config(notes=notes)
        for lane in range(8):
            assert config.note_color(lane) == (lane * 10, lane * 10, lane * 10)

    def test_ln_body_color_returns_per_lane_color(self):
        ln_bodies = tuple((i * 5, i * 5, i * 5) for i in range(8))
        config = make_config(ln_bodies=ln_bodies)
        for lane in range(8):
            assert config.ln_body_color(lane) == (lane * 5, lane * 5, lane * 5)


# ---------------------------------------------------------------------------
# Renderer ABC
# ---------------------------------------------------------------------------

class TestRendererABC:
    def test_cannot_instantiate_renderer_directly(self):
        from render import Renderer
        with pytest.raises(TypeError):
            Renderer()

    def test_concrete_subclass_missing_method_cannot_instantiate(self):
        from render import Renderer

        class Incomplete(Renderer):
            def begin_frame(self): ...
            def draw_note(self, x, y, width, height, lane): ...
            # missing draw_ln_body, end_frame, poll_quit

        with pytest.raises(TypeError):
            Incomplete()


# ---------------------------------------------------------------------------
# PygameRenderer.__init__
# ---------------------------------------------------------------------------

class TestPygameRendererInit:
    def test_init_calls_pygame_init(self, mock_pygame, renderer):
        mock_pygame.init.assert_called_once()

    def test_set_mode_receives_tuple(self, mock_pygame):
        """set_mode must receive (width, height) as a tuple, not two args."""
        from render import PygameRenderer
        config = make_config(window_width=800, window_height=600)
        PygameRenderer(config)
        mock_pygame.display.set_mode.assert_called_once_with((800, 600))


# ---------------------------------------------------------------------------
# PygameRenderer.begin_frame
# ---------------------------------------------------------------------------

class TestBeginFrame:
    def test_fills_screen_with_background_color(self, renderer, mock_pygame):
        renderer.begin_frame()
        renderer.screen.fill.assert_called_once_with(renderer.config.background)


# ---------------------------------------------------------------------------
# PygameRenderer.draw_note
# ---------------------------------------------------------------------------

class TestDrawNote:
    def test_draws_rect_with_correct_args(self, renderer, mock_pygame):
        renderer.draw_note(x=100, y=200, width=40, height=10, lane=0)
        mock_pygame.draw.rect.assert_called_once_with(
            renderer.screen,
            renderer.config.notes[0],
            (100, 200, 40, 10),
        )

    def test_draws_rect_with_correct_lane_color(self, renderer, mock_pygame):
        notes = tuple((i * 10, 0, 0) for i in range(8))
        renderer.config = make_config(notes=notes)
        renderer.draw_note(x=0, y=0, width=40, height=10, lane=3)
        _, color, _ = mock_pygame.draw.rect.call_args[0]
        assert color == (30, 0, 0)


# ---------------------------------------------------------------------------
# PygameRenderer.draw_ln_body
# ---------------------------------------------------------------------------

class TestDrawLnBody:
    def test_draws_rect_at_top_y(self, renderer, mock_pygame):
        renderer.draw_ln_body(x=50, top_y=100, width=40, bottom_y=300, lane=0)
        _, _, rect = mock_pygame.draw.rect.call_args[0]
        assert rect[1] == 100  # y = top_y

    def test_rect_height_is_bottom_minus_top(self, renderer, mock_pygame):
        renderer.draw_ln_body(x=50, top_y=100, width=40, bottom_y=300, lane=0)
        _, _, rect = mock_pygame.draw.rect.call_args[0]
        assert rect[3] == 200  # height = bottom_y - top_y = 300 - 100

    def test_draws_with_ln_body_color(self, renderer, mock_pygame):
        ln_bodies = tuple((i * 10, 0, 0) for i in range(8))
        renderer.config = make_config(ln_bodies=ln_bodies)
        renderer.draw_ln_body(x=0, top_y=50, width=40, bottom_y=150, lane=2)
        _, color, _ = mock_pygame.draw.rect.call_args[0]
        assert color == (20, 0, 0)


# ---------------------------------------------------------------------------
# PygameRenderer.end_frame
# ---------------------------------------------------------------------------

class TestEndFrame:
    def test_flips_display(self, renderer, mock_pygame):
        renderer.end_frame()
        mock_pygame.display.flip.assert_called_once()

    def test_ticks_clock_at_fps(self, renderer, mock_pygame):
        renderer.end_frame()
        renderer.clock.tick.assert_called_once_with(renderer.config.fps)


# ---------------------------------------------------------------------------
# PygameRenderer.poll_quit
# ---------------------------------------------------------------------------

class TestPollQuit:
    def _make_event(self, mock_pygame, event_type, **attrs):
        event = MagicMock()
        event.type = event_type
        for k, v in attrs.items():
            setattr(event, k, v)
        return event

    def test_quit_event_calls_pygame_quit(self, renderer, mock_pygame):
        quit_event = self._make_event(mock_pygame, mock_pygame.QUIT)
        mock_pygame.event.get.return_value = [quit_event]
        renderer.poll_quit()
        mock_pygame.quit.assert_called_once()

    def test_escape_keydown_calls_pygame_quit(self, renderer, mock_pygame):
        esc_event = self._make_event(mock_pygame, mock_pygame.KEYDOWN, key=mock_pygame.K_ESCAPE)
        mock_pygame.event.get.return_value = [esc_event]
        renderer.poll_quit()
        mock_pygame.quit.assert_called_once()

    def test_other_keydown_does_not_quit(self, renderer, mock_pygame):
        key_event = self._make_event(mock_pygame, mock_pygame.KEYDOWN, key=65)  # 'A'
        mock_pygame.event.get.return_value = [key_event]
        renderer.poll_quit()
        mock_pygame.quit.assert_not_called()

    def test_no_events_does_not_quit(self, renderer, mock_pygame):
        mock_pygame.event.get.return_value = []
        renderer.poll_quit()
        mock_pygame.quit.assert_not_called()
