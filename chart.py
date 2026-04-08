"""Data classes for a parsed BMS chart"""

from dataclasses import dataclass
from typing import Dict, List

@dataclass(order=True)
class Note:
    """A single playfield note.

    ln_end_time is only meaningful when is_ln_start is True.
    is_ln_end notes are not rendered, their sound fires at the head.
    """
    beat: float
    time: float
    lane: int          # 0–6 = keys, 7 = scratch
    wav_id: str
    is_ln_start: bool
    is_ln_end: bool
    ln_end_time: float

@dataclass
class BPMChange:
    beat: float
    time: float
    bpm: float

    def __lt__(self, other):
        return self.beat < other.beat

@dataclass
class MeasureLine:
    beat: float
    time: float
    measure: int

    def __lt__(self, other):
        return self.beat < other.beat

@dataclass
class BGMEvent:
    beat: float
    time: float
    wav_id: str

    def __lt__(self, other):
        return self.beat < other.beat

@dataclass
class StopEvent:
    """A scroll stop. The chart freezes for `duration` seconds at this beat."""
    beat: float
    time: float
    duration: float  # seconds

@dataclass
class Chart:
    """Top-level container returned by parse_bms. All lists are sorted by time."""
    # headers
    title: str
    artist: str
    genre: str
    initial_bpm: float
    rank: int
    total: float
    level: int
    player: int

    # assets
    wav_table: Dict[str, str]
    bpm_table: Dict[str, float]
    stop_table: Dict[str, float]

    # events
    notes: List[Note]
    bpm_changes: List[BPMChange]
    measure_lines: List[MeasureLine]
    bgm_events: List[BGMEvent]
    stop_events: List[StopEvent]

    # metadata
    ln_obj: str
    total_beats: float
    total_time: float
