from abc import ABC, abstractmethod
from dataclasses import dataclass
from math import floor
import pygame

type LaneWidths = tuple[int, int, int, int, int, int, int, int]
type Color = tuple[int, int, int]
type Notes = tuple[Color, Color, Color, Color, Color, Color, Color, Color]
type LNBodies = tuple[Color, Color, Color, Color, Color, Color, Color, Color]

@dataclass
class RenderConfig:
    window_width: int
    window_height: int
    fps: float
    scroll_speed: float # pixels/second
    judgement_y_ratio: float # 0.0 top, 1.0 bottom
    lane_widths: LaneWidths
    note_height: int

    background: Color
    lane: Color
    border: Color
    judgement_line: Color
    measure_line: Color
    hud_text: Color
    notes: Notes
    ln_bodies: LNBodies

    @property
    def total_lane_width(self):
        return sum(self.lane_widths)
    
    @property
    def lane_x_offset(self):
        return (self.window_width - self.total_lane_width) // 2
    
    @property
    def judgement_y(self):
        return floor(self.judgement_y_ratio * self.window_height)
    
    def lane_x(self, lane):
        return self.lane_x_offset + (sum(self.lane_widths[:lane]))
    
    def note_color(self, lane):
        return self.notes[lane]
    
    def ln_body_color(self, lane):
        return self.ln_bodies[lane]
    
class Renderer(ABC):
    @abstractmethod
    def begin_frame(self):
        ...

    @abstractmethod
    def draw_note(self, x, y, width, height, lane):
        ...

    @abstractmethod
    def draw_ln_body(self, x, top_y, width, bottom_y, lane):
        ...

    @abstractmethod
    def end_frame(self):
        ...

    @abstractmethod
    def poll_quit(self):
        ...

    """probably belong somewhere else? minimal player doesn't necessarily need these

    def draw_lane_background(self, config):
        ...

    def draw_measure_line(self, config, y):
        ...

    def draw_lane_background(self):
        ...

    def draw_hud(self):
        ...
    """

class PygameRenderer(Renderer):
    def __init__(self, config: RenderConfig):
        self.config = config

        pygame.init()
        pygame.font.init()
        self.screen = pygame.display.set_mode((self.config.window_width, self.config.window_height))
        self.clock = pygame.time.Clock()
        self.running = True

    def begin_frame(self):
        self.screen.fill(self.config.background)

    def draw_note(self, x, y, width, height, lane):
        color = self.config.notes[lane]

        pygame.draw.rect(
            self.screen,
            color,
            (x, y, width, height)
        )
    
    def draw_ln_body(self, x, top_y, width, bottom_y, lane):
        color = self.config.ln_bodies[lane]
        height = bottom_y - top_y

        pygame.draw.rect(
            self.screen,
            color,
            (x, top_y, width, height)
        )

    def end_frame(self):
        pygame.display.flip()
        self.clock.tick(self.config.fps)

    def poll_quit(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                pygame.quit()