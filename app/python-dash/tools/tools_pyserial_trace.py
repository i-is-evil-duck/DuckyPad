import time, threading

# --- which pyserial call hangs? monkeypatch time markers
import serial
ser = None

def probe():
    global ser
    t0 = time.time()
    try:
        ser = serial.Serial('COM4', 115200, timeout=0.4, write_timeout=0.4)
        ser.flushInput()
        t1 = time.time()
        got = ser.read(512)
        print('open+flush took %.2fs, read(512) took %.2fs' % (t1 - t0, time.time() - t1))
        print('repr:', repr(got[:60]))
        ser.close()
    except Exception as e:
        print('error:', e)

t = threading.Thread(target=probe, daemon=True)
t.start()
t.join(6)
if t.is_alive():
    import traceback, sys
    print('HUNG again - stack of the hung thread:')
    import ctypes
    frame = sys._current_frames().get(t.ident)
    traceback.print_stack(frame)
