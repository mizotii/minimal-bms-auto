"""Data classes for a parsed BMS chart"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

@dataclass
class Event:
    beat: float
    time: float

    def __lt__(self, other):
        return self.time < other.time
    
@dataclass
class SoundEvent(Event):
    wav_id: str
    
@dataclass
class Note(SoundEvent):
    """A single playfield note.

    ln_end_time is only meaningful when is_ln_start is True.
    is_ln_end notes are not rendered, their sound fires at the head.
    """
    lane: int          # 0–6 = keys, 7 = scratch
    is_ln_start: bool
    is_ln_end: bool
    ln_end_time: float

@dataclass
class BPMChange(Event):
    bpm: float

@dataclass
class MeasureLine(Event):
    measure: int

@dataclass
class BGMEvent(SoundEvent):
    pass

@dataclass
class StopEvent(Event):
    """A scroll stop. The chart freezes for `duration` seconds at this beat."""
    duration: float  # seconds

@dataclass
class Chart:
    """Top-level container returned by parse_bms. All lists are sorted by time."""
    filepath: Path

    # headers
    title: str
    subtitle: str
    artist: str
    subartist: str
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
    sound_events: List[SoundEvent]
    notes: List[Note]
    bpm_changes: List[BPMChange]
    measure_lines: List[MeasureLine]
    bgm_events: List[BGMEvent]
    stop_events: List[StopEvent]

    # metadata
    ln_obj: str
    total_beats: float
    total_time: float
