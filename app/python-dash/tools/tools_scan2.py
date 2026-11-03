import serial, time

def scan(baud, seconds=3.0, toggle_dtr=True, drop=100):
    try:
        s = serial.Serial('COM4', 115200, timeout=0.3)
    except Exception as e:
        print(f'{baud}: open err {e}')
        return
    # set baud via reconfigure
    s.baudrate = baud
    if toggle_dtr:
        s.dtr = False
        time.sleep(0.25)          # let a Nano/CH340 reset settle
        s.dtr = True
    deadline = time.time() + seconds
    n = 0
    first = b''
    while time.time() < deadline:
        chunk = s.read(256)
        if chunk:
            n += len(chunk)
            if not first:
                first = chunk
    s.close()
    pipe_count = first.count(b'|')
    print(f'{baud}: {n} bytes in {seconds}s ({n/seconds:.0f} B/s), sample={first[:40]!r} pipes_in_sample={pipe_count}')

for b in (115200, 9600):
    scan(b)
