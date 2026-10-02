# -*- coding: utf-8 -*-
r"""일기 제목 그림 (NIKKI.BIN 0x40 1CPT, 서술자 표 0.BIN 0x70F2C) — 2026-10-02
  0: «俺と魔王» 296×64 붓글씨(색 1=속 → 5=가장자리 안티) + 오른쪽 아래 도장 «けいん»(색 7·8)
     → «나와 마왕»(연성체, 안티를 1‥5 로) + 도장 안 «케/인»(갈무리7, 색 8)
  1: «俺の♥愛の記録(メモリー)» 256×64 틀(색 4 바탕·6 테두리) 안 글자 = 노랑 7 + 그림자 1·2, «愛» = 분홍 A + 그림자 1·2, 루비 = 노랑 7
     → «나의 사랑의 기록»(검은고딕) + «사랑» 분홍 + 하트 그대로 + 루비 «메모리»(갈무리9)
  from gfx_nikki import redraw; new_blob = redraw(blob)
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from PIL import Image, ImageDraw, ImageFont
import gfx

FD = 'C:/claude/utils/font/'


def tt(path, size, s):
    """TTF 글자 → (명암 0‥255 그림, 잉크 상자)"""
    f = ImageFont.truetype(FD + path, size)
    l, t, r, b = f.getbbox(s)
    im = Image.new('L', (r - l + 4, b - t + 4)); ImageDraw.Draw(im).text((2 - l, 2 - t), s, font=f, fill=255)
    return im


def title0(P):
    """나와 마왕"""
    h = len(P); w = len(P[0])
    N = [r[:] for r in P]
    for y in range(h):
        for x in range(0, 276):
            N[y][x] = 0
    from PIL import ImageFilter
    im = tt('yeonsung/YeonSung-Regular.ttf', 66, '나와 마왕').filter(ImageFilter.MaxFilter(3))   # 붓글씨 굵게
    if im.width > 270:
        im = im.resize((270, im.height * 270 // im.width), Image.LANCZOS)
    ox = (276 - im.width) // 2; oy = (h - im.height) // 2
    for y in range(im.height):
        for x in range(im.width):
            v = im.getpixel((x, y))
            if v > 40 and 0 <= y + oy < h:
                N[y + oy][x + ox] = 1 if v > 200 else 2 if v > 160 else 3 if v > 120 else 4 if v > 80 else 5
    # 도장(x 280‥295, y 43‥60) 안 «けいん» → «케/인»
    for y in range(45, 59):
        for x in range(282, 294):
            if N[y][x] in (7, 8):
                N[y][x] = 0
    for k, ch in enumerate('케인'):
        pts, cw = gfx.text_mask('Galmuri7', ch)
        ys = [p[1] for p in pts]
        for x, y in pts:
            N[46 + k * 7 + y - min(ys)][288 - cw // 2 + x] = 8
    return N


def shade(N, M, ink, x0, x1, y0, y1):
    """잉크 M(점 집합)을 ink 색으로, 오른쪽·아래 1px 그림자 1, 그 바깥 1px 2"""
    for x, y in M:
        N[y][x] = ink
    for x, y in M:
        for dx, dy, c in ((1, 0, 1), (0, 1, 1), (1, 1, 1), (2, 1, 2), (1, 2, 2), (2, 2, 2)):
            q = (x + dx, y + dy)
            if q not in M and x0 <= q[0] <= x1 and y0 <= q[1] <= y1 and N[q[1]][q[0]] in (4, 2):
                N[q[1]][q[0]] = c


def title1(P):
    """나의 사랑의 기록 (+ 루비 메모리)"""
    N = [r[:] for r in P]
    X0, X1, Y0, Y1 = 12, 243, 9, 51                   # 틀 안쪽
    heart = {(x, y): P[y][x] for y in range(9, 24) for x in range(82, 104) if P[y][x] in (8, 9, 10, 3)}
    for y in range(Y0, Y1 + 1):
        for x in range(X0, X1 + 1):
            N[y][x] = 4
    for y in range(Y1 + 1, Y1 + 4):                     # 틀 선 근처까지 내려온 원문 글자 그림자 찌꺼기
        for x in range(X0, X1 + 1):
            if N[y][x] in (1, 2, 3, 7, 8, 9, 10):
                N[y][x] = 4
    parts = [('나의 ', 7), ('사랑', 10), ('의 기록', 7)]
    ims = [(tt('logo/BlackHanSans.ttf', 29, s.strip() or ' '), c, s) for s, c in parts]
    gap = 6
    total = sum(im.width for im, _, _ in ims) + gap * 2
    x = (X0 + X1 + 1 - total) // 2; base = 21
    boxes = []
    for im, c, s in ims:
        M = {(x + i, base + j) for j in range(im.height) for i in range(im.width) if im.getpixel((i, j)) > 110}
        M = {(a, b) for a, b in M if X0 <= a <= X1 - 2 and Y0 <= b <= Y1 - 2}
        shade(N, M, c, X0, X1, Y0, Y1)
        boxes.append((x, x + im.width, s)); x += im.width + gap
    # 하트 = «사랑» 위 가운데
    hx = (boxes[1][0] + boxes[1][1]) // 2 - 93
    for (a, b), c in heart.items():
        if X0 <= a + hx <= X1:
            N[b][a + hx] = c
    # 루비 «메모리» = «기록» 위
    pts, rw = gfx.text_mask('Galmuri9', '메모리')
    gx = (boxes[2][0] + boxes[2][1]) // 2 + 14 - rw // 2
    ys = [p[1] for p in pts]
    M = {(gx + px, 9 + py - min(ys)) for px, py in pts}
    shade(N, M, 7, X0, X1, Y0, Y1)
    return N


def redraw(blob):
    nb = bytearray(blob)
    for off, w, h, fn in ((0, 296, 64, title0), (0x2500, 256, 64, title1)):
        P = gfx.getpx(blob, off, w, h); N = fn(P)
        gfx.putpx(nb, off, w, h, N)
    return bytes(nb)


if __name__ == '__main__':
    import cpt
    raw = open(os.path.join(cpt.DISC, 'NIKKI.BIN'), 'rb').read(); blob, e = cpt.unpack(raw, 0x40)
    nb = redraw(blob)
    pal = [(30, 30, 40), (250, 240, 200), (200, 190, 160), (150, 140, 120), (100, 95, 85), (60, 58, 55), (140, 110, 70), (250, 230, 40), (200, 60, 120), (230, 90, 150), (250, 110, 170), (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0)]
    pal[4] = (90, 60, 30); pal[1] = (40, 20, 10); pal[2] = (70, 40, 20)
    out = Image.new('RGB', (600, 280))
    for k, (off, w, h) in enumerate(((0, 296, 64), (0x2500, 256, 64))):
        for j, b in enumerate((blob, nb)):
            P = gfx.getpx(b, off, w, h)
            for y in range(h):
                for x in range(w):
                    out.putpixel((j * 300 + x, k * 140 + y * 2 // 2), pal[P[y][x]])
    out = out.resize((1200, 560), 0)
    p = os.path.join(os.path.dirname(HERE), 'work', 'sheet', 'gfx_NIKKI.png'); out.save(p); print(p, len(cpt.pack(nb)), e - 0x40)
