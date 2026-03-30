from dataclasses import dataclass
from typing import Dict, List

@dataclass
class Note:
    beat: float
    time: float
    lane: int
    wav_id: str
    is_ln_start: bool
    is_ln_end: bool
    ln_end_time: float

@dataclass
class BPMChange:
    beat: float
    time: float
    bpm: float

@dataclass
class MeasureLine:
    measure: int
    beat: float
    time: float

@dataclass
class BGMEvent:
    beat: float
    time: float
    wav_id: str

@dataclass
class StopEvent:
    beat: float
    time: float
    duration: float

@dataclass
class Chart:
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
    bgm_events: List[BGMEvent]
    bpm_changes: List[BPMChange]
    measure_lines: List[MeasureLine]
    stop_events: List[StopEvent]

    # metadata
    ln_obj: str
    total_beats: float
    total_time: float
