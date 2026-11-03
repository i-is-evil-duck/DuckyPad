import serial, time
from collections import Counter

for baud in (115200, 9600):
    try:
        s = serial.Serial('COM4', baud, timeout=0.3)
    except Exception as e:
        print(f'{baud}: open err {e}')
        continue
    s.reset_input_buffer()
    time.sleep(0.05)
    deadline = time.time() + 1.5
    c = Counter()
    sample = b''
    while time.time() < deadline:
        chunk = s.read(512)
        if chunk:
            c.update(chunk)
            if len(sample) < 200:
                sample += chunk
    s.close()
    print(f'--- {baud}: distinctive bytes in 1.5s')
    top = c.most_common(10)
    for byte, n in top:
        print(f'  {byte:#04x} : {n}')
    print('  sample:', sample[:80].hex(' '))
    asc = ''.join(chr(b) if 32 <= b < 127 else '.' for b in sample[:80])
    print('  ascii:', asc)
