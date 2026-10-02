# -*- coding: utf-8 -*-
r"""스테이트 VDP1 스프라이트 텍스처의 출처 찾기 — 1CPT 해제본 + 날 파일에서 텍스처 바이트 검색
  python tools/srcfind.py <상태이름> [최소바이트]
"""
import os, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import cpt, vdp1

_POOL = None


def pool():
    global _POOL
    if _POOL is None:
        _POOL = []
        for f, p, e, n in cpt.scan():
            d = open(os.path.join(cpt.DISC, f), 'rb').read()
            _POOL.append(('%s@%X' % (f, p), cpt.unpack(d, p)[0]))
        for f in sorted(os.listdir(cpt.DISC)):
            if f.endswith(('.BIN', '.KNJ', '.FNT', '.MWI', '.KPD')):
                _POOL.append((f, open(os.path.join(cpt.DISC, f), 'rb').read()))
    return _POOL


def find(tex):
    """텍스처에서 0 아닌 바이트가 많은 32B 조각으로 검색 → [(이름, 텍스처 시작 위치)]"""
    hits = []
    for k in range(0, max(1, len(tex) - 32), 16):
        c = tex[k:k + 32]
        if sum(1 for x in c if x) < 12:
            continue
        for nm, d in pool():
            i = d.find(c)
            while i >= 0:
                hits.append((nm, i - k)); i = d.find(c, i + 1)
        if hits:
            return sorted(set(hits))
    return hits


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    s = sys.argv[1]; v = open(os.path.join(ROOT, 'work', 'mem', s, 'VDP1_VRAM.bin'), 'rb').read()
    for i, (a, c) in enumerate(vdp1.walk(v)):
        if c[0] & 0xF not in (0, 1, 2):
            continue
        mode, src, w, h = vdp1.tex(v, c)
        bpp = {0: 4, 1: 4, 2: 8, 3: 8, 4: 8, 5: 16}.get(mode, 4)
        n = w * h * bpp // 8
        if not n:
            continue
        hs = find(v[src:src + n])
        xy = [x - 0x10000 if x & 0x8000 else x for x in c[6:8]]
        print('%3d src=%05X %3dx%-3d m%d colr=%04X xy=%s → %s' % (i, src, w, h, mode, c[3], xy, ' '.join('%s+%X' % h for h in hs[:4]) or '-'))
