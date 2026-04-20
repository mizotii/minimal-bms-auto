def _decode_line(line):
    try:
        decoded_line = line.decode('cp932')
    except (ValueError, UnicodeDecodeError):
        decoded_line = line.decode('latin-1')
    return decoded_line