from dataclasses import dataclass

type LaneWidths = tuple[int, int, int, int, int, int, int, int]
type Color = tuple[int, int, int]
type Notes = tuple[Color, Color, Color, Color, Color, Color, Color, Color]

@dataclass
class RenderConfig:
    window_width: float
    window_height: float
    fps: float
    scroll_speed: float # pixels/second
    judgement_y_ratio: float # 0.0 top, 1.0 bottom
    lane_widths: LaneWidths
    note_height: float

    background: Color
    lane: Color
    border: Color
    judgement_line: Color
    measure_line: Color
    hud_text: Color
    notes: Notes