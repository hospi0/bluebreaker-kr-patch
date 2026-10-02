# -*- coding: utf-8 -*-
r"""1CPT 압축(0.BIN 0x06020294 해제기 그대로) — 머리 '1CPT' + u32 BE 풀린 크기, +8 부터 명령 바이트:
    b > 0  : 다음 b 바이트 그대로
    b == 0 : 끝
    b < 0  : 다음 바이트 o → 거리 o+1 뒤에서 (2−b) 바이트 복사(겹침 허용)
  python tools/cpt.py scan            → 모든 work/disc 파일의 1CPT 위치·크기
  python tools/cpt.py x 파일 [오프셋]  → work/cpt/<파일>_<오프셋>.bin
"""
import os, struct, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DISC = os.path.join(ROOT, 'work', 'disc')


def unpack(d, p=0):
    """→ (풀린 바이트, 압축 끝 위치)"""
    assert d[p:p + 4] == b'1CPT'
    size = struct.unpack_from('>I', d, p + 4)[0]
    i = p + 8; out = bytearray()
    while True:
        b = d[i]; i += 1
        if b == 0:
            break
        if b < 0x80:
            out += d[i:i + b]; i += b
        else:
            n = 2 - (b - 256); src = len(out) - (d[i] + 1); i += 1
            for k in range(n):
                out.append(out[src + k])
    return bytes(out), i


def pack(data):
    """탐욕 LZ(거리 1‥256, 길이 3‥130) — 해제기와 같은 형식"""
    out = bytearray(b'1CPT' + struct.pack('>I', len(data))); lit = bytearray(); i = 0; n = len(data)

    def flush():
        while lit:
            c = lit[:127]; out.append(len(c)); out.extend(c); del lit[:127]
    while i < n:
        best_l, best_d = 0, 0
        for dist in range(1, min(256, i) + 1):
            s = i - dist; l = 0
            while l < 130 and i + l < n and data[s + l] == data[i + l]:
                l += 1
            if l > best_l:
                best_l, best_d = l, dist
                if l == 130:
                    break
        if best_l >= 3:
            flush(); out.append(256 - (best_l - 2)); out.append(best_d - 1); i += best_l
        else:
            lit.append(data[i]); i += 1
    flush(); out.append(0)
    return bytes(out)


def scan():
    res = []
    for f in sorted(os.listdir(DISC)):
        d = open(os.path.join(DISC, f), 'rb').read(); p = d.find(b'1CPT')
        while p >= 0:
            try:
                u, e = unpack(d, p)
                if len(u) == struct.unpack_from('>I', d, p + 4)[0]:
                    res.append((f, p, e, len(u)))
            except Exception:
                pass
            p = d.find(b'1CPT', p + 1)
    return res


if __name__ == '__main__':
    if sys.argv[1] == 'scan':
        for f, p, e, n in scan():
            print('%-14s %8X..%8X  풀림 %6X' % (f, p, e, n))
    elif sys.argv[1] == 'x':
        f = sys.argv[2]; d = open(os.path.join(DISC, f), 'rb').read(); p = int(sys.argv[3], 16) if len(sys.argv) > 3 else d.find(b'1CPT')
        u, e = unpack(d, p); od = os.path.join(ROOT, 'work', 'cpt'); os.makedirs(od, exist_ok=True)
        open(os.path.join(od, '%s_%X.bin' % (f, p)), 'wb').write(u); print(len(u), hex(e))
