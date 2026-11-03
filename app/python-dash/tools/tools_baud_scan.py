import serial, time

for baud in (9600, 115200, 57600, 19200, 4800, 19200, 38400):
    try:
        s = serial.Serial('COM4', baud, timeout=0.3)
        s.reset_input_buffer()
        time.sleep(0.1)
        data = s.read(96)
        s.close()
        if not data:
            print(f'@{baud}: (no data)')
            continue
        asc = ''.join(chr(b) if 32 <= b < 127 else '.' for b in data[:80])
        print(f'@{baud}: {data[:24].hex(" ")}')
        print(f'         ascii: {asc}')
        if '|' in asc:
            print(f'>>> BAUD {baud} LOOKS RIGHT <<<')
    except Exception as e:
        print(f'@{baud}: err {e}')
