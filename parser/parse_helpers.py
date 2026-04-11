def _decode_line(line):
    try:
        decoded_line = line.decode('shift_jis')
    except ValueError:
        decoded_line = line.decode('latin-1')
    return decoded_line