# -*- coding: utf-8 -*-
r"""전투 HUD 동료·적 이름 그림 — SIDEFILE.BIN «1BIN» 덩어리(1CPT 와 같은 코덱: 머리 '1BIN' + u32 BE 풀린 크기) 안 구운 그림 (2026-10-02)
  이름 칸 = 16×16 4bpp 스프라이트 세 장(0x180 B, 48×8 — 아래 8줄 비움, 색 0·1(그림자)·F(글자)). 칸이 여러 개 이어지기도 함(유닛마다 이름·별칭).
  python tools/sidename.py scan   → work/side/slots.json (덩어리·칸 위치·그림 해시) · work/sheet/side_uniq.png (고유 그림 번호표)
"""
import hashlib, json, os, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
SIDE = os.path.join(ROOT, 'work', 'disc', 'SIDEFILE.BIN')
SLOT = 0x180


def unpack(d, p):
    assert d[p:p + 4] == b'1BIN'
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


def chunks(d):
    i = d.find(b'1BIN')
    while i >= 0:
        yield i
        i = d.find(b'1BIN', i + 1)


def is_name_cell(c):
    if any(c[64:128]):
        return False
    nib = {b >> 4 for b in c[:64]} | {b & 15 for b in c[:64]}
    return nib <= {0, 1, 15} and 15 in nib


def ink(t):
    return sum(1 for b in t for v in (b >> 4, b & 15) if v == 15)


def rows(t):
    """0x180 칸 → 8줄 × 48 색 번호"""
    return [[(t[s * 128 + y * 8 + x // 2] >> (4 if x % 2 == 0 else 0)) & 15 for s in range(3) for x in range(16)] for y in range(8)]


def is_rule(t):
    """가로줄·화살표 같은 그림 잡음(한 줄에만 잉크가 몰림)"""
    r = rows(t)
    used = [y for y in range(8) if any(v == 15 for v in r[y])]
    return len(used) <= 2


def scan():
    d = open(SIDE, 'rb').read()
    slots = []
    for p in chunks(d):
        o, _ = unpack(d, p)
        k = 0
        while k + 128 <= len(o):
            if not is_name_cell(o[k:k + 128]):
                k += 128; continue
            j = k
            while j + 128 <= len(o) and is_name_cell(o[j:j + 128]):
                j += 128
            for s in range(k, j, SLOT):
                t = o[s:s + SLOT]
                if len(t) < SLOT or any(t[c + 64:c + 128] for c in (0, 128, 256) if c < len(t)) and False:
                    pass
                t = t.ljust(SLOT, b'\0')
                if ink(t) >= 20 and not is_rule(t) and all(not any(t[c + 64:c + 128]) for c in (0, 128, 256)):
                    slots.append({'chunk': p, 'off': s, 'hash': hashlib.md5(t).hexdigest()[:10]})
            k = j
    return slots


if __name__ == '__main__' and sys.argv[1:] == ['scan']:
    from PIL import Image, ImageDraw
    d = open(SIDE, 'rb').read()
    slots = scan()
    uniq = {}
    cache = {}
    for s in slots:
        if s['hash'] not in uniq:
            if s['chunk'] not in cache:
                cache[s['chunk']] = unpack(d, s['chunk'])[0]
            uniq[s['hash']] = cache[s['chunk']][s['off']:s['off'] + SLOT]
    order = list(uniq)
    for s in slots:
        s['n'] = order.index(s['hash'])
    os.makedirs(os.path.join(ROOT, 'work', 'side'), exist_ok=True)
    json.dump(slots, open(os.path.join(ROOT, 'work', 'side', 'slots.json'), 'w'), indent=0)
    per = 40
    cols = (len(order) + per - 1) // per
    im = Image.new('L', (cols * 90, per * 11), 0); dr = ImageDraw.Draw(im)
    for n, h in enumerate(order):
        r = rows(uniq[h]); X = (n // per) * 90; Y = (n % per) * 11
        dr.text((X, Y - 1), '%d' % n, fill=150)
        for y in range(8):
            for x in range(48):
                im.putpixel((X + 18 + x, Y + y), r[y][x] * 17)
    im.resize((im.width * 4, im.height * 4), Image.NEAREST).save(os.path.join(ROOT, 'work', 'sheet', 'side_uniq.png'))
    print('칸 %d · 고유 그림 %d' % (len(slots), len(order)))


# ── 빌드: work/ko/side_names.tsv(번호·원문·번역) → 같은 그림(해시)인 칸 전부 다시 그려 1BIN 재압축·제자리 ──
G7 = r'C:\claude\utils\font\Galmuri-v2.40.3\Galmuri7.bdf'
INK, SHADOW = 15, 1                                  # 원본: 글자 F + 오른쪽 1px 그림자 1 (아래 그림자 없음)


def render(text):
    sys.path.insert(0, r'C:\claude\project\anearth-kr-patch\tools')
    import bdf
    F = bdf.Font(G7)
    pts, _ = F.draw(text, 0, 0)
    xs = [x for x, _ in pts]; ys = [y for _, y in pts]
    w = max(xs) - min(xs) + 1
    if w + 1 > 48:
        raise SystemExit('⛔HUD 이름 %r 폭 %dpx > 47' % (text, w))
    oy = (8 - (max(ys) - min(ys) + 1)) // 2 - min(ys)
    ink = {(x - min(xs), y + oy) for x, y in pts}
    g = [[0] * 48 for _ in range(8)]
    for x, y in ink:
        if 0 <= y < 8 and x + 1 < 48 and (x + 1, y) not in ink:
            g[y][x + 1] = SHADOW
    for x, y in ink:
        if 0 <= y < 8:
            g[y][x] = INK
    t = bytearray(SLOT)
    for s in range(3):
        for y in range(8):
            for x in range(0, 16, 2):
                t[s * 128 + y * 8 + x // 2] = (g[y][s * 16 + x] << 4) | g[y][s * 16 + x + 1]
    return bytes(t)


def pack_lazy(data, tag=b'1BIN'):
    """cpt.pack 과 같은 형식, 한 칸 내다보기(다음 자리 일치가 더 길면 지금은 글자 하나로) — 탐욕보다 조금 작다"""
    n = len(data)

    def best(i):
        bl, bd = 0, 0
        for dist in range(1, min(256, i) + 1):
            s = i - dist; l = 0
            while l < 130 and i + l < n and data[s + l] == data[i + l]:
                l += 1
            if l > bl:
                bl, bd = l, dist
                if l == 130:
                    break
        return bl, bd
    out = bytearray(tag + struct.pack('>I', n)); lit = bytearray(); i = 0

    def flush():
        while lit:
            c = lit[:127]; out.append(len(c)); out.extend(c); del lit[:127]
    nxt = best(0) if n else (0, 0)
    while i < n:
        l, dd = nxt
        if l >= 3:
            l2, _ = best(i + 1) if i + 1 < n else (0, 0)
            if l2 > l + 1:
                lit.append(data[i]); i += 1; nxt = (l2, _); continue
            flush(); out.append(256 - (l - 2)); out.append(dd - 1); i += l
        else:
            lit.append(data[i]); i += 1
        nxt = best(i) if i < n else (0, 0)
    flush(); out.append(0)
    return bytes(out)


# ── 전투 «ミス!» 글자(2026-10-02 실기): SIDEFILE 1BIN@0x2E80 풀린 본의 16×16 칸 — 왼쪽 8px 만 쓰고 8px 간격으로 늘어놓는다(VDP1 0x27F00‥).
#   원본 꼴 = 채움 D + 4방 1px 테두리 1. 한글은 손으로 그린 채움 모양(아래 «#») → 테두리 자동.
MISS_CHUNK = 0x2E80
MISS = {0x5C80: ('ミ', '미', ['', '', '', '',
                               '.###.##', '.#.#.##', '.#.#.##', '.#.#.##', '.#.#.##', '.###.##',
                               '.....##', '.....##', '.....##', '.....##', '.....##']),
        0x5D00: ('ス', '스', ['', '', '', '',
                               '...##', '...##', '...##', '..####', '.##..##', '.#....#',
                               '', '', '', '.######', '.######'])}
FILL, EDGE = 13, 1


def miss_cell(rows):
    fill = {(x, y) for y, r in enumerate(rows) for x, c in enumerate(r) if c == '#'}
    t = bytearray(128)
    for y in range(16):
        for x in range(8):
            v = FILL if (x, y) in fill else EDGE if any((x + dx, y + dy) in fill for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))) else 0
            t[y * 8 + x // 2] |= v << (4 if x % 2 == 0 else 0)
    return bytes(t)


def build():
    """→ SIDEFILE.BIN 새 바이트(바뀐 1BIN 덩어리만 다시 압축, 원래 압축 길이 이하 + 0 채움)"""
    import cpt
    tr = {}
    for l in open(os.path.join(ROOT, 'work', 'ko', 'side_names.tsv'), encoding='utf-8').read().split('\n')[1:]:
        c = l.split('\t')
        if len(c) >= 3 and c[2].strip():
            tr[int(c[0])] = c[2].strip()
    d = bytearray(open(SIDE, 'rb').read())
    slots = scan()
    uniq = []
    for s in slots:
        if s['hash'] not in uniq:
            uniq.append(s['hash'])
    by_chunk = {}
    for s in slots:
        n = uniq.index(s['hash'])
        if n in tr:
            by_chunk.setdefault(s['chunk'], []).append((s['off'], tr[n]))
    by_chunk.setdefault(MISS_CHUNK, [])
    starts = sorted(chunks(bytes(d)))
    nslot = 0
    for p, items in sorted(by_chunk.items()):
        o, end = unpack(bytes(d), p)
        o = bytearray(o)
        for off, text in items:
            o[off:off + SLOT] = render(text); nslot += 1
        if p == MISS_CHUNK:
            for off, (jp, ko, rows_) in MISS.items():
                assert o[off + 3 * 8:off + 4 * 8] != bytes(8), '«%s» 칸 %X 비어 있음' % (jp, off)
                o[off:off + 128] = miss_cell(rows_)
        c = b'1BIN' + cpt.pack(bytes(o))[4:]
        if len(c) > end - p:
            c2 = pack_lazy(bytes(o))
            if len(c2) < len(c):
                c = c2
        nxt = next((q for q in starts if q > p), len(d))
        room = end - p
        while p + room < nxt and d[p + room] == 0:            # 뒤 0 여백(섹터 채움)까지 — 다음 덩어리 전까지
            room += 1
        if nxt % 0x800 == 0 or nxt == len(d):
            # 레코드 = 0x800 경계에서 [덩어리 A][4B 정렬][덩어리 B][다음 섹터까지 이전 데이터 찌꺼기] — B(레코드 마지막)는 다음 레코드 전까지 써도 됨
            room = nxt - p
        if len(c) > room:
            raise SystemExit('⛔SIDEFILE 1BIN %X 압축 %d > 원래 %d' % (p, len(c), room))
        d[p:p + len(c)] = c
        d[p + len(c):p + max(room, end - p)] = bytes(max(room, end - p) - len(c))
    print('HUD 이름 그림 %d칸 · 덩어리 %d개' % (nslot, len(by_chunk)))
    return bytes(d)
