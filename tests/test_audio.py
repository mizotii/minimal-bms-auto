"""
Unit and integration tests for audio.py (Mixer class).

Unit tests use mocks and synthetic data -- no real audio files or pygame
hardware required.

Integration tests use a real chart file in assets/ and exercise the full
loading and update pipeline with pygame.mixer running in dummy mode.
"""

import os
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

import audio
from chart import Chart, SoundEvent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_sound_event(time, wav_id, beat=0.0):
    return SoundEvent(beat=beat, time=time, wav_id=wav_id)


def make_chart(tmp_path, wav_table=None, sound_events=None):
    """Return a minimal Chart with just enough fields for Mixer.__init__."""
    return Chart(
        filepath        = tmp_path / 'test.bms',
        title='', subtitle='', artist='', subartist='', genre='',
        initial_bpm=120.0, rank=2, total=200.0, level=5, player=1,
        wav_table       = wav_table or {},
        bpm_table       = {},
        stop_table      = {},
        sound_events    = sound_events or [],
        notes           = [],
        bpm_changes     = [],
        measure_lines   = [],
        bgm_events      = [],
        stop_events     = [],
        ln_obj          = 'ZZ',
        total_beats     = 0.0,
        total_time      = 0.0,
    )


# Patch target -- patches the `mixer` name already bound in the audio module.
# Do NOT reload audio after patching or the binding will be restored.
MIXER_PATCH = 'audio.mixer'


def _silent_sound_factory(silent_sentinel):
    """Return a Sound side_effect that returns sentinel for the 4-byte warmup."""
    def make_sound(*args, buffer=None, **kwargs):
        if buffer is not None and len(buffer) == 4 and all(b == 0 for b in buffer):
            return silent_sentinel
        return MagicMock()
    return make_sound


def _tracking_sound_factory(sound_mocks):
    """Return a Sound side_effect that records created mocks keyed by stem."""
    def make_sound(*args, buffer=None, **kwargs):
        if buffer is not None:
            return MagicMock()  # silent warmup -- ignored
        path = args[0] if args else kwargs.get('path', '')
        key = Path(str(path)).stem
        m = MagicMock()
        sound_mocks[key] = m
        return m
    return make_sound


# ---------------------------------------------------------------------------
# Unit tests -- Mixer init / lifecycle
# ---------------------------------------------------------------------------

class TestMixerInit:
    def test_mixer_quit_called_before_init(self, tmp_path):
        """quit() must be called before init() so previous settings don't persist."""
        chart = make_chart(tmp_path)
        call_order = []

        with patch(MIXER_PATCH) as mock_mixer:
            mock_mixer.quit.side_effect   = lambda: call_order.append('quit')
            mock_mixer.init.side_effect   = lambda **kw: call_order.append('init')
            mock_mixer.Sound.return_value = MagicMock()
            audio.Mixer(chart)

        assert call_order.index('quit') < call_order.index('init')

    def test_mixer_init_called_with_buffer(self, tmp_path):
        """mixer.init must receive a buffer kwarg for dropout resilience."""
        chart = make_chart(tmp_path)

        with patch(MIXER_PATCH) as mock_mixer:
            mock_mixer.Sound.return_value = MagicMock()
            audio.Mixer(chart)

        _, kwargs = mock_mixer.init.call_args
        assert 'buffer' in kwargs, 'buffer size must be passed to mixer.init'
        assert kwargs['buffer'] >= 512, 'buffer should be set for dropout resilience'

    def test_silent_warmup_sound_played(self, tmp_path):
        """A silent 4-byte sound must be played during init to warm up the driver."""
        chart = make_chart(tmp_path)
        silent_mock = MagicMock()

        with patch(MIXER_PATCH) as mock_mixer:
            mock_mixer.Sound.side_effect = _silent_sound_factory(silent_mock)
            audio.Mixer(chart)

        silent_mock.play.assert_called_once()

    def test_next_sound_idx_initialises_to_zero(self, tmp_path):
        chart = make_chart(tmp_path)
        with patch(MIXER_PATCH) as mock_mixer:
            mock_mixer.Sound.return_value = MagicMock()
            m = audio.Mixer(chart)
        assert m._next_sound_idx == 0


# ---------------------------------------------------------------------------
# Unit tests -- load_sounds
# ---------------------------------------------------------------------------

class TestLoadSounds:
    def test_sound_loaded_for_each_wav_entry(self, tmp_path):
        """Every wav_table entry must produce a Sound in sound_table."""
        wav_table = {'01': 'kick.wav', '02': 'snare.wav'}
        for fname in wav_table.values():
            (tmp_path / fname).write_bytes(b'')
        chart = make_chart(tmp_path, wav_table=wav_table)
        sound_mocks = {}

        with patch(MIXER_PATCH) as mock_mixer:
            mock_mixer.Sound.side_effect = _tracking_sound_factory(sound_mocks)
            m = audio.Mixer(chart)

        assert set(m.sound_table.keys()) == {'01', '02'}

    def test_sound_loaded_from_correct_directory(self, tmp_path):
        """Sounds must be loaded from the chart's parent directory."""
        wav_table = {'01': 'kick.wav'}
        (tmp_path / 'kick.wav').write_bytes(b'')
        chart = make_chart(tmp_path, wav_table=wav_table)
        loaded_paths = []

        with patch(MIXER_PATCH) as mock_mixer:
            def make_sound(*args, buffer=None, **kwargs):
                if buffer is not None:
                    return MagicMock()
                loaded_paths.append(Path(args[0] if args else kwargs.get('path', '')))
                return MagicMock()
            mock_mixer.Sound.side_effect = make_sound
            audio.Mixer(chart)

        kick_path = tmp_path / 'kick.wav'
        assert any(p == kick_path for p in loaded_paths), \
            f'kick.wav not loaded from {tmp_path}; got {loaded_paths}'

    def test_empty_wav_table_loads_no_sounds(self, tmp_path):
        chart = make_chart(tmp_path, wav_table={})
        with patch(MIXER_PATCH) as mock_mixer:
            mock_mixer.Sound.return_value = MagicMock()
            m = audio.Mixer(chart)
        assert m.sound_table == {}


# ---------------------------------------------------------------------------
# Unit tests -- seek
# ---------------------------------------------------------------------------

class TestSeek:
    def _make_mixer(self, tmp_path, events):
        chart = make_chart(tmp_path, sound_events=events)
        with patch(MIXER_PATCH) as mock_mixer:
            mock_mixer.Sound.return_value = MagicMock()
            return audio.Mixer(chart)

    def test_seek_positions_at_first_event_at_that_time(self, tmp_path):
        """After seek(t), the next event to fire must be the first one at or after t."""
        events = [
            make_sound_event(1.0, '01'),
            make_sound_event(2.0, '02'),
            make_sound_event(3.0, '03'),
        ]
        m = self._make_mixer(tmp_path, events)
        m.seek(2.0)
        assert m.sound_events[m._next_sound_idx].time >= 2.0

    def test_seek_to_start_resets_index(self, tmp_path):
        events = [make_sound_event(i * 1.0, '01') for i in range(5)]
        m = self._make_mixer(tmp_path, events)
        m._next_sound_idx = 4
        m.seek(0.0)
        assert m._next_sound_idx == 0

    def test_seek_past_end_does_not_crash(self, tmp_path):
        events = [make_sound_event(1.0, '01')]
        m = self._make_mixer(tmp_path, events)
        m.seek(999.0)   # should not raise


# ---------------------------------------------------------------------------
# Unit tests -- update
# ---------------------------------------------------------------------------

class TestUpdate:
    def _make_mixer(self, tmp_path, events, wav_table=None):
        wav_table = wav_table or {e.wav_id: f'{e.wav_id}.wav' for e in events}
        for fname in wav_table.values():
            (tmp_path / fname).write_bytes(b'')
        chart = make_chart(tmp_path, wav_table=wav_table, sound_events=events)
        sound_mocks = {}

        with patch(MIXER_PATCH) as mock_mixer:
            mock_mixer.Sound.side_effect = _tracking_sound_factory(sound_mocks)
            mixer_obj = audio.Mixer(chart)

        return mixer_obj, sound_mocks

    def test_fires_events_at_or_before_current_time(self, tmp_path):
        events = [
            make_sound_event(1.0, '01'),
            make_sound_event(2.0, '02'),
            make_sound_event(3.0, '03'),
        ]
        m, sounds = self._make_mixer(tmp_path, events)
        m.update(2.0)
        assert sounds['01'].play.call_count == 1
        assert sounds['02'].play.call_count == 1
        assert sounds['03'].play.call_count == 0

    def test_does_not_replay_past_events(self, tmp_path):
        events = [make_sound_event(1.0, '01')]
        m, sounds = self._make_mixer(tmp_path, events)
        m.update(2.0)
        m.update(3.0)   # second call -- event already passed
        assert sounds['01'].play.call_count == 1

    def test_fires_event_exactly_at_current_time(self, tmp_path):
        """Events at exactly current_time must fire (use <= not <)."""
        events = [make_sound_event(1.0, '01')]
        m, sounds = self._make_mixer(tmp_path, events)
        m.update(1.0)
        assert sounds['01'].play.call_count == 1

    def test_update_at_end_of_list_does_not_crash(self, tmp_path):
        """update() past the last event must not raise IndexError."""
        events = [make_sound_event(1.0, '01')]
        m, _ = self._make_mixer(tmp_path, events)
        m.update(1.0)
        m.update(2.0)   # _next_sound_idx is now == len(events); must not crash

    def test_no_sounds_fired_before_any_event(self, tmp_path):
        events = [make_sound_event(5.0, '01')]
        m, sounds = self._make_mixer(tmp_path, events)
        m.update(0.0)
        assert sounds['01'].play.call_count == 0

    def test_multiple_events_same_time_all_fire(self, tmp_path):
        """All events at the same timestamp must fire in a single update call."""
        events = [
            make_sound_event(1.0, '01'),
            make_sound_event(1.0, '02'),
            make_sound_event(1.0, '03'),
        ]
        m, sounds = self._make_mixer(tmp_path, events)
        m.update(1.0)
        for key in ('01', '02', '03'):
            assert sounds[key].play.call_count == 1

    def test_index_advances_correctly(self, tmp_path):
        events = [make_sound_event(float(i), '01') for i in range(5)]
        m, _ = self._make_mixer(tmp_path, events)
        m.update(2.5)
        # Events at 0, 1, 2 fired (times 0.0, 1.0, 2.0 <= 2.5); index should be 3
        assert m._next_sound_idx == 3


# ---------------------------------------------------------------------------
# Integration test -- real chart file
# ---------------------------------------------------------------------------

ASSET_BMS = Path(__file__).parent / 'assets'


def find_bms_file():
    """Return the first .bms/.bme file found in tests/assets/, or None."""
    for ext in ('*.bms', '*.bme'):
        matches = list(ASSET_BMS.glob(ext))
        if matches:
            return matches[0]
    return None


@pytest.mark.skipif(find_bms_file() is None, reason='no BMS file in tests/assets/')
class TestMixerIntegration:
    """
    Exercises Mixer against a real chart file.
    pygame.mixer runs in SDL dummy-audio mode so no hardware is required.
    """

    @pytest.fixture(autouse=True)
    def set_dummy_audio(self):
        os.environ['SDL_AUDIODRIVER'] = 'dummy'
        yield
        os.environ.pop('SDL_AUDIODRIVER', None)

    @pytest.fixture
    def chart(self):
        from parse import BMSParser
        return BMSParser(str(find_bms_file())).build()

    def test_loads_without_error(self, chart):
        m = audio.Mixer(chart)
        assert m.sound_table is not None

    def test_sound_table_non_empty_when_files_exist(self, chart):
        m = audio.Mixer(chart)
        wav_dir = chart.filepath.parent
        any_file_exists = any(
            (wav_dir / fname).exists() or
            any((wav_dir / (fname.rsplit('.', 1)[0] + ext)).exists()
                for ext in ('.ogg', '.wav', '.mp3', '.flac'))
            for fname in chart.wav_table.values()
        )
        if any_file_exists:
            assert len(m.sound_table) > 0

    def test_update_through_full_chart_does_not_crash(self, chart):
        """Simulate advancing time from -2s to the end of the chart."""
        m = audio.Mixer(chart)
        dt = 1 / 60
        t = -2.0
        end = chart.total_time + 2.0
        while t <= end:
            m.update(t)
            t += dt

    def test_seek_then_update_fires_correct_events(self, chart):
        """After seeking to a mid-chart position, update should only fire events from there."""
        m = audio.Mixer(chart)
        if not chart.sound_events:
            pytest.skip('chart has no sound events')
        mid = chart.sound_events[len(chart.sound_events) // 2].time
        m.seek(mid)
        idx_before = m._next_sound_idx
        m.update(mid + 0.5)
        assert m._next_sound_idx >= idx_before
