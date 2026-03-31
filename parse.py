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

    ln_obj = ''

    raw_data = []

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
                v = m.group(2).strip()

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
                    case 'PLAYLEVEL':
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
                        wav_table[k[3:]] = v
                    case s if s.startswith('BPM'):
                        try:
                            bpm_table[k[3:]] = float(v)
                        except:
                            pass
                    case s if s.startswith('STOP'):
                        try:
                            stop_table[k[4:]] = float(v)
                        except:
                            pass

                continue

            m = DATA_PATTERN.search(decoded_line)
            if m:
                raw_data.append(m.groups())

                continue
    
    # beat to time
    for r in raw_data:
        pass



if __name__ == '__main__':
    parse_bms('./ceu/7keys_white.bms')
