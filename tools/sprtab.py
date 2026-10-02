# -*- coding: utf-8 -*-
r"""0.BIN 스프라이트 서술자 표 — 항목 16 B: u16 폭 · u16 높이 · i16 원점x · i16 원점y · u16 깃발 · u16 _ · u32 텍스처 오프셋(그 표가 쓰는 1CPT 해제본 기준)
  python tools/sprtab.py <표 시작 hex> <개수> <1CPT 출처 예: SYS.BIN@180> [팔레트 출처 파일:오프셋 hex] → work/sheet/<표>.png (번호 붙은 일람)
"""
import os, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import cpt
D0 = os.path.join(cpt.DISC, '0.BIN')


def table(start, n):
    d = open(D0, 'rb').read()
    return [dict(zip(('w', 'h', 'ox', 'oy', 'flag', 'z', 'off'), struct.unpack_from('>HHhhHHI', d, start + 16 * k))) | {'at': start + 16 * k} for k in range(n)]


def blob(spec):
    f, p = spec.split('@'); d = open(os.path.join(cpt.DISC, f), 'rb').read()
    return cpt.unpack(d, int(p, 16))[0]


def render(b, e, scale=2):
    from PIL import Image
    w, h = e['w'], e['h']; im = Image.new('L', (w, h))
    for y in range(h):
        for x in range(w):
            i = e['off'] + (y * w + x) // 2
            if i >= len(b): continue
            p = b[i] >> 4 if x % 2 == 0 else b[i] & 15
            im.putpixel((x, y), 40 + p * 13 if p else 0)
    return im.resize((w * scale, h * scale), 0)


if __name__ == '__main__':
    from PIL import Image, ImageDraw
    st, n, spec = int(sys.argv[1], 16), int(sys.argv[2]), sys.argv[3]
    T = table(st, n); b = blob(spec)
    ims = [render(b, e) for e in T]
    W = max(i.width for i in ims) + 90; H = sum(i.height + 6 for i in ims)
    sheet = Image.new('L', (W, H), 20); dr = ImageDraw.Draw(sheet); y = 0
    for k, (e, im) in enumerate(zip(T, ims)):
        dr.text((2, y), '%d %X %dx%d f%X' % (k, e['off'], e['w'], e['h'], e['flag']), fill=255)
        sheet.paste(im, (88, y)); y += im.height + 6
    od = os.path.join(ROOT, 'work', 'sheet'); os.makedirs(od, exist_ok=True)
    p = os.path.join(od, '%X.png' % st); sheet.save(p); print(p, len(T))
