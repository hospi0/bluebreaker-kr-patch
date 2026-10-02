# -*- coding: utf-8 -*-
r"""타이틀 화면 일본어(부제 «～剣よりも微笑みを～»·작은 «ブルーブレイカー») 한글화 (2026-10-02)
  그림 = BG.BIN «1SBG» 덩어리 @0x2C3000(1CPT 와 같은 코덱, 머리 '1SBG'+u32 크기) → 풀면 u16 폭 320 · u16 높이 240 · 팔레트 256×RGB555 · 320×240 8bpp
  두 글 모두 «밝은 연기 띠 위 어두운 글자» → ①띠 안 어두운 글자 픽셀을 주변 밝은 색으로 메움(반복 평균) ②같은 어두운 색으로 한글(4배 그려 덮임 비율로 섞음) ③팔레트 최근접 색
  덩어리 자리 = 0x800 정렬, 다음 덩어리 0x2CB800 → 새 압축 ≤ 0x8800.
  python tools/title.py   → work/title/title_ko.png(미리보기, 원본|새것)
"""
import os, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import cpt
from PIL import Image, ImageDraw, ImageFont

BG = os.path.join(ROOT, 'work', 'disc', 'BG.BIN')
AT, ROOM = 0x2C3000, 0x8800
MJ = r'C:\claude\utils\font\nanum-myeongjo\NanumMyeongjoExtraBold.ttf'
GO = r'C:\claude\utils\font\nanum-gothic\NanumGothicExtraBold.ttf'
# (상자 x0, y0, x1, y1(포함), 글, 글꼴, 글자 높이 px, 지울 어두움 문턱)
JOBS = [(57, 109, 252, 122, '~ 검보다도 미소를 ~', MJ, 16, 80, 2),
        (182, 56, 275, 66, '블루 브레이커', GO, 10, 115, 1)]   # 끝 = 4배 그림 획 굵기


def unpack(d, p):
    assert d[p:p + 4] == b'1SBG'
    size = struct.unpack_from('>I', d, p + 4)[0]; i = p + 8; out = bytearray()
    while len(out) < size:
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


def pal_of(u):
    return [((c & 31) << 3, (c >> 5 & 31) << 3, (c >> 10 & 31) << 3) for c in struct.unpack_from('>256H', u, 4)]


def lum(c):
    return sum(c) // 3


def nearest(pal, c, cache={}):
    k = (id(pal), c)
    if k not in cache:
        cache[k] = min(range(256), key=lambda i: (pal[i][0] - c[0]) ** 2 + (pal[i][1] - c[1]) ** 2 + (pal[i][2] - c[2]) ** 2)
    return cache[k]


def process(u):
    pal = pal_of(u)
    px = bytearray(u[516:516 + 320 * 240])
    rgb = [list(pal[p]) for p in px]
    for x0, y0, x1, y1, text, fn, hpx, thr, sw in JOBS:
        # ① 어두운 글자 픽셀 → 주변 밝은 색 평균으로 메움
        mask = {(x, y) for y in range(y0, y1 + 1) for x in range(x0, x1 + 1) if lum(rgb[y * 320 + x]) < thr}
        ink = min(((lum(rgb[y * 320 + x]), px[y * 320 + x]) for x, y in mask))[1]   # 글자색 = 가장 어두운 색
        todo = set(mask)
        while todo:
            done = {}
            for x, y in todo:
                ns = [rgb[(y + dy) * 320 + x + dx] for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                      if (dx or dy) and 0 <= x + dx < 320 and 0 <= y + dy < 240 and (x + dx, y + dy) not in todo]
                if len(ns) >= 2:
                    done[(x, y)] = [sum(c[i] for c in ns) // len(ns) for i in range(3)]
            if not done:
                break
            for (x, y), c in done.items():
                rgb[y * 320 + x] = c
            todo -= set(done)
        # ② 한글 — 4배로 그려 덮임 비율로 글자색과 섞음, 상자 가운데
        S = 4
        f = ImageFont.truetype(fn, hpx * S)
        bb = f.getbbox(text, stroke_width=sw)
        tw, th = bb[2] - bb[0], bb[3] - bb[1]
        W, H = (x1 - x0 + 1), (y1 - y0 + 1)
        if tw > W * S:
            f = ImageFont.truetype(fn, int(hpx * S * W * S / tw)); bb = f.getbbox(text, stroke_width=sw); tw, th = bb[2] - bb[0], bb[3] - bb[1]
        im = Image.new('L', (W * S, H * S), 0)
        ImageDraw.Draw(im).text(((W * S - tw) // 2 - bb[0], (H * S - th) // 2 - bb[1]), text, font=f, fill=255, stroke_width=sw, stroke_fill=255)
        im = im.resize((W, H), Image.BOX)
        ic = pal[ink]
        for y in range(H):
            for x in range(W):
                a = im.getpixel((x, y)) / 255
                if a > 0.08:
                    c = rgb[(y0 + y) * 320 + x0 + x]
                    rgb[(y0 + y) * 320 + x0 + x] = [int(c[i] * (1 - a) + ic[i] * a) for i in range(3)]
        for y in range(max(0, y0 - 1), min(240, y1 + 2)):
            for x in range(max(0, x0 - 1), min(320, x1 + 2)):
                px[y * 320 + x] = nearest(pal, tuple(rgb[y * 320 + x]))
    return u[:516] + bytes(px) + u[516 + 320 * 240:]


def build():
    """→ {'BG.BIN': bytes}"""
    d = bytearray(open(BG, 'rb').read())
    u, _ = unpack(bytes(d), AT)
    new = process(u)
    c = b'1SBG' + cpt.pack(new)[4:]
    if len(c) > ROOM:
        raise SystemExit('⛔타이틀 그림 압축 %d > 자리 %d' % (len(c), ROOM))
    d[AT:AT + len(c)] = c
    d[AT + len(c):AT + ROOM] = bytes(ROOM - len(c))
    chk, _ = unpack(bytes(d), AT)
    assert chk == new
    print('타이틀 그림 %d B / 자리 %d B' % (len(c), ROOM))
    return {'BG.BIN': bytes(d)}


def preview():
    d = open(BG, 'rb').read()
    u, _ = unpack(d, AT)
    pal = pal_of(u)
    out = Image.new('RGB', (640, 240))
    for k, b in enumerate((u, process(u))):
        im = Image.new('P', (320, 240)); im.putpalette([x for c in pal for x in c]); im.putdata(b[516:516 + 76800])
        out.paste(im.convert('RGB'), (k * 320, 0))
    out.resize((1280, 480), Image.NEAREST).save(os.path.join(ROOT, 'work', 'title', 'title_ko.png'))
    out.crop((0, 40, 640, 130)).resize((1920, 270), Image.NEAREST).save(os.path.join(ROOT, 'work', 'title', 'title_ko_crop.png'))


if __name__ == '__main__':
    preview()
