# -*- coding: utf-8 -*-
r"""VDP2 NBG 면 그리기(이 게임 설정: 셀 1×1, 패턴 이름 2워드, 면 64×64 = 0x4000, 맵 0x1C‥0x1F → VRAM 0x70000+n×0x4000)
  python tools/nbg.py s3   → work/mem/s3/nbg0‥3.png (512×512, 16색은 CRAM 팔레트 그대로)
  2워드 이름: 첫 워드 상위 = 플래그·팔레트(bit 6‥0 팔레트 번호), 둘째 워드 = 문자 번호(×0x20 = VRAM 주소, 4bpp)
"""
import os, struct, sys
from PIL import Image
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(s):
    p = os.path.join(ROOT, 'work', 'mem', s)
    return (open(os.path.join(p, 'VDP2_VRAM.bin'), 'rb').read(), open(os.path.join(p, 'CRAM.bin'), 'rb').read())


def color(cram, idx):
    c = struct.unpack_from('>H', cram, (idx * 2) % len(cram))[0]
    return ((c & 31) << 3, (c >> 5 & 31) << 3, (c >> 10 & 31) << 3)


def cells(v, n):
    base = 0x70000 + n * 0x4000
    for cy in range(64):
        for cx in range(64):
            w0, w1 = struct.unpack_from('>HH', v, base + (cy * 64 + cx) * 4)
            yield cx, cy, w0, w1


def render(s, n):
    v, cram = load(s); im = Image.new('RGB', (512, 512))
    for cx, cy, w0, w1 in cells(v, n):
        ch = w1 & 0x7FFF; pal = w0 & 0x7F; a = ch * 0x20
        hf = w0 & 0x4000; vf = w0 & 0x8000
        for y in range(8):
            for x in range(8):
                b = v[(a + y * 4 + x // 2) % len(v)]; p = b >> 4 if x % 2 == 0 else b & 15
                if p:
                    xx = 7 - x if hf else x; yy = 7 - y if vf else y
                    im.putpixel((cx * 8 + xx, cy * 8 + yy), color(cram, pal * 16 + p))
    im.save(os.path.join(ROOT, 'work', 'mem', s, 'nbg%d.png' % n))


if __name__ == '__main__':
    for n in range(4):
        render(sys.argv[1], n)
