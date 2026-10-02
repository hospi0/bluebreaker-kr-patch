# -*- coding: utf-8 -*-
r"""SCR.BIN 묶음 구조 (2026-10-02)
  SCR.BIN = 0x800 정렬 묶음들. 묶음 머리 = u32 BE 스크립트 시작 오프셋 n개(묶음 기준) + NUL 로 끝나는 이름표 문자열
  (빈 문자열이면 00 한 바이트) → 첫 오프셋 = 첫 스크립트 시작. 마지막 오프셋도 스크립트 시작(끝 표지 아님).
  스크립트 사이 점프는 «스크립트 번호»(JP 00 nn · JTR 표 u16) — 바이트 주소 아님.
  묶음 끝 = 다음 묶음 시작(마지막 스크립트 뒤는 이전 버퍼 찌꺼기가 섞여 있음 — 같이 옮긴다).
  blocks(d) → [(시작, n, 오프셋 목록, 다음 묶음 시작)]
"""
import struct


def header(d, b):
    """b 에 묶음 머리가 있으면 n(항목 수), 아니면 0
       ★이름표는 길이 자유(예: 0x44800 «BPAN011» → 첫 오프셋 0x48) — 2026-10-02 실기 멈춤 원인(4n+1 만 보던 판정이 놓침)"""
    if b + 8 > len(d):
        return 0
    f = struct.unpack_from('>I', d, b)[0]
    if not 5 <= f < 0x1000 or d[b + f - 1] != 0:
        return 0
    for n in range(f // 4, 0, -1):
        lab = d[b + 4 * n:b + f - 1]
        if any(not 0x20 <= c < 0x7F for c in lab):
            continue
        o = [struct.unpack_from('>I', d, b + 4 * i)[0] for i in range(n)]
        if o[0] == f and all(x <= y for x, y in zip(o, o[1:])) and o[-1] < 0x10000:
            return n
    return 0


def blocks(d):
    st = [b for b in range(0, len(d), 0x800) if header(d, b)]
    out = []
    for i, b in enumerate(st):
        n = header(d, b)
        o = [struct.unpack_from('>I', d, b + 4 * k)[0] for k in range(n)]
        out.append((b, n, o, st[i + 1] if i + 1 < len(st) else len(d)))
    return out


# ★0.BIN 0x6E3E4 = SCR.BIN 묶음 표 299개 (u16 BE 섹터, u16 BE «읽는 길이») — 게임은 이 길이만큼만 스크립트 버퍼(Low RAM 0x200000)로 옮긴다.
#   길이 뒤는 찌꺼기. 묶음을 길게 다시 쓰고 이 값을 안 고치면 끝 명령이 잘려 해석기가 엉뚱한 데를 실행한다
#   (2026-10-02 실기: 상자에서 «요정의 서» 얻은 뒤 멈춤 — 0x3B800 «…를 손에 넣었다» 길이 0x66 고정).
#   blocks() 판정이 놓친 묶음 3개(0x39800·0xBF000·0xC2800 — 이름표가 SJIS 메모)도 이 표에는 있다.
TABLE, NTABLE = 0x6E3E4, 299


def table_blocks(d, d0):
    """→ [(시작, n, 오프셋 목록, 다음 묶음 시작, 읽는 길이, 표 주소)] — 묶음 시작·길이는 0.BIN 표에서"""
    ent = [struct.unpack_from('>HH', d0, TABLE + 4 * i) for i in range(NTABLE)]
    out = []
    for i, (s, sz) in enumerate(ent):
        b = s * 0x800; e = ent[i + 1][0] * 0x800 if i + 1 < NTABLE else len(d)
        f = struct.unpack_from('>I', d, b)[0]; offs = []
        while 4 * len(offs) + 4 <= f:
            v = struct.unpack_from('>I', d, b + 4 * len(offs))[0]
            if not f <= v < sz:
                break
            offs.append(v)
        lab = d[b + 4 * len(offs):b + f]
        assert offs and offs[0] == f and lab.endswith(b'\0') and b'\0' not in lab[:-1] and sz <= e - b, hex(b)
        out.append((b, len(offs), offs, e, sz, TABLE + 4 * i))
    return out


if __name__ == '__main__':
    import os
    d = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'work', 'disc', 'SCR.BIN'), 'rb').read()
    B = blocks(d)
    bad = [hex(b) for b, n, o, e in B if b + o[-1] >= e]
    print('묶음 %d · 마지막 스크립트가 다음 묶음을 넘는 것 %s' % (len(B), bad))
