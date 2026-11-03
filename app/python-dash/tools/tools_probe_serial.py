"""Hardened COM4 open test - can never hang the shell (threaded open with join timeout)."""
import sys, time, threading
import serial

BAUDS = (115200, 9600, 19200, 57600)

def try_baud(baud, results):
    try:
        ser = serial.Serial("COM4", baud, timeout=0.4)
    except Exception as e:
        results[baud] = f"open error: {e}"
        return
    try:
        ser.reset_input_buffer()
        got, t0 = [], time.time()
        while time.time() - t0 < 1.5 and len(got) < 5:
            line = ser.readline().decode("ascii", "ignore").strip()
            if line:
                got.append(line)
        results[baud] = got
    finally:
        ser.close()

results = {}
for baud in BAUDS:
    t = threading.Thread(target=try_baud, args=(baud, results), daemon=True)
    t.start()
    t.join(timeout=4)
    if t.is_alive():
        results[baud] = "OPEN HUNG (driver wedged - replug USB needed)"
    if isinstance(results.get(baud), list) and results[baud]:
        break

for baud, r in results.items():
    if isinstance(r, list):
        print(f"COM4 @ {baud}: {len(r)} lines")
        for l in r[:5]:
            print("   ", l[:100])
    else:
        print(f"COM4 @ {baud}: {r}")
sys.stdout.flush()
