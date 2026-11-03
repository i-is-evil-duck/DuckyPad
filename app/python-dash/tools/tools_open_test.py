import ctypes, time

k32 = ctypes.windll.kernel32
gr = 0xC0000000  # GENERIC_READ | GENERIC_WRITE
path = '\\\\.\\COM4'

t0 = time.time()
h = k32.CreateFileW(path, gr, 0, None, 3, 0, None)  # OPEN_EXISTING
print('CreateFile returned in %.2fs, handle=%d, err=%d' % (time.time() - t0, h, k32.GetLastError()))
if h not in (-1, 0):
    dcb = (ctypes.c_uint8 * 100)()
    dcb[0] = 100  # DCBlength
    ok = k32.GetCommState(h, dcb)
    print('GetCommState ok=%s' % ok)
    t1 = time.time()
    ok = k32.SetCommState(h, dcb)
    print('SetCommState ok=%s took %.2fs err=%d' % (ok, time.time() - t1, k32.GetLastError()))
    t2 = time.time()
    ok = k32.EscapeCommFunction(h, 5)  # SETDTR
    print('EscapeComm DTR ok=%s took %.2fs' % (ok, time.time() - t2))
    k32.CloseHandle(h)
