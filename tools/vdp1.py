# -*- coding: utf-8 -*-
r"""VDP1 명령 표 훑기 — python tools/vdp1.py s4 [png]
  명령 32 B: CTRL LINK PMOD COLR SRCA SIZE XA YA XB YB XC YC XD YD GRDA _
  png 를 주면 일반 스프라이트(CTRL&0xF==0)의 텍스처를 work/mem/<s>/spr_<번호>.png 로 그린다(4bpp 는 0=검정,그 외 흰색 명암)
"""
import os, struct, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KIND = {0: 'normal', 1: 'scaled', 2: 'distort', 4: 'poly', 5: 'polyline', 6: 'line', 8: 'uclip', 9: 'sysclip', 10: 'local', }


def walk(v):
    a = 0; seen = set(); out = []; stack = []
    while a not in seen and len(out) < 2000:
        seen.add(a)
        c = struct.unpack_from('>16H', v, a)
        ctrl = c[0]
        if ctrl & 0x8000:
            break
        jp = (ctrl >> 12) & 7
        if not ctrl & 0x4000:
            out.append((a, c))
        nxt = a + 32
        if jp == 1: nxt = c[1] * 8
        elif jp == 2: stack.append(a + 32); nxt = c[1] * 8
        elif jp == 3: nxt = stack.pop() if stack else a + 32
        a = nxt
    return out


def tex(v, c):
    pm = c[2]; mode = (pm >> 3) & 7; src = c[4] * 8; w = ((c[5] >> 8) & 0x3F) * 8; h = c[5] & 0xFF
    return mode, src, w, h


def main():
    s = sys.argv[1]; v = open(os.path.join(ROOT, 'work', 'mem', s, 'VDP1_VRAM.bin'), 'rb').read()
    cmds = walk(v)
    for i, (a, c) in enumerate(cmds):
        k = KIND.get(c[0] & 0xF, hex(c[0] & 0xF))
        mode, src, w, h = tex(v, c)
        xy = [x - 0x10000 if x & 0x8000 else x for x in c[6:14]]
        print('%3d %05X %-8s pm=%04X colr=%04X src=%05X %3dx%-3d xy=%s' % (i, a, k, c[2], c[3], src, w, h, xy[:4]))
    if len(sys.argv) > 2:
        from PIL import Image
        for i, (a, c) in enumerate(cmds):
            if c[0] & 0xF not in (0, 1, 2):
                continue
            mode, src, w, h = tex(v, c)
            if not w or not h:
                continue
            im = Image.new('L', (w, h))
            for y in range(h):
                for x in range(w):
                    if mode in (0, 1):
                        b = v[(src + (y * w + x) // 2) % len(v)]; p = (b >> 4) if x % 2 == 0 else b & 15
                        im.putpixel((x, y), p * 17)
                    elif mode in (2, 3, 4):
                        im.putpixel((x, y), v[(src + y * w + x) % len(v)])
                    else:
                        p = struct.unpack_from('>H', v, (src + (y * w + x) * 2) % len(v))[0]
                        im.putpixel((x, y), ((p & 31) + (p >> 5 & 31) + (p >> 10 & 31)) * 8 // 3 * 255 // 248 if p else 0)
            im.save(os.path.join(ROOT, 'work', 'mem', s, 'spr_%03d.png' % i))


if __name__ == '__main__':
    main()
