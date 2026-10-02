# -*- coding: utf-8 -*-
r"""그림 글자 한글화 (2026-10-02) — work/ko/gfx.tsv(묶음·번호·원문·번역) → 1CPT 그림 묶음 안 스프라이트를 같은 크기·같은 색 번호로 다시 그림
  스프라이트 위치·크기 = 0.BIN 서술자 표(tools/sprtab.py) — 크기는 그대로 두고 글자만 바꾼다(VRAM 배치·표 수정 0).
  색 = 원본에서 잰 색 번호: 외곽선형(글자 + 8방향 테두리) / 그림자형(글자 + 오른쪽·아래 그림자) / 줄마다 다른 글자색(그러데이션)은 원본 그 줄의 최빈 색.
  글꼴 = 갈무리11(16px 칸) → 넘치면 갈무리11 Condensed / 8px 칸 = 갈무리7. 칸 안 세로 위치 = 원본 글자 잉크 범위의 가운데.
  1CPT 는 다시 압축(tools/cpt.py)해 원래 자리에 — 원본 압축 길이 이하면 0 으로 채워 파일 크기 유지, 넘치면 빌드 실패(뒤에 다른 데이터가 붙은 파일 보호).
  python tools/gfx.py [--preview]   → files() 를 insert.py 가 부른다 / --preview = work/sheet/gfx_<묶음>.png (원본 | 새것)
"""
import os, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, r'C:\claude\project\anearth-kr-patch\tools')
import bdf, cpt, sprtab

G = 'C:/claude/utils/font/Galmuri-v2.40.3/'
_F = {}


def font(name):
    if name not in _F:
        _F[name] = bdf.Font(G + name + '.bdf')
    return _F[name]


# 묶음: 1CPT 출처 · 서술자 표(시작, 개수) 또는 단일 그림(폭, 높이)
GROUPS = {
    'GLD': dict(src=('GLD.BIN', 0x40), tab=(0x5F794, 57)),
    'SYS': dict(src=('SYS.BIN', 0x180), tab=(0x67730, 178)),
    'ST': dict(src=('ST.BIN', 0x300), tab=(0x672E8, 64)),
    'CONF': dict(src=('CONFSP.CPT', 0), one=(136, 16)),
    'KAISOU': dict(src=('KAISOUSP.CPT', 0), one=(80, 16)),
    'TITL': dict(src=('TITLSP.CPT', 0), tab=(0x7140C, 48)),
}
BIG = ['Galmuri11', 'Galmuri11-Condensed']
HUGE = ['Galmuri14', 'Galmuri11', 'Galmuri11-Condensed']        # 제목·타이틀 메뉴(원본 글자 14~15px)
SMALL = ['Galmuri7']


def style(g, k):
    """→ dict(kind, ink(None=줄마다), edge, align, region, fonts)"""
    if g in ('GLD', 'ST'):
        return dict(kind='outline', ink=0xF, edge=0xB, align='left', fonts=BIG)
    if g == 'SYS':
        if 7 <= k <= 71:
            return dict(kind='outline', ink=0x2, edge=0x3, align='left', fonts=BIG)
        if 102 <= k <= 113:
            return dict(kind='shadow', ink=None, edge=0xF, align='left', fonts=HUGE, bold=True)
        if 134 <= k <= 141:
            return dict(kind='shadow', ink=0xF, edge=0x1, align='center' if k >= 136 else 'left', fonts=BIG)
        if 162 <= k <= 174:
            return dict(kind='shadow', ink=0xF, edge=0x1, align='left', fonts=SMALL)
    if g == 'CONF':
        return dict(kind='shadow', ink=None, edge=0xF, align='center', region=(19, 114), fonts=HUGE, bold=True)
    if g == 'KAISOU':
        return dict(kind='shadow', ink=None, edge=0xF, align='center', region=(19, 61), fonts=HUGE, bold=True)
    if g == 'TITL':
        if 26 <= k <= 32:
            return dict(kind='outline', ink=0x1, edge=0x4, align='left', fonts=BIG)
        if 33 <= k <= 46:
            return dict(kind='outline', ink=None, edge=0x4, align='left', fonts=HUGE, pair=True, **({'region': (0, 58)} if k == 45 else {}))   # 45 = «おまけ♥» 하트 남김
        if k == 47:
            return dict(kind='shadow', ink=None, edge=0xF, align='center', region=(20, 124), fonts=HUGE, bold=True)
    raise KeyError((g, k))


def getpx(b, off, w, h):
    return [[(b[off + (y * w + x) // 2] >> 4) if x % 2 == 0 else (b[off + (y * w + x) // 2] & 15) for x in range(w)] for y in range(h)]


def putpx(b, off, w, h, P):
    for y in range(h):
        for x in range(0, w, 2):
            b[off + (y * w + x) // 2] = (P[y][x] << 4) | P[y][x + 1]


def text_mask(fn, s, gap=0, space=None):
    """→ (점 집합(x,y — y 는 글꼴 윗선 기준), 잉크 폭)"""
    F = font(fn); pts = set(); x = 0
    for ch in s:
        c = F.g.get(ord(ch))
        if c is None:
            raise SystemExit('⛔글꼴 %s 에 %r 없음' % (fn, ch))
        w, h, xo, yo = c['bbx']
        top = F.asc - (h + yo)
        for r, hx in enumerate(c['rows']):
            v = int(hx, 16); n = len(hx) * 4
            for i in range(w):
                if (v >> (n - 1 - i)) & 1:
                    pts.add((x + xo + i, top + r))
        x += (space if (ch == ' ' and space is not None) else c['dw']) + (gap if ch != ' ' else 0)
    if not pts:
        return pts, 0
    mx = min(p[0] for p in pts)
    pts = {(px - mx, py) for px, py in pts}
    return pts, max(p[0] for p in pts) + 1


def fit(st, s, avail):
    for fn in st['fonts']:
        for space, gap in ((None, 0), (3, 0), (2, -1)):
            pts, w = text_mask(fn, s, gap + (1 if st.get('bold') else 0), space)
            if st.get('bold'):                                  # 굵게 = 오른쪽으로 1px 번짐
                pts = pts | {(x + 1, y) for x, y in pts}; w += 1
            if w <= avail:
                return pts, w, fn
    raise SystemExit('⛔칸에 안 들어감 %r (가용 %dpx)' % (s, avail))


def draw(P, s, st):
    """원본 픽셀 P(줄 목록)에 글자 s 를 다시 그린 새 픽셀"""
    h = len(P); w = len(P[0])
    x0, x1 = st.get('region', (0, w - 1))
    edge = st['edge']
    ink_px = [(x, y) for y in range(h) for x in range(x0, x1 + 1) if P[y][x] not in (0, edge)]
    if not ink_px:
        raise SystemExit('⛔원본 잉크 없음')
    t = min(y for _, y in ink_px); bt = max(y for _, y in ink_px)
    lft = min(x for x, _ in ink_px)
    # 줄마다 글자색(그러데이션) — 그 줄 최빈 색, 없으면 가까운 줄
    rows = {}
    for y in range(h):
        cnt = {}
        for x in range(x0, x1 + 1):
            c = P[y][x]
            if c not in (0, edge):
                cnt[c] = cnt.get(c, 0) + 1
        if cnt:
            rows[y] = max(cnt, key=cnt.get)

    def ink(y):
        if st['ink'] is not None:
            return st['ink']
        k = min(rows, key=lambda r: abs(r - y))
        return rows[k]
    pad = 2 if st['kind'] == 'outline' else 1
    avail = (x1 - x0 + 1) - pad
    pts, tw, fn = fit(st, s, avail)
    ys = [p[1] for p in pts]; gh = max(ys) - min(ys) + 1
    oy = t + max(0, ((bt - t + 1) - gh) // 2) - min(ys)
    if oy + max(ys) + (1 if pad else 0) >= h:
        oy = h - 1 - max(ys) - (1 if st['kind'] == 'outline' else 1)
    if oy + min(ys) < (1 if st['kind'] == 'outline' else 0):
        oy = (1 if st['kind'] == 'outline' else 0) - min(ys)
    if st['align'] == 'center':
        ox = x0 + ((x1 - x0 + 1) - tw) // 2
    else:
        ox = max(x0 + (1 if st['kind'] == 'outline' else 0), min(lft, x1 + 1 - pad - tw + (1 if st['kind'] == 'outline' else 0)))
    M = {(x + ox, y + oy) for x, y in pts}
    N = [row[:] for row in P]
    for y in range(h):
        for x in range(x0, x1 + 1):
            N[y][x] = 0
    for y in range(h):
        for x in range(x0, x1 + 1):
            if (x, y) in M:
                N[y][x] = ink(y)
            elif st['kind'] == 'outline' and any((x + dx, y + dy) in M for dx in (-1, 0, 1) for dy in (-1, 0, 1)):
                N[y][x] = edge
            elif st['kind'] == 'shadow' and ((x - 1, y) in M or (x, y - 1) in M or (x - 1, y - 1) in M):
                N[y][x] = edge
    return N, fn


# ST.BIN 44번 «PARTY DATA» 판(288×72) 안 라벨 — (x0, x1, 윗줄, 아랫줄, 번역): 칸을 바탕색 3 으로 지우고 글자색 9(외곽선 없음)로. 쌍점·숫자·G 는 그대로
PANEL = [(6, 45, 15, 24, '현재지'), (7, 31, 31, 40, '요일'), (8, 31, 47, 56, '남은'), (83, 109, 47, 56, '주기'), (137, 174, 47, 56, '소지금')]


def panel(P):
    N = [r[:] for r in P]
    for x0, x1, r0, r1, s in PANEL:
        for y in range(r0, r1 + 1):
            for x in range(x0, x1 + 1):
                N[y][x] = 3
        pts, w = text_mask('Galmuri11', s)
        if w > x1 - x0 + 4:
            raise SystemExit('⛔판 라벨 넘침 %r' % s)
        ys = [q[1] for q in pts]; oy = r0 - min(ys)
        for x, y in pts:
            N[y + oy][x + x0] = 9
    return N


def load_tsv():
    out = {}
    for l in open(os.path.join(ROOT, 'work', 'ko', 'gfx.tsv'), encoding='utf-8').read().split('\n')[1:]:
        if l.strip():
            g, k, src, ko = l.split('\t')
            out.setdefault(g, []).append((int(k), src, ko))
    return out


def build(preview=False):
    """→ {파일이름: 새 바이트}"""
    tsv = load_tsv(); files = {}; prev = {}
    for g, items in tsv.items():
        cfg = GROUPS[g]; fname, p = cfg['src']
        raw = open(os.path.join(cpt.DISC, fname), 'rb').read()
        blob, end = cpt.unpack(raw, p); nb = bytearray(blob)
        if 'tab' in cfg:
            T = sprtab.table(*cfg['tab'])
        else:
            T = [dict(off=0, w=cfg['one'][0], h=cfg['one'][1])]
        shots = []
        for k, src, ko in items:
            st = style(g, k); e = T[k]
            if st.get('pair'):                                  # 위·아래 반쪽(80×8 두 장) = 한 낱말 80×16
                e2 = T[k + 1]; w = e['w']
                P = getpx(blob, e['off'], w, e['h']) + getpx(blob, e2['off'], w, e2['h'])
                N, fn = draw(P, ko, st)
                putpx(nb, e['off'], w, e['h'], N[:e['h']]); putpx(nb, e2['off'], w, e2['h'], N[e['h']:])
            else:
                P = getpx(blob, e['off'], e['w'], e['h'])
                N, fn = draw(P, ko, st)
                putpx(nb, e['off'], e['w'], e['h'], N)
            shots.append((k, P, N, fn, ko))
        if g == 'ST':
            e = T[44]; P = getpx(blob, e['off'], e['w'], e['h']); N = panel(P)
            putpx(nb, e['off'], e['w'], e['h'], N); shots.append((44, P, N, 'Galmuri11', 'PARTY DATA'))
        comp = cpt.pack(bytes(nb))
        old = end - p
        if len(comp) > old:
            raise SystemExit('⛔%s 압축 %d B > 원래 %d B' % (fname, len(comp), old))
        files[fname] = raw[:p] + comp + bytes(old - len(comp)) + raw[end:]
        prev[g] = shots
        print('%-12s 스프라이트 %3d · 압축 %d/%d B' % (fname, len(items), len(comp), old))
    # 일기 제목(NIKKI.BIN — 1CPT 뒤에 일기 데이터가 붙어 있어 압축 길이를 넘기면 안 됨)
    import gfx_nikki
    raw = open(os.path.join(cpt.DISC, 'NIKKI.BIN'), 'rb').read(); blob, end = cpt.unpack(raw, 0x40)
    comp = cpt.pack(gfx_nikki.redraw(blob)); old = end - 0x40
    if len(comp) > old:
        raise SystemExit('⛔NIKKI.BIN 압축 %d B > 원래 %d B' % (len(comp), old))
    files['NIKKI.BIN'] = raw[:0x40] + comp + bytes(old - len(comp)) + raw[end:]
    print('%-12s 스프라이트 %3d · 압축 %d/%d B' % ('NIKKI.BIN', 2, len(comp), old))
    for f, v in files.items():                                  # 검산: 다시 풀어 크기·뒤쪽 바이트
        o = open(os.path.join(cpt.DISC, f), 'rb').read()
        assert len(v) == len(o), f
    if preview:
        sheets(prev)
    return files


# 미리보기용 실제 팔레트(스테이트 CRAM + VDP1 COLR 뱅크) — 묶음별 대표값, 번호별 예외
PAL = {'GLD': ('메인메뉴', 0x61C0), 'ST': ('서브메뉴', 0x6200), 'SYS': ('장소', 0x6010), 'CONF': ('컨피그', 0x2270), 'KAISOU': ('컨피그', 0x2270)}
PAL_K = {('SYS', k): ('장비', 0x7070) for k in range(102, 114)}
PAL_K.update({('SYS', k): ('도구', 0x7050) for k in range(134, 142)})
PAL_K.update({('SYS', k): ('서브메뉴', 0x4060) for k in range(162, 175)})


def palette(g, k):
    st = PAL_K.get((g, k)) or PAL.get(g)
    if not st:
        return [(0, 0, 0)] + [(40 + i * 13,) * 3 for i in range(1, 16)]
    cram = open(os.path.join(ROOT, 'work', 'mem', st[0], 'CRAM.bin'), 'rb').read()
    out = []
    for i in range(16):
        c = struct.unpack_from('>H', cram, ((st[1] + i) * 2) % len(cram))[0]
        out.append(((c & 31) << 3, (c >> 5 & 31) << 3, (c >> 10 & 31) << 3))
    out[0] = (60, 50, 40)
    return out


def sheets(prev):
    from PIL import Image, ImageDraw
    for g, shots in prev.items():
        S = 3; W = max(len(P[0]) for _, P, _, _, _ in shots) * S
        H = sum(len(P) * S + 4 for _, P, _, _, _ in shots)
        im = Image.new('RGB', (W * 2 + 140, H), (30, 30, 60)); dr = ImageDraw.Draw(im); y = 0
        for k, P, N, fn, ko in shots:
            pal = [(25, 25, 50)] + [(150 + i * 7,) * 3 for i in range(1, 16)]
            if (g, k) == ('ST', 44):
                pal[3] = (70, 70, 80); pal[4] = (40, 40, 40); pal[1] = (120, 120, 120)
            else:
                pal[style(g, k)['edge']] = (90, 60, 60)
            for col, Q in ((0, P), (1, N)):
                for yy, row in enumerate(Q):
                    for xx, c in enumerate(row):
                        if True:
                            dr.rectangle([col * (W + 10) + xx * S, y + yy * S, col * (W + 10) + xx * S + S - 1, y + yy * S + S - 1], fill=pal[c])
            dr.text((W * 2 + 24, y), '%d %s' % (k, fn[-4:]), fill=(255, 255, 0))
            y += len(P) * S + 4
        p = os.path.join(ROOT, 'work', 'sheet', 'gfx_%s.png' % g); im.save(p); print(p)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    build('--preview' in sys.argv)

