from audio import Mixer, AUDIO_LATENCY
from bisect import bisect_right
from chart import Chart
from render import Renderer, RenderConfig

PREROLL_DURATION = 0.0

class Player:
    def __init__(self, chart: Chart, renderer: Renderer, config: RenderConfig, audio: Mixer=None):
        self.chart = chart
        self.renderer = renderer
        self.config = config
        self.audio = audio

        self.current_time = PREROLL_DURATION * -1.0

        self.notes = chart.notes
        self.measure_lines = chart.measure_lines

        self.is_playing = False
        self.bpm_changes = chart.bpm_changes

        self.notes_time_only = [n.time for n in self.notes]
        self.bpm_changes_time_only = [c.time for c in self.bpm_changes]

    @property
    def current_bpm(self):
        floor_idx = bisect_right(self.bpm_changes_time_only, self.current_time) - 1
        return self.bpm_changes[floor_idx].bpm
    
    @property
    def pixel_visibility(self):
        return self.config.window_height / self.config.scroll_speed
    
    @property
    def lookahead(self):
        return self.pixel_visibility * self.config.judgement_y_ratio
    
    @property
    def lookbehind(self):
        return self.pixel_visibility - self.lookahead
    
    def render_frame(self):
        self.renderer.begin_frame()
        # self.renderer.draw_lane_background()
        # self.get_visible_measure_lines()
        visible_notes = self.get_visible_notes()
        for n in visible_notes:
            
            if not n.is_ln_end:
                lane=n.lane
                x = self.config.lane_x(lane)
                bottom_y = self.time_to_y(n.time)
                width = self.config.lane_widths[lane]

                self.renderer.draw_note(
                    x=x,
                    y=bottom_y,
                    width=self.config.lane_widths[lane],
                    height=self.config.note_height,
                    lane=lane
                )

                if n.is_ln_start:
                    self.renderer.draw_ln_body(
                        x=x,
                        top_y=self.time_to_y(n.ln_end_time),
                        width=width,
                        bottom_y=bottom_y,
                        lane=lane
                    )

        # self.draw_judgement_line()
        # self.draw_hud
        self.renderer.end_frame()

    def start(self):
        self.is_playing = True

    def pause(self):
        self.is_playing = False

    def seek(self, time):
        self.current_time = time
        if self.audio:
            self.audio.seek(time)

    def time_to_y(self, event_time):
        return self.config.judgement_y - (self.config.scroll_speed * (event_time - self.current_time))

    def get_visible_notes(self):
        lookahead_idx = bisect_right(self.notes_time_only, self.current_time + self.lookahead)
        lookbehind_idx = bisect_right(self.notes_time_only, self.current_time - self.lookbehind)
        return self.notes[lookbehind_idx:lookahead_idx]

    """
    def get_visible_measure_lines(self):
        lookahead_idx = bisect_right(self._measure_lines, self.lookahead)
        lookbehind_idx = bisect_right(self._measure_lines, self.lookbehind)
        return self._measure_lines[lookbehind_idx:lookahead_idx]

    def draw_judgement_line(self):
        pass

    def draw_hud(self):
        pass
    """
    
    def update(self, time_delta):
        if self.is_playing:
            self.current_time += time_delta
            if self.audio:
                self.audio.update(self.current_time + AUDIO_LATENCY)