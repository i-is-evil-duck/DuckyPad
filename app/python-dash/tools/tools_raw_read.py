import ctypes, time

k32 = ctypes.windll.kernel32
gr = 0xC0000000
path = '\\\\.\\COM4'

h = k32.CreateFileW(path, gr, 0, None, 3, 0, None)
if h in (-1, 0):
    print('open failed, err=%d' % k32.GetLastError())
    raise SystemExit

# purge buffers
k32.PurgeComm(h, 0xF)  # PURGE_TXCLEAR|PURGE_RXCLEAR|PURGE_TXABORT|PURGE_RXABORT

# set timeouts: ReadIntervalTimeout=20, ReadTotal=100ms
cto = (ctypes.c_uint32 * 5)(20, 0, 0, 0, 100)
ok = k32.SetCommTimeouts(h, cto)
print('SetCommTimeouts ok=%s' % ok)

# configure 115200 8N1 via DCB
dcb = (ctypes.c_uint8 * 100)()
dcb[0] = 100
k32.GetCommState(h, dcb)
import struct
# rebuild DCB fields: (bytes per ctypes c_uint8*100 interpreted as struct)
# use ctypes cast to struct approach
class DCB(ctypes.Structure):
    _fields_ = [
        ("DCBlength", ctypes.c_uint32),
        ("BaudRate", ctypes.c_uint32),
        ("flags", ctypes.c_uint32),
        ("wReserved", ctypes.c_uint16),
        ("XonLim", ctypes.c_uint16),
        ("XoffLim", ctypes.c_uint16),
        ("ByteSize", ctypes.c_uint8),
        ("Parity", ctypes.c_uint8),
        ("StopBits", ctypes.c_uint8),
        ("XonChar", ctypes.c_char),
        ("XoffChar", ctypes.c_char),
        ("ErrorChar", ctypes.c_char),
        ("EofChar", ctypes.c_char),
        ("EvtChar", ctypes.c_char),
        ("wReserved1", ctypes.c_uint16),
    ]
d = DCB()
pv = ctypes.cast(ctypes.pointer(d), ctypes.c_void_p)
# dump existing settings first
k32.GetCommState(h, ctypes.byref(d))
print('current baud=%d bytesize=%d' % (d.BaudRate, d.ByteSize))
d.BaudRate = 115200
d.flags = d.flags | 1  # fBinary
d.ByteSize, d.Parity, d.StopBits = 8, 0, 0
ok = k32.SetCommState(h, ctypes.byref(d))
print('SetCommState 115200 ok=%s' % ok)

# read loop 1.5s
buf = ctypes.create_string_buffer(4096)
got = b''
t0 = time.time()
while time.time() - t0 < 1.5:
    n = ctypes.c_uint32(0)
    ok = k32.ReadFile(h, buf, 4096, ctypes.byref(n), None)
    if ok and n.value:
        got += buf.raw[:n.value]
k32.CloseHandle(h)
lines = [x.decode('ascii', 'ignore') for x in got.replace(b'\r', b'\n').split(b'\n') if x.strip()]
print('read %d bytes, %d lines' % (len(got), len(lines)))
for l in lines[:6]:
    print('  ', l[:100])
