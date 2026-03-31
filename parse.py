import re
from chart import Chart

HEADER_PATTERN = re.compile('^#([A-Za-z][A-Za-z0-9]*)[ \t]+(.+)$')
DATA_PATTERN = re.compile('^#(\d{3})([0-9A-Za-z]{2}):(.*)$')

def parse_bms(filepath):
    title = ''
    artist = ''
    genre = ''
    initial_bpm = 120.0
    rank = 0
    total = 0.0
    level = 0
    player = 0

    wav_table = {}
    bpm_table = {}
    stop_table = {}

    notes = []
    bgm_events = []
    bpm_changes = []
    measure_lines = []
    stop_events = []

    ln_obj = ''
    total_beats = 0.0
    total_time = 0.0

    with open(filepath, 'rb') as f:
        lines = f.readlines()
        for line in lines:
            try:
                decoded_line = line.decode('shift_jis')
            except ValueError:
                decoded_line = line.decode('latin-1')
            
            m = HEADER_PATTERN.search(decoded_line)
            if m:
                k = m.group(1).upper()
                v = m.group(2)

                match k:
                    case 'TITLE':
                        title = v
                    case 'ARTIST':
                        artist = v
                    case 'GENRE':
                        genre = v
                    case 'BPM':
                        try:
                            initial_bpm = float(v)
                        except:
                            pass
                    case 'RANK':
                        try:
                            rank = int(v)
                        except:
                            pass
                    case 'TOTAL':
                        try:
                            total = float(v)
                        except:
                            pass
                    case 'LEVEL':
                        try:
                            level = int(v)
                        except:
                            pass
                    case 'PLAYER':
                        try:
                            player = int(v)
                        except:
                            pass
                    case 'LNOBJ':
                        ln_obj = v
                    case s if s.startswith('WAV'):
                        wav_table[k[3:]] = v.strip()
                    case s if s.startswith('BPM'):
                        bpm_table[k[3:]] = v.strip()
                    case s if s.startswith('STOP'):
                        stop_table[k[4:]] = v.strip()


            else:
                m = DATA_PATTERN.search(decoded_line)
                if m:
                    k = m.group(1).upper()
                    v = m.group(2)

                    match k:
                        case s if s.startswith('BPM'):



if __name__ == '__main__':
    parse_bms('./ceu/7keys_white.bms')
