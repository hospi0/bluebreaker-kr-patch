# -*- coding: utf-8 -*-
r"""번역 삽입 (2026-10-02) — work/ko/{scr,sys}.tsv → 4.KNJ · SCR.BIN · 0.BIN 등 → 트랙 1
  글자: 번역에 나오는 한글 음절을 4.KNJ 한자 칸(JIS 16구 1점부터 차례로)에 갈무리14 로 그리고 그 SJIS 코드로 쓴다.
  대사(SCR.BIN): 묶음(tools/scrblk.py)마다 대사 단위를 바꿔 다시 짜고 머리 오프셋 표를 고친다
                 (점프는 스크립트 번호라 그대로) — 새 묶음이 원래 묶음 칸(다음 묶음 시작까지)을 넘으면 빌드 실패.
                 ★묶음 목록·«읽는 길이» = 0.BIN 0x6E3E4 표 — 길이 뒤 찌꺼기는 버리고 새 길이를 표에 쓴다.
  메뉴(0.BIN 등): 제자리 — 원래 바이트 안, 남는 곳은 00. 0x1FA24 «す。»(두 설정 설명의 둘째 줄 공용) → «다。».
  빌더 규칙: 문장부호 뒤 공백 1칸 삭제 · 대사의 ASCII 영숫자·괄호 → 전각(원문 대사엔 1바이트가 쉼표·반각 가나뿐)
             · 대사 한 줄 폭 ≤ 17(전각 1 · 반각 0.5) · 인코딩 못 하는 글자 = 빌드 실패.
  동영상(Z##.CPK): tools/moviesub.py 가 구운 work/kr/Z##.CPK(원본과 같은 크기)를 제자리로.
  python tools/insert.py [--dry] [--install]
"""
import json, os, re, shutil, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import disc, iso, poc, scrblk
from ko_merge import width

DISC = os.path.join(ROOT, 'work', 'disc')
OUT = poc.OUT
INSTALL = r'F:\hospi\roms\ss roms\Blue Breaker - Ken yori mo Hohoemi o (Japan)'
PUNCT = ',.!?:;)]}\'"~、。，．！？：；）］｝」』】〉》”’…‥・·～〜♪♥'
NL = chr(92) + 'n'
WIDTH = 17
TOK = re.compile(r'\{[^}]*\}|\\n')


def squeeze(s):
    """문장부호 뒤 공백 1칸 삭제(2칸 이상은 칸 맞춤이라 둔다)"""
    return re.sub('([' + re.escape(PUNCT) + ']) (?! )', r'\1', s)


def to_full(s, letters_only=False):
    """토큰 밖 ASCII 영숫자·괄호 → 전각. letters_only(보충 제자리 줄) = 영문자만(4.KNJ 1바이트 칸에 숫자·부호 글자는 있고 영문자는 비어 있음 — 원문 반각 숫자 «0日目» 유지)"""
    out = []
    for t in re.split(r'(\{[^}]*\}|\\n)', s):
        if not TOK.fullmatch(t or 'x'):
            t = ''.join(chr(ord(c) + 0xFEE0) if c.isascii() and (c.isalpha() if letters_only else (c.isalnum() or c in '()')) else c for c in t)
        out.append(t)
    return ''.join(out)


def load(name):
    rows = [l.split('\t') for l in open(os.path.join(ROOT, 'work', 'ko', name + '.tsv'), encoding='utf-8').read().split('\n')[1:] if l]
    return {r[0]: r for r in rows}


def charmap(texts):
    syl = sorted({c for t in texts for c in TOK.sub('', t) if '가' <= c <= '힣'})
    cmap = {}
    for k, ch in enumerate(syl):
        ku, ten = 16 + k // 94, 1 + k % 94
        cmap[ch] = (ku, ten, poc.sjis_of(ku, ten))
    return cmap


def encode(s, cmap):
    out = bytearray()
    for t in re.split(r'(\{[^}]*\}|\\n)', s):
        if not t:
            continue
        if t == NL:
            out += b'RT'
        elif t in ('{PC}', '{EP}', '{TC}'):
            out += t[1:3].encode()
        elif re.fullmatch(r'\{MK\d\}', t):
            out += t[1:4].encode()
        elif t.startswith('{NMR:'):
            out += b'NMR' + t[5:-1].encode()
        elif t.startswith('{NM:'):                                # NM + 4자(기술 설명의 «NM2000», tools/extract3.py)
            out += b'NM' + t[4:-1].encode()
        elif t == '{sp}':
            out += b' '
        elif t.startswith('{a:'):
            out.append(int(t[3:5], 16))
        else:
            for c in t:
                if c in cmap:
                    out += cmap[c][2]
                else:
                    try:
                        out += c.encode('cp932')
                    except UnicodeEncodeError:
                        raise SystemExit('⛔인코딩 못 하는 글자 %r in %r' % (c, s))
    return bytes(out)


def rebuild(d, b, offs, e, mine, tr, cmap):
    """묶음 [b, e) 안 대사 단위 mine 을 번역으로 바꾸고 머리 오프셋 표를 고친 새 묶음"""
    parts, pos, shifts = [], b, []
    for o in mine:
        new = encode(tr[o['id']], cmap)
        if o['id'].startswith(('C', 'D')):                       # 보충(tools/extract2.py·extract3.py) = 제자리 — 원래 길이, 남으면 반각 공백
            room = o['end'] - o['start']
            if len(new) > room:
                raise SystemExit('⛔보충 %s 예산 %d B < %d B' % (o['id'], room, len(new)))
            new += b' ' * (room - len(new))
        parts.append(d[pos:o['start']]); parts.append(new)
        shifts.append((o['start'] - b, len(new) - (o['end'] - o['start'])))
        pos = o['end']
    parts.append(d[pos:e])
    blk = bytearray(b''.join(parts))
    starts = {o['start'] for o in mine}
    for k, off in enumerate(offs):
        no = off + sum(dl for s, dl in shifts if s < off)
        struct.pack_into('>I', blk, 4 * k, no)
        if d[b + off] != blk[no] and (off + b) not in starts:   # 검산: 스크립트 첫 바이트(명령)가 그대로인지(글로 시작하는 항목 = 아이템 설명 등은 제외)
            raise SystemExit('⛔오프셋 검산 실패 묶음 %X 항목 %d' % (b, k))
    return blk


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    scr_tr, sys_tr = load('scr'), load('sys')
    if os.path.exists(os.path.join(ROOT, 'work', 'ko', 'scr2.tsv')):
        scr_tr.update(load('scr2'))                              # 보충 추출(C#####)
    if os.path.exists(os.path.join(ROOT, 'work', 'ko', 'sys2.tsv')):  # 보충 추출 3(D#####) — SCR.BIN 줄은 대사 쪽, 나머지는 메뉴 쪽
        for k, r in load('sys2').items():
            (scr_tr if r[1].startswith('SCR.BIN') else sys_tr)[k] = r
    tr = {}
    errs = []
    for i, r in scr_tr.items():
        if r[5]:
            t = to_full(squeeze(r[5]), letters_only=i.startswith(('C', 'D')))
            if r[2] == '나레이션':                                # 실기 «나레이션 들여쓰기x» — 첫 줄 전각 공백 들여쓰기 뺌
                t = t.lstrip('　')
            for seg in t.replace('{PC}', NL).split(NL):
                if width(seg) > WIDTH:
                    errs.append('%s 폭 %.1f > %d: %s' % (i, width(seg), WIDTH, seg))
            tr[i] = t
    for i, r in sys_tr.items():
        if r[5]:
            tr[i] = squeeze(r[5])
    if errs:
        raise SystemExit('⛔대사 줄 폭 초과 %d줄\n' % len(errs) + '\n'.join(errs))
    cmap = charmap(list(tr.values()))
    print('번역 %d줄 · 한글 %d자 → KNJ %d구‥%d구' % (len(tr), len(cmap), 16, 16 + (len(cmap) - 1) // 94))

    # 글꼴
    F = poc.bdf.Font(poc.GAL)
    knj = bytearray(open(os.path.join(DISC, '4.KNJ'), 'rb').read())
    for ch, (ku, ten, _) in cmap.items():
        i = 128 + (ku - 1) * 94 + (ten - 1)
        knj[i * 32:i * 32 + 32] = poc.glyph(F, ch)

    occ = json.load(open(os.path.join(ROOT, 'work', 'extract.json'), encoding='utf-8'))
    files = {'4.KNJ': bytes(knj)}

    # 대사 SCR.BIN — 묶음마다 다시 짜기
    d = open(os.path.join(DISC, 'SCR.BIN'), 'rb').read()
    out = bytearray(d)
    units = sorted((o for o in occ if o['sec'] == 'scr' and o['id'] in tr), key=lambda o: o['start'])
    d0 = open(os.path.join(DISC, '0.BIN'), 'rb').read()
    B = scrblk.table_blocks(d, d0); over = []; nchg = 0; ngrow = 0
    sizes = {}                                                   # 0.BIN 묶음 표 주소 → 새 «읽는 길이»
    for b, n, offs, e, sz, ta in B:
        # 읽는 길이 뒤(찌꺼기)에 걸친 단위는 버린다 — 게임이 안 읽는다
        mine = [o for o in units if o['start'] >= b and o['end'] <= b + sz]
        if not mine:
            continue
        blk = rebuild(d, b, offs, b + sz, mine, tr, cmap)
        if len(blk) > e - b or len(blk) > 0xFFFF:
            over.append('%X: %d B > 칸 %d B' % (b, len(blk), e - b)); continue
        out[b:e] = bytes(blk) + bytes(e - b - len(blk))
        sizes[ta] = len(blk); nchg += 1; ngrow += len(blk) > sz
    if over:
        raise SystemExit('⛔묶음 칸 초과 %d곳\n' % len(over) + '\n'.join(over))
    files['SCR.BIN'] = bytes(out)
    big = max(sizes.values(), default=0); old_max = max(x[4] for x in B)
    print('대사 단위 %d · 바뀐 묶음 %d/%d (원래 읽는 길이보다 길어진 것 %d) · 가장 긴 묶음 %X (원본 최대 %X)' % (len(units), nchg, len(B), ngrow, big, old_max))
    if big > old_max:
        print('  ⚠원본 최대 길이보다 긴 묶음 — 스크립트 버퍼(Low RAM 0x200000) 넘침 여부 실기 확인')

    # 메뉴 — 제자리
    bufs = {}; over = []; nput = 0
    # ★고정 칸 이름(아이템·무기 표: 12 B 칸이 16 B 간격으로 늘어선 것, 또는 원문이 «　» 로 칸을 채운 것)은 남는 자리를 00 이 아니라 반각 공백으로.
    #   원문은 늘 칸을 꽉 채워 쓴다 — 상점 목록은 칸 수만큼 셀을 잡아, 11 B + 00 이면 셀이 한 칸 어긋나 «꽃» 뒤 찌꺼기·가격 숫자가 이름 칸에 겹쳤다(실기 2026-10-02).
    rooms = {(o['file'], o['start']): o['end'] - o['start'] for o in occ if o['sec'] == 'sys'}
    def fixed(o):
        r = o['end'] - o['start']
        if o['text'].endswith('　'):
            return True
        return r == 12 and (rooms.get((o['file'], o['start'] - 16)) == 12 or rooms.get((o['file'], o['start'] + 16)) == 12)
    nfix = 0
    for o in occ:
        if o['sec'] != 'sys' or o['id'] not in tr:
            continue
        f = o['file']
        if f not in bufs:
            bufs[f] = bytearray(open(os.path.join(DISC, f), 'rb').read())
        new = encode(tr[o['id']], cmap); room = o['end'] - o['start']
        if len(new) > room:
            over.append('%s %s:%X 예산 %d B < %d B  %s' % (o['id'], f, o['start'], room, len(new), tr[o['id']])); continue
        pad = b' ' if fixed(o) else b'\0'
        nfix += pad == b' ' and len(new) < room
        bufs[f][o['start']:o['end']] = new + pad * (room - len(new)); nput += 1
    if over:
        raise SystemExit('⛔메뉴 문자열 예산 초과 %d곳\n' % len(over) + '\n'.join(sorted(set(over))))
    b0 = bufs.setdefault('0.BIN', bytearray(open(os.path.join(DISC, '0.BIN'), 'rb').read()))
    assert bytes(b0[0x1FA24:0x1FA28]) == 'す。'.encode('cp932')
    b0[0x1FA24:0x1FA26] = encode('다', cmap)
    for ta, n in sizes.items():                                  # SCR.BIN 묶음 «읽는 길이» 표(tools/scrblk.py TABLE)
        struct.pack_into('>H', b0, ta + 2, n)
    for f, v in bufs.items():
        files[f] = bytes(v)
    print('메뉴 %d자리(고정 칸 공백 채움 %d) · 바뀐 파일 %s' % (nput, nfix, sorted(files)))

    import gfx                                                   # 그림 글자(1CPT 그림 묶음 — tools/gfx.py, work/ko/gfx.tsv)
    for f, v in gfx.build().items():
        assert f not in files, f
        files[f] = v
    # ★상태창 이름 팔레트(CRAM 0x470 ← SYS.BIN 0xE0, 16색 RGB555): 홀수 = 흰 그러데이션, 짝수 = 보라 강조.
    #   원본 가나 이름은 전용 굵은 글꼴의 강조 픽셀을 쓰지만, 한글(4.KNJ 1bpp)은 3·7번 줄 전체가 강조색(4·8)으로 칠해져 가로줄(실기 2026-10-02)
    #   → 4번 = 3번 색, 8번 = 7번 색(이름이 전부 한글이라 가나 강조는 안 쓰임)
    sy = bytearray(files.get('SYS.BIN') or open(os.path.join(DISC, 'SYS.BIN'), 'rb').read())
    assert sy[0xE0:0xE4] == bytes.fromhex('00007fff'), 'SYS.BIN 이름 팔레트 위치 불일치'
    sy[0xE8:0xEA] = sy[0xE6:0xE8]; sy[0xF0:0xF2] = sy[0xEE:0xF0]
    files['SYS.BIN'] = bytes(sy)
    import sidename                                              # 전투 HUD 동료·적 이름 그림(SIDEFILE.BIN 1BIN — tools/sidename.py, work/ko/side_names.tsv)
    files['SIDEFILE.BIN'] = sidename.build()
    import title                                                 # 타이틀 화면 부제·작은 가타카나(BG.BIN 1SBG @0x2C3000 — tools/title.py)
    files.update(title.build())
    import glob                                                  # 동영상 자막(tools/moviesub.py → work/kr/Z##.CPK, 원본과 같은 크기 — 제자리)
    for p in sorted(glob.glob(os.path.join(ROOT, 'work', 'kr', 'Z*.CPK'))):
        nm = os.path.basename(p)
        assert os.path.getsize(p) == os.path.getsize(os.path.join(ROOT, 'work', 'movie', 'cpk', nm)), nm
        files[nm] = open(p, 'rb').read()
    os.makedirs(os.path.join(ROOT, 'work', 'new'), exist_ok=True)       # 고친 파일 사본(분석용)
    for f, v in files.items():
        if not f.endswith('.CPK'):                               # 동영상은 work/kr 에 이미 있음
            open(os.path.join(ROOT, 'work', 'new', f), 'wb').write(v)
    if '--dry' in sys.argv:
        print('(--dry: 디스크 안 씀)'); return
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    iso.patch(disc.ROM, OUT, files)
    print('→', OUT)
    if '--install' in sys.argv:
        dst = os.path.join(INSTALL, os.path.basename(OUT))
        shutil.copy2(OUT, dst); print('F: 설치', dst)


if __name__ == '__main__':
    main()
