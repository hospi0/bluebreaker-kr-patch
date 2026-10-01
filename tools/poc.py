# -*- coding: utf-8 -*-
r"""PoC (2026-10-01) — SCR.BIN 0x41FD5 디자 대사 «ディーザ「よーし、自己紹介はすんRT　だな。» (42 B, «{»…«PC}» 사이)를
  같은 42 B 한국어로: «디자「좋아、자기소개는　다RT　끝난　거지。».
  한글 14자 = 4.KNJ 의 JIS 82구 1‥14점(2수준 한자, 거의 안 씀) 칸에 갈무리14(16×16 안 x 1‥, y 1‥)로 그리고 그 SJIS 로 씀.
  KNJ 번호 = 128 + (구−1)×94 + (점−1), 글자 32 B(16줄 × 2 B, 비트 15 = 왼쪽).
  python tools/poc.py → work/out/…(Track 1).bin
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, r'C:\claude\project\anearth-kr-patch\tools')
import bdf
sys.path.insert(0, HERE)
import disc, iso

GAL = r'C:\claude\utils\font\Galmuri-v2.40.3\Galmuri14.bdf'
OUT = os.path.join(ROOT, 'work', 'out', os.path.basename(disc.ROM))
OLD = 'ディーザ「よーし、自己紹介はすんRT　だな。'
NEW = '디자「좋아、자기소개는　다RT　끝난　거지。'
KU = 82


def sjis_of(ku, ten):
    return bytes([0xA0 + ku, 0xA0 + ten]).decode('euc_jp').encode('cp932')


def glyph(F, ch):
    pts, _ = F.draw(ch, 0, 0)
    xs = [x for x, _ in pts]; ys = [y for _, y in pts]
    ox = (16 - (max(xs) - min(xs) + 1)) // 2 - min(xs); oy = (16 - (max(ys) - min(ys) + 1)) // 2 - min(ys)
    rows = [0] * 16
    for x, y in pts:
        X, Y = x + ox, y + oy
        if 0 <= X < 16 and 0 <= Y < 16:
            rows[Y] |= 0x8000 >> X
    return b''.join(r.to_bytes(2, 'big') for r in rows)


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    F = bdf.Font(GAL)
    knj = bytearray(open(os.path.join(ROOT, 'work', 'disc', '4.KNJ'), 'rb').read())
    scr = bytearray(open(os.path.join(ROOT, 'work', 'disc', 'SCR.BIN'), 'rb').read())
    hang = []
    for ch in NEW:
        if '가' <= ch <= '힣' and ch not in hang:
            hang.append(ch)
    code = {}
    for t, ch in enumerate(hang, 1):
        i = 128 + (KU - 1) * 94 + (t - 1)
        knj[i * 32:i * 32 + 32] = glyph(F, ch); code[ch] = sjis_of(KU, t)
    old = OLD.encode('cp932')
    new = b''.join(code[ch] if ch in code else ch.encode('cp932') for ch in NEW.replace('RT', '\x00')).replace(b'\x00', b'RT')
    n = scr.count(old); assert n >= 1
    assert len(new) == len(old), (len(new), len(old))
    scr[:] = scr.replace(old, new)
    print('한글 %d자 → KNJ %d구 · 대사 %d B 제자리 %d곳' % (len(hang), KU, len(new), n))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    iso.patch(disc.ROM, OUT, {'4.KNJ': bytes(knj), 'SCR.BIN': bytes(scr)})
    print('→', OUT)


if __name__ == '__main__':
    main()
